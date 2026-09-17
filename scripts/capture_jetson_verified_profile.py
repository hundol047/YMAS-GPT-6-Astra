#!/usr/bin/env python3
"""Captures a candidate verified-profile record from a REAL deployment run's own output files into
runtime/jetson_verified_profile.json (gitignored, never the source config).

This never edits config/jetson_agx_orin_profiles.json itself -- that file is only ever hand-edited
by a human who has reviewed a real run's output and decided to promote it (see that file's own
_readme). This script only assembles what a real `deploy_jetson_agx.sh --auto` run on real
hardware actually observed -- detected hardware/L4T/JetPack/CUDA/cuDNN/TensorRT/Python ABI, the
ONNX Runtime version and provider status actually seen, the real inference/API/benchmark results
-- into one reviewable file, so a human never has to reconstruct that from scattered runtime/*.json
files by hand.

deploy_jetson_agx.sh only calls this when hardware_is_agx_orin (or --allow-other-orin's
is_supported_target) is actually true for the machine that just ran -- this script itself does not
decide that; it faithfully reports whatever the caller's input files say, including "not real
hardware" if that's what they say.

Usage: python3 scripts/capture_jetson_verified_profile.py --detect-json PATH --verify-json PATH
           --health-json PATH [--predict-json PATH] [--agent-analyze-json PATH]
           [--benchmark-json PATH] --out PATH
"""
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path


def _load(path):
    if not path:
        return None
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception as e:
        return {'_error': f'could not read/parse {path}: {e}'}


def build_capture(detect, verify, health, predict, agent_analyze, benchmark):
    hw = detect.get('hardware', {}) if detect else {}
    l4t = detect.get('nvidia_stack', {}).get('l4t', {}) if detect else {}
    cuda = detect.get('nvidia_stack', {}).get('cuda', {}) if detect else {}
    system = detect.get('system', {}) if detect else {}
    onnx = (verify or {}).get('onnxruntime', {})
    return {
        'captured_at': datetime.now(timezone.utc).isoformat(),
        'hardware_is_agx_orin': hw.get('hardware_is_agx_orin'),
        'orin_family': hw.get('orin_family'),
        'machine_arch': hw.get('machine_arch'),
        'compute_capability': hw.get('compute_capability'),
        'l4t_major': l4t.get('l4t_major'),
        'l4t_revision': l4t.get('l4t_revision'),
        'jetpack_family': l4t.get('jetpack_family'),
        'cuda_major': cuda.get('cuda_major'),
        'cuda_minor': cuda.get('cuda_minor'),
        'cudnn_major': (detect or {}).get('nvidia_stack', {}).get('cudnn_major'),
        'tensorrt_major': (detect or {}).get('nvidia_stack', {}).get('tensorrt_major'),
        'tensorrt_minor': (detect or {}).get('nvidia_stack', {}).get('tensorrt_minor'),
        'python_version': system.get('python_version'),
        'python_abi': system.get('python_abi'),
        'onnxruntime_version': None,  # not captured by verify_jetson_agx_gpu.py today -- fill by
                                       # hand from `pip show onnxruntime` / onnxruntime-gpu on the
                                       # device if promoting this into the source config.
        'onnxruntime_available_providers': onnx.get('available_providers'),
        'onnxruntime_session_providers': onnx.get('session_providers'),
        'onnxruntime_provider_status': onnx.get('provider_status'),
        'onnxruntime_nodes_executed_by_provider': onnx.get('nodes_executed_by_provider'),
        'onnxruntime_verification_status': onnx.get('verification_status'),
        'model_sha256': onnx.get('model_sha256'),
        'predict_endpoint_result': predict,
        'agent_analyze_endpoint_result': agent_analyze,
        'benchmark_result': benchmark,
        'note': ("This file is a CAPTURE of one real deployment run's own observed output -- it is "
                 'never auto-promoted into config/jetson_agx_orin_profiles.json. A human must review '
                 'it (filling in onnxruntime_version/onnxruntime_source by hand, since this script '
                 'does not itself query pip) and, if it looks right, copy the relevant fields into a '
                 'NEW profile entry there with verified=true and a matching config/'
                 'jetson_ort_candidates.json entry linked via ort_candidate_id -- never edit an '
                 'existing profile entry in place.'),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--detect-json', required=True)
    ap.add_argument('--verify-json', required=True)
    ap.add_argument('--health-json', default=None)
    ap.add_argument('--predict-json', default=None)
    ap.add_argument('--agent-analyze-json', default=None)
    ap.add_argument('--benchmark-json', default=None)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    detect = _load(args.detect_json)
    verify = _load(args.verify_json)
    predict = _load(args.predict_json)
    agent_analyze = _load(args.agent_analyze_json)
    benchmark = _load(args.benchmark_json)

    capture = build_capture(detect, verify, _load(args.health_json), predict, agent_analyze, benchmark)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(capture, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(capture, indent=2, ensure_ascii=False))
    print(f'\nWrote {out_path} -- review by hand before promoting anything into '
          f'config/jetson_agx_orin_profiles.json.', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
