# YMAS-GPT-6-Astra · SynexAgent

기존 v3 ONNX 모델을 실제로 실행하는 **가상 환자 기반 Clinical Copilot MVP**입니다. 환자를 선택하면 규칙·모델·검사 변화 분석을 보여주며, 약물을 가상으로 추가하여 점수와 경고의 전후 변화를 비교할 수 있습니다.

**데모 전용입니다. 실제 진단·처방 시스템이 아니며, 처방을 자동 확정하지 않습니다.** 화면의 백분율은 합성·규칙 라벨을 학습한 모델 점수이며 실제 부작용 발생 확률이 아닙니다. 제공된 약물 규칙도 임상 검증된 지식베이스로 간주하지 않습니다.

## 빠른 실행 — Windows PowerShell

Python 3.12, Node.js 22 이상이 필요합니다. 터미널은 다운로드한 프로젝트 폴더에서 여십시오. Git이 없으면 GitHub **Code → Download ZIP**으로 내려받아 압축을 푸십시오.

```powershell
git clone https://github.com/hundol047/YMAS-GPT-6-Astra.git
cd YMAS-GPT-6-Astra
python --version
node --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

브라우저에서 **http://127.0.0.1:8000**을 여십시오. API 설명은 **http://127.0.0.1:8000/docs**입니다. 처음 설치할 때는 인터넷 연결이 필요합니다. 설치와 빌드 후에는 모델 추론에 외부 API 키가 필요하지 않습니다.

가상환경 활성화 없이 `.venv\Scripts\python.exe`를 직접 호출하므로 PowerShell 실행 정책을 바꿀 필요가 없습니다.

### Python / npm 오류

- `py` 명령이 없으면 우선 `python --version`을 사용하십시오. 두 명령 모두 없으면 [Python 공식 다운로드](https://www.python.org/downloads/)에서 Python 3.12를 설치하고 `Add python.exe to PATH`를 선택한 뒤 PowerShell을 새로 여십시오.
- `python`이 Microsoft Store만 열면 설치된 Python의 경로를 확인하거나 Windows 앱 실행 별칭을 확인하십시오.
- `npm`이 없으면 [Node.js 공식 사이트](https://nodejs.org/)에서 설치하고 터미널을 다시 여십시오.
- `package.json`을 찾지 못하면 **`cd frontend` 이후** `npm ci`를 실행하십시오. 프로젝트 최상위는 Python+React 통합 폴더이며 npm 프로젝트가 아닙니다.
- 프론트엔드 빌드 없이 API만 시작하면 `/` 화면은 제공되지 않습니다. 위 명령 순서대로 빌드 후 서버를 실행하십시오.
- 8000 포트가 사용 중이면 실행 중인 이전 SynexAgent를 종료하거나 `--port 8001`로 바꾸십시오. 빌드된 화면은 같은 서버를 사용하므로 추가 설정이 필요 없습니다.

## macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd frontend
npm ci
npm run build
cd ..
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

## 화면을 수정하면서 실행

첫 번째 터미널에서 위 Python 서버를 실행합니다. 두 번째 터미널에서는:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1
```

http://127.0.0.1:5173 에서 실행합니다. `/api` 요청은 Vite가 8000의 FastAPI로 전달합니다. 운영 빌드는 FastAPI가 정적 파일과 API를 함께 제공합니다.

## 포함 기능

- 검색 가능한 5명 가상 환자와 환자별 실제 ONNX 점수
- 환자·약물·상호작용·알레르기·질환·검사·모델·요약의 8단계 결과 재생
- 위험 병용, 약물군 중복, 동일 성분 후보, 기저질환, 알레르기, 다약제 및 중증 이력 경고
- 경고 상세 근거·규칙 위치·모델 입력 연결 표시
- 원처방을 보존하는 약물 추가 시뮬레이션과 `%p` 전후 비교
- 의료진 확인·무시·보류, 사유 입력, 서버 SQLite 검토 이력
- 검사 수치 추적 그래프 및 참고범위 검토 경고
- 불완전 데이터 표시, FHIR R4 개념에 따른 데모 Bundle 출력
- CPU 기본 실행과 선택적 TensorRT/CUDA provider 탐색·CPU fallback

| 데모 환자 | 검증 목적 |
|---|---|
| 김하늘 / SYN-001 | 위험 신호 없는 기준 사례 |
| 박도윤 / SYN-002 | Warfarin + Aspirin 병용, INR 변화 |
| 이서준 / SYN-003 | 기존 규칙의 상호작용 없이 약물 10종 |
| 정수아 / SYN-004 | 현재 상호작용 없이 중증 약물 반응 이력 |
| 최지우 / SYN-005 | 기저질환·주의 경고 누적·신기능 추적 |

