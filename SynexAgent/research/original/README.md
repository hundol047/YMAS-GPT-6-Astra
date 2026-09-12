# SynexAgent — 딥러닝 버전 (RiskDeepMLP)

[YMAS(SynexAgent)](https://github.com/hundol047/YMAS) 저장소
`backend/train_with_oversampling.py`(v7, 입력5 → 은닉8 → 출력1, 파라미터
57개인 1층짜리 얕은 신경망)를 다층 구조로 확장한 딥러닝 버전을 담은
별도 저장소입니다.

> **배포 상태**: v3(`risk_model_deep_v3.onnx`)가 YMAS 저장소의
> `backend/infer_server.py` / `frontend/src/App.jsx`에 실제로 연결되어
> 서빙 중입니다 (YMAS 저장소 커밋 `584b086` 참고). v7은 더 이상 기본
> 서빙 모델이 아니고, 필요시 되돌릴 수 있도록 `backend/risk_model.onnx`로
> 남아 있습니다.

## 구성

```
.
├── data/
│   ├── risk_training_data.csv     v1용, 특성 5개 (YMAS backend/real_dataset.json 통합, 116,262행)
│   ├── risk_training_data_v2.csv  v2용, 특성 7개 · 기존 라벨 (build_dataset_v2.py, 75,421행)
│   └── risk_training_data_v3.csv  v3용, 특성 7개 · 확장 라벨 (build_dataset_v3.py, 86,116행)
├── drug_catalog.json / rules.json  YMAS 저장소 backend/에서 복사한 참조 데이터 (build_dataset_v2/v3.py가 씀)
├── export_csv.py                   v1: real_dataset.json -> CSV 변환 (참고/재현용)
├── build_dataset_v2.py             v2: Synthea 원본 CSV -> 특성 7개 CSV 변환 (라벨은 기존과 동일)
├── build_dataset_v3.py             v3: build_dataset_v2.py + 라벨 정의 확장
├── train_deep.py / risk_model_deep.pt / .onnx        v1 (특성 5개, 4개 은닉층)
├── train_deep_v2.py / risk_model_deep_v2.pt / .onnx  v2 (특성 7개, 5개 은닉층, 기존 라벨)
└── train_deep_v3.py / risk_model_deep_v3.pt / .onnx  v3 (특성 7개, 5개 은닉층, 확장 라벨) -- 최신
```

## v7과의 차이

### 1. 모델 구조 — 1층 → 4층

```
v7:   입력(5) -> Linear(8) -> Tanh -> Linear(1) -> Sigmoid                [57 파라미터]
딥러닝: 입력(5) -> [Linear(64)-BN-ReLU-Dropout]
                -> [Linear(32)-BN-ReLU-Dropout]
                -> [Linear(16)-BN-ReLU-Dropout]
                -> [Linear(8)-BN-ReLU-Dropout]
                -> Linear(1) -> Sigmoid                                    [~3,200 파라미터]
```

각 층에 BatchNorm(학습 안정화)과 Dropout(과적합 방지)을 추가했고, 학습률도
60에폭마다 절반으로 줄어드는 스케줄러를 적용했습니다.

### 2. 오버샘플링 지터 버그 수정 (중요)

v7을 실제로 뜯어보다가 발견한 버그입니다. 클래스 불균형(고위험 9.6%)을
보정하려고 "위험" 샘플을 복제할 때, v7은 **5개 특성 전부**에 작은 무작위
잡음(지터, ±0.03)을 더했습니다.

문제는 `adverse_history`(과거 부작용 이력)가 이 데이터셋 116,262명 **전원
0.0**이라는 점입니다 — 실제로는 전혀 변하지 않는 상수입니다. 그런데 지터가
여기에도 섞이면서, "위험으로 복제된 가짜 샘플"만 유일하게 0보다 살짝 큰
값(0~0.03)을 갖게 됐고, 모델이 "`adverse_history`가 0보다 조금이라도 크면
무조건 위험"이라는, **임상적으로 아무 의미 없는 지름길**을 학습해버렸습니다.

**실제 영향**: 프론트엔드(`App.jsx`)는 부작용 이력이 없는 환자에게도
`adverse_history=0.1`을 보내는데(정확히 0.0을 보내는 경우가 없음), 이는
버그가 걸리는 구간이라 **다른 조건과 무관하게 거의 항상 "위험"으로
판정되고 있었습니다** (무작위 조합 200개 테스트 결과 200개 전부 위험 판정).
검증셋도 같은 이유로 이 문제를 전혀 못 잡아냈습니다(검증셋도 상수 0이라
지터 구간을 안 지나감) — 그래서 v7의 Precision 98.8%라는 수치 자체는
정직하지만, 그 좋은 수치 뒤에 이 결함이 가려져 있었습니다.

**이 버전에서 고친 방법**: 오버샘플링 지터를 실제로 값이 연속적인 3개 특성
(`drug_conflict`, `comorbidity_load`, `age_risk`)에만 적용하고, 이진/상수에
가까운 `allergy_flag`, `adverse_history`는 지터에서 제외했습니다.

## 여전히 남은 한계 (정직하게)

`adverse_history`는 지터 버그는 고쳤지만, 데이터 자체가 여전히 116,262명
전원 0.0이라 **이 특성에서 배울 신호 자체가 없습니다** (모델이 이 특성을
그냥 무시하게 됨 — 위험하게 오작동하진 않지만, 유용하지도 않은 상태).

근본적으로 고치려면 Synthea `allergies.csv`의 `SEVERITY1`/`SEVERITY2`
(MILD/MODERATE/SEVERE 같은 실제 중증도 값 — 이미 확인해봤고 실제로
채워져 있음)를 이용해 이 특성을 다시 계산해야 합니다. 다만 그러려면
Synthea를 다시 돌려야 합니다 (v7 학습에 쓴 원본 raw CSV는 디스크 절약을
위해 검증 후 삭제해둔 상태). 이번 버전은 "구조를 딥러닝으로 바꾸고,
데이터 재생성 없이 고칠 수 있는 확실한 버그(지터)만 먼저 고친" 중간
단계입니다.

## 실제로 검증한 결과

**검증셋 성능** (23,252명, 자연 발생 고위험 2,221명 — 오버샘플링 안 함):
Recall 100% / Precision 93.3% / F1 96.5% (v7: 100% / 98.8% / 99.4%)

v7보다 검증셋 Precision은 낮습니다 — Dropout/BatchNorm으로 인한 정규화 효과로
결정 경계가 v7만큼 날카롭지 않기 때문입니다. 하지만 이 수치 비교만으로는
버그가 고쳐졌다는 게 안 드러납니다(검증셋 자체가 `adverse_history=0`
상수라 버그 구간을 안 지나가서 v7도 검증셋에선 문제없이 보였습니다).
**진짜 차이는 실제 서비스가 보내는 입력값으로 테스트했을 때 드러납니다:**

| 테스트 케이스 (약물충돌, 기저질환, 연령, 알레르기, **과거부작용=0.1**) | v6 | v7 | 딥러닝(버그 수정) |
|---|---|---|---|
| 저위험(다른 4개 특성 전부 낮음) | 99.1% | **100.0%** | **0.0%** |
| 중등도(주의 알림 1개 수준) | 100.0% | **100.0%** | **0.0%** |
| 고위험(위험 알림 1개) | 100.0% | 100.0% | 96.1% |
| 고위험(위험 알림 2개+) | 100.0% | 100.0% | 96.0% |

`adverse_history=0.1`은 프론트엔드가 "부작용 이력 없음"인 환자에게 실제로
보내는 값입니다. v6·v7은 이 값 하나 때문에 **아무 위험 요인이 없는 환자도
100% 위험으로 잘못 판정**했지만, 딥러닝 버전은 실제 위험 요인이 있을 때만
확률을 올립니다.

**결정론성**: 완전히 동일한 입력을 30회 반복 호출 → 30번 다 정확히 같은 값
(`0.9606945515...`, 소수점 10자리까지 동일). 드롭아웃은 `model.eval()`
모드(추론 시)에서는 자동으로 비활성화되므로, 학습 때와 달리 배포된
ONNX 추론은 v7과 마찬가지로 완전히 결정론적입니다.

## v2 — 특성을 5개 -> 7개로 확장 (그리고 여기서 배운 것)

"더 깊게, 더 정확하게" 만들어 달라는 요청에, 층만 더 쌓는 대신 실제로
Synthea를 다시 돌려서(`build_dataset_v2.py`) 특성을 늘렸습니다:

- `adverse_history` 재계산 — 이전엔 116,262명 전원 0.0인 죽은 특성이었는데,
  이번엔 `allergies.csv`의 실제 `SEVERITY1`/`SEVERITY2`(MILD/MODERATE/SEVERE)
  값을 써서 4.5%(75,421명 중 3,373명)가 실제 0이 아닌 값을 갖게 만들었습니다.
- `polypharmacy_load`(신규) — 매칭 약물 개수 정규화. 다약제 자체가
  임상적으로 알려진 독립 위험요인입니다.
- `therapy_duration_load`(신규) — `medications.csv`의 `DISPENSES`(리필
  횟수)로 장기 복용 정도를 정규화.
- 네트워크도 4층(64-32-16-8) -> 5층(128-64-32-16-8)으로 더 깊고 넓게.

`train_deep_v2.py` / `data/risk_training_data_v2.csv`(75,421행)가 결과물입니다.

### 검증 결과: 소폭 개선, 그리고 왜 그것뿐인지

| 버전 | 특성 수 | 은닉층 | Recall | Precision | F1 |
|---|---|---|---|---|---|
| v7 (YMAS 저장소) | 5 | 1 | 100% | 98.8% | 99.4% |
| 딥러닝 v1 (지터 버그만 수정) | 5 | 4 | 100% | 93.3% | 96.5% |
| **딥러닝 v2 (특성 확장)** | **7** | **5** | **100%** | **94.2%** | **97.0%** |

v1 -> v2로 Precision이 93.3% -> 94.2%로 올랐습니다. 다만 그 이유를
**순열 중요도(permutation importance)** 로 검증소보니, 왜 딱 이만큼만
올랐는지가 명확해졌습니다 — 검증셋에서 각 특성의 값을 무작위로
섞었을 때 F1이 얼마나 떨어지는지 측정한 결과:

| 특성 | F1 하락폭 |
|---|---|
| `drug_conflict` | **+86.0%p** |
| `comorbidity_load` | +1.2%p |
| `polypharmacy_load` | +0.35%p |
| `age_risk` | +0.0%p |
| `allergy_flag` | +0.0%p |
| `adverse_history` | +0.0%p |
| `therapy_duration_load` | +0.0%p |

**모델 판단의 86%가 여전히 `drug_conflict` 단 하나에서 나옵니다.**
`polypharmacy_load`는 라벨과의 단순 상관계수는 0.51로 꽤 높았는데도
(약을 많이 먹을수록 상호작용 규칙에 걸릴 확률도 같이 올라가는 게
당연하니까요), 정작 모델 판단에는 거의 기여를 못 합니다 — `drug_conflict`가
이미 그 정보를 대부분 포함하고 있어서 중복(redundant)이기 때문입니다.

**근본 원인**: `build_dataset_v2.py`의 라벨 자체가 여전히
`danger_count > 0`(즉 `drug_conflict`가 만들어지는 바로 그 규칙 판정)만으로
정의됩니다. `polypharmacy_load`나 `adverse_history`가 아무리 실제 값을
가져도, **라벨을 만드는 공식 자체가 그 특성들을 안 쓰기 때문에** 모델이
배울 수가 없습니다. 즉 이번 작업으로:
- 층은 확실히 더 깊어졌고 (4층 -> 5층)
- 특성도 확실히 더 풍부해졌고 (5개 -> 7개, 버그도 고쳐짐)
- 그런데 "정확도"는 라벨 정의 자체의 한계 때문에 아주 조금만 올랐습니다.

**진짜로 더 올리려면**: 라벨링 규칙(`build_dataset_v2.py`의 `label = 1 if
danger_count > 0 else 0`) 자체를 "다약제(예: 10종 이상) 단독으로도 주의
등급 부여" 같은 임상적 판단으로 확장해야 합니다. 이건 코드 문제가 아니라
"무엇을 위험으로 볼 것인가"를 정하는 제품/임상 판단이라, 제가 임의로
정하지 않고 다음 단계로 남겨뒀습니다.

### 배포 시 주의

v2는 입력이 5개 -> 7개로 바뀌어서, YMAS 저장소 `backend/infer_server.py`의
기존 Pydantic 스키마(정확히 5개 필드)와는 **더 이상 그대로 호환되지
않습니다**. 배포하려면 `infer_server.py`의 `RiskFeatures`에
`polypharmacy_load`, `therapy_duration_load`를 추가하고, `adverse_history`
계산 로직도 실제 알레르기 중증도 기반으로 바꿔야 합니다.

## v3 — 라벨 정의 자체를 확장 (진짜 정확도 개선)

v2 절의 결론("라벨이 특성을 안 쓰면 모델도 못 배운다")을 실제로 해결한
버전입니다. `build_dataset_v3.py`가 라벨 규칙에 임상적으로 근거 있는
3가지 조건을 추가했습니다 (기존 `danger_count > 0`에 OR로 추가):

- **과다다약제**: 매칭 약물 10종 이상 (노인약료 문헌에서 "hyperpolypharmacy"로
  구분하는 통상 기준. 개별 상호작용이 없어도 그 자체로 이상반응 위험 증가)
- **중증 약물 알레르기/불내성 이력**: `adverse_history`가 SEVERE(1.0)
- **주의 알림 누적**: "주의" 등급 알림이 3개 이상 겹침

새로 80,612명을 생성해서(`data/risk_training_data_v3.csv`, 86,116행)
라벨 재계산 → 고위험 비율이 9.7%(v2) -> **12.5%**로 늘었습니다 (그중
2,507명이 새 기준으로만 추가된 사람들 — 기존 규칙만으로는 안 걸렸을
사람들입니다).

### 결과: 진짜로 정확해졌습니다

| 버전 | 특성 | 라벨 기준 | Recall | Precision | F1 |
|---|---|---|---|---|---|
| 딥러닝 v1 | 5 | danger_count>0만 | 100% | 93.3% | 96.5% |
| 딥러닝 v2 | 7 | danger_count>0만 (특성만 확장) | 100% | 94.2% | 97.0% |
| **딥러닝 v3** | **7** | **danger_count>0 + 다약제 + 중증알레르기 + 주의누적** | **100%** | **100%** | **100%** |

v2에서 v3로 넘어오면서 순열 중요도도 완전히 달라졌습니다:

| 특성 | v2 기여도 | v3 기여도 |
|---|---|---|
| drug_conflict | 86.0%p | 51.4%p |
| polypharmacy_load | 0.35%p | **25.1%p** |
| adverse_history | 0.0%p | **12.4%p** |
| allergy_flag | 0.0%p | **10.6%p** |
| comorbidity_load | 1.2%p | 0.05%p |
| age_risk | 0.0%p | 0.05%p |
| therapy_duration_load | 0.0%p | 0.0%p |

이제 4개 특성이 골고루 기여합니다. 실제로 확인해보면, **약물 상호작용이
전혀 없어도** 다약제 단독(polypharmacy_load=1.0, 나머지 위험요인 0)만으로
99.99%, 중증 알레르기 단독만으로 99.7%가 나옵니다 — 모델이 진짜로 여러
독립적 위험 신호를 학습했다는 뜻입니다.

### 정직한 해설: 왜 100%가 나왔는가

100%는 "임상적으로 완벽한 AI"라서가 아니라, **라벨이 이제 입력 특성들의
결정론적 함수가 됐기 때문**입니다. 4가지 조건 중 3개(다약제, 중증알레르기,
그리고 상호작용 자체)가 사실상 입력 특성(`polypharmacy_load`,
`adverse_history`, `drug_conflict`)에서 거의 그대로 복원 가능한 값이라,
표현력 있는 신경망(5층, 오버샘플링으로 경계 부근까지 촘촘히 학습)이면
그 함수를 정확히 근사하는 게 어렵지 않습니다. 즉 v1/v2와 달리
**"라벨과 특성이 서로 잘 맞아떨어지도록 설계했기 때문에" 나온 성능**이지,
모델이 데이터에서 예상 못한 새로운 임상 패턴을 발견한 게 아닙니다.

다만 이건 실제 서비스 관점에서는 좋은 소식입니다 — v1/v2처럼 "모델이
결국 규칙 엔진 하나만 따라 하는" 문제 없이, **다약제·중증알레르기 같은
새 위험 신호도 이제 실제로 판정에 반영**됩니다. 다음 단계로 더
정확하게 만들려면, 라벨 기준 자체를 더 정교하게(예: 임계값을 10종이
아니라 나이·신장기능별로 다르게 주기 등) 다듬거나, 실제 임상 전문가
검토를 받는 것이 필요합니다.

### 버그 재검증

adverse_history=0.1 고정 + 나머지 랜덤 200개 조합 → 128/200 위험 판정
(v6/v7 버그였다면 200/200이 나와야 함 — 재발하지 않았습니다). 결정론성도
동일 입력 30회 반복으로 재확인했습니다.

### 100%가 이 분할에서만 우연히 나온 건 아닌지 — 5-fold 교차검증

100%라는 수치를 그대로 믿기엔 의심스러워서(`train_deep_v3.py`는 seed=0으로
고정된 단 하나의 80/20 분할만 씀), `crossval_v3.py`로 서로 겹치지 않는
5개의 다른 분할 각각에서 처음부터 다시 학습·검증해봤습니다:

```
fold 1/5  val_n=17224 (고위험 2145)  acc=100.00%  precision=100.00%  recall=100.00%  f1=100.00%
fold 2/5  val_n=17224 (고위험 2145)  acc=100.00%  precision=100.00%  recall=100.00%  f1=100.00%
fold 3/5  val_n=17223 (고위험 2145)  acc=100.00%  precision=100.00%  recall=100.00%  f1=100.00%
fold 4/5  val_n=17223 (고위험 2145)  acc=100.00%  precision=100.00%  recall=100.00%  f1=100.00%
fold 5/5  val_n=17222 (고위험 2144)  acc=100.00%  precision=100.00%  recall=100.00%  f1=100.00%

5-fold 평균: acc/precision/recall/f1 전부 100.00%, 표준편차 0.00%p
```

**5개 폴드 전부, 데이터의 어느 20%를 검증셋으로 떼어내도 100%가 나옵니다.**
즉 원래 보고한 100%는 운 좋은 분할 하나에서 나온 우연이 아니라, 위
"정직한 해설"에서 설명한 대로 **라벨이 입력 특성의 (거의) 결정론적
함수이기 때문에 구조적으로 재현되는 결과**입니다.

## 재현하는 방법

```bash
# v1 (특성 5개, data/risk_training_data.csv는 이미 포함되어 있음)
python3 export_csv.py --src ../YMAS/backend/real_dataset.json   # 다시 뽑을 때만
python3 train_deep.py       # risk_model_deep.pt / risk_model_deep.onnx 생성

# v2 (특성 7개 · 기존 라벨, data/risk_training_data_v2.csv도 이미 포함되어 있음)
python3 build_dataset_v2.py --csv-dir <Synthea csv 폴더>   # 다시 뽑을 때만
python3 train_deep_v2.py    # risk_model_deep_v2.pt / risk_model_deep_v2.onnx 생성

# v3 (특성 7개 · 확장 라벨, data/risk_training_data_v3.csv도 이미 포함되어 있음) -- 최신, 권장
python3 build_dataset_v3.py --csv-dir <Synthea csv 폴더>   # 다시 뽑을 때만
python3 train_deep_v3.py    # risk_model_deep_v3.pt / risk_model_deep_v3.onnx 생성
```

## 배포

- **`risk_model_deep.onnx`(v1)**: YMAS 저장소 `backend/infer_server.py`와
  입출력 스펙이 동일합니다 (`features`: [drug_conflict, comorbidity_load,
  age_risk, allergy_flag, adverse_history] 5개 → `risk_probability`).
  `MODEL_PATH`만 이 파일로 바꾸면 그대로 서빙할 수 있습니다.
- **`risk_model_deep_v2.onnx` / `risk_model_deep_v3.onnx`(권장)**: 입력이
  7개(`drug_conflict, comorbidity_load, age_risk, allergy_flag,
  adverse_history, polypharmacy_load, therapy_duration_load`)로 늘어서
  기존 `infer_server.py`의 Pydantic 스키마(`RiskFeatures`, 5개 필드)로는
  그대로 안 됩니다. 배포하려면 그 스키마에 두 필드를 추가하고, 요청을
  만드는 쪽(프론트엔드 등)에서도 `polypharmacy_load`(약물 개수/10),
  `therapy_duration_load`(리필횟수/24 정도)를 같이 계산해서 보내야 합니다.
