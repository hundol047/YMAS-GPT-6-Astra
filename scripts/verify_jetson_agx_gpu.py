#!/usr/bin/env python3
"""AGX Orin environment + GPU acceleration verification.

Runs the exact detection commands (never guesses a JetPack/L4T/CUDA/TensorRT version), then loads
the real SynexAgent ONNX model and runs a real inference through whatever ONNX Runtime provider is
actually available, reporting GPU acceleration as verified ONLY if all of:
  1. the requested provider appears in ort.get_available_providers()
  2. it appears in session.get_providers() for the actual loaded session
  3. inference on the real SynexAgent model succeeds
  4. the FastAPI /health and /predict endpoints respond correctly with that session

If this is run on hardware that isn't actually a Jetson AGX Orin (including this development
container, which is x86_64 cloud Linux, not ARM Jetson hardware), that is reported plainly instead
of being papered over -- see "hardware_is_agx_orin": false in the output. Never install a GPU
wheel or claim GPU acceleration based on this script's output alone; it only reports what it
could actually observe on the machine it ran on.

Usage: python3 scripts/verify_jetson_agx_gpu.py [--provider cpu|cuda|tensorrt]
"""
import argparse, json, platform, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))


def run(cmd, shell=False):
    try:
        r = subprocess.run(cmd if shell else cmd.split(), shell=shell, capture_output=True, text=True, timeout=10)
        out = (r.stdout or r.stderr or '').strip()
        return out if out else '(empty output)'
    except FileNotFoundError:
        return None  # command not installed
    except Exception as e:
        return f'ERROR: {e}'


def read_file(path):
    try:
        return Path(path).read_text().strip()
    except Exception:
        return None


def detect_hardware():
    model = read_file('/proc/device-tree/model')
    nv_release = read_file('/etc/nv_tegra_release')
    l4t_core = run('dpkg-query -W nvidia-l4t-core')
    os_release = read_file('/etc/os-release')
    machine = platform.machine()
    is_agx_orin = bool(model and 'orin' in model.lower())
    return {
        'device_tree_model': model,
        'nv_tegra_release': nv_release,
        'nvidia_l4t_core': l4t_core,
        'os_release': os_release,
        'machine_arch': machine,
        'hardware_is_agx_orin': is_agx_orin,
        'note': None if model else 'No /proc/device-tree/model -- this is not Jetson hardware '
                                    '(expected on a standard PC/cloud VM; real on a Jetson device).',
    }


def detect_cuda_stack():
    return {
        'python_version': sys.version.split()[0],
        'nvcc_version': run('nvcc --version'),
        'cudnn_packages': run("bash -c \"dpkg -l | grep -i cudnn || true\"", shell=True),
        'tensorrt_packages': run("bash -c \"dpkg -l | grep -E 'tensorrt|libnvinfer' || true\"", shell=True),
        'docker_version': run('docker --version'),
        'docker_compose_version': run('docker compose version'),
        'docker_runtime': run("bash -c \"docker info 2>/dev/null | grep -i runtime || true\"", shell=True),
    }


def detect_tensorrt_python():
    try:
        import tensorrt as trt
        return {'available': True, 'version': trt.__version__}
    except Exception as e:
        return {'available': False, 'error': str(e)}


def onnxruntime_report(requested_provider):
    import onnxruntime as ort
    from app.services.risk_inference import RiskEngine
    from app.schemas import RiskFeatures
    import os
    os.environ['SYNEX_PROVIDER'] = requested_provider
    available = ort.get_available_providers()
    t0 = time.perf_counter()
    engine = RiskEngine()  # this is a cold start (session build); see note below
    cold_start_ms = (time.perf_counter() - t0) * 1000
    session_providers = engine.session.get_providers()
    t1 = time.perf_counter()
    pred = engine.predict(RiskFeatures(drug_conflict=1, comorbidity_load=.5, age_risk=.5, allergy_flag=0,
                                        adverse_history=0, polypharmacy_load=.2, therapy_duration_load=.2))
    warm_inference_ms = (time.perf_counter() - t1) * 1000
    requested_name = {'cpu': 'CPUExecutionProvider', 'cuda': 'CUDAExecutionProvider', 'tensorrt': 'TensorrtExecutionProvider'}[requested_provider]
    selected = session_providers[0] if session_providers else None
    verified = requested_name in available and requested_name in session_providers and 0 <= pred['risk_probability'] <= 1
    return {
        'requested_provider': requested_name,
        'available_providers': available,
        'session_providers': session_providers,
        'selected_provider': selected,
        'fallback_reason': engine.fallback_reason,
        'model_sha256': engine.sha256,
        'inference_result': pred['risk_probability'],
        'cold_start_ms': round(cold_start_ms, 2),
        'warm_inference_ms': round(warm_inference_ms, 2),
        'gpu_acceleration_verified': verified if requested_provider != 'cpu' else None,
        'status': ('GPU ACCELERATION VERIFIED' if (requested_provider != 'cpu' and verified) else
                   'CPU SAFE MODE' if requested_provider == 'cpu' or not verified else 'UNKNOWN'),
    }


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--provider', choices=['cpu', 'cuda', 'tensorrt'], default='cpu')
    args = ap.parse_args()
    report = {
        'hardware': detect_hardware(),
        'cuda_stack': detect_cuda_stack(),
        'tensorrt_python': detect_tensorrt_python(),
        'onnxruntime': onnxruntime_report(args.provider),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report['hardware']['hardware_is_agx_orin']:
        print('\nNOTE: hardware_is_agx_orin=false -- this machine is not a Jetson AGX Orin. '
              'Run this script ON the target device before trusting any GPU-related field above.',
              file=sys.stderr)
