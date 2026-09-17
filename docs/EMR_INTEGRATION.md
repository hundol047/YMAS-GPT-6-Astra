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
| `SYNEX_SMART_TRUSTED_ISSUER` (단수) | `FHIR_AUTH_MODE=smart`일 때 세션의 `iss`와 비교할 신뢰 issuer. 생략 시 `FHIR_BASE_URL`을 그대로 사용. **아래 `SYNEX_SMART_TRUSTED_ISSUERS`(복수)와는 다른 변수입니다** — 이건 세션 발급 *이후* FHIR 요청 단계의 신뢰 검사이고, 복수형은 `/smart/launch` 진입 *시점*의 SSRF 방지용 allowlist입니다 |
| `SYNEX_SMART_TRUSTED_ISSUERS` (복수, 콤마 구분) | `/smart/launch?iss=...`가 discovery 요청을 보내기 전 허용하는 issuer 목록. 미설정 시(데모 기본값) allowlist 검사는 건너뛰지만 https-only/사설 IP 차단 등 나머지 검증은 항상 적용됨 — 아래 "SMART 발급자 검증" 참고 |
| `SYNEX_SMART_ALLOW_INSECURE_LOCALHOST` | `true`로 설정하면 `http://localhost`/`127.0.0.1` issuer를 예외적으로 허용(로컬 개발용 가짜 IdP 전용). 운영 환경에서는 절대 `true`로 두지 않음 |
| `SMART_LAUNCH_STATE_TTL_SECONDS` | launch state(PKCE `state`)가 유효한 시간(초). 기본 600. 매 조회 시점에 실제로 만료 검사함 — 아래 참고 |
| `CDS_AUTH_MODE` | `none`(기본, CDS Hooks 표준 상호운용성 우선) 또는 `bearer`(운영 권장) — 아래 "CDS Hooks 인증" 참고 |

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

### CDS Hooks 인증 (`CDS_AUTH_MODE`)

`GET /cds-services`(discovery)는 **모든 모드에서 항상 공개**입니다 — CDS Hooks 스펙상 클라이언트가 인증 이전에 서비스 목록을 조회할 수 있어야 하기 때문입니다. 인증이 걸리는 건 실행 엔드포인트(`POST /cds-services/synex-medication-safety`)뿐이고, 이는 앱 전역 `AUTH_MODE`와 독립적인 `CDS_AUTH_MODE`로 별도 제어됩니다(`AUTH_MODE=demo`로 나머지 앱을 데모 모드로 띄운 채 CDS Hooks 실행 엔드포인트만 진짜 bearer 토큰을 요구하는 배포가 가능합니다):

- `CDS_AUTH_MODE=none`(기본): 인증 검사 없음 — 대부분의 CDS Hooks 레퍼런스 구현 기본값과 동일, 데모/상호운용성 테스트에 적합.
- `CDS_AUTH_MODE=bearer`(운영 권장): `Authorization: Bearer <token>`을 `AUTH_MODE=oidc`와 **동일한** JWKS 기반 `verify_oidc_token()`으로 검증(별도 static-secret 방식이 아니라 기존 검증기 재사용)한 뒤, 그 신원이 `cds:invoke` 권한을 갖고 있는지 확인합니다(`backend/app/services/auth.py`의 `require_cds_invoke()`). 토큰 없음/무효 토큰은 401, `cds:invoke` 없는 역할은 403. 현재 `clinician_readonly`/`clinician`/`pharmacist`/`admin` 전부 `cds:invoke`를 보유합니다(별도 system-account 개념을 새로 만들지 않고 기존 역할에 최소 권한만 추가).

`GET /smart/launch?iss=...&launch=...`, `GET /smart/callback`이 PKCE 기반 SMART App Launch를 구현합니다 (`backend/app/services/smart_launch.py`). 가짜 인가서버를 대상으로 PKCE/redirect 구성만 테스트했습니다 — **실제 EMR 런처나 실제 FHIR 인가서버와의 라운드트립은 검증하지 않았습니다.**

