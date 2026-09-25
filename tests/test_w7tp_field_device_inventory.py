#!/usr/bin/env python3
"""Focused tests for the SUNMI/HomePad candidate inventory verifier."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts/verify/verify_w7tp_field_device_inventory.py"
SPEC = importlib.util.spec_from_file_location("verify_w7tp_field_device_inventory", VERIFIER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("VERIFIER_IMPORT_FAILED")
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


class W7TPFieldDeviceInventoryTests(unittest.TestCase):
    """Exercise the fourteen explicit inventory and container gates."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = verifier.load_json(ROOT / verifier.INVENTORY)
        cls.capability = verifier.load_json(ROOT / verifier.CAPABILITY)
        cls.container = verifier.load_json(ROOT / verifier.CONTAINER)
        cls.voice = verifier.load_json(ROOT / verifier.VOICE)

    def assert_reason(self, reason: str, callable_, *args) -> None:
        with self.assertRaises(verifier.VerificationFailure) as caught:
            callable_(*args)
        self.assertEqual(caught.exception.reason_code, reason)

    def test_01_current_candidate_artifacts_pass(self) -> None:
        verifier.verify(ROOT)

    def test_02_taiji01_cannot_be_target(self) -> None:
        inventory = copy.deepcopy(self.inventory)
        inventory["target_roles"].append("taiji01")
        self.assert_reason("TARGET_ROLES_INVALID", verifier.validate_inventory, inventory, ROOT)

    def test_03_sunmi_requires_direct_evidence_or_hold(self) -> None:
        inventory = copy.deepcopy(self.inventory)
        sunmi = next(item for item in inventory["devices"] if item["device_role"] == "SUNMI_POS")
        sunmi["manufacturer"] = None
        sunmi["identity_method"] = "NO_DIRECT_DEVICE_BINDING"
        sunmi["hold_reason"] = None
        sunmi["deployment_eligibility"] = True
        self.assert_reason(
            "SUNMI_DIRECT_EVIDENCE_OR_HOLD_REQUIRED",
            verifier.validate_inventory,
            inventory,
            ROOT,
        )

    def test_04_homepads_are_two_distinct_records(self) -> None:
        inventory = copy.deepcopy(self.inventory)
        inventory["devices"] = [
            item for item in inventory["devices"] if item["device_role"] != "HOME_PAD_2"
        ]
        self.assert_reason("DEVICE_CARDINALITY_INVALID", verifier.validate_inventory, inventory, ROOT)

    def test_05_hostname_only_identity_is_forbidden(self) -> None:
        inventory = copy.deepcopy(self.inventory)
        inventory["devices"][0]["identity_method"] = "HOSTNAME_ONLY"
        self.assert_reason("HOSTNAME_IDENTITY_GUESS_FORBIDDEN", verifier.validate_inventory, inventory, ROOT)

    def test_06_raw_secret_field_is_rejected(self) -> None:
        voice = copy.deepcopy(self.voice)
        voice["api_key"] = "fixture-redacted"
        self.assert_reason(
            "RAW_SECRET_DETECTED",
            verifier.validate_profiles,
            self.capability,
            self.container,
            voice,
        )

    def test_07_voice_license_must_be_opaque(self) -> None:
        voice = copy.deepcopy(self.voice)
        voice["voice_license_ref"] = "inline-value"
        self.assert_reason(
            "VOICE_LICENSE_PROFILE_INVALID",
            verifier.validate_profiles,
            self.capability,
            self.container,
            voice,
        )

    def test_08_container_cannot_embed_credentials(self) -> None:
        container = copy.deepcopy(self.container)
        container["credential_embedded"] = True
        self.assert_reason(
            "CONTAINER_SECURITY_PROFILE_INVALID",
            verifier.validate_profiles,
            self.capability,
            container,
            self.voice,
        )

    def test_09_container_must_be_non_root(self) -> None:
        container = copy.deepcopy(self.container)
        container["non_root_required"] = False
        self.assert_reason(
            "CONTAINER_SECURITY_PROFILE_INVALID",
            verifier.validate_profiles,
            self.capability,
            container,
            self.voice,
        )

    def test_10_voice_candidate_cannot_direct_commit(self) -> None:
        capability = copy.deepcopy(self.capability)
        capability["direct_commit"] = True
        self.assert_reason(
            "CAPABILITY_CANDIDATE_GATE_INVALID",
            verifier.validate_profiles,
            capability,
            self.container,
            self.voice,
        )

    def test_11_every_address_requires_evidence_ref(self) -> None:
        inventory = copy.deepcopy(self.inventory)
        sunmi = next(item for item in inventory["devices"] if item["device_role"] == "SUNMI_POS")
        sunmi["address_evidence_refs"] = {}
        self.assert_reason("ADDRESS_EVIDENCE_REF_MISSING", verifier.validate_inventory, inventory, ROOT)

    def test_12_offline_device_cannot_be_ready(self) -> None:
        inventory = copy.deepcopy(self.inventory)
        inventory["unresolved_devices"][0]["deployment_eligibility"] = True
        self.assert_reason("OFFLINE_DEVICE_READY_FOR_DEPLOYMENT", verifier.validate_inventory, inventory, ROOT)

    def test_13_owner_maps_v3_to_sunmi_android_13(self) -> None:
        inventory = copy.deepcopy(self.inventory)
        sunmi = next(item for item in inventory["devices"] if item["device_role"] == "SUNMI_POS")
        sunmi["node_id"] = "drallion"
        self.assert_reason("SUNMI_OWNER_MAPPING_INVALID", verifier.validate_inventory, inventory, ROOT)

    def test_14_drallion_chromeos_is_never_sunmi(self) -> None:
        inventory = copy.deepcopy(self.inventory)
        drallion = next(
            item
            for item in inventory["unresolved_devices"]
            if item.get("tailscale_machine_name") == "drallion"
        )
        drallion["candidate_roles"].append("SUNMI_POS")
        self.assert_reason(
            "DRALLION_CHROMEOS_BOUNDARY_INVALID",
            verifier.validate_inventory,
            inventory,
            ROOT,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
