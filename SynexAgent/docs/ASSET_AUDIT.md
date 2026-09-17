# 기존 자산 분석 및 변경

| 자산 | 확인 결과 | 처리 |
|---|---|---|
| YMAS-main ZIP | 디렉터리와 27-byte README만 존재 | 과거 프로젝트 부재로 해석하지 않음 |
| YMAS Deep Learning ZIP | 24개 항목, 약 33.4MB | 원본 전체 보존 |
| ONNX v1 | features [batch,5] | 참고 보존 |
| ONNX v2/v3 | features [batch,7], risk_probability [batch] | v3 서비스 기본 모델 |
| PyTorch .pt | state-dict tensor key와 저장 구조 확인 | 임의 pickle 실행 없이 원본 보존 |
| train_deep v1/v2/v3 | feature·층·오버샘플링·검증 방식 분석 | 서비스에서 재학습하지 않음 |
| CSV v1/v2/v3 | 116262 / 75421 / 86116행, 라벨·컬럼 직접 확인 | 연구 원본 보존 |
| rules.json | interactions 224, comorbid 10, allergy 8 | 근거 경로와 원본 해시 표시 |
| drug_catalog.json | 제공 카탈로그 ID·그룹·검색 성분 확인 | 약물 선택·원본 규칙 매칭 재사용 |
| dataset 생성 코드 | 중증도 .34/.67/1, 평균 DISPENSES/24 | API 서버 feature 계산에 적용 |
| 기존 테스트 | 약물 문자열 매칭·ID·중증도 검증 | 원본 보존, 새 API 회귀 테스트 추가 |
| YMAS commit 584b086 | GitHub 연결 후 7-feature 서버·React 자료 확인 | API 계약 참고, UI/서비스는 요구사항대로 신규 작성 |

## 수정/회피한 문제

- 과거 프론트엔드의 부작용 이력 없음 `0.1`을 없애고 실제 이력 없음은 `0.0`으로 전달합니다.
- 과거의 이력 있음 `0.6` 대신 원본 중증도 정의를 사용합니다.
- 과거 복용일수 `/730` proxy 대신 원본 `DISPENSES/24`를 사용하며 누락을 표시합니다.
- 약물·검사 정보를 화면에서 계산해 `/predict`로 전달하던 구조를 서버 feature pipeline으로 옮겼습니다.
- 원본 서버의 현재 작업 디렉터리 의존 모델 경로를 `__file__` 기반 절대 경로로 바꿨습니다.
- 원본 서버의 광범위 CORS 대신 로컬 개발 origin 기본값을 사용합니다.
- v3의 입력 차원·이름을 실행 시 확인하여 5-feature 모델과 섞이지 않도록 했습니다.
- 새로운 다약제·중증 반응 카드를 표시하되 drug_conflict에 중복 가산하지 않습니다.
- 임의 SHAP 막대·임상 확률·가짜 분석 시간을 표시하지 않습니다.

원본 코드 자체를 소급 수정한 것은 아니며 `research/original`은 제공 자료 그대로입니다. 원본 생성기의 복합제 alias 손실 가능성, 영어 질환/한국어 규칙 일치 한계, 과거 처방 포함 문제는 모델 카드에 남겼습니다. 원본 모델과 라벨 정의를 몰래 바꾸지 않았습니다.
