# Security & PHI handling

This document covers what this repository implements today versus what a real hospital
deployment still needs. Nothing here has been audited by a security team or a real institution;
treat it as an engineering starting point, not a compliance attestation.

## What's implemented

- **Auth**: `AUTH_MODE=oidc` verifies bearer JWTs against a real OIDC issuer's JWKS (signature,
  issuer, audience, expiry) -- see `backend/app/services/auth.py`. A browser client uses a second
  path instead of resending the raw token on every request: `POST /auth/session` verifies the
  token once and exchanges it for an HttpOnly `synex_auth_session` cookie backed by a server-side
  session store (`_AuthSessionStore`, TTL-enforced on every read, not just on write) -- the SPA
  never holds the token in localStorage/sessionStorage/a URL/React state. This is a SEPARATE
  session/cookie from SMART's `synex_session` (patient context + FHIR token) -- see
  `docs/EMR_INTEGRATION.md`'s "AUTH_MODE=oidc" section. Default `AUTH_MODE=demo` keeps the existing
  fixed identity for local development/demo, matching prior behavior exactly.
- **RBAC**: role → permission table plus a `NEVER_GRANTED` set (patient edit, automatic
  prescription changes, rule edits) no role can ever pass, checked in code, not just documented.
  `clinician_readonly` is genuinely read-only (cannot write/sign a note or place an order) -- see
  `docs/EMR_INTEGRATION.md`'s "RBAC 역할" section for the current 4-role split.
- **Audit**: append-only SQLite event log; every write now carries `user_id`/`role` when `AUTH_MODE=oidc`
  is set (or the demo identity otherwise). No delete/update path exists for audit rows.
- **Secrets**: `FHIR_CLIENT_SECRET`, OIDC config, etc. are read only from environment variables at
  runtime. None are committed to this repo, and `.env.example`/`.gitignore` keep real `.env` files
  out of git. Nothing in `backend/app/services/*.py` writes a secret to disk, a log line, or a
  Docker image layer.
- **PHI never logged**: `/health/subsystems` (see `backend/app/main.py`) intentionally returns
  only component status, never patient data -- covered by
  `backend/tests/test_observability.py::test_health_subsystems_response_has_no_patient_fields`.
  The Jetson scripts (`scripts/verify_jetson_agx_gpu.py`, `scripts/benchmark_jetson.py`) never
  touch patient records -- they run inference on synthetic feature vectors, not real patient input.
- **Data minimization**: `FHIRAdapter` fetches only the resource types this app actually uses
  (Condition/MedicationRequest/MedicationStatement/AllergyIntolerance/Observation), not a full
  patient record dump.
- **Concurrency-safe idempotency**: Medication Order's `Idempotency-Key` guarantee is enforced by a
  SQL uniqueness constraint (`PRIMARY KEY(scope,key)`, or Redis `SET NX` when `SYNEX_REDIS_URL` is
  set) -- see `backend/app/services/idempotency.py`. Two genuinely concurrent requests carrying the
  same key can never both create an order; only one claims the key, the other waits for and returns
  its result. The frontend's button-disabled state is a secondary defense only, never relied on.
- **SMART launch SSRF defense**: `/smart/launch?iss=...` validates the caller-supplied `iss` (HTTPS-
  only, no embedded credentials, `SYNEX_SMART_TRUSTED_ISSUERS` allowlist, private/loopback/link-
  local IP rejection via `ipaddress`) BEFORE any outbound discovery request -- see
  `smart_launch.validate_smart_issuer()`. SMART launch state (`_LaunchStore`) now enforces its TTL
  on every read (`pop()`), not just opportunistically on the next write, so an expired `state` can
  never be used for a token exchange.
- **CDS Hooks execution auth**: `GET /cds-services` (discovery) stays public in every mode, per the
  CDS Hooks spec. `POST /cds-services/{service}` (execution) is gated by `CDS_AUTH_MODE` --
  `none` (default) or `bearer` (production-recommended, reuses the same JWKS-based
  `verify_oidc_token()` AUTH_MODE=oidc uses, plus a `cds:invoke` permission check) -- independent of
  the app-wide `AUTH_MODE`.

## What a real deployment still needs (not implemented here)

- **TLS**: this app assumes TLS termination happens in front of it (a real deployment's reverse
  proxy/ingress, not application code here). Nothing in this repo configures TLS certificates.
- **Session expiration / token refresh UX**: `SmartOAuthClient`/`verify_oidc_token` handle token
  acquisition and expiry checks, and both server-side session stores (`_AuthSessionStore` for
  OIDC, `_SessionStore` for SMART) now actually expire a session on every read past their TTL
  (not just opportunistically on the next write) -- but there is still no FRONTEND session-expiry
  UX (a re-login prompt when a session lapses mid-use, silent token refresh, etc.).
- **Network segmentation**: the intended shape is EMR/OCS → hospital network → Jetson AGX Orin
  (local inference) with minimal external cloud transmission -- see `docs/JETSON_DEPLOYMENT.md`.
  This repo does not configure any network policy; that's deployment-environment-specific.
  Note `.venv/`, `data/audit.sqlite3*` etc. are already excluded from source control (`.gitignore`).
- **Data retention policy**: the audit DB grows without a retention/pruning policy today.
  `AuditStore.list()` caps a single query at 200 rows, but nothing deletes old rows.
- **Real encryption at rest**: `backend/data/audit.sqlite3` is a plain (unencrypted) SQLite file.
  A real deployment on hospital infrastructure should put it on encrypted storage.
- **Independent security review**: none of the above has been reviewed by a security team; treat
  every item in "What's implemented" as "exists in code and is unit-tested," not "certified safe."

## PHI-in-logs checklist (for anyone extending this app)

Before adding a new `print`/`log.info`/diagnostic script, check it against:
- [ ] Does it include a patient name, ID, diagnosis, medication, or lab value? → don't log it.
- [ ] Does a benchmark/diagnostic script (`scripts/*.py`) touch real patient records? → it shouldn't;
      use synthetic feature vectors like `scripts/benchmark_jetson.py` does.
- [ ] Does a new `/health`-style endpoint return anything beyond component status? → it shouldn't.
