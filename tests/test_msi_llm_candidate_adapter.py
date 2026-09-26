#!/usr/bin/env python3
"""Tests for T-011B MSI local-LLM candidate adapter."""

from __future__ import annotations

import copy
import json
import unittest

from tools.total_field.msi_llm_candidate_adapter import (
    MSILLMCandidateHold,
    adjudicate_msi_candidate_return,
    combine_model_visible_contexts,
    load_model_selection_contract,
    run_msi_llm_candidate,
    select_msi_llm_model,
)
from tools.total_field_dynamic_context_pull import (
    RESULT_SCHEMA,
    canonical_sha256 as dynamic_sha256,
    validate_model_visible_context,
)


def resource_decision() -> dict:
    return {
        "QUALIFIED_SET": ["MSI_OLLAMA_LOCAL"],
        "PREFERRED_SET": ["MSI_OLLAMA_LOCAL"],
        "RESOURCE_COORDINATES": [
            {
                "RESOURCE_ID": "MSI_OLLAMA_LOCAL",
                "CURRENT_STATE": "AVAILABLE",
                "CAPABILITY_SET": [
                    "LANGUAGE",
                    "INTENT",
                    "CODE",
                    "TOOLS",
                    "LOCAL_REVIEW",
                ],
                "AUTHORITY_CLASS": "CANDIDATE_ONLY_NOT_D8",
            }
        ],
    }


def dynamic_result() -> dict:
    context = {
        "context_ref": "context:test:t011b:dynamic",
        "state_projection": {
            "task_state": "READY",
            "work_ref": "work_ref:t011b",
        },
        "evidence_refs": ["evidence:test:t011b:dynamic"],
        "capability_refs": ["capability:test:dynamic-context"],
        "acceptance_conditions": ["condition:test:dynamic-context-valid"],
        "schema_refs": ["schema:test:dynamic-context:v1"],
        "interface_refs": ["interface:total-field-dynamic-context-pull:v1"],
        "non_core_rule_capsule_refs": [],
    }
    result = {
        "schema_version": RESULT_SCHEMA,
        "task_ref": "task:T-011B",
        "model_visible_context": validate_model_visible_context(context),
        "persistence_policy": {
            "dynamic_context_persistence_allowed": False,
            "full_state_persistence_allowed": False,
            "personal_plaintext_persistence_allowed": False,
            "credential_persistence_allowed": False,
        },
        "authority": {
            "provider_authority": False,
            "model_authority": False,
            "candidate_only": True,
            "formal_effect_authority": "LOCAL_TOTAL_FIELD",
        },
        "return_coordinate": "total-field:candidate-gateway:llm-push",
        "pull_result_sha256": "",
    }
    basis = copy.deepcopy(result)
    basis.pop("pull_result_sha256")
    result["pull_result_sha256"] = dynamic_sha256(basis)
    return result


def member_context() -> dict:
    member_projection = {
        "member_coordinate": {
            "natural_person_ref": "member_ref:sha256:aaa",
            "identity_root_ref": "identity_root_ref:sha256:bbb",
            "organization_ref": "organization_ref:sha256:ccc",
            "seat_ref": "seat_ref:sha256:ddd",
            "role_ref": "role_ref:sha256:eee",
            "session_ref": "session_ref:sha256:fff",
            "scene_ref": "scene_ref:sha256:111",
        },
        "request_authorization_separation": {
            "organization_request_ref": "organization_request_ref:sha256:222",
            "organization_request_is_member_authorization": False,
            "member_authorization_ref": "member_consent_receipt_ref:sha256:333",
            "member_authorization_state": "CONSENT_VERIFIED",
            "member_authorization_authority": "member",
            "legal_basis_ref": None,
            "legal_basis_verification_ref": None,
            "authority_basis_mode": "MEMBER_CONSENT",
        },
        "task_scope": {
            "purpose_ref": "purpose_ref:sha256:444",
            "scope_refs": ["scope_ref:sha256:555"],
            "effect_class": "REVERSIBLE_ENGINEERING",
            "issued_at_epoch": 100,
            "expires_at_epoch": 200,
        },
        "data_boundary": {
            "model_visible_member_data": "OPAQUE_REFERENCES_ONLY",
            "plaintext_policy": "LOCAL_ONLY_NEVER_MODEL_VISIBLE",
            "reconstruction_policy": "NO_AUTOMATIC_PLAINTEXT_RECONSTRUCTION",
            "odoo_role": "PROCESS_AND_MASKED_PROJECTION_NOT_SOVEREIGN_ROOT",
            "dynamic_context_persistence": "REFERENCES_ONLY",
        },
        "capability_boundary": {
            "allowed_capability_refs": ["capability_ref:sha256:666"],
            "forbidden_capability_classes": ["PLAINTEXT_DISCLOSURE"],
        },
        "risk_state": "PASS",
        "authority_route": {
            "member_gate_ref": "member_gate_ref:sha256:777",
            "member_authorization_ref": "member_consent_receipt_ref:sha256:333",
            "total_field_receipt_ref": "total_field_receipt_ref:sha256:888",
            "nonce_consumption_evidence_ref": "nonce_evidence_ref:sha256:999",
            "candidate_authority": "NONE",
            "provider_authority": "NONE",
            "model_authority": "NONE",
            "formal_effect_route": "EXISTING_TAIJI01_TOTAL_FIELD",
        },
        "source_context_sha256": "a" * 64,
    }
    context = {
        "context_ref": "memberctx:test:t011b",
        "state_projection": {
            "member_sovereign_context": member_projection,
        },
        "evidence_refs": ["evidence:test:t011b:member"],
        "capability_refs": ["capability_ref:sha256:666"],
        "acceptance_conditions": [
            "condition:member-context:opaque-references-only",
            "condition:member-context:no-runtime-effect",
        ],
        "schema_refs": ["schema:w7tp-member-sovereign-context:v1"],
        "interface_refs": ["interface:member-sovereign-context:v1"],
        "non_core_rule_capsule_refs": [],
    }
    return validate_model_visible_context(context)


