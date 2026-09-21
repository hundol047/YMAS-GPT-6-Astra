#!/usr/bin/env bash
# One-command Jetson AGX Orin deployment for SynexAgent Y-MAS RC1.
#
#   bash scripts/deploy_jetson_agx.sh --auto
#   bash scripts/deploy_jetson_agx.sh --auto --require-gpu
#
# Safety rules this script enforces end to end:
#   - NEVER installs a GPU ONNX Runtime wheel for an unverified/unmatched JetPack/L4T/CUDA
#     combination -- see scripts/jetson_common.py's profile_matches() and
#     scripts/install_jetson_ort.py's NO_CANDIDATE_CONFIGURED path. An unmatched environment falls
#     back to CPU Safe Mode, or FAILS outright if --require-gpu/--require-tensorrt was passed.
#   - NEVER installs both `onnxruntime` (CPU) and `onnxruntime-gpu` at once.
#   - NEVER upgrades JetPack, flashes firmware, changes the bootloader, or runs `apt dist-upgrade`.
#   - NEVER changes the power mode (nvpmodel) unless --performance-mode is explicitly passed.
#   - Uses its own `.venv-jetson/` -- never mixed with the plain-PC `.venv/` this repo's README
#     quick-start uses.
#
# This script has been run in THIS development container (x86_64 cloud Linux -- confirmed via
# scripts/detect_jetson_env.py to have no /proc/device-tree/model, no L4T, no CUDA toolchain, no
# NVIDIA GPU at all), where it correctly detects "not Jetson hardware" and takes the CPU Safe Mode
# path -- that is the one thing actually verified from here. The GPU install/verification path is
# written but UNEXERCISED until run on a real Jetson AGX Orin; nothing in this script's own output
# claims otherwise.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

# --- defaults -------------------------------------------------------------------------------
AUTO=false
REQUIRE_GPU=false
REQUIRE_TENSORRT=false
PROVIDER="auto"          # auto|cpu|cuda|tensorrt
PORT="8000"
HOST="127.0.0.1"
FP16=false
BUILD_ORT_TENSORRT=false
REBUILD_FRONTEND=false
INSTALL_SERVICE=false
ALLOW_OTHER_ORIN=false
PERFORMANCE_MODE=false
PYTHON_OVERRIDE=""
ORT_WHEEL_OVERRIDE="${SYNEX_ORT_WHEEL:-}"

usage() {
  cat <<'EOF'
Usage: bash scripts/deploy_jetson_agx.sh [options]

  --auto                  Run the full detect -> install -> verify -> benchmark -> report flow.
  --require-gpu           Fail (non-zero exit) unless the running session actually used CUDA or
                          TensorRT -- never silently "succeeds" in CPU Safe Mode.
  --require-tensorrt      Like --require-gpu, but specifically requires TensorrtExecutionProvider.
  --provider auto|cpu|cuda|tensorrt   Force a specific SYNEX_PROVIDER instead of auto-selecting.
  --port PORT             (default 8000)
  --host HOST              (default 127.0.0.1; use 0.0.0.0 to expose on the LAN)
  --fp16                  Enable TensorRT FP16 ONLY if scripts/validate_fp16.py passes first.
  --build-ort-tensorrt    Allow an optional ONNX Runtime TensorRT-EP source build if no pre-built
                          wheel candidate is configured (see scripts/build_ort_tensorrt.sh).
  --rebuild-frontend      Rebuild frontend/dist with npm instead of using the tracked build as-is.
  --install-service       Write (not install/enable) a systemd unit template for this deployment.
  --allow-other-orin      Also accept Jetson Orin NX/Nano as a valid target (default: AGX Orin only).
  --performance-mode      Read AND record the current nvpmodel power mode around the benchmark
                          (never changes it without this flag, and even then only records, per the
                          "print/read-only unless explicitly asked" policy -- see docs).
  --python /path/to/python   Use this specific interpreter to create .venv-jetson instead of the
                          system default `python3`. Never auto-picks "the newest available python3.x"
                          -- on a real JetPack/Ubuntu image, plain `python3` IS the supported default;
                          silently preferring a newer python3.1x that happens to also be installed can
                          select an ABI NVIDIA's own GPU ONNX Runtime wheels were never built for.
  --ort-wheel /path/to/verified.whl   Install THIS specific, already-verified ONNX Runtime wheel
                          instead of consulting config/jetson_ort_candidates.json. Use this once you
                          have obtained and confirmed a real GPU ORT wheel for this exact device
                          (see docs/JETSON_DEPLOYMENT.md) -- never a guessed or unconfirmed URL. On
                          JetPack 5, this is the PREFERRED path for a working ORT install: the
                          generic PyPI ARM64 CPU wheel (requirements-jetpack5-ort-cpu.txt) is not
                          assumed unconditionally safe there -- it native-crashed on real AGX Orin
                          + JetPack 5.1.2 hardware -- so a Jetson-specific build (this device's own
                          source build, or an NVIDIA-provided ARM64 wheel) is preferred once you
                          have one. Either way, whatever gets installed is only ever trusted after
                          scripts/ort_smoke_test.py (an isolated subprocess) confirms it actually
                          imports and runs without crashing -- never on installation success alone.
                          Same effect as setting SYNEX_ORT_WHEEL in the environment.
  -h, --help              This message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --auto) AUTO=true; shift ;;
    --require-gpu) REQUIRE_GPU=true; shift ;;
    --require-tensorrt) REQUIRE_TENSORRT=true; REQUIRE_GPU=true; shift ;;
    --provider) PROVIDER="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --fp16) FP16=true; shift ;;
    --build-ort-tensorrt) BUILD_ORT_TENSORRT=true; shift ;;
    --rebuild-frontend) REBUILD_FRONTEND=true; shift ;;
    --install-service) INSTALL_SERVICE=true; shift ;;
    --allow-other-orin) ALLOW_OTHER_ORIN=true; shift ;;
    --performance-mode) PERFORMANCE_MODE=true; shift ;;
    --python) PYTHON_OVERRIDE="$2"; shift 2 ;;
    --ort-wheel) ORT_WHEEL_OVERRIDE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done
