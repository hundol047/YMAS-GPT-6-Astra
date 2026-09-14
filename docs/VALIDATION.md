# 검증 결과

검증일: 2026-09-11. Python 3.12 / Linux x86_64 / ONNX Runtime CPU. 모델은 원본 v3이며 재학습하지 않았습니다.

| 항목 | 결과 |
|---|---|
| 제공 ONNX v1/v2/v3 checker 및 shape 검사 | 통과 |
| 기본 v3 모델 SHA256 원본 대조 | 동일 |
| 백엔드 17개 자동 테스트 | 통과 |
| 원본 dataset 매칭 테스트 5개 | 통과 |
| React DOM 통합 테스트 3개 | 통과 |
| 프론트엔드 production build | 통과 |
| FastAPI 시작 및 /health | 통과 |
| Vite 개발 서버 시작 | 127.0.0.1 바인딩에서 통과 |
| production /, favicon 및 API 경로 | TestClient로 확인 |
| 실제 브라우저 시각·모바일 검증 | 미완료 — 내부 preview URL에 ERR_BLOCKED_BY_CLIENT |
| 실제 Jetson·TensorRT·Docker 실행 | 미실시 |
| 실환자 임상 검증·성능 보정 | 미실시 |

## 필수 사례의 실제 출력

| 사례 | 원본 규칙 danger/caution | 실제 모델 점수 |
|---|---|---|
| 위험요인 없는 SYN-001 | 0 / 0 | 0.0000209% |
| 상호작용 SYN-002 | 1 / 0 | 95.2914% |
| 상호작용 없이 다약제 10종 SYN-003 | 0 / 0 | 99.9882% |
| 중증 약물 반응 SYN-004 | 0 / 0 | 99.6504% |
| 기저질환·주의 누적 SYN-005 | 0 / 4 | 99.8243% |

별도 자동 사례에서 주의 3건을 정확히 구성하여 drug_conflict=.6 및 고위험을 확인했습니다. 동일 입력 30회 결과가 같음을 확인했습니다. 시뮬레이션에서 모델 feature를 다시 계산하고 전후 차이를 `%p`로 반환하며 원처방을 보존함을 확인했습니다.

## DOM 통합 테스트의 의미

React를 jsdom에 렌더링하고 실제 FastAPI TestClient와 원본 ONNX를 **stdio 테스트 bridge**로 호출합니다. 위험 점수나 환자 분석 응답을 하드코딩하지 않습니다.

검증한 흐름:
1. 박도윤 분석 → 상호작용 상세 → 사유를 포함한 확인 → 검토 이력 표시 → 김하늘 전환 → 와파린 가상 추가 → 진료기록에서 원처방 보존 확인.
2. 환자 검색 → 결과 없음 → 빠른 환자 전환 → 이전 분석이 섞이지 않는지 확인 → 다시 분석.
3. 연결 실패 표시 → 다시 시도 → 분석 복구.

이 테스트는 CSS 시각 품질, 실제 브라우저의 SSE 구현, HTTP 네트워크, 작은 화면 배치 또는 그래프 렌더링 검증을 대체하지 않습니다. 브라우저 검증 차단을 통과로 기록하지 않습니다.

## 재실행

프로젝트 루트:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\python.exe scripts\test_integration.py
cd frontend
npm run build
```

학습 원본 테스트는 research/original 디렉터리에서 `python test_build_dataset.py`로 실행합니다. 원본 모듈의 상대 경로를 보존했으므로 해당 작업 디렉터리가 필요합니다.
