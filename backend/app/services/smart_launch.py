"""SMART App Launch (EHR launch) scaffold: GET /smart/launch?iss=...&launch=... is the URL an EMR
opens SynexAgent with, carrying the FHIR server base (iss) and an opaque launch token the EMR
expects back during token exchange so it can hand over patient context.

This builds a spec-shaped authorization redirect with PKCE (code_verifier/code_challenge, state)
and a callback that exchanges the code for a token. It has NOT been exercised against a real EMR's
SMART launcher or a real FHIR authorization server -- there isn't one reachable here. Verified here
only via unit tests that the redirect URL and PKCE parameters are constructed correctly
(backend/tests/test_cds_hooks.py); the actual authorization round-trip is unverified.

State is kept in a local SQLite file (default backend/data/smart_launch.sqlite3, override with
SYNEX_SMART_LAUNCH_PATH), so it survives a process restart on a single-instance demo deployment --
this was previously an in-memory dict that lost every in-flight launch on restart. It still does
NOT survive across multiple worker processes/replicas sharing no filesystem; a real multi-worker
deployment needs a shared store (Redis, a real DB) instead, same as backend/app/services/audit.py's
own SQLite-is-fine-for-one-instance choice.
"""
import base64, hashlib, os, secrets, sqlite3
from datetime import datetime, timezone
from pathlib import Path
import httpx

_DEFAULT_LAUNCH_DB = Path(__file__).resolve().parents[2] / 'data' / 'smart_launch.sqlite3'


class _LaunchStore:
    def __init__(self, path=None):
        self.path = str(path or os.getenv('SYNEX_SMART_LAUNCH_PATH', _DEFAULT_LAUNCH_DB))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS launches (state TEXT PRIMARY KEY, code_verifier TEXT NOT NULL, '
                       'iss TEXT NOT NULL, launch TEXT NOT NULL, redirect_uri TEXT NOT NULL, created_at TEXT NOT NULL)')

    def _connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def put(self, state, data):
        with self._connect() as db:
            db.execute('INSERT OR REPLACE INTO launches VALUES (?,?,?,?,?,?)',
                       (state, data['code_verifier'], data['iss'], data['launch'], data['redirect_uri'],
                        datetime.now(timezone.utc).isoformat()))

    def pop(self, state):
        with self._connect() as db:
            row = db.execute('SELECT code_verifier, iss, launch, redirect_uri FROM launches WHERE state=?', (state,)).fetchone()
            if row:
                db.execute('DELETE FROM launches WHERE state=?', (state,))
        return {'code_verifier': row[0], 'iss': row[1], 'launch': row[2], 'redirect_uri': row[3]} if row else None


_LAUNCHES = _LaunchStore()


def _pkce_pair():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    return verifier, challenge


def discover_authorize_endpoint(iss: str, transport=None) -> str:
    try:
        r = httpx.Client(transport=transport, timeout=10).get(f'{iss.rstrip("/")}/.well-known/smart-configuration')
        r.raise_for_status()
        return r.json()['authorization_endpoint']
    except Exception:
        return f'{iss.rstrip("/")}/oauth2/authorize'  # conservative fallback; real deployments should verify


def build_authorize_redirect(iss: str, launch: str, client_id: str, redirect_uri: str, scope: str, transport=None) -> str:
    state = secrets.token_urlsafe(16)
    verifier, challenge = _pkce_pair()
    _LAUNCHES.put(state, {'code_verifier': verifier, 'iss': iss, 'launch': launch, 'redirect_uri': redirect_uri})
    authorize_endpoint = discover_authorize_endpoint(iss, transport=transport)
    params = {
        'response_type': 'code', 'client_id': client_id, 'redirect_uri': redirect_uri,
        'launch': launch, 'scope': scope, 'state': state, 'aud': iss,
        'code_challenge': challenge, 'code_challenge_method': 'S256',
    }
    return f'{authorize_endpoint}?{httpx.QueryParams(params)}'


def exchange_code(state: str, code: str, client_id: str, transport=None) -> dict:
    launch = _LAUNCHES.pop(state)
    if not launch:
        raise KeyError('Unknown or expired launch state')
    token_endpoint = discover_authorize_endpoint(launch['iss'], transport=transport).replace('/authorize', '/token')
    r = httpx.Client(transport=transport, timeout=10).post(token_endpoint, data={
        'grant_type': 'authorization_code', 'code': code, 'redirect_uri': launch['redirect_uri'],
        'client_id': client_id, 'code_verifier': launch['code_verifier'],
    })
    r.raise_for_status()
    return r.json()