if [[ "$PROVIDER" != "auto" && "$PROVIDER" != "cpu" && "$PROVIDER" != "cuda" && "$PROVIDER" != "tensorrt" ]]; then
  echo "Invalid --provider: $PROVIDER (must be auto|cpu|cuda|tensorrt)"; exit 1
fi

VENV_DIR="$ROOT/.venv-jetson"
PY="$VENV_DIR/bin/python3"
RUNTIME_DIR="$ROOT/runtime"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$RUNTIME_DIR/reports"
BENCH_DIR="$RUNTIME_DIR/benchmarks/$TS"
mkdir -p "$RUNTIME_DIR" "$REPORT_DIR" "$BENCH_DIR"

echo "== Step 1-4/20: Hardware + JetPack/L4T + NVIDIA stack detection =="
ALLOW_FLAG=""
if [ "$ALLOW_OTHER_ORIN" = true ]; then ALLOW_FLAG="--allow-other-orin"; fi
DETECT_JSON_PATH="$RUNTIME_DIR/jetson_environment.json"
python3 scripts/detect_jetson_env.py $ALLOW_FLAG --out "$DETECT_JSON_PATH" >/dev/null
IS_TARGET=$(python3 -c "import json;print(json.load(open('$DETECT_JSON_PATH'))['hardware']['is_supported_target'])")
ORIN_FAMILY=$(python3 -c "import json;print(json.load(open('$DETECT_JSON_PATH'))['hardware']['orin_family'])")
ARCH=$(python3 -c "import json;print(json.load(open('$DETECT_JSON_PATH'))['hardware']['machine_arch'])")
echo "detected: orin_family=$ORIN_FAMILY arch=$ARCH is_supported_target=$IS_TARGET"
if [ "$IS_TARGET" != "True" ]; then
  echo "This deployment target is not Jetson AGX Orin (pass --allow-other-orin to also accept Orin NX/Nano for testing)."
fi

echo "== Step 5/20: Python environment (.venv-jetson, never mixed with .venv) =="
# Default to the system's own `python3` (command -v python3) -- the JetPack/Ubuntu-provided
# default -- never "the newest python3.x that happens to also be installed". A verified deployment
# profile's python_abi was confirmed against THAT default interpreter; silently preferring a newer
# one changes the ABI a GPU ONNX Runtime candidate is selected for, away from what was verified. Use
# --python /path/to/python to explicitly target a different interpreter (e.g. a non-default python3.x
# actually intended for this deployment) -- this script never guesses that choice on its own.
if [ -n "$PYTHON_OVERRIDE" ]; then
  if ! command -v "$PYTHON_OVERRIDE" >/dev/null 2>&1 && [ ! -x "$PYTHON_OVERRIDE" ]; then
    echo "--python $PYTHON_OVERRIDE is not an executable interpreter."; exit 1
  fi
  PYTHON_BIN="$PYTHON_OVERRIDE"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "No python3 interpreter found on this system (pass --python /path/to/python to specify one)."; exit 1
