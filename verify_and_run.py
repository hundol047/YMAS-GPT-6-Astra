"""
SynexAgent 실행 전 검증 + 실행 스크립트
사용법: 이 파일을 SynexAgent/ 최상위 폴더(README.md 옆)에 넣고

    python verify_and_run.py            # 검증만
    python verify_and_run.py --run      # 검증 통과 시 백엔드 서버까지 실행
    python verify_and_run.py --install  # 부족한 pip 패키지 자동 설치 후 검증
"""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
SCRIPTS = ROOT / "scripts"

REQUIRED_PACKAGES = ["fastapi", "uvicorn", "onnxruntime", "numpy", "pydantic"]
REQUIRED_FILES = [
    BACKEND / "requirements.txt",
    BACKEND / "app" / "main.py",
    BACKEND / "models" / "risk_model_deep_v3.onnx",
    BACKEND / "data" / "patients.json",
    BACKEND / "data" / "drug_catalog.json",
    BACKEND / "data" / "rules.json",
]

results = []  # (label, ok: bool, detail: str)


def check(label, ok, detail=""):
    results.append((label, ok, detail))
    mark = "OK " if ok else "FAIL"
    print(f"[{mark}] {label}" + (f" - {detail}" if detail else ""))
    return ok


def _detect_jetson_agx_orin_jetpack5_cp38():
    """The ONLY exception to 'PC requires Python >= 3.10': a CONFIRMED Jetson AGX Orin running
    JetPack 5 (L4T 35.x) on Python 3.8/cp38 -- see backend/requirements-jetpack5.txt and
    docs/JETSON_DEPLOYMENT.md for why that's a real, hardware-detected compatibility path, not a
    blanket 'Python 3.8 is fine everywhere' relaxation. A generic x86 PC that merely happens to run
    Python 3.8 must still fail this check -- only real AGX Orin + JetPack 5 hardware qualifies.
    Returns a dict with at least 'qualifies': bool; never raises (any detection failure -> False)."""
    try:
        sys.path.insert(0, str(SCRIPTS))
        import jetson_common as jc
        hw = jc.detect_hardware()
        l4t = jc.classify_l4t_family(jc.read_file('/etc/nv_tegra_release'))
        qualifies = (hw['hardware_is_agx_orin'] and l4t['jetpack_family'] == 'jetpack5'
                     and sys.version_info[:2] == (3, 8))
        return {'qualifies': qualifies, 'orin_family': hw['orin_family'],
                'l4t_major': l4t['l4t_major'], 'jetpack_family': l4t['jetpack_family']}
    except Exception as e:
        return {'qualifies': False, 'error': str(e)}


def check_python_version():
    if sys.version_info >= (3, 10):
        check("Python >= 3.10 (PC 표준 경로)", True, f"현재 {sys.version.split()[0]}")
        return
    jp5 = _detect_jetson_agx_orin_jetpack5_cp38()
    if jp5['qualifies']:
        check("Python 3.8 (확인된 Jetson AGX Orin + JetPack 5 호환 경로)", True,
              f"현재 {sys.version.split()[0]} on {jp5['orin_family']}, L4T {jp5['l4t_major']}, "
              f"jetpack_family={jp5['jetpack_family']} -- backend/requirements-jetpack5.txt 사용")
        return
    check("Python >= 3.10 (또는 확인된 Jetson AGX Orin + JetPack 5 + Python 3.8)", False,
          f"현재 {sys.version.split()[0]} -- 이 조합은 지원되지 않습니다. 일반 PC는 Python 3.10 이상이 "
          f"필요하고, Python 3.8은 실제로 감지된 Jetson AGX Orin + JetPack 5 장비에서만 예외로 허용됩니다"
          + (f" (감지 결과: {jp5})" if 'error' not in jp5 else ""))


def check_files():
    for f in REQUIRED_FILES:
        check(f"파일 존재: {f.relative_to(ROOT)}", f.exists())


def check_packages(auto_install=False):
    missing = []
    for pkg in REQUIRED_PACKAGES:
        found = importlib.util.find_spec(pkg) is not None
        check(f"패키지: {pkg}", found)
        if not found:
            missing.append(pkg)
    if missing and auto_install:
        print(f"\n미설치 패키지 설치 중: {missing}")
        jp5 = _detect_jetson_agx_orin_jetpack5_cp38()
        if jp5['qualifies']:
            # JetPack 5/cp38 path: core deps + the cp38-compatible CPU ONNX Runtime pin (never
            # requirements.txt's onnxruntime==1.30.0, which has no cp38 wheel at all).
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r",
                                    str(BACKEND / "requirements-jetpack5.txt")])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r",
                                    str(BACKEND / "requirements-jetpack5-ort-cpu.txt")])
        else:
            req = BACKEND / "requirements.txt"
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req)])
        for pkg in missing:
            check(f"재확인: {pkg}", importlib.util.find_spec(pkg) is not None)
    return missing


def check_node_npm():
    node = shutil.which("node")
    npm = shutil.which("npm")
    check("node 설치됨", node is not None, node or "PATH에 없음")
    check("npm 설치됨", npm is not None, npm or "PATH에 없음")
    check("frontend/dist 빌드됨", (FRONTEND / "dist" / "index.html").exists(),
          "없으면: cd frontend && npm ci && npm run build")


def run_model_smoke_test():
    """실제 모델 로드 + 데모 환자 추론까지 돌려서 백엔드 로직이 살아있는지 확인."""
    sys.path.insert(0, str(BACKEND))
    try:
        from app.services.risk_inference import RiskEngine
        from app.services.emr_adapter import DemoAdapter
        from app.services.clinical_agent import ClinicalAgent
    except Exception as e:
        check("백엔드 모듈 임포트", False, str(e))
        return

    try:
        engine = RiskEngine()
        health = engine.health()
        check("ONNX 모델 로드 및 health()", True, json.dumps(health, ensure_ascii=False))
    except Exception as e:
        check("ONNX 모델 로드", False, str(e))
        return

    try:
        agent = ClinicalAgent(engine)
        patients = DemoAdapter().list()
        for p in patients:
            a = agent.run(p)
            print(f"    - {p.id} risk={a['risk']['risk_probability']:.4f}")
        check("데모 환자 5명 추론 성공", True, f"{len(patients)}명 처리")
    except Exception as e:
        check("데모 환자 추론", False, str(e))


def run_server():
    print("\n백엔드 서버 실행: http://127.0.0.1:8000  (Ctrl+C로 종료)")
    subprocess.call([
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--app-dir", str(BACKEND),
        "--host", "127.0.0.1", "--port", "8000",
    ])


def main():
    auto_install = "--install" in sys.argv
    do_run = "--run" in sys.argv

    print("=== 1. Python 버전 ===")
    check_python_version()

    print("\n=== 2. 필수 파일 존재 확인 ===")
    check_files()

    print("\n=== 3. 필수 pip 패키지 확인 ===")
    check_packages(auto_install=auto_install)

    print("\n=== 4. Node/npm/프론트엔드 빌드 확인 ===")
    check_node_npm()

    print("\n=== 5. 모델 로드 + 추론 스모크 테스트 ===")
    run_model_smoke_test()

    print("\n=== 결과 요약 ===")
    failed = [r for r in results if not r[1]]
    total = len(results)
    print(f"{total - len(failed)}/{total} 통과")
    if failed:
        print("실패 항목:")
        for label, _, detail in failed:
            print(f"  - {label} ({detail})")

    if not failed and do_run:
        run_server()
    elif failed and do_run:
        print("\n검증 실패 항목이 있어 서버를 실행하지 않습니다. 위 실패 항목을 먼저 해결하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
