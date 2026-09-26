#!/usr/bin/env python3
"""Tests for the T-005 capability internalization overlay."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.capability_internalization import (
    CapabilityInternalizationError,
    REQUIRED_CLASSES,
    load_internalization_registry,
    select_internalized_capabilities,
)


class CapabilityInternalizationTest(unittest.TestCase):
    def test_registry_covers_required_capability_classes(self) -> None:
        registry = load_internalization_registry()
        classes = {
            item["capability_class"]
            for item in registry["capabilities"]
        }
        self.assertEqual(classes, REQUIRED_CLASSES)
        self.assertFalse(registry["canonical"])
        self.assertEqual(
            registry["registry_role"],
            "OVERLAY_ONLY_DOES_NOT_REPLACE_EXISTING_OWNERS",
        )

    def test_provider_authority_wall_is_global_and_per_capability(self) -> None:
        registry = load_internalization_registry()
        boundary = registry["authority_boundary"]
        self.assertFalse(boundary["provider_authority"])
        self.assertFalse(boundary["external_authority_inherited"])
        self.assertTrue(boundary["total_field_verify_required"])
        self.assertEqual(boundary["formal_effect_boundary"], "TAIJI01_TOTAL_FIELD")
        for item in registry["capabilities"]:
            d8 = item["d8_authority"]
            self.assertFalse(d8["provider_authority"])
            self.assertFalse(d8["final_decision"])
            self.assertFalse(d8["canonical"])
            self.assertTrue(d8["requires_total_field_verify"])
            self.assertTrue(item["d7_risk"]["fail_closed"])

    def test_d3_d5_selects_msi_llm_candidate(self) -> None:
        result = select_internalized_capabilities(
            d3_node="MSI",
            d5_modes=["CANDIDATE_ONLY"],
            required_tags=["CODE"],
        )
        self.assertEqual(
            result["selected_capability_ids"],
            ["CAP_INTERNAL_LLM_V1"],
        )
        self.assertFalse(result["authority_boundary"]["provider_authority"])

    def test_d7_forbidden_risk_excludes_provider_black_box(self) -> None:
        result = select_internalized_capabilities(
            d3_node="MSI",
            d5_modes=["CANDIDATE_ONLY"],
            required_tags=["CODE"],
            forbidden_risks=["PROVIDER_BLACK_BOX"],
        )
        self.assertEqual(result["selected_capability_ids"], [])


    def test_dynamic_context_selection_is_pointer_first(self) -> None:
        result = select_internalized_capabilities(
            d3_node="taiji01",
            d5_modes=["CANDIDATE_ONLY"],
            required_tags=["DYNAMIC_CONTEXT"],
        )
        self.assertEqual(
            result["selected_capability_ids"],
            ["CAP_INTERNAL_DYNAMIC_CONTEXT_V1"],
        )
        item = result["selected_capabilities"][0]
        self.assertIn("POINTER_FIRST", item["selection_tags"])
        self.assertFalse(item["d5_execution"]["direct_effect"])

    def test_gst_selection_preserves_bounded_runtime_and_no_d8(self) -> None:
        result = select_internalized_capabilities(
            d3_node="taiji01",
            d5_modes=["BOUNDED_EFFECT"],
            required_tags=["GST_V23"],
        )
        self.assertEqual(
            result["selected_capability_ids"],
            ["CAP_INTERNAL_GST_V23_V1"],
        )
        gst = result["selected_capabilities"][0]
        self.assertEqual(gst["status"], "ACTIVE_RUNTIME")
        self.assertTrue(gst["d5_execution"]["direct_effect"])
        self.assertFalse(gst["d8_authority"]["provider_authority"])

    def test_authority_escalation_in_registry_fails_closed(self) -> None:
        registry = load_internalization_registry()
        registry["capabilities"][0]["d8_authority"]["provider_authority"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(
                json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(CapabilityInternalizationError):
                load_internalization_registry(registry_path=path)

    def test_all_source_refs_resolve_in_current_repo(self) -> None:
        registry = load_internalization_registry()
        self.assertEqual(len(registry["capabilities"]), 7)


if __name__ == "__main__":
    unittest.main()
