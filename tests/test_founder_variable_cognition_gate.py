from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.founder_variable_cognition_gate import (
    authorize_total_field_change,
    build_execution_evidence,
    build_sealed_founder_root,
    compose_capability_candidate,
    evaluate_founder_identity_gate,
    govern_package_action,
    select_execution_path,
)


PAYLOAD = b"variable-cognition-package-synthetic-payload-v1"
DEVICE_FINGERPRINT = "sha256:" + "2" * 64
OIDC_ISSUER = "https://accounts.google.com"
OIDC_SUBJECT_SHA256 = "3" * 64


def founder_root() -> dict[str, object]:
    return build_sealed_founder_root(
        DEVICE_FINGERPRINT,
        OIDC_ISSUER,
        OIDC_SUBJECT_SHA256,
    )


def founder_identity_request() -> dict[str, object]:
    return {
        "device_principal_fingerprint": DEVICE_FINGERPRINT,
        "google_oidc_issuer": OIDC_ISSUER,
        "google_oidc_subject_sha256": OIDC_SUBJECT_SHA256,
        "explicit_founder_command": True,
        "founder_command_ref": "founder-command:synthetic-test-001",
        "d8_decision": "ALLOW",
        "future_identity_adapters": {
            "tw_moi_digital_natural_person_id": "DISABLED_NOT_CONFIGURED",
            "physical_natural_person_certificate_card": "DISABLED_NOT_CONFIGURED",
        },
    }


def candidate_manifest() -> dict[str, object]:
    return {
        "package_id": "vcp:synthetic-cognition-v1",
        "name": "Synthetic Verified Cognition",
        "version": "1.0.0",
        "sha256": hashlib.sha256(PAYLOAD).hexdigest(),
        "source_ref": "source:synthetic-test",
        "capability_scope": ["candidate_reasoning"],
        "requested_permissions": ["emit_candidate", "write_package_evidence"],
        "allowed_nodes": ["taiji01", "FOUNDER_GPU_EXECUTION_NODE"],
        "compatibility": {
            "cpu_baseline_required": True,
            "required_dependencies": ["total-field-gate-v1"],
            "conflicts": [],
        },
        "reconstruction_conditions": {
            "equivalence_level": "L2",
            "total_field_seal_required": True,
        },
        "packet_carried_protocol": {
            "kind": "W7TP_8D_STATE_FIELD_PACKET",
            "protocol_native": True,
            "references": True,
            "lookup": True,
            "reconstruction_contract": True,
        },
        "packet_carried_validation": {
            "total_field_verification": True,
            "before_state_sha256": True,
            "after_state_sha256": True,
        },
        "evidence_refs": ["evidence:synthetic-test"],
        "risk_status": "CLEAR",
        "installed_by": None,
        "founder_command_ref": None,
        "lifecycle_state": "CANDIDATE",
        "created_at": "2026-07-16T07:04:07Z",
        "updated_at": "2026-07-16T07:04:07Z",
    }


