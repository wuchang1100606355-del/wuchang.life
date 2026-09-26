#!/usr/bin/env python3

from __future__ import annotations

import json
import unittest

from tools.total_field.w7tp_all_node_audio_topology import (
    DEPRECATED_MSI_WSL_TAILSCALE_IP,
    EXPECTED_NODES,
    WINDOWS_AUDIO_ROLES,
    load_audio_topology,
    resolve_audio_target,
)


class AllNodeAudioTopologyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.topology = load_audio_topology()
        cls.nodes = {
            item["node_ref"]: item
            for item in cls.topology["nodes"]
        }

    def test_exact_node_coverage(self) -> None:
        self.assertEqual(set(self.nodes), EXPECTED_NODES)

    def test_msi_windows_roles_are_single_endpoint_per_direction(self) -> None:
        msi = self.nodes["MSI"]
        self.assertEqual(set(msi["render"]["roles"]), WINDOWS_AUDIO_ROLES)
        self.assertEqual(set(msi["capture"]["roles"]), WINDOWS_AUDIO_ROLES)
        self.assertIn("7934958d", msi["render"]["endpoint_id"])
        self.assertIn("062ac6b4", msi["capture"]["endpoint_id"])

    def test_taiji03_windows_roles_are_single_endpoint_per_direction(self) -> None:
        node = self.nodes["taiji03"]
        self.assertEqual(set(node["render"]["roles"]), WINDOWS_AUDIO_ROLES)
        self.assertEqual(set(node["capture"]["roles"]), WINDOWS_AUDIO_ROLES)
        self.assertIn("8d745c20", node["render"]["endpoint_id"])
        self.assertIn("bd1c9ba8", node["capture"]["endpoint_id"])

    def test_office_hom_epod_routes_only_through_taiji01(self) -> None:
        result = resolve_audio_target("office")
        self.assertEqual(result["state"], "PASS_AUDIO_TARGET")
        self.assertEqual(result["bridge_node_ref"], "taiji01")
        self.assertTrue(result["requires_total_field_allow"])
        self.assertEqual(
            result["target"]["device_ref"],
            "HOME_POD_LAN_AUDIO_NODE_OFFICE_01",
        )
        self.assertEqual(result["target"]["host"], "192.168.50.101")
        self.assertEqual(result["target"]["port"], 7000)

    def test_msi_apple_music_is_local_only_for_default_playback(self) -> None:
        policy = self.nodes["MSI"]["application_audio_policy"]
        self.assertTrue(policy["apple_music_local_computer"])
        self.assertFalse(policy["apple_music_office_airplay_direct"])
        self.assertTrue(policy["office_network_playback_via_taiji01_only"])

    def test_unverified_android_audio_nodes_are_held(self) -> None:
        for target in ("TAIJI04", "DRALLION"):
            result = resolve_audio_target(target)
            self.assertTrue(result["state"].startswith("HOLD_"))
            self.assertFalse(result["selectable"])

    def test_compute_nodes_cannot_be_selected_as_user_audio(self) -> None:
        for target in ("PENGUIN", "US_VM"):
            result = resolve_audio_target(target)
            self.assertEqual(result["state"], "BLOCK_NO_USER_AUDIO_ROLE")
            self.assertFalse(result["selectable"])

    def test_deprecated_msi_wsl_tailscale_is_absent(self) -> None:
        encoded = json.dumps(self.topology, ensure_ascii=False)
        self.assertNotIn(DEPRECATED_MSI_WSL_TAILSCALE_IP, encoded)

    def test_taiji01_is_broker_not_user_audio_endpoint(self) -> None:
        node = self.nodes["taiji01"]
        self.assertEqual(node["role"], "TOTAL_FIELD_AUDIO_BROKER")
        self.assertFalse(node["user_audio_endpoint"])
        self.assertFalse(node["local_audio_authoritative"])


if __name__ == "__main__":
    unittest.main()
