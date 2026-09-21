"""Python 3.8 / Jetson AGX Orin + JetPack 5.1.2 compatibility path tests.

These run on whatever Python this test suite itself runs under (this development container has no
Python 3.8 interpreter available -- see docs/JETSON_DEPLOYMENT.md's Root Cause section) -- they
verify the DETECTION LOGIC and the SHAPE of the compatibility artifacts (requirements files,
verify_and_run.py's branch), not an actual Python-3.8 install. The AST-based checks below are the
closest thing to a real "does this parse/import cleanly on 3.8" proof available without a 3.8
interpreter: ast.parse(..., feature_version=(3, 8)) uses CPython's own grammar-version-aware parser.
"""
import ast
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
SCRIPTS = ROOT / "scripts"


# --- requirements-jetpack5.txt / requirements-jetpack5-ort-cpu.txt shape --------------------------

def test_requirements_jetpack5_file_exists_and_is_separate_from_pc_requirements():
    jp5 = BACKEND / "requirements-jetpack5.txt"
    core = BACKEND / "requirements-core.txt"
    assert jp5.exists()
    assert jp5.read_text(encoding="utf-8") != core.read_text(encoding="utf-8")


def test_requirements_jetpack5_pins_are_exact_and_never_reference_onnxruntime():
    lines = [l.strip() for l in (BACKEND / "requirements-jetpack5.txt").read_text(encoding="utf-8").splitlines()]
    pkg_lines = [l for l in lines if l and not l.startswith("#")]
    assert pkg_lines, "requirements-jetpack5.txt has no package pins"
    for line in pkg_lines:
        assert "==" in line, f"{line!r} is not an exact pin"
        assert not line.lower().startswith("onnxruntime"), (
            "ONNX Runtime must never be in requirements-jetpack5.txt -- GPU/CPU selection needs "
            "the verified-profile gate / requirements-jetpack5-ort-cpu.txt, not a blanket core pin"
        )
    names = {l.split("==")[0].lower() for l in pkg_lines}
    for required in ("fastapi", "uvicorn", "numpy", "pydantic", "httpx", "pyjwt", "cryptography", "redis"):
        assert required in names, f"requirements-jetpack5.txt is missing a pin for {required}"


def test_requirements_jetpack5_ort_cpu_pins_a_cp38_compatible_onnxruntime():
    path = BACKEND / "requirements-jetpack5-ort-cpu.txt"
    assert path.exists()
    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    assert len(lines) == 1 and lines[0].startswith("onnxruntime==")
    # The PC path's own onnxruntime pin (requirements.txt) must be a DIFFERENT (newer) version --
    # that PC pin has no cp38 wheel at all, which is exactly why this separate file exists.
    pc_pin = next(l for l in (BACKEND / "requirements.txt").read_text(encoding="utf-8").splitlines()
                  if l.strip().startswith("onnxruntime=="))
    assert lines[0] != pc_pin.strip()


# --- verify_and_run.py's Jetson AGX Orin + JetPack 5 + cp38 exception path ------------------------

