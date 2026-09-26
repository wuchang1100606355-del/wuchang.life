#!/usr/bin/env python3
"""Tests for MSI local-LLM LAN-first endpoint routing."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from core import msi_local_llm_route as route


class MSILocalLLMRouteTest(unittest.TestCase):
    def test_lan_is_selected_first_when_available(self):
        with patch.object(
            route,
            "endpoint_has_model",
            side_effect=lambda url, model, timeout=2.0: (
                url == route.MSI_LAN_OLLAMA_URL
            ),
        ):
            result = route.resolve_msi_ollama_url("model:test")
        self.assertEqual(result["state"], "PASS_MSI_LOCAL_LLM_ROUTE")
        self.assertEqual(result["selected_url"], route.MSI_LAN_OLLAMA_URL)
        self.assertEqual(result["selected_transport"], "LAN")
        self.assertTrue(result["lan_first"])

    def test_windows_tailscale_is_fallback_after_lan_failure(self):
        with patch.object(
            route,
            "endpoint_has_model",
            side_effect=lambda url, model, timeout=2.0: (
                url == route.MSI_WINDOWS_TAILSCALE_OLLAMA_URL
            ),
        ):
            result = route.resolve_msi_ollama_url("model:test")
        self.assertEqual(
            result["selected_url"],
            route.MSI_WINDOWS_TAILSCALE_OLLAMA_URL,
        )
        self.assertEqual(result["selected_transport"], "TAILSCALE_WINDOWS")
        self.assertEqual(
            [item["transport"] for item in result["attempts"]],
            ["LAN", "TAILSCALE_WINDOWS"],
        )


    def test_deprecated_wsl_tailscale_override_is_never_admitted(self):
        candidates = route.endpoint_candidates(
            route.DEPRECATED_MSI_WSL_TAILSCALE_OLLAMA_URL
        )
        urls = [item["url"] for item in candidates]
        self.assertNotIn(
            route.DEPRECATED_MSI_WSL_TAILSCALE_OLLAMA_URL,
            urls,
        )
        self.assertEqual(
            urls,
            [
                route.MSI_LAN_OLLAMA_URL,
                route.MSI_WINDOWS_TAILSCALE_OLLAMA_URL,
            ],
        )

    def test_unknown_operator_override_is_only_last_fallback(self):
        candidates = route.endpoint_candidates("http://10.0.0.9:11434")
        self.assertEqual(candidates[0]["transport"], "LAN")
        self.assertEqual(candidates[1]["transport"], "TAILSCALE_WINDOWS")
        self.assertEqual(candidates[2]["transport"], "OPERATOR_OVERRIDE")

    def test_no_live_endpoint_returns_hold_without_deprecated_selection(self):
        with patch.object(route, "endpoint_has_model", return_value=False):
            result = route.resolve_msi_ollama_url(
                "model:test",
                override_url=route.DEPRECATED_MSI_WSL_TAILSCALE_OLLAMA_URL,
            )
        self.assertEqual(result["state"], "HOLD_MSI_LOCAL_LLM_UNREACHABLE")
        self.assertIsNone(result["selected_url"])
        self.assertFalse(result["deprecated_wsl_tailscale_selected"])


if __name__ == "__main__":
    unittest.main()
