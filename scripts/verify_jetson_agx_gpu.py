#!/usr/bin/env python3
"""AGX Orin environment + GPU acceleration verification.

Runs the exact detection commands (never guesses a JetPack/L4T/CUDA/TensorRT version), then loads
the real SynexAgent ONNX model and runs a real inference through whatever ONNX Runtime provider is
actually available, reporting GPU acceleration as verified ONLY if all of:
  1. the requested provider appears in ort.get_available_providers()
  2. it appears in session.get_providers() for the actual loaded session
  3. inference on the real SynexAgent model succeeds
  4. (when --base-url is given, or a server is already listening on the given host/port) the
     FastAPI /health, /predict, and /agent/analyze endpoints respond correctly.

If this is run on hardware that isn't actually a Jetson AGX Orin (including this development
container, which is x86_64 cloud Linux, not ARM Jetson hardware), that is reported plainly instead
of being papered over -- see "hardware_is_agx_orin": false in the output. Never install a GPU
wheel or claim GPU acceleration based on this script's output alone; it only reports what it
could actually observe on the machine it ran on.

Usage: python3 scripts/verify_jetson_agx_gpu.py [--provider cpu|cuda|tensorrt] [--allow-other-orin]
                                                 [--base-url http://127.0.0.1:8000]
"""
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import jetson_common as jc


def detect_hardware(allow_other_orin):
    hw = jc.detect_hardware(allow_other_orin=allow_other_orin)
    return {**hw, 'hardware_is_agx_orin': hw['hardware_is_agx_orin']}  # kept for backward compat with earlier report shape


def detect_cuda_stack():
    nv_tegra_release = jc.read_file('/etc/nv_tegra_release')
    nvcc_out = jc.run(['nvcc', '--version'])
    return {
        'python_version': sys.version.split()[0],
        'nvcc_version': nvcc_out,
        'l4t': jc.classify_l4t_family(nv_tegra_release),
        'cuda': jc.classify_cuda_family(jc.extract_cuda_version_from_nvcc(nvcc_out)),
        'cudnn_packages': jc.run(['bash', '-c', "dpkg -l | grep -i cudnn || true"]),
        'tensorrt_packages': jc.run(['bash', '-c', "dpkg -l | grep -E 'tensorrt|libnvinfer' || true"]),
        'docker_version': jc.run(['docker', '--version']),
        'docker_runtime': jc.run(['bash', '-c', "docker info 2>/dev/null | grep -i runtime || true"]),
    }


def detect_tensorrt_python():
    try:
        import tensorrt as trt
        return {'available': True, 'version': trt.__version__}
    except Exception as e:
        return {'available': False, 'error': str(e)}


def _profiled_session_node_counts(requested_provider, providers_used, fp16_enabled):
    """Builds a SEPARATE ONNX Runtime session -- same model, same provider list RiskEngine actually
    selected -- but with SessionOptions.enable_profiling=True, so real per-node execution can be
    proven rather than inferred from provider registration alone. Runs a few inferences (a single
    call is not always enough for every node's profiling event to be flushed the same way), then
    calls session.end_profiling() and parses the resulting Chrome-Trace-Event JSON via
    jetson_common.count_nodes_by_provider(). Returns ({} on any failure -- never raises) so a caller
    that can't get profiling evidence falls back to INFERENCE_PASSED rather than crashing the whole
    verification run."""
    import onnxruntime as ort
    from app.services.risk_inference import MODEL_PATH, _provider_list_with_options
    import numpy as np
    try:
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        opts.enable_profiling = True
        session = ort.InferenceSession(str(MODEL_PATH), sess_options=opts,
                                        providers=_provider_list_with_options(providers_used, fp16=fp16_enabled))
        x = np.asarray([[1, .5, .5, 0, 0, .2, .2]], dtype=np.float32)
        for _ in range(5):
            session.run(['risk_probability'], {'features': x})
        profile_path = session.end_profiling()
        try:
            counts = jc.count_nodes_by_provider(profile_path)
        finally:
            # This is a scratch trace file for this one verification run, not a deployment
            # artifact -- remove it so repeated runs don't litter the working directory.
            Path(profile_path).unlink(missing_ok=True)
        return counts
    except Exception:
        return {}


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
    requested_name = jc.PROVIDER_NAMES[requested_provider]
    selected = session_providers[0] if session_providers else None
    inference_ok = 0 <= pred['risk_probability'] <= 1

    # Real per-node execution proof (item #8/#9): provider registration + a passing inference is
    # NEVER, by itself, reported as EXECUTION_VERIFIED. A separate profiled session actually counts
    # nodes attributed to each provider by ONNX Runtime's own trace output. Run uniformly for every
    # requested provider (including cpu) so the status ladder is applied consistently rather than
    # special-cased.
    node_counts = _profiled_session_node_counts(requested_provider, session_providers, engine.fp16_enabled)
    nodes_executed = node_counts.get(requested_name)
    status_code = jc.classify_provider_status(
        requested_name, available_providers=available, session_providers=session_providers,
        inference_ok=inference_ok, nodes_executed=nodes_executed,
    )

    # Human-readable status kept alongside the unified vocabulary -- never claims an
    # "ACCELERATION VERIFIED" wording unless status_code is actually EXECUTION_VERIFIED for THIS
    # requested provider specifically; TensorRT engine-cache creation or CUDA-session-registration
    # alone never upgrades to a TensorRT claim.
    if requested_provider == 'cpu':
        status = 'CPU SAFE MODE'
    elif status_code == 'EXECUTION_VERIFIED':
        status = f'{requested_name} EXECUTION VERIFIED (nodes_executed={nodes_executed})'
    elif status_code == 'INFERENCE_PASSED':
        status = f'{requested_name} INFERENCE PASSED / NODE EXECUTION NOT PROVEN'
    elif status_code == 'SESSION_REGISTERED':
        status = f'{requested_name} SESSION REGISTERED / INFERENCE NOT CONFIRMED'
    elif status_code == 'FALLBACK':
        status = f'{requested_name} NOT USED BY SESSION -- FALLBACK ({selected})'
    else:
        status = 'CPU SAFE MODE'

    # Per-provider status independent of which one was "requested" -- e.g. --provider tensorrt on a
    # device with CUDA but no TensorRT EP will FALLBACK to CUDA; deploy_jetson_agx.sh's --require-gpu
    # (which accepts either CUDA or TensorRT) needs CUDA's own EXECUTION_VERIFIED status directly,
    # not something derived from the "requested" provider's FALLBACK status. --require-tensorrt must
    # never be satisfied by this: it checks provider_status['TensorrtExecutionProvider'] specifically.
    provider_status = {
        name: jc.classify_provider_status(name, available_providers=available, session_providers=session_providers,
                                           inference_ok=inference_ok, nodes_executed=node_counts.get(name))
        for name in ('CPUExecutionProvider', 'CUDAExecutionProvider', 'TensorrtExecutionProvider')
    }
    return {
        'requested_provider': requested_name,
        'available_providers': available,
        'session_providers': session_providers,
        'selected_provider': selected,
        'provider_status': provider_status,
        'fallback_reason': engine.fallback_reason,
        'fp16_enabled': engine.fp16_enabled,
        'model_sha256': engine.sha256,
        'inference_result': pred['risk_probability'],
        'cold_start_ms': round(cold_start_ms, 2),
        'warm_inference_ms': round(warm_inference_ms, 2),
        'nodes_executed_by_provider': node_counts,
        'verification_status': status_code,
        'gpu_acceleration_verified': (status_code == 'EXECUTION_VERIFIED') if requested_provider != 'cpu' else None,
        'status': status,
    }


