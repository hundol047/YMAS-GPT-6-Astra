#!/usr/bin/env python3
"""Reports what THIS device's environment looks like against the configured verified profiles and
ORT candidates -- and nothing more. It never fills in config/jetson_ort_candidates.json, never
guesses a wheel URL, and never marks anything verified. Finding a wheel "on the internet" that
looks like it should work for this device is explicitly NOT something this script (or any script
in this repo) treats as verification -- see config/jetson_ort_candidates.json's own _readme.

What it reports:
  - the detected environment (same fields scripts/jetson_common.py's PROFILE_MATCH_FIELDS compares)
  - whether any profile in config/jetson_agx_orin_profiles.json exactly matches it, and if so
    whether that profile is verified=true
  - if a verified profile matches, whether its ort_candidate_id resolves to a filled-in candidate
  - an explicit manual_verification_required flag -- true unless a verified profile AND a resolved,
    filled-in candidate both already exist for this exact environment

Usage: python3 scripts/suggest_jetson_ort_candidate.py [--python /path/to/python]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jetson_common as jc


def detected_environment(python_bin: str) -> dict:
    hw = jc.detect_hardware()
    l4t = jc.classify_l4t_family(jc.read_file('/etc/nv_tegra_release'))
    nvcc = jc.run(['nvcc', '--version'])
    cuda = jc.classify_cuda_family(jc.extract_cuda_version_from_nvcc(nvcc))
    cudnn_major = jc.extract_cudnn_major(jc.run(['bash', '-c', 'dpkg -l | grep -i cudnn || true']))
    trt = jc.extract_tensorrt_version(jc.run(['bash', '-c', "dpkg -l | grep -E 'tensorrt|libnvinfer' || true"]))
    return {
        'arch': hw['machine_arch'],
        'orin_family': hw['orin_family'],
        'hardware_is_agx_orin': hw['hardware_is_agx_orin'],
        'l4t_major': l4t['l4t_major'],
        'jetpack_family': l4t['jetpack_family'],
        'cuda_major': cuda['cuda_major'],
        'cuda_minor': cuda['cuda_minor'],
        'cudnn_major': cudnn_major,
        'tensorrt_major': trt['tensorrt_major'],
        'tensorrt_minor': trt['tensorrt_minor'],
        'python_abi': jc.python_abi_of(python_bin),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--python', default=sys.executable,
                     help='Interpreter whose ABI to match against (default: this script\'s own interpreter)')
    ap.add_argument('--profiles-file', default=None)
    ap.add_argument('--candidates-file', default=None)
    args = ap.parse_args()

    detected = detected_environment(args.python)
    profiles = jc.load_profiles(Path(args.profiles_file) if args.profiles_file else None)
    candidates = jc.load_ort_candidates(Path(args.candidates_file) if args.candidates_file else None)

    # Report BOTH: any exact match regardless of verified (so a human can see "this profile's
    # fields match but it's still a template"), and the actual verified match the real install
    # gate (install_jetson_ort.py) would use.
    any_exact_match = next((p for p in profiles if jc.profile_matches(detected, p)), None)
    verified_match = jc.find_matching_verified_profile(detected, profiles)
    candidate = jc.resolve_ort_candidate_for_profile(verified_match, candidates) if verified_match else None

    manual_verification_required = not (verified_match is not None and candidate is not None)

    result = {
        'detected_environment': detected,
        'matching_profile_id': any_exact_match['id'] if any_exact_match else None,
        'matching_profile_is_verified': bool(any_exact_match and any_exact_match.get('verified')),
        'verified_profile_id': verified_match['id'] if verified_match else None,
        'linked_ort_candidate_id': candidate['id'] if candidate else None,
        'linked_ort_candidate_filled_in': bool(candidate),
        'manual_verification_required': manual_verification_required,
        'note': ('This is a REPORT only -- it never writes to config/jetson_ort_candidates.json or '
                 'config/jetson_agx_orin_profiles.json, and finding a wheel that looks compatible '
                 '"on the internet" is never, by itself, a basis for marking anything verified here. '
                 'A verified profile and a filled-in linked candidate can only come from a real '
                 'install + import + provider-availability check on this exact device (see '
                 'scripts/install_jetson_ort.py and scripts/verify_jetson_agx_gpu.py), followed by a '
                 'human manually adding the resulting entries to those two config files.'),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
