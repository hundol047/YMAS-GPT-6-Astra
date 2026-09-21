"""Shared, hardware-detection-only logic for the Jetson AGX Orin deployment scripts
(detect_jetson_env.py, verify_jetson_agx_gpu.py, benchmark_jetson.py, deploy_jetson_agx.sh via
`python3 -m scripts.jetson_common` one-liners). Deliberately has NO dependency on onnxruntime or
any other backend package -- it must run standalone, before anything Jetson-specific is installed,
on a bare Python 3 interpreter.

Every function here only reads real system state (files, subprocess output) or classifies already-
read strings -- nothing here guesses a JetPack/L4T/CUDA version, and nothing here marks a deployment
profile "verified". That happens only via a real run on real hardware, recorded by the caller.
"""
from __future__ import annotations
import json, os, platform, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd, timeout=10):
    """Run a command, returning its stripped stdout/stderr, or None if the binary doesn't exist.
    Never raises for a missing command -- that's expected on most hosts (e.g. no `nvcc` on a
    runtime-only JetPack, no `tegrastats` off Jetson) and callers must treat None as
    'undetermined', not 'absent capability'."""
    try:
        r = subprocess.run(cmd if isinstance(cmd, list) else cmd.split(), capture_output=True,
                            text=True, timeout=timeout)
        out = (r.stdout or r.stderr or '').strip()
        return out if out else '(empty output)'
    except FileNotFoundError:
        return None
    except Exception as e:
        return f'ERROR: {e}'


def read_file(path):
    try:
        return Path(path).read_text().strip()
    except Exception:
        return None


# --- Hardware model classification --------------------------------------------------------------
# The bug this fixes: a naive `'orin' in model.lower()` check also matches "Jetson Orin NX" and
# "Jetson Orin Nano" device-tree model strings, misclassifying them as AGX Orin. "AGX Orin" is
# checked as its own, more specific substring first.
def classify_orin_family(model_str: str | None) -> str | None:
    if not model_str:
        return None
    m = model_str.lower()
    if 'agx orin' in m:
        return 'AGX Orin'
    if 'orin nx' in m:
        return 'Orin NX'
    if 'orin nano' in m:
        return 'Orin Nano'
    if 'orin' in m:
        return 'Orin (unspecified variant)'
    return None


# AGX Orin, Orin NX, and Orin Nano all use the same Ampere-generation GPU architecture -- this is
# a fixed hardware fact about the SoC family, not a guess, and is safe to state once the device is
# confirmed to be an Orin-family part via the device-tree model string above.
ORIN_COMPUTE_CAPABILITY = '8.7'


def detect_hardware(allow_other_orin: bool = False) -> dict:
    model = read_file('/proc/device-tree/model')
    machine = platform.machine()
    family = classify_orin_family(model)
    is_agx_orin = family == 'AGX Orin'
    is_other_orin = family in ('Orin NX', 'Orin Nano', 'Orin (unspecified variant)')
    # The default deployment target is AGX Orin specifically -- an NX/Nano is a DIFFERENT module
    # with different thermal/power/memory envelopes, never silently treated as AGX Orin.  Testing
    # against those other Orin variants is only ever opt-in via --allow-other-orin.
    is_supported_target = is_agx_orin or (allow_other_orin and is_other_orin)
    return {
        'device_tree_model': model,
        'machine_arch': machine,
        'is_aarch64': machine == 'aarch64',
        'orin_family': family,
        'hardware_is_agx_orin': is_agx_orin,
        'hardware_is_other_orin': is_other_orin,
        'is_supported_target': is_supported_target,
        'allow_other_orin': allow_other_orin,
        'compute_capability': ORIN_COMPUTE_CAPABILITY if family else None,
        'note': (None if model else
                 'No /proc/device-tree/model -- this is not Jetson hardware at all '
                 '(expected on a standard PC/cloud VM; real on a Jetson device).'),
    }


