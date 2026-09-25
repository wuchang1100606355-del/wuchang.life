from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.total_field import w7tp_reconstruct_isolated_reviewer as reconstruct_reviewer
from tools.total_field import w7tp_successor_rebind_reviewer_v1 as successor_reviewer
from tools.total_field import w7tp_successor_rebind_seal_v1 as successor_seal
from tools.total_field import w7tp_total_field_authority_binding_v1 as authority_binding


class TotalFieldAuthorityBindingV1Tests(unittest.TestCase):
    @staticmethod
    def valid_binding() -> dict:
        return {
            "node_id": "taiji01",
            "state": "ACTIVE_TOTAL_FIELD_AUTHORITY",
            "contract_state": "ACTIVE_FORMAL",
            "formal_decision_authority": True,
            "formal_seal_authority": True,
            "allowed_effects": [
                "AUTHORIZE_FORMAL_SUCCESSOR_REBIND_REVIEW",
                "AUTHORIZE_RECONSTRUCT_ISOLATED_REVIEW_ONLY",
            ],
        }

    def test_schema_is_valid_draft_2020_12(self):
        schema = json.loads(authority_binding.SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self.assertFalse(list(Draft202012Validator(schema).iter_errors(self.valid_binding())))

    def test_positive_binding_passes_shared_validator(self):
        result = authority_binding.validate_authority_binding(
            self.valid_binding(),
            required_effect=reconstruct_reviewer.AUTHORIZED_EFFECT,
        )
        self.assertEqual("taiji01", result["node_id"])

    def test_required_consumer_fields_fail_closed(self):
        cases = {
            "wrong_node": ("node_id", "MSI"),
            "wrong_state": ("state", "REQUEST_ONLY"),
            "wrong_contract_state": ("contract_state", "CANDIDATE_ONLY"),
            "decision_false": ("formal_decision_authority", False),
            "seal_false": ("formal_seal_authority", False),
            "effects_wrong_type": (
                "allowed_effects",
                "AUTHORIZE_RECONSTRUCT_ISOLATED_REVIEW_ONLY",
            ),
        }
        for name, (field, value) in cases.items():
            with self.subTest(name=name):
                candidate = self.valid_binding()
                candidate[field] = value
                with self.assertRaises(authority_binding.AuthorityBindingValidationError) as raised:
                    authority_binding.validate_authority_binding(candidate)
                self.assertEqual("REJECT_AUTHORITY_BINDING_SCHEMA", raised.exception.reason_code)
                self.assertEqual(f"$.{field}", raised.exception.path)

    def test_duplicate_effects_fail_closed(self):
        candidate = self.valid_binding()
        candidate["allowed_effects"] = [
            "AUTHORIZE_RECONSTRUCT_ISOLATED_REVIEW_ONLY",
            "AUTHORIZE_RECONSTRUCT_ISOLATED_REVIEW_ONLY",
        ]
        with self.assertRaises(authority_binding.AuthorityBindingValidationError) as raised:
            authority_binding.validate_authority_binding(candidate)
        self.assertEqual("REJECT_AUTHORITY_BINDING_SCHEMA", raised.exception.reason_code)
        self.assertEqual("$.allowed_effects", raised.exception.path)

    def test_allowed_effect_with_empty_prohibited_effects_passes(self):
        candidate = self.valid_binding()
        candidate["prohibited_effects"] = []
        result = authority_binding.validate_authority_binding(
            candidate,
            required_effect=reconstruct_reviewer.AUTHORIZED_EFFECT,
        )
        self.assertEqual(candidate, result)

    def test_unrelated_prohibited_effect_does_not_block_allowed_effect(self):
        candidate = self.valid_binding()
        candidate["prohibited_effects"] = ["AUTHORIZE_UNRELATED_EFFECT"]
        result = authority_binding.validate_authority_binding(
            candidate,
            required_effect=reconstruct_reviewer.AUTHORIZED_EFFECT,
        )
        self.assertEqual(candidate, result)

    def test_prohibited_effect_overrides_allowed_effect(self):
        candidate = self.valid_binding()
        candidate["prohibited_effects"] = [reconstruct_reviewer.AUTHORIZED_EFFECT]
        with self.assertRaises(authority_binding.AuthorityBindingValidationError) as raised:
            authority_binding.validate_authority_binding(
                candidate,
                required_effect=reconstruct_reviewer.AUTHORIZED_EFFECT,
            )
        self.assertEqual("HOLD_AUTHORITY_EFFECT_PROHIBITED", raised.exception.reason_code)
        self.assertEqual("$.prohibited_effects", raised.exception.path)

    def test_prohibited_only_effect_holds(self):
        candidate = self.valid_binding()
        candidate["allowed_effects"] = ["AUTHORIZE_FORMAL_SUCCESSOR_REBIND_REVIEW"]
        candidate["prohibited_effects"] = [reconstruct_reviewer.AUTHORIZED_EFFECT]
        with self.assertRaises(authority_binding.AuthorityBindingValidationError) as raised:
            authority_binding.validate_authority_binding(
                candidate,
                required_effect=reconstruct_reviewer.AUTHORIZED_EFFECT,
            )
        self.assertEqual("HOLD_AUTHORITY_EFFECT_PROHIBITED", raised.exception.reason_code)
        self.assertEqual("$.prohibited_effects", raised.exception.path)

    def test_missing_required_effect_holds(self):
        candidate = self.valid_binding()
        candidate["allowed_effects"] = ["AUTHORIZE_FORMAL_SUCCESSOR_REBIND_REVIEW"]
        candidate["prohibited_effects"] = []
        with self.assertRaises(authority_binding.AuthorityBindingValidationError) as raised:
            authority_binding.validate_authority_binding(
                candidate,
                required_effect=reconstruct_reviewer.AUTHORIZED_EFFECT,
            )
        self.assertEqual("HOLD_AUTHORITY_EFFECT_NOT_ALLOWED", raised.exception.reason_code)
        self.assertEqual("$.allowed_effects", raised.exception.path)

    def test_unresolved_prohibited_effects_holds_when_effect_required(self):
        candidate = self.valid_binding()
        candidate["prohibited_effects"] = {"SEMANTICS_STATUS": "UNRESOLVED"}
        with self.assertRaises(authority_binding.AuthorityBindingValidationError) as raised:
            authority_binding.validate_authority_binding(
                candidate,
                required_effect=reconstruct_reviewer.AUTHORIZED_EFFECT,
            )
        self.assertEqual(
            "HOLD_AUTHORITY_PROHIBITED_EFFECTS_UNRESOLVED",
            raised.exception.reason_code,
        )
        self.assertEqual("$.prohibited_effects", raised.exception.path)

    def test_prohibited_effects_wrong_type_fails_closed(self):
        candidate = self.valid_binding()
        candidate["prohibited_effects"] = reconstruct_reviewer.AUTHORIZED_EFFECT
        with self.assertRaises(authority_binding.AuthorityBindingValidationError) as raised:
            authority_binding.validate_authority_binding(candidate)
        self.assertEqual("REJECT_AUTHORITY_BINDING_SCHEMA", raised.exception.reason_code)
        self.assertEqual("$.prohibited_effects", raised.exception.path)

    def test_duplicate_prohibited_effects_fail_closed(self):
        candidate = self.valid_binding()
        candidate["prohibited_effects"] = [
            reconstruct_reviewer.AUTHORIZED_EFFECT,
            reconstruct_reviewer.AUTHORIZED_EFFECT,
        ]
        with self.assertRaises(authority_binding.AuthorityBindingValidationError) as raised:
            authority_binding.validate_authority_binding(candidate)
        self.assertEqual("REJECT_AUTHORITY_BINDING_SCHEMA", raised.exception.reason_code)
        self.assertEqual("$.prohibited_effects", raised.exception.path)

    def test_additional_property_fails_closed(self):
        candidate = self.valid_binding()
        candidate["unregistered_authority"] = True
        with self.assertRaises(authority_binding.AuthorityBindingValidationError) as raised:
            authority_binding.validate_authority_binding(candidate)
        self.assertEqual("REJECT_AUTHORITY_BINDING_SCHEMA", raised.exception.reason_code)

    def test_three_current_consumers_accept_one_legal_object(self):
        candidate = self.valid_binding()
        self.assertTrue(successor_reviewer._validate_authority(candidate, test_mode=False))
        successor_seal._validate_formal_authority(candidate)
        authority_binding.validate_authority_binding(
            candidate,
            required_effect=reconstruct_reviewer.AUTHORIZED_EFFECT,
        )

    def test_reconstruct_consumer_accepts_hash_bound_legal_object(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pointer = self.valid_binding()
            pointer_path = root / "authority.json"
            pointer_path.write_text(
                json.dumps(pointer, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            now = datetime(2026, 8, 21, 18, 10, tzinfo=timezone.utc)
            request = {
                "authority": {
                    "pointer_ref": "authority.json",
                    "pointer_sha256": hashlib.sha256(pointer_path.read_bytes()).hexdigest(),
                    "founder_authorization_ref": "founder.json",
                    "founder_authorization_sha256": "0" * 64,
                },
                "target": {
                    "field_snapshot_sha256": reconstruct_reviewer.TARGET_FIELD_SNAPSHOT_SHA256,
                    "base_state_sha256": reconstruct_reviewer.TARGET_BASE_STATE_SHA256,
                    "canonical_sha256": reconstruct_reviewer.TARGET_SUCCESSOR_CANONICAL_SHA256,
                },
                "delta": {
                    "sha256": reconstruct_reviewer.MINIMUM_GENERATIVE_DELTA_SHA256,
                },
                "workspace": {"root": "/tmp/reconstruct-isolated-test"},
                "exact_targets": ["candidate-a", "candidate-b"],
                "authorized_steps": ["RECONSTRUCT", "VERIFY"],
                "maximum_effect": reconstruct_reviewer.MAXIMUM_EFFECT,
            }
            founder = {
                "state": "FOUNDER_AUTHORIZATION_APPROVED",
                "authorized_effect": reconstruct_reviewer.AUTHORIZED_EFFECT,
                "target_node": "taiji01",
                "target_field_snapshot_sha256": request["target"]["field_snapshot_sha256"],
                "target_base_state_sha256": request["target"]["base_state_sha256"],
                "target_successor_canonical_sha256": request["target"]["canonical_sha256"],
                "minimum_generative_delta_sha256": request["delta"]["sha256"],
                "exact_workspace": request["workspace"]["root"],
                "exact_targets": request["exact_targets"],
                "authorized_steps": request["authorized_steps"],
                "maximum_effect": request["maximum_effect"],
                "single_use": True,
                "created_at": "2026-08-21T18:00:00Z",
                "expires_at": "2026-08-21T18:30:00Z",
            }
            founder_path = root / "founder.json"
            founder_path.write_text(
                json.dumps(founder, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            request["authority"]["founder_authorization_sha256"] = hashlib.sha256(
                founder_path.read_bytes()
            ).hexdigest()
            result = reconstruct_reviewer._validate_authority(request, root, now)
            self.assertEqual(
                request["authority"]["pointer_sha256"],
                result["authority_pointer_sha256"],
            )

    def test_reserved_semantics_are_explicit_candidate_markers(self):
        candidate = self.valid_binding()
        for field in (
            "authority_scope",
            "prohibited_effects",
            "effective_at",
            "expires_at",
            "revocation",
            "lineage",
            "governing_contract_refs",
        ):
            candidate[field] = {"SEMANTICS_STATUS": "UNRESOLVED"}
        authority_binding.validate_authority_binding(candidate)


if __name__ == "__main__":
    unittest.main()
