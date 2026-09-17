"""Medication Order idempotency (Idempotency-Key header): concurrency-safe by construction, not
just by convention. The old version of this module was a bare `dict[key] -> record` -- fine for a
single sequential retry, but wide open to the classic double-submit race:

    Request A -- get(key) -> nothing
    Request B -- get(key) -> nothing      (both read before either writes)
    A -- creates RX-001
    B -- creates RX-002                   (duplicate order, same Idempotency-Key)

That must never happen, even when A and B are two genuinely concurrent requests (the frontend's
button-disabled state is only a secondary defense -- see main.py's create_medication_order -- the
guarantee has to live here). The fix is a SQL `PRIMARY KEY(scope, key)` uniqueness constraint as
the actual atomicity primitive: only the very first INSERT for a given (scope, key) can succeed,
so concurrent racers naturally serialize on it. The interface built around that is claim-then-work:

    result = store.begin(scope, key, request_hash)
    if result.owner:
        ... do the real work ...
        store.complete(scope, key, response_status=200, response_body=...)   # or store.fail(...)
    else:
        return result.response_body   # a concurrent/earlier request already handled this key

SQLite-backed by default (matching every other stateful service in this codebase --
smart_launch._LaunchStore/_SessionStore, auth._AuthSessionStore); set SYNEX_REDIS_URL to switch to
a real multi-worker/multi-process-safe backend using Redis's atomic `SET NX`. Both backends
implement the identical begin()/complete()/fail() interface.
"""
import json, os, sqlite3, time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parents[2] / 'data' / 'idempotency.sqlite3'
# How long a COMPLETED record is kept around to answer a delayed retry with the original response.
RECORD_TTL_SECONDS = 24 * 3600
# A PENDING claim older than this is presumed abandoned -- the worker that owned it crashed (or was
# killed) mid-request without ever reaching complete()/fail() -- and may be reclaimed by the next
# caller rather than left stuck forever. This is a crash-recovery path, not the normal one: a
# healthy request releases its claim (via complete() or fail()) in well under this window.
STALE_CLAIM_SECONDS = 30
# How long a concurrent LOSER waits for the winner to finish before giving up.
WAIT_TIMEOUT_SECONDS = 10
POLL_INTERVAL_SECONDS = 0.05


class IdempotencyConflict(Exception):
    """Same Idempotency-Key reused with a different request payload -- callers turn this into an
    HTTP 409 rather than silently reusing (or overwriting) the original response."""


class IdempotencyTimeout(Exception):
    """The request that owns this key hasn't completed within WAIT_TIMEOUT_SECONDS."""


@dataclass
class ClaimResult:
    owner: bool
    response_status: "int | None" = None
    response_body: object = None


class _SqliteIdempotencyStore:
    def __init__(self, path=None):
        self.path = str(path or os.getenv('SYNEX_IDEMPOTENCY_PATH', _DEFAULT_DB))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS idempotency_records ('
                       'scope TEXT NOT NULL, key TEXT NOT NULL, request_hash TEXT NOT NULL, '
                       'status TEXT NOT NULL, response_status INTEGER, response_body TEXT, '
                       'created_at_ts REAL NOT NULL, PRIMARY KEY (scope, key))')

    @contextmanager
    def _connect(self):
        # See audit.AuditStore.connect()'s comment: guarantees the connection closes after every
        # call, not just eventually via garbage collection -- important here in particular since
        # _wait_for_result() can loop many times (up to WAIT_TIMEOUT_SECONDS) polling this method.
        db = sqlite3.connect(self.path, timeout=15)
        try:
            with db:
                yield db
        finally:
            db.close()

    def _try_insert(self, scope, key, request_hash) -> bool:
        try:
            with self._connect() as db:
                db.execute('INSERT INTO idempotency_records '
                           '(scope,key,request_hash,status,response_status,response_body,created_at_ts) '
                           'VALUES (?,?,?,?,?,?,?)', (scope, key, request_hash, 'pending', None, None, time.time()))
            return True
        except sqlite3.IntegrityError:
            return False

    def _read(self, scope, key):
        with self._connect() as db:
            return db.execute('SELECT request_hash, status, response_status, response_body, created_at_ts '
                               'FROM idempotency_records WHERE scope=? AND key=?', (scope, key)).fetchone()

    def _delete_if_pending(self, scope, key):
        with self._connect() as db:
            db.execute("DELETE FROM idempotency_records WHERE scope=? AND key=? AND status='pending'", (scope, key))

    def begin(self, scope: str, key: str, request_hash: str) -> ClaimResult:
        with self._connect() as db:
            db.execute('DELETE FROM idempotency_records WHERE status=? AND created_at_ts < ?',
                       ('completed', time.time() - RECORD_TTL_SECONDS))
        if self._try_insert(scope, key, request_hash):
            return ClaimResult(owner=True)
        return self._wait_for_result(scope, key, request_hash)

    def _wait_for_result(self, scope, key, request_hash) -> ClaimResult:
        deadline = time.time() + WAIT_TIMEOUT_SECONDS
        while True:
            row = self._read(scope, key)
            if row is None:
                if self._try_insert(scope, key, request_hash):
                    return ClaimResult(owner=True)
                continue  # someone else claimed it between our read and insert attempt -- re-read
            existing_hash, status, response_status, response_body, created_at_ts = row
            if existing_hash != request_hash:
                raise IdempotencyConflict()
            if status == 'completed':
                return ClaimResult(owner=False, response_status=response_status,
                                    response_body=json.loads(response_body) if response_body is not None else None)
            if time.time() - created_at_ts > STALE_CLAIM_SECONDS:
                self._delete_if_pending(scope, key)
                continue  # abandoned claim (owner crashed mid-request) -- try to reclaim it
            if time.time() >= deadline:
                raise IdempotencyTimeout(f'Idempotency-Key {key!r} is still being processed by another request')
            time.sleep(POLL_INTERVAL_SECONDS)

    def complete(self, scope, key, *, response_status, response_body) -> None:
        with self._connect() as db:
            db.execute('UPDATE idempotency_records SET status=?, response_status=?, response_body=? WHERE scope=? AND key=?',
                       ('completed', response_status, json.dumps(response_body), scope, key))

    def fail(self, scope, key) -> None:
        self._delete_if_pending(scope, key)