class FounderVariableCognitionGateTest(unittest.TestCase):
    def test_founder_dual_factor_explicit_command_allows(self) -> None:
        result = evaluate_founder_identity_gate(founder_identity_request(), founder_root())
        self.assertEqual(result["decision"], "ALLOW")
        self.assertTrue(all(result["checks"].values()))

    def test_missing_local_root_holds(self) -> None:
        result = evaluate_founder_identity_gate(founder_identity_request())
        self.assertEqual(result["decision"], "HOLD")
        self.assertEqual(
            result["reason_code"], "HOLD_FOUNDER_ROOT_NOT_PROVISIONED_OR_INVALID"
        )

    def test_google_oidc_only_blocks(self) -> None:
        request = founder_identity_request()
        request.pop("device_principal_fingerprint")
        self.assertEqual(
            evaluate_founder_identity_gate(request, founder_root())["decision"],
            "BLOCK",
        )

    def test_device_principal_only_blocks(self) -> None:
        request = founder_identity_request()
        request.pop("google_oidc_subject_sha256")
        self.assertEqual(
            evaluate_founder_identity_gate(request, founder_root())["decision"],
            "BLOCK",
        )

    def test_extra_identity_field_and_enabled_future_adapter_block(self) -> None:
        extra = founder_identity_request()
        extra["unregistered_identity_factor"] = "synthetic"
        self.assertEqual(
            evaluate_founder_identity_gate(extra, founder_root())["decision"],
            "BLOCK",
        )
        enabled_adapter = founder_identity_request()
        enabled_adapter["future_identity_adapters"] = {
            "tw_moi_digital_natural_person_id": "ENABLED",
            "physical_natural_person_certificate_card": "DISABLED_NOT_CONFIGURED",
        }
        self.assertEqual(
            evaluate_founder_identity_gate(enabled_adapter, founder_root())["decision"],
            "BLOCK",
        )

    def test_name_or_command_string_cannot_elevate(self) -> None:
        request = founder_identity_request()
        request["founder_natural_person"] = "synthetic-name"
        self.assertEqual(
            evaluate_founder_identity_gate(request, founder_root())["decision"],
            "BLOCK",
        )

    def test_plaintext_identity_or_token_is_blocked(self) -> None:
        for field in ("email", "access_token", "password", "credential"):
            with self.subTest(field=field):
                request = founder_identity_request()
                request[field] = "synthetic-sensitive-fixture"
                result = evaluate_founder_identity_gate(request, founder_root())
                self.assertEqual(result["decision"], "BLOCK")
                self.assertEqual(
                    result["reason_code"], "SENSITIVE_IDENTITY_MATERIAL_BLOCKED"
                )

    def test_admin_cannot_modify_total_field(self) -> None:
        result = authorize_total_field_change(
            "ADMIN", founder_identity_request(), founder_root()
        )
        self.assertEqual(result["decision"], "BLOCK")
        self.assertEqual(result["target"], "TOTAL_FIELD_CANONICAL")

    def test_personnel_cannot_install_package(self) -> None:
        result = govern_package_action(
            "install",
            "PERSONNEL",
            founder_identity_request(),
            candidate_manifest(),
            PAYLOAD,
            ["total-field-gate-v1"],
            founder_root(),
        )
        self.assertEqual(result["decision"], "BLOCK")

    def test_ai_cannot_install_but_can_submit_candidate(self) -> None:
        blocked = govern_package_action(
            "install",
            "AI",
            founder_identity_request(),
            candidate_manifest(),
            PAYLOAD,
            ["total-field-gate-v1"],
            founder_root(),
        )
        candidate = govern_package_action(
            "submit_candidate",
            "AI",
            {},
            candidate_manifest(),
            PAYLOAD,
            ["total-field-gate-v1"],
        )
        self.assertEqual(blocked["decision"], "BLOCK")
        self.assertEqual(candidate["decision"], "CANDIDATE")

    def test_privilege_escalation_is_quarantined(self) -> None:
        manifest = candidate_manifest()
        manifest["capability_scope"] = ["modify_founder_identity_root"]
        result = govern_package_action(
            "submit_candidate", "AI", {}, manifest, PAYLOAD, ["total-field-gate-v1"]
        )
        self.assertEqual(result["decision"], "QUARANTINE")
        self.assertEqual(result["lifecycle_state"], "QUARANTINED")

    def test_hash_mismatch_is_quarantined(self) -> None:
        manifest = candidate_manifest()
        manifest["sha256"] = "0" * 64
        result = govern_package_action(
            "submit_candidate", "NODE", {}, manifest, PAYLOAD, ["total-field-gate-v1"]
        )
        self.assertEqual(result["decision"], "QUARANTINE")
        self.assertIn("PACKAGE_SHA256_MISMATCH", result["validation"]["errors"])

    def test_founder_can_install_verified_package(self) -> None:
        result = govern_package_action(
            "install",
            "FOUNDER",
            founder_identity_request(),
            candidate_manifest(),
            PAYLOAD,
            ["total-field-gate-v1"],
            founder_root(),
        )
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["lifecycle_state"], "VERIFIED")

    def test_two_enabled_capabilities_fuse_into_new_candidate(self) -> None:
        source_a = candidate_manifest()
        source_a["lifecycle_state"] = "ENABLED"
        source_b = candidate_manifest()
        source_b["package_id"] = "vcp:synthetic-cognition-v2"
        source_b["lifecycle_state"] = "ENABLED"
        source_b["capability_scope"] = ["candidate_evidence_synthesis"]
        source_b["requested_permissions"] = ["read_package_state", "emit_candidate"]

        composite_payload = b"synthetic-composite-capability-payload-v1"
        composite = candidate_manifest()
        composite["package_id"] = "vcp:synthetic-composite-cognition-v1"
        composite["name"] = "Synthetic Composite Cognition"
        composite["sha256"] = hashlib.sha256(composite_payload).hexdigest()
        composite["capability_scope"] = ["derived_reasoning_and_evidence_synthesis"]

        result = compose_capability_candidate(
            [(source_a, PAYLOAD), (source_b, PAYLOAD)],
            composite,
            composite_payload,
            ["total-field-gate-v1"],
        )

        self.assertEqual(result["decision"], "CANDIDATE")
        self.assertEqual(result["lifecycle_state"], "CANDIDATE")
        self.assertEqual(result["manifest"]["composition"]["mode"], "STACK_AND_FUSE")
        self.assertEqual(len(result["manifest"]["composition"]["source_packages"]), 2)
        schema = json.loads(
            (ROOT / "schemas/field/variable_cognition_package_manifest.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator(schema).validate(result["manifest"])

    def test_capability_fusion_permission_expansion_is_quarantined(self) -> None:
        source_a = candidate_manifest()
        source_a["lifecycle_state"] = "ENABLED"
        source_b = candidate_manifest()
        source_b["package_id"] = "vcp:synthetic-cognition-v2"
        source_b["lifecycle_state"] = "ENABLED"

        composite_payload = b"synthetic-composite-capability-payload-v2"
        composite = candidate_manifest()
        composite["package_id"] = "vcp:synthetic-composite-cognition-v2"
        composite["sha256"] = hashlib.sha256(composite_payload).hexdigest()
        composite["requested_permissions"] = [
            "emit_candidate",
            "execute_local_verified_reconstruction",
        ]

        result = compose_capability_candidate(
            [(source_a, PAYLOAD), (source_b, PAYLOAD)],
            composite,
            composite_payload,
            ["total-field-gate-v1"],
        )

        self.assertEqual(result["decision"], "QUARANTINE")
        self.assertEqual(result["reason"], "COMPOSITION_PERMISSION_EXPANSION")
        self.assertEqual(result["lifecycle_state"] if "lifecycle_state" in result else result["manifest"]["lifecycle_state"], "QUARANTINED")

    def test_enabled_package_execution_emits_state_hashes(self) -> None:
        manifest = candidate_manifest()
        manifest["lifecycle_state"] = "ENABLED"
        evidence = build_execution_evidence(manifest, {"state": "before"}, {"state": "after"})
        self.assertEqual(evidence["decision"], "ALLOW")
        self.assertEqual(len(evidence["before_state_sha256"]), 64)
        self.assertEqual(len(evidence["after_state_sha256"]), 64)
        self.assertNotEqual(evidence["before_state_sha256"], evidence["after_state_sha256"])

    def test_msi_online_uses_gpu_support(self) -> None:
        result = select_execution_path(True)
        self.assertEqual(result["execution_mode"], "GPU_SUPPORT")
        self.assertIn("CPU_BASELINE", result["execution_nodes"])
        self.assertIn("FOUNDER_GPU_EXECUTION_NODE", result["execution_nodes"])

    def test_msi_offline_keeps_cpu_baseline(self) -> None:
        result = select_execution_path(False)
        self.assertEqual(result["execution_mode"], "CPU_BASELINE_CONTINUES")
        self.assertEqual(result["execution_nodes"], ["CPU_BASELINE"])

    def test_cloud_model_without_founder_authorization_blocks(self) -> None:
        result = select_execution_path(
            False,
            cloud_model_requested=True,
            founder_identity_request={},
            sealed_root=founder_root(),
        )
        self.assertEqual(result["cloud_model_decision"], "BLOCK")
        self.assertFalse(result["cloud_model_auto_enabled"])

    def test_schemas_accept_allow_gate_and_candidate_manifest(self) -> None:
        for relative_path, instance in (
            ("schemas/field/founder_identity_gate.schema.json", founder_identity_request()),
            ("schemas/field/variable_cognition_package_manifest.schema.json", candidate_manifest()),
        ):
            schema = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(instance)


if __name__ == "__main__":
    unittest.main()