fi
echo "Using $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1)) to create $VENV_DIR"
# Robustness: a venv without a working pip (seen for real: ".venv-jetson/bin/python3: No module
# named pip", typically because the system's python3-venv/ensurepip package is missing or partial)
# is NEVER silently reused -- it's removed and recreated, and if pip still can't be made to work,
# this script fails with the exact remediation command rather than limping on with a broken
# environment. This never runs `sudo apt install` itself -- only prints what the operator needs to
# run, since this script must not assume passwordless sudo or silently modify system packages.
create_or_repair_venv() {
  if [ -d "$VENV_DIR" ]; then
    if "$PY" -m pip --version >/dev/null 2>&1; then
      return 0
    fi
    echo "$VENV_DIR exists but has no working pip -- removing and recreating it (never reusing a broken venv)."
    rm -rf "$VENV_DIR"
  fi
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  if "$PY" -m pip --version >/dev/null 2>&1; then
    return 0
  fi
  echo "$VENV_DIR was created but pip is still missing -- trying '$PYTHON_BIN -m ensurepip --upgrade'."
  if "$PY" -m ensurepip --upgrade >/dev/null 2>&1 && "$PY" -m pip --version >/dev/null 2>&1; then
    return 0
  fi
  echo ""
  echo "FAILED: could not get a working pip into $VENV_DIR."
  echo "This usually means the system's venv/ensurepip support is incomplete for $PYTHON_BIN."
  echo "On a real JetPack/Ubuntu image, install it yourself, then re-run this script:"
  echo "  sudo apt-get update && sudo apt-get install -y python3-venv python3-pip"
  exit 1
}
create_or_repair_venv
"$PY" -m pip install -q --upgrade pip

