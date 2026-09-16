# Security & PHI handling

This document covers what this repository implements today versus what a real hospital
deployment still needs. Nothing here has been audited by a security team or a real institution;
treat it as an engineering starting point, not a compliance attestation.

## What's implemented

- **Auth**: `AUTH_MODE=oidc` verifies bearer JWTs against a real OIDC issuer's JWKS (signature,
  issuer, audience, expiry) -- see `backend/app/services/auth.py`. Default `AUTH_MODE=demo` keeps
  the existing fixed "DR" identity for local development/demo, matching prior behavior exactly.
- **RBAC**: role → permission table plus a `NEVER_GRANTED` set (patient edit, automatic
  prescription changes, rule edits) no role can ever pass, checked in code, not just documented.
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

## What a real deployment still needs (not implemented here)

- **TLS**: this app assumes TLS termination happens in front of it (a real deployment's reverse
  proxy/ingress, not application code here). Nothing in this repo configures TLS certificates.
- **Session expiration / token refresh UX**: `SmartOAuthClient`/`verify_oidc_token` handle token
  acquisition and expiry checks, but there is no frontend session-expiry UX (re-login prompt, etc.).
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
