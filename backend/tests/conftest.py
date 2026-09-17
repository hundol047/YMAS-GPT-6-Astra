import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app
@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('SYNEX_AUDIT_PATH',str(tmp_path/'audit.sqlite3'))
    # IdempotencyStore is instantiated fresh per app lifespan (see main.py), so this env var IS
    # effective per-test. SYNEX_SMART_LAUNCH_PATH/SYNEX_SESSION_PATH/SYNEX_AUTH_SESSION_PATH are NOT
    # -- smart_launch.py/auth.py build their stores once as module-level singletons at import time,
    # before any test's monkeypatch runs, so tests needing an isolated launch/session store construct
    # one directly (e.g. _LaunchStore(path=tmp_path/...) -- see test_launch_state_survives_a_process_restart).
    monkeypatch.setenv('SYNEX_IDEMPOTENCY_PATH',str(tmp_path/'idempotency.sqlite3'))
    with TestClient(app) as c:yield c