# --- JetPack / L4T / CUDA family classification -------------------------------------------------
# An EXACT mapping table, not a range guess: each L4T major version this function recognizes is a
# real, documented JetPack generation (JetPack 5 = L4T 34/35, JetPack 6 = L4T 36, JetPack 7 =
# L4T 39 -- NVIDIA's own release notes, not this project's invention). An L4T major this table
# doesn't list (e.g. 37/38, which NVIDIA never shipped as a JetPack-numbered L4T release, or
# anything newer than what's listed here) returns None ("unsupported"/unrecognized) rather than
# guessing a family for it -- adding support for a genuinely new generation means adding a new
# entry here with its real, confirmed L4T major, never inferring one.
L4T_MAJOR_TO_JETPACK_FAMILY = {34: 'jetpack5', 35: 'jetpack5', 36: 'jetpack6', 39: 'jetpack7'}
CUDA_MAJOR_TO_JETPACK_FAMILY = {11: 'jetpack5', 12: 'jetpack6', 13: 'jetpack7'}


def classify_jetpack_family(l4t_major: int | None) -> str | None:
    if l4t_major is None:
        return None
    return L4T_MAJOR_TO_JETPACK_FAMILY.get(l4t_major)


def classify_l4t_family(nv_tegra_release_text: str | None) -> dict:
    if not nv_tegra_release_text:
        return {'l4t_major': None, 'l4t_revision': None, 'jetpack_family': None}
    major_match = re.search(r'R(\d+)', nv_tegra_release_text)
    rev_match = re.search(r'REVISION:\s*([\d.]+)', nv_tegra_release_text)
    major = int(major_match.group(1)) if major_match else None
    revision = rev_match.group(1) if rev_match else None
    return {'l4t_major': major, 'l4t_revision': revision, 'jetpack_family': classify_jetpack_family(major)}


def classify_cuda_family(cuda_version_str: str | None) -> dict:
    """cuda_version_str is expected like '11.4', '12.6', or '13.0' (from nvcc --version or
    /usr/local/cuda/version.json) -- returns the major/minor split and which JetPack family that
    CUDA major version is associated with, purely for cross-checking against the L4T-derived
    family (a mismatch between the two is a signal worth surfacing, not silently ignored)."""
    if not cuda_version_str:
        return {'cuda_major': None, 'cuda_minor': None, 'jetpack_family': None}
    m = re.search(r'(\d+)\.(\d+)', cuda_version_str)
    if not m:
        return {'cuda_major': None, 'cuda_minor': None, 'jetpack_family': None}
    major, minor = int(m.group(1)), int(m.group(2))
    return {'cuda_major': major, 'cuda_minor': minor, 'jetpack_family': CUDA_MAJOR_TO_JETPACK_FAMILY.get(major)}


def extract_cuda_version_from_nvcc(nvcc_output: str | None) -> str | None:
    if not nvcc_output:
        return None
    m = re.search(r'[Rr]elease\s+(\d+\.\d+)', nvcc_output)
    return m.group(1) if m else None


def _cuda_version_from_version_json(version_json_text: str | None) -> str | None:
    if not version_json_text:
        return None
    try:
        v = json.loads(version_json_text).get('cuda', {}).get('version')
    except Exception:
        return None
    if not v:
        return None
    m = re.search(r'(\d+)\.(\d+)', v)
    return f'{m.group(1)}.{m.group(2)}' if m else None


def _cuda_version_from_version_txt(version_txt_text: str | None) -> str | None:
    # Older CUDA toolkit installs write a plain-text /usr/local/cuda/version.txt like
    # "CUDA Version 11.4.19" -- newer ones use version.json instead (checked first).
    if not version_txt_text:
        return None
    m = re.search(r'(\d+)\.(\d+)', version_txt_text)
    return f'{m.group(1)}.{m.group(2)}' if m else None


