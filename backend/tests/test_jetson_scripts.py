"""These exercise the Jetson scripts' real logic on THIS machine (x86_64 cloud Linux, not Jetson
hardware) -- the one thing they can prove from here is that hardware detection and the CPU Safe
Mode fallback are correct, since that's the actual environment available. They do not and cannot
prove GPU acceleration works; that needs a real Jetson AGX Orin.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def run_script(name, *args):
    return subprocess.run([sys.executable, str(ROOT / 'scripts' / name), *args],
                          capture_output=True, text=True, timeout=30)

def test_verify_script_reports_non_jetson_hardware_honestly():
    r = run_script('verify_jetson_agx_gpu.py', '--provider', 'cpu')
    assert r.returncode == 0, r.stderr
    body = json.loads(r.stdout)
    assert body['hardware']['hardware_is_agx_orin'] is False
    assert body['onnxruntime']['status'] == 'CPU SAFE MODE'
    assert body['onnxruntime']['selected_provider'] == 'CPUExecutionProvider'

def test_verify_script_requesting_gpu_never_claims_verified_when_unavailable():
    r = run_script('verify_jetson_agx_gpu.py', '--provider', 'tensorrt')
    assert r.returncode == 0, r.stderr
    body = json.loads(r.stdout)
    assert body['onnxruntime']['gpu_acceleration_verified'] is False
    assert body['onnxruntime']['status'] != 'GPU ACCELERATION VERIFIED'

def test_deployment_profiles_ship_with_no_fabricated_verified_entry():
    profiles = json.loads((ROOT / 'config' / 'jetson_agx_orin_profiles.json').read_text(encoding='utf-8'))
    assert not any(p.get('verified') for p in profiles['profiles']), \
        'no profile should be marked verified without a real run on real AGX Orin hardware'

def test_benchmark_script_never_fabricates_unavailable_provider_numbers():
    r = run_script('benchmark_jetson.py', '--warmup', '2', '--short', '3', '--sustained', '3')
    assert r.returncode == 0, r.stderr
    body = json.loads(r.stdout)
    for benchmark_key in ('model_microbenchmark', 'application_benchmark'):
        cpu = next(p for p in body[benchmark_key] if p['provider'] == 'CPUExecutionProvider')
        assert cpu['available'] is True and 'latency_ms' in cpu
        assert cpu['requested_provider'] == 'CPUExecutionProvider'
        assert cpu['execution_verified_provider'] == 'CPUExecutionProvider'
        for gpu in body[benchmark_key]:
            if gpu['provider'] != 'CPUExecutionProvider':
                assert gpu['available'] is False
                assert 'latency_ms' not in gpu
                assert gpu['execution_verified_provider'] is None

def test_verify_script_reports_real_per_node_execution_proof_for_cpu():
    # On this non-Jetson host, CPU is the only real provider -- its own node execution should be
    # provably counted (never just inferred from registration), and CUDA/TensorRT (unavailable
    # here) must never be reported as EXECUTION_VERIFIED.
    r = run_script('verify_jetson_agx_gpu.py', '--provider', 'cpu')
    assert r.returncode == 0, r.stderr
    body = json.loads(r.stdout)
    onnx = body['onnxruntime']
    assert onnx['verification_status'] == 'EXECUTION_VERIFIED'
    assert onnx['nodes_executed_by_provider'].get('CPUExecutionProvider', 0) > 0
    assert onnx['provider_status']['CUDAExecutionProvider'] != 'EXECUTION_VERIFIED'
    assert onnx['provider_status']['TensorrtExecutionProvider'] != 'EXECUTION_VERIFIED'

def test_suggest_ort_candidate_never_claims_verification_from_a_report_only_run():
    r = run_script('suggest_jetson_ort_candidate.py')
    assert r.returncode == 0, r.stderr
    body = json.loads(r.stdout)
    assert body['manual_verification_required'] is True
    assert body['linked_ort_candidate_filled_in'] is False
    assert 'detected_environment' in body

def test_capture_verified_profile_writes_a_reviewable_file_not_the_source_config(tmp_path):
    detect_json = tmp_path / 'detect.json'
    verify_json = tmp_path / 'verify.json'
    out_json = tmp_path / 'jetson_verified_profile.json'
    detect_json.write_text(json.dumps({
        'hardware': {'hardware_is_agx_orin': False, 'orin_family': None, 'machine_arch': 'x86_64', 'compute_capability': None},
        'nvidia_stack': {'l4t': {'l4t_major': None, 'l4t_revision': None, 'jetpack_family': None},
                          'cuda': {'cuda_major': None, 'cuda_minor': None}, 'cudnn_major': None,
                          'tensorrt_major': None, 'tensorrt_minor': None},
        'system': {'python_version': '3.11.15', 'python_abi': 'cp311'},
    }))
    verify_json.write_text(json.dumps({'onnxruntime': {
        'available_providers': ['CPUExecutionProvider'], 'session_providers': ['CPUExecutionProvider'],
        'provider_status': {'CPUExecutionProvider': 'EXECUTION_VERIFIED'},
        'nodes_executed_by_provider': {'CPUExecutionProvider': 85},
        'verification_status': 'EXECUTION_VERIFIED', 'model_sha256': 'abc123',
    }}))
    r = run_script('capture_jetson_verified_profile.py', '--detect-json', str(detect_json),
                   '--verify-json', str(verify_json), '--out', str(out_json))
    assert r.returncode == 0, r.stderr
    assert out_json.exists()
    captured = json.loads(out_json.read_text())
    assert captured['model_sha256'] == 'abc123'
    assert captured['hardware_is_agx_orin'] is False
    # This is a scratch capture file, never the source config -- confirm nothing under config/ moved.
    profiles = json.loads((ROOT / 'config' / 'jetson_agx_orin_profiles.json').read_text(encoding='utf-8'))
    assert not any(p.get('verified') for p in profiles['profiles'])
