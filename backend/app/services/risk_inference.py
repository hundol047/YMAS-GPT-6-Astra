import hashlib
import logging
import os
from pathlib import Path
import numpy as np
import onnxruntime as ort
from ..schemas import RiskFeatures

FEATURES = ['drug_conflict','comorbidity_load','age_risk','allergy_flag','adverse_history','polypharmacy_load','therapy_duration_load']
MODEL_PATH = Path(__file__).resolve().parents[2] / 'models' / 'risk_model_deep_v3.onnx'
# The only three values SYNEX_PROVIDER understands. An unrecognized value (a typo like 'gpu' or
# 'nvidia', or anything else) is NOT silently treated as 'cpu' with no trace -- that would hide a
# real deployment misconfiguration (someone requested acceleration and got neither the accelerator
# nor a warning). It falls back to CPU, same as an unavailable accelerator, but logs a warning and
# sets fallback_reason so /health surfaces it -- consistent with how every other
# requested-but-unavailable-provider case in this class is already reported, rather than raising
# and refusing to start the whole app over an env var typo.
VALID_PROVIDERS = ('cpu', 'cuda', 'tensorrt')


def select_providers(requested: str, available: list) -> tuple:
    """Pure provider-selection logic, pulled out of RiskEngine.__init__ so it's unit-testable
    against a MOCKED available-providers list without needing real CUDA/TensorRT hardware or an
    actual ONNX session -- see test_risk_inference.py. Returns (providers_list, fallback_reason).

    requested is expected already-lowercased; an unrecognized value falls back to 'cpu' with a
    fallback_reason set (never silently treated as a plain, unremarked 'cpu' -- see VALID_PROVIDERS'
    comment above for why: a typo like SYNEX_PROVIDER=gpu should be visible in /health, not just
    quietly behave like SYNEX_PROVIDER=cpu)."""
    fallback_reason = None
    if requested not in VALID_PROVIDERS:
        logging.warning('Unsupported SYNEX_PROVIDER=%r (valid: %s); falling back to cpu', requested, ', '.join(VALID_PROVIDERS))
        fallback_reason = f"Unsupported SYNEX_PROVIDER={requested!r} (valid: {', '.join(VALID_PROVIDERS)}); using CPU"
        requested = 'cpu'
    if requested == 'cpu':
        return ['CPUExecutionProvider'], fallback_reason
    if requested == 'cuda':
        providers = [p for p in ['CUDAExecutionProvider','CPUExecutionProvider'] if p in available]
        if 'CUDAExecutionProvider' not in providers:
            fallback_reason = 'CUDA provider unavailable; using CPU fallback'
        return providers, fallback_reason
    # requested == 'tensorrt'
    providers = [p for p in ['TensorrtExecutionProvider','CUDAExecutionProvider','CPUExecutionProvider'] if p in available]
    if 'TensorrtExecutionProvider' not in providers:
        fallback_reason = 'TensorRT provider unavailable; using CPU/CUDA fallback'
    return providers, fallback_reason


class RiskEngine:
    def __init__(self):
        requested = os.getenv('SYNEX_PROVIDER','cpu').lower()
        available = ort.get_available_providers()
        providers, self.fallback_reason = select_providers(requested, available)
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        try:
            self.session = ort.InferenceSession(str(MODEL_PATH), sess_options=opts, providers=providers)
        except Exception:
            if providers == ['CPUExecutionProvider']:
                raise
            logging.exception('Accelerator initialization failed; falling back to CPU')
            self.fallback_reason = 'Accelerator initialization failed; CPU fallback'
            self.session = ort.InferenceSession(str(MODEL_PATH), sess_options=opts, providers=['CPUExecutionProvider'])
        inp, out = self.session.get_inputs()[0], self.session.get_outputs()[0]
        if inp.name != 'features' or inp.shape[-1] != 7 or inp.type != 'tensor(float)' or out.name != 'risk_probability':
            raise RuntimeError('Unexpected model input/output contract')
        self.sha256 = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
        self.predict(RiskFeatures(**dict(zip(FEATURES,[0,0,0.3,0,0,0.1,0]))))

    def predict(self, features: RiskFeatures):
        values = features.model_dump()
        x = np.asarray([[values[k] for k in FEATURES]], dtype=np.float32)
        score = float(self.session.run(['risk_probability'], {'features':x})[0].reshape(-1)[0])
        if not np.isfinite(score) or not 0 <= score <= 1:
            raise RuntimeError('Invalid model output')
        return {'risk_probability':score,'risk_level':'high' if score > 0.5 else 'low',
                'features':values, 'model':'risk_model_deep_v3.onnx', 'model_sha256':self.sha256,
                'calibrated':False, 'interpretation':'Prototype AI risk score; not a clinical event probability'}

    def health(self):
        return {'model_loaded':True,'model_sha256':self.sha256,'providers':self.session.get_providers(),
                'fallback_reason':self.fallback_reason,'input':{'name':'features','shape':['batch',7]},
                'output':{'name':'risk_probability','shape':['batch']}}
