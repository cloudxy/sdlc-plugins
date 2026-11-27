"""API-level checks for the tenant audit CSV export. Run from the example project root."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import audit_export


def _event(tenant="ten_a", event_id="evt_1", when=None):
    return {
        "tenant_id": tenant,
        "event_id": event_id,
        "occurred_at": when or datetime(2026, 11, 21, 8, 30, tzinfo=timezone(timedelta(hours=8))),
        "actor_id": "usr_1",
        "action": "member.invite",
        "object_type": "member",
        "object_id": "usr_2",
    }


class ExportAuditCsvTest(unittest.TestCase):
    def test_admin_exports_utc_csv(self):
        text = audit_export.export_audit_csv(
            {"role": "tenant_admin", "tenant_id": "ten_a"}, [_event()])
        lines = text.splitlines()
        self.assertEqual(
            lines[0],
            "event_id,occurred_at_utc,actor_id,action,object_type,object_id",
        )
        self.assertEqual(
            lines[1],
            "evt_1,2026-11-21T00:30:00Z,usr_1,member.invite,member,usr_2",
        )

    def test_empty_events_return_header_only(self):
        text = audit_export.export_audit_csv(
            {"role": "tenant_admin", "tenant_id": "ten_a"}, [])
        self.assertEqual(
            text.strip(),
            "event_id,occurred_at_utc,actor_id,action,object_type,object_id",
        )

    def test_member_is_forbidden(self):
        with self.assertRaises(audit_export.ExportError) as caught:
            audit_export.export_audit_csv({"role": "member", "tenant_id": "ten_a"}, [])
        self.assertEqual(caught.exception.code, "forbidden")

    def test_cross_tenant_event_is_refused(self):
        with self.assertRaises(audit_export.ExportError) as caught:
            audit_export.export_audit_csv(
                {"role": "tenant_admin", "tenant_id": "ten_a"},
                [_event(tenant="ten_b", event_id="evt_other")],
            )
        self.assertEqual(caught.exception.code, "forbidden")
        self.assertNotIn("evt_other", str(caught.exception))

    def test_naive_timestamp_is_rejected(self):
        naive = _event(when=datetime(2026, 11, 21, 8, 30))
        with self.assertRaises(audit_export.ExportError) as caught:
            audit_export.export_audit_csv(
                {"role": "tenant_admin", "tenant_id": "ten_a"}, [naive])
        self.assertEqual(caught.exception.code, "invalid")

    def test_row_limit(self):
        admin = {"role": "tenant_admin", "tenant_id": "ten_a"}
        at_limit = [_event(event_id=f"evt_{i}") for i in range(audit_export.ROW_LIMIT)]
        text = audit_export.export_audit_csv(admin, at_limit)
        self.assertEqual(len(text.splitlines()), audit_export.ROW_LIMIT + 1)
        over = at_limit + [_event(event_id="evt_over")]
        with self.assertRaises(audit_export.ExportError) as caught:
            audit_export.export_audit_csv(admin, over)
        self.assertEqual(caught.exception.code, "limit")


if __name__ == "__main__":
    unittest.main()
