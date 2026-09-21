"""These exercise the Jetson scripts' real logic on THIS machine (x86_64 cloud Linux, not Jetson
hardware) -- the one thing they can prove from here is that hardware detection and the CPU Safe
Mode fallback are correct, since that's the actual environment available. They do not and cannot
prove GPU acceleration works; that needs a real Jetson AGX Orin.
"""
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def run_script(name, *args, env=None):
    return subprocess.run([sys.executable, str(ROOT / 'scripts' / name), *args],
                          capture_output=True, text=True, timeout=30, env=env)

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


def test_deploy_script_help_documents_python_and_ort_wheel_overrides():
    r = subprocess.run(['bash', str(ROOT / 'scripts' / 'deploy_jetson_agx.sh'), '--help'],
                        capture_output=True, text=True, timeout=15)
    assert r.returncode == 0, r.stderr
    assert '--python /path/to/python' in r.stdout
    assert '--ort-wheel' in r.stdout


def test_deploy_script_rejects_unknown_option():
    r = subprocess.run(['bash', str(ROOT / 'scripts' / 'deploy_jetson_agx.sh'), '--not-a-real-flag'],
                        capture_output=True, text=True, timeout=15)
    assert r.returncode != 0
    assert 'Unknown option' in r.stdout


def test_deploy_script_source_defines_jetpack5_branch_and_venv_robustness():
    """Static check that the JetPack5/cp38 branch and the broken-venv recreate path are actually
    wired into the script text (the functional end-to-end path needs aarch64 hardware this sandbox
    doesn't have -- see docs/JETSON_DEPLOYMENT.md)."""
    src = (ROOT / 'scripts' / 'deploy_jetson_agx.sh').read_text(encoding='utf-8')
    assert 'requirements-jetpack5.txt' in src
    assert 'requirements-jetpack5-ort-cpu.txt' in src
    assert 'jetpack5' in src and 'cp38' in src
    assert 'create_or_repair_venv' in src
    assert 'ensurepip' in src
    assert 'SYNEX_ORT_WHEEL' in src


# --- ORT native-crash isolation: scripts/ort_smoke_test.py + verify_jetson_agx_gpu.py's gate ------

def test_ort_smoke_test_script_succeeds_on_a_working_onnxruntime():
    r = run_script('ort_smoke_test.py')
    assert r.returncode == 0, r.stderr
    line = json.loads(r.stdout.strip().splitlines()[-1])
    assert line['stage'] == 'import' and line['ok'] is True
    assert 'CPUExecutionProvider' in line['providers']

def test_ort_smoke_test_script_full_mode_loads_model_and_runs_inference():
    env = dict(os.environ, SYNEX_PROVIDER='cpu')
    r = run_script('ort_smoke_test.py', '--full', env=env)
    assert r.returncode == 0, r.stderr
    lines = [json.loads(l) for l in r.stdout.strip().splitlines()]
    stages = [l['stage'] for l in lines]
    assert stages == ['import', 'model_load', 'inference']
    assert all(l['ok'] for l in lines)
    assert 0 <= lines[-1]['risk_probability'] <= 1


def _fake_crashing_onnxruntime_pythonpath(tmp_path):
    """Writes a fake `onnxruntime` module that prints the real ort_smoke_test.py 'import' stage
    marker and then os.abort()s -- simulating the EXACT real failure confirmed on a Jetson AGX Orin
    + JetPack 5.1.2 device (a C++ assertion inside the installed wheel -> SIGABRT -> "Aborted (core
    dumped)"), so this test exercises the real subprocess-classification path against a real OS-level
    signal kill, not just a hand-constructed returncode."""
    fake_dir = tmp_path / 'fake_ort_site'
    fake_dir.mkdir()
    (fake_dir / 'onnxruntime.py').write_text(
        'import json, os\n'
        'print(json.dumps({"stage": "import", "ok": True, "version": "1.19.2-fake", '
        '"providers": ["CPUExecutionProvider"]}), flush=True)\n'
        'os.abort()\n'
    )
    return fake_dir


