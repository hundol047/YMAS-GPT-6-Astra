"""Regression guard for a real file-descriptor leak found during RC1 stabilization: every SQLite-
backed store in this codebase (AuditStore, _AuthSessionStore, _SqliteIdempotencyStore, _LaunchStore,
_SessionStore) used to open a connection via `sqlite3.connect(...)` and rely ONLY on the
connection's own `with db:` for commit/rollback -- which never closes the connection. Under a
repeated-request smoke test (POST /agent/analyze in a loop against a live server), the process's
open file descriptor count climbed steadily instead of staying flat.

Each store's connect()/_connect() is now itself a context manager that guarantees `.close()` runs
in a `finally` block. This test proves that property directly, for every store, by wrapping
sqlite3.connect and asserting every Connection it returns is closed by the time the `with` block
using it has exited -- not eventually via garbage collection, immediately.
"""
import sqlite3


def _tracking_connect(monkeypatch, module):
    """Monkeypatch `module.sqlite3.connect` to remember every real Connection object it creates.
    sqlite3.Connection is a C type -- its `close` attribute can't be monkeypatched per-instance --
    so "is this one closed?" is checked afterward by trying a harmless query: a closed connection
    raises sqlite3.ProgrammingError, an open (leaked) one does not."""
    real_connect = sqlite3.connect
    seen = []

    def fake_connect(*a, **kw):
        conn = real_connect(*a, **kw)
        seen.append(conn)
        return conn

    monkeypatch.setattr(module.sqlite3, 'connect', fake_connect)
    return seen


def _all_closed(connections):
    for conn in connections:
        try:
            conn.execute('SELECT 1')
        except sqlite3.ProgrammingError:
            continue  # closed, as expected
        return False  # still usable -- never closed, i.e. leaked
    return True


def test_audit_store_closes_every_connection(tmp_path, monkeypatch):
    import app.services.audit as audit_module
    seen = _tracking_connect(monkeypatch, audit_module)
    store = audit_module.AuditStore(path=tmp_path / 'audit.sqlite3')
    store.record('SYN-001', 'patient_selected', {})
    store.list('SYN-001')
    assert len(seen) >= 2  # __init__'s CREATE TABLE + record() + list() each open their own
    assert _all_closed(seen), 'a connection was left open (not closed) after use'


def test_auth_session_store_closes_every_connection(tmp_path, monkeypatch):
    import app.services.auth as auth_module
    seen = _tracking_connect(monkeypatch, auth_module)
    store = auth_module._AuthSessionStore(path=tmp_path / 'auth_session.sqlite3')
    store.put('session-1', user_id='u1', role='clinician')
    store.get('session-1')
    assert len(seen) >= 2
    assert _all_closed(seen)


def test_idempotency_store_closes_every_connection(tmp_path, monkeypatch):
    import app.services.idempotency as idem_module
    seen = _tracking_connect(monkeypatch, idem_module)
    store = idem_module._SqliteIdempotencyStore(path=tmp_path / 'idempotency.sqlite3')
    result = store.begin('scope-1', 'key-1', 'hash-1')
    assert result.owner
    store.complete('scope-1', 'key-1', response_status=200, response_body={'ok': True})
    assert len(seen) >= 2
    assert _all_closed(seen)


def test_smart_launch_store_closes_every_connection(tmp_path, monkeypatch):
    import app.services.smart_launch as smart_module
    seen = _tracking_connect(monkeypatch, smart_module)
    store = smart_module._LaunchStore(path=tmp_path / 'smart_launch.sqlite3')
    store.put('state-1', {'code_verifier': 'v', 'iss': 'https://fake.example', 'launch': 'l',
                           'redirect_uri': 'https://synex.example/cb', 'token_endpoint': 'https://fake.example/token'})
    store.pop('state-1')
    assert len(seen) >= 2
    assert _all_closed(seen)


def test_smart_session_store_closes_every_connection(tmp_path, monkeypatch):
    import app.services.smart_launch as smart_module
    seen = _tracking_connect(monkeypatch, smart_module)
    store = smart_module._SessionStore(path=tmp_path / 'smart_session.sqlite3')
    store.put('session-1', patient_id='SYN-002', iss='https://fake.example', access_token='tok')
    store.context('session-1')
    assert len(seen) >= 2
    assert _all_closed(seen)
