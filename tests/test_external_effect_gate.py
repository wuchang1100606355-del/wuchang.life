import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.external_effect_gate import ExternalEffectHold, authorize_external_effect


class ExternalEffectGateTests(unittest.TestCase):
    def authority(self, allowed):
        td = tempfile.TemporaryDirectory()
        path = Path(td.name) / "authority.json"
        path.write_text(json.dumps({
            "state": "ACTIVE_TOTAL_FIELD_AUTHORITY",
            "allowed_effects": allowed,
            "prohibited_effects": [],
        }))
        self.addCleanup(td.cleanup)
        return path

    def test_read_only_does_not_create_effect_authority(self):
        out = authorize_external_effect(
            task_id="T-012", node="MSI", object_ref="network", operation="observe"
        )
        self.assertEqual(out["state"], "ALLOW_READ_ONLY_EXTERNAL_OBSERVATION")
        self.assertFalse(out["effect_authority"])

    def test_mutation_without_permit_fails_closed(self):
        with self.assertRaisesRegex(ExternalEffectHold, "HOLD_EXTERNAL_MUTATION_EFFECT_PERMIT_REQUIRED"):
            authorize_external_effect(
                task_id="T-012", node="MSI", object_ref="nic:61", operation="disable"
            )

    def test_observer_authority_cannot_be_used_for_mutation(self):
        path = self.authority(["AUTHORIZE_ADAPTIVE_NETWORK_RUNTIME_OBSERVER"])
        permit = {
            "task_id": "T-012", "node": "MSI", "object_ref": "nic:61",
            "operation": "disable", "preimage_ref": "pre:1", "rollback_ref": "rb:1",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "authority_ref": str(path),
            "authorized_effect": "AUTHORIZE_NETWORK_MUTATION",
        }
        with self.assertRaisesRegex(ExternalEffectHold, "HOLD_EXTERNAL_EFFECT_NOT_ALLOWED_BY_TOTAL_FIELD"):
            authorize_external_effect(
                task_id="T-012", node="MSI", object_ref="nic:61",
                operation="disable", permit=permit, authority_path=path,
            )

    def test_exact_allowed_effect_can_pass(self):
        path = self.authority(["AUTHORIZE_NETWORK_MUTATION"])
        permit = {
            "task_id": "T-012", "node": "MSI", "object_ref": "nic:61",
            "operation": "disable", "preimage_ref": "pre:1", "rollback_ref": "rb:1",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "authority_ref": str(path),
            "authorized_effect": "AUTHORIZE_NETWORK_MUTATION",
        }
        out = authorize_external_effect(
            task_id="T-012", node="MSI", object_ref="nic:61",
            operation="disable", permit=permit, authority_path=path,
        )
        self.assertEqual(out["state"], "ALLOW_EXACT_EXTERNAL_EFFECT")


if __name__ == "__main__":
    unittest.main()