def test_ort_smoke_test_script_itself_gets_killed_by_a_real_native_crash(tmp_path):
    fake_dir = _fake_crashing_onnxruntime_pythonpath(tmp_path)
    env = dict(os.environ)
    env['PYTHONPATH'] = str(fake_dir) + os.pathsep + env.get('PYTHONPATH', '')
    r = run_script('ort_smoke_test.py', env=env)
    assert r.returncode != 0
    sys.path.insert(0, str(ROOT / 'scripts'))
    import jetson_common as jc
    assert jc.classify_subprocess_termination(r.returncode) == 'NATIVE_CRASH'


def test_verify_jetson_agx_gpu_isolates_a_native_ort_crash_and_never_runs_inference(tmp_path):
    """End-to-end: verify_jetson_agx_gpu.py must run its ORT smoke test in an isolated subprocess
    FIRST, detect the crash, exit with its dedicated exit code (3), and report
    ORT_NATIVE_RUNTIME_CRASH -- never attempting (and thereby never itself crashing from) the
    in-process RiskEngine/inference path that onnxruntime_report() would otherwise run."""
    fake_dir = _fake_crashing_onnxruntime_pythonpath(tmp_path)
    env = dict(os.environ)
    env['PYTHONPATH'] = str(fake_dir) + os.pathsep + env.get('PYTHONPATH', '')
    r = run_script('verify_jetson_agx_gpu.py', '--provider', 'cpu', env=env)
    assert r.returncode == 3, f'expected the dedicated ORT-smoke-test-failure exit code; got {r.returncode}, stderr={r.stderr}'
    body = json.loads(r.stdout)
    assert body['onnxruntime']['status'] == 'ORT_NATIVE_RUNTIME_CRASH'
    assert body['ort_smoke_test']['status'] == 'ORT_NATIVE_RUNTIME_CRASH'
    assert body['ort_smoke_test']['last_stage_completed'] == 'import'
    # The crash must be reported plainly, never mislabeled as a GPU/CPU equivalence problem.
    assert 'equivalence' not in json.dumps(body).lower()
    assert 'ORT_NATIVE_RUNTIME_CRASH' in r.stderr


def test_deploy_script_stops_before_step_10_equivalence_on_a_verify_exit_code_3():
    """Static/control-flow check that deploy_jetson_agx.sh actually stops (exit 6) on
    verify_jetson_agx_gpu.py's dedicated crash exit code (3) BEFORE it ever reaches step 10's
    compare_cpu_gpu_results.py invocation -- the real end-to-end path needs a full venv+pip install
    cycle this sandbox's non-aarch64/no-Jetson environment can't meaningfully exercise, so this
    verifies the actual control flow in the script text: the `VERIFY_RC = 3` branch's `exit 6`
    appears strictly before the `compare_cpu_gpu_results.py` call, in the same unconditional
    top-level sequence (not nested inside something that could be skipped)."""
    src = (ROOT / 'scripts' / 'deploy_jetson_agx.sh').read_text(encoding='utf-8')
    verify_rc_check = src.index('VERIFY_RC" = "3"')
    exit_6_after_crash = src.index('exit 6', verify_rc_check)
    compare_call = src.index('compare_cpu_gpu_results.py')
    assert verify_rc_check < exit_6_after_crash < compare_call, (
        'deploy_jetson_agx.sh must check verify_jetson_agx_gpu.py\'s crash exit code and exit '
        'BEFORE calling compare_cpu_gpu_results.py -- otherwise a native crash in step 8-9 can '
        'still reach step 10 and get mislabeled as a CPU/GPU equivalence failure'
    )
    # The crash-specific exit must not be gated behind anything that could make it optional --
    # confirm it's inside the same `if [ "$VERIFY_RC" = "3" ]` block, not merely present somewhere
    # later in the file by coincidence.
    between = src[verify_rc_check:exit_6_after_crash]
    assert 'compare_cpu_gpu_results.py' not in between
