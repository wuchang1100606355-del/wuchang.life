#!/usr/bin/env python3
"""Tests for T-011C Chrome/Codex interface candidate projection."""

from __future__ import annotations

import copy
import hashlib
import unittest
from pathlib import Path

from tools.total_field.t011c_interface_candidate_adapter import (
    T011CInterfaceHold,
    build_t011c_interface_candidate,
)


def candidate_packet() -> dict:
    text = '{"candidate_summary":"safe local candidate","next_interface":"total-field-verifier","risk_flags":[]}'
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "schema_version": "w7tp.local-llm-candidate-return.v1",
        "state": "CANDIDATE_READY",
        "task_ref": "task:T-011B",
        "intent_ref": "intent_ref:t011c:test",
        "provider_ref": "MSI_OLLAMA_LOCAL",
        "model_ref": "taiji-qwen2.5-coder-7b:ctx16k",
        "context_ref": "t011bctx:sha256:abc",
        "context_sha256": "a" * 64,
        "candidate_ref": "candidate:sha256:" + digest,
        "candidate_sha256": digest,
        "candidate_text": text,
        "candidate_only": True,
        "must_not_execute": True,
        "requires_total_field_verify": True,
        "member_plaintext_transferred": False,
        "secret_transferred": False,
        "raw_browser_page_transferred": False,
        "authority": {
            "provider_authority": False,
            "model_authority": False,
            "codex_authority": False,
            "browser_authority": False,
            "formal_effect_boundary": "TAIJI01_TOTAL_FIELD",
        },
        "d4_evidence": {
            "model_selection_sha256": "b" * 64,
            "dynamic_context_ref": "context:test:dynamic",
            "member_context_ref": "memberctx:test:member",
            "model_response_sha256": "c" * 64,
            "endpoint_ref": "MSI_WINDOWS_TAILSCALE_FALLBACK",
            "endpoint_transport": "TAILSCALE_WINDOWS",
        },
        "d7_risk": {
            "risk_flags": [],
            "output_scan_pass": True,
            "hold_reason": None,
        },
        "return_coordinate": "total-field:candidate-gateway:llm-push",
    }


def total_field_receipt(packet: dict) -> dict:
    return {
        "state": "PASS_T011B_TOTAL_FIELD_CANDIDATE_RETURN",
        "candidate_sha256": packet["candidate_sha256"],
        "candidate_text_submitted_to_total_field": False,
        "candidate_execution_allowed": False,
        "final_decision": "ALLOW",
        "fixed_point_status": "REACHED",
        "commit_applied": True,
        "decision_reason_codes": ["FIXED_POINT_REACHED"],
        "state_ref": "tfs-state:candidate:v0.1:test",
        "tfid": "tfid:candidate:v0.1:test",
        "total_field_hash": "d" * 64,
        "formal_effect_boundary": "TAIJI01_TOTAL_FIELD",
    }


ROOT = Path(__file__).resolve().parents[1]


class T011CInterfaceCandidateAdapterTest(unittest.TestCase):
    def test_builds_display_only_chrome_and_noninvoked_codex_candidate(self):
        packet = candidate_packet()
        result = build_t011c_interface_candidate(
            t011b_candidate_return=packet,
            total_field_return_receipt=total_field_receipt(packet),
            allowed_files=["tools/example.py"],
        )
        self.assertEqual(result["state"], "PASS_T011C_INTERFACE_CANDIDATE")
        self.assertTrue(result["candidate_only"])
        self.assertFalse(result["runtime_effect"])
        self.assertFalse(result["codex_invocation_performed"])
        view = result["chrome_view"]
        self.assertTrue(view["display_only"])
        self.assertFalse(view["execution_allowed"])
        self.assertEqual(view["candidate_text"], packet["candidate_text"])
        codex = result["codex_task_packet_candidate"]
        self.assertEqual(codex["packet_type"], "W7TP_CODEX_TASK_PACKET")
        self.assertFalse(codex["codex_authority"])
        self.assertTrue(codex["candidate_only"])
        self.assertFalse(codex["safety_flags"]["AUTO_STAGE"])
        self.assertFalse(codex["safety_flags"]["AUTO_COMMIT"])
        self.assertFalse(codex["safety_flags"]["DEPLOY"])
        self.assertFalse(codex["safety_flags"]["SERVICE_RESTART"])
        self.assertEqual(codex["allowed_files"], ["tools/example.py"])

    def test_candidate_hash_tamper_holds(self):
        packet = candidate_packet()
        receipt = total_field_receipt(packet)
        packet["candidate_text"] = "tampered"
        with self.assertRaisesRegex(
            T011CInterfaceHold,
            "HOLD_T011C_CANDIDATE_HASH_MISMATCH",
        ):
            build_t011c_interface_candidate(
                t011b_candidate_return=packet,
                total_field_return_receipt=receipt,
                allowed_files=["tools/example.py"],
            )

    def test_total_field_receipt_must_match_candidate(self):
        packet = candidate_packet()
        receipt = total_field_receipt(packet)
        receipt["candidate_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            T011CInterfaceHold,
            "HOLD_T011C_TOTAL_FIELD_RECEIPT_INVALID",
        ):
            build_t011c_interface_candidate(
                t011b_candidate_return=packet,
                total_field_return_receipt=receipt,
                allowed_files=["tools/example.py"],
            )

    def test_path_escape_is_rejected(self):
        packet = candidate_packet()
        with self.assertRaisesRegex(
            T011CInterfaceHold,
            "HOLD_T011C_ALLOWED_FILE_INVALID",
        ):
            build_t011c_interface_candidate(
                t011b_candidate_return=packet,
                total_field_return_receipt=total_field_receipt(packet),
                allowed_files=["../escape.py"],
            )

    def test_chrome_sidepanel_poc_is_packaged_and_display_only(self):
        extension = ROOT / "web/xiaoj_member_browser_extension"
        html = (extension / "sidepanel.html").read_text(encoding="utf-8")
        js = (extension / "sidepanel.js").read_text(encoding="utf-8")
        package = (
            ROOT / "tools/member_browser/package_xiaoj_member_browser_release.py"
        ).read_text(encoding="utf-8")
        self.assertIn('src="t011c_candidate_view.js"', html)
        self.assertIn('id="t011cCandidateJson"', html)
        self.assertIn('id="loadT011cBtn"', html)
        self.assertIn("loadT011CCandidateView", js)
        self.assertIn(
            "web/xiaoj_member_browser_extension/t011c_candidate_view.js",
            package,
        )
        self.assertNotIn("XIAOJ_T011C_EXECUTE", js)


if __name__ == "__main__":
    unittest.main()