### SMART 발급자 검증 (SSRF 방지)

`iss` 쿼리 파라미터는 전적으로 호출자가 제어하는 값입니다 — 과거에는 이 값을 검증 없이 그대로 `.well-known/smart-configuration`에 대한 outbound HTTP 요청에 사용했고, 이는 교과서적인 SSRF 취약점이었습니다(공격자가 `iss=http://169.254.169.254/`나 내부망 주소를 넘기면 이 서버가 그대로 요청을 보냄). `validate_smart_issuer()`(`smart_launch.py`)가 이제 discovery 요청 **이전에** 반드시 실행되며, 다음을 순서대로 검사합니다:

1. **인증정보 임베딩 거부**: `https://user:pass@...` 형태 거부.
2. **로컬호스트 예외**: `SYNEX_SMART_ALLOW_INSECURE_LOCALHOST=true`이고 호스트가 `localhost`/`127.0.0.1`/`::1`이면 즉시 허용(로컬 개발 전용, 운영 기본값 아님).
3. **https-only**: 위 예외가 아니면 scheme이 `https`가 아닌 모든 요청 거부 (`http://`, `file://`, `ftp://` 등).
4. **Allowlist**: `SYNEX_SMART_TRUSTED_ISSUERS`가 설정되어 있으면 정규화된 `iss`가 그 목록에 있어야 함(트레일링 슬래시/쿼리·프래그먼트는 정규화 후 비교). 미설정 시 이 단계는 건너뜀(데모 기본값) — 그래도 5번은 항상 적용됨.
5. **사설/내부 IP 차단**: 호스트 자체가 리터럴 IP면 바로, 아니면 DNS로 해석한 IP들에 대해 `ipaddress`로 private/loopback/link-local/reserved/multicast 여부를 검사해 거부(`169.254.169.254`, `10.x`, `192.168.x`, `127.0.0.1` 등). DNS 해석이 실패하면(존재하지 않는 호스트 등) 이 단계는 통과시킵니다 — 뒤따르는 실제 HTTP 요청이 어차피 연결에 실패하기 때문입니다. **정직하게 밝히자면**: 이 검사와 실제 접속 사이에는 이론적으로 DNS 리바인딩 TOCTOU 창이 남아 있습니다(해석된 IP를 그대로 고정해 접속하는 커스텀 transport까지는 구현하지 않았음) — "합리적으로 가능한 범위"의 방어이지 완벽한 차단은 아닙니다.

허용/차단 예시는 `backend/tests/test_cds_hooks.py`의 `test_validate_smart_issuer_*`/`test_untrusted_or_private_issuer_never_makes_a_discovery_request`에서 실제로 검증합니다(사설 IP·localhost·allowlist 밖 도메인·`file://`/`ftp://` 전부 거부, allowlist 안 https만 통과, 거부되는 경우 discovery 요청 자체가 발생하지 않음을 mock transport로 증명).

### SMART Discovery: authorization_endpoint와 token_endpoint를 독립적으로 사용

과거 `exchange_code()`는 `authorization_endpoint.replace('/authorize', '/token')` 같은 문자열 치환으로 token endpoint를 "추측"했습니다 — SMART 스펙에 없는 패턴이고, 실제 EHR의 두 endpoint가 그 URL 모양을 공유하지 않으면(예: `https://ehr.example/oauth/a` + `https://auth.example/token-exchange`) 조용히 깨집니다. 지금은 `discover_smart_configuration()`이 `.well-known/smart-configuration` 응답에서 `authorization_endpoint`와 `token_endpoint`를 **각각 독립적으로** 읽고, 둘 중 하나라도 없으면 즉시 실패합니다(추측 fallback 없음). `token_endpoint`는 `/smart/launch` 시점에 발견되어 launch state와 함께 **저장**되고, `/smart/callback`은 저장된 값을 그대로 사용합니다 — 콜백 시점에 다시 discovery를 하거나 문자열로 재구성하지 않습니다. `backend/tests/test_cds_hooks.py::test_smart_exchange_code_via_fake_authorization_server`가 두 endpoint를 완전히 다른 도메인/경로로 설정해 이를 증명합니다.

