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

Runs the full 20-step flow end to end: hardware detection → JetPack/L4T/CUDA/cuDNN/TensorRT
detection → Python venv (`.venv-jetson/`, default interpreter `command -v python3`; never mixed
with the plain-PC `.venv/`) → core dependency install → ONNX Runtime install matched to the
detected environment via the exact verified-profile gate (or CPU fallback) → provider + real
inference + profiling-based node-execution verification → CPU/GPU result equivalence check
(SYN-001..005) → frontend/dist check → backend smoke tests → server startup → `/health` →
`/predict` → `/agent/analyze` → `--require-gpu`/`--require-tensorrt` enforcement → benchmark (with
`tegrastats` sampling when available) → `runtime/reports/jetson-deployment-<timestamp>.{json,txt}`
→ verified-profile capture (real hardware only).

On hardware that isn't Jetson AGX Orin (or where no verified deployment profile matches), this
takes the CPU Safe Mode path and reports so honestly -- it never installs a guessed GPU wheel.
Use `--python /path/to/python` to target a specific interpreter for `.venv-jetson` instead of the
system default (see "Python interpreter selection" below).

## Y-MAS GPU-required Deploy

```bash
bash scripts/deploy_jetson_agx.sh --auto --require-gpu
# or, to specifically require TensorRT:
bash scripts/deploy_jetson_agx.sh --auto --require-tensorrt
```

Fails (non-zero exit, no silent CPU-mode "success") unless the requested provider was actually
**execution-verified** (`jetson_common.classify_provider_status()` returned `EXECUTION_VERIFIED`
for `CUDAExecutionProvider` -- `--require-gpu` -- or specifically `TensorrtExecutionProvider` --
`--require-tensorrt`), via `jetson_common.check_gpu_requirement_by_status()`. Session provider
*registration* alone (`CUDAExecutionProvider` merely appearing in `session.get_providers()`) is
never enough -- see "Status vocabulary" below. A CUDA-only fallback never satisfies
`--require-tensorrt`, however verified CUDA's own status is. Confirmed in this environment:
`--require-gpu` here exits 4 with a reason naming both providers' actual status (`NOT_AVAILABLE` on
this non-GPU host) -- exactly the intended behavior.

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
| `--python /path/to/python` | Use this interpreter to create `.venv-jetson` instead of the system default `command -v python3`. The default is never "the newest `python3.x` available" -- see "Python interpreter selection" below. |

## Diagnostic tools (usable standalone, without deploying anything)

```bash
python3 scripts/detect_jetson_env.py            # hardware/JetPack/L4T/CUDA/cuDNN/TensorRT/tools --
                                                 # no onnxruntime dependency, works before anything
                                                 # Jetson-specific is installed
python3 scripts/verify_jetson_agx_gpu.py --provider tensorrt   # real ONNX session + ORT-profiling-
                                                                # based node execution proof +
                                                                # optional live /health,/predict,
                                                                # /agent/analyze checks
python3 scripts/benchmark_jetson.py              # model microbenchmark + application (ClinicalAgent)
                                                  # benchmark, per provider actually available --
                                                  # each entry reports requested_provider /
                                                  # actual_session_providers /
                                                  # execution_verified_provider separately
python3 scripts/compare_cpu_gpu_results.py       # CPU vs CUDA/TensorRT result equivalence across
                                                  # all 5 demo patients (risk_probability tolerance,
                                                  # risk_level must never differ, alerts/training_counts
                                                  # must be identical -- provider-independent by design)
python3 scripts/validate_fp16.py                 # FP16 vs FP32 TensorRT comparison gate for --fp16
python3 scripts/jetson_ymas_e2e.py --base-url http://127.0.0.1:8000   # the 15-step SYN-002 scenario
                                                                        # against a live server
python3 scripts/suggest_jetson_ort_candidate.py [--python /path]  # REPORT ONLY: detected environment,
                                                                   # any matching profile, whether it's
                                                                   # verified, whether its ort_candidate_id
                                                                   # resolves to a filled-in candidate,
                                                                   # and manual_verification_required --
                                                                   # never writes to config/, never marks
                                                                   # anything verified
```

Every one of these reports `NOT_AVAILABLE`/`SKIPPED`/`hardware_is_agx_orin: false` rather than a
fabricated pass when run off real Jetson hardware -- confirmed by actually running each of them in
this development container.