echo "== Step 5b/20: JetPack family + target Python ABI branch =="
# The target venv's OWN interpreter ABI (queried by actually running it), never this script's own
# interpreter's ABI -- see jetson_common.python_abi_of's docstring for why those can legitimately
# differ (e.g. --python pointing at a non-default interpreter).
TARGET_PYTHON_ABI=$(python3 -c "
import sys; sys.path.insert(0,'scripts')
import jetson_common as jc
print(jc.python_abi_of('$PY') or '')
")
JETPACK_FAMILY=$(python3 -c "import json;print(json.load(open('$DETECT_JSON_PATH'))['nvidia_stack']['l4t']['jetpack_family'] or '')")
echo "target venv python_abi=$TARGET_PYTHON_ABI jetpack_family=$JETPACK_FAMILY"
if [ "$JETPACK_FAMILY" = "jetpack5" ] && [ "$TARGET_PYTHON_ABI" = "cp38" ]; then
  # Confirmed real environment: NVIDIA Jetson AGX Orin Developer Kit, JetPack 5.1.2 (L4T 35.4.1),
  # Python 3.8.10 -- current PyPI releases of fastapi/uvicorn/numpy/pydantic/pyjwt/cryptography/
  # redis dropped Python 3.8 wheels (confirmed via each package's own PyPI release metadata, not
  # guessed -- see backend/requirements-jetpack5.txt's header), which is EXACTLY the
  # "Could not find a version that satisfies the requirement fastapi==0.141.1" failure this branch
  # fixes. Any other JetPack family, or a JetPack 5 device on a different Python, keeps using the
  # normal requirements-core.txt/requirements.txt path below unchanged.
  echo "JetPack 5 + Python 3.8 (cp38) detected -- using backend/requirements-jetpack5.txt."
  CORE_REQ_FILE="backend/requirements-jetpack5.txt"
  CPU_ORT_REQ_FILE="backend/requirements-jetpack5-ort-cpu.txt"
else
  CORE_REQ_FILE="backend/requirements-core.txt"
  CPU_ORT_REQ_FILE=""   # empty means "use requirements.txt's onnxruntime== pin", below
fi

echo "== Step 6/20: Core dependency installation ($CORE_REQ_FILE, no ONNX Runtime yet) =="
"$PY" -m pip install -q -r "$CORE_REQ_FILE"

cpu_ort_pin() {
  if [ -n "$CPU_ORT_REQ_FILE" ]; then
    grep -E '^onnxruntime==' "$CPU_ORT_REQ_FILE"
  else
    grep -E '^onnxruntime==' backend/requirements.txt
  fi
}

echo "== Step 7/20: ONNX Runtime installation matching the detected environment =="
# NOTE: whichever branch below installs a CPU-only onnxruntime pin, that install is NOT the finish
# line -- step 8-9 always runs it through scripts/ort_smoke_test.py in an isolated subprocess before
# trusting it for anything. The generic PyPI ARM64 CPU wheel native-crashed for real on a Jetson AGX
# Orin + JetPack 5.1.2 device (see requirements-jetpack5-ort-cpu.txt's header) -- "pip install
# succeeded" is never treated as "this wheel actually works on this device".
EFFECTIVE_PROVIDER="cpu"
GPU_INSTALL_STATUS="not_attempted"
if [ "$PROVIDER" = "cpu" ]; then
  echo "Provider explicitly forced to cpu -- installing plain CPU onnxruntime."
  "$PY" -m pip uninstall -y -q onnxruntime onnxruntime-gpu >/dev/null 2>&1 || true
  ONNXRUNTIME_PIN=$(cpu_ort_pin)
  "$PY" -m pip install -q "$ONNXRUNTIME_PIN"
  GPU_INSTALL_STATUS="skipped_cpu_forced"
elif [ "$ARCH" != "aarch64" ]; then
  echo "arch=$ARCH is not aarch64 -- a Jetson GPU ONNX Runtime build cannot be installed here. CPU Safe Mode."
  ONNXRUNTIME_PIN=$(cpu_ort_pin)
  "$PY" -m pip install -q "$ONNXRUNTIME_PIN"
  GPU_INSTALL_STATUS="skipped_not_aarch64"
elif [ -n "$ORT_WHEEL_OVERRIDE" ]; then
  # --ort-wheel/SYNEX_ORT_WHEEL: install THIS specific wheel directly, bypassing
  # config/jetson_ort_candidates.json entirely -- the operator is asserting they already confirmed
  # this exact wheel works on this exact device (see docs/JETSON_DEPLOYMENT.md). This script does
  # not re-verify the URL/file is genuine beyond checking it exists; scripts/verify_jetson_agx_gpu.py
  # (step 8-9 below) still independently proves whether it actually executes GPU nodes.
  if [ ! -f "$ORT_WHEEL_OVERRIDE" ]; then
    echo "--ort-wheel $ORT_WHEEL_OVERRIDE does not exist -- refusing to guess a substitute."; exit 1
  fi
  echo "--ort-wheel passed -- installing $ORT_WHEEL_OVERRIDE directly (skipping candidate lookup)."
  "$PY" -m pip uninstall -y -q onnxruntime onnxruntime-gpu >/dev/null 2>&1 || true
  if "$PY" -m pip install -q "$ORT_WHEEL_OVERRIDE"; then
    GPU_INSTALL_STATUS="ort_wheel_override_installed"
  else
    echo "Failed to install $ORT_WHEEL_OVERRIDE -- falling back to CPU Safe Mode."
    GPU_INSTALL_STATUS="ort_wheel_override_failed"
    "$PY" -m pip uninstall -y -q onnxruntime onnxruntime-gpu >/dev/null 2>&1 || true
    ONNXRUNTIME_PIN=$(cpu_ort_pin)
    "$PY" -m pip install -q "$ONNXRUNTIME_PIN"
  fi
else
  if [ "$BUILD_ORT_TENSORRT" = true ]; then
    echo "--build-ort-tensorrt passed -- attempting TensorRT EP source build (see scripts/build_ort_tensorrt.sh)."
    if bash scripts/build_ort_tensorrt.sh; then
      WHEEL=$(find runtime/onnxruntime-src/build -iname 'onnxruntime_gpu*.whl' 2>/dev/null | head -1)
      if [ -n "$WHEEL" ]; then
        "$PY" -m pip uninstall -y -q onnxruntime onnxruntime-gpu >/dev/null 2>&1 || true
        "$PY" -m pip install -q "$WHEEL"
        GPU_INSTALL_STATUS="source_build_installed"
      else
        echo "Source build finished but no wheel found -- falling back to prebuilt candidate lookup."
        GPU_INSTALL_STATUS="source_build_no_wheel"
      fi
    else
      echo "Source build prerequisites not met or build failed -- falling back to prebuilt candidate lookup."
      GPU_INSTALL_STATUS="source_build_failed"
    fi
  fi
  if [ "$GPU_INSTALL_STATUS" != "source_build_installed" ]; then
    set +e
    INSTALL_OUT=$(python3 scripts/install_jetson_ort.py --python "$PY" 2>&1)
    INSTALL_RC=$?
    set -e
    echo "$INSTALL_OUT"
    case "$INSTALL_RC" in
      0) GPU_INSTALL_STATUS="installed_and_verified" ;;
      2) GPU_INSTALL_STATUS="no_candidate_configured" ;;
      *) GPU_INSTALL_STATUS="install_failed" ;;
    esac
  fi
  if [ "$GPU_INSTALL_STATUS" != "installed_and_verified" ] && [ "$GPU_INSTALL_STATUS" != "source_build_installed" ]; then
    echo "No GPU ONNX Runtime installed ($GPU_INSTALL_STATUS) -- installing plain CPU onnxruntime instead."
    "$PY" -m pip uninstall -y -q onnxruntime onnxruntime-gpu >/dev/null 2>&1 || true
    ONNXRUNTIME_PIN=$(cpu_ort_pin)
    "$PY" -m pip install -q "$ONNXRUNTIME_PIN"
  fi