def _cuda_version_from_dpkg(dpkg_cuda_output: str | None) -> str | None:
    """Parses a CUDA major.minor out of `dpkg -l` lines for CUDA runtime/toolkit packages -- e.g.
    package names like `cuda-toolkit-11-4`/`cuda-cudart-11-4` (JetPack's own naming), or a version
    column like `11.4.19-1` next to a `cuda*` package name. This is the last-resort source: no
    `nvcc` on PATH and no /usr/local/cuda/version.{json,txt} still leaves a real signal on a device
    where the CUDA runtime packages are genuinely installed (e.g. nvcc missing from a runtime-only
    JetPack image, or simply not on this shell's PATH -- both real, observed cases, not hypothetical)."""
    if not dpkg_cuda_output:
        return None
    m = re.search(r'cuda-toolkit-(\d+)-(\d+)', dpkg_cuda_output)
    if m:
        return f'{m.group(1)}.{m.group(2)}'
    m = re.search(r'cuda-cudart-(\d+)-(\d+)', dpkg_cuda_output)
    if m:
        return f'{m.group(1)}.{m.group(2)}'
    m = re.search(r'\bcuda\S*\s+(\d+)\.(\d+)\.\d+', dpkg_cuda_output)
    if m:
        return f'{m.group(1)}.{m.group(2)}'
    return None


def detect_cuda_version_string(*, nvcc_output: str | None = None, cuda_version_json_text: str | None = None,
                                cuda_version_txt_text: str | None = None, dpkg_cuda_output: str | None = None) -> dict:
    """The CUDA-version fallback chain, pure (never runs a subprocess or reads a file itself -- the
    caller passes in whatever run()/read_file() already collected from each source, which is what
    makes this testable without real hardware and reusable identically from both
    detect_jetson_env.py and install_jetson_ort.py -- see collect_cuda_version() below for the
    real-IO wrapper both of them actually call, so the two scripts can never diverge on this).

    Order, stopping at the first real signal found -- NEVER guessed, null if none of the four agree:
      1. `nvcc --version`
      2. /usr/local/cuda/version.json
      3. /usr/local/cuda/version.txt
      4. `dpkg -l` CUDA runtime/toolkit package names/versions

    Returns {'cuda_version': 'MAJOR.MINOR' | None, 'cuda_version_source': one of
    'nvcc'/'version.json'/'version.txt'/'dpkg' | None}."""
    version = extract_cuda_version_from_nvcc(nvcc_output)
    if version:
        return {'cuda_version': version, 'cuda_version_source': 'nvcc'}
    version = _cuda_version_from_version_json(cuda_version_json_text)
    if version:
        return {'cuda_version': version, 'cuda_version_source': 'version.json'}
    version = _cuda_version_from_version_txt(cuda_version_txt_text)
    if version:
        return {'cuda_version': version, 'cuda_version_source': 'version.txt'}
    version = _cuda_version_from_dpkg(dpkg_cuda_output)
    if version:
        return {'cuda_version': version, 'cuda_version_source': 'dpkg'}
    return {'cuda_version': None, 'cuda_version_source': None}


def collect_cuda_version() -> dict:
    """Actually gathers each raw source (nvcc subprocess, the two /usr/local/cuda/version.* files,
    a dpkg query) and runs detect_cuda_version_string() over them. This is the SINGLE place both
    detect_jetson_env.py and install_jetson_ort.py call for CUDA version detection -- previously
    install_jetson_ort.py only tried `nvcc --version` with no fallback at all, which on a real
    Jetson AGX Orin + JetPack 5.1.2 device where `nvcc` simply wasn't on this shell's PATH (CUDA
    11.4.19 was genuinely installed) produced cuda_major/cuda_minor: null there while
    detect_jetson_env.py (which already had a version.json fallback) correctly found 11.4 -- the
    two scripts disagreeing on the same real hardware. Sharing this one function is what prevents
    that class of bug from recurring."""
    nvcc_out = run(['nvcc', '--version'])
    version_json = read_file('/usr/local/cuda/version.json')
    version_txt = read_file('/usr/local/cuda/version.txt')
    dpkg_cuda = run(['bash', '-c', "dpkg -l | grep -iE 'cuda-toolkit|cuda-cudart|^ii  cuda' || true"])
    result = detect_cuda_version_string(nvcc_output=nvcc_out, cuda_version_json_text=version_json,
                                         cuda_version_txt_text=version_txt, dpkg_cuda_output=dpkg_cuda)
    result['nvcc_version_raw'] = nvcc_out
    return result