## Status vocabulary -- these are different things, never conflated

`scripts/jetson_common.py::classify_provider_status()` returns exactly one of six values, computed
per provider (`CPUExecutionProvider`/`CUDAExecutionProvider`/`TensorrtExecutionProvider`):

| Status | Meaning |
|---|---|
| `NOT_AVAILABLE` | The provider isn't in `ort.get_available_providers()` at all (a build-time fact about the installed ONNX Runtime package). |
| `AVAILABLE` | Available, but no session has been built yet to check further. |
| `SESSION_REGISTERED` | The provider is in `session.get_providers()`, but real inference hasn't been confirmed yet (or failed). Registration alone is never treated as more than this. |
| `FALLBACK` | The provider was available but the live session ended up using something else (e.g. `--provider tensorrt` requested, but only CUDA was actually usable). |
| `INFERENCE_PASSED` | A real forward pass succeeded end-to-end on this provider, but per-node execution evidence (see below) couldn't be gathered -- not "unverified", just short of the strongest proof. |
| `EXECUTION_VERIFIED` | Real ONNX Runtime profiling (`SessionOptions.enable_profiling=True` + `session.end_profiling()`, parsed by `jetson_common.count_nodes_by_provider()`) proved at least one node actually executed on this specific provider. **This is the only status `--require-gpu`/`--require-tensorrt` accept.** |

`scripts/verify_jetson_agx_gpu.py` builds a dedicated profiled session (separate from the one
`RiskEngine` itself builds for normal serving) to gather this evidence, and reports it as
`provider_status: {CPUExecutionProvider: ..., CUDAExecutionProvider: ..., TensorrtExecutionProvider: ...}`
plus `nodes_executed_by_provider` (raw counts) in its JSON output. TensorRT engine-cache creation
alone, or a CUDA session merely being registered, is never reported as `EXECUTION_VERIFIED` for
TensorRT -- and a CUDA-only fallback never satisfies a TensorRT requirement.

## Dependency strategy

- `backend/requirements-core.txt`: everything except ONNX Runtime (FastAPI, NumPy, Pydantic,
  Uvicorn, httpx, PyJWT, cryptography, redis).
- `backend/requirements.txt`: `requirements-core.txt` + the plain PyPI CPU `onnxruntime` wheel --
  used for a normal PC, and used as the Jetson CPU-fallback pin (`grep '^onnxruntime==' backend/requirements.txt`
  extracts just the version, never installed on `aarch64` alongside a GPU build).
- On Jetson, `scripts/install_jetson_ort.py` **never** matches a candidate directly against the
  detected environment. It first requires an EXACT match (`scripts/jetson_common.py::profile_matches`,
  comparing `l4t_major`/`cuda_major`/`cuda_minor`/`cudnn_major`/`tensorrt_major`/`tensorrt_minor`/
  `python_abi`/`arch` -- all non-null and equal) against a `verified: true` entry in
  `config/jetson_agx_orin_profiles.json`. Only THEN does it look up that profile's own
  `ort_candidate_id` in `config/jetson_ort_candidates.json` (`jetson_common.resolve_ort_candidate_for_profile`).
  No verified profile matches → `NO_VERIFIED_PROFILE`. A verified profile matches but its
  `ort_candidate_id` doesn't resolve to a filled-in candidate → `NO_VERIFIED_ORT_CANDIDATE`. Either
  way, CPU Safe Mode follows (or `--require-gpu`/`--require-tensorrt` fails outright) -- a verified
  profile alone proves the *environment* was confirmed on real hardware, it does not by itself
  supply a working wheel. `config/jetson_ort_candidates.json` ships with **zero real candidates**;
  see `scripts/suggest_jetson_ort_candidate.py` for a read-only report of where this device stands
  against both files, without ever writing to either.
- The ABI used for both the profile match and the candidate lookup is the ABI of the **target
  venv's own interpreter** (`jetson_common.python_abi_of(python_bin)`, which runs that specific
  interpreter to ask it), never the ABI of whatever Python happens to be running the installer
  script itself -- these can legitimately differ (e.g. a system default `cp310` running the
  installer against a `--python /usr/bin/python3.12` target venv).
- `onnxruntime` (CPU) and `onnxruntime-gpu` are never installed together -- both are explicitly
  uninstalled before either install path proceeds.

## JetPack family classification (an exact table, not a range guess)