fi

if [ "$PROVIDER" = "auto" ]; then
  # Let RiskEngine's own existing tensorrt -> cuda -> cpu cascade (services/risk_inference.py)
  # pick whichever is actually available -- avoids duplicating that fallback logic here in bash.
  EFFECTIVE_PROVIDER="tensorrt"
else
  EFFECTIVE_PROVIDER="$PROVIDER"
fi
echo "requested SYNEX_PROVIDER=$EFFECTIVE_PROVIDER (auto lets RiskEngine cascade tensorrt->cuda->cpu)"

echo "== Step 8-9/20: ISOLATED ORT smoke test -> provider enumeration -> model load -> one inference -> profiling =="
"$PY" -m pip install -q httpx==0.28.1
# verify_jetson_agx_gpu.py itself now runs scripts/ort_smoke_test.py as an ISOLATED subprocess
# FIRST, before ever importing onnxruntime in-process -- exactly the order this step's name
# describes (import smoke test -> provider enumeration -> model load -> one inference -> profiling).
# A native ORT crash there (confirmed for real on Jetson AGX Orin + JetPack 5.1.2 with the generic
# PyPI CPU onnxruntime==1.19.2 wheel: SIGABRT / "Aborted (core dumped)") makes verify_jetson_agx_gpu.py
# exit 3 -- NEVER treated the same as an ordinary failure, and NEVER silently swallowed with `|| true`
# the way earlier revisions of this script did (which is exactly what let a crash here get relabeled
# "CPU/GPU result equivalence FAILED" by step 10, even though step 10 never even started).
# stdout (the JSON report) and stderr (the human-readable summary/notes) are captured separately --
# merging them would produce a file that's neither valid JSON nor readable text.
set +e
"$PY" scripts/verify_jetson_agx_gpu.py --provider "$EFFECTIVE_PROVIDER" $ALLOW_FLAG \
  > "$RUNTIME_DIR/verify_report.json" 2> "$RUNTIME_DIR/verify_report.stderr.log"
VERIFY_RC=$?
set -e
cat "$RUNTIME_DIR/verify_report.stderr.log" >&2
cat "$RUNTIME_DIR/verify_report.json"
if [ "$VERIFY_RC" = "3" ]; then
  ORT_STATUS=$(python3 -c "import json;print(json.load(open('$RUNTIME_DIR/verify_report.json'))['onnxruntime']['status'])" 2>/dev/null || echo "UNKNOWN")
  echo ""
  echo "DEPLOYMENT STATUS: $ORT_STATUS -- stopping BEFORE the CPU/GPU equivalence step (step 10 never ran)."
  echo "This is a real ONNX Runtime failure (see $RUNTIME_DIR/verify_report.stderr.log for the raw"
  echo "crash/exception output), never mislabeled as an equivalence mismatch -- equivalence testing"
  echo "requires a working provider on both sides, which this environment does not currently have."
  exit 6
elif [ "$VERIFY_RC" != "0" ]; then
  echo "verify_jetson_agx_gpu.py exited $VERIFY_RC (not the ORT-smoke-test-specific exit 3) -- treating as a general verification failure."
  exit "$VERIFY_RC"
