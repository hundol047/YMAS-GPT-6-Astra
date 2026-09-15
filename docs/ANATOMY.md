# 3D Anatomical Risk Viewer — 구현 및 실행 안내

기존 SynexAgent React/Vite + FastAPI/ONNX 프로젝트에 추가한 기능입니다. 새 프로젝트를 만들지 않았으며 기존 환자 목록, SSE 분석, ONNX 점수, 경고 상세, 의료진 검토, audit log, 처방 시뮬레이션, 검사 차트와 진료 기록을 유지합니다.

## 실행 방법

ZIP을 압축 해제한 뒤 **SynexAgent 폴더**에서 실행하십시오. Python 3.12 및 Node.js 20.19+ 또는 호환되는 최신 LTS가 필요합니다. 이 작업에서는 Python 3.12 / Node 24에서 검증했습니다.

### Windows PowerShell — 포함된 완성 빌드 실행

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

브라우저에서 http://127.0.0.1:8000 을 엽니다. 프런트엔드 완성 빌드(frontend/dist)를 포함하므로 이 방식은 npm 작업 없이 실행할 수 있습니다. Python이 설치되지 않았다면 먼저 설치하고 터미널을 다시 여십시오.

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### 개발 및 재빌드

백엔드를 실행한 상태에서 별도 터미널을 엽니다.

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

http://127.0.0.1:5173 에서 개발 화면을 봅니다. 배포용 파일을 갱신할 때는 frontend 폴더에서 `npm run build`를 실행하고 백엔드를 재시작합니다. 기존 Docker 실행 안내는 루트 README에 있습니다.

## 사용 흐름

1. 환자를 선택하고 분석 완료를 기다립니다.
2. **3D 해부학** 탭을 엽니다. SYN-005의 신장과 전신 관련 신호를 확인할 수 있습니다.
3. 장기 목록 또는 3D 메시를 클릭하면 장기가 강조되고 카메라와 오른쪽 근거 패널이 이동합니다. 더블클릭도 지원합니다.
4. 눈 버튼으로 각 장기를 숨기거나 표시합니다. 목록에서 장기를 다시 선택하면 숨김이 해제됩니다.
5. 드래그로 회전, 휠/핀치로 확대·축소, 우클릭 드래그로 이동합니다. RESET/FRONT/BACK/LEFT/RIGHT/TOP 버튼도 제공합니다.
6. Axial/Coronal/Sagittal을 선택하고 단면 위치를 이동합니다. **실제 메시 절단**을 체크하면 보이는 메시가 해당 평면에서 잘립니다.
7. 관련 경고 보기를 누르면 기존 검토 모달이 열립니다. 모달의 **3D에서 보기**로 다시 이동할 수 있습니다.
8. 분석 요약에서 처방 시뮬레이션을 실행한 뒤 3D 탭에서 현재/가상 처방 결과를 비교합니다. 실제 처방은 바뀌지 않습니다.

## 구현 구조

- `frontend/src/components/anatomy/AnatomyWorkspace.jsx`: 환자·시뮬레이션 상태, 선택 상태, 패널 구성
- `AnatomyScene.jsx`: WebGL, OrbitControls, 카메라 이동, 절단 평면, 방향 표시, 오류 대체 화면
- `AnatomyModel.jsx`: 독립 장기 메시, 투명 외곽, 척추, 위험 색상·맥동·마커
- `geometry.js`: 직접 만든 간략 해부학 표면 생성
- `AnatomyAssets.jsx`: 선택적 useGLTF 로더, 정규화, 로딩/오류 대체
- `AnatomySlicePanel.jsx`: 같은 메시의 삼각형과 절단 평면 교차를 계산하는 SVG 단면
- `AnatomyControls.jsx`, `AnatomyOrganList.jsx`, `AnatomyRiskPanel.jsx`, `AnatomyLegend.jsx`: 독립 UI
- `frontend/src/data/anatomyMap.js`: 모델 좌표, 장기 이름, 레이어 그룹, 심각도 표기
- `backend/app/services/anatomy.py`: 명시적 규칙을 통한 해부학적 관련성 연결
- `backend/data/anatomy_mapping.json`: 영어·한국어 키워드 설정

## 데이터와 API

