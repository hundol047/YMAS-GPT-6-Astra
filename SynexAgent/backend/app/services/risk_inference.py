import hashlib
import logging
import os
from pathlib import Path
import numpy as np
import onnxruntime as ort
from ..schemas import RiskFeatures

FEATURES = ['drug_conflict','comorbidity_load','age_risk','allergy_flag','adverse_history','polypharmacy_load','therapy_duration_load']
MODEL_PATH = Path(__file__).resolve().parents[2] / 'models' / 'risk_model_deep_v3.onnx'

class RiskEngine:
    def __init__(self):
        requested = os.getenv('SYNEX_PROVIDER','cpu').lower()
        available = ort.get_available_providers()
        providers = ['CPUExecutionProvider']
        self.fallback_reason = None
        if requested == 'tensorrt':
            providers = [p for p in ['TensorrtExecutionProvider','CUDAExecutionProvider','CPUExecutionProvider'] if p in available]
            if 'TensorrtExecutionProvider' not in providers:
                self.fallback_reason = 'TensorRT provider unavailable; using CPU/CUDA fallback'
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
