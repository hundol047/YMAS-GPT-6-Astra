# EMR Adapter 경계

`backend/app/services/emr_adapter.py`의 `DemoAdapter.list/get`은 내부 `Patient` 스키마로 복사본을 제공합니다. 현재 `backend/data/patients.json`만 읽으며 실제 병원 시스템, 인증 정보, 환자 개인정보와 연결하지 않습니다.

| 내부 자료 | 향후 FHIR R4 리소스 | 필요한 검증 |
|---|---|---|
| 기본 정보 | Patient | 식별자·성별·생년월일·기준시점 |
| 활성 약물 | MedicationStatement / MedicationRequest | 성분코드·활성상태·투여량·경로·기간 |
| 기저질환 | Condition | 표준 코드와 제공 규칙의 조건 매핑 |
| 알레르기·반응 | AllergyIntolerance | 약물 범주·중증도·기록 상태 |
| 검사 이력 | Observation | LOINC·단위·참고범위·측정시점 |

`GET /patients/{id}/fhir`는 리소스 관계를 보여주는 **데모 projection**입니다. FHIR 인증, 프로파일 validator 통과, 실제 EHR read/write를 주장하지 않습니다. 실제 FHIR importer는 포함하지 않았습니다.

연동 시 기관별 adapter가 검증한 값을 내부 스키마로 변환해야 합니다. 식별자·알레르기·활성 처방이 불완전하면 임의 정상으로 보정하지 말고 missing 정보로 전달하십시오. 약물 문자열만으로 성분/복합제/소아제형을 확정하지 마십시오. 서버 내부 feature engineering 경계를 유지하여 브라우저 값과 학습 feature가 어긋나는 문제를 방지합니다.

외부 기관 연결 전에 읽기 전용 권한, 기관 승인, 인증/RBAC, 전송·저장 암호화, 감사 이력과 데이터 보존을 설계해야 합니다. 처방 쓰기 기능은 이 MVP에 없습니다.
