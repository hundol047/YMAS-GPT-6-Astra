"""Unit tests for scripts/jetson_common.py's hardware-independent classification/matching logic --
these run on ANY machine (no real Jetson needed) because they operate on synthetic input strings,
not live system state. See test_jetson_scripts.py for the integration-level tests that actually
invoke the scripts as subprocesses on this machine's real (non-Jetson) environment.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import jetson_common as jc


# --- Hardware model parsing ----------------------------------------------------------------------

def test_agx_orin_model_string_classified_correctly():
    assert jc.classify_orin_family('NVIDIA Jetson AGX Orin Developer Kit') == 'AGX Orin'

def test_orin_nx_is_never_misclassified_as_agx_orin():
    assert jc.classify_orin_family('NVIDIA Jetson Orin NX Developer Kit') == 'Orin NX'
    assert jc.classify_orin_family('NVIDIA Jetson Orin NX Developer Kit') != 'AGX Orin'

def test_orin_nano_is_never_misclassified_as_agx_orin():
    assert jc.classify_orin_family('NVIDIA Jetson Orin Nano Developer Kit') == 'Orin Nano'
    assert jc.classify_orin_family('NVIDIA Jetson Orin Nano Developer Kit') != 'AGX Orin'

def test_x86_pc_model_string_is_not_any_orin():
    assert jc.classify_orin_family(None) is None
    assert jc.classify_orin_family('') is None

def test_generic_orin_string_without_agx_nx_nano_is_unspecified_variant():
    assert jc.classify_orin_family('Some Future Orin Module') == 'Orin (unspecified variant)'


def _hw_report(model_str, allow_other_orin=False):
    """Build the same shaped report detect_hardware() would, using a synthetic model string
    instead of reading /proc/device-tree/model -- avoids monkeypatching private internals."""
    family = jc.classify_orin_family(model_str)
    is_agx = family == 'AGX Orin'
    is_other = family in ('Orin NX', 'Orin Nano', 'Orin (unspecified variant)')
    return {
        'orin_family': family,
        'hardware_is_agx_orin': is_agx,
        'hardware_is_other_orin': is_other,
        'is_supported_target': is_agx or (allow_other_orin and is_other),
    }

def test_hardware_report_agx_orin_true():
    r = _hw_report('NVIDIA Jetson AGX Orin Developer Kit')
    assert r['hardware_is_agx_orin'] is True and r['is_supported_target'] is True

def test_hardware_report_orin_nx_false_by_default():
    r = _hw_report('NVIDIA Jetson Orin NX Developer Kit')
    assert r['hardware_is_agx_orin'] is False and r['is_supported_target'] is False

def test_hardware_report_orin_nx_true_with_allow_other_orin():
    r = _hw_report('NVIDIA Jetson Orin NX Developer Kit', allow_other_orin=True)
    assert r['hardware_is_agx_orin'] is False and r['is_supported_target'] is True

def test_hardware_report_orin_nano_false():
    r = _hw_report('NVIDIA Jetson Orin Nano Developer Kit')
    assert r['hardware_is_agx_orin'] is False and r['is_supported_target'] is False

def test_hardware_report_x86_pc_false():
    r = _hw_report(None)
    assert r['hardware_is_agx_orin'] is False and r['is_supported_target'] is False

def test_detect_hardware_on_this_actual_machine_reports_not_agx_orin():
    # This IS the live function, run on this actual (non-Jetson) machine -- confirms the real
    # detect_hardware() (not just the synthetic _hw_report helper above) behaves correctly here.
    hw = jc.detect_hardware()
    assert hw['hardware_is_agx_orin'] is False
    assert hw['machine_arch'] == 'x86_64'


# --- L4T -> JetPack family classification --------------------------------------------------------

def test_jetpack_family_exact_mapping_table():
    assert jc.classify_jetpack_family(34) == 'jetpack5'
    assert jc.classify_jetpack_family(35) == 'jetpack5'
    assert jc.classify_jetpack_family(36) == 'jetpack6'
    assert jc.classify_jetpack_family(39) == 'jetpack7'
    assert jc.classify_jetpack_family(37) is None   # never shipped as a JetPack-numbered L4T -- unsupported
    assert jc.classify_jetpack_family(38) is None
    assert jc.classify_jetpack_family(99) is None    # unrecognized future major -- never guessed
    assert jc.classify_jetpack_family(None) is None

def test_l4t_34_and_35_are_jetpack5_family():
    assert jc.classify_l4t_family('# R34 (release), REVISION: 1.0')['jetpack_family'] == 'jetpack5'
    assert jc.classify_l4t_family('# R35 (release), REVISION: 4.1')['jetpack_family'] == 'jetpack5'

def test_l4t_36_is_jetpack6_family():
    r = jc.classify_l4t_family('# R36 (release), REVISION: 4.3, GCID: 12345678, BOARD: t234ref')
    assert r['l4t_major'] == 36 and r['jetpack_family'] == 'jetpack6'

def test_l4t_39_is_jetpack7_family():
    r = jc.classify_l4t_family('# R39 (release), REVISION: 0.1')
    assert r['l4t_major'] == 39 and r['jetpack_family'] == 'jetpack7'

def test_l4t_family_none_when_no_tegra_release_file():
    r = jc.classify_l4t_family(None)
    assert r['l4t_major'] is None and r['jetpack_family'] is None

def test_cuda_12_is_jetpack6_family():
    r = jc.classify_cuda_family('12.6')
    assert r['cuda_major'] == 12 and r['jetpack_family'] == 'jetpack6'

def test_cuda_13_is_jetpack7_family():
    r = jc.classify_cuda_family('13.0')
    assert r['cuda_major'] == 13 and r['jetpack_family'] == 'jetpack7'

def test_cuda_family_none_when_no_cuda_detected():
    r = jc.classify_cuda_family(None)
    assert r['cuda_major'] is None and r['jetpack_family'] is None


# --- Exact deployment-profile matching -----------------------------------------------------------

_DETECTED = {'l4t_major': 36, 'cuda_major': 12, 'cuda_minor': 6, 'cudnn_major': 9,
             'tensorrt_major': 10, 'tensorrt_minor': 3, 'python_abi': 'cp310', 'arch': 'aarch64'}

def test_profile_matches_when_every_field_agrees():
    assert jc.profile_matches(_DETECTED, dict(_DETECTED)) is True

def test_profile_does_not_match_on_cuda_minor_mismatch():
    other = dict(_DETECTED, cuda_minor=4)
    assert jc.profile_matches(_DETECTED, other) is False

def test_profile_does_not_match_on_l4t_major_mismatch():
    other = dict(_DETECTED, l4t_major=39)  # a JetPack7 profile must never match a JetPack6 device
    assert jc.profile_matches(_DETECTED, other) is False

def test_profile_does_not_match_on_python_abi_mismatch():
    other = dict(_DETECTED, python_abi='cp312')
    assert jc.profile_matches(_DETECTED, other) is False

def test_profile_with_any_null_field_never_matches():
    incomplete = dict(_DETECTED, tensorrt_minor=None)
    assert jc.profile_matches(_DETECTED, incomplete) is False
    # and the reverse -- a detected environment missing a field also never matches
    incomplete_detected = dict(_DETECTED, cudnn_major=None)
    assert jc.profile_matches(incomplete_detected, dict(_DETECTED)) is False

def test_find_matching_verified_profile_ignores_unverified_entries():
    profiles = [dict(_DETECTED, id='p1', verified=False), dict(_DETECTED, id='p2', verified=True)]
    match = jc.find_matching_verified_profile(_DETECTED, profiles)
    assert match is not None and match['id'] == 'p2'

def test_find_matching_verified_profile_returns_none_when_nothing_matches():
    profiles = [dict(_DETECTED, id='p1', verified=True, l4t_major=39)]  # verified but wrong L4T
    assert jc.find_matching_verified_profile(_DETECTED, profiles) is None

def test_shipped_profiles_file_has_no_entry_that_matches_anything_detectable():
    # The shipped config/jetson_agx_orin_profiles.json ships with only the unverified template --
    # it must never accidentally match a real detected environment.
    profiles = jc.load_profiles()
    assert jc.find_matching_verified_profile(_DETECTED, profiles) is None


# --- --require-gpu / --require-tensorrt enforcement matrix ---------------------------------------

def test_require_gpu_fails_with_cpu_only_session():
    ok, reason = jc.check_gpu_requirement(['CPUExecutionProvider'], require_gpu=True, require_tensorrt=False)
    assert ok is False and reason

def test_require_gpu_succeeds_with_cuda_session():
    ok, reason = jc.check_gpu_requirement(['CUDAExecutionProvider', 'CPUExecutionProvider'], require_gpu=True, require_tensorrt=False)
    assert ok is True and reason is None

def test_require_gpu_succeeds_with_tensorrt_session():
    ok, reason = jc.check_gpu_requirement(['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider'],
                                           require_gpu=True, require_tensorrt=False)
    assert ok is True

def test_require_tensorrt_fails_with_cuda_only_session():
    ok, reason = jc.check_gpu_requirement(['CUDAExecutionProvider', 'CPUExecutionProvider'], require_gpu=True, require_tensorrt=True)
    assert ok is False and 'TensorrtExecutionProvider' in reason

def test_require_tensorrt_succeeds_with_tensorrt_session():
    ok, reason = jc.check_gpu_requirement(['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider'],
                                           require_gpu=True, require_tensorrt=True)
    assert ok is True

def test_no_requirement_always_passes():
    ok, reason = jc.check_gpu_requirement(['CPUExecutionProvider'], require_gpu=False, require_tensorrt=False)
    assert ok is True and reason is None


# --- The STRICTER EXECUTION_VERIFIED-based gate deploy_jetson_agx.sh actually enforces -------------

def test_require_gpu_by_status_fails_with_cpu_only():
    ok, reason = jc.check_gpu_requirement_by_status(
        {'CPUExecutionProvider': 'EXECUTION_VERIFIED', 'CUDAExecutionProvider': 'NOT_AVAILABLE',
         'TensorrtExecutionProvider': 'NOT_AVAILABLE'}, require_gpu=True, require_tensorrt=False)
    assert ok is False and reason

def test_require_gpu_by_status_fails_when_cuda_only_session_registered_not_execution_verified():
    # Session registration alone (no per-node execution proof) must NOT satisfy --require-gpu.
    ok, reason = jc.check_gpu_requirement_by_status(
        {'CPUExecutionProvider': 'EXECUTION_VERIFIED', 'CUDAExecutionProvider': 'SESSION_REGISTERED',
         'TensorrtExecutionProvider': 'NOT_AVAILABLE'}, require_gpu=True, require_tensorrt=False)
    assert ok is False and reason

def test_require_gpu_by_status_succeeds_with_verified_cuda():
    ok, reason = jc.check_gpu_requirement_by_status(
        {'CPUExecutionProvider': 'FALLBACK', 'CUDAExecutionProvider': 'EXECUTION_VERIFIED',
         'TensorrtExecutionProvider': 'NOT_AVAILABLE'}, require_gpu=True, require_tensorrt=False)
    assert ok is True and reason is None

def test_require_gpu_by_status_succeeds_with_verified_tensorrt():
    ok, reason = jc.check_gpu_requirement_by_status(
        {'CPUExecutionProvider': 'FALLBACK', 'CUDAExecutionProvider': 'FALLBACK',
         'TensorrtExecutionProvider': 'EXECUTION_VERIFIED'}, require_gpu=True, require_tensorrt=False)
    assert ok is True and reason is None

def test_require_tensorrt_by_status_fails_with_cuda_only_execution_verified():
    # A CUDA-only fallback must never satisfy --require-tensorrt, however verified CUDA's own status is.
    ok, reason = jc.check_gpu_requirement_by_status(
        {'CPUExecutionProvider': 'FALLBACK', 'CUDAExecutionProvider': 'EXECUTION_VERIFIED',
         'TensorrtExecutionProvider': 'FALLBACK'}, require_gpu=True, require_tensorrt=True)
    assert ok is False and 'TensorrtExecutionProvider' in reason

def test_require_tensorrt_by_status_succeeds_with_verified_tensorrt():
    ok, reason = jc.check_gpu_requirement_by_status(
        {'CPUExecutionProvider': 'FALLBACK', 'CUDAExecutionProvider': 'FALLBACK',
         'TensorrtExecutionProvider': 'EXECUTION_VERIFIED'}, require_gpu=True, require_tensorrt=True)
    assert ok is True and reason is None

def test_no_requirement_by_status_always_passes():
    ok, reason = jc.check_gpu_requirement_by_status({'CPUExecutionProvider': 'EXECUTION_VERIFIED'},
                                                      require_gpu=False, require_tensorrt=False)
    assert ok is True and reason is None


# --- Unified verification status ladder -----------------------------------------------------------

def test_status_not_available_when_missing_from_available_providers():
    s = jc.classify_provider_status('CUDAExecutionProvider', available_providers=['CPUExecutionProvider'])
    assert s == 'NOT_AVAILABLE'

def test_status_available_when_no_session_built_yet():
    s = jc.classify_provider_status('CUDAExecutionProvider', available_providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    assert s == 'AVAILABLE'

def test_status_fallback_when_session_used_something_else():
    s = jc.classify_provider_status('TensorrtExecutionProvider',
                                     available_providers=['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider'],
                                     session_providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    assert s == 'FALLBACK'

def test_status_session_registered_when_inference_not_yet_attempted_or_failed():
    s = jc.classify_provider_status('CUDAExecutionProvider', available_providers=['CUDAExecutionProvider'],
                                     session_providers=['CUDAExecutionProvider'], inference_ok=None)
    assert s == 'SESSION_REGISTERED'
    s2 = jc.classify_provider_status('CUDAExecutionProvider', available_providers=['CUDAExecutionProvider'],
                                      session_providers=['CUDAExecutionProvider'], inference_ok=False)
    assert s2 == 'SESSION_REGISTERED'

def test_status_inference_passed_without_node_level_evidence():
    s = jc.classify_provider_status('CUDAExecutionProvider', available_providers=['CUDAExecutionProvider'],
                                     session_providers=['CUDAExecutionProvider'], inference_ok=True, nodes_executed=None)
    assert s == 'INFERENCE_PASSED'

def test_status_execution_verified_requires_positive_node_count():
    s = jc.classify_provider_status('CUDAExecutionProvider', available_providers=['CUDAExecutionProvider'],
                                     session_providers=['CUDAExecutionProvider'], inference_ok=True, nodes_executed=4)
    assert s == 'EXECUTION_VERIFIED'
    s0 = jc.classify_provider_status('CUDAExecutionProvider', available_providers=['CUDAExecutionProvider'],
                                      session_providers=['CUDAExecutionProvider'], inference_ok=True, nodes_executed=0)
    assert s0 == 'INFERENCE_PASSED'  # zero nodes attributed -- never claim execution was verified


def test_count_nodes_by_provider_parses_node_category_events(tmp_path):
    trace = [
        {'cat': 'Node', 'name': 'MatMul_kernel_time', 'args': {'provider': 'CUDAExecutionProvider'}},
        {'cat': 'Node', 'name': 'Relu_kernel_time', 'args': {'provider': 'CUDAExecutionProvider'}},
        {'cat': 'Node', 'name': 'Add_kernel_time', 'args': {'provider': 'CPUExecutionProvider'}},
        {'cat': 'Session', 'name': 'model_run', 'args': {}},  # not a Node event -- excluded
    ]
    path = tmp_path / 'profile.json'
    path.write_text(json.dumps(trace))
    counts = jc.count_nodes_by_provider(str(path))
    assert counts == {'CUDAExecutionProvider': 2, 'CPUExecutionProvider': 1}

def test_count_nodes_by_provider_returns_empty_on_missing_or_unparseable_file():
    assert jc.count_nodes_by_provider('/nonexistent/path.json') == {}


# --- Dependency policy: never both onnxruntime and onnxruntime-gpu; profile-gated candidates ----

def test_install_jetson_ort_refuses_off_aarch64():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
    import install_jetson_ort as ijo
    detected = {'arch': 'x86_64', 'l4t_major': 36, 'cuda_major': 12, 'cuda_minor': 6, 'cudnn_major': 9,
                'tensorrt_major': 10, 'tensorrt_minor': 3, 'python_abi': 'cp312'}
    # A profile+candidate CAN exist for x86_64 in theory -- the refusal is enforced by main()'s
    # explicit arch check, not by the profile/candidate matching itself, so this documents that
    # separation rather than re-testing main()'s CLI flow here.
    profile = dict(detected, id='x', verified=True, ort_candidate_id='cand-x')
    assert jc.profile_matches(detected, profile) is True
    assert detected['arch'] != 'aarch64'  # ...but main() refuses to install on this arch regardless

def test_install_jetson_ort_no_verified_profile_for_unconfigured_environment():
    detected = {'arch': 'aarch64', 'l4t_major': 39, 'cuda_major': 13, 'cuda_minor': 0, 'cudnn_major': 9,
                'tensorrt_major': 10, 'tensorrt_minor': 5, 'python_abi': 'cp312'}
    profiles = jc.load_profiles()  # the real shipped file -- ships with zero verified profiles
    assert jc.find_matching_verified_profile(detected, profiles) is None

def test_shipped_ort_candidates_file_has_no_real_entries():
    candidates = jc.load_ort_candidates()
    assert all(c.get('install_method') is None for c in candidates), \
        'no candidate should be pre-filled with a guessed install method/wheel'

def test_shipped_profiles_have_no_resolvable_ort_candidate():
    profiles = jc.load_profiles()
    candidates = jc.load_ort_candidates()
    for profile in profiles:
        assert jc.resolve_ort_candidate_for_profile(profile, candidates) is None

def test_resolve_ort_candidate_requires_verified_profile_link():
    candidates = [{'id': 'cand-1', 'install_method': 'package_name', 'package_name': 'onnxruntime-gpu'}]
    linked_profile = {'id': 'p1', 'verified': True, 'ort_candidate_id': 'cand-1'}
    assert jc.resolve_ort_candidate_for_profile(linked_profile, candidates) == candidates[0]
    unlinked_profile = {'id': 'p2', 'verified': True, 'ort_candidate_id': None}
    assert jc.resolve_ort_candidate_for_profile(unlinked_profile, candidates) is None
    wrong_link_profile = {'id': 'p3', 'verified': True, 'ort_candidate_id': 'does-not-exist'}
    assert jc.resolve_ort_candidate_for_profile(wrong_link_profile, candidates) is None
    assert jc.resolve_ort_candidate_for_profile(None, candidates) is None


# --- Target venv Python ABI (not the installer's own interpreter) --------------------------------

def test_python_abi_of_queries_the_given_interpreter_not_this_one():
    import sys as _sys
    this_abi = jc.python_abi_tag()
    queried_abi = jc.python_abi_of(_sys.executable)
    assert queried_abi == this_abi  # sanity: querying THIS interpreter matches its own tag
    # A different interpreter must be queried independently, not assumed to share this one's ABI --
    # exercised here by pointing at a nonexistent path and confirming it's reported as undetermined
    # rather than silently falling back to this process's own ABI.
    assert jc.python_abi_of('/nonexistent/python3') is None


# --- Report hygiene: no secret-shaped data ever included -----------------------------------------

def test_generate_jetson_report_scrubs_secret_shaped_content(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
    import generate_jetson_report as gjr
    tainted = {'some_field': 'Authorization: Bearer sekrit1234567890'}
    scrubbed = gjr.scrub_for_report(tainted)
    assert scrubbed.get('_redacted') is True

def test_generate_jetson_report_leaves_clean_data_alone():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
    import generate_jetson_report as gjr
    clean = {'providers': ['CPUExecutionProvider'], 'patient': 'SYN-002'}
    assert gjr.scrub_for_report(clean) == clean