def extract_cudnn_major(dpkg_cudnn_output: str | None) -> int | None:
    if not dpkg_cudnn_output:
        return None
    m = re.search(r'cudnn8?9?[-.]?(\d+)', dpkg_cudnn_output.lower())
    # Prefer an explicit version token like "cudnn9-cuda-12" or "libcudnn9" -- fall back to the
    # first standalone integer found near "cudnn" if the package naming doesn't match that shape.
    m2 = re.search(r'libcudnn(\d+)', dpkg_cudnn_output.lower())
    if m2:
        return int(m2.group(1))
    return int(m.group(1)) if m else None


def extract_tensorrt_version(dpkg_tensorrt_output: str | None) -> dict:
    if not dpkg_tensorrt_output:
        return {'tensorrt_major': None, 'tensorrt_minor': None}
    m = re.search(r'(\d+)\.(\d+)\.\d+', dpkg_tensorrt_output)
    if not m:
        return {'tensorrt_major': None, 'tensorrt_minor': None}
    return {'tensorrt_major': int(m.group(1)), 'tensorrt_minor': int(m.group(2))}


def python_abi_tag() -> str:
    """The ABI of the interpreter RUNNING THIS CODE -- only meaningful when the caller genuinely
    wants that (e.g. detect_jetson_env.py describing the host's own default python3). Selecting a
    GPU ONNX Runtime candidate for a target venv must use python_abi_of(target_python) instead --
    never this function -- since the installer script and the target venv can be different
    interpreters (see install_jetson_ort.py)."""
    import sys
    return f'cp{sys.version_info.major}{sys.version_info.minor}'


def python_abi_of(python_bin: str) -> str | None:
    """Queries the ABI of a SPECIFIC python executable (e.g. the target .venv-jetson interpreter)
    by actually running it, rather than assuming it matches whatever interpreter is running this
    installer script. Returns None if that interpreter can't be invoked."""
    out = run([python_bin, '-c', "import sys; print(f'cp{sys.version_info.major}{sys.version_info.minor}')"])
    if out is None or out.startswith('ERROR:') or out == '(empty output)':
        return None
    return out.strip()


# --- Exact deployment-profile matching -----------------------------------------------------------
# The fields a candidate profile MUST match, exactly, against the live-detected environment before
# it can ever be used to pick a GPU wheel. Missing/None on either side means "cannot confirm a
# match" -- never treated as a wildcard.
PROFILE_MATCH_FIELDS = ('l4t_major', 'cuda_major', 'cuda_minor', 'cudnn_major',
                        'tensorrt_major', 'tensorrt_minor', 'python_abi', 'arch')


def profile_matches(detected: dict, profile: dict) -> bool:
    """True only if EVERY field in PROFILE_MATCH_FIELDS is present (non-None) on both sides and
    equal. A profile with any null field can never match -- it's an incomplete/template entry, not
    a wildcard. This is deliberately strict: picking the wrong JetPack's GPU wheel for the running
    device is a worse failure mode than falling back to CPU Safe Mode."""
    for field in PROFILE_MATCH_FIELDS:
        d, p = detected.get(field), profile.get(field)
        if d is None or p is None or d != p:
            return False
    return True


def find_matching_verified_profile(detected: dict, profiles: list) -> dict | None:
    """Only ever considers profiles with verified is True -- see profiles' own docstring in
    config/jetson_agx_orin_profiles.json: verified=true is only ever set from a real device run,
    never guessed. Returns the first exact match, or None."""
    for profile in profiles:
        if profile.get('verified') and profile_matches(detected, profile):
            return profile
    return None


