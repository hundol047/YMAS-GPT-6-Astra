"""Test-only stdin bridge to the real FastAPI app and ONNX model. No network socket."""
import json,os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from fastapi.testclient import TestClient
from app.main import app
with tempfile.TemporaryDirectory(prefix='synex-dom-') as temp:
    os.environ['SYNEX_AUDIT_PATH']=str(Path(temp)/'audit.sqlite3')
    with TestClient(app) as client:
        for line in sys.stdin:
            req=json.loads(line)
            try:
                headers={'Content-Type':'application/json',**{k:v for k,v in (req.get('headers') or {}).items() if v is not None}}
                r=client.request(req['method'],req['path'],content=req.get('body'),headers=headers)
                out={'id':req['id'],'status':r.status_code,'body':r.text}
            except Exception as error:
                out={'id':req['id'],'status':500,'body':json.dumps({'detail':str(error)})}
            print(json.dumps(out),flush=True)
