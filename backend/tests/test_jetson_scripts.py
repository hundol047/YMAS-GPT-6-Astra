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
    profiles = json.loads((ROOT / 'config' / 'jetson_agx_orin_profiles.json').read_text())
    assert not any(p.get('verified') for p in profiles['profiles']), \
        'no profile should be marked verified without a real run on real AGX Orin hardware'

def test_benchmark_script_never_fabricates_unavailable_provider_numbers():
    r = run_script('benchmark_jetson.py', '--warmup', '2', '--short', '3', '--sustained', '3')
    assert r.returncode == 0, r.stderr
    body = json.loads(r.stdout)
    cpu = next(p for p in body['providers'] if p['provider'] == 'CPUExecutionProvider')
    assert cpu['available'] is True and 'latency_ms' in cpu
    for gpu in body['providers']:
        if gpu['provider'] != 'CPUExecutionProvider':
            assert gpu['available'] is False
            assert 'latency_ms' not in gpu
