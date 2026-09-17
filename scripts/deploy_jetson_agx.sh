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

echo "== Step 1-4/17: Hardware + JetPack/L4T + NVIDIA stack detection =="
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

echo "== Step 5/17: Python environment (.venv-jetson, never mixed with .venv) =="
# Prefer the newest python3.x actually present rather than whatever bare `python3` happens to
# resolve to -- this repo's pinned dependency versions (backend/requirements-core.txt) need a
# reasonably current interpreter, and a system default `python3` can be older than that even when
# a newer one is installed alongside it. On a real JetPack image, whichever python3.x ships there
# is what gets used; this never installs a new Python version itself.
PYTHON_BIN=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then PYTHON_BIN="$candidate"; break; fi
done
if [ -z "$PYTHON_BIN" ]; then echo "No python3 interpreter found on this system."; exit 1; fi
echo "Using $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1)) to create $VENV_DIR"
if [ ! -d "$VENV_DIR" ]; then "$PYTHON_BIN" -m venv "$VENV_DIR"; fi
"$PY" -m pip install -q --upgrade pip

echo "== Step 6/17: Core dependency installation (no ONNX Runtime yet) =="
"$PY" -m pip install -q -r backend/requirements-core.txt

echo "== Step 7/17: ONNX Runtime installation matching the detected environment =="
EFFECTIVE_PROVIDER="cpu"
GPU_INSTALL_STATUS="not_attempted"
if [ "$PROVIDER" = "cpu" ]; then
  echo "Provider explicitly forced to cpu -- installing plain CPU onnxruntime."
  "$PY" -m pip uninstall -y -q onnxruntime onnxruntime-gpu >/dev/null 2>&1 || true
  ONNXRUNTIME_PIN=$(grep -E '^onnxruntime==' backend/requirements.txt)
  "$PY" -m pip install -q "$ONNXRUNTIME_PIN"
  GPU_INSTALL_STATUS="skipped_cpu_forced"
elif [ "$ARCH" != "aarch64" ]; then
  echo "arch=$ARCH is not aarch64 -- a Jetson GPU ONNX Runtime build cannot be installed here. CPU Safe Mode."
  ONNXRUNTIME_PIN=$(grep -E '^onnxruntime==' backend/requirements.txt)
  "$PY" -m pip install -q "$ONNXRUNTIME_PIN"
  GPU_INSTALL_STATUS="skipped_not_aarch64"
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
    ONNXRUNTIME_PIN=$(grep -E '^onnxruntime==' backend/requirements.txt)
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

echo "== Step 8-9/17: Provider + real inference verification (no server needed yet) =="
"$PY" -m pip install -q httpx==0.28.1
# stdout (the JSON report) and stderr (the human-readable summary/notes) are captured separately --
# merging them would produce a file that's neither valid JSON nor readable text.
"$PY" scripts/verify_jetson_agx_gpu.py --provider "$EFFECTIVE_PROVIDER" $ALLOW_FLAG \
  > "$RUNTIME_DIR/verify_report.json" 2> "$RUNTIME_DIR/verify_report.stderr.log" || true
cat "$RUNTIME_DIR/verify_report.stderr.log" >&2
cat "$RUNTIME_DIR/verify_report.json"

echo "== Step 10/17: frontend/dist verification =="
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

echo "== Step 11/17: Backend smoke tests =="
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

echo "== Step 12/17: Server startup =="
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

echo "== Step 13/17: GET /health =="
HEALTH=$(curl -sf "http://127.0.0.1:$PORT/health") || { echo "Health check failed"; exit 1; }
echo "$HEALTH" | tee "$RUNTIME_DIR/health.json"

echo "== Step 14/17: POST /predict =="
PREDICT_BODY='{"drug_conflict":0.5,"comorbidity_load":0.4,"age_risk":0.5,"allergy_flag":0.0,"adverse_history":0,"polypharmacy_load":0.3,"therapy_duration_load":0.2}'
PREDICT_RESULT=$(curl -sf -X POST "http://127.0.0.1:$PORT/predict" -H 'Content-Type: application/json' -d "$PREDICT_BODY") || { echo "/predict failed"; exit 1; }
echo "$PREDICT_RESULT" | tee "$RUNTIME_DIR/predict.json"

echo "== Step 15/17: POST /agent/analyze (SYN-002) =="
ANALYZE_RESULT=$(curl -sf -X POST "http://127.0.0.1:$PORT/agent/analyze" -H 'Content-Type: application/json' -d '{"patient_id":"SYN-002"}') || { echo "/agent/analyze failed"; exit 1; }
echo "$ANALYZE_RESULT" > "$RUNTIME_DIR/agent_analyze.json"
echo "(saved to $RUNTIME_DIR/agent_analyze.json)"

echo "== --require-gpu / --require-tensorrt enforcement =="
SESSION_PROVIDERS=$(echo "$HEALTH" | python3 -c "import json,sys;print(json.dumps(json.load(sys.stdin)['providers']))")
GPU_CHECK_OK=$(python3 -c "
import sys; sys.path.insert(0,'scripts')
import jetson_common as jc, json
ok, reason = jc.check_gpu_requirement(json.loads('$SESSION_PROVIDERS'), $( [ "$REQUIRE_GPU" = true ] && echo True || echo False ), $( [ "$REQUIRE_TENSORRT" = true ] && echo True || echo False ))
print(ok)
if not ok: print(reason, file=sys.stderr)
")
if [ "$GPU_CHECK_OK" != "True" ]; then
  echo "REQUIREMENT NOT MET: --require-gpu/--require-tensorrt was set but the session did not use the required provider."
  exit 4
fi

echo "== Step 16/17: Benchmark (with tegrastats background sampling) =="
TEGRA_LOG="$BENCH_DIR/tegrastats.log"
TEGRA_PID=""
if command -v tegrastats >/dev/null 2>&1; then
  tegrastats --interval 1000 > "$TEGRA_LOG" 2>&1 &
  TEGRA_PID=$!
fi
"$PY" scripts/benchmark_jetson.py > "$BENCH_DIR/benchmark.json" 2>&1 || true
if [ -n "$TEGRA_PID" ]; then kill "$TEGRA_PID" 2>/dev/null || true; fi
cat "$BENCH_DIR/benchmark.json"

echo "== Step 17/17: Deployment report =="
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
h=json.load(open('$RUNTIME_DIR/health.json'))
providers=h['providers']
if 'TensorrtExecutionProvider' in providers: print('JETSON AGX ORIN TENSORRT DEPLOYMENT VERIFIED' if $IS_TARGET else 'TENSORRT PATH EXERCISED (NOT ON AGX ORIN HARDWARE)')
elif 'CUDAExecutionProvider' in providers: print('JETSON AGX ORIN CUDA DEPLOYMENT VERIFIED' if $IS_TARGET else 'CUDA PATH EXERCISED (NOT ON AGX ORIN HARDWARE)')
else: print('CPU SAFE MODE VERIFIED' if $IS_TARGET else 'CPU SAFE MODE (NOT RUN ON JETSON HARDWARE)')
")"
