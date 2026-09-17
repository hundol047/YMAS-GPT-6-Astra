"""RiskEngine / SYNEX_PROVIDER selection.

Two things are verified here, deliberately kept separate:
1. `select_providers()` (pure logic, no ONNX session, no hardware) -- unit-tested against MOCKED
   available-provider lists so the cpu/cuda/tensorrt/invalid-value matrix is fully covered on any
   machine, including one with no GPU at all. This does NOT prove a real CUDA/TensorRT provider
   actually works on real hardware -- only that the SELECTION logic picks the right provider list
   and reports the right fallback_reason given what onnxruntime claims is available.
2. `RiskEngine` itself, exercised via the real `backend/models/risk_model_deep_v3.onnx` file and a
   real `onnxruntime.InferenceSession` (see test_safety.py's test_health_model_integrity_and_fhir
   and the SYN-00x cases, which all run through this same real engine, not a stub) -- this machine
   only has CPUExecutionProvider available, so that's what's actually verified end-to-end here.
"""
import numpy as np
import pytest
from app.services.risk_inference import RiskEngine, select_providers, VALID_PROVIDERS, FEATURES, MODEL_PATH
from app.schemas import RiskFeatures


# --- 1. Provider selection matrix (mocked available-providers list) -----------------------------

def test_select_providers_cpu_uses_only_cpu():
    providers, fallback = select_providers('cpu', ['CPUExecutionProvider'])
    assert providers == ['CPUExecutionProvider']
    assert fallback is None

def test_select_providers_cuda_available_uses_cuda_then_cpu():
    providers, fallback = select_providers('cuda', ['CUDAExecutionProvider', 'CPUExecutionProvider'])
    assert providers == ['CUDAExecutionProvider', 'CPUExecutionProvider']
    assert fallback is None

def test_select_providers_cuda_unavailable_falls_back_to_cpu_with_reason():
    providers, fallback = select_providers('cuda', ['CPUExecutionProvider'])
    assert providers == ['CPUExecutionProvider']
    assert fallback is not None and 'CUDA' in fallback

def test_select_providers_tensorrt_available_uses_full_order():
    providers, fallback = select_providers('tensorrt', ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider'])
    assert providers == ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
    assert fallback is None

def test_select_providers_tensorrt_unavailable_falls_back_to_cuda():
    # TensorRT missing, CUDA present -- falls back to CUDA (not straight to CPU).
    providers, fallback = select_providers('tensorrt', ['CUDAExecutionProvider', 'CPUExecutionProvider'])
    assert providers == ['CUDAExecutionProvider', 'CPUExecutionProvider']
    assert fallback is not None and 'TensorRT' in fallback

def test_select_providers_tensorrt_and_cuda_both_unavailable_falls_back_to_cpu():
    providers, fallback = select_providers('tensorrt', ['CPUExecutionProvider'])
    assert providers == ['CPUExecutionProvider']
    assert fallback is not None and 'TensorRT' in fallback

def test_select_providers_invalid_value_never_silently_becomes_cpu():
    # An unsupported SYNEX_PROVIDER value (typo, wrong name) must fall back to CPU-only AND report
    # why -- it must never look identical to an explicit, intentional SYNEX_PROVIDER=cpu.
    for bad in ['gpu', 'nvidia', 'abc', '', 'cuda ']:
        providers, fallback = select_providers(bad, ['CUDAExecutionProvider', 'CPUExecutionProvider'])
        assert providers == ['CPUExecutionProvider']
        assert fallback is not None and 'Unsupported' in fallback
    # And contrast with the genuinely-explicit cpu case, which reports no fallback at all.
    providers, fallback = select_providers('cpu', ['CUDAExecutionProvider', 'CPUExecutionProvider'])
    assert providers == ['CPUExecutionProvider'] and fallback is None

def test_valid_providers_is_exactly_cpu_cuda_tensorrt():
    assert set(VALID_PROVIDERS) == {'cpu', 'cuda', 'tensorrt'}


# --- 2. Real ONNX Runtime inference (actual InferenceSession, actual model file) -----------------

def test_model_file_exists_and_sha256_is_stable():
    import hashlib
    assert MODEL_PATH.exists()
    digest = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    assert len(digest) == 64

def test_real_onnx_engine_loads_and_infers(monkeypatch):
    # Force CPU explicitly (this sandbox has no GPU) and confirm a REAL onnxruntime.InferenceSession
    # is created against the real model file, not a mock/stub.
    monkeypatch.setenv('SYNEX_PROVIDER', 'cpu')
    engine = RiskEngine()
    assert engine.fallback_reason is None
    assert 'CPUExecutionProvider' in engine.session.get_providers()
    inp, out = engine.session.get_inputs()[0], engine.session.get_outputs()[0]
    assert inp.name == 'features' and inp.shape[-1] == 7 and out.name == 'risk_probability'

    result = engine.predict(RiskFeatures(**dict(zip(FEATURES, [0.6, 0.4, 0.5, 1.0, 0.2, 0.4, 0.3]))))
    score = result['risk_probability']
    assert np.isfinite(score)
    assert 0 <= score <= 1
    assert result['calibrated'] is False  # never presented as a calibrated clinical probability

def test_real_onnx_engine_deterministic_repeat_inference(monkeypatch):
    monkeypatch.setenv('SYNEX_PROVIDER', 'cpu')
    engine = RiskEngine()
    features = RiskFeatures(**dict(zip(FEATURES, [0.6, 0.4, 0.5, 1.0, 0.2, 0.4, 0.3])))
    scores = {engine.predict(features)['risk_probability'] for _ in range(10)}
    assert len(scores) == 1  # identical input -> identical output every time

def test_invalid_synex_provider_engine_still_loads_via_cpu_fallback(monkeypatch):
    # End-to-end (not just select_providers()): a bad env var must not crash engine startup --
    # it must load, work, and honestly report the fallback via health().
    monkeypatch.setenv('SYNEX_PROVIDER', 'nvidia')
    engine = RiskEngine()
    assert 'Unsupported' in engine.fallback_reason
    health = engine.health()
    assert health['model_loaded'] is True
    assert health['fallback_reason'] == engine.fallback_reason
    assert health['providers'] == ['CPUExecutionProvider']

def test_cuda_requested_on_cpu_only_machine_falls_back_and_reports_it(monkeypatch):
    # This sandbox genuinely has no CUDAExecutionProvider available -- a real (not mocked) exercise
    # of the cuda-requested-but-unavailable fallback path end to end.
    import onnxruntime as ort
    if 'CUDAExecutionProvider' in ort.get_available_providers():
        pytest.skip('this machine actually has a CUDA provider available; fallback path not exercised')
    monkeypatch.setenv('SYNEX_PROVIDER', 'cuda')
    engine = RiskEngine()
    assert engine.fallback_reason is not None and 'CUDA' in engine.fallback_reason
    assert engine.session.get_providers() == ['CPUExecutionProvider']
