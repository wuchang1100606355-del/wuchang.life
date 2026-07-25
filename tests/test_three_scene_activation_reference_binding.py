from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.three_major_scene_product_candidate import (  # noqa: E402
    ACTIVATION_BINDING_FILES,
    ACTIVATION_BINDING_RUN_ID,
    EXPECTED_ACTIVATION_BINDING_BASE,
    FUND_AUTHORITY_REF,
    PROPERTY_STATUTORY_MISSING,
    PROPERTY_STATUTORY_SOURCES,
    SCENE_FILES,
    ThreeMajorSceneProductError,
    build_activation_binding_supplement,
    build_committee_branch_reference_contract,
    build_fund_authority_contract,
    build_property_statutory_source_manifest,
    build_total_field_activation_binding_receipt,
    write_activation_precondition_binding,
)


CREATED_AT = "2026-07-23T17:00:00Z"
BASE_DIR = Path(
    "runtime/total_field/three_major_scenes"
) / ACTIVATION_BINDING_RUN_ID


class ThreeSceneActivationReferenceBindingTests(unittest.TestCase):
    def setUp(self):
        self.fund = build_fund_authority_contract(created_at=CREATED_AT)
        self.statutory = build_property_statutory_source_manifest(
            retrieved_at=CREATED_AT
        )
        self.committee = build_committee_branch_reference_contract(
            created_at=CREATED_AT
        )

    def supplement(self):
        return build_activation_binding_supplement(
            run_id=ACTIVATION_BINDING_RUN_ID,
            packet_hashes=EXPECTED_ACTIVATION_BINDING_BASE["packet_sha256"],
            fund_contract=self.fund,
            fund_file_sha256="1" * 64,
            statutory_manifest=self.statutory,
            statutory_file_sha256="2" * 64,
            committee_contract=self.committee,
            committee_file_sha256="3" * 64,
            created_at=CREATED_AT,
        )

    def test_fund_contract_is_exact_local_symbolic_conservation(self):
        self.assertEqual(self.fund["authority_ref"], FUND_AUTHORITY_REF)
        self.assertEqual(self.fund["ratio"], "1:1:1")
        self.assertEqual(self.fund["base_unit"], "法幣")
        self.assertEqual(self.fund["authority"], "LOCAL_TOTAL_FIELD_ONLY")
        self.assertEqual(self.fund["cloud_fill"], "FORBIDDEN")
        self.assertFalse(self.fund["bank_account_plaintext"])
        self.assertFalse(self.fund["member_plaintext"])
        self.assertFalse(self.fund["actual_issuance_quota"])
        self.assertFalse(self.fund["activated"])
        self.assertEqual(
            self.fund["contract_sha256"],
            hashlib.sha256(
                json.dumps(
                    {
                        key: value
                        for key, value in self.fund.items()
                        if key != "contract_sha256"
                    },
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        )

    def test_statutory_manifest_uses_only_verified_official_sources(self):
        self.assertEqual(self.statutory["source_count"], len(PROPERTY_STATUTORY_SOURCES))
        self.assertEqual(
            self.statutory["missing_preconditions"],
            list(PROPERTY_STATUTORY_MISSING),
        )
        self.assertEqual(
            self.statutory["verification_status"],
            "VERIFIED_OR_EXACT_MISSING_LIST",
        )
        for source in self.statutory["sources"]:
            with self.subTest(source=source["document_title"]):
                self.assertTrue(source["official_url"].startswith("https://"))
                self.assertTrue(source["local_reference_or_hash"].startswith("sha256:"))
                self.assertEqual(source["retrieved_at"], CREATED_AT)
        self.assertFalse(self.statutory["generated_content_used"])
        self.assertEqual(self.statutory["cloud_fill"], "FORBIDDEN")

    def test_committee_contract_is_unbound_opaque_and_not_activated(self):
        self.assertEqual(
            self.committee["rule"], "ONE_COMMITTEE=ONE_BRANCH_TOTAL_FIELD"
        )
        for key in (
            "committee_branch_total_field_ref",
            "observation_domain_ref",
            "committee_packet_ref",
            "family_minimum_organization_field_ref",
            "property_scene_packet_ref",
        ):
            self.assertTrue(self.committee[key].startswith("caller-supplied:"))
        self.assertEqual(
            self.committee["lifecycle"],
            "UNBOUND_CALLER_SUPPLIED_REFERENCE_CONTRACT",
        )
        self.assertFalse(self.committee["hardcoded_community_identity"])
        self.assertFalse(self.committee["hardcoded_address"])
        self.assertFalse(self.committee["member_plaintext"])
        self.assertFalse(self.committee["activated"])

    def test_supplement_binds_all_scene_precondition_keys_without_rebuild(self):
        supplement = self.supplement()
        self.assertTrue(supplement["base_packets_immutable"])
        self.assertEqual(supplement["activation_preconditions"], "BOUND")
        self.assertEqual(
            supplement["unresolved_scene_precondition_keys"],
            {scene: [] for scene in SCENE_FILES},
        )
        self.assertFalse(supplement["cloud_fill_used"])
        self.assertFalse(supplement["member_plaintext"])
        self.assertFalse(supplement["bank_account_plaintext"])
        self.assertFalse(supplement["activated"])

    def test_total_field_receipt_uses_existing_candidate_gateway_without_commit(self):
        receipt = build_total_field_activation_binding_receipt(
            self.supplement(), run_id=ACTIVATION_BINDING_RUN_ID
        )
        self.assertEqual(
            receipt["receiver_ref"],
            "tools.total_field_candidate_gateway.receive_candidate",
        )
        self.assertEqual(
            receipt["binding_state"],
            "PASS_ACTIVATION_PRECONDITIONS_BOUND",
        )
        self.assertFalse(receipt["gateway_commit_applied"])
        self.assertFalse(receipt["activated"])

    def test_writer_only_adds_binding_artifacts_and_refuses_overwrite(self):
        original_names = [
            "MANIFEST.json",
            "SHARED_SOVEREIGN_AI_SKILL_CONTRACT.json",
            *SCENE_FILES.values(),
        ]
        original_hashes = {
            name: hashlib.sha256((BASE_DIR / name).read_bytes()).hexdigest()
            for name in original_names
        }
        with TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / ACTIVATION_BINDING_RUN_ID
            target.mkdir()
            for name in original_names:
                shutil.copy2(BASE_DIR / name, target / name)
            result = write_activation_precondition_binding(
                run_id=ACTIVATION_BINDING_RUN_ID,
                output_parent=parent,
                created_at=CREATED_AT,
            )
            self.assertEqual(
                result["STATE"],
                "PASS_THREE_SCENE_ACTIVATION_PRECONDITIONS_BOUND",
            )
            self.assertEqual(
                set(result["FILES_CHANGED"]), set(ACTIVATION_BINDING_FILES.values())
            )
            self.assertEqual(
                original_hashes,
                {
                    name: hashlib.sha256((target / name).read_bytes()).hexdigest()
                    for name in original_names
                },
            )
            checksum_lines = (target / ACTIVATION_BINDING_FILES["checksums"]).read_text(
                encoding="utf-8"
            ).splitlines()
            self.assertEqual(len(checksum_lines), 5)
            with self.assertRaisesRegex(
                ThreeMajorSceneProductError,
                "ACTIVATION_BINDING_OUTPUT_EXISTS",
            ):
                write_activation_precondition_binding(
                    run_id=ACTIVATION_BINDING_RUN_ID,
                    output_parent=parent,
                    created_at=CREATED_AT,
                )


if __name__ == "__main__":
    unittest.main()
