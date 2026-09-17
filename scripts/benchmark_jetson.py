#!/usr/bin/env python3
"""Jetson AGX Orin inference benchmark: CPU vs CUDA vs TensorRT on the same real SynexAgent ONNX
model and the same input, with proper warm-up/short/sustained phases.

Every number in the report is a real measurement from this run on this machine -- there is no
placeholder or estimated figure. A provider that isn't actually available here (which is every
GPU provider on this x86 development container) is marked "not available on this host" and
simply excluded from the report rather than filled in with a guess.

tegrastats (RAM/CPU/GPU/EMC/temperature/power/clock) is sampled only when the `tegrastats` binary
exists, i.e. only on real Jetson hardware -- it is not simulated.

Usage: python3 scripts/benchmark_jetson.py [--warmup 10] [--short 50] [--sustained 100]
"""
import argparse, json, shutil, statistics, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import jetson_common as jc


def _node_counts(providers_used, fp16_enabled):
    """Same real-profiling technique as scripts/verify_jetson_agx_gpu.py -- a dedicated session
    with SessionOptions.enable_profiling=True, so a benchmark entry's execution_verified_provider
    reflects actual per-node execution proof, not just session provider registration."""
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
            Path(profile_path).unlink(missing_ok=True)
        return counts
    except Exception:
        return {}


def percentile(values, p):
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] if f == c else s[f] + (s[c] - s[f]) * (k - f)


def time_calls(fn, n):
    out = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t0) * 1000)
    return out


def _latency_stats(all_ms):
    return {'avg': round(statistics.mean(all_ms), 4), 'p50': round(percentile(all_ms, 50), 4),
            'p95': round(percentile(all_ms, 95), 4), 'p99': round(percentile(all_ms, 99), 4),
            'min': round(min(all_ms), 4), 'max': round(max(all_ms), 4)}


def bench_provider(provider_env, warmup, short, sustained):
    """Model microbenchmark: RiskEngine.predict() in a tight loop -- isolates the ONNX Runtime
    session's own inference cost from the rest of the request path (see bench_provider_app below
    for the whole-request figure).

    Reports requested_provider / actual_session_providers / execution_verified_provider as three
    separate fields (item #12): a benchmark entry is only ever labeled as measuring the REQUESTED
    provider if that provider was both the session's actual provider AND proven, via real ORT
    profiling, to have executed at least one node -- session registration alone (or a silent
    fallback to a different provider) is never enough to attach that label."""
    import onnxruntime as ort
    import os
    from app.services.risk_inference import RiskEngine
    from app.schemas import RiskFeatures
    requested_name = {'cpu': 'CPUExecutionProvider', 'cuda': 'CUDAExecutionProvider', 'tensorrt': 'TensorrtExecutionProvider'}[provider_env]
    if provider_env != 'cpu' and requested_name not in ort.get_available_providers():
        return {'provider': requested_name, 'requested_provider': requested_name, 'actual_session_providers': None,
                'execution_verified_provider': None, 'available': False, 'note': 'not available on this host -- no fabricated numbers'}
    os.environ['SYNEX_PROVIDER'] = provider_env
    t0 = time.perf_counter()
    engine = RiskEngine()
    cold_start_ms = (time.perf_counter() - t0) * 1000
    session_providers = engine.session.get_providers()
    node_counts = _node_counts(session_providers, engine.fp16_enabled)
    execution_verified_provider = next((p for p in session_providers if node_counts.get(p, 0) > 0), None)
    if session_providers[0] != requested_name or execution_verified_provider != requested_name:
        return {'provider': requested_name, 'requested_provider': requested_name, 'actual_session_providers': session_providers,
                'execution_verified_provider': execution_verified_provider, 'available': False,
                'note': (f'requested {requested_name} but execution-verified provider was {execution_verified_provider!r} '
                         '(session providers: %s) -- reporting as unavailable, never labeling this as a benchmark '
                         'of the requested provider without real per-node execution proof' % session_providers)}
    features = RiskFeatures(drug_conflict=.6, comorbidity_load=.4, age_risk=.5, allergy_flag=0,
                            adverse_history=0, polypharmacy_load=.3, therapy_duration_load=.2)
    call = lambda: engine.predict(features)
    time_calls(call, warmup)  # discarded, JIT/engine-build warm-up
    short_ms = time_calls(call, short)
    sustained_ms = time_calls(call, sustained)
    all_ms = short_ms + sustained_ms
    return {
        'provider': requested_name, 'requested_provider': requested_name, 'actual_session_providers': session_providers,
        'execution_verified_provider': execution_verified_provider, 'available': True, 'cold_start_ms': round(cold_start_ms, 3),
        'warmup_runs': warmup, 'short_runs': short, 'sustained_runs': sustained,
        'latency_ms': _latency_stats(all_ms),
        'throughput_per_sec': round(1000 / statistics.mean(all_ms), 2),
    }


