# EMR Adapter 경계

`backend/app/services/emr_adapter.py`는 이제 `BaseEMRAdapter` 인터페이스와 두 구현체로 나뉩니다.

- **DemoAdapter** (기존, 변경 없음): `backend/data/patients.json`만 읽습니다.
- **FHIRAdapter** (신규): 실제 FHIR R4 서버와 SMART on FHIR client_credentials OAuth2로 통신합니다. **이 개발 환경에서 접근 가능한 실제 병원 FHIR 서버가 없어 실제 서버 대상으로는 검증하지 못했습니다.** 가짜 FHIR 서버(`httpx.MockTransport`)를 대상으로 요청/응답 파싱 정확성만 단위 테스트했습니다 (`backend/tests/test_fhir_adapter.py`). 실제 기관 서버에 연결하기 전 그 서버 자체를 대상으로 별도 검증이 필요합니다.

`EMR_MODE=demo`(기본) 또는 `EMR_MODE=fhir`로 전환합니다. FHIR 모드 환경변수:

| 변수 | 용도 |
|---|---|
| `FHIR_BASE_URL` | FHIR 서버 base URL (필수) |
| `FHIR_CLIENT_ID` / `FHIR_CLIENT_SECRET` | SMART client_credentials (없으면 무인증 요청) |
| `FHIR_SCOPE` | 기본 `system/*.read` |
| `FHIR_TOKEN_URL` | `.well-known/smart-configuration` discovery 실패 시 수동 지정 |
| `FHIR_REDIRECT_URI` | SMART App Launch용 (`GET /smart/launch`, `GET /smart/callback`) |

비밀값은 환경변수에서만 읽으며 Git이나 Docker 이미지에 넣지 않습니다.

| 내부 자료 | FHIR R4 리소스 | 구현 상태 |
|---|---|---|
| 기본 정보 | Patient | 구현 (name/gender/birthDate → age) |
| 활성 약물 | MedicationStatement / MedicationRequest | 구현 |
| 기저질환 | Condition | 구현 (텍스트만; 코드 매핑은 `terminology_mapper.py`가 별도 수행) |
| 알레르기·반응 | AllergyIntolerance | 구현 |
| 검사 이력 | Observation | 구현 |
| 진료/영상 | Encounter, DiagnosticReport, ImagingStudy | fetch 헬퍼 없음 — 내부 Patient 스키마에 대응 필드가 아직 없어 향후 확장 지점으로 남김 |
| 환자 목록 조회 | 전체 roster 검색 | **미구현.** `FHIRAdapter.list()`는 `NotImplementedError`를 던집니다 — 기관 승인된 전체 검색 스코프가 보통 없고, 실제 사용 경로는 SMART App Launch가 넘겨주는 단일 환자 id이기 때문입니다. |

누락된 필드는 `Patient.missing`에 그대로 기록됩니다 (예: `"condition history (none returned)"`) — 임의로 정상으로 보정하지 않습니다.

`GET /patients/{id}/fhir`(DemoAdapter)는 여전히 **데모 projection**입니다. FHIR 모드에서는 서버가 이미 제공하는 `Patient/{id}/$everything` 번들을 그대로 전달합니다(재가공하지 않음).

## 표준 코드 정규화

`backend/app/services/terminology_mapper.py`가 RxNorm/ATC(약물)·LOINC(검사)·ICD-10/SNOMED CT(진단) 매핑을 담당합니다. 고정 참조 테이블 방식이며, 매핑이 없으면 `mapping_status:'unmapped'`로 명시합니다 — 임의 추정하지 않습니다. `GET /patients/{id}/terminology`로 확인할 수 있습니다. 178개 약물 카탈로그 중 일부(안정적으로 확인 가능한 성분급 RxCUI/ATC만)만 매핑했습니다; 확장은 검증된 코드를 테이블에 추가하는 방식으로만 합니다.

## CDS Hooks / SMART App Launch

`GET /cds-services`, `POST /cds-services/synex-medication-safety`(`medication-prescribe` 훅)가 구현되어 있습니다 (`backend/app/services/cds_hooks.py`). 자체 데모 환자를 대상으로 스펙 형태를 테스트했습니다(`backend/tests/test_cds_hooks.py`) — **실제 EMR의 CDS Hooks 클라이언트에서 카드가 어떻게 렌더링되는지는 검증하지 않았습니다.**

`GET /smart/launch?iss=...&launch=...`, `GET /smart/callback`이 PKCE 기반 SMART App Launch를 구현합니다 (`backend/app/services/smart_launch.py`). 가짜 인가서버를 대상으로 PKCE/redirect 구성만 테스트했습니다 — **실제 EMR 런처나 실제 FHIR 인가서버와의 라운드트립은 검증하지 않았습니다.**

## 인증/RBAC/감사

`AUTH_MODE=demo`(기본, 기존 "DR" 동작 유지) 또는 `AUTH_MODE=oidc`(실제 JWT/JWKS 검증). 자세한 내용과 남은 과제는 `docs/SECURITY.md` 참고.

## 연동 전 체크리스트

외부 기관 연결 전에 다음을 실제로 확인해야 합니다(이 저장소는 코드/테스트만 제공하며 아래를 실제로 수행하지 않았습니다):

- [ ] 실제 기관 FHIR 서버를 대상으로 `FHIRAdapter` 재검증 (`test_fhir_adapter.py`는 가짜 서버만 사용)
- [ ] 실제 기관 OIDC/IdP를 대상으로 `AUTH_MODE=oidc` 재검증 (`test_auth.py`는 자체 서명 키만 사용)
- [ ] 읽기 전용 권한 범위로 기관 승인
- [ ] 전송·저장 암호화 (TLS는 애플리케이션 밖에서 구성 — `docs/SECURITY.md`)
- [ ] 데이터 보존 정책 (현재 감사 로그에 보존/삭제 정책 없음)
- [ ] 처방 쓰기 기능은 이 MVP에 없으며 추가 계획도 없습니다 (`NEVER_GRANTED` 참고)
