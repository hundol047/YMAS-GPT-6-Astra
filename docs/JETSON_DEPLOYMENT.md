# Jetson Orin 배포 경로

## 새로 추가된 도구 (AGX Orin 확정 이후)

- `scripts/verify_jetson_agx_gpu.py`: 명세된 감지 명령(`/proc/device-tree/model`, `nv_tegra_release`, `nvidia-l4t-core`, CUDA/cuDNN/TensorRT 패키지, Docker)을 그대로 실행하고, 실제 ONNX 모델로 추론까지 수행한 뒤 `TensorrtExecutionProvider`/`CUDAExecutionProvider`가 `available_providers` **와** `session_providers` 양쪽에 모두 있고 추론이 성공했을 때만 "GPU ACCELERATION VERIFIED"를 출력합니다. 이 저장소의 개발 컨테이너는 x86_64라 항상 `hardware_is_agx_orin: false` + CPU SAFE MODE로 나옵니다 — 실제 장치에서 실행해야 의미 있는 값이 나옵니다.
- `config/jetson_agx_orin_profiles.json`: JetPack/L4T/CUDA/cuDNN/TensorRT/Docker 베이스 이미지 조합별 배포 프로파일. 이번 작업에서는 `verified:true`인 프로파일을 하나도 채우지 않았습니다 — 실제 장치에서 `verify_jetson_agx_gpu.py`를 실행한 결과로만 채워야 합니다.
- `scripts/deploy_jetson_agx.sh`: 감지 → 프로파일 매칭(미검증 조합이면 무조건 CPU Safe Mode) → (가능하면) Docker 빌드 → 서버 기동 → `/health` 확인 → provider 검증 → 상태 출력까지 한 번에 수행합니다. 이 개발 컨테이너에서 실행하면 CPU Safe Mode 경로가 끝까지 성공하는 것을 확인했습니다; GPU 빌드 경로는 실제 AGX Orin이 아니면 도달하지 않습니다.
- `scripts/benchmark_jetson.py`: warmup/short/sustained 3단계로 실제 지연시간(avg/p50/p95/min/max)과 처리량을 측정합니다. 이 호스트에는 CUDA/TensorRT가 없으므로 해당 provider는 `available:false`로만 표시되고 숫자를 채우지 않습니다 — 가짜 벤치마크 수치를 생성하지 않습니다. `tegrastats`/`nvpmodel`은 실제 Jetson에서만 값이 채워집니다.

## 현재 검증 범위

일반 Linux x86_64의 ONNX Runtime CPU에서 모델 로드와 API 테스트를 수행했습니다. Jetson 하드웨어·TensorRT 엔진 성능·MONAI/Clara 배포는 검증하지 않았습니다. 이 모델은 구조화 데이터 MLP이며 영상 전처리 프레임워크가 필요하지 않아 MONAI를 실행 의존성에 추가하지 않았습니다.

## CPU 실행부터 확인

1. Jetson의 JetPack, CUDA, TensorRT, Python 및 aarch64 환경을 확인합니다.
2. 해당 환경에 맞는 ONNX Runtime을 설치합니다. PC용 x86_64 wheel이나 일반 최신 GPU wheel을 무조건 설치하지 마십시오.
3. `backend/requirements.txt`의 FastAPI/NumPy/Pydantic/Uvicorn 요구사항을 환경에 맞게 설치합니다. 이미 호환 ORT를 설치했다면 requirements의 ORT 고정버전을 다시 덮어쓰지 마십시오.
4. 프로젝트 루트에서 `python scripts/check_runtime.py`로 실제 모델과 provider를 확인합니다.
5. 프론트엔드 `npm ci`, `npm run build` 후 `python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`을 실행합니다.

## TensorRT provider 선택

호환하는 ORT TensorRT 빌드가 설치된 Jetson에서:

```bash
export SYNEX_PROVIDER=tensorrt
python scripts/check_runtime.py
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

서버는 사용 가능한 `TensorrtExecutionProvider → CUDAExecutionProvider → CPUExecutionProvider` 순서로 설정합니다. 가속 provider를 사용할 수 없거나 초기화가 실패하면 CPU fallback 사유가 `/health`에 나타납니다. 모델 자체가 손상되었으면 가짜 값으로 실행하지 않고 시작에 실패합니다. provider 목록에 TensorRT가 있는 것만으로 모든 노드가 GPU에 배치됐다고 주장할 수 없습니다.

별도 TensorRT 엔진을 만들 경우 원본 ONNX를 보존하십시오. 대상 장치의 TensorRT `trtexec --help`로 플래그를 확인한 뒤, 해당 버전에서 지원하는 경우 다음 형태를 사용합니다:

```bash
trtexec --onnx=backend/models/risk_model_deep_v3.onnx --saveEngine=risk_model_deep_v3.engine --minShapes=features:1x7 --optShapes=features:1x7 --maxShapes=features:32x7
```

`.engine`은 현재 FastAPI가 직접 읽는 파일이 아닙니다. 현재 가속 경로는 ONNX Runtime TensorRT provider가 관리하는 실행입니다. FP16/INT8 적용 전후에는 경계값·위험도 분류·반복성·지연시간을 CPU 기준과 비교해야 합니다. 이번 작업에서는 엔진 생성이나 속도 개선을 수행했다고 주장하지 않습니다.

## 공식 자료

- [ONNX Runtime TensorRT provider 설치·JetPack 링크 및 호환 표](https://onnxruntime.ai/docs/execution-providers/TensorRT-ExecutionProvider.html): provider를 명시적으로 등록하고 비지원 노드를 위한 CUDA provider를 함께 설정하는 방식을 참고했습니다. 확인일 2026-09-11.
- [NVIDIA Jetson용 PyTorch 설치](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html): 향후 장치 내 재학습/영상 AI가 필요할 때 JetPack에 맞는 패키지 선택을 위한 자료입니다. 현재 ONNX 추론에는 PyTorch가 필요하지 않습니다.

MONAI/Clara의 특정 최신 릴리스나 Orin 호환성이 검증되었다고 주장하지 않습니다. 향후 영상 모델은 별도 service/interface로 연결하고 현재 7-feature 계약과 분리하십시오.
