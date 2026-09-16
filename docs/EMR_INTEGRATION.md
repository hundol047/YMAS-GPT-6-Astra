# EMR Adapter 경계

`backend/app/services/emr_adapter.py`는 이제 `BaseEMRAdapter` 인터페이스와 두 구현체로 나뉩니다.

- **DemoAdapter** (기존, 변경 없음): `backend/data/patients.json`만 읽습니다.
- **FHIRAdapter** (신규): 실제 FHIR R4 서버와 SMART on FHIR client_credentials OAuth2로 통신합니다. **이 개발 환경에서 접근 가능한 실제 병원 FHIR 서버가 없어 실제 서버 대상으로는 검증하지 못했습니다.** 가짜 FHIR 서버(`httpx.MockTransport`)를 대상으로 요청/응답 파싱 정확성만 단위 테스트했습니다 (`backend/tests/test_fhir_adapter.py`). 실제 기관 서버에 연결하기 전 그 서버 자체를 대상으로 별도 검증이 필요합니다.

`EMR_MODE=demo`(기본) 또는 `EMR_MODE=fhir`로 전환합니다. FHIR 모드 환경변수:

| 변수 | 용도 |
|---|---|
| `FHIR_BASE_URL` | FHIR 서버 base URL (필수) |
| `FHIR_AUTH_MODE` | `client_credentials`(기본) 또는 `smart` — 아래 참고 |
| `FHIR_CLIENT_ID` / `FHIR_CLIENT_SECRET` | `FHIR_AUTH_MODE=client_credentials`일 때만 사용 (없으면 무인증 요청) |
| `FHIR_SCOPE` | 기본 `system/*.read` |
| `FHIR_TOKEN_URL` | `.well-known/smart-configuration` discovery 실패 시 수동 지정 |
| `FHIR_REDIRECT_URI` | SMART App Launch용 (`GET /smart/launch`, `GET /smart/callback`) |
| `SYNEX_SMART_TRUSTED_ISSUER` | `FHIR_AUTH_MODE=smart`일 때 세션의 `iss`와 비교할 신뢰 issuer. 생략 시 `FHIR_BASE_URL`을 그대로 사용 |

비밀값은 환경변수에서만 읽으며 Git이나 Docker 이미지에 넣지 않습니다.

### FHIR_AUTH_MODE: client_credentials vs smart

`FHIRAdapter`가 각 요청에 붙일 토큰을 어떻게 구하는지는 두 가지 모드로 완전히 분리되어 있고, 절대 섞이지 않습니다(`backend/app/services/emr_adapter.py`의 `TokenProvider` 구현체 두 개):

- **`FHIR_AUTH_MODE=client_credentials`(기본, 이전과 동일)**: `SmartOAuthClient`가 발급한 앱 전역 토큰 하나를 모든 요청에 사용합니다. `FHIR_CLIENT_ID`가 없으면 토큰 없이(이미 인증된/네트워크 제한된 엔드포인트라고 가정) 요청합니다.
- **`FHIR_AUTH_MODE=smart`**: 실제 SMART App Launch → 세션 → FHIR 요청 체인을 사용합니다. 각 요청은 그 브라우저의 `synex_session` 쿠키가 가리키는 세션에 저장된, 그 임상의 본인의 access token을 사용합니다(공유 토큰이 아님). **Fail-closed입니다**: 유효한 세션이 없거나, 세션이 만료됐거나, 세션의 `iss`가 `SYNEX_SMART_TRUSTED_ISSUER`(또는 `FHIR_BASE_URL`)와 일치하지 않으면 — FHIR 서버로 요청을 아예 보내지 않고 `401`을 반환합니다(`SmartAuthRequired` 예외 → `main.py`의 전역 exception handler). 무인증 요청으로 조용히 넘어가는 경로는 없습니다. Issuer 검증은 trailing slash만 정규화하고 나머지는 정확히 일치해야 합니다 — 다른 병원 FHIR 서버 앞으로 발급된 토큰을 이 서버로 보내는 사고를 막기 위함입니다.