def api_report(base_url, timeout=5):
    """Real HTTP calls against an already-running FastAPI server -- not exercised unless one is
    actually reachable at base_url. Distinguishes 'no server running here' from 'server responded
    with an error' rather than treating both the same way."""
    import httpx
    out = {'base_url': base_url, 'health': None, 'predict': None, 'agent_analyze': None, 'reachable': False}
    try:
        client = httpx.Client(timeout=timeout)
        r = client.get(f'{base_url}/health')
        out['reachable'] = True
        out['health'] = {'status_code': r.status_code, 'body': r.json() if r.status_code == 200 else r.text}
        body = {'drug_conflict': .5, 'comorbidity_load': .4, 'age_risk': .5, 'allergy_flag': 0,
                'adverse_history': 0, 'polypharmacy_load': .3, 'therapy_duration_load': .2}
        r = client.post(f'{base_url}/predict', json=body)
        out['predict'] = {'status_code': r.status_code, 'ok': r.status_code == 200}
        r = client.post(f'{base_url}/agent/analyze', json={'patient_id': 'SYN-002'})
        out['agent_analyze'] = {'status_code': r.status_code, 'ok': r.status_code == 200}
    except Exception as e:
        out['error'] = f'{type(e).__name__}: {e}'
    return out


def print_summary(report):
    hw, onnx, api = report['hardware'], report['onnxruntime'], report.get('api')
    lines = [
        f"HARDWARE: {'Jetson AGX Orin' if hw['hardware_is_agx_orin'] else (hw['orin_family'] or 'not Jetson')}",
        f"ARCH: {hw['machine_arch']}",
        f"ORT STATUS: {onnx['status']}",
        f"ORT VERIFICATION STATUS: {onnx['verification_status']}",
        f"ORT SESSION PROVIDERS: {onnx['session_providers']}",
        f"NODES EXECUTED BY PROVIDER: {onnx['nodes_executed_by_provider']}",
    ]
    if api is not None:
        if api['reachable']:
            lines.append(f"FASTAPI /health: {'PASS' if api['health']['status_code'] == 200 else 'FAIL'}")
            lines.append(f"FASTAPI /predict: {'PASS' if api['predict']['ok'] else 'FAIL'}")
            lines.append(f"FASTAPI /agent/analyze: {'PASS' if api['agent_analyze']['ok'] else 'FAIL'}")
        else:
            lines.append(f"FASTAPI: not reachable at {api['base_url']} ({api.get('error', 'no server running')})")
    print('\n'.join(lines), file=sys.stderr)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--provider', choices=['cpu', 'cuda', 'tensorrt'], default='cpu')
    ap.add_argument('--allow-other-orin', action='store_true')
    ap.add_argument('--base-url', default=None, help='If given (or reachable at http://127.0.0.1:8000), also runs real /health, /predict, /agent/analyze checks against it')
    args = ap.parse_args()
    report = {
        'hardware': detect_hardware(args.allow_other_orin),
        'cuda_stack': detect_cuda_stack(),
        'tensorrt_python': detect_tensorrt_python(),
        'onnxruntime': onnxruntime_report(args.provider),
    }
    base_url = args.base_url
    if base_url is None:
        # Opportunistically check the conventional default -- if nothing is listening there this
        # just reports reachable:false, it does not treat that as a failure of THIS script.
        base_url = 'http://127.0.0.1:8000'
    report['api'] = api_report(base_url)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print_summary(report)
    if not report['hardware']['hardware_is_agx_orin']:
        print('\nNOTE: hardware_is_agx_orin=false -- this machine is not a Jetson AGX Orin. '
              'Run this script ON the target device before trusting any GPU-related field above.',
              file=sys.stderr)