def load_profiles(path: Path | None = None) -> list:
    path = path or (ROOT / 'config' / 'jetson_agx_orin_profiles.json')
    return json.loads(path.read_text(encoding='utf-8'))['profiles']


def load_ort_candidates(path: Path | None = None) -> list:
    path = path or (ROOT / 'config' / 'jetson_ort_candidates.json')
    return json.loads(path.read_text(encoding='utf-8'))['candidates']


def resolve_ort_candidate_for_profile(profile: dict | None, candidates: list) -> dict | None:
    """The ONLY sanctioned path from a verified deployment profile to an actual ONNX Runtime
    install: look up profile['ort_candidate_id'] in the candidates list by id. Deliberately does
    NOT fall back to matching environment fields directly against candidates -- see this module's
    and config/jetson_agx_orin_profiles.json's docstrings for why (a verified profile proves the
    ENVIRONMENT was confirmed on real hardware; it does not by itself supply a working wheel, and a
    candidate must be explicitly linked to that specific verified profile, never inferred)."""
    if profile is None:
        return None
    candidate_id = profile.get('ort_candidate_id')
    if not candidate_id:
        return None
    for c in candidates:
        if c.get('id') == candidate_id and c.get('install_method') is not None:
            return c
    return None


# --- Provider requirement name mapping ------------------------------------------------------------
PROVIDER_NAMES = {'cpu': 'CPUExecutionProvider', 'cuda': 'CUDAExecutionProvider', 'tensorrt': 'TensorrtExecutionProvider'}


def check_gpu_requirement(session_providers: list, require_gpu: bool, require_tensorrt: bool) -> tuple:
    """Returns (ok, reason). --require-tensorrt implies --require-gpu's CUDA check is not enough on
    its own -- TensorrtExecutionProvider specifically must be the session's actual provider set.
    A session that silently fell back to CPU never satisfies either flag.

    NOTE: this checks session REGISTRATION only (session.get_providers()). The stricter gate
    deploy_jetson_agx.sh actually enforces for --require-gpu/--require-tensorrt additionally
    requires EXECUTION_VERIFIED status (see classify_provider_status/count_nodes_by_provider
    below) -- a provider merely being registered on the session is not, by itself, proof any node
    actually ran on it."""
    if require_tensorrt:
        if 'TensorrtExecutionProvider' in session_providers:
            return True, None
        return False, 'TensorrtExecutionProvider was required but the session did not use it'
    if require_gpu:
        if 'CUDAExecutionProvider' in session_providers or 'TensorrtExecutionProvider' in session_providers:
            return True, None
        return False, 'A GPU execution provider was required but the session used CPU only'
    return True, None


def check_gpu_requirement_by_status(provider_status: dict, require_gpu: bool, require_tensorrt: bool) -> tuple:
    """The STRICTER gate deploy_jetson_agx.sh actually enforces for --require-gpu/--require-tensorrt:
    takes the provider_status dict scripts/verify_jetson_agx_gpu.py's onnxruntime_report() produces
    (each of CPUExecutionProvider/CUDAExecutionProvider/TensorrtExecutionProvider mapped to one of
    VERIFICATION_STATUSES), and requires EXECUTION_VERIFIED specifically -- never satisfied by
    AVAILABLE/SESSION_REGISTERED/INFERENCE_PASSED/FALLBACK, which all fall short of real per-node
    execution proof. --require-tensorrt is never satisfied by a CUDA-only fallback, however verified
    CUDA's own status is. Returns (ok, reason)."""
    if require_tensorrt:
        status = provider_status.get('TensorrtExecutionProvider')
        if status == 'EXECUTION_VERIFIED':
            return True, None
        return False, f'--require-tensorrt: TensorrtExecutionProvider status={status!r}, need EXECUTION_VERIFIED'
    if require_gpu:
        cuda_status = provider_status.get('CUDAExecutionProvider')
        trt_status = provider_status.get('TensorrtExecutionProvider')
        if cuda_status == 'EXECUTION_VERIFIED' or trt_status == 'EXECUTION_VERIFIED':
            return True, None
        return False, (f'--require-gpu: CUDA status={cuda_status!r}, TensorRT status={trt_status!r}, '
                        'need EXECUTION_VERIFIED on at least one')
    return True, None


