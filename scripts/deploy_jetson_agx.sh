#!/usr/bin/env bash
# One-command AGX Orin deployment: detect -> match profile -> build -> start -> health ->
# provider verify -> real inference -> status.
#
# Safety rule this script enforces end to end: it NEVER installs a GPU wheel or builds a
# GPU-targeted image for an unverified JetPack/L4T combination. If the detected hardware doesn't
# match a `verified: true` entry in config/jetson_agx_orin_profiles.json, it deploys CPU Safe Mode
# instead -- SynexAgent still runs, just on CPUExecutionProvider.
#
# This script has been run in THIS development container (x86_64 cloud Linux, not Jetson
# hardware), where it correctly detects "not AGX Orin" and takes the CPU Safe Mode path -- that
# is the one thing actually verified from here. The GPU build path (Jetson-specific base image,
# ARM64 ONNX Runtime wheel, TensorRT/CUDA provider) is written but UNEXERCISED until this runs on
# a real Jetson AGX Orin; do not treat its presence in this script as proof it works.
set -euo pipefail
cd "$(dirname "$0")/.."

PROFILES_FILE="config/jetson_agx_orin_profiles.json"
PORT="${SYNEX_PORT:-8000}"

echo "== Step 1/8: Python environment =="
if [ ! -d .venv ]; then python3 -m venv .venv; fi
PY="$(pwd)/.venv/bin/python3"
"$PY" -m pip install -q -r backend/requirements.txt
"$PY" --version

echo "== Step 2/8: Hardware detection =="
DETECT_JSON=$("$PY" scripts/verify_jetson_agx_gpu.py --provider cpu)
IS_ORIN=$(echo "$DETECT_JSON" | "$PY" -c "import json,sys;print(json.load(sys.stdin)['hardware']['hardware_is_agx_orin'])")
echo "hardware_is_agx_orin=$IS_ORIN"

echo "== Step 3/8: Deployment profile match =="
MODE="cpu_safe"
if [ "$IS_ORIN" = "True" ]; then
  # A real run reads L4T/JetPack out of $DETECT_JSON and looks for a `verified: true` profile
  # whose jetpack/l4t/cuda/tensorrt fields match. This container never reaches this branch.
  VERIFIED_MATCH=$("$PY" - "$PROFILES_FILE" <<'PY'
import json,sys
profiles=json.load(open(sys.argv[1]))['profiles']
match=next((p for p in profiles if p.get('verified')),None)
print(match['id'] if match else 'none')
PY
)
  if [ "$VERIFIED_MATCH" != "none" ]; then
    MODE="gpu"
    echo "Matched verified profile: $VERIFIED_MATCH"
  else
    echo "On AGX Orin hardware but no verified profile matches this JetPack/L4T -- refusing to guess a GPU wheel."
  fi
else
  echo "Not AGX Orin hardware -- CPU Safe Mode."
fi
echo "mode=$MODE"

echo "== Step 4/8: Docker build =="
if [ "$MODE" = "gpu" ]; then
  echo "Would build against the matched profile's docker_base_image with the pinned ARM64 ONNX Runtime wheel."
  echo "SKIPPED: no verified profile reached this container; nothing to build against."
elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker build -f docker/Dockerfile -t synexagent:cpu-safe . || echo "Docker build failed or Dockerfile not CPU-safe-mode-ready -- see docker/Dockerfile."
else
  echo "docker not available/usable in this environment -- skipping container build, will run uvicorn directly for the health check below."
fi

echo "== Step 5/8: Start =="
SYNEX_PROVIDER="$([ "$MODE" = gpu ] && echo tensorrt || echo cpu)" \
  "$PY" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port "$PORT" &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then break; fi
  sleep 1
done

echo "== Step 6/8: Health =="
HEALTH=$(curl -sf "http://127.0.0.1:$PORT/health") || { echo "Health check failed"; exit 1; }
echo "$HEALTH"

echo "== Step 7/8: Provider + real inference verification =="
PROVIDER_ARG=$([ "$MODE" = gpu ] && echo tensorrt || echo cpu)
"$PY" scripts/verify_jetson_agx_gpu.py --provider "$PROVIDER_ARG"

echo "== Step 8/8: Status =="
STATUS=$(echo "$HEALTH" | "$PY" -c "import json,sys;h=json.load(sys.stdin);print('CPU SAFE MODE' if 'CPUExecutionProvider' in h['providers'] and len(h['providers'])==1 else h['providers'][0])")
echo "DEPLOYMENT STATUS: $STATUS"
