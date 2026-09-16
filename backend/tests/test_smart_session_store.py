"""_SessionStore (SQLite-backed SMART session storage) TTL enforcement -- see smart_launch.py's
class docstring. Before this round, a session's age was only checked opportunistically inside
put()'s cleanup sweep, so an old session already in the table stayed readable via context()/
token_for() until some UNRELATED put() happened to sweep it. Both read methods now check the row's
own age on every call.

Tested directly against the class (not through the full app) with a real SQLite file in tmp_path,
and time.time() monkeypatched to simulate the passage of time without an actual sleep. Redis
behavior (_RedisSessionStore) is unchanged -- ex=SESSION_TTL_SECONDS already gives it real
self-expiry, see _RedisLaunchStore's own real-redis-server test for the equivalent proof pattern.
"""
from app.services import smart_launch
from app.services.smart_launch import _SessionStore, SESSION_TTL_SECONDS


def test_fresh_session_context_and_token_readable(tmp_path):
    store = _SessionStore(path=tmp_path / 'session.sqlite3')
    session_id = 'sess-1'
    store.put(session_id, patient_id='SYN-002', iss='https://fake-fhir.example/r4', access_token='tok-abc')
    assert store.context(session_id) == {'patient_id': 'SYN-002', 'iss': 'https://fake-fhir.example/r4'}
    assert store.token_for(session_id) == 'tok-abc'


def test_expired_session_context_and_token_return_none_and_row_is_deleted(tmp_path, monkeypatch):
    store = _SessionStore(path=tmp_path / 'session.sqlite3')
    session_id = 'sess-2'
    base_time = 1_000_000.0
    monkeypatch.setattr(smart_launch.time, 'time', lambda: base_time)
    store.put(session_id, patient_id='SYN-002', iss='https://fake-fhir.example/r4', access_token='tok-abc')

    # Still fresh just before the TTL boundary.
    monkeypatch.setattr(smart_launch.time, 'time', lambda: base_time + SESSION_TTL_SECONDS - 1)
    assert store.context(session_id) == {'patient_id': 'SYN-002', 'iss': 'https://fake-fhir.example/r4'}
    assert store.token_for(session_id) == 'tok-abc'

    # Past the TTL: both reads must return None, never the stale patient_id/iss/token.
    monkeypatch.setattr(smart_launch.time, 'time', lambda: base_time + SESSION_TTL_SECONDS + 1)
    assert store.context(session_id) is None
    assert store.token_for(session_id) is None

    # The expired row is actually removed by the read itself, not just filtered at read time --
    # this proves cleanup doesn't depend on some other, unrelated put() happening later.
    with store._connect() as db:
        assert db.execute('SELECT 1 FROM sessions WHERE session_id=?', (session_id,)).fetchone() is None


def test_reading_an_unknown_session_returns_none(tmp_path):
    store = _SessionStore(path=tmp_path / 'session.sqlite3')
    assert store.context('nope-at-all') is None
    assert store.token_for('nope-at-all') is None