이 access token은 세션 저장소(`backend/app/services/smart_launch.py`의 `_SessionStore`)에만 있으며, 브라우저·로그·감사 기록 어디에도 노출되지 않습니다 — 세션은 `SESSION_TTL_SECONDS`(8시간)가 지나면 `context()`/`token_for()` 조회 시점에 실제로 만료 처리되어(다음 `put()`을 기다리지 않고) `None`을 반환하고 해당 행을 삭제합니다.

| 내부 자료 | FHIR R4 리소스 | 구현 상태 |
|---|---|---|
| 기본 정보 | Patient | 구현 (name/gender/birthDate → age) |
| 활성 약물 | MedicationStatement / MedicationRequest | 구현 |
| 기저질환 | Condition | 구현 (텍스트만; 코드 매핑은 `terminology_mapper.py`가 별도 수행) |
| 알레르기·반응 | AllergyIntolerance | 구현 |
| 검사 이력 | Observation | 구현 (검사 수치) + 키/몸무게 (LOINC 8302-2/29463-7, cm·in / kg·lb 단위 인식 후 변환; 다른 단위나 값이 없으면 `missing`에 기록하고 3D 인체도는 기본 체형으로 표시) |
| 진료/영상 | Encounter, DiagnosticReport, ImagingStudy | 구현 (`Patient.encounters`/`diagnostic_reports`/`imaging_studies`에 간단한 요약 형태로 매핑: id/날짜/종류 또는 명칭/상태[/결론 또는 modality]. 전체 FHIR 리소스를 그대로 저장하지는 않음). 환자가 이 이력이 없는 것은 검사·약물·기저질환과 달리 정상적인 상태라 `missing`에 gap으로 기록하지 않음 |
| 환자 목록 조회 | 전체 roster 검색 | **의도적 미구현.** `FHIRAdapter.list()`는 `NotImplementedError`를 던집니다 — 기관 승인된 전체 검색 스코프가 보통 없고, 실제 사용 경로는 SMART App Launch가 넘겨주는 단일 환자 id이기 때문입니다. `GET /patients`가 501을 반환하면 프론트엔드는 사이드바 목록 대신 "환자 ID 직접 입력" 조회창을 보여줍니다(`frontend/src/App.jsx`의 `patientsUnavailable` 상태) — `/catalog` 등 다른 초기 로드는 이 501에 더 이상 함께 실패하지 않습니다. |

누락된 필드는 `Patient.missing`에 그대로 기록됩니다 (예: `"condition history (none returned)"`) — 임의로 정상으로 보정하지 않습니다.

`GET /patients/{id}/fhir`(DemoAdapter)는 여전히 **데모 projection**입니다. FHIR 모드에서는 서버가 이미 제공하는 `Patient/{id}/$everything` 번들을 그대로 전달합니다(재가공하지 않음).

## 표준 코드 정규화

`backend/app/services/terminology_mapper.py`가 RxNorm/ATC(약물)·LOINC(검사)·ICD-10/SNOMED CT(진단) 매핑을 담당합니다. 고정 참조 테이블 방식이며, 매핑이 없으면 `mapping_status:'unmapped'`로 명시합니다 — 임의 추정하지 않습니다. `GET /patients/{id}/terminology`로 확인할 수 있습니다. 178개 약물 카탈로그 중 21개(성분급 RxCUI/ATC를 안정적으로 확인 가능한 것만, `backend/data/patients.json`이 실제로 쓰는 13개 전부 포함)만 매핑했습니다; 이 환경은 외부 네트워크가 막혀 있어 RxNav 등 실시간 용어 API로 나머지를 검증할 수 없었습니다 — 확장은 검증된 코드를 테이블에 직접 추가하는 방식으로만 하고, 불확실한 코드는 절대 채우지 않습니다. 검사(lab)·기저질환(condition) 매핑은 이 앱이 실제로 쓰는 값(검사 7종, 상병 4종) 전부를 이미 커버합니다.

## CDS Hooks / SMART App Launch

