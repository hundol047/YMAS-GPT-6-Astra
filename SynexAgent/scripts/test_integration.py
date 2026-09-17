"""Run React DOM integration tests against FastAPI/ONNX via a local stdio bridge."""
import os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
npm='npm.cmd' if os.name=='nt' else 'npm'
code=subprocess.call([npm,'test'],cwd=root/'frontend',env={**os.environ,'SYNEX_TEST_PYTHON':sys.executable})
sys.exit(code)
