from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.three_major_scene_product_candidate import (  # noqa: E402
    FUND_PRECONDITIONS,
    SCENE_FILES,
    SHARED_SKILL_REFS,
    ThreeMajorSceneProductError,
    apply_scene_workflow_event,
    build_cloud_fill_receipt,
    build_cloud_fill_request,
    build_code_gap_manifest,
    build_identity_tensor_packet,
    build_scene_packet,
    build_shared_sovereign_ai_skill_contract,
    build_total_field_candidate_receipt,
    load_product_config,
    parse_scene_packet,
    reconstruct_scene_intent_field,
    validate_cloud_fill_candidate,
    verify_scene_packet,
    write_candidate_bundle,
)


class ThreeMajorSceneProductCandidateTests(unittest.TestCase):
    def setUp(self):
        self.product = load_product_config()
        self.identity = build_identity_tensor_packet(
            "identity-packet-ref:test-member",
            resource_refs=("resource-ref:test-scope",),
        )
        self.created_at = "2026-07-23T16:00:00Z"
        self.now = "2026-07-23T16:00:01Z"

    def authority_refs(self, scene):
        refs = {
            key: f"authority-ref:{key}" for key in FUND_PRECONDITIONS
        }
        if scene in {"public_benefit", "property"}:
            refs["legal_document_source_refs"] = [
                "legal-source-ref:verified-local-index"
            ]
        if scene == "property":
            refs["management_committee_branch_total_field_ref"] = (
                "branch-total-field-ref:test-committee"
            )
        return refs

    def packet(self, scene, *, authority_refs=None, nonce_suffix="base"):
        return build_scene_packet(
            scene,
            identity_packet=self.identity,
            intent_text=f"{scene} product intent",
            event_type="TEST_PRODUCT_EVENT",
            event_refs=(f"evidence-ref:{scene}",),
            authority_refs=(
                self.authority_refs(scene)
                if authority_refs is None
                else authority_refs
            ),
            nonce=(f"nonce-{scene}-{nonce_suffix}-0123456789"),
            created_at=self.created_at,
            ttl_seconds=3600,
            product_config=self.product,
        )

    def test_shared_contract_is_one_reference_for_all_three_scenes(self):
        contract = build_shared_sovereign_ai_skill_contract(self.product)
        self.assertEqual(tuple(contract["skills"]), SHARED_SKILL_REFS)
        self.assertFalse(contract["central_real_name_identity_graph"])
        self.assertFalse(contract["member_plaintext_to_cloud"])
        self.assertFalse(contract["raw_media_to_cloud"])
        refs = set()
        hashes = set()
        for scene in SCENE_FILES:
            packet = self.packet(scene)
            refs.add(packet["shared_skill_contract_ref"])
            hashes.add(packet["shared_skill_contract_sha256"])
            self.assertNotIn("three_party_collaboration", packet)
        self.assertEqual(refs, {contract["contract_ref"]})
        self.assertEqual(hashes, {contract["contract_sha256"]})

    def test_three_scene_packets_parse_and_verify(self):
        expected_types = {
            "public_benefit": "COMMUNITY_ASSOCIATION_PUBLIC_BENEFIT_SCENE_PACKET",
            "property": "INTEGRATED_PROPERTY_MANAGEMENT_SCENE_PACKET",
            "merchant": "COMMUNITY_MERCHANT_MANAGEMENT_SCENE_PACKET",
        }
        for scene in SCENE_FILES:
            with self.subTest(scene=scene):
                packet = self.packet(scene)
                parsed = parse_scene_packet(json.dumps(packet, ensure_ascii=False))
                receipt = verify_scene_packet(
                    parsed,
                    identity_packet=self.identity,
                    now=self.now,
                )
                self.assertEqual(parsed["packet_type"], expected_types[scene])
                self.assertEqual(receipt["decision"], "PASS_CANDIDATE")
                self.assertTrue(
                    all(value == "PASS" for value in receipt["checks"].values())
                )

    def test_missing_authority_inputs_are_preconditions_not_cloud_fill(self):
        for scene in SCENE_FILES:
            with self.subTest(scene=scene):
                packet = self.packet(scene, authority_refs={})
                receipt = verify_scene_packet(
                    packet,
                    identity_packet=self.identity,
                    now=self.now,
                )
                self.assertEqual(receipt["decision"], "PRECONDITION_MISSING")
                self.assertTrue(receipt["missing_preconditions"])
                if scene in {"public_benefit", "merchant"}:
                    self.assertTrue(
                        set(FUND_PRECONDITIONS).issubset(
                            receipt["missing_preconditions"]
                        )
                    )
                forbidden = set(packet["D6"]["cloud_fill_forbidden"])
                self.assertIn("one_to_one_to_one_formula", forbidden)
                self.assertIn("fund_rules_or_values", forbidden)

    def test_public_benefit_product_has_five_competitive_core_units(self):
        features = self.packet("public_benefit")["D4"]["product_features"]
        self.assertTrue(
            {
                "dedicated_service_team",
                "commercial_volunteer_team",
                "delivery_service",
                "renyi_cafe_branch",
                "community_digital_development_fund",
            }.issubset(features)
        )
        delivery = features["delivery_service"]
        self.assertIn("外送", delivery["system_description"])
        self.assertIn("DRAFT->PURCHASER_CONFIRMED", delivery["transitions"])
        self.assertIn("DELIVERED->SETTLEMENT_CANDIDATE", delivery["transitions"])
        self.assertTrue(delivery["member_checkout_confirmation_required"])
        self.assertEqual(
            delivery["guest_label_when_phone_last_three_blank"], "一般路人"
        )
        self.assertTrue(delivery["phone_last_three_is_lookup_hint_only"])
        self.assertFalse(delivery["autonomous_payment_execution"])
        volunteer = features["commercial_volunteer_team"]
        self.assertIn("delivery_assignment", volunteer["functions"])
        self.assertIn("merchant_service_assignment", volunteer["functions"])
        central = features["renyi_cafe_branch"][
            "community_happiness_coin_central_bank_concept"
        ]
        self.assertFalse(central["actual_currency_or_bank_claim"])
        self.assertEqual(
            central["issuance_and_limit_authority"], "LOCAL_TOTAL_FIELD_ONLY"
        )

    def test_configured_workflow_transitions_execute_and_reject_drift(self):
        accepted = apply_scene_workflow_event(
            "public_benefit",
            "volunteer_assignment",
            current_state="MATCHED",
            target_state="ACCEPTED",
            event_ref="event-ref:volunteer-explicit-acceptance",
            product_config=self.product,
        )
        self.assertEqual(accepted["candidate_state"], "ACCEPTED")
        self.assertFalse(accepted["runtime_enabled"])
        with self.assertRaisesRegex(
            ThreeMajorSceneProductError, "WORKFLOW_TRANSITION_FORBIDDEN"
        ):
            apply_scene_workflow_event(
                "property",
                "camera_review",
                current_state="REQUESTED",
                target_state="CLOSED",
                event_ref="event-ref:skip-review",
                product_config=self.product,
            )

    def test_reconstruction_projects_required_end_to_end_flow(self):
        packet = self.packet("public_benefit")
        reconstruction = reconstruct_scene_intent_field(
            packet,
            identity_packet=self.identity,
            now=self.now,
        )
        self.assertEqual(
            reconstruction["state"],
            "RECONSTRUCTED_CANDIDATE_READY_FOR_TOTAL_FIELD",
        )
        self.assertEqual(
            list(reconstruction["flow_projection"]),
            [
                "TOTAL_FIELD_DESCRIPTION",
                "D1_INTENT",
                "D3_COORDINATE",
                "REQUIRED_SKILL_REFS",
                "EVENT",
                "STATE_TRANSITION",
                "CLOUD_FILLABLE_CODE_ZONE",
                "LOCAL_RECONSTRUCTION",
                "D7_VERIFICATION",
                "D8_RECEIPT",
            ],
        )

    def test_replay_and_tamper_are_rejected(self):
        packet = self.packet("merchant")
        ledger = set()
        first = verify_scene_packet(
            packet,
            identity_packet=self.identity,
            now=self.now,
            replay_ledger=ledger,
        )
        second = verify_scene_packet(
            packet,
            identity_packet=self.identity,
            now=self.now,
            replay_ledger=ledger,
        )
        self.assertEqual(first["decision"], "PASS_CANDIDATE")
        self.assertEqual(second["decision"], "REJECT")
        self.assertEqual(second["checks"]["replay"], "FAIL")
        tampered = json.loads(json.dumps(packet))
        tampered["D1"]["D1_INTENT"] = "tampered"
        receipt = verify_scene_packet(
            tampered,
            identity_packet=self.identity,
            now=self.now,
        )
        self.assertEqual(receipt["checks"]["integrity"], "FAIL")

    def test_plaintext_and_cloud_authority_paths_are_blocked(self):
        with self.assertRaisesRegex(
            ThreeMajorSceneProductError, "AUTHORITY_REF_PLAINTEXT_FORBIDDEN"
        ):
            self.packet(
                "public_benefit",
                authority_refs={"member_plaintext": "forbidden"},
            )
        with self.assertRaisesRegex(
            ThreeMajorSceneProductError, "CLOUD_AUTHORITY_ZONE_FORBIDDEN"
        ):
            validate_cloud_fill_candidate(
                {
                    "code_zones": ["one_to_one_to_one_formula"],
                    "candidate_only": True,
                    "formal_execution_authority": False,
                    "database_write": False,
                    "deploy": False,
                    "restart": False,
                    "router_write": False,
                    "canonical_write": False,
                }
            )
        with self.assertRaisesRegex(
            ThreeMajorSceneProductError, "CLOUD_AUTHORITY_CLAIM_FORBIDDEN"
        ):
            validate_cloud_fill_candidate(
                {
                    "code_zones": ["serializer"],
                    "candidate_only": True,
                    "formal_execution_authority": True,
                    "database_write": False,
                    "deploy": False,
                    "restart": False,
                    "router_write": False,
                    "canonical_write": False,
                }
            )

    def test_code_gap_and_cloud_receipts_do_not_fake_provider(self):
        manifest = build_code_gap_manifest(self.product)
        request = build_cloud_fill_request(manifest)
        receipt = build_cloud_fill_receipt(manifest)
        self.assertEqual(manifest["gaps"], [])
        self.assertFalse(manifest["cloud_fill_required"])
        self.assertEqual(
            request["request_state"], "NOT_DISPATCHED_NO_GENERAL_CODE_GAPS"
        )
        self.assertEqual(
            request["payload_mode"], "DEIDENTIFIED_INCOMPLETE_REFERENCE_ONLY"
        )
        self.assertFalse(request["member_plaintext_included"])
        self.assertEqual(receipt["state"], "NOT_REQUESTED_NO_GENERAL_CODE_GAPS")
        self.assertFalse(receipt["provider_response_present"])
        self.assertFalse(receipt["fake_provider_response"])
        self.assertFalse(receipt["authority_rule_sent"])

    def test_total_field_receipt_uses_existing_gateway_without_adoption(self):
        packets = {scene: self.packet(scene) for scene in SCENE_FILES}
        receipt = build_total_field_candidate_receipt(
            packets, run_id="THREE_SCENE_TEST"
        )
        self.assertEqual(
            receipt["receiver_ref"],
            "tools.total_field_candidate_gateway.receive_candidate",
        )
        self.assertEqual(receipt["canonical_status"], "CANDIDATE_NOT_CANONICAL")
        self.assertFalse(receipt["canonical_write"])
        self.assertEqual(set(receipt["scene_results"]), set(SCENE_FILES))
        for result in receipt["scene_results"].values():
            self.assertIn(
                result["source_adoption"],
                {"CANDIDATE_ONLY", "HOLD_GATEWAY_COMMIT_OUT_OF_SCOPE"},
            )

    def test_bundle_contains_all_required_artifacts_and_valid_checksums(self):
        with TemporaryDirectory() as temp_dir:
            result = write_candidate_bundle(
                run_id="THREE_SCENE_BUNDLE_TEST",
                output_parent=temp_dir,
                created_at=self.created_at,
            )
            root = Path(result["OUTPUT_ROOT"])
            required = {
                *SCENE_FILES.values(),
                "SHARED_SOVEREIGN_AI_SKILL_CONTRACT.json",
                "VERIFIED_8D_IDENTITY_TENSOR_CANDIDATE.json",
                "THREE_MAJOR_SCENE_PACKET_SCHEMA.json",
                "CODE_GAP_MANIFEST.json",
                "CLOUD_FILL_REQUEST.json",
                "CLOUD_FILL_CANDIDATE_RECEIPT.json",
                "LOCAL_RECONSTRUCTION_RECEIPT.json",
                "TOTAL_FIELD_CANDIDATE_RECEIPT.json",
                "REQUIREMENTS_AUDIT.json",
                "MANIFEST.json",
                "SHA256SUMS",
            }
            self.assertEqual({path.name for path in root.iterdir()}, required)
            audit = json.loads((root / "REQUIREMENTS_AUDIT.json").read_text())
            self.assertEqual(audit["source_candidate_completion"], "PASS")
            self.assertEqual(
                audit["activation_readiness"], "HOLD_PRECONDITION_MISSING"
            )
            self.assertTrue(
                all(status == "PASS" for status in audit["checks"].values())
            )
            for line in (root / "SHA256SUMS").read_text().splitlines():
                expected, name = line.split("  ", 1)
                actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
