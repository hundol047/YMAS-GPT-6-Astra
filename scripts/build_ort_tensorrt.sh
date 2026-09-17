#!/usr/bin/env bash
# Optional TensorRT-execution-provider source build of ONNX Runtime, for when a pre-built ARM64
# wheel with the TensorRT EP compiled in isn't available for the detected JetPack. Only ever
# invoked when the caller explicitly passes --build-ort-tensorrt to deploy_jetson_agx.sh -- this is
# NOT part of the default --auto flow, since a source build is slow, uses real disk/memory, and
# is unnecessary whenever CUDA-only acceleration (no TensorRT) is enough.
#
# This script has NEVER been run to completion anywhere -- it has no ARM64/CUDA/TensorRT toolchain
# available in this development container to build against. Prerequisite checks below are real
# (they check for actual files/binaries), but the build itself is UNEXERCISED until run on a real
# Jetson AGX Orin with CUDA + cuDNN + TensorRT + cmake + a C/C++ toolchain installed.
set -euo pipefail
cd "$(dirname "$0")/.."

ORT_REPO_DIR="${ORT_REPO_DIR:-runtime/onnxruntime-src}"
ORT_VERSION="${ORT_VERSION:-}"  # if unset, whatever branch/tag is already checked out is used
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
# AGX Orin (and Orin NX/Nano) are all compute capability 8.7 (sm_87) -- a fixed hardware fact for
# this SoC family, not a guess. Overridable via env for a different target GPU.
CMAKE_CUDA_ARCHITECTURES="${CMAKE_CUDA_ARCHITECTURES:-87}"

echo "== ONNX Runtime TensorRT EP source build: prerequisite check =="
fail=0
check_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "MISSING: $1"
    fail=1
  else
    echo "found: $1 ($("$1" --version 2>&1 | head -1))"
  fi
}
check_cmd cmake
check_cmd git
check_cmd gcc
check_cmd g++

if [ ! -d "$CUDA_HOME" ]; then
  echo "MISSING: CUDA toolkit not found at CUDA_HOME=$CUDA_HOME"
  fail=1
else
  echo "found: CUDA toolkit at $CUDA_HOME"
fi

CUDNN_HEADER=$(find /usr/include /usr/local -maxdepth 4 -iname 'cudnn*.h' 2>/dev/null | head -1)
if [ -z "$CUDNN_HEADER" ]; then
  echo "MISSING: cuDNN headers not found (searched /usr/include, /usr/local)"
  fail=1
else
  echo "found: cuDNN header at $CUDNN_HEADER"
fi

TRT_HEADER=$(find /usr/include /usr/local -maxdepth 4 -iname 'NvInfer.h' 2>/dev/null | head -1)
if [ -z "$TRT_HEADER" ]; then
  echo "MISSING: TensorRT headers (NvInfer.h) not found"
  fail=1
else
  echo "found: TensorRT header at $TRT_HEADER"
fi

FREE_DISK_KB=$(df --output=avail "$(pwd)" | tail -1 | tr -d ' ')
if [ -n "$FREE_DISK_KB" ] && [ "$FREE_DISK_KB" -lt 15000000 ]; then
  echo "WARNING: less than ~15GB free disk (${FREE_DISK_KB}KB) -- an ORT source build commonly needs more than that"
fi

FREE_MEM_KB=$(awk '/MemAvailable/{print $2}' /proc/meminfo 2>/dev/null || echo '')
PARALLEL_JOBS=2
if [ -n "$FREE_MEM_KB" ] && [ "$FREE_MEM_KB" -lt 8000000 ]; then
  echo "Low available memory (${FREE_MEM_KB}KB) -- limiting build parallelism to avoid OOM (--parallel $PARALLEL_JOBS)"
else
  PARALLEL_JOBS=$(nproc 2>/dev/null || echo 2)
fi

if [ "$fail" -ne 0 ]; then
  echo ""
  echo "TENSORRT SOURCE BUILD PREREQUISITES NOT MET -- refusing to start the build."
  echo "Install the missing items above on the target Jetson device, then re-run with --build-ort-tensorrt."
  exit 1
fi

if [ ! -d "$ORT_REPO_DIR" ]; then
  echo "== Cloning microsoft/onnxruntime into $ORT_REPO_DIR =="
  git clone --recursive https://github.com/microsoft/onnxruntime "$ORT_REPO_DIR"
fi
cd "$ORT_REPO_DIR"
if [ -n "$ORT_VERSION" ]; then
  git checkout "$ORT_VERSION"
fi

echo "== Build options (see ./build.sh --help for this checkout's actual supported flags -- do not"
echo "   assume flags from an older/different ORT version's documentation) =="
./build.sh --help | head -40 || true

echo ""
echo "== Starting build (--parallel $PARALLEL_JOBS, CMAKE_CUDA_ARCHITECTURES=$CMAKE_CUDA_ARCHITECTURES) =="
echo "This step is UNEXERCISED from this development container -- it requires a real CUDA/cuDNN/"
echo "TensorRT-equipped Jetson AGX Orin, which is not what this script is running on right now."
./build.sh --config Release --build_wheel --use_cuda --use_tensorrt \
  --cuda_home "$CUDA_HOME" --tensorrt_home "$(dirname "$(dirname "$TRT_HEADER")")" \
  --parallel "$PARALLEL_JOBS" \
  --cmake_extra_defines "CMAKE_CUDA_ARCHITECTURES=$CMAKE_CUDA_ARCHITECTURES" \
  --skip_tests

echo ""
echo "Build finished. The resulting wheel is under build/Linux/Release/dist/*.whl -- install it into"
echo "the target venv, then run scripts/verify_jetson_agx_gpu.py --provider tensorrt to confirm"
echo "TensorrtExecutionProvider actually loads and produces a real inference before relying on it."
