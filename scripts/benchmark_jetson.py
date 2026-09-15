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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))


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


def bench_provider(provider_env, warmup, short, sustained):
    import onnxruntime as ort
    import os
    from app.services.risk_inference import RiskEngine
    from app.schemas import RiskFeatures
    requested_name = {'cpu': 'CPUExecutionProvider', 'cuda': 'CUDAExecutionProvider', 'tensorrt': 'TensorrtExecutionProvider'}[provider_env]
    if provider_env != 'cpu' and requested_name not in ort.get_available_providers():
        return {'provider': requested_name, 'available': False, 'note': 'not available on this host -- no fabricated numbers'}
    os.environ['SYNEX_PROVIDER'] = provider_env
    t0 = time.perf_counter()
    engine = RiskEngine()
    cold_start_ms = (time.perf_counter() - t0) * 1000
    if engine.session.get_providers()[0] != requested_name:
        return {'provider': requested_name, 'available': False,
                'note': f'requested but session actually used {engine.session.get_providers()[0]} -- reporting as unavailable, not silently benchmarking the fallback as if it were this provider'}
    features = RiskFeatures(drug_conflict=.6, comorbidity_load=.4, age_risk=.5, allergy_flag=0,
                            adverse_history=0, polypharmacy_load=.3, therapy_duration_load=.2)
    call = lambda: engine.predict(features)
    time_calls(call, warmup)  # discarded, JIT/engine-build warm-up
    short_ms = time_calls(call, short)
    sustained_ms = time_calls(call, sustained)
    all_ms = short_ms + sustained_ms
    return {
        'provider': requested_name, 'available': True, 'cold_start_ms': round(cold_start_ms, 3),
        'warmup_runs': warmup, 'short_runs': short, 'sustained_runs': sustained,
        'latency_ms': {'avg': round(statistics.mean(all_ms), 4), 'p50': round(percentile(all_ms, 50), 4),
                       'p95': round(percentile(all_ms, 95), 4), 'min': round(min(all_ms), 4), 'max': round(max(all_ms), 4)},
        'throughput_per_sec': round(1000 / statistics.mean(all_ms), 2),
    }


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
        'providers': [bench_provider(p, args.warmup, args.short, args.sustained) for p in ('cpu', 'cuda', 'tensorrt')],
        'note': 'Only measured numbers are reported. Providers unavailable on this host are marked '
                'available:false and excluded from latency figures, never estimated.',
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
