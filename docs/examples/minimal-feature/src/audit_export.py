"""Tenant-admin audit-log CSV export.

The sample is the function an API handler would call. It does not open a
socket. Timestamps are written in UTC. A caller who is not that tenant's
admin, or a row from another tenant, gets an error and no CSV body.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

COLUMNS = ("event_id", "occurred_at_utc", "actor_id", "action", "object_type", "object_id")
ROW_LIMIT = 10000


class ExportError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def export_audit_csv(actor: dict, events: list) -> str:
    """Return a CSV document or raise ExportError before any body is produced."""
    if actor.get("role") != "tenant_admin" or not actor.get("tenant_id"):
        raise ExportError("forbidden", "only a tenant admin of a named tenant can export")
    tenant = actor["tenant_id"]
    rows = []
    for event in events:
        if event.get("tenant_id") != tenant:
            raise ExportError("forbidden", "cross-tenant event refused")
        occurred = event.get("occurred_at")
        if not isinstance(occurred, datetime) or occurred.tzinfo is None:
            raise ExportError("invalid", "occurred_at must be timezone-aware")
        rows.append({
            "event_id": event["event_id"],
            "occurred_at_utc": occurred.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "actor_id": event["actor_id"],
            "action": event["action"],
            "object_type": event["object_type"],
            "object_id": event["object_id"],
        })
    if len(rows) > ROW_LIMIT:
        raise ExportError("limit", f"export exceeds {ROW_LIMIT} rows")
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