fi

echo "== Step 10/20: CPU/GPU result equivalence check (SYN-001..005) =="
# Only ever reached once step 8-9's isolated ORT smoke test AND the full in-process verification
# both actually succeeded -- a real provider produced a real result on at least the CPU side before
# this comparison is even attempted. A GPU deployment is never reported as successful if its actual
# numeric/classification output diverges from the CPU baseline beyond the tolerance
# compare_cpu_gpu_results.py defines -- this is never skipped just because it might fail; failing
# HERE means the GPU deployment itself failed (CPU_GPU_MISMATCH), not that this check was optional.
set +e
"$PY" scripts/compare_cpu_gpu_results.py > "$RUNTIME_DIR/cpu_gpu_comparison.json" 2>"$RUNTIME_DIR/cpu_gpu_comparison.stderr.log"
COMPARISON_RC=$?
set -e
cat "$RUNTIME_DIR/cpu_gpu_comparison.stderr.log" >&2
cat "$RUNTIME_DIR/cpu_gpu_comparison.json"
if [ "$COMPARISON_RC" -ge 128 ]; then
  # A shell exit code >=128 means the process was killed by signal (COMPARISON_RC - 128) -- e.g. 134
  # = SIGABRT, 139 = SIGSEGV. This is the same native-crash failure mode as step 8-9, just caught
  # here as defense in depth (compare_cpu_gpu_results.py also builds real ORT sessions in-process,
  # for both the CPU baseline and any available GPU candidate) -- reported as a crash, never as
  # "CPU/GPU result equivalence FAILED", since equivalence was never actually compared.
  SIGNAL_NUM=$((COMPARISON_RC - 128))
  echo ""
  echo "DEPLOYMENT STATUS: ORT_NATIVE_RUNTIME_CRASH -- compare_cpu_gpu_results.py was killed by signal $SIGNAL_NUM (exit $COMPARISON_RC)."
  echo "This is a native ONNX Runtime crash during the equivalence check itself, never mislabeled as a mismatch."
  exit 6
elif [ "$COMPARISON_RC" != "0" ]; then
  echo "DEPLOYMENT STATUS: CPU_GPU_MISMATCH -- a provider that was actually used produced results that diverge from the CPU baseline beyond tolerance (see $RUNTIME_DIR/cpu_gpu_comparison.json). This deployment is NOT successful."
  exit 5
fi

echo "== Step 11/20: frontend/dist verification =="
if [ "$REBUILD_FRONTEND" = true ]; then
  if command -v npm >/dev/null 2>&1; then
    echo "--rebuild-frontend passed -- rebuilding frontend/dist."
    (cd frontend && npm ci && npm run build)
  else
    echo "--rebuild-frontend passed but npm is not installed -- cannot rebuild. Using the tracked frontend/dist as-is."
  fi
elif [ -f "frontend/dist/index.html" ]; then
  echo "frontend/dist already present (tracked in the repo) -- using it as-is, no Node.js needed on this device."
else
  echo "WARNING: frontend/dist/index.html not found and --rebuild-frontend not passed -- the SPA will not be served."
fi

echo "== Step 12/20: Backend smoke tests =="
# Installed separately from requirements-dev.txt on purpose: that file pulls in requirements.txt,
# which would reinstall the plain CPU onnxruntime and stomp whatever GPU build step 7 just set up.
"$PY" -m pip install -q pytest==9.1.1 httpx==0.28.1 onnx==1.22.0
if SYNEX_PROVIDER="$EFFECTIVE_PROVIDER" "$PY" -m pytest backend/tests -q > "$RUNTIME_DIR/pytest_output.txt" 2>&1; then
  echo "backend tests: PASS (see $RUNTIME_DIR/pytest_output.txt)"
else
  echo "backend tests: FAILURES -- see $RUNTIME_DIR/pytest_output.txt"
  tail -30 "$RUNTIME_DIR/pytest_output.txt"
fi

if [ "$PERFORMANCE_MODE" = true ]; then
  echo "-- --performance-mode: reading (not changing) current power mode --"
  command -v nvpmodel >/dev/null 2>&1 && nvpmodel -q || echo "nvpmodel not present on this host"
fi