`scripts/jetson_common.py::classify_l4t_family()` classifies a detected L4T major version via an
EXACT lookup table -- each entry is a real, NVIDIA-documented JetPack generation, never a guessed
range:

| L4T major | JetPack family |
|---|---|
| 34, 35 | `jetpack5` |
| 36 | `jetpack6` |
| 39 | `jetpack7` |
| anything else (e.g. 37, 38, or unrecognized) | `None` (unsupported/unrecognized -- never guessed) |

`CUDA_MAJOR_TO_JETPACK_FAMILY` provides the same mapping from CUDA major version (11→jetpack5,
12→jetpack6, 13→jetpack7) purely for cross-checking against the L4T-derived family; a mismatch
between the two is surfaced, not silently ignored. `config/jetson_agx_orin_profiles.json` profiles
are matched against the live-detected environment field-by-field (`l4t_major`/`cuda_major`/
`cuda_minor`/`cudnn_major`/`tensorrt_major`/`tensorrt_minor`/`python_abi`/`arch` -- ALL must be
non-null and equal); a profile missing any of those fields (like the shipped `unverified-template`)
can never match, by construction.

## Python interpreter selection

`.venv-jetson` is created from `command -v python3` by default -- the JetPack/Ubuntu-provided
system default -- **never** "the newest `python3.x` also installed on this system". A verified
deployment profile's `python_abi` was confirmed against that default interpreter; silently
preferring a newer one changes the ABI a GPU ONNX Runtime candidate gets selected for, away from
what was actually verified. Use `--python /path/to/python` to explicitly target a different
interpreter when that's genuinely what this deployment needs -- this script never guesses that
choice on its own. (On this development container, the system default `python3` is 3.11, which is
older than `backend/requirements-core.txt`'s `numpy` pin requires -- `--python /usr/bin/python3.12`
was used to validate the rest of this flow end-to-end here; on a real JetPack image, whichever
`python3` ships as that image's default is what gets used unless `--python` overrides it.)

## Verified-profile capture (real hardware only)

On a run where `hardware_is_agx_orin` (or, with `--allow-other-orin`, an accepted other-Orin
target) is actually true, the last step writes `runtime/jetson_verified_profile.json`
(`scripts/capture_jetson_verified_profile.py`) -- a snapshot of everything that run actually
observed: hardware/L4T/JetPack family/CUDA/cuDNN/TensorRT/Python ABI, the ONNX Runtime
provider/execution status actually seen, the model SHA-256, and the `/predict`/`/agent/analyze`/
benchmark results. This is a **gitignored, human-reviewable file, never an automatic edit** to
`config/jetson_agx_orin_profiles.json` -- promoting it into a new `verified: true` profile entry
(with a matching `config/jetson_ort_candidates.json` entry linked via `ort_candidate_id`) is always
a manual step a person takes after reviewing the capture. On a non-Jetson host (like this
development container) this step is skipped entirely, never producing a capture that would
misleadingly look like a hardware-observed record.

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
runtime/verify_report.json               # scripts/verify_jetson_agx_gpu.py output (incl. provider_status,
                                          # nodes_executed_by_provider, verification_status)
runtime/cpu_gpu_comparison.json          # scripts/compare_cpu_gpu_results.py output
runtime/health.json / predict.json / agent_analyze.json
runtime/pytest_output.txt
runtime/tensorrt-cache/                  # TensorRT engine/timing cache -- never committed
runtime/benchmarks/<timestamp>/          # benchmark.json + tegrastats.log
runtime/reports/jetson-deployment-<timestamp>.{json,txt}
runtime/jetson_verified_profile.json     # capture from a REAL hardware run only -- see above; never
                                          # auto-promoted into config/jetson_agx_orin_profiles.json
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

Earlier revisions of this document described a simpler 8-step CPU-only-tested flow, a naive
`'orin' in model.lower()` hardware check (which would have misclassified a Jetson Orin NX/Nano as
AGX Orin), a JetPack classification based on version *ranges* rather than an exact table, and a
`--require-gpu`/`--require-tensorrt` gate based on session provider *registration* rather than real
per-node execution proof. All are superseded by the sections above; see `scripts/jetson_common.py`
for the corrected classification/verification logic and its test coverage in
`backend/tests/test_jetson_common.py` and `backend/tests/test_jetson_scripts.py`.
