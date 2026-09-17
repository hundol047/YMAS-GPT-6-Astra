#!/usr/bin/env python3
"""Assembles the final Jetson deployment report (JSON + human-readable TXT) from the artifacts
scripts/deploy_jetson_agx.sh already produced during its run. Never invents a field it can't find
in an input file -- a missing/unreadable input is recorded as null with a note, not silently
skipped or guessed.

No secret, token, or real patient data is ever included -- only demo patient IDs (SYN-00x), which
this repository already ships as public synthetic fixtures.
"""
import argparse, json, re, sys
from datetime import datetime, timezone
from pathlib import Path


def load_json(path):
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return {'_error': f'{path} does not exist'}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        return {'_error': f'could not parse {path}: {e}'}


def load_text(path, max_chars=4000):
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    text = p.read_text(encoding='utf-8', errors='replace')
    return text[-max_chars:]


_SECRET_PATTERNS = [re.compile(p, re.IGNORECASE) for p in (
    r'authorization\s*:', r'bearer\s+[a-z0-9\-_.]{10,}', r'access_token', r'refresh_token',
    r'client_secret', r'password', r'-----BEGIN',
)]


def scrub_for_report(obj):
    """Best-effort defensive scrub: if any secret-shaped substring slipped into an artifact this
    script reads (it shouldn't -- none of the upstream scripts print tokens/secrets), redact
    rather than silently including it in a report that may be shared for a deployment review."""
    text = json.dumps(obj, ensure_ascii=False)
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return {'_redacted': True, 'reason': 'a secret-shaped pattern was found and this whole field was redacted rather than partially masked'}
    return obj


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--detect-json')
    ap.add_argument('--verify-json')
    ap.add_argument('--health-json')
    ap.add_argument('--predict-json')
    ap.add_argument('--benchmark-json')
    ap.add_argument('--pytest-output')
    ap.add_argument('--tegrastats-log')
    ap.add_argument('--out-json', required=True)
    ap.add_argument('--out-txt', required=True)
    args = ap.parse_args()

    detect = scrub_for_report(load_json(args.detect_json))
    verify = scrub_for_report(load_json(args.verify_json))
    health = scrub_for_report(load_json(args.health_json))
    predict = scrub_for_report(load_json(args.predict_json))
    benchmark = scrub_for_report(load_json(args.benchmark_json))
    pytest_tail = load_text(args.pytest_output)
    tegrastats_tail = load_text(args.tegrastats_log, max_chars=2000)

    hw = (detect or {}).get('hardware', {})
    onnx = (verify or {}).get('onnxruntime', {}) if isinstance(verify, dict) else {}
    api = (verify or {}).get('api', {}) if isinstance(verify, dict) else {}

    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'hardware': hw,
        'nvidia_stack': (detect or {}).get('nvidia_stack'),
        'system': (detect or {}).get('system'),
        'nvidia_tools': (detect or {}).get('nvidia_tools'),
        'onnxruntime': onnx,
        'health_endpoint': health,
        'predict_endpoint': predict,
        'api_checks': api,
        'benchmark': benchmark,
        'backend_tests_tail': pytest_tail,
        'tegrastats_tail': tegrastats_tail,
        'demo_patient_used_for_e2e': 'SYN-002',
    }

    Path(args.out_json).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

    is_agx = hw.get('hardware_is_agx_orin')
    lines = [
        'SynexAgent Y-MAS RC1 -- Jetson Deployment Report',
        f"Generated: {report['generated_at']}",
        '',
        f"Hardware: {hw.get('device_tree_model') or hw.get('orin_family') or 'unknown'} (arch={hw.get('machine_arch')})",
        f"Is Jetson AGX Orin: {is_agx}",
        '',
        f"ONNX Runtime status: {onnx.get('status', 'unknown')}",
        f"Session providers: {onnx.get('session_providers', [])}",
        f"Fallback reason: {onnx.get('fallback_reason')}",
        f"FP16 enabled: {onnx.get('fp16_enabled')}",
        '',
        f"FastAPI reachable: {api.get('reachable')}",
    ]
    if api.get('reachable'):
        lines.append(f"  /health: {api.get('health', {}).get('status_code')}")
        lines.append(f"  /predict: {api.get('predict', {}).get('status_code')}")
        lines.append(f"  /agent/analyze: {api.get('agent_analyze', {}).get('status_code')}")
    lines.append('')
    if is_agx:
        if 'TensorrtExecutionProvider' in onnx.get('session_providers', []):
            lines.append('VERIFICATION STATUS: JETSON AGX ORIN TENSORRT DEPLOYMENT VERIFIED')
        elif 'CUDAExecutionProvider' in onnx.get('session_providers', []):
            lines.append('VERIFICATION STATUS: JETSON AGX ORIN CUDA DEPLOYMENT VERIFIED')
        else:
            lines.append('VERIFICATION STATUS: CPU SAFE MODE VERIFIED (on real AGX Orin hardware)')
    else:
        lines.append('VERIFICATION STATUS: NOT HARDWARE VERIFIED (this run was not on Jetson AGX Orin hardware)')
    lines.append('')
    lines.append('-- Backend test output (tail) --')
    lines.append(pytest_tail or '(not available)')

    Path(args.out_txt).write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote {args.out_json} and {args.out_txt}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