echo "== Step 13/20: Server startup =="
SYNEX_TENSORRT_FP16_VALUE="false"
if [ "$FP16" = true ]; then
  echo "--fp16 passed -- validating FP16 vs FP32 before enabling it (see scripts/validate_fp16.py)."
  if "$PY" scripts/validate_fp16.py > "$RUNTIME_DIR/fp16_validation.json" 2>&1; then
    FP16_STATUS=$(python3 -c "import json;print(json.load(open('$RUNTIME_DIR/fp16_validation.json'))['status'])")
    if [ "$FP16_STATUS" = "PASS" ]; then
      SYNEX_TENSORRT_FP16_VALUE="true"
      echo "FP16 validation PASSED -- enabling."
    else
      echo "FP16 validation did not PASS (status=$FP16_STATUS) -- keeping FP32."
    fi
  else
    echo "FP16 validation script failed to run -- keeping FP32."
  fi
fi

SYNEX_PROVIDER="$EFFECTIVE_PROVIDER" SYNEX_TENSORRT_FP16="$SYNEX_TENSORRT_FP16_VALUE" \
  "$PY" -m uvicorn app.main:app --app-dir backend --host "$HOST" --port "$PORT" &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then break; fi
  sleep 1
done

echo "== Step 14/20: GET /health =="
HEALTH=$(curl -sf "http://127.0.0.1:$PORT/health") || { echo "Health check failed"; exit 1; }
echo "$HEALTH" | tee "$RUNTIME_DIR/health.json"

echo "== Step 15/20: POST /predict =="
PREDICT_BODY='{"drug_conflict":0.5,"comorbidity_load":0.4,"age_risk":0.5,"allergy_flag":0.0,"adverse_history":0,"polypharmacy_load":0.3,"therapy_duration_load":0.2}'
PREDICT_RESULT=$(curl -sf -X POST "http://127.0.0.1:$PORT/predict" -H 'Content-Type: application/json' -d "$PREDICT_BODY") || { echo "/predict failed"; exit 1; }
echo "$PREDICT_RESULT" | tee "$RUNTIME_DIR/predict.json"

echo "== Step 16/20: POST /agent/analyze (SYN-002) =="
ANALYZE_RESULT=$(curl -sf -X POST "http://127.0.0.1:$PORT/agent/analyze" -H 'Content-Type: application/json' -d '{"patient_id":"SYN-002"}') || { echo "/agent/analyze failed"; exit 1; }
echo "$ANALYZE_RESULT" > "$RUNTIME_DIR/agent_analyze.json"
echo "(saved to $RUNTIME_DIR/agent_analyze.json)"

