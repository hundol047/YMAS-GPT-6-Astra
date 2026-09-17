#!/usr/bin/env python3
"""Selects and installs a single ONNX Runtime package matching the ACTUAL detected environment.

Hard rules this enforces:
  1. Never installs onnxruntime (CPU) and onnxruntime-gpu together -- uninstalls both first.
  2. Never installs a generic x86/manylinux wheel on aarch64 -- refuses outright off that arch
     unless --dry-run (dry-run only prints what WOULD happen, for testing the selection logic on
     any machine, and never invokes pip).
  3. Never guesses a wheel URL/version for a JetPack/CUDA/Python combination that isn't already an
     explicit, filled-in entry in config/jetson_ort_candidates.json -- an unmatched environment is
     reported as "no candidate configured" (exit code 2) and the caller (deploy_jetson_agx.sh)
     falls back to CPU Safe Mode rather than guessing.
  4. A successful pip install is NOT the finish line: this script re-imports onnxruntime in a
     fresh subprocess afterward and confirms the requested GPU provider actually appears in
     ort.get_available_providers() before reporting success.

Usage: python3 scripts/install_jetson_ort.py --python /path/to/venv/bin/python3 [--dry-run]
"""
import argparse, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jetson_common as jc

ROOT = Path(__file__).resolve().parents[1]


def load_candidates(path=None):
    path = path or (ROOT / 'config' / 'jetson_ort_candidates.json')
    return json.loads(path.read_text(encoding='utf-8'))['candidates']


def find_candidate(detected, candidates):
    for c in candidates:
        if c.get('install_method') is None:
            continue  # unfilled template entry -- never matches
        fields = ('jetpack_family', 'cuda_major', 'python_abi', 'arch')
        if all(detected.get(f) is not None and detected.get(f) == c.get(f) for f in fields):
            return c
    return None


def detected_environment():
    hw = jc.detect_hardware()
    l4t = jc.classify_l4t_family(jc.read_file('/etc/nv_tegra_release'))
    nvcc = jc.run(['nvcc', '--version'])
    cuda = jc.classify_cuda_family(jc.extract_cuda_version_from_nvcc(nvcc))
    family = l4t['jetpack_family'] or cuda['jetpack_family']
    return {
        'arch': hw['machine_arch'],
        'jetpack_family': family,
        'cuda_major': cuda['cuda_major'],
        'python_abi': jc.python_abi_tag(),
    }


def pip_uninstall_existing(python_bin, dry_run):
    cmd = [python_bin, '-m', 'pip', 'uninstall', '-y', 'onnxruntime', 'onnxruntime-gpu']
    if dry_run:
        return {'command': ' '.join(cmd), 'dry_run': True}
    r = subprocess.run(cmd, capture_output=True, text=True)
    return {'command': ' '.join(cmd), 'returncode': r.returncode, 'stdout': r.stdout[-2000:], 'stderr': r.stderr[-2000:]}


def pip_install_candidate(python_bin, candidate, dry_run):
    method = candidate['install_method']
    if method == 'pip_index_url':
        cmd = [python_bin, '-m', 'pip', 'install', '--index-url', candidate['pip_index_url'], candidate['wheel_filename_or_spec']]
    elif method == 'wheel_file':
        cmd = [python_bin, '-m', 'pip', 'install', candidate['wheel_filename_or_spec']]
    elif method == 'package_name':
        cmd = [python_bin, '-m', 'pip', 'install', candidate['package_name']]
    else:
        raise ValueError(f'Unknown install_method {method!r} in candidate {candidate.get("id")}')
    if dry_run:
        return {'command': ' '.join(cmd), 'dry_run': True}
    r = subprocess.run(cmd, capture_output=True, text=True)
    return {'command': ' '.join(cmd), 'returncode': r.returncode, 'stdout': r.stdout[-2000:], 'stderr': r.stderr[-2000:]}


def verify_installed(python_bin):
    """Re-checks in a FRESH subprocess (not this process's own import cache) that onnxruntime
    imports and reports the expected providers -- a pip 'Successfully installed' line is not
    itself proof the package actually works on this hardware."""
    r = subprocess.run([python_bin, '-c', 'import onnxruntime as ort; import json; '
                        'print(json.dumps({"version": ort.__version__, "providers": ort.get_available_providers()}))'],
                        capture_output=True, text=True)
    if r.returncode != 0:
        return {'ok': False, 'error': r.stderr[-2000:]}
    try:
        return {'ok': True, **json.loads(r.stdout.strip().splitlines()[-1])}
    except Exception as e:
        return {'ok': False, 'error': f'could not parse verification output: {e}', 'raw': r.stdout}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--python', required=True, help='Path to the target venv python executable')
    ap.add_argument('--candidates-file', default=None)
    ap.add_argument('--dry-run', action='store_true', help='Print the plan without running pip or touching the environment')
    args = ap.parse_args()

    detected = detected_environment()
    result = {'detected': detected}

    if detected['arch'] != 'aarch64' and not args.dry_run:
        result['status'] = 'REFUSED'
        result['reason'] = f"Refusing to install a Jetson GPU ONNX Runtime build on arch={detected['arch']!r} (not aarch64)."
        print(json.dumps(result, indent=2))
        return 3

    candidates = load_candidates(args.candidates_file)
    candidate = find_candidate(detected, candidates)
    if candidate is None:
        result['status'] = 'NO_CANDIDATE_CONFIGURED'
        result['reason'] = ('No entry in config/jetson_ort_candidates.json matches this exact '
                             'jetpack_family/cuda_major/python_abi/arch combination. Add a real, '
                             'device-verified entry there rather than guessing -- falling back to CPU Safe Mode.')
        print(json.dumps(result, indent=2))
        return 2

    result['matched_candidate'] = candidate['id']
    result['uninstall'] = pip_uninstall_existing(args.python, args.dry_run)
    result['install'] = pip_install_candidate(args.python, candidate, args.dry_run)
    if args.dry_run:
        result['status'] = 'DRY_RUN'
        print(json.dumps(result, indent=2))
        return 0

    if result['install']['returncode'] != 0:
        result['status'] = 'INSTALL_FAILED'
        print(json.dumps(result, indent=2))
        return 1

    verification = verify_installed(args.python)
    result['verification'] = verification
    expected_provider = jc.PROVIDER_NAMES.get('cuda')
    if verification.get('ok') and expected_provider in verification.get('providers', []):
        result['status'] = 'INSTALLED_AND_VERIFIED'
        print(json.dumps(result, indent=2))
        return 0
    result['status'] = 'INSTALLED_BUT_NOT_VERIFIED'
    result['reason'] = f'pip install succeeded but {expected_provider} did not appear in ort.get_available_providers() afterward.'
    print(json.dumps(result, indent=2))
    return 1


if __name__ == '__main__':
    sys.exit(main())