`GET /cds-services`, `POST /cds-services/synex-medication-safety`(`medication-prescribe` 훅)가 구현되어 있습니다 (`backend/app/services/cds_hooks.py`). 자체 데모 환자를 대상으로 스펙 형태를 테스트했습니다(`backend/tests/test_cds_hooks.py`) — **실제 EMR의 CDS Hooks 클라이언트에서 카드가 어떻게 렌더링되는지는 검증하지 않았습니다.**

`GET /smart/launch?iss=...&launch=...`, `GET /smart/callback`이 PKCE 기반 SMART App Launch를 구현합니다 (`backend/app/services/smart_launch.py`). 가짜 인가서버를 대상으로 PKCE/redirect 구성만 테스트했습니다 — **실제 EMR 런처나 실제 FHIR 인가서버와의 라운드트립은 검증하지 않았습니다.**

launch state(state→code_verifier 매핑) 저장소는 두 가지입니다:
- `SYNEX_REDIS_URL` 미설정(기본): 로컬 SQLite(`backend/data/smart_launch.sqlite3`, `SYNEX_SMART_LAUNCH_PATH`로 변경 가능). 단일 인스턴스 배포 기준 프로세스 재시작에는 살아남지만(이전에는 순수 in-memory dict라 재시작 시 진행 중인 런치가 전부 소실됐습니다), 워커/레플리카가 여러 개면 서로 파일을 공유하지 못해 여전히 안 됩니다.
- `SYNEX_REDIS_URL` 설정 시: `_RedisLaunchStore`. 같은 Redis를 보는 모든 워커/레플리카가 launch state를 공유하며, 항목은 10분 후 자동 만료됩니다(별도 정리 작업 불필요). **실제 로컬 `redis-server`를 띄워 두 개의 독립된 `_RedisLaunchStore` 인스턴스(별도 워커 프로세스를 시뮬레이션)로 검증했습니다** — 목(mock)이 아닙니다 (`backend/tests/test_smart_launch_redis.py`; redis-server가 없는 환경에서는 깨끗하게 skip됩니다). 즉 멀티 워커 배포의 SMART launch state 공유 문제는 `SYNEX_REDIS_URL`만 설정하면 실제로 해결됩니다.

`backend/app/services/audit.py`의 감사 로그(analyses/events)는 여전히 SQLite 전용이라 이 Redis 전환의 대상이 아닙니다 — 감사 로그는 순서·기간별 조회가 필요한 영속 기록이라 launch state(수 분 내 소모되는 1회성 토큰)와 저장 요구사항이 달라서, 멀티 워커 환경에서 쓰려면 Redis가 아니라 Postgres 같은 실제 공유 RDB로의 마이그레이션이 필요합니다 — 이번 범위 밖입니다.

## 인증/RBAC/감사

`AUTH_MODE=demo`(기본, 고정된 데모 신원 — role은 `clinician`) 또는 `AUTH_MODE=oidc`. 자세한 내용과 남은 과제는 `docs/SECURITY.md` 참고.

### RBAC 역할 (실제 코드 기준, `backend/app/services/auth.py`)

- **`clinician_readonly`**: 진짜 읽기 전용입니다 — 환자/분석/노트/주문/감사 로그 조회만 가능하고, 노트 작성·서명·처방/검사 주문·경고 검토(`alert:review`)는 전부 403입니다. OIDC 모드에서 role claim이 없거나 인식 못 하는 값일 때의 최소권한 기본값이기도 합니다.
- **`clinician`**: `clinician_readonly`가 할 수 있는 모든 것 + 노트 작성/서명 + vitals/진단 입력 + 처방/검사 주문 + 경고 검토/AI 피드백. 데모 모드의 기본 신원이 이 역할입니다.
- **`pharmacist`**: 환자/분석/주문 읽기+쓰기 + 경고 검토. 노트 접근 권한은 없습니다(SOAP 문서 작성 주체가 아님).
- **`admin`**: `NEVER_GRANTED`(`patient:edit`/`prescription:auto_modify`/`rule:edit`) 제외 전체 권한.

