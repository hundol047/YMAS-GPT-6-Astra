# Jetson AGX Orin Deployment

This document describes the actual Jetson deployment tooling in this repository as of the
current code -- not an aspiration. **Nothing in this document has been exercised on real Jetson
AGX Orin hardware from this development environment** (confirmed via `scripts/detect_jetson_env.py`:
this is x86_64 cloud Linux, no `/proc/device-tree/model`, no L4T, no CUDA toolchain, no NVIDIA
GPU). Every script below runs correctly here and takes the CPU Safe Mode path honestly -- that is
the one thing actually verified from this environment. Run it on a real device before trusting any
GPU-related claim.

## Quick Deploy

```bash
bash scripts/deploy_jetson_agx.sh --auto
```

Runs the full flow end to end: hardware detection → JetPack/L4T/CUDA/cuDNN/TensorRT detection →
Python venv (`.venv-jetson/`, never mixed with the plain-PC `.venv/`) → core dependency install →
ONNX Runtime install matched to the detected environment (or CPU fallback) → provider + real
inference verification → frontend/dist check → backend smoke tests → server startup → `/health` →
`/predict` → `/agent/analyze` → benchmark (with `tegrastats` sampling when available) →
`runtime/reports/jetson-deployment-<timestamp>.{json,txt}`.

On hardware that isn't Jetson AGX Orin (or where no verified deployment profile matches), this
takes the CPU Safe Mode path and reports so honestly -- it never installs a guessed GPU wheel.

## Y-MAS GPU-required Deploy

```bash
bash scripts/deploy_jetson_agx.sh --auto --require-gpu
# or, to specifically require TensorRT:
bash scripts/deploy_jetson_agx.sh --auto --require-tensorrt
```

Fails (non-zero exit, no silent CPU-mode "success") unless the running server's session actually
used `CUDAExecutionProvider` (`--require-gpu`) or specifically `TensorrtExecutionProvider`
(`--require-tensorrt`). Confirmed in this environment: `--require-gpu` here exits 4 with
`"A GPU execution provider was required but the session used CPU only"` -- exactly the intended
behavior on non-GPU hardware.

## Other flags

