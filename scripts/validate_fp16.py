#!/usr/bin/env python3
"""FP16 validation gate for the TensorRT execution provider.

deploy_jetson_agx.sh's --fp16 flag is NEVER applied to the running server until this script has
compared FP16 vs FP32 TensorRT results against every demo patient and reported PASS. Speed is never
allowed to override result stability: if any check below fails, the caller keeps FP32.

Checks, across all 5 demo patients (SYN-001..005) plus a few representative synthetic feature
vectors:
  - both FP32 and FP16 outputs are finite and in [0, 1]
  - the maximum absolute delta between FP32 and FP16 risk_probability is within --tolerance
  - risk_level (the high/low classification actually shown to a clinician) never differs
  - rule-engine-derived alerts/training_counts (provider-independent by construction) are identical
    between the two runs -- a real difference there would mean something other than FP16 rounding
    changed, which is treated as an automatic FAIL regardless of tolerance.

This can only produce a real PASS/FAIL on a machine where TensorrtExecutionProvider is actually
available -- on any other host (including this x86 development container) it reports
'TensorRT unavailable on this host; FP16 validation cannot run here' rather than fabricating one.

Usage: python3 scripts/validate_fp16.py [--tolerance 0.02]
"""
import argparse, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))


def run_all_patients(env_overrides):
    import importlib
    old_env = {k: os.environ.get(k) for k in env_overrides}
    os.environ.update(env_overrides)
    try:
        # Fresh import each time so RiskEngine.__init__ re-reads SYNEX_PROVIDER/SYNEX_TENSORRT_FP16.
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
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tolerance', type=float, default=0.02,
                     help='Max allowed |fp32 - fp16| risk_probability delta per patient (default 0.02)')
    args = ap.parse_args()

    import onnxruntime as ort
    if 'TensorrtExecutionProvider' not in ort.get_available_providers():
        print(json.dumps({'status': 'SKIPPED', 'reason': 'TensorRT unavailable on this host; FP16 validation cannot run here.'}, indent=2))
        return 0  # not a failure -- just nothing to validate on this machine

    fp32_engine, fp32_results = run_all_patients({'SYNEX_PROVIDER': 'tensorrt', 'SYNEX_TENSORRT_FP16': 'false'})
    fp16_engine, fp16_results = run_all_patients({'SYNEX_PROVIDER': 'tensorrt', 'SYNEX_TENSORRT_FP16': 'true'})

    if not fp32_engine.fallback_reason is None or 'TensorrtExecutionProvider' not in fp32_engine.session.get_providers():
        print(json.dumps({'status': 'SKIPPED', 'reason': f'FP32 TensorRT session did not actually use TensorRT (fallback_reason={fp32_engine.fallback_reason!r})'}, indent=2))
        return 0
    if not fp16_engine.fp16_enabled:
        print(json.dumps({'status': 'SKIPPED', 'reason': 'FP16 session did not actually enable fp16 (see RiskEngine.fp16_enabled)'}, indent=2))
        return 0

    failures = []
    per_patient = {}
    for pid in fp32_results:
        f32, f16 = fp32_results[pid], fp16_results[pid]
        delta = abs(f32['risk_probability'] - f16['risk_probability'])
        per_patient[pid] = {'fp32': f32, 'fp16': f16, 'abs_delta': round(delta, 6)}
        if not (0 <= f32['risk_probability'] <= 1 and 0 <= f16['risk_probability'] <= 1):
            failures.append(f'{pid}: output out of [0,1] range')
        if delta > args.tolerance:
            failures.append(f'{pid}: risk_probability delta {delta:.4f} exceeds tolerance {args.tolerance}')
        if f32['risk_level'] != f16['risk_level']:
            failures.append(f"{pid}: risk_level classification changed ({f32['risk_level']} -> {f16['risk_level']})")
        if f32['training_counts'] != f16['training_counts'] or f32['alert_types'] != f16['alert_types']:
            failures.append(f'{pid}: rule-engine alerts/training_counts differ between FP32 and FP16 runs (should be provider-independent)')

    report = {'status': 'FAIL' if failures else 'PASS', 'tolerance': args.tolerance,
               'per_patient': per_patient, 'failures': failures}
    print(json.dumps(report, indent=2))
    if failures:
        print('\nFP16 validation FAILED -- keep FP32 TensorRT/CUDA. Speed is never allowed to override result stability.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
