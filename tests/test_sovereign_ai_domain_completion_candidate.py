#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thirty focused tests for sovereign multi-domain completion candidates."""

from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.domain_completion_total_field_gateway import (  # noqa: E402
    DomainCompletionTotalFieldGateway,
    GATEWAY_REF,
)
from tools.sovereign_ai_domain_completion_candidate import (  # noqa: E402
    DomainCompletionError,
    InMemoryCompletionProvider,
    build_candidate,
    build_xiaoj_envelope,
    calculate_candidate_hash,
    validate_candidate,
)


MODULE_PATHS = (
    ROOT / "tools/sovereign_ai_domain_completion_candidate.py",
    ROOT / "tools/domain_completion_total_field_gateway.py",
)


class SovereignAIDomainCompletionCandidateTests(unittest.TestCase):
    """Deterministic, source, privacy, adjudication, and side-effect checks."""

    def setUp(self) -> None:
        self.observation_domains = {
            f"observation-domain:{domain.casefold()}:fixture:v0.1": {
                "configured": True,
                "observations": {
                    "observation_ref": f"observation:{domain.casefold()}:fixture:v0.1"
                },
            }
            for domain in ("COMMUNITY", "COMMERCE", "PROPERTY")
        }
        self.gateway = DomainCompletionTotalFieldGateway(
            observation_domains=self.observation_domains
        )

    def _candidate(
        self,
        *,
        domain: str = "COMMUNITY",
        attribute_name: str = "public_description",
        candidate_value: object = "candidate-value",
        source_mode: str = "TOTAL_FIELD_PULL",
        sensitivity: str = "SAFE_DERIVED",
        evidence_refs: list[str] | None = None,
        requires_human_confirmation: bool = False,
        event_suffix: str = "001",
    ) -> dict[str, object]:
        return build_candidate(
            domain=domain,
            entity_ref=f"entity:{domain.casefold()}:fixture:001",
            attribute_name=attribute_name,
            candidate_value=candidate_value,
            source_mode=source_mode,
            model_ref="model:in-memory:fixture:v0.1",
            provider_ref="provider:in-memory:fixture:v0.1",
            event_ref=f"event:domain-completion:{event_suffix}",
            observation_domain_ref=(
                f"observation-domain:{domain.casefold()}:fixture:v0.1"
            ),
            rule_ref="rules/tfct/identity_v0_1",
            evidence_refs=[] if evidence_refs is None else evidence_refs,
            confidence=0.75,
            sensitivity=sensitivity,
            requires_human_confirmation=requires_human_confirmation,
        )

    def _identity_key(self, candidate: dict[str, object]) -> str:
        return "|".join(
            str(candidate[key]) for key in ("domain", "entity_ref", "attribute_name")
        )

    def _receive(
        self, candidate: dict[str, object], previous: object = "previous-value"
    ) -> dict[str, object]:
        return self.gateway.receive_candidate(candidate, previous_value=previous)

    def _provider(self, candidate: dict[str, object]) -> InMemoryCompletionProvider:
        return InMemoryCompletionProvider({"request:fixture:001": [candidate]})

    def _previous_values(
        self, candidate: dict[str, object], previous: object = "previous-value"
    ) -> dict[str, object]:
        return {self._identity_key(candidate): previous}

    def _module_trees(self) -> tuple[ast.AST, ...]:
        return tuple(
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for path in MODULE_PATHS
        )

    def _import_roots(self) -> set[str]:
        names: set[str] = set()
        for tree in self._module_trees():
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.add(node.module.split(".")[0])
        return names

    def test_01_community_candidate_completion(self) -> None:
        result = self._receive(self._candidate(domain="COMMUNITY"))
        self.assertEqual(result["domain"], "COMMUNITY")
        self.assertEqual(result["final_decision"], "ALLOW")

    def test_02_commerce_candidate_completion(self) -> None:
        result = self._receive(self._candidate(domain="COMMERCE"))
        self.assertEqual(result["domain"], "COMMERCE")
        self.assertEqual(result["final_decision"], "ALLOW")

    def test_03_property_candidate_completion(self) -> None:
        result = self._receive(self._candidate(domain="PROPERTY"))
        self.assertEqual(result["domain"], "PROPERTY")
        self.assertEqual(result["final_decision"], "ALLOW")

    def test_04_identical_input_same_candidate_hash(self) -> None:
        self.assertEqual(
            self._candidate()["candidate_hash"], self._candidate()["candidate_hash"]
        )

    def test_05_key_order_does_not_change_hash(self) -> None:
        candidate = self._candidate(candidate_value={"alpha": 1, "beta": {"x": 2}})
        reversed_candidate = {
            key: candidate[key] for key in reversed(tuple(candidate.keys()))
        }
        self.assertEqual(
            calculate_candidate_hash(candidate),
            calculate_candidate_hash(reversed_candidate),
        )
        self.assertEqual(validate_candidate(reversed_candidate).candidate_hash, candidate["candidate_hash"])

    def test_06_total_field_pull_success(self) -> None:
        candidate = self._candidate()
        results = self.gateway.total_field_pull(
            self._provider(candidate),
            "request:fixture:001",
            previous_values=self._previous_values(candidate),
        )
        self.assertEqual(results[0]["source_mode"], "TOTAL_FIELD_PULL")
        self.assertEqual(results[0]["final_decision"], "ALLOW")

    def test_07_llm_push_success(self) -> None:
        candidate = self._candidate()
        results = self.gateway.llm_push(
            self._provider(candidate),
            "request:fixture:001",
            previous_values=self._previous_values(candidate),
        )
        self.assertEqual(results[0]["source_mode"], "LLM_PUSH")
        self.assertEqual(results[0]["final_decision"], "ALLOW")

    def test_08_xiaoj_local_success(self) -> None:
        candidate = self._candidate()
        results = self.gateway.xiaoj_local(
            self._provider(candidate),
            "request:fixture:001",
            persona_text="fixture-persona",
            previous_values=self._previous_values(candidate),
        )
        self.assertEqual(results[0]["source_mode"], "XIAOJ_LOCAL")
        self.assertEqual(results[0]["persona_governance_separation"], "PASS")

    def test_09_all_sources_use_same_total_field_gateway(self) -> None:
        import tools.domain_completion_total_field_gateway as gateway_module

        candidate = self._candidate()
        previous = self._previous_values(candidate)
        original = gateway_module.total_field_receive_candidate
        with patch.object(
            gateway_module, "total_field_receive_candidate", wraps=original
        ) as receiver:
            self.gateway.total_field_pull(
                self._provider(candidate), "request:fixture:001", previous_values=previous
            )
            self.gateway.llm_push(
                self._provider(candidate), "request:fixture:001", previous_values=previous
            )
            self.gateway.xiaoj_local(
                self._provider(candidate),
                "request:fixture:001",
                persona_text="fixture-persona",
                previous_values=previous,
            )
        self.assertEqual(receiver.call_count, 3)

    def test_10_cloud_direct_commit_is_blocked(self) -> None:
        candidate = self._candidate()
        candidate["committed"] = True
        with self.assertRaises(DomainCompletionError) as caught:
            self.gateway.receive_candidate(candidate, previous_value="previous-value")
        self.assertEqual(caught.exception.reason_code, "EXTERNAL_AUTHORITY_CLAIM_BLOCKED")

    def test_11_xiaoj_direct_commit_is_blocked(self) -> None:
        candidate = self._candidate()
        candidate["final_decision"] = "ALLOW"
        with self.assertRaises(DomainCompletionError) as caught:
            build_xiaoj_envelope("fixture-persona", candidate)
        self.assertEqual(caught.exception.reason_code, "EXTERNAL_AUTHORITY_CLAIM_BLOCKED")

    def test_12_member_plaintext_is_held_without_echo(self) -> None:
        secret_fixture = "MEMBER-PLAINTEXT-FIXTURE-DO-NOT-ECHO"
        result = self._receive(
            self._candidate(
                attribute_name="member_plaintext",
                candidate_value=secret_fixture,
                sensitivity="PRIVACY_RESTRICTED",
                requires_human_confirmation=True,
            )
        )
        self.assertIn(result["final_decision"], {"HOLD", "BLOCK"})
        self.assertNotIn(secret_fixture, json.dumps(result, ensure_ascii=False))

    def test_13_raw_token_is_blocked_without_echo(self) -> None:
        secret_fixture = "RAW-TOKEN-FIXTURE-DO-NOT-ECHO"
        result = self._receive(
            self._candidate(
                attribute_name="raw_token",
                candidate_value=secret_fixture,
                sensitivity="PRIVACY_RESTRICTED",
                requires_human_confirmation=True,
            )
        )
        self.assertEqual(result["final_decision"], "BLOCK")
        self.assertFalse(result["commit_applied"])
        self.assertNotIn(secret_fixture, json.dumps(result, ensure_ascii=False))

    def test_14_ownership_requires_owner_confirmation(self) -> None:
        result = self._receive(
            self._candidate(
                attribute_name="ownership",
                sensitivity="OWNER_CONFIRMATION_REQUIRED",
                requires_human_confirmation=True,
            )
        )
        self.assertEqual(result["sensitivity"], "OWNER_CONFIRMATION_REQUIRED")
        self.assertEqual(result["final_decision"], "HOLD")

    def test_15_financial_candidate_requires_review(self) -> None:
        result = self._receive(
            self._candidate(
                attribute_name="financial_amount",
                candidate_value={"amount_status": "candidate-only"},
                sensitivity="FINANCIAL_REVIEW_REQUIRED",
                requires_human_confirmation=True,
            )
        )
        self.assertEqual(result["sensitivity"], "FINANCIAL_REVIEW_REQUIRED")
        self.assertEqual(result["final_decision"], "HOLD")

    def test_16_legal_candidate_requires_review(self) -> None:
        result = self._receive(
            self._candidate(
                attribute_name="contract",
                sensitivity="LEGAL_REVIEW_REQUIRED",
                requires_human_confirmation=True,
            )
        )
        self.assertEqual(result["sensitivity"], "LEGAL_REVIEW_REQUIRED")
        self.assertEqual(result["final_decision"], "HOLD")

    def test_17_safe_attribute_can_allow(self) -> None:
        result = self._receive(self._candidate(attribute_name="public_label"))
        self.assertEqual(result["final_decision"], "ALLOW")
        self.assertTrue(result["commit_applied"])

    def test_18_insufficient_evidence_holds(self) -> None:
        result = self._receive(
            self._candidate(
                attribute_name="equipment_safety_status",
                sensitivity="EVIDENCE_REQUIRED",
                evidence_refs=[],
            )
        )
        self.assertEqual(result["final_decision"], "HOLD")
        self.assertIn("HOLD_EVIDENCE_REQUIRED", result["decision_reason_codes"])

    def test_19_candidate_conflict_holds_independently(self) -> None:
        first = self._candidate(candidate_value="alpha", event_suffix="conflict-a")
        second = self._candidate(candidate_value="beta", event_suffix="conflict-b")
        results = self.gateway.receive_batch(
            [first, second], previous_values=self._previous_values(first)
        )
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item["final_decision"] == "HOLD" for item in results))
        self.assertTrue(all(not item["commit_applied"] for item in results))

    def test_20_allow_commits_candidate_value(self) -> None:
        result = self._receive(self._candidate(candidate_value={"label": "safe"}))
        self.assertTrue(result["commit_applied"])
        self.assertEqual(result["committed"], result["proposed"])

    def test_21_hold_preserves_previous(self) -> None:
        result = self._receive(
            self._candidate(sensitivity="EVIDENCE_REQUIRED"), previous="previous"
        )
        self.assertEqual(result["final_decision"], "HOLD")
        self.assertEqual(result["committed"], "previous")

    def test_22_block_preserves_previous(self) -> None:
        result = self._receive(
            self._candidate(
                attribute_name="token", sensitivity="PRIVACY_RESTRICTED"
            ),
            previous="previous",
        )
        self.assertEqual(result["final_decision"], "BLOCK")
        self.assertEqual(result["committed"], "previous")

    def test_23_quarantine_preserves_previous(self) -> None:
        result = self._receive(
            self._candidate(sensitivity="UNSUPPORTED"), previous="previous"
        )
        self.assertEqual(result["final_decision"], "QUARANTINE")
        self.assertEqual(result["committed"], "previous")

    def test_24_persona_text_is_excluded_from_tfs_and_hash(self) -> None:
        candidate = self._candidate()
        first = build_xiaoj_envelope("persona-alpha", candidate)
        second = build_xiaoj_envelope("persona-beta", candidate)
        self.assertEqual(
            first.governance_candidate.candidate_hash,
            second.governance_candidate.candidate_hash,
        )
        result = self.gateway.receive_candidate(
            first.governance_payload(), previous_value="previous"
        )
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("persona-alpha", serialized)
        self.assertNotIn("persona-beta", serialized)

    def test_25_no_database_write_api(self) -> None:
        self.assertTrue(
            self._import_roots().isdisjoint(
                {"sqlite3", "psycopg", "psycopg2", "sqlalchemy", "odoo"}
            )
        )

    def test_26_no_deploy_api(self) -> None:
        self.assertNotIn("subprocess", self._import_roots())
        self.assertTrue(all("deploy(" not in path.read_text(encoding="utf-8") for path in MODULE_PATHS))

    def test_27_no_restart_or_reboot_api(self) -> None:
        source = "\n".join(path.read_text(encoding="utf-8") for path in MODULE_PATHS)
        self.assertNotIn("restart(", source)
        self.assertNotIn("reboot(", source)

    def test_28_no_router_write_api(self) -> None:
        source = "\n".join(path.read_text(encoding="utf-8") for path in MODULE_PATHS)
        self.assertNotIn("router_write(", source)
        self.assertNotIn("firewall", source.casefold())

    def test_29_no_real_cloud_call(self) -> None:
        self.assertTrue(
            self._import_roots().isdisjoint(
                {"openai", "requests", "httpx", "urllib", "socket"}
            )
        )
        provider = self._provider(self._candidate())
        provider.candidates_for("request:fixture:001", "LLM_PUSH")
        self.assertEqual(provider.call_count, 1)

    def test_30_error_codes_are_stable(self) -> None:
        invalid = self._candidate()
        invalid["candidate_hash"] = "0" * 64
        codes: list[str] = []
        for _ in range(2):
            with self.assertRaises(DomainCompletionError) as caught:
                validate_candidate(copy.deepcopy(invalid))
            codes.append(caught.exception.reason_code)
        self.assertEqual(codes, ["CANDIDATE_HASH_MISMATCH"] * 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
