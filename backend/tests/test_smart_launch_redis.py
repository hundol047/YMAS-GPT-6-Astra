"""Exercises _RedisLaunchStore against a REAL local redis-server (not a mock) -- proves the
multi-worker gap in smart_launch.py's SQLite fallback is actually closed: two independent
_RedisLaunchStore instances pointed at the same Redis simulate two separate worker processes, and a
launch written by one is readable (and TTL-expiring, and one-time-use) from the other.

Requires a redis-server reachable at SYNEX_TEST_REDIS_URL (default redis://127.0.0.1:6399/1, matching
this repo's dev-container which ships redis-server locally). Skips cleanly if that's not available,
rather than failing the whole suite in an environment without Redis.
"""
import os
import time
import pytest

redis = pytest.importorskip('redis')
from app.services.smart_launch import _RedisLaunchStore, LAUNCH_TTL_SECONDS

REDIS_URL = os.getenv('SYNEX_TEST_REDIS_URL', 'redis://127.0.0.1:6399/1')


def _redis_available():
    try:
        redis.Redis.from_url(REDIS_URL, socket_connect_timeout=1).ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _redis_available(), reason=f'no redis-server reachable at {REDIS_URL}')


def _flush():
    redis.Redis.from_url(REDIS_URL).flushdb()


def test_launch_state_visible_across_separate_store_instances():
    # Two _RedisLaunchStore(...) objects here stand in for two separate uvicorn worker processes
    # that both set SYNEX_REDIS_URL to the same Redis -- this is exactly the case the SQLite
    # fallback cannot handle (each worker would have its own local file).
    _flush()
    worker_a = _RedisLaunchStore(REDIS_URL)
    worker_b = _RedisLaunchStore(REDIS_URL)
    worker_a.put('state-xyz', {'code_verifier': 'v1', 'iss': 'https://fake-fhir.example/r4',
                                'launch': 'launch-1', 'redirect_uri': 'https://synex.example/callback'})
    launch = worker_b.pop('state-xyz')
    assert launch == {'code_verifier': 'v1', 'iss': 'https://fake-fhir.example/r4',
                       'launch': 'launch-1', 'redirect_uri': 'https://synex.example/callback'}


def test_launch_state_is_one_time_use():
    _flush()
    store = _RedisLaunchStore(REDIS_URL)
    store.put('state-once', {'code_verifier': 'v', 'iss': 'i', 'launch': 'l', 'redirect_uri': 'r'})
    assert store.pop('state-once') is not None
    assert store.pop('state-once') is None  # a replayed callback must not resurrect it


def test_launch_state_expires_on_its_own():
    _flush()
    store = _RedisLaunchStore(REDIS_URL)
    store.put('state-ttl', {'code_verifier': 'v', 'iss': 'i', 'launch': 'l', 'redirect_uri': 'r'})
    ttl = redis.Redis.from_url(REDIS_URL).ttl('synex:smart_launch:state-ttl')
    assert 0 < ttl <= LAUNCH_TTL_SECONDS