> 과거 이 문서(2026-09 점검 결과, 아래)는 "`clinician_readonly`가 쓰기 권한을 갖는 것은 버그가 아니라 의도된 설계"라고 적었으나, 실제로는 **버그였고 이후 라운드에서 수정되었습니다** — `clinician_readonly`로 노트 서명이나 처방 주문이 가능했던 것은 RBAC이 이름과 다르게 동작하는 실질적 결함이었습니다. 아래 2026-09 섹션의 해당 항목은 이제 사실이 아니므로 그렇게 읽지 마십시오(원문은 그 시점의 판단 기록으로 남겨둡니다).

### AUTH_MODE=oidc: Bearer 토큰 vs 세션 쿠키

`get_current_user()`(`backend/app/services/auth.py`)는 두 가지 자격 증명을 받습니다:

1. `Authorization: Bearer <token>` — JWKS로 서명 검증. 스크립트/서버 간 클라이언트가 쓰는 경로입니다.
2. `synex_auth_session` HttpOnly 쿠키 — 브라우저 SPA가 쓰는 경로입니다. `POST /auth/session`이 이미 확보한 bearer 토큰을 **한 번만** 검증하고, 그 결과(`user_id`, `role`)를 서버 쪽 세션 저장소(`_AuthSessionStore`, SQLite 또는 `SYNEX_REDIS_URL` 설정 시 Redis)에 저장한 뒤 불투명한 세션 id를 쿠키로 내려줍니다. 이후 요청은 `credentials:'include'`만 있으면 자동으로 인증됩니다 — 브라우저는 토큰을 localStorage/sessionStorage/URL/React state 어디에도 저장하지 않습니다(저장할 토큰 자체가 없습니다).

**이 `synex_auth_session`은 SMART의 `synex_session`과 완전히 다른, 별도의 쿠키/세션입니다** — `synex_session`은 "이 브라우저가 보고 있는 SMART 환자 컨텍스트 + FHIR access token"이고, `synex_auth_session`은 "이 브라우저를 사용하는 임상의가 누구고 어떤 role인지"입니다. 두 세션은 절대 섞이지 않습니다.

`POST /auth/session`은 OIDC Authorization Code 리다이렉트 플로우 자체(실제 IdP에 로그인해 처음 토큰을 발급받는 과정)는 구현하지 않습니다 — 그 부분은 이 환경에서 검증 불가능한 기존 한계(`verify_oidc_token()`의 모듈 docstring 참고)와 동일합니다. 이 엔드포인트는 "이미 확보한 토큰을 세션으로 교환하는" 그 다음 단계만 제공합니다.

## Clinical Workspace (Encounter 중심 임상 기록)

`EMR_MODE=demo`에서는 Encounter/SOAP Note/Vital Signs/구조화 Diagnosis/Medication Order/Lab Order/Timeline/Clinical Summary/Unified Results가 전부 실제로 동작합니다(`backend/app/services/repositories.py`, `main.py`의 `/encounters/...`, `/patients/{id}/...` 엔드포인트들). 서명된 노트는 amendment로만 수정 가능하고, Medication Order 생성은 `Idempotency-Key` 헤더로 HTTP 레벨 재시도 중복도 막습니다(같은 키+다른 payload는 409), Diagnosis 생성은 `code_system+code`(코드 없으면 정규화된 display name) 기준으로 활성 진단 중복을 서버에서 막습니다.

**FHIR integration is currently read-focused. External EMR write-back is not enabled.** `EMR_MODE=fhir`에서는 위 Clinical Workspace 쓰기 엔드포인트들이 전부 `501 Not Implemented`를 반환합니다 — `FHIRAdapter.mutate()`가 의도적으로 `NotImplementedError`를 던지기 때문입니다(`BaseEMRAdapter.mutate()`의 docstring 참고). 즉 이 앱이 실제 병원 FHIR 서버에 `MedicationRequest`/`Condition`/`Encounter` POST 같은 쓰기 요청을 보내는 경로는 존재하지 않으며, 추가할 계획도 이번 범위에 없습니다. FHIR 모드의 읽기(Patient/Condition/MedicationStatement/AllergyIntolerance/Observation/Encounter/DiagnosticReport/ImagingStudy GET, `$everything` 번들)만 실제로 연결되어 있습니다.