class MSILLMCandidateAdapterTest(unittest.TestCase):
    def test_model_selection_contract_is_fail_closed_and_candidate_only(self):
        contract = load_model_selection_contract()
        self.assertEqual(contract["task_coordinate"], "T-011B")
        self.assertEqual(contract["provider_ref"], "MSI_OLLAMA_LOCAL")
        self.assertFalse(contract["authority_boundary"]["provider_authority"])
        self.assertFalse(contract["authority_boundary"]["runtime_effect"])
        self.assertFalse(contract["data_boundary"]["member_plaintext_to_model"])
        self.assertFalse(contract["selection_policy"]["preferred_provider_required"])
        self.assertEqual(
            [item["url"] for item in contract["endpoint_candidates"]],
            [
                "http://192.168.50.82:11434",
                "http://100.105.82.28:11434",
            ],
        )
        self.assertEqual(
            [item["transport"] for item in contract["endpoint_candidates"]],
            ["LAN", "TAILSCALE_WINDOWS"],
        )

    def test_combines_dynamic_and_member_context_without_plaintext(self):
        combined = combine_model_visible_contexts(
            dynamic_result(),
            member_context(),
        )
        self.assertEqual(validate_model_visible_context(combined), combined)
        self.assertIn("dynamic_context_projection", combined["state_projection"])
        self.assertIn("member_sovereign_context", combined["state_projection"])
        encoded = json.dumps(combined, ensure_ascii=False).lower()
        self.assertNotIn("member_plaintext", encoded)
        self.assertNotIn("private_key", encoded)
        self.assertNotIn("bearer ", encoded)

    def test_selects_only_current_msi_local_model_candidate(self):
        combined = combine_model_visible_contexts(dynamic_result(), member_context())
        selection = select_msi_llm_model(
            resource_decision=resource_decision(),
            combined_context=combined,
            task_ref="task:T-011B",
            intent_ref="intent_ref:sha256:t011b",
        )
        self.assertEqual(selection["provider_ref"], "MSI_OLLAMA_LOCAL")
        self.assertEqual(selection["model_ref"], "taiji-qwen2.5-coder-7b:ctx16k")
        self.assertTrue(selection["candidate_only"])
        self.assertFalse(selection["runtime_effect"])
        self.assertFalse(selection["provider_authority"])


    def test_global_preference_does_not_override_explicit_t011b_msi_binding(self):
        decision = resource_decision()
        decision["PREFERRED_SET"] = ["GEMINI_CODE_ASSIST"]
        combined = combine_model_visible_contexts(dynamic_result(), member_context())
        selection = select_msi_llm_model(
            resource_decision=decision,
            combined_context=combined,
            task_ref="task:T-011B",
            intent_ref="intent_ref:sha256:t011b",
        )
        self.assertEqual(selection["provider_ref"], "MSI_OLLAMA_LOCAL")
        self.assertFalse(selection["preferred_provider_observed"])

    def test_dynamic_context_authority_drift_holds(self):
        bad = dynamic_result()
        bad["authority"]["model_authority"] = True
        basis = copy.deepcopy(bad)
        basis.pop("pull_result_sha256")
        bad["pull_result_sha256"] = dynamic_sha256(basis)
        with self.assertRaisesRegex(
            MSILLMCandidateHold,
            "HOLD_T011B_DYNAMIC_CONTEXT_AUTHORITY_DRIFT",
        ):
            combine_model_visible_contexts(bad, member_context())

    def test_member_plaintext_boundary_drift_holds(self):
        bad = member_context()
        bad["state_projection"]["member_sovereign_context"]["data_boundary"][
            "model_visible_member_data"
        ] = "PLAINTEXT"
        with self.assertRaisesRegex(
            MSILLMCandidateHold,
            "HOLD_T011B_MEMBER_DATA_BOUNDARY_DRIFT",
        ):
            combine_model_visible_contexts(dynamic_result(), bad)


    def test_candidate_return_from_fake_model_is_non_executable(self):
        captured = {}

        def fake_transport(url, model, messages, timeout):
            captured["url"] = url
            captured["model"] = model
            captured["messages"] = messages
            return {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "candidate_summary": "reference-only candidate",
                            "next_interface": "total-field-verifier",
                            "risk_flags": [],
                        }
                    ),
                },
                "done": True,
            }

        result = run_msi_llm_candidate(
            dynamic_context_pull_result=dynamic_result(),
            member_model_visible_context=member_context(),
            resource_decision=resource_decision(),
            task_ref="task:T-011B",
            intent_ref="intent_ref:sha256:t011b",
            transport=fake_transport,
        )
        self.assertEqual(result["state"], "CANDIDATE_READY")
        self.assertTrue(result["candidate_only"])
        self.assertTrue(result["must_not_execute"])
        self.assertTrue(result["requires_total_field_verify"])
        self.assertFalse(result["member_plaintext_transferred"])
        self.assertFalse(result["authority"]["model_authority"])
        self.assertEqual(captured["model"], "taiji-qwen2.5-coder-7b:ctx16k")
        self.assertEqual(captured["url"], "http://192.168.50.82:11434")
        self.assertEqual(result["d4_evidence"]["endpoint_ref"], "MSI_LAN_PRIMARY")
        self.assertEqual(result["d4_evidence"]["endpoint_transport"], "LAN")
        prompt = json.dumps(captured["messages"], ensure_ascii=False).lower()
        self.assertNotIn("member_plaintext", prompt)
        self.assertNotIn("private_key", prompt)

    def test_candidate_return_routes_through_existing_total_field(self):
        def fake_transport(url, model, messages, timeout):
            return {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "candidate_summary": "candidate for review",
                            "next_interface": "total-field-verifier",
                            "risk_flags": [],
                        }
                    ),
                },
                "done": True,
            }

        packet = run_msi_llm_candidate(
            dynamic_context_pull_result=dynamic_result(),
            member_model_visible_context=member_context(),
            resource_decision=resource_decision(),
            task_ref="task:T-011B",
            intent_ref="intent_ref:sha256:t011b",
            transport=fake_transport,
        )
        receipt = adjudicate_msi_candidate_return(packet)
        self.assertEqual(
            receipt["state"],
            "PASS_T011B_TOTAL_FIELD_CANDIDATE_RETURN",
        )
        self.assertEqual(receipt["final_decision"], "ALLOW")
        self.assertEqual(receipt["fixed_point_status"], "REACHED")
        self.assertFalse(receipt["candidate_text_submitted_to_total_field"])
        self.assertFalse(receipt["candidate_execution_allowed"])
        self.assertEqual(
            receipt["formal_effect_boundary"],
            "TAIJI01_TOTAL_FIELD",
        )

    def test_hold_candidate_is_not_submitted_to_total_field(self):
        def fake_transport(url, model, messages, timeout):
            return {
                "message": {
                    "role": "assistant",
                    "content": "contact test@example.com",
                },
                "done": True,
            }

        packet = run_msi_llm_candidate(
            dynamic_context_pull_result=dynamic_result(),
            member_model_visible_context=member_context(),
            resource_decision=resource_decision(),
            task_ref="task:T-011B",
            intent_ref="intent_ref:sha256:t011b",
            transport=fake_transport,
        )
        self.assertEqual(packet["state"], "HOLD")
        with self.assertRaisesRegex(
            MSILLMCandidateHold,
            "HOLD_T011B_CANDIDATE_NOT_READY",
        ):
            adjudicate_msi_candidate_return(packet)


    def test_sensitive_model_output_becomes_hold_without_retaining_text(self):
        def fake_transport(url, model, messages, timeout):
            return {
                "message": {
                    "role": "assistant",
                    "content": "contact test@example.com",
                },
                "done": True,
            }

        result = run_msi_llm_candidate(
            dynamic_context_pull_result=dynamic_result(),
            member_model_visible_context=member_context(),
            resource_decision=resource_decision(),
            task_ref="task:T-011B",
            intent_ref="intent_ref:sha256:t011b",
            transport=fake_transport,
        )
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["candidate_text"], "")
        self.assertFalse(result["d7_risk"]["output_scan_pass"])
        self.assertIn("EMAIL_LITERAL", result["d7_risk"]["risk_flags"])

    def test_model_tool_call_is_forbidden(self):
        def fake_transport(url, model, messages, timeout):
            return {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{"function": {"name": "write_file"}}],
                }
            }

        with self.assertRaisesRegex(
            MSILLMCandidateHold,
            "HOLD_T011B_MODEL_TOOL_CALL_FORBIDDEN",
        ):
            run_msi_llm_candidate(
                dynamic_context_pull_result=dynamic_result(),
                member_model_visible_context=member_context(),
                resource_decision=resource_decision(),
                task_ref="task:T-011B",
                intent_ref="intent_ref:sha256:t011b",
                transport=fake_transport,
            )


if __name__ == "__main__":
    unittest.main()
