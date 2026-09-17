#!/usr/bin/env python3
"""Standalone Jetson/JetPack/L4T/CUDA/TensorRT/NVIDIA-stack detector.

Deliberately has ZERO dependency on onnxruntime or any backend package -- it must be able to run
on a bare Python 3 interpreter before any Jetson-specific dependency is installed, since
deploy_jetson_agx.sh needs this detector's output to decide WHICH onnxruntime package (if any) to
install in the first place.

Every field is read from real system state. A missing tool (e.g. no `nvcc` on a runtime-only
JetPack image, no `tegrastats` off Jetson hardware) is reported as null/None, never guessed or
assumed absent-therefore-CPU-only -- multiple sources are cross-checked where possible (see
docstring on jetson_common.classify_cuda_family). Writes runtime/jetson_environment.json
(gitignored) and also prints the same JSON to stdout for scripting.

Usage: python3 scripts/detect_jetson_env.py [--allow-other-orin] [--out PATH]
"""
import argparse, json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jetson_common as jc


def detect_nvidia_stack():
    nv_tegra_release = jc.read_file('/etc/nv_tegra_release')
    l4t_core = jc.run(['dpkg-query', '-W', 'nvidia-l4t-core'])
    jetpack_pkg = jc.run(['bash', '-c', 'dpkg -l | grep -i nvidia-jetpack || true'])
    nvcc_out = jc.run(['nvcc', '--version'])
    cuda_version_json = jc.read_file('/usr/local/cuda/version.json')
    cuda_version_str = jc.extract_cuda_version_from_nvcc(nvcc_out)
    if not cuda_version_str and cuda_version_json:
        try:
            cuda_version_str = json.loads(cuda_version_json).get('cuda', {}).get('version')
        except Exception:
            pass
    cudnn_pkgs = jc.run(['bash', '-c', 'dpkg -l | grep -i cudnn || true'])
    tensorrt_pkgs = jc.run(['bash', '-c', "dpkg -l | grep -E 'tensorrt|libnvinfer' || true"])
    tensorrt_python_version = None
    try:
        import tensorrt as trt  # noqa: local optional import, may not exist off-Jetson
        tensorrt_python_version = trt.__version__
    except Exception:
        pass
    l4t_family = jc.classify_l4t_family(nv_tegra_release)
    cuda_family = jc.classify_cuda_family(cuda_version_str)
    family_agreement = (l4t_family['jetpack_family'] is None or cuda_family['jetpack_family'] is None
                         or l4t_family['jetpack_family'] == cuda_family['jetpack_family'])
    return {
        'nv_tegra_release_raw': nv_tegra_release,
        'nvidia_l4t_core_package': l4t_core,
        'nvidia_jetpack_package': jetpack_pkg,
        'l4t': l4t_family,
        'nvcc_version_raw': nvcc_out,
        'cuda_version': cuda_version_str,
        'cuda': cuda_family,
        'jetpack_family_agreement': family_agreement,
        'cudnn_packages_raw': cudnn_pkgs,
        'cudnn_major': jc.extract_cudnn_major(cudnn_pkgs),
        'tensorrt_packages_raw': tensorrt_pkgs,
        **jc.extract_tensorrt_version(tensorrt_pkgs),
        'tensorrt_python_version': tensorrt_python_version,
    }


def detect_system():
    return {
        'python_version': sys.version.split()[0],
        'python_abi': jc.python_abi_tag(),
        'os_release': jc.read_file('/etc/os-release'),
        'kernel': jc.run(['uname', '-a']),
        'free_disk_kb_root': _disk_free_kb('/'),
        'free_memory_kb': _mem_free_kb(),
    }


def _disk_free_kb(path):
    try:
        usage = shutil.disk_usage(path)
        return usage.free // 1024
    except Exception:
        return None


def _mem_free_kb():
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemAvailable:'):
                return int(line.split()[1])
    except Exception:
        pass
    return None


def detect_nvidia_tools():
    nvpmodel = jc.run(['nvpmodel', '-q'])
    tegrastats_present = shutil.which('tegrastats') is not None
    docker_version = jc.run(['docker', '--version'])
    docker_info_runtime = jc.run(['bash', '-c', "docker info 2>/dev/null | grep -i runtime || true"])
    return {
        'nvpmodel_query': nvpmodel,
        'jetson_clocks_show': jc.run(['jetson_clocks', '--show']),
        'tegrastats_available': tegrastats_present,
        'docker_version': docker_version,
        'docker_nvidia_runtime_configured': bool(docker_info_runtime and 'nvidia' in docker_info_runtime.lower()),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--allow-other-orin', action='store_true',
                     help='Also treat Orin NX/Nano as a supported test target (default target is AGX Orin only)')
    ap.add_argument('--out', default=None, help='Write JSON here in addition to stdout (default: runtime/jetson_environment.json)')
    args = ap.parse_args()

    report = {
        'hardware': jc.detect_hardware(allow_other_orin=args.allow_other_orin),
        'nvidia_stack': detect_nvidia_stack(),
        'system': detect_system(),
        'nvidia_tools': detect_nvidia_tools(),
    }

    out_path = Path(args.out) if args.out else Path(__file__).resolve().parents[1] / 'runtime' / 'jetson_environment.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report['hardware']['hardware_is_agx_orin']:
        print(f"\nNOTE: this host is not a Jetson AGX Orin (orin_family={report['hardware']['orin_family']!r}). "
              "Every field above describes THIS machine only -- run this script ON the target device "
              "before trusting any JetPack/CUDA/TensorRT-related field for deployment decisions.",
              file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
