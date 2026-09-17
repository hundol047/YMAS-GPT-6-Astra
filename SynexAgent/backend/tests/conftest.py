import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app
@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('SYNEX_AUDIT_PATH',str(tmp_path/'audit.sqlite3'))
    with TestClient(app) as c:yield c