| Flag | Effect |
|---|---|
| `--provider auto\|cpu\|cuda\|tensorrt` | Force a specific `SYNEX_PROVIDER` instead of letting `auto` request `tensorrt` and let `RiskEngine`'s own cascade (tensorrt→cuda→cpu) pick what's actually available. |
| `--port`, `--host` | Server bind address (default `127.0.0.1:8000`; use `--host 0.0.0.0` to expose on the LAN). |
| `--fp16` | Enable TensorRT FP16 -- but ONLY after `scripts/validate_fp16.py` passes (see below); otherwise FP32 is kept and this is logged. |
| `--build-ort-tensorrt` | Allow an optional ONNX Runtime TensorRT-EP source build (`scripts/build_ort_tensorrt.sh`) when no pre-built wheel candidate is configured. Checks real prerequisites (cmake/git/gcc/CUDA/cuDNN/TensorRT headers, disk, memory) and refuses to start the build if any are missing. |
| `--rebuild-frontend` | Rebuild `frontend/dist` with `npm ci && npm run build` instead of using the tracked build as-is (the default -- Jetson deployment needs no Node.js at all unless this is passed). |
| `--install-service` | Writes (never installs/enables) a `systemd` unit template to `runtime/synexagent.service` for manual review and installation. |
| `--allow-other-orin` | Also accept Jetson Orin NX/Nano as a valid target for testing (default target is AGX Orin specifically -- a naive `'orin' in model` string check would misclassify NX/Nano as AGX Orin, which this repo's `scripts/jetson_common.py::classify_orin_family()` fixes). |
| `--performance-mode` | Reads (never changes) the current `nvpmodel` power mode around the benchmark. Power mode is never changed automatically, with or without this flag. |

## Diagnostic tools (usable standalone, without deploying anything)

```bash
python3 scripts/detect_jetson_env.py            # hardware/JetPack/L4T/CUDA/cuDNN/TensorRT/tools --
                                                 # no onnxruntime dependency, works before anything
                                                 # Jetson-specific is installed
python3 scripts/verify_jetson_agx_gpu.py --provider tensorrt   # real ONNX session + optional live
                                                                # /health,/predict,/agent/analyze checks
python3 scripts/benchmark_jetson.py              # model microbenchmark + application (ClinicalAgent)
                                                  # benchmark, per provider actually available
python3 scripts/compare_cpu_gpu_results.py       # CPU vs CUDA/TensorRT result equivalence across
                                                  # all 5 demo patients (risk_probability tolerance,
                                                  # risk_level must never differ, alerts/training_counts
                                                  # must be identical -- provider-independent by design)
python3 scripts/validate_fp16.py                 # FP16 vs FP32 TensorRT comparison gate for --fp16
python3 scripts/jetson_ymas_e2e.py --base-url http://127.0.0.1:8000   # the 15-step SYN-002 scenario
                                                                        # against a live server
```

Every one of these reports `NOT_AVAILABLE`/`SKIPPED`/`hardware_is_agx_orin: false` rather than a
fabricated pass when run off real Jetson hardware -- confirmed by actually running each of them in
this development container.

## Status vocabulary -- these are different things, never conflated

- **GPU AVAILABLE**: `ort.get_available_providers()` lists `CUDAExecutionProvider` (a build-time
  fact about the installed ONNX Runtime package, says nothing about whether it actually works).
- **GPU VERIFIED** (`CUDA ACCELERATION VERIFIED`): a real `InferenceSession` was created with
  `CUDAExecutionProvider`, `session.get_providers()` confirms it's actually in use, and a real
  inference on the real SynexAgent model succeeded.
- **TensorRT AVAILABLE**: `TensorrtExecutionProvider` is in `get_available_providers()`.
- **TensorRT VERIFIED** (`TENSORRT ACCELERATION VERIFIED`): same real-session-and-real-inference
  bar as CUDA, specifically for the TensorRT EP. A GPU wheel without the TensorRT EP compiled in
  reports `CUDA ACCELERATION VERIFIED / TENSORRT EP NOT AVAILABLE`, never upgraded to a TensorRT claim.
- **CPU FALLBACK / CPU SAFE MODE**: the session actually used `CPUExecutionProvider`, whether
  because CPU was explicitly requested, no GPU is available, or an accelerator failed to
  initialize (`fallback_reason` in `/health` explains which).

## Dependency strategy

- `backend/requirements-core.txt`: everything except ONNX Runtime (FastAPI, NumPy, Pydantic,
  Uvicorn, httpx, PyJWT, cryptography, redis).
- `backend/requirements.txt`: `requirements-core.txt` + the plain PyPI CPU `onnxruntime` wheel --
  used for a normal PC, and used as the Jetson CPU-fallback pin (`grep '^onnxruntime==' backend/requirements.txt`
  extracts just the version, never installed on `aarch64` alongside a GPU build).
- On Jetson, `scripts/install_jetson_ort.py` selects a GPU ONNX Runtime candidate from
  `config/jetson_ort_candidates.json` matched EXACTLY against the detected
  `jetpack_family`/`cuda_major`/`python_abi`/`arch` (see `scripts/jetson_common.py::profile_matches`
  for the equivalent deployment-profile logic). That file ships with **zero real candidates** --
  every real wheel URL/version must be added by hand on the real device after a real successful
  install, never guessed here. An unmatched environment falls back to CPU, or fails outright under
  `--require-gpu`/`--require-tensorrt`.
- `onnxruntime` (CPU) and `onnxruntime-gpu` are never installed together -- both are explicitly
  uninstalled before either install path proceeds.

## JetPack family classification (not hardcoded to one version)

`scripts/jetson_common.py::classify_l4t_family()` classifies a detected L4T major version into a
*family* (`jetpack6` for L4T 34-36 / CUDA 12.x, `jetpack7` for L4T 37-39 / CUDA 13.x) rather than
asserting an exact minor/patch version ever shipped. `config/jetson_agx_orin_profiles.json`
profiles are matched against the live-detected environment field-by-field
(`l4t_major`/`cuda_major`/`cuda_minor`/`cudnn_major`/`tensorrt_major`/`tensorrt_minor`/
`python_abi`/`arch` -- ALL must be non-null and equal); a profile missing any of those fields (like
the shipped `unverified-template`) can never match, by construction.

## FP16

`--fp16` never applies on its own judgment. `scripts/validate_fp16.py` runs the TensorRT session
twice (FP32 and FP16) across all 5 demo patients and only reports `PASS` if: both outputs are
finite and in [0,1], the max `risk_probability` delta is within `--tolerance` (default 0.02),
`risk_level` never differs, and rule-engine alerts/training_counts (provider-independent by
construction) are byte-identical. Any failure keeps FP32. On this non-GPU host it correctly reports
`SKIPPED` ("TensorRT unavailable on this host").

## TensorRT EP options actually used

`RiskEngine` attaches only options this ONNX Runtime version's TensorRT EP documents:
`device_id`, `trt_engine_cache_enable`, `trt_engine_cache_path` (pointed at the gitignored
`runtime/tensorrt-cache/` -- a compiled `.engine` is only valid for the exact device/driver/
TensorRT/CUDA combination it was built on, so it is never committed), `trt_timing_cache_enable`,
and `trt_fp16_enable` only when `--fp16` was validated and passed.

## Optional TensorRT EP source build

```bash
bash scripts/deploy_jetson_agx.sh --auto --build-ort-tensorrt
```

Only attempted when explicitly passed. `scripts/build_ort_tensorrt.sh` checks real prerequisites
(cmake, git, gcc/g++, CUDA toolkit dir, cuDNN headers, TensorRT headers, free disk/memory) and
refuses to start the build if any are missing -- confirmed in this environment, where it correctly
reports all three of CUDA/cuDNN/TensorRT missing and exits without attempting a build. Builds with
`CMAKE_CUDA_ARCHITECTURES=87` (AGX Orin/Orin NX/Orin Nano are all compute capability 8.7 -- a fixed
hardware fact, not a guess) and reads the checked-out ONNX Runtime's own `./build.sh --help` rather
than assuming flags from older documentation.

## Docker (secondary to the native path)

`docker/Dockerfile` (CPU, unchanged) stays as-is. `docker/Dockerfile.jetson` is a SEPARATE file for
the GPU path -- it takes a `BASE_IMAGE` build-arg that must be a real, already-verified
JetPack-matched NVIDIA base image tag (never hardcoded here, since no such tag has been confirmed
to exist and work from this environment). The native `.venv-jetson/` path above is the first path
to get fully working before adding Docker's extra layer of complexity, per this project's own
stated priority.

## Runtime data layout (all gitignored)

```
runtime/jetson_environment.json          # scripts/detect_jetson_env.py output
runtime/verify_report.json               # scripts/verify_jetson_agx_gpu.py output
runtime/health.json / predict.json / agent_analyze.json
runtime/pytest_output.txt
runtime/tensorrt-cache/                  # TensorRT engine/timing cache -- never committed
runtime/benchmarks/<timestamp>/          # benchmark.json + tegrastats.log
runtime/reports/jetson-deployment-<timestamp>.{json,txt}
runtime/synexagent.service               # written by --install-service, never auto-installed
```

## Packaging a release archive

```bash
bash scripts/package_jetson_release.sh
```

Produces `SynexAgent-YMAS-RC1-Jetson-AGX-Orin.tar.gz` containing only `backend/`, `frontend/dist/`,
`scripts/`, `config/`, `docs/`, `VERSION`, `.env.example` -- explicitly enumerated, not "copy
everything and exclude a blocklist" -- and refuses to write the archive if any `.sqlite*`/`.env`/
`.engine`-shaped file is found in the staged tree.

## What this deployment layer does NOT do

- Does not upgrade JetPack, flash firmware, change the bootloader, or run `apt dist-upgrade`.
- Does not change `nvpmodel` power mode automatically, ever.
- Does not add DLA, INT8, or any new clinical/EMR feature -- the Clinical Workspace and medical
  logic are frozen at the RC1 state this deployment layer wraps around.
- Does not claim NVIDIA/TensorRT acceleration without a real measured session/inference to back it up.

## Historical note

Earlier revisions of this document described a simpler 8-step CPU-only-tested flow and a naive
`'orin' in model.lower()` hardware check (which would have misclassified a Jetson Orin NX/Nano as
AGX Orin). Both are superseded by the sections above; see `scripts/jetson_common.py` for the
corrected classification logic and its test coverage in `backend/tests/test_jetson_common.py`.