`GET /patients/{patient_id}/anatomy`는 다음 필드를 반환합니다.

- `patient_id`, `mapping_version`
- `targets`: 장기 수준 관련 신호
- `systemic`: 전신 관련 신호
- `imaging_available: false`
- `model_score_localized: false`

각 신호에는 `organ_id`, `severity`, `title`, `reason`, `alert_id`, `sources`, `localization`, `confidence`가 있습니다. 검사 근거의 값·단위·날짜, 질환 이름, 관련 약물 ID를 보존합니다.

동일한 anatomy 객체가 기존 ClinicalAgent 결과에 포함되어 `/agent/analyze`, SSE 결과, `/prescription/simulate`의 before/after에서도 일관되게 제공됩니다. 프런트엔드는 별도의 중복 키워드 매핑 없이 현재 분석의 anatomy를 사용합니다. 시뮬레이션 경고 상세에는 after의 analysis_id를 전달해 검토 기록의 소속을 보존합니다.

| 입력 근거 | 연결 |
|---|---|
| renal, kidney, eGFR, Creatinine, CKD, 신기능·신부전 | 양측 신장 |
| hepatic, liver, AST, ALT, 간기능 | 간 |
| cardiac, QT, arrhythmia, 심부전 | 심장 |
| respiratory, pulmonary, COPD, 천식 | 양측 폐 |
| gastric, GI, 위장·소화기 | 위 참고 영역 |
| neurologic, CNS, 중추신경 | 뇌 |
| 알레르기, 중증 반응 이력, 다약제, 중복약물, 누적 경고 | 전신 |
| 출혈 관련 약물 상호작용 및 Warfarin + Aspirin | 전신 |
| 명시적 장기 근거가 없는 나머지 경고 | 전신 |

ASCII 키워드에는 단어 경계를 적용해 AST가 last, GI가 digoxin에 오인 매칭되는 것을 방지합니다. 여러 장기에 근거가 있으면 복수 연결합니다. 신호의 위험·주의 수준은 기존 경고에서 가져오며 기저질환 기록 자체는 정보 수준입니다. 약물 이름만으로 특정 장기의 병변을 추정하지 않습니다. 전체 모델 점수를 장기별 확률로 분해하지 않습니다.

## dependency

- 추가: `three 0.180.0`, `@react-three/fiber 9.4.0`, `@react-three/drei 10.7.6`
- 추가: `@fontsource-variable/noto-sans-kr` — 한글이 없는 환경에서도 표시되도록 로컬 폰트 포함, SIL OFL
- React 및 React DOM은 19 계열을 유지하며 `19.2.4`로 함께 고정했습니다. 설치 당시 최신 버전 자동 선택에 따른 R3F peer 범위 충돌을 피하고 lockfile로 재현합니다.
- 백엔드 dependency는 추가하지 않았습니다.

## Patient Digital Twin 업그레이드 (2단계)

