import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from tools.d8_guard_eval import (
    ACTIVE_GTP_CANONICAL,
    GTP_TECHNICAL_DRIFT_ALERT_ID,
    GTP_TECHNICAL_DRIFT_RULES,
    _is_protected_full_scan_path,
    _resolve_adi_canonical,
    _scan_general_drift,
    matches,
    scan_technical_definition_drift,
    scan_technical_definition_drift_file,
)


ROOT = Path(__file__).resolve().parents[1]


class GtpTechnicalDriftScannerTests(unittest.TestCase):
    def rule_ids(self, result):
        return {finding["rule_id"] for finding in result["findings"]}

    def test_detects_all_required_gtp_drift_classes(self):
        sample = "\n".join(
            [
                "GTP is file transfer, cloud sync, backup, compression, and download decryption.",
                "GTP is complete and PASS.",
                "8D is eight flat fields.",
                "GTP uses LLM and floating-point vectors instead of deterministic lookup.",
                "Canonical and Runtime are updated and memory is anchored.",
            ]
        )
        result = scan_technical_definition_drift(sample, "samples/gtp_true_drift.md")
        self.assertEqual(result["state"], "BLOCK_TECHNICAL_DEFINITION_DRIFT")
        self.assertTrue({"GTP-TD-001", "GTP-TD-002", "GTP-TD-003", "GTP-TD-004", "GTP-TD-005"} <= self.rule_ids(result))

    def test_active_canonical_phrase_alone_is_not_authority_drift(self):
        result = scan_technical_definition_drift_file(ROOT / ACTIVE_GTP_CANONICAL)
        self.assertEqual(result["state"], "PASS_NO_TECHNICAL_DEFINITION_DRIFT")
        self.assertEqual(result["findings"], [])

    def test_required_semantic_model_authority_triggers_rule_006(self):
        sample = "GTP requires LLM cosine similarity as the necessary verifier and final decision authority."
        result = scan_technical_definition_drift(sample, "samples/gtp_semantic_authority.md")
        finding = next(item for item in result["findings"] if item["rule_id"] == "GTP-TD-006")
        self.assertEqual(finding["severity"], "BLOCK")

    def test_founder_discrete_equivalence_clarification_is_not_drift(self):
        sample = "\n".join(
            [
                "semantic-state equivalent means deterministic discrete-state equivalence.",
                "LLM, embedding, vector database, cosine similarity, fuzzy matching, probability scores, and floating semantic scores must not become required verifiers, decision makers, or execution authority.",
                "LLM is candidate only and cannot independently form PASS or ALLOW.",
            ]
        )
        result = scan_technical_definition_drift(sample, "samples/founder_clarification.md")
        self.assertNotIn("GTP-TD-006", self.rule_ids(result))

    def test_canonical_negative_definition_is_not_drift(self):
        canonical_line = (ROOT / ACTIVE_GTP_CANONICAL).read_text(encoding="utf-8").splitlines()[23]
        result = scan_technical_definition_drift(canonical_line, ACTIVE_GTP_CANONICAL)
        self.assertEqual(result["state"], "PASS_NO_TECHNICAL_DEFINITION_DRIFT")
        self.assertEqual(result["findings"], [])

    def test_negated_prohibitions_are_not_drift(self):
        sample = "\n".join(
            [
                "GTP is not file moving, sync, backup, compression, or download decryption.",
                "8D is not eight fields and must not be flattened.",
                "GTP must not use LLM, diffusion, or floating vectors to replace deterministic lookup.",
                "Canonical is not updated and memory is not anchored.",
                "The semantic-state-equivalent mode is forbidden and quarantined.",
            ]
        )
        result = scan_technical_definition_drift(sample, "samples/gtp_negative_policy.md")
        self.assertEqual(result["findings"], [])

    def test_quotes_and_fenced_samples_are_not_drift(self):
        sample = "\n".join(
            [
                "> GTP is file transfer and backup.",
                "```text",
                "GTP uses LLM instead of lookup.",
                "8D is eight fields.",
                "```",
            ]
        )
        result = scan_technical_definition_drift(sample, "samples/quoted_prior_art.md")
        self.assertEqual(result["findings"], [])

    def test_test_sample_path_is_excluded(self):
        result = scan_technical_definition_drift(
            "GTP is file transfer and backup.",
            "tests/fixtures/test_gtp_drift_sample.txt",
        )
        self.assertEqual(result["state"], "PASS_EXCLUDED_TEST_OR_QUOTED_CONTEXT")
        self.assertEqual(result["findings"], [])

    def test_redteam_quarantine_evidence_is_excluded(self):
        sample = """
        {
          "retrieval_scope": "redteam_only",
          "quarantine": true,
          "summary": "GTP is file transfer and backup."
        }
        """
        result = scan_technical_definition_drift(sample, "runtime/d8_db/reports/redteam_evidence.json")
        self.assertEqual(result["state"], "PASS_EXCLUDED_REDTEAM_QUARANTINE_EVIDENCE")
        self.assertEqual(result["findings"], [])

    def test_fake_pass_without_required_operands_is_hold_finding(self):
        result = scan_technical_definition_drift("GTP complete: PASS.", "samples/fake_pass.md")
        finding = next(item for item in result["findings"] if item["rule_id"] == "GTP-TD-002")
        self.assertEqual(finding["severity"], "HOLD")
        self.assertIn("Missing operands:", finding["correction"])

    def test_receipted_update_claim_is_not_unreceipted_drift(self):
        sample = "GTP canonical is updated. Total Field receipt=receipt:test:1."
        result = scan_technical_definition_drift(sample, "samples/receipted_update.md")
        self.assertNotIn("GTP-TD-005", self.rule_ids(result))

    def test_matcher_reuses_gtp_alert_extension_point(self):
        alert = {"event_type": GTP_TECHNICAL_DRIFT_ALERT_ID}
        drift_scope = {
            "technical_drift_scan": {
                "domain": "GTP",
                "source_file": "scope/gtp_claim.md",
                "content": "GTP is cloud sync and backup.",
            }
        }
        clean_scope = {
            "technical_drift_scan": {
                "domain": "GTP",
                "source_file": "scope/gtp_policy.md",
                "content": "GTP is not cloud sync or backup.",
            }
        }
        self.assertTrue(matches(alert, drift_scope))
        self.assertFalse(matches(alert, clean_scope))

    def test_findings_have_only_reviewable_metadata(self):
        result = scan_technical_definition_drift("8D is eight fields.", "samples/flat_8d.md")
        finding = result["findings"][0]
        self.assertEqual(
            set(finding),
            {
                "rule_id",
                "file",
                "line",
                "evidence_sha256",
                "canonical_reference",
                "severity",
                "correction",
            },
        )
        self.assertEqual(set(GTP_TECHNICAL_DRIFT_RULES), {f"GTP-TD-{number:03d}" for number in range(1, 12)})