@pytest.fixture
def verify_and_run_module():
    spec = importlib.util.spec_from_file_location("verify_and_run", ROOT / "verify_and_run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_detects_qualifying_jetson_agx_orin_jetpack5_cp38(verify_and_run_module, monkeypatch):
    sys.path.insert(0, str(SCRIPTS))
    import jetson_common as jc
    monkeypatch.setattr(jc, "detect_hardware", lambda: {"hardware_is_agx_orin": True, "orin_family": "AGX Orin"})
    monkeypatch.setattr(jc, "classify_l4t_family", lambda _: {"l4t_major": 35, "jetpack_family": "jetpack5"})
    monkeypatch.setattr(jc, "read_file", lambda _: "some nv_tegra_release text")
    monkeypatch.setattr(sys, "version_info", (3, 8, 10, "final", 0))
    result = verify_and_run_module._detect_jetson_agx_orin_jetpack5_cp38()
    assert result["qualifies"] is True
    assert result["jetpack_family"] == "jetpack5"


def test_does_not_qualify_on_non_agx_orin_hardware_even_with_python38(verify_and_run_module, monkeypatch):
    sys.path.insert(0, str(SCRIPTS))
    import jetson_common as jc
    monkeypatch.setattr(jc, "detect_hardware", lambda: {"hardware_is_agx_orin": False, "orin_family": None})
    monkeypatch.setattr(jc, "classify_l4t_family", lambda _: {"l4t_major": None, "jetpack_family": None})
    monkeypatch.setattr(jc, "read_file", lambda _: None)
    monkeypatch.setattr(sys, "version_info", (3, 8, 10, "final", 0))
    result = verify_and_run_module._detect_jetson_agx_orin_jetpack5_cp38()
    assert result["qualifies"] is False


def test_does_not_qualify_on_agx_orin_with_jetpack6_not_5(verify_and_run_module, monkeypatch):
    sys.path.insert(0, str(SCRIPTS))
    import jetson_common as jc
    monkeypatch.setattr(jc, "detect_hardware", lambda: {"hardware_is_agx_orin": True, "orin_family": "AGX Orin"})
    monkeypatch.setattr(jc, "classify_l4t_family", lambda _: {"l4t_major": 36, "jetpack_family": "jetpack6"})
    monkeypatch.setattr(jc, "read_file", lambda _: "text")
    monkeypatch.setattr(sys, "version_info", (3, 8, 10, "final", 0))
    result = verify_and_run_module._detect_jetson_agx_orin_jetpack5_cp38()
    assert result["qualifies"] is False


def test_does_not_qualify_on_agx_orin_jetpack5_with_a_newer_python(verify_and_run_module, monkeypatch):
    # A real AGX Orin JetPack 5 device someone later upgraded to a non-default newer Python must NOT
    # silently qualify -- this path is specifically for the confirmed cp38 default, not "any Python
    # on JetPack 5 hardware".
    sys.path.insert(0, str(SCRIPTS))
    import jetson_common as jc
    monkeypatch.setattr(jc, "detect_hardware", lambda: {"hardware_is_agx_orin": True, "orin_family": "AGX Orin"})
    monkeypatch.setattr(jc, "classify_l4t_family", lambda _: {"l4t_major": 35, "jetpack_family": "jetpack5"})
    monkeypatch.setattr(jc, "read_file", lambda _: "text")
    monkeypatch.setattr(sys, "version_info", (3, 11, 0, "final", 0))
    result = verify_and_run_module._detect_jetson_agx_orin_jetpack5_cp38()
    assert result["qualifies"] is False


def test_generic_x86_python38_never_qualifies(verify_and_run_module, monkeypatch):
    # The one thing this whole exception path must never become: "Python 3.8 is fine everywhere".
    sys.path.insert(0, str(SCRIPTS))
    import jetson_common as jc
    monkeypatch.setattr(jc, "detect_hardware", lambda: {"hardware_is_agx_orin": False, "orin_family": None})
    monkeypatch.setattr(jc, "classify_l4t_family", lambda _: {"l4t_major": None, "jetpack_family": None})
    monkeypatch.setattr(jc, "read_file", lambda _: None)
    monkeypatch.setattr(sys, "version_info", (3, 8, 10, "final", 0))
    result = verify_and_run_module._detect_jetson_agx_orin_jetpack5_cp38()
    assert result["qualifies"] is False


def test_pc_path_python_check_does_not_even_look_at_jetson_detection(verify_and_run_module, monkeypatch):
    """On a real Python >= 3.10 host, check_python_version must short-circuit to the PC path without
    needing (or being able) to call Jetson hardware detection at all."""
    called = {"hit": False}

    def _boom():
        called["hit"] = True
        raise AssertionError("should never be called on a Python >= 3.10 host")

    monkeypatch.setattr(verify_and_run_module, "_detect_jetson_agx_orin_jetpack5_cp38", _boom)
    verify_and_run_module.results.clear()
    verify_and_run_module.check_python_version()
    assert called["hit"] is False
    label, ok, _ = verify_and_run_module.results[-1]
    assert ok is True
    assert "PC" in label


# --- Python 3.8 syntax/runtime-evaluation compatibility (no interpreter needed) -------------------

def _iter_py_files():
    for base in (BACKEND / "app", SCRIPTS):
        yield from base.rglob("*.py")


def test_every_backend_and_script_file_parses_under_python38_grammar():
    bad = []
    for f in _iter_py_files():
        try:
            ast.parse(f.read_text(encoding="utf-8"), filename=str(f), feature_version=(3, 8))
        except SyntaxError as e:
            bad.append((str(f.relative_to(ROOT)), str(e)))
    assert not bad, f"Python 3.8-incompatible syntax found: {bad}"


def _has_future_annotations(tree):
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            if any(a.name == "annotations" for a in node.names):
                return True
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        else:
            break
    return False


def _annotation_nodes(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                yield node.returns
            for a in list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs):
                if a.annotation is not None:
                    yield a.annotation
            if node.args.vararg and node.args.vararg.annotation is not None:
                yield node.args.vararg.annotation
            if node.args.kwarg and node.args.kwarg.annotation is not None:
                yield node.args.kwarg.annotation
        elif isinstance(node, ast.AnnAssign):
            yield node.annotation


def _is_risky(node):
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id in (
        "list", "dict", "tuple", "set", "frozenset"
    ):
        return "PEP585 builtin generic subscript (needs Python >= 3.9)"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return "PEP604 union operator (needs Python >= 3.10)"
    return None


def test_no_unprotected_39_or_310_only_annotation_syntax_in_backend_or_scripts():
    """A `list[str]`/`int | None`-shaped annotation is only safe on Python 3.8 if the module defers
    annotation evaluation (`from __future__ import annotations`) AND nothing resolves those hints
    at runtime (Pydantic model fields / FastAPI route signatures always do resolve them, which is
    why schemas.py and main.py use typing.Optional/List explicitly instead of relying on this)."""
    findings = []
    for f in _iter_py_files():
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        if _has_future_annotations(tree):
            continue
        for ann in _annotation_nodes(tree):
            for node in ast.walk(ann):
                reason = _is_risky(node)
                if reason:
                    findings.append(f"{f.relative_to(ROOT)}:{node.lineno} {reason}")
                    break
    assert not findings, f"Risky unprotected annotation syntax: {findings}"


def test_schemas_module_uses_typing_optional_not_pep604_union():
    """schemas.py fields are Pydantic v2 models -- Pydantic resolves every field annotation to a
    real type object when building its schema, so PEP 604 `X | None` there would break on Python
    3.8 even with `from __future__ import annotations` (postponed evaluation only defers WHEN it's
    evaluated, not what it evaluates to)."""
    src = (BACKEND / "app" / "schemas.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            pytest.fail(f"schemas.py:{node.lineno} uses a PEP 604 `|` union -- must use typing.Optional/Union")


# --- config/jetson_agx_orin_profiles.json's real AGX Orin + JetPack 5.1.2 entry -------------------

def test_real_agx_orin_jetpack512_environment_is_recorded_but_not_fabricated_verified():
    profiles = json.loads((ROOT / "config" / "jetson_agx_orin_profiles.json").read_text(encoding="utf-8"))["profiles"]
    entry = next((p for p in profiles if p["id"] == "agx-orin-jp512-cp38-environment-confirmed"), None)
    assert entry is not None, "expected the real confirmed Jetson AGX Orin + JetPack 5.1.2 profile entry"
    assert entry["l4t_major"] == 35
    assert entry["cuda_major"] == 11 and entry["cuda_minor"] == 4
    assert entry["cudnn_major"] == 8
    assert entry["tensorrt_major"] == 8 and entry["tensorrt_minor"] == 5
    assert entry["python_abi"] == "cp38"
    assert entry["arch"] == "aarch64"
    # Environment confirmation is NOT GPU execution verification -- never fabricated as verified.
    assert entry["verified"] is False
    assert entry["ort_candidate_id"] is None


def test_agx_orin_jetpack512_profile_exactly_matches_its_own_declared_environment():
    sys.path.insert(0, str(SCRIPTS))
    import jetson_common as jc
    detected = {
        "l4t_major": 35, "cuda_major": 11, "cuda_minor": 4, "cudnn_major": 8,
        "tensorrt_major": 8, "tensorrt_minor": 5, "python_abi": "cp38", "arch": "aarch64",
    }
    profiles = jc.load_profiles()
    entry = next(p for p in profiles if p["id"] == "agx-orin-jp512-cp38-environment-confirmed")
    assert jc.profile_matches(detected, entry) is True
    # But since verified=false, the real install gate still refuses to use it for GPU wheel selection.
    assert jc.find_matching_verified_profile(detected, profiles) is None