launch state(state→code_verifier+token_endpoint 매핑) 저장소는 두 가지입니다:
- `SYNEX_REDIS_URL` 미설정(기본): 로컬 SQLite(`backend/data/smart_launch.sqlite3`, `SYNEX_SMART_LAUNCH_PATH`로 변경 가능). **TTL은 매 조회(`pop()`) 시점에 실제로 검사됩니다** — `put()` 시점의 opportunistic sweep에만 의존하지 않으므로, 만료된 state는 물리적으로 아직 테이블에 남아 있어도 절대 반환되지 않고 토큰 교환에 쓰일 수 없습니다(`SMART_LAUNCH_STATE_TTL_SECONDS`로 조절, 기본 600초). 단일 인스턴스 배포 기준 프로세스 재시작에는 살아남지만, 워커/레플리카가 여러 개면 서로 파일을 공유하지 못해 여전히 안 됩니다.
- `SYNEX_REDIS_URL` 설정 시: `_RedisLaunchStore`. 같은 Redis를 보는 모든 워커/레플리카가 launch state를 공유하며, 항목은 `SMART_LAUNCH_STATE_TTL_SECONDS` 후 자동 만료됩니다(별도 정리 작업 불필요). **실제 로컬 `redis-server`를 띄워 두 개의 독립된 `_RedisLaunchStore` 인스턴스(별도 워커 프로세스를 시뮬레이션)로 검증했습니다** — 목(mock)이 아닙니다 (`backend/tests/test_smart_launch_redis.py`; redis-server가 없는 환경에서는 깨끗하게 skip됩니다). 즉 멀티 워커 배포의 SMART launch state 공유 문제는 `SYNEX_REDIS_URL`만 설정하면 실제로 해결됩니다.

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

`EMR_MODE=demo`에서는 Encounter/SOAP Note/Vital Signs/구조화 Diagnosis/Medication Order/Lab Order/Timeline/Clinical Summary/Unified Results가 전부 실제로 동작합니다(`backend/app/services/repositories.py`, `main.py`의 `/encounters/...`, `/patients/{id}/...` 엔드포인트들). 서명된 노트는 amendment로만 수정 가능하고, Diagnosis 생성은 `code_system+code`(코드 없으면 정규화된 display name) 기준으로 활성 진단 중복을 서버에서 막습니다.

**Problem List vs Encounter Diagnosis**: `Patient.problem_list`(환자 단위의 활성 진단 목록, 예: "Atrial fibrillation / active")와 개별 `ClinicalEncounter.diagnosis_ids`(그 진료에서 다룬 진단들)는 서로 다른 개념입니다. 같은 활성 진단을 새 Encounter가 다시 기록하면 `problem_list`에 중복 항목을 만들지 않고 기존 Diagnosis를 재사용하지만, **그 새 Encounter의 `diagnosis_ids`에는 반드시 연결됩니다** — 과거에는 재사용 분기에서 이 연결을 빼먹어, Encounter B가 기존 진단을 다시 기록해도 `diagnosis_ids`가 비어 있는 채로 남는 버그가 있었습니다(수정됨, `DiagnosisRepository.create()`). 같은 Encounter에 같은 진단을 두 번 기록해도 `diagnosis_ids`에 id가 중복 추가되지 않도록 멱등하게 처리합니다. resolved 상태였던 과거 진단 + 새로 발생한 active 진단(재발) 조합은 여전히 중복으로 보지 않고 둘 다 허용합니다. `backend/tests/test_clinical_workspace.py::test_diagnosis_recorded_on_new_encounter_links_without_duplicating_problem_list`가 이 전체를 검증합니다.