- **성별 특화 인체**: `patient.sex`가 `male`/`female`일 때만 해당 체형 프로파일(`anatomyMap.js`의 `BODY_PROFILES`)을 사용합니다. 그 외 값이거나 없으면 "Sex-specific anatomy unavailable" 안내를 표시하고 중립(unspecified) 프로파일로 대체합니다 — 임의 추정하지 않습니다. 몸통은 흉곽·허리·골반 단면 반경이 다른 lathe(회전체) 실루엣이라 남녀가 실제로 다른 형태로 보입니다. GLB로 교체하려면 `frontend/public/models/anatomy/README.md`의 `VITE_ANATOMY_MODEL_URL_MALE`/`_FEMALE`를 참고하십시오.
- **레이어 패널**: Body/Skeleton/장기(15종, 아래 표 참고) 각각에 Eye(표시·숨김), Isolate(단독 보기), 체크박스(다중 선택)를 제공합니다. SHOW ALL / HIDE ALL / SHOW SELECTED / RESET VIEW 버튼은 모두 3D visibility만 바꾸며 환자 데이터나 장기 객체를 삭제하지 않습니다.
- **BODY OPACITY 슬라이더 + 프리셋**(Skin/Transparent/X-Ray/Organs Only): 신체 셸의 투명도와 body/skeleton 표시 여부를 함께 제어합니다.
- **PATIENT CONDITIONS 패널**: `patient.conditions`를 그대로 나열하고(없으면 "No documented condition data"), 고정 테이블(`CONDITION_ICD10`)의 ICD-10 코드를 병기합니다. 클릭하면 백엔드가 이미 계산한 `anatomy.targets`의 조건-근거 연결(고정 키워드 매핑, LLM 실시간 추론 아님)을 따라 해당 장기로 포커스하고 body opacity를 낮춥니다. 연결된 장기가 없으면 전신으로 대체합니다.
- **장기 상세 탭**(Anatomy/Clinical Data/Imaging/Labs/Medication/Warnings): Clinical Data 탭은 기존 `AnatomyRiskPanel`을 그대로 재사용합니다. Labs/Medication은 고정 테이블(`ORGAN_LABS`)과 백엔드가 이미 반환한 `sources`만 사용하며, 화면에는 환자에게 실제로 존재하는 값만 표시합니다.
- **범례**: Cyan(임상 연관)/Amber(검토 권고)/Red(고위험)/Purple(영상 소견) 4단계. Purple은 실제 segmentation이 있을 때만 쓰도록 예약되어 있으며, 이 데모에는 segmentation 데이터가 없으므로 현재 어떤 장기도 Purple로 표시되지 않습니다.
- **IMAGING STUDIES (데모)**: 환자 실제 영상이 없으므로 기본값은 "No patient imaging available."이며, `OPEN DEMO IMAGING`을 눌러야 3-분할 Axial/Coronal/Sagittal 데모 패널이 열립니다. 이 패널은 실제 DICOM/NIfTI를 읽지 않고, 3D와 동일한 참고 메시 단면(`geometry.crossSectionPaths`)을 사용합니다. 한 화면 클릭 시 나머지 두 화면의 교차선(crosshair)이 함께 이동하고, 슬라이더를 움직이면 위쪽 3D 모델의 절단면도 즉시 반영됩니다(기존 단일 단면 절단 메커니즘 재사용). SEGMENTATION 섹션은 실제 segmentation 데이터가 없다는 사실을 그대로 표시하며 가짜 병변(Tumor 등)을 생성하지 않습니다.
- **REFERENCE ANATOMY vs PATIENT-DERIVED IMAGING**: 이 프로젝트에는 후자가 없습니다. 데모 영상 패널·3D 모델 모두 "REFERENCE" 라벨을 유지합니다.

추가된 장기: 췌장(pancreas), 비장(spleen), 방광(bladder), 소장(smallIntestine), 대장(largeIntestine). `backend/data/anatomy_mapping.json`에 대응 키워드를 추가했습니다.

## 현재 범위와 확장 지점

현재 모델은 직접 만든 **procedural/basic anatomy placeholder**입니다. 장기 메시를 감싸는 반투명 인체 실루엣(머리·목·몸통·골반·팔·다리)도 같은 방식의 절차적 참고 형상이며, 장기 분리·선택·위험 연결·실제 절단 기능은 동작하지만 레퍼런스 영상과 같은 정밀 해부학 GLB 또는 CT 재구성은 아닙니다. 실제 CT/MRI/DICOM, 종양·출혈 위치, 환자 영상·segmentation은 포함하지 않습니다. 단면의 상대 좌표는 mm가 아니며, 절단면 표면 캡을 생성하지 않으므로 잘린 메시 내부는 열린 형태입니다.

정밀 GLB 교체 위치와 필수 mesh 이름은 `frontend/public/models/anatomy/README.md`를 참고하십시오. 모델 파일이 없거나 형식이 맞지 않으면 기본 모델로 대체합니다. 제3자 장기 모델은 번들에 포함하지 않았습니다. 폰트 라이선스는 `docs/licenses/Noto-Sans-KR-OFL.txt`에 포함했습니다.

향후 실제 환자 영상은 별도 영상 제공자와 DICOM 좌표 변환, segmentation provenance, 측정 검증을 구현한 뒤 연결해야 합니다. 현재 참고 모델 정규화 코드를 환자별 segmentation 좌표 처리에 재사용하면 안 됩니다.

클리핑 구현 참고: https://threejs.org/docs/#api/en/materials/Material