def bench_provider_app(provider_env, warmup, short, sustained):
    """Application-level benchmark: the full ClinicalAgent.run() path (rule engine + risk model +
    Clinical Summary assembly) for one demo patient -- the equivalent of what POST /agent/analyze
    does, measured in-process rather than through the HTTP stack so it works standalone without a
    server already running. The same fallback-detection rule as bench_provider applies: if the
    engine actually ended up on a different provider than requested, this is reported as
    unavailable rather than silently benchmarked as the requested provider."""
    import onnxruntime as ort
    import os
    from app.services.risk_inference import RiskEngine
    from app.services.emr_adapter import DemoAdapter
    from app.services.clinical_agent import ClinicalAgent
    requested_name = {'cpu': 'CPUExecutionProvider', 'cuda': 'CUDAExecutionProvider', 'tensorrt': 'TensorrtExecutionProvider'}[provider_env]
    if provider_env != 'cpu' and requested_name not in ort.get_available_providers():
        return {'provider': requested_name, 'requested_provider': requested_name, 'actual_session_providers': None,
                'execution_verified_provider': None, 'available': False, 'note': 'not available on this host -- no fabricated numbers'}
    os.environ['SYNEX_PROVIDER'] = provider_env
    engine = RiskEngine()
    session_providers = engine.session.get_providers()
    node_counts = _node_counts(session_providers, engine.fp16_enabled)
    execution_verified_provider = next((p for p in session_providers if node_counts.get(p, 0) > 0), None)
    if session_providers[0] != requested_name or execution_verified_provider != requested_name:
        return {'provider': requested_name, 'requested_provider': requested_name, 'actual_session_providers': session_providers,
                'execution_verified_provider': execution_verified_provider, 'available': False,
                'note': f'requested {requested_name} but execution-verified provider was {execution_verified_provider!r} -- reporting as unavailable'}
    agent = ClinicalAgent(engine)
    patient = DemoAdapter().get('SYN-002')
    call = lambda: agent.run(patient)
    time_calls(call, warmup)
    short_ms = time_calls(call, short)
    sustained_ms = time_calls(call, sustained)
    all_ms = short_ms + sustained_ms
    return {'provider': requested_name, 'requested_provider': requested_name, 'actual_session_providers': session_providers,
            'execution_verified_provider': execution_verified_provider, 'available': True, 'patient': 'SYN-002',
            'latency_ms': _latency_stats(all_ms), 'throughput_per_sec': round(1000 / statistics.mean(all_ms), 2)}


def tegrastats_sample():
    if not shutil.which('tegrastats'):
        return {'available': False, 'note': 'tegrastats not present -- not real Jetson hardware, no simulated sample'}
    try:
        p = subprocess.run(['tegrastats', '--interval', '500', '--count', '1'], capture_output=True, text=True, timeout=5)
        return {'available': True, 'raw': p.stdout.strip()}
    except Exception as e:
        return {'available': False, 'error': str(e)}


def power_mode():
    if not shutil.which('nvpmodel'):
        return None
    try:
        return subprocess.run(['nvpmodel', '-q'], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception as e:
        return f'ERROR: {e}'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--warmup', type=int, default=10)
    ap.add_argument('--short', type=int, default=50)
    ap.add_argument('--sustained', type=int, default=100)
    args = ap.parse_args()
    report = {
        'power_mode_before_benchmark': power_mode(),
        'tegrastats_sample': tegrastats_sample(),
        'model_microbenchmark': [bench_provider(p, args.warmup, args.short, args.sustained) for p in ('cpu', 'cuda', 'tensorrt')],
        'application_benchmark': [bench_provider_app(p, args.warmup, args.short, args.sustained) for p in ('cpu', 'cuda', 'tensorrt')],
        'note': 'Only measured numbers are reported. Providers unavailable on this host (or that '
                'silently fell back to a different provider than requested) are marked '
                'available:false and excluded from latency figures, never estimated. A GPU provider '
                'is NOT assumed faster than CPU for this small (7-feature) model -- host/device '
                'transfer overhead can make it slower; report whatever was actually measured.',
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