**Medication Order Idempotency는 동시성 안전(concurrency-safe)합니다** — 단순 순차 재시도 방어를 넘어, 같은 `Idempotency-Key`를 가진 요청 여러 개가 진짜로 동시에 도착해도 정확히 하나만 실제 처방 생성 작업을 수행합니다. 서버 측 보장이 핵심이며 프론트엔드의 버튼 비활성화는 부차적 방어일 뿐입니다 — 아래 "Idempotency 저장소" 참고.

**FHIR integration is currently read-focused. External EMR write-back is not enabled.** `EMR_MODE=fhir`에서는 위 Clinical Workspace 쓰기 엔드포인트들이 전부 `501 Not Implemented`를 반환합니다 — `FHIRAdapter.mutate()`가 의도적으로 `NotImplementedError`를 던지기 때문입니다(`BaseEMRAdapter.mutate()`의 docstring 참고). 즉 이 앱이 실제 병원 FHIR 서버에 `MedicationRequest`/`Condition`/`Encounter` POST 같은 쓰기 요청을 보내는 경로는 존재하지 않으며, 추가할 계획도 이번 범위에 없습니다. FHIR 모드의 읽기(Patient/Condition/MedicationStatement/AllergyIntolerance/Observation/Encounter/DiagnosticReport/ImagingStudy GET, `$everything` 번들)만 실제로 연결되어 있습니다.

### Idempotency 저장소 (동시성 안전)

`backend/app/services/idempotency.py`는 이제 단순 `dict[key] -> 마지막 응답` 캐시가 아닙니다. 실제 레이스 컨디션(요청 A와 B가 동시에 같은 키를 `get()`했을 때 둘 다 "없음"을 보고 각자 새 처방을 만드는 경우)을 SQL 유일성 제약(`PRIMARY KEY(scope, key)`, `SYNEX_REDIS_URL` 설정 시 Redis `SET NX`)으로 원천 차단합니다: 동시에 도착한 요청 중 오직 하나의 `INSERT`만 성공하고, 나머지는 그 승자의 실제 처방 완료를 기다렸다가(`wait_for_completion`에 해당하는 폴링) 같은 응답을 돌려받습니다 — 각자 처방을 만드는 경로 자체가 존재하지 않습니다. 같은 키에 다른 payload가 오면 409. 오류로 끝난 시도는 클레임을 반납해 같은 키로 재시도할 수 있게 합니다(성공한 응답만 캐시됨). `SYNEX_REDIS_URL` 설정 시 `_RedisIdempotencyStore`로 전환되어 여러 워커/레플리카가 같은 클레임 상태를 공유합니다 — 이전에는 이 저장소만 Redis 백엔드가 없었지만 이번에 추가되었습니다. `backend/tests/test_clinical_workspace.py`의 `test_medication_order_idempotency_key_is_concurrency_safe`(진짜 `ThreadPoolExecutor` 동시 요청 8개, 응답 전부 동일 order_id + Medication/Order/Timeline 각각 정확히 1건), `test_medication_order_idempotency_key_concurrent_conflicting_payload_is_409`, `test_idempotency_store_lookup_is_not_process_local`(별도 인스턴스가 같은 SQLite 파일을 통해 클레임을 본다는 것을 증명)로 실제 검증됩니다.

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