권장 데모 순서: 박도윤 선택 → 경고 상세 → 사유를 적고 확인 → 검토 이력 확인 → 김하늘 선택 → 새 약물 추가 비교 → 다른 환자의 독립 위험요인 확인.

## API

| Method | 경로 | 동작 |
|---|---|---|
| GET | `/health` | 모델 이름·shape·해시·실행 provider |
| GET | `/patients`, `/patients/{id}` | 가상 환자 목록·상세 |
| GET | `/catalog` | 제공 약물 카탈로그 |
| POST | `/predict` | 7개 정규화 feature의 실제 ONNX 추론 |
| POST | `/medication-check` | 내부 Patient 스키마의 가상 데이터 분석 |
| POST | `/agent/analyze` | `{"patient_id":"SYN-002"}` 분석 및 기록 |
| GET | `/agent/stream/{id}` | 서버 분석의 완료 단계와 결과 SSE |
| POST | `/prescription/simulate` | patient_id·drug_id의 가상 약물 추가 |
| POST | `/reviews` | 분석에 속한 경고 검토 및 사유 저장 |
| GET | `/audit/{id}` | 최근 200건 서버 기록 |
| GET | `/patients/{id}/fhir` | 개념 증명용 FHIR Bundle |

## 테스트

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

프론트엔드 DOM 통합 테스트는 실제 FastAPI와 ONNX를 로컬 stdio bridge로 호출합니다. 별도 웹 서버는 필요하지 않습니다.

```powershell
.\.venv\Scripts\python.exe scripts\test_integration.py
```

자세한 결과와 제한은 [검증 보고서](docs/VALIDATION.md)를 확인하십시오.

## Docker

Docker Engine 또는 Docker Desktop이 설치된 환경에서:

```bash
docker compose up --build
```

http://127.0.0.1:8000 을 여십시오. 웹 화면과 API를 한 컨테이너로 제공하며 로그는 `synex-audit` 볼륨에 보존합니다. Docker 설정은 제공되지만 이번 환경에서 Docker 실행은 검증하지 않았습니다.

## 재사용 자산과 문서

- 원본 `risk_model_deep_v3.onnx`는 바이트 단위로 보존했습니다.
- 7개 feature 순서, 학습 규칙의 danger/caution 계산, 0.34/0.67/1.0 중증도 점수, `/24` 리필 정규화를 재사용했습니다.
- `research/original/`에 제공된 모델·학습 및 생성 코드·CSV를 보존했습니다. 해당 README의 과거 성능 표현은 원문 기록이며 이 MVP의 임상 검증 주장이 아닙니다.
- GitHub YMAS 커밋 `584b086bc4573810a5833373696535d8393ec80a`의 7-feature 추론 계약 및 React 구성도 비교했습니다. 과거 프론트엔드의 이력 없음 `0.1`과 복용일수 `/730` 대리값은 복사하지 않았습니다.
- [아키텍처](docs/ARCHITECTURE.md), [모델 카드](docs/MODEL_CARD.md), [EMR 연동](docs/EMR_INTEGRATION.md), [Jetson 배포](docs/JETSON_DEPLOYMENT.md), [자산 분석](docs/ASSET_AUDIT.md)

## 현재 범위

인증·사용자 권한·실제 EMR 연결·임상 검증·처방 실행은 포함하지 않습니다. 실제 환자 데이터를 입력하지 마십시오. LLM 서비스 대신 근거를 연결하는 결정론적 요약 에이전트를 사용합니다. 위험 요인 목록은 SHAP 값이나 인과 기여율이 아닙니다. 릴스 링크에 접근할 수 없어 문서의 UI 요구사항에 따라 재해석했습니다. Python+ONNX 서버를 사용하므로 정적 GitHub Pages만으로 실행할 수 없습니다.

## 3D Anatomical Risk Viewer (추가)

기존 분석 요약 옆 **3D 해부학** 탭에서 위험 신호 관련 장기를 확인할 수 있습니다. 실제 환자 영상 또는 병변 위치가 아닌 참고 해부학적 관련성 표시입니다.

[실행 방법·구현 구조·API·dependency·한계](docs/ANATOMY.md) · [검증 결과](docs/ANATOMY_VALIDATION.md) · [변경 파일 목록](docs/ANATOMY_CHANGES.json)

완성된 frontend/dist가 포함되어 있으므로 Python dependency를 설치한 뒤 프로젝트 루트에서 `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`으로 실행할 수 있습니다.