class FullSystemDeterministicDriftScannerTests(unittest.TestCase):
    def rule_ids(self, findings):
        return {finding["rule_id"] for finding in findings}

    def test_general_rules_detect_authority_state_identity_and_parallel_drift(self):
        sample = "\n".join(
            [
                "Canonical is ACTIVE and VERIFIED.",
                "Memory is anchored and persisted.",
                "A token grants sovereign identity and execution authorization.",
                "Create a parallel receiver.",
            ]
        )
        findings, suppressed = _scan_general_drift(
            ROOT / "docs/full_scan_true_drift.md",
            sample,
            "0" * 64,
        )
        self.assertEqual(suppressed, 0)
        self.assertTrue(
            {"AUTH-TD-001", "STATE-TD-001", "ARCH-TD-001"}
            <= self.rule_ids(findings)
        )
        self.assertFalse(any(rule_id.startswith("IDENTITY-") for rule_id in self.rule_ids(findings)))

    def test_general_negative_and_historical_lines_are_suppressed(self):
        sample = "\n".join(
            [
                "Canonical must not be declared ACTIVE without a receipt.",
                "Historical: a token grants sovereign identity.",
            ]
        )
        findings, suppressed = _scan_general_drift(
            ROOT / "docs/full_scan_negative_policy.md",
            sample,
            "1" * 64,
        )
        self.assertEqual(findings, [])
        self.assertGreaterEqual(suppressed, 2)

    def test_adi_without_exact_canonical_and_active_index_is_unbound(self):
        with TemporaryDirectory() as directory:
            result = _resolve_adi_canonical(Path(directory))
        self.assertEqual(result["state"], "HOLD_ADI_CANONICAL_UNBOUND")
        self.assertEqual(result["files_scanned"], 0)
        self.assertEqual(result["hold_count"], 1)

    def test_protected_source_names_are_rejected_before_read(self):
        self.assertTrue(_is_protected_full_scan_path(ROOT / "docs/.env.audit"))
        self.assertTrue(_is_protected_full_scan_path(ROOT / "runtime/private/member_state.json"))
        self.assertTrue(
            _is_protected_full_scan_path(
                ROOT / "runtime/total_field/reports/FULL_SYSTEM_DETERMINISTIC_DRIFT_BASELINE_TEST.json"
            )
        )

    def test_receiver_verification_rule_ignores_unrelated_verified_status(self):
        unrelated, _ = _scan_general_drift(
            ROOT / "docs/unrelated_status.md",
            "Build status is VERIFIED.",
            "2" * 64,
        )
        receiver, _ = _scan_general_drift(
            ROOT / "docs/receiver_status.md",
            "GTP receiver status is VERIFIED.",
            "3" * 64,
        )
        self.assertNotIn("EVIDENCE-TD-002", self.rule_ids(unrelated))
        self.assertIn("EVIDENCE-TD-002", self.rule_ids(receiver))

    def test_canonical_variable_name_is_not_an_authority_claim(self):
        findings, _ = _scan_general_drift(
            ROOT / "tools/canonical_variable.py",
            'canonical = f"{size}{item}"\ncanonical_ref = "X-W7TP-Canonical-Ref"',
            "4" * 64,
        )
        self.assertNotIn("AUTH-TD-001", self.rule_ids(findings))


if __name__ == "__main__":
    unittest.main()