# --- Distinguishing a native ONNX Runtime crash from an ordinary Python exception -----------------
# Confirmed for real on a Jetson AGX Orin + JetPack 5.1.2 device: the generic PyPI ARM64 CPU
# onnxruntime==1.19.2 wheel (installed as the JetPack5 CPU fallback) native-crashed during
# session/inference use -- `Aborted (core dumped)`, a C++ `Assertion '__n < this->size()' failed`
# inside libstdc++'s std::vector::operator[], not a Python exception at all. The deploy flow used
# to run inference in-process and treat ANY resulting failure the same way ("CPU/GPU result
# equivalence FAILED"), which is actively misleading for a crash that never got anywhere near
# comparing two results. Everything below exists so a native crash is (a) isolated in its own
# subprocess so it can never take the calling script down with it, and (b) reported as exactly what
# it is, distinct from every other failure mode.
DEPLOYMENT_FAILURE_STATUSES = (
    'ORT_IMPORT_FAILED', 'ORT_NATIVE_RUNTIME_CRASH', 'MODEL_LOAD_FAILED', 'INFERENCE_FAILED', 'CPU_GPU_MISMATCH',
    # Not returned by classify_ort_smoke_test itself (a hang, not a crash or exception) -- the
    # caller (verify_jetson_agx_gpu.py's subprocess.run(..., timeout=...)) reports this one directly
    # when the smoke-test subprocess simply never finishes, so it's never silently ignored either.
    'ORT_SMOKE_TEST_TIMEOUT',
)


def classify_subprocess_termination(returncode: int) -> str:
    """'OK' / 'PYTHON_EXCEPTION' / 'NATIVE_CRASH', from a subprocess.run() returncode alone.

    On POSIX, subprocess.run's .returncode is NEGATIVE exactly when the child was killed by a
    signal (== -signal_number -- e.g. -6 for SIGABRT/`abort()`, -11 for SIGSEGV); an ordinary
    uncaught Python exception always exits with code 1 (positive), never a signal. This is the only
    reliable way to tell "the program ran and raised" apart from "the process was killed out from
    under it" using just the exit status."""
    if returncode == 0:
        return 'OK'
    if returncode < 0:
        return 'NATIVE_CRASH'
    return 'PYTHON_EXCEPTION'


def parse_ort_smoke_test_progress(stdout_text: str) -> list:
    """Parses scripts/ort_smoke_test.py's stdout -- one flushed JSON object per completed stage
    (`{"stage": "import"/"model_load"/"inference", "ok": true, ...}`) -- into a list of stage dicts.
    A crash mid-write leaves a partial or missing trailing line; that line is silently dropped
    (never guessed at) rather than raising, so the caller sees exactly how far it got before dying."""
    stages = []
    for line in (stdout_text or '').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            stages.append(json.loads(line))
        except Exception:
            break
    return stages


