"""SMART App Launch (EHR launch) scaffold: GET /smart/launch?iss=...&launch=... is the URL an EMR
opens SynexAgent with, carrying the FHIR server base (iss) and an opaque launch token the EMR
expects back during token exchange so it can hand over patient context.

This builds a spec-shaped authorization redirect with PKCE (code_verifier/code_challenge, state)
and a callback that exchanges the code for a token. It has NOT been exercised against a real EMR's
SMART launcher or a real FHIR authorization server -- there isn't one reachable here. Verified here
only via unit tests that the redirect URL and PKCE parameters are constructed correctly
(backend/tests/test_cds_hooks.py); the actual authorization round-trip is unverified.

State is kept in an in-memory dict, fine for a demo/single-process deployment; a real deployment
needs a shared store (Redis, DB) so launch state survives across workers/restarts.
"""
import base64, hashlib, os, secrets
import httpx

_LAUNCHES: dict[str, dict] = {}  # state -> {code_verifier, iss, launch, redirect_uri}


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
    _LAUNCHES[state] = {'code_verifier': verifier, 'iss': iss, 'launch': launch, 'redirect_uri': redirect_uri}
    authorize_endpoint = discover_authorize_endpoint(iss, transport=transport)
    params = {
        'response_type': 'code', 'client_id': client_id, 'redirect_uri': redirect_uri,
        'launch': launch, 'scope': scope, 'state': state, 'aud': iss,
        'code_challenge': challenge, 'code_challenge_method': 'S256',
    }
    return f'{authorize_endpoint}?{httpx.QueryParams(params)}'


def exchange_code(state: str, code: str, client_id: str, transport=None) -> dict:
    launch = _LAUNCHES.get(state)
    if not launch:
        raise KeyError('Unknown or expired launch state')
    token_endpoint = discover_authorize_endpoint(launch['iss'], transport=transport).replace('/authorize', '/token')
    r = httpx.Client(transport=transport, timeout=10).post(token_endpoint, data={
        'grant_type': 'authorization_code', 'code': code, 'redirect_uri': launch['redirect_uri'],
        'client_id': client_id, 'code_verifier': launch['code_verifier'],
    })
    r.raise_for_status()
    return r.json()