echo "== Step 17/20: --require-gpu / --require-tensorrt enforcement =="
# Gates on the ACTUAL per-node execution proof from step 8-9's profiled verification run
# (verify_report.json's onnxruntime.provider_status), never on session provider REGISTRATION alone
# -- "CUDAExecutionProvider" appearing in session.get_providers() is not, by itself, proof any node
# ran on it (see jetson_common.classify_provider_status / count_nodes_by_provider). A CUDA-only
# fallback (TensorRT EP unavailable/unused) never satisfies --require-tensorrt.
GPU_CHECK_OK=$(python3 -c "
import json, sys
sys.path.insert(0, 'scripts')
import jetson_common as jc
report = json.load(open('$RUNTIME_DIR/verify_report.json'))
status = report.get('onnxruntime', {}).get('provider_status', {})
require_gpu, require_tensorrt = $( [ "$REQUIRE_GPU" = true ] && echo True || echo False ), $( [ "$REQUIRE_TENSORRT" = true ] && echo True || echo False )
ok, reason = jc.check_gpu_requirement_by_status(status, require_gpu, require_tensorrt)
print(ok)
if not ok:
    print(reason, file=sys.stderr)
")
if [ "$GPU_CHECK_OK" != "True" ]; then
  echo "REQUIREMENT NOT MET: --require-gpu/--require-tensorrt was set but real per-node GPU execution was not verified (see $RUNTIME_DIR/verify_report.json)."
  exit 4
fi

echo "== Step 18/20: Benchmark (with tegrastats background sampling) =="
TEGRA_LOG="$BENCH_DIR/tegrastats.log"
TEGRA_PID=""
if command -v tegrastats >/dev/null 2>&1; then
  tegrastats --interval 1000 > "$TEGRA_LOG" 2>&1 &
  TEGRA_PID=$!
fi
"$PY" scripts/benchmark_jetson.py > "$BENCH_DIR/benchmark.json" 2>&1 || true
if [ -n "$TEGRA_PID" ]; then kill "$TEGRA_PID" 2>/dev/null || true; fi
cat "$BENCH_DIR/benchmark.json"

echo "== Step 19/20: Deployment report =="
python3 scripts/generate_jetson_report.py \
  --detect-json "$DETECT_JSON_PATH" \
  --verify-json "$RUNTIME_DIR/verify_report.json" \
  --health-json "$RUNTIME_DIR/health.json" \
  --predict-json "$RUNTIME_DIR/predict.json" \
  --benchmark-json "$BENCH_DIR/benchmark.json" \
  --pytest-output "$RUNTIME_DIR/pytest_output.txt" \
  --tegrastats-log "$TEGRA_LOG" \
  --out-json "$REPORT_DIR/jetson-deployment-$TS.json" \
  --out-txt "$REPORT_DIR/jetson-deployment-$TS.txt"
echo "Report written to $REPORT_DIR/jetson-deployment-$TS.{json,txt}"

echo "== Step 20/20: Verified-profile capture (real hardware only) =="
if [ "$IS_TARGET" = "True" ]; then
  # Captures what THIS run actually observed into a NEW file for human review -- never auto-edits
  # config/jetson_agx_orin_profiles.json itself. Only runs when this deployment happened on a
  # detected AGX Orin (or, with --allow-other-orin, an accepted other-Orin target); on a non-Jetson
  # host this step is skipped entirely rather than writing a capture that would misleadingly look
  # like a hardware-observed record.
  python3 scripts/capture_jetson_verified_profile.py \
    --detect-json "$DETECT_JSON_PATH" \
    --verify-json "$RUNTIME_DIR/verify_report.json" \
    --health-json "$RUNTIME_DIR/health.json" \
    --predict-json "$RUNTIME_DIR/predict.json" \
    --agent-analyze-json "$RUNTIME_DIR/agent_analyze.json" \
    --benchmark-json "$BENCH_DIR/benchmark.json" \
    --out "$RUNTIME_DIR/jetson_verified_profile.json" >/dev/null
  echo "Wrote $RUNTIME_DIR/jetson_verified_profile.json -- review by hand before promoting anything into config/jetson_agx_orin_profiles.json."
else
  echo "Skipped: this run was not on a detected Jetson AGX Orin (is_supported_target=$IS_TARGET) -- no verified-profile capture written."
fi

if [ "$INSTALL_SERVICE" = true ]; then
  echo "== systemd service template (written, NOT installed/enabled) =="
  SERVICE_PATH="$RUNTIME_DIR/synexagent.service"
  cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=SynexAgent Y-MAS Clinical Workspace
After=network.target

[Service]
Type=simple
WorkingDirectory=$ROOT
Environment=SYNEX_PROVIDER=$EFFECTIVE_PROVIDER
Environment=SYNEX_TENSORRT_FP16=$SYNEX_TENSORRT_FP16_VALUE
ExecStart=$PY -m uvicorn app.main:app --app-dir backend --host $HOST --port $PORT
Restart=on-failure
User=%i

[Install]
WantedBy=multi-user.target
EOF
  echo "Wrote $SERVICE_PATH -- review it, then (as root) copy to /etc/systemd/system/ and run"
  echo "'systemctl daemon-reload && systemctl enable --now synexagent' yourself. This script never"
  echo "does that automatically."
fi

echo ""
echo "DEPLOYMENT STATUS: $(python3 -c "
import json
report = json.load(open('$RUNTIME_DIR/verify_report.json'))
status = report.get('onnxruntime', {}).get('provider_status', {})
is_target = $IS_TARGET
# Never printed unless this run actually happened ON a detected AGX Orin (is_target) -- running
# this script on a non-Jetson host (e.g. this development container) always reports the honest
# 'NOT HARDWARE VERIFIED' status, whatever provider_status shows, per the explicit rule that a
# CUDA/TensorRT VERIFIED claim is only ever made from a run that actually happened on real hardware.
if not is_target:
    print('JETSON DEPLOYMENT CODE PREPARED / NOT HARDWARE VERIFIED')
elif status.get('TensorrtExecutionProvider') == 'EXECUTION_VERIFIED':
    print('JETSON AGX ORIN TENSORRT EXECUTION VERIFIED')
elif status.get('CUDAExecutionProvider') == 'EXECUTION_VERIFIED':
    print('JETSON AGX ORIN CUDA EXECUTION VERIFIED')
else:
    print('JETSON AGX ORIN CPU VERIFIED')
")"