**4차 (동시성/보안/SMART 표준 준수 최종 정리 — 새 기능 추가가 아니라 기존 워크플로 마감)**
- **처리함**: Medication Order Idempotency를 진짜 동시성 안전(SQL 유일성 제약 기반)으로 재구현 — 이전 3차의 `Idempotency-Key`는 순차 재시도만 안전했고 진짜 동시 요청 두 개가 동시에 "없음"을 본 뒤 각자 처방을 만드는 레이스는 막지 못했음(수정됨, "Idempotency 저장소" 섹션). SMART launch state TTL을 `put()` opportunistic sweep에서 `pop()` 매 조회 시점 실제 만료 검사로 변경(`_SessionStore`가 이미 갖고 있던 패턴을 `_LaunchStore`에도 적용). `discover_authorize_endpoint()`의 `.replace('/authorize','/token')` 문자열 치환을 제거하고 `authorization_endpoint`/`token_endpoint`를 discovery 문서에서 독립적으로 읽는 `discover_smart_configuration()`으로 교체, `token_endpoint`를 launch state에 저장해 콜백이 그대로 재사용하도록 함. `/smart/launch?iss=...`에 대한 SSRF 방지(`validate_smart_issuer()`: https-only, 인증정보 임베딩 거부, `SYNEX_SMART_TRUSTED_ISSUERS` allowlist, 사설/내부 IP 차단, discovery 요청 이전 검증)를 추가. Encounter가 기존 활성 Diagnosis를 재사용할 때 그 Encounter의 `diagnosis_ids`에 실제로 연결되지 않던 버그 수정. CDS Hooks 실행 엔드포인트에 `CDS_AUTH_MODE` 기반 인증(discovery는 계속 공개) 추가.
- **이 환경에서는 처리 불가(이전과 동일한 이유)**: 실제 병원 SMART 런처·OIDC IdP 대상 검증은 여전히 이 환경의 네트워크 제약 때문에 불가능합니다 — 이번 라운드의 SSRF 방지 로직도 mock transport와 `ipaddress`/`socket.getaddrinfo` 단위 테스트로만 검증했습니다.

## 연동 전 체크리스트

외부 기관 연결 전에 다음을 실제로 확인해야 합니다(이 저장소는 코드/테스트만 제공하며 아래를 실제로 수행하지 않았습니다):

- [ ] 실제 기관 FHIR 서버를 대상으로 `FHIRAdapter` 재검증 (`test_fhir_adapter.py`는 가짜 서버만 사용)
- [ ] 실제 기관 OIDC/IdP를 대상으로 `AUTH_MODE=oidc` 재검증 (`test_auth.py`는 자체 서명 키만 사용, `POST /auth/session` 경로 포함)
- [ ] 실제 SMART App Launch 런처·인가서버 대상으로 `FHIR_AUTH_MODE=smart` 체인(launch → session → issuer 검증 → FHIR 요청) 재검증
- [ ] 읽기 전용 권한 범위로 기관 승인
- [ ] 전송·저장 암호화 (TLS는 애플리케이션 밖에서 구성 — `docs/SECURITY.md`)
- [ ] 데이터 보존 정책 (현재 감사 로그에 보존/삭제 정책 없음)
- [ ] **외부 FHIR 서버로의 쓰기(write-back)는 이 앱에 없으며 추가 계획도 없습니다** — `EMR_MODE=demo`의 Clinical Workspace(Encounter/Note/MedicationOrder/LabOrder 등)는 이 앱 자체의 데모 상태에만 쓰고, `EMR_MODE=fhir`에서는 같은 엔드포인트들이 501을 반환합니다(`FHIRAdapter.mutate()`, `NEVER_GRANTED` 참고).
- [ ] `IdempotencyStore`/`_AuthSessionStore`/`_SessionStore`/`_LaunchStore`는 기본적으로 로컬 SQLite입니다(감사 로그와 동일한 프로토타입 범위) — 워커/레플리카를 2개 이상 띄우는 배포라면 `SYNEX_REDIS_URL`을 설정해 전부(SMART launch/session state, OIDC 인증 세션, **Medication Order Idempotency-Key도 포함** — 이전에는 Redis 백엔드가 없었지만 이번에 추가됨) 공유하십시오. 감사 로그는 이 설정과 무관하게 여전히 SQLite 전용이라 별도 검토가 필요합니다.
