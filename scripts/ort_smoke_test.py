#!/usr/bin/env python3
"""Minimal, ISOLATED ONNX Runtime smoke test -- always run as its own subprocess, never in-process
inside another script, specifically so a native ONNX Runtime crash (confirmed for real on a Jetson
AGX Orin + JetPack 5.1.2 device with the generic PyPI ARM64 CPU onnxruntime==1.19.2 wheel: a C++
`Assertion '__n < this->size()' failed` inside libstdc++'s std::vector::operator[], -> SIGABRT ->
"Aborted (core dumped)") can never take the calling orchestrator down with it, and can be told
apart from an ordinary Python exception by the caller inspecting how this process terminated (see
scripts/jetson_common.py's classify_ort_smoke_test / classify_subprocess_termination).

Prints ONE flushed JSON object per completed stage to stdout, in order:
  {"stage": "import", "ok": true, "version": "...", "providers": [...]}
  {"stage": "model_load", "ok": true, "model_sha256": "...", "session_providers": [...]}   (--full only)
  {"stage": "inference", "ok": true, "risk_probability": 0.42}                             (--full only)

A crash mid-run leaves stdout truncated right after the last stage that actually completed -- the
caller uses that (not this process's own judgment, since a crashed process can't report on itself)
to know whether the crash happened during import, during model/session construction, or during the
inference call itself.

Without --full: only the "import" stage runs (`import onnxruntime` + get_available_providers()) --
no model load, no session, no inference -- so a crash here is unambiguously about the ORT
package/wheel itself, never about this project's model file or session options.

With --full: also builds the real SynexAgent RiskEngine (honoring SYNEX_PROVIDER/SYNEX_TENSORRT_FP16
from the environment, exactly like the real server) and runs exactly one inference.

Usage: python3 scripts/ort_smoke_test.py [--full]
Exit code 0 = every requested stage completed successfully. Non-zero with a normal Python traceback
on stderr = an ordinary exception (import/model/inference failure -- see PYTHON_EXCEPTION in
classify_subprocess_termination). No further output + the process was killed by a signal = a native
crash (NATIVE_CRASH) -- this script cannot detect or report that about itself; the caller must
inspect the subprocess's own termination.
"""
import argparse
import json
import sys
from pathlib import Path


def _emit(stage, ok, **extra):
    print(json.dumps({'stage': stage, 'ok': ok, **extra}), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--full', action='store_true',
                     help='Also load the real SynexAgent ONNX model and run one inference (not just import).')
    args = ap.parse_args()

    import onnxruntime as ort
    _emit('import', True, version=ort.__version__, providers=ort.get_available_providers())

    if not args.full:
        return 0

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
    from app.services.risk_inference import RiskEngine
    from app.schemas import RiskFeatures

    engine = RiskEngine()
    _emit('model_load', True, model_sha256=engine.sha256, session_providers=engine.session.get_providers())

    pred = engine.predict(RiskFeatures(drug_conflict=1, comorbidity_load=.5, age_risk=.5, allergy_flag=0,
                                        adverse_history=0, polypharmacy_load=.2, therapy_duration_load=.2))
    _emit('inference', True, risk_probability=pred['risk_probability'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