## 2026-09 부족 사항 점검 결과

`지금 현재 emr에 대해 부족한 부분이 어디야?`에 대한 답으로 나온 항목들을 이 환경에서 실제로 고칠 수 있는 만큼 처리했습니다. 두 차례에 걸쳐 진행했습니다.

**1차**
- **처리함**: 키/몸무게 Observation 매핑, `terminology_mapper.py`의 데모 환자 실사용 약물 커버리지(6개 누락 발견 후 추가), `GET /patients` 501이 `/catalog`까지 함께 실패시키던 문제, FHIR 모드에서 환자 목록 대신 보여줄 수동 ID 조회 UI, SMART launch state의 in-memory → SQLite 영속화.

**2차 (위 1차 결과에 대한 후속 질문 "이것들은 해결할 수 있는거지? 해결해줘"에 대한 답)**
- **처리함**: Encounter/DiagnosticReport/ImagingStudy를 `Patient.encounters`/`diagnostic_reports`/`imaging_studies`로 실제 매핑(이전 docstring은 "fetch 헬퍼 포함"이라고 썼지만 실제로는 그런 헬퍼도, 대응 스키마 필드도 존재하지 않았던 과장된 설명이었음 — 이번에 코드와 설명을 일치시킴). SMART launch state에 `SYNEX_REDIS_URL` 기반 실제 Redis 백엔드 추가 — 로컬 `redis-server`를 직접 띄우고 두 개의 독립된 스토어 인스턴스(별도 워커 프로세스 시뮬레이션)로 상태 공유·1회성 소모·TTL 만료를 모두 실증 테스트함(mock 아님). 즉 "멀티 워커에서 launch state 공유 안 됨" 항목은 실제로 해결됨.
- **당시 "의도적으로 그대로 둔 항목"으로 기록했던 RBAC 세분화는 이후 실제로 버그로 재확인되어 수정되었습니다.** 이 시점에는 `clinician_readonly`가 노트 서명/처방 주문까지 가능한 것을 "readonly는 EMR 데이터를 쓰지 않는다는 뜻일 뿐 AI 경고 검토는 감사 추적이라 예외"라는 논리로 의도된 설계라 판단했으나, 실제로는 노트 작성·서명·Medication/Lab Order 생성까지 `clinician_readonly`로 가능했던 것은 "읽기 전용" role의 이름과 명백히 모순되는 결함이었습니다. 위 "RBAC 역할" 섹션이 현재 실제 동작입니다 — `clinician_readonly`는 이제 정말로 읽기만 가능합니다.
- **부분적으로만 가능함**: `terminology_mapper.py` 추가 확장. 이 환경은 RxNav 같은 실시간 용어 API를 호출할 수 없어(아래 참고) 정적 지식만으로 코드를 채워야 하는데, "검증된 코드만 넣는다"는 이 파일 자체의 원칙과 충돌하는 리스크(잘못된 RxCUI/ATC를 "매핑됨"으로 표시하는 것은 "매핑 안 됨"보다 더 나쁨)가 있어 이번에는 추가 확장을 보류했습니다. 실사용 약물 13종은 이미 1차에서 전부 커버되어 있습니다.
- **이 환경에서는 처리 불가**: 실제 병원 FHIR 서버·SMART 런처·OIDC IdP 대상 검증. 이 세션의 아웃바운드 네트워크는 조직 정책상 소수 도메인(anthropic/npm/pypi 등)으로만 허용되어 있어(egress 프록시가 그 외 모든 CONNECT를 403으로 거부) 공개 FHIR 테스트 서버나 RxNav 같은 실시간 용어 API조차 이 환경에서는 호출할 수 없습니다 — 직접 curl로 재확인했습니다. 실제 검증은 해당 인프라에 접근 가능한 환경에서 다시 수행해야 합니다. (참고: `redis-server`와 PyPI는 이 환경에 이미 있어서 Redis 관련 작업은 진짜로 검증 가능했습니다 — 네트워크 제약은 "임의의 외부 인터넷"에만 걸려 있습니다.)
- **실제로는 조치가 필요 없다고 판단한 항목**: 검사 최신성(freshness) 정책 테이블 — `LAB_MAX_AGE_DAYS`는 이 앱이 실제로 참조하는 검사 7종(Creatinine/eGFR/Potassium/INR/AST/ALT/Glucose)을 이미 전부 포함하고 있어 추가할 항목이 없습니다.

