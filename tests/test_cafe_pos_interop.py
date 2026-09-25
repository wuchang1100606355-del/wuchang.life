from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from tools.total_field.founder_variable_cognition_gate import build_sealed_founder_root
from tools.total_field.quickclick_menu_snapshot import build_web_data
from tools.total_field.w7tp_field_application_runtime import FieldApplicationError
from tools.total_field.w7tp_core_encoding import (
    build_encoding_registry,
    build_source_coordinate,
    build_surface_binding_ref,
    explain_code,
)
from tools.total_field.w7tp_intent_field_suite.cafe_pos_interop import (
    DEFAULT_MENU_SNAPSHOT_PATH,
    build_binding_seal_request,
    build_preview_binding_registry,
    evaluate_binding_seal_request,
    rectify_surface_candidate,
)
from tools.total_field.w7tp_intent_field_suite.canonical_hash import canonical_sha256
from tools.total_field.w7tp_intent_field_suite.deployment import ROOT
from tools.total_field.w7tp_intent_field_suite.cli import main as suite_main


class CafePosInteropTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        snapshot = json.loads(DEFAULT_MENU_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        cls.menu = build_web_data(snapshot)
        cls.registries = {
            surface: build_preview_binding_registry(surface)
            for surface in ("ODOO_HUMAN", "ADI_AI")
        }

    def _surface_candidate(self, surface: str, product: dict) -> dict:
        registry = self.registries[surface]
        return self._candidate_for(self.menu, registry, product)

    def _production_registry(self, surface: str) -> dict:
        registry = copy.deepcopy(self.registries[surface])
        registry["state"] = "PROVISIONED_VERIFIED_READ_ONLY_BINDINGS"
        registry["production_bindings"] = True
        for field, entity_type in (
            ("product_bindings", "PRODUCT"),
            ("question_bindings", "QUESTION"),
            ("option_bindings", "OPTION"),
        ):
            prefix = (
                f"ODOO_{entity_type}_REF:v1:sha256:"
                if surface == "ODOO_HUMAN"
                else f"ADI_5D_{entity_type}_REF:v1:sha256:"
            )
            for item in registry[field]:
                item["surface_ref"] = prefix + canonical_sha256(
                    {
                        "fixture": "synthetic-external-read-only-binding",
                        "surface": surface,
                        "entity_type": entity_type,
                        "source_ref": item["source_ref"],
                    }
                )
        unsigned = dict(registry)
        unsigned.pop("content_sha256")
        registry["content_sha256"] = canonical_sha256(unsigned)
        return registry

    @staticmethod
    def _candidate_for(menu: dict, registry: dict, product: dict) -> dict:
        product_ref = next(
            item["surface_ref"]
            for item in registry["product_bindings"]
            if item["source_ref"] == product["sourceRef"]
        )
        questions = [
            question
            for group in menu["optionGroups"]
            if group["id"] in product["optionGroupIds"]
            for question in group["questions"]
        ]
        selections = {}
        for question in questions:
            if not question["required"]:
                continue
            source_question_ref = (
                f"QUICKCLICK:{menu['source']['id']}:{question['id']}"
            )
            source_option_ref = (
                f"QUICKCLICK:{menu['source']['id']}:"
                f"{question['options'][0]['id']}"
            )
            surface_question_ref = next(
                item["surface_ref"]
                for item in registry["question_bindings"]
                if item["source_ref"] == source_question_ref
            )
            surface_option_ref = next(
                item["surface_ref"]
                for item in registry["option_bindings"]
                if item["source_ref"] == source_option_ref
            )
            selections[surface_question_ref] = surface_option_ref
        return {"product_ref": product_ref, "quantity": 2, "selections": selections}

    def test_core_encoding_registry_explains_every_position(self) -> None:
        registry = build_encoding_registry()
        schema = json.loads(
            (ROOT / "schemas/field/w7tp_core_encoding_registry.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(registry)

        source = build_source_coordinate("OPTION", "M387676", "O7835309:Q1:O2")
        explanation = explain_code(source)
        self.assertEqual(explanation["entity_type"], "OPTION")
        self.assertEqual(
            [position["meaning"] for position in explanation["positions"]],
            [
                "SOURCE_AUTHORITY_NAMESPACE",
                "MENU_IDENTITY",
                "OPTION_GROUP_IDENTITY",
                "QUESTION_ORDINAL_WITHIN_GROUP",
                "OPTION_ORDINAL_WITHIN_QUESTION",
            ],
        )
        surface_ref = build_surface_binding_ref("ADI_AI", "OPTION", source)
        surface_explanation = explain_code(surface_ref)
        self.assertEqual(surface_explanation["surface"], "ADI_AI")
        self.assertEqual(surface_explanation["positions"][1]["meaning"], "ENCODING_MAJOR_VERSION")

    def test_source_coordinates_do_not_collapse_reused_or_missing_codes(self) -> None:
        option_codes = [
            option["sourceOptionCode"]
            for group in self.menu["optionGroups"]
            for question in group["questions"]
            for option in question["options"]
            if option["sourceOptionCode"]
        ]
        self.assertEqual(len(set(option_codes)), 40)
        self.assertEqual(sum(code is None for group in self.menu["optionGroups"] for question in group["questions"] for code in [option["sourceOptionCode"] for option in question["options"]]), 15)
        for registry in self.registries.values():
            self.assertEqual(len(registry["product_bindings"]), 58)
            self.assertEqual(len(registry["question_bindings"]), 45)
            self.assertEqual(len(registry["option_bindings"]), 212)
            self.assertEqual(
                len({item["surface_ref"] for item in registry["option_bindings"]}),
                212,
            )
        self.assertEqual(
            sum(product["sourceProductCode"] is None for product in self.menu["products"]),
            10,
        )
        self.assertTrue(
            all(
                item["surface_ref"].startswith("ODOO_PRODUCT_PREVIEW_REF:v1:sha256:")
                for item in self.registries["ODOO_HUMAN"]["product_bindings"]
            )
        )

    def test_odoo_human_and_adi_ai_rectify_to_identical_semantics(self) -> None:
        product = next(item for item in self.menu["products"] if item["optionGroupIds"])
        results = {
            surface: rectify_surface_candidate(
                surface,
                self._surface_candidate(surface, product),
                binding_registry=self.registries[surface],
            )
            for surface in ("ODOO_HUMAN", "ADI_AI")
        }
        self.assertEqual(
            results["ODOO_HUMAN"]["semantic_candidate"],
            results["ADI_AI"]["semantic_candidate"],
        )
        self.assertEqual(
            results["ODOO_HUMAN"]["semantic_content_sha256"],
            results["ADI_AI"]["semantic_content_sha256"],
        )
        self.assertNotEqual(
            results["ODOO_HUMAN"]["envelope_content_sha256"],
            results["ADI_AI"]["envelope_content_sha256"],
        )
        self.assertEqual(results["ADI_AI"]["execution_metadata"]["llm_execution"], "USER_DEVICE_ONLY")
        self.assertTrue(results["ODOO_HUMAN"]["total_field"]["same_semantic_flow"])

    def test_menu_addition_and_deletion_rebuild_dynamic_bindings(self) -> None:
        original = json.loads(DEFAULT_MENU_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        original_registry = self.registries["ODOO_HUMAN"]
        original_refs = {
            item["source_ref"]: item["surface_ref"]
            for item in original_registry["product_bindings"]
        }
        schema_path = ROOT / "schemas/field/w7tp_cafe_pos_interop_candidate.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        active_product = next(
            product for product in original["products"] if product["category"] != "濾掛咖啡"
        )
        for operation, expected_count in (("delete", 57), ("add", 59)):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                snapshot = copy.deepcopy(original)
                snapshot["source"]["sha256"] = (
                    "1" * 64 if operation == "delete" else "2" * 64
                )
                if operation == "delete":
                    snapshot["products"] = [
                        product
                        for product in snapshot["products"]
                        if product["product_id"] != active_product["product_id"]
                    ]
                    snapshot["counts"]["products"] -= 1
                else:
                    added = copy.deepcopy(active_product)
                    added.update(
                        {
                            "product_id": "99000001",
                            "product_code": None,
                            "sku": None,
                            "name": f"{active_product['name']}測試新增",
                        }
                    )
                    snapshot["products"].append(added)
                    snapshot["counts"]["products"] += 1
                path = Path(directory) / "menu-snapshot.json"
                path.write_text(
                    json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                    encoding="utf-8",
                )
                menu = build_web_data(snapshot)
                registry = build_preview_binding_registry(
                    "ODOO_HUMAN", snapshot_path=path
                )
                candidate_product = menu["products"][0]
                result = rectify_surface_candidate(
                    "ODOO_HUMAN",
                    self._candidate_for(menu, registry, candidate_product),
                    binding_registry=registry,
                    snapshot_path=path,
                )
                self.assertEqual(result["binding_registry"]["product_count"], expected_count)
                shared_binding = next(
                    item
                    for item in registry["product_bindings"]
                    if item["source_ref"] in original_refs
                )
                self.assertEqual(
                    shared_binding["surface_ref"],
                    original_refs[shared_binding["source_ref"]],
                )
                self.assertNotEqual(
                    registry["content_sha256"], original_registry["content_sha256"]
                )
                Draft202012Validator(schema).validate(result)

    def test_required_option_unknown_coordinate_and_quantity_fail_closed(self) -> None:
        product = next(item for item in self.menu["products"] if item["optionGroupIds"])
        candidate = self._surface_candidate("ODOO_HUMAN", product)
        candidate["selections"] = {}
        with self.assertRaises(FieldApplicationError) as missing:
            rectify_surface_candidate(
                "ODOO_HUMAN",
                candidate,
                binding_registry=self.registries["ODOO_HUMAN"],
            )
        self.assertEqual(missing.exception.reason_code, "CAFE_POS_REQUIRED_OPTION_MISSING")

        candidate = self._surface_candidate("ODOO_HUMAN", product)
        candidate["product_ref"] = "ODOO_PRODUCT_REF:unknown"
        with self.assertRaises(FieldApplicationError) as unknown:
            rectify_surface_candidate(
                "ODOO_HUMAN",
                candidate,
                binding_registry=self.registries["ODOO_HUMAN"],
            )
        self.assertEqual(unknown.exception.reason_code, "CAFE_POS_UNKNOWN_PRODUCT_REF")

        candidate = self._surface_candidate("ODOO_HUMAN", product)
        candidate["quantity"] = 100
        with self.assertRaises(FieldApplicationError) as quantity:
            rectify_surface_candidate(
                "ODOO_HUMAN",
                candidate,
                binding_registry=self.registries["ODOO_HUMAN"],
            )
        self.assertEqual(quantity.exception.reason_code, "CAFE_POS_QUANTITY_INVALID")

    def test_registry_tamper_duplicate_and_adi_rule_disclosure_fail_closed(self) -> None:
        product = self.menu["products"][0]
        candidate = self._surface_candidate("ADI_AI", product)
        registry = copy.deepcopy(self.registries["ADI_AI"])
        registry["source_snapshot"]["source_export_sha256"] = "0" * 64
        unsigned = dict(registry)
        unsigned.pop("content_sha256")
        registry["content_sha256"] = canonical_sha256(unsigned)
        with self.assertRaises(FieldApplicationError) as snapshot:
            rectify_surface_candidate("ADI_AI", candidate, binding_registry=registry)
        self.assertEqual(snapshot.exception.reason_code, "CAFE_POS_BINDING_SNAPSHOT_MISMATCH")

        registry = copy.deepcopy(self.registries["ADI_AI"])
        registry["option_bindings"][1]["surface_ref"] = registry["option_bindings"][0]["surface_ref"]
        unsigned = dict(registry)
        unsigned.pop("content_sha256")
        registry["content_sha256"] = canonical_sha256(unsigned)
        with self.assertRaises(FieldApplicationError) as duplicate:
            rectify_surface_candidate("ADI_AI", candidate, binding_registry=registry)
        self.assertEqual(duplicate.exception.reason_code, "CAFE_POS_SURFACE_REF_DUPLICATE")

        registry = copy.deepcopy(self.registries["ADI_AI"])
        registry["adi_internal_rules_disclosed"] = True
        unsigned = dict(registry)
        unsigned.pop("content_sha256")
        registry["content_sha256"] = canonical_sha256(unsigned)
        with self.assertRaises(FieldApplicationError) as disclosure:
            rectify_surface_candidate("ADI_AI", candidate, binding_registry=registry)
        self.assertEqual(disclosure.exception.reason_code, "CAFE_POS_ADI_RULE_DISCLOSURE_BLOCKED")

        registry = copy.deepcopy(self.registries["ADI_AI"])
        registry["state"] = "PROVISIONED_VERIFIED_READ_ONLY_BINDINGS"
        registry["production_bindings"] = True
        unsigned = dict(registry)
        unsigned.pop("content_sha256")
        registry["content_sha256"] = canonical_sha256(unsigned)
        with self.assertRaises(FieldApplicationError) as unsealed:
            rectify_surface_candidate("ADI_AI", candidate, binding_registry=registry)
        self.assertEqual(
            unsealed.exception.reason_code,
            "CAFE_POS_PRODUCTION_BINDING_SEAL_NOT_VERIFIED",
        )

    def test_production_binding_seal_request_holds_without_local_founder_root(self) -> None:
        registry = self._production_registry("ODOO_HUMAN")
        request = build_binding_seal_request(registry)
        evaluation = evaluate_binding_seal_request(registry)
        schema = json.loads(
            (ROOT / "schemas/field/w7tp_cafe_pos_binding_seal.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(request)
        Draft202012Validator(schema).validate(evaluation)
        self.assertEqual(request["state"], "NEEDS_FOUNDER_DUAL_ROOT_AUTHORIZATION")
        self.assertEqual(evaluation["decision"], "HOLD")
        self.assertEqual(
            evaluation["reason_code"],
            "HOLD_FOUNDER_ROOT_NOT_PROVISIONED_OR_INVALID",
        )
        self.assertIsNone(evaluation["binding_seal_ref"])
        encoded = json.dumps(evaluation, ensure_ascii=False)
        self.assertNotIn("https://accounts.google.com", encoded)
        self.assertTrue(
            all(isinstance(value, bool) for value in evaluation["identity_gate"]["checks"].values())
        )

    def test_verified_dual_root_seals_read_only_bindings_but_not_formal_order(self) -> None:
        registry = self._production_registry("ADI_AI")
        device_fingerprint = "sha256:" + "7" * 64
        oidc_issuer = "https://accounts.google.com"
        oidc_subject_sha256 = "8" * 64
        root = build_sealed_founder_root(
            device_fingerprint,
            oidc_issuer,
            oidc_subject_sha256,
        )
        identity_request = {
            "device_principal_fingerprint": device_fingerprint,
            "google_oidc_issuer": oidc_issuer,
            "google_oidc_subject_sha256": oidc_subject_sha256,
            "explicit_founder_command": True,
            "founder_command_ref": "founder-command:synthetic-binding-seal-001",
            "d8_decision": "ALLOW",
            "future_identity_adapters": {
                "tw_moi_digital_natural_person_id": "DISABLED_NOT_CONFIGURED",
                "physical_natural_person_certificate_card": "DISABLED_NOT_CONFIGURED",
            },
        }
        evaluation = evaluate_binding_seal_request(
            registry,
            founder_identity_request=identity_request,
            sealed_founder_root=root,
        )
        self.assertEqual(evaluation["decision"], "ALLOW")
        self.assertTrue(
            evaluation["binding_seal_ref"].startswith(
                "total-field-binding-seal-sha256:"
            )
        )
        product = self.menu["products"][0]
        result = rectify_surface_candidate(
            "ADI_AI",
            self._candidate_for(self.menu, registry, product),
            binding_registry=registry,
            founder_identity_request=identity_request,
            sealed_founder_root=root,
        )
        self.assertEqual(
            result["production_gate"]["binding_readiness"],
            "VERIFIED_READ_ONLY",
        )
        self.assertNotIn(
            "HOLD_ADI_BINDINGS_NOT_PROVISIONED",
            result["production_gate"]["reason_codes"],
        )
        self.assertFalse(result["production_gate"]["formal_pos_order"])
        self.assertFalse(result["D8"]["formal_execution_authority"])
        schema = json.loads(
            (ROOT / "schemas/field/w7tp_cafe_pos_interop_candidate.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator(schema).validate(result)

    def test_cli_emits_seal_request_without_accepting_identity_material(self) -> None:
        registry = self._production_registry("ODOO_HUMAN")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "production-bindings.json"
            path.write_text(
                json.dumps(registry, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            with patch("builtins.print") as output:
                code = suite_main(
                    [
                        "cafe-pos-binding-seal-request",
                        "--bindings",
                        str(path),
                    ]
                )
        self.assertEqual(code, 0)
        result = json.loads(output.call_args.args[0])
        self.assertEqual(result["state"], "NEEDS_FOUNDER_DUAL_ROOT_AUTHORIZATION")
        encoded = json.dumps(result, ensure_ascii=False)
        for forbidden in ("password", "token", "credential", "google_oidc_subject_sha256"):
            self.assertNotIn(forbidden, encoded.casefold())

    def test_generated_candidate_validates_schema_and_has_no_side_effects(self) -> None:
        product = self.menu["products"][0]
        result = rectify_surface_candidate(
            "ADI_AI",
            self._surface_candidate("ADI_AI", product),
            binding_registry=self.registries["ADI_AI"],
        )
        schema_path = ROOT / "schemas/field/w7tp_cafe_pos_interop_candidate.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(result)
        self.assertEqual(result["production_gate"]["state"], "HOLD")
        self.assertIn(
            "HOLD_ADI_BINDINGS_NOT_PROVISIONED",
            result["production_gate"]["reason_codes"],
        )
        self.assertTrue(all(value is False for value in result["side_effects"].values()))
        self.assertEqual(
            result["semantic_content_sha256"],
            canonical_sha256(result["semantic_candidate"]),
        )


if __name__ == "__main__":
    unittest.main()
