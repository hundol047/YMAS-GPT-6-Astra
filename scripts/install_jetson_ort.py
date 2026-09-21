#!/usr/bin/env python3
"""Selects and installs a single ONNX Runtime package matching the ACTUAL detected environment.

Hard rules this enforces:
  1. Never installs onnxruntime (CPU) and onnxruntime-gpu together -- uninstalls both first.
  2. Never installs a generic x86/manylinux wheel on aarch64 -- refuses outright off that arch
     unless --dry-run (dry-run only prints what WOULD happen, for testing the selection logic on
     any machine, and never invokes pip).
  3. A GPU candidate is reached ONLY through an exact-matching VERIFIED deployment profile in
     config/jetson_agx_orin_profiles.json -- never by matching environment fields against
     config/jetson_ort_candidates.json directly. This is the real deploy gate: no verified profile
     matches -> NO_VERIFIED_PROFILE; a matching verified profile with no resolvable
     ort_candidate_id -> NO_VERIFIED_ORT_CANDIDATE. Either way, CPU Safe Mode follows, never a
     guessed wheel.
  4. Candidate/profile matching uses the ABI of the TARGET python (the venv this ONNX Runtime is
     being installed into, queried via `--python`), never the ABI of whatever interpreter happens
     to be running this installer script itself.
  5. A successful pip install is NOT the finish line: this script re-imports onnxruntime in a
     fresh subprocess afterward and confirms the requested GPU provider actually appears in
     ort.get_available_providers() before reporting success.

Usage: python3 scripts/install_jetson_ort.py --python /path/to/venv/bin/python3 [--dry-run]
"""
import argparse, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jetson_common as jc

ROOT = Path(__file__).resolve().parents[1]


def detected_environment(python_bin: str) -> dict:
    """Builds the exact same field set jetson_common.PROFILE_MATCH_FIELDS compares -- using the
    TARGET python's ABI (python_abi_of(python_bin)), not this script's own interpreter."""
    hw = jc.detect_hardware()
    l4t = jc.classify_l4t_family(jc.read_file('/etc/nv_tegra_release'))
    # Shared with detect_jetson_env.py (jc.collect_cuda_version) -- this used to call ONLY
    # `nvcc --version` with no fallback, which on a real Jetson AGX Orin + JetPack 5.1.2 device
    # where `nvcc` wasn't on this shell's PATH (CUDA 11.4.19 was genuinely installed) produced
    # cuda_major/cuda_minor: null here while detect_jetson_env.py's version.json fallback correctly
    # found 11.4 -- the two scripts disagreeing about the same real hardware. Never divergent now.
    cuda = jc.classify_cuda_family(jc.collect_cuda_version()['cuda_version'])
    cudnn_major = jc.extract_cudnn_major(jc.run(['bash', '-c', 'dpkg -l | grep -i cudnn || true']))
    trt = jc.extract_tensorrt_version(jc.run(['bash', '-c', "dpkg -l | grep -E 'tensorrt|libnvinfer' || true"]))
    return {
        'arch': hw['machine_arch'],
        'l4t_major': l4t['l4t_major'],
        'cuda_major': cuda['cuda_major'],
        'cuda_minor': cuda['cuda_minor'],
        'cudnn_major': cudnn_major,
        'tensorrt_major': trt['tensorrt_major'],
        'tensorrt_minor': trt['tensorrt_minor'],
        'python_abi': jc.python_abi_of(python_bin),
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
    ap.add_argument('--profiles-file', default=None)
    ap.add_argument('--candidates-file', default=None)
    ap.add_argument('--dry-run', action='store_true', help='Print the plan without running pip or touching the environment')
    args = ap.parse_args()

    detected = detected_environment(args.python)
    result = {'detected': detected}

    if detected['arch'] != 'aarch64' and not args.dry_run:
        result['status'] = 'REFUSED'
        result['reason'] = f"Refusing to install a Jetson GPU ONNX Runtime build on arch={detected['arch']!r} (not aarch64)."
        print(json.dumps(result, indent=2))
        return 3

    profiles_path = Path(args.profiles_file) if args.profiles_file else None
    candidates_path = Path(args.candidates_file) if args.candidates_file else None
    profiles = jc.load_profiles(profiles_path)
    matched_profile = jc.find_matching_verified_profile(detected, profiles)
    if matched_profile is None:
        result['status'] = 'NO_VERIFIED_PROFILE'
        result['reason'] = ('No entry in config/jetson_agx_orin_profiles.json with verified=true exactly '
                             'matches this environment (arch/l4t_major/cuda_major/cuda_minor/cudnn_major/'
                             'tensorrt_major/tensorrt_minor/python_abi). A profile is only ever marked '
                             'verified from a real successful run on real hardware -- falling back to CPU Safe Mode.')
        print(json.dumps(result, indent=2))
        return 2

    result['matched_profile'] = matched_profile['id']
    candidates = jc.load_ort_candidates(candidates_path)
    candidate = jc.resolve_ort_candidate_for_profile(matched_profile, candidates)
    if candidate is None:
        result['status'] = 'NO_VERIFIED_ORT_CANDIDATE'
        result['reason'] = (f"Profile {matched_profile['id']!r} matched this environment, but its "
                             "ort_candidate_id does not resolve to a filled-in entry in "
                             "config/jetson_ort_candidates.json. A verified profile proves the environment "
                             "was confirmed on real hardware; it does not by itself supply a working ORT "
                             "wheel -- falling back to CPU Safe Mode.")
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
