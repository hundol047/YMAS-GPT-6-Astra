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
# Deliberately a RANGE-based classifier, not a hardcoded exact-version assumption: it recognizes
# which release *family* a detected L4T/CUDA major version belongs to without asserting a specific
# minor/patch version ever shipped. New minor releases within a family need no code change here;
# a genuinely new major generation needs a new range added, never a guessed version number.
def classify_l4t_family(nv_tegra_release_text: str | None) -> dict:
    if not nv_tegra_release_text:
        return {'l4t_major': None, 'l4t_revision': None, 'jetpack_family': None}
    major_match = re.search(r'R(\d+)', nv_tegra_release_text)
    rev_match = re.search(r'REVISION:\s*([\d.]+)', nv_tegra_release_text)
    major = int(major_match.group(1)) if major_match else None
    revision = rev_match.group(1) if rev_match else None
    family = None
    if major is not None:
        if 34 <= major <= 36:
            family = 'jetpack6'
        elif 37 <= major <= 39:
            family = 'jetpack7'
    return {'l4t_major': major, 'l4t_revision': revision, 'jetpack_family': family}


def classify_cuda_family(cuda_version_str: str | None) -> dict:
    """cuda_version_str is expected like '12.6' or '13.0' (from nvcc --version or
    /usr/local/cuda/version.json) -- returns the major/minor split and which JetPack family that
    CUDA major version is associated with, purely for cross-checking against the L4T-derived
    family (a mismatch between the two is a signal worth surfacing, not silently ignored)."""
    if not cuda_version_str:
        return {'cuda_major': None, 'cuda_minor': None, 'jetpack_family': None}
    m = re.search(r'(\d+)\.(\d+)', cuda_version_str)
    if not m:
        return {'cuda_major': None, 'cuda_minor': None, 'jetpack_family': None}
    major, minor = int(m.group(1)), int(m.group(2))
    family = 'jetpack6' if major == 12 else 'jetpack7' if major == 13 else None
    return {'cuda_major': major, 'cuda_minor': minor, 'jetpack_family': family}


def extract_cuda_version_from_nvcc(nvcc_output: str | None) -> str | None:
    if not nvcc_output:
        return None
    m = re.search(r'[Rr]elease\s+(\d+\.\d+)', nvcc_output)
    return m.group(1) if m else None


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
    import sys
    return f'cp{sys.version_info.major}{sys.version_info.minor}'


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


# --- Provider requirement name mapping ------------------------------------------------------------
PROVIDER_NAMES = {'cpu': 'CPUExecutionProvider', 'cuda': 'CUDAExecutionProvider', 'tensorrt': 'TensorrtExecutionProvider'}


def check_gpu_requirement(session_providers: list, require_gpu: bool, require_tensorrt: bool) -> tuple:
    """Returns (ok, reason). --require-tensorrt implies --require-gpu's CUDA check is not enough on
    its own -- TensorrtExecutionProvider specifically must be the session's actual provider set.
    A session that silently fell back to CPU never satisfies either flag."""
    if require_tensorrt:
        if 'TensorrtExecutionProvider' in session_providers:
            return True, None
        return False, 'TensorrtExecutionProvider was required but the session did not use it'
    if require_gpu:
        if 'CUDAExecutionProvider' in session_providers or 'TensorrtExecutionProvider' in session_providers:
            return True, None
        return False, 'A GPU execution provider was required but the session used CPU only'
    return True, None
