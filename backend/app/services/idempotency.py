"""HTTP-level idempotency (Idempotency-Key header), separate from the repository-level idempotency
already in repositories.py (which only protects a SINGLE known resource id, e.g. confirm(order_id)
called twice -- it can't help when a network retry causes the SAME logical create request to hit
the server twice with no id yet, each producing a brand-new order id).

Same narrow-interface style as AuditStore/_LaunchStore: an in-memory dict here, trivially
replaceable with Redis/Postgres later since callers only ever use get()/put() with a plain tuple
key. Not persisted across a process restart -- same prototype-scope caveat as the rest of this
repository layer (see repositories.py's own module docstring).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class IdempotencyRecord:
    request_hash: str
    response_body: object
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IdempotencyStore:
    def __init__(self):
        self._records: dict[tuple, IdempotencyRecord] = {}

    def get(self, scope_key: tuple) -> IdempotencyRecord | None:
        return self._records.get(scope_key)

    def put(self, scope_key: tuple, *, request_hash: str, response_body) -> IdempotencyRecord:
        record = IdempotencyRecord(request_hash=request_hash, response_body=response_body)
        self._records[scope_key] = record
        return record