class _RedisIdempotencyStore:
    """Real multi-worker-safe idempotency: every worker/replica pointed at the same Redis sees the
    same in-flight claims, so two Uvicorn/Gunicorn worker processes racing on the same
    Idempotency-Key still serialize correctly (a Python-process-local dict never could). Atomicity
    comes from Redis's `SET key value NX` (set-if-not-exists), the same primitive the SQLite backend
    gets from its PRIMARY KEY constraint."""
    def __init__(self, url):
        import redis
        self._r = redis.Redis.from_url(url, decode_responses=True)

    def _key(self, scope, key):
        return f'synex:idempotency:{scope}:{key}'

    def _try_insert(self, redis_key, request_hash) -> bool:
        payload = json.dumps({'request_hash': request_hash, 'status': 'pending', 'response_status': None, 'response_body': None})
        return bool(self._r.set(redis_key, payload, nx=True, ex=STALE_CLAIM_SECONDS))

    def begin(self, scope: str, key: str, request_hash: str) -> ClaimResult:
        redis_key = self._key(scope, key)
        if self._try_insert(redis_key, request_hash):
            return ClaimResult(owner=True)
        return self._wait_for_result(redis_key, request_hash)

    def _wait_for_result(self, redis_key, request_hash) -> ClaimResult:
        deadline = time.time() + WAIT_TIMEOUT_SECONDS
        while True:
            raw = self._r.get(redis_key)
            if raw is None:
                if self._try_insert(redis_key, request_hash):
                    return ClaimResult(owner=True)
                continue
            d = json.loads(raw)
            if d['request_hash'] != request_hash:
                raise IdempotencyConflict()
            if d['status'] == 'completed':
                return ClaimResult(owner=False, response_status=d['response_status'], response_body=d['response_body'])
            if time.time() >= deadline:
                raise IdempotencyTimeout(f'Idempotency-Key {redis_key!r} is still being processed by another request')
            time.sleep(POLL_INTERVAL_SECONDS)

    def complete(self, scope, key, *, response_status, response_body) -> None:
        redis_key = self._key(scope, key)
        raw = self._r.get(redis_key)
        request_hash = json.loads(raw)['request_hash'] if raw else ''
        payload = json.dumps({'request_hash': request_hash, 'status': 'completed',
                               'response_status': response_status, 'response_body': response_body})
        self._r.set(redis_key, payload, ex=RECORD_TTL_SECONDS)

    def fail(self, scope, key) -> None:
        self._r.delete(self._key(scope, key))


def IdempotencyStore(path=None):
    """Factory (kept as the historical class-shaped name main.py imports/calls) rather than a
    module-level singleton like smart_launch._LAUNCHES: main.py instantiates a fresh one per app
    lifespan, and tests (Phase 12.B) construct a brand-new instance to confirm lookups don't depend
    on a process-local dict -- both need `path=None` to mean 'the default/env-configured store',
    not 'a private in-memory one'."""
    redis_url = os.getenv('SYNEX_REDIS_URL')
    return _RedisIdempotencyStore(redis_url) if redis_url else _SqliteIdempotencyStore(path)