def classify_ort_smoke_test(returncode: int, stdout_text: str) -> dict:
    """The single place that turns an `scripts/ort_smoke_test.py [--full]` subprocess's raw
    (returncode, stdout) into one of DEPLOYMENT_FAILURE_STATUSES, or 'OK'. Never reports
    'CPU_GPU_MISMATCH' here -- that status belongs only to compare_cpu_gpu_results.py, once BOTH
    sides of a comparison actually produced a real result; something that crashed before even
    finishing a single import/inference never gets that label.

    Returns {'status': ..., 'last_stage_completed': 'import'|'model_load'|'inference'|None,
    'stages': [...]} -- last_stage_completed is a diagnostic aid (e.g. crashing right after 'import'
    completed but before 'model_load' printed means the crash happened during model/session
    construction, not the bare `import onnxruntime` itself)."""
    stages = parse_ort_smoke_test_progress(stdout_text)
    last_stage = stages[-1]['stage'] if stages else None
    termination = classify_subprocess_termination(returncode)

    if returncode == 0 and last_stage in ('import', 'model_load', 'inference'):
        return {'status': 'OK', 'last_stage_completed': last_stage, 'stages': stages}
    if termination == 'NATIVE_CRASH':
        return {'status': 'ORT_NATIVE_RUNTIME_CRASH', 'last_stage_completed': last_stage, 'stages': stages}
    if last_stage is None:
        return {'status': 'ORT_IMPORT_FAILED', 'last_stage_completed': None, 'stages': stages}
    if last_stage == 'import':
        return {'status': 'MODEL_LOAD_FAILED', 'last_stage_completed': last_stage, 'stages': stages}
    if last_stage == 'model_load':
        return {'status': 'INFERENCE_FAILED', 'last_stage_completed': last_stage, 'stages': stages}
    # Reached 'inference' in the stage list but returncode != 0 and wasn't a signal -- something
    # went wrong after printing that marker but before a clean exit; still not a crash, still not a
    # silent success. Treated as INFERENCE_FAILED rather than invented as anything more specific.
    return {'status': 'INFERENCE_FAILED', 'last_stage_completed': last_stage, 'stages': stages}


# --- Unified verification status vocabulary -------------------------------------------------------
# A ladder from "never seen" to "proven to have actually executed a node" -- FALLBACK is the one
# side-branch (the provider WAS available, but the live session ended up using something else).
# "the provider name appears in get_available_providers()/session.get_providers()" is NEVER, by
# itself, reported as more than AVAILABLE/SESSION_REGISTERED -- EXECUTION_VERIFIED requires actual
# per-node profiling evidence (see count_nodes_by_provider), and INFERENCE_PASSED (a real forward
# pass succeeded end-to-end) sits between the two because a real deployment may not always be able
# to gather per-node attribution (e.g. an older ORT build whose profiling JSON omits the `provider`
# arg on Node events) and should not be reported as "not verified" purely for that reason -- but it
# is also never silently upgraded to EXECUTION_VERIFIED without that evidence.
VERIFICATION_STATUSES = ('NOT_AVAILABLE', 'AVAILABLE', 'SESSION_REGISTERED', 'FALLBACK', 'INFERENCE_PASSED', 'EXECUTION_VERIFIED')


def classify_provider_status(provider_name: str, *, available_providers: list, session_providers: list | None = None,
                              inference_ok: bool | None = None, nodes_executed: int | None = None) -> str:
    if provider_name not in available_providers:
        return 'NOT_AVAILABLE'
    if session_providers is None:
        return 'AVAILABLE'
    if provider_name not in session_providers:
        return 'FALLBACK'
    if not inference_ok:
        return 'SESSION_REGISTERED'
    if nodes_executed is None:
        return 'INFERENCE_PASSED'
    return 'EXECUTION_VERIFIED' if nodes_executed > 0 else 'INFERENCE_PASSED'


def count_nodes_by_provider(profiling_json_path) -> dict:
    """Parses an ONNX Runtime profiling trace (from SessionOptions.enable_profiling=True +
    session.end_profiling()) and counts 'Node' category events per the `provider` field ORT
    attaches to each node's profiling event args. Returns {} (never raises) if the file can't be
    read/parsed, or if this ORT build's profiling output doesn't include a `provider` arg per node
    -- callers must treat an empty dict as 'node-level execution not proven', not as zero nodes
    definitely having run on every provider."""
    try:
        events = json.loads(Path(profiling_json_path).read_text(encoding='utf-8'))
    except Exception:
        return {}
    counts: dict = {}
    for e in events if isinstance(events, list) else []:
        if not isinstance(e, dict) or e.get('cat') != 'Node':
            continue
        provider = (e.get('args') or {}).get('provider')
        if provider:
            counts[provider] = counts.get(provider, 0) + 1
    return counts
