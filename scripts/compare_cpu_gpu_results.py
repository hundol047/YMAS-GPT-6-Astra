#!/usr/bin/env python3
"""CPU vs GPU result-equivalence check (Phase 25): runs every demo patient (SYN-001..005) through
the real ClinicalAgent under a CPU baseline, then again under CUDA and/or TensorRT (whichever
providers are actually available on this host), and compares:
  - risk_probability (must be within --tolerance of the CPU baseline)
  - risk_level (the high/low classification a clinician actually sees -- must NEVER differ)
  - alert types and training_counts (rule-engine output, provider-independent by construction --
    any difference here means something other than floating-point rounding changed, and is always
    a FAIL regardless of tolerance)

A GPU deployment is never reported as passing this check unless it was actually exercised: if
CUDA/TensorRT aren't available on this host, those providers are reported 'not available', not
silently skipped as if they matched.

Usage: python3 scripts/compare_cpu_gpu_results.py [--tolerance 0.02]
"""
import argparse, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))


def run_all_patients(provider):
    import importlib
    old = os.environ.get('SYNEX_PROVIDER')
    os.environ['SYNEX_PROVIDER'] = provider
    try:
        import app.services.risk_inference as risk_inference_module
        importlib.reload(risk_inference_module)
        from app.services.emr_adapter import DemoAdapter
        from app.services.clinical_agent import ClinicalAgent
        engine = risk_inference_module.RiskEngine()
        agent = ClinicalAgent(engine)
        results = {}
        for patient in DemoAdapter().list():
            a = agent.run(patient)
            results[patient.id] = {
                'risk_probability': a['risk']['risk_probability'],
                'risk_level': a['risk']['risk_level'],
                'training_counts': a['training_counts'],
                'alert_types': sorted(x['type'] for x in a['alerts']),
            }
        return engine, results
    finally:
        if old is None:
            os.environ.pop('SYNEX_PROVIDER', None)
        else:
            os.environ['SYNEX_PROVIDER'] = old


def compare(baseline, candidate, tolerance):
    failures = []
    per_patient = {}
    for pid in baseline:
        b, c = baseline[pid], candidate[pid]
        delta = abs(b['risk_probability'] - c['risk_probability'])
        per_patient[pid] = {'cpu': b, 'gpu': c, 'abs_delta': round(delta, 6)}
        if delta > tolerance:
            failures.append(f'{pid}: risk_probability delta {delta:.4f} exceeds tolerance {tolerance}')
        if b['risk_level'] != c['risk_level']:
            failures.append(f"{pid}: risk_level classification changed ({b['risk_level']} -> {c['risk_level']}) -- clinically meaningful, GPU deploy is a FAIL")
        if b['training_counts'] != c['training_counts'] or b['alert_types'] != c['alert_types']:
            failures.append(f'{pid}: rule-engine alerts/training_counts differ (should be provider-independent)')
    return per_patient, failures


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tolerance', type=float, default=0.02)
    args = ap.parse_args()

    import onnxruntime as ort
    available = ort.get_available_providers()

    cpu_engine, cpu_results = run_all_patients('cpu')
    report = {'tolerance': args.tolerance, 'cpu_baseline_model_sha256': cpu_engine.sha256, 'comparisons': {}}
    overall_fail = False

    for provider_env, provider_name in (('cuda', 'CUDAExecutionProvider'), ('tensorrt', 'TensorrtExecutionProvider')):
        if provider_name not in available:
            report['comparisons'][provider_env] = {'status': 'NOT_AVAILABLE', 'reason': f'{provider_name} not available on this host'}
            continue
        engine, results = run_all_patients(provider_env)
        if provider_name not in engine.session.get_providers():
            report['comparisons'][provider_env] = {'status': 'NOT_ACTUALLY_USED',
                                                     'reason': f'requested but session used {engine.session.get_providers()}'}
            continue
        per_patient, failures = compare(cpu_results, results, args.tolerance)
        status = 'FAIL' if failures else 'PASS'
        overall_fail = overall_fail or bool(failures)
        report['comparisons'][provider_env] = {'status': status, 'per_patient': per_patient, 'failures': failures}

    print(json.dumps(report, indent=2))
    if overall_fail:
        print('\nCPU/GPU result equivalence FAILED for at least one provider -- see failures above. '
              'Do not report that GPU deployment as verified.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