**3차 (Clinical Workspace 중복 처리/인증/세션 보안/SMART-FHIR 일관성 정리)**
- **처리함**: RBAC 세분화를 실제로 수행(위 2차의 "손대지 않겠다"는 판단을 재검토 후 버그로 확정, 위 "RBAC 역할" 섹션). Medication Order에 `Idempotency-Key` 헤더 기반 HTTP 레벨 멱등성 추가(별도 `IdempotencyStore`, 같은 키+다른 payload는 409). Diagnosis 생성에 code/display_name 기준 활성-진단 중복 방지 추가(resolved→새 active 재발은 허용). SMART 세션(SQLite) TTL을 `put()` 시점 opportunistic sweep에서 `context()`/`token_for()` 매 조회 시점 실제 만료 검사로 변경. `FHIR_AUTH_MODE=smart`를 fail-closed로 전환(세션/토큰 없음 또는 issuer 불일치 시 무인증 fallback 대신 401) + issuer 검증 추가. `AUTH_MODE=oidc`용 브라우저 세션 쿠키 경로(`POST /auth/session` + `synex_auth_session`) 추가 — SMART 세션과 별개. Clinical Summary의 medication 문장 source id가 Timeline의 source_id와 다른 스킴(`order:RX-<id>` vs `RX-<id>`)이던 버그 수정, "관련 기록 보기"가 실제로 해당 Timeline 항목을 찾아 하이라이트하도록 확인.

## 연동 전 체크리스트

외부 기관 연결 전에 다음을 실제로 확인해야 합니다(이 저장소는 코드/테스트만 제공하며 아래를 실제로 수행하지 않았습니다):

- [ ] 실제 기관 FHIR 서버를 대상으로 `FHIRAdapter` 재검증 (`test_fhir_adapter.py`는 가짜 서버만 사용)
- [ ] 실제 기관 OIDC/IdP를 대상으로 `AUTH_MODE=oidc` 재검증 (`test_auth.py`는 자체 서명 키만 사용, `POST /auth/session` 경로 포함)
- [ ] 실제 SMART App Launch 런처·인가서버 대상으로 `FHIR_AUTH_MODE=smart` 체인(launch → session → issuer 검증 → FHIR 요청) 재검증
- [ ] 읽기 전용 권한 범위로 기관 승인
- [ ] 전송·저장 암호화 (TLS는 애플리케이션 밖에서 구성 — `docs/SECURITY.md`)
- [ ] 데이터 보존 정책 (현재 감사 로그에 보존/삭제 정책 없음)
- [ ] **외부 FHIR 서버로의 쓰기(write-back)는 이 앱에 없으며 추가 계획도 없습니다** — `EMR_MODE=demo`의 Clinical Workspace(Encounter/Note/MedicationOrder/LabOrder 등)는 이 앱 자체의 데모 상태에만 쓰고, `EMR_MODE=fhir`에서는 같은 엔드포인트들이 501을 반환합니다(`FHIRAdapter.mutate()`, `NEVER_GRANTED` 참고).
- [ ] `IdempotencyStore`/`_AuthSessionStore`/`_SessionStore`는 모두 단일 프로세스 in-memory 또는 로컬 SQLite입니다(감사 로그와 동일한 프로토타입 범위) — 워커/레플리카를 2개 이상 띄우는 배포라면 `SYNEX_REDIS_URL`을 설정해 SMART launch/session state를 공유하십시오. `IdempotencyStore`(Medication Order Idempotency-Key)는 아직 Redis 백엔드가 없습니다 — 멀티 워커에서 그대로 쓰면 워커별로 멱등성 기록이 갈라집니다. 감사 로그는 이 설정과 무관하게 여전히 SQLite 전용이라 별도 검토가 필요합니다.
