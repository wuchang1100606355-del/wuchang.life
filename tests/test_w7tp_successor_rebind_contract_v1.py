import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.total_field import w7tp_successor_rebind_reviewer_v1 as reviewer
from tools.total_field import w7tp_successor_rebind_seal_v1 as seal_tool


class SuccessorRebindContractV1Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 8, 4, 2, 0, tzinfo=timezone.utc)
        self.actual_root = Path(__file__).resolve().parents[1]
        schema_names = (
            "w7tp_total_field_successor_rebind_review_request_v1.schema.json",
            "w7tp_total_field_successor_rebind_decision_v1.schema.json",
            "w7tp_total_field_successor_rebind_receipt_v1.schema.json",
            "w7tp_total_field_successor_rebind_seal_v1.schema.json",
        )
        for name in schema_names:
            target = self.root / "schemas" / "field" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.actual_root / "schemas" / "field" / name, target)
        self.predecessor_commit = "1" * 40
        self.current_commit = "2" * 40
        self.predecessor_blob = b"def total_field_candidate_decision():\n    return 'HOLD'\n"
        self.current_blob = (
            b"BreakpointReachabilityDenied = RuntimeError\n"
            b"breakpoint_segment_ref = 'bound'\n"
            b"def total_field_candidate_decision():\n    return 'HOLD'\n"
        )

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def non_execution():
        return {field: False for field in reviewer.NON_EXECUTION_FIELDS}

    def source_loader(self, commit, path):
        self.assertEqual("core/adi_native/verifier.py", path)
        if commit == self.predecessor_commit:
            return self.predecessor_blob
        if commit == self.current_commit:
            return self.current_blob
        raise reviewer.SuccessorRebindReviewError(reviewer.DECISION_HOLD, "HOLD_TEST_COMMIT_MISSING")

    def subject_loader(self, commit):
        self.assertEqual(self.current_commit, commit)
        return "feat(adi-native): enforce breakpoint reachability contract v1"

    def resign_request(self, path):
        value = json.loads(path.read_text(encoding="utf-8"))
        value.pop("request_self_sha256", None)
        value["request_self_sha256"] = reviewer.sha256_bytes(reviewer.canonical_json_bytes(value))
        self.write_json(path, value)
        return value

    def make_package(self, name="valid", *, created_at=None, expires_at=None, authority_state="TEST_ONLY"):
        case = self.root / "cases" / name
        canonical = case / "ACTIVE_W7TP_CANONICAL_POINTER.json"
        self.write_json(canonical, {"state": "ACTIVE_CANONICAL", "version": "2.1"})
        candidate = case / "candidate"
        manifest = candidate / "SHA256_MANIFEST.json"
        self.write_json(manifest, {"run_id": name, "candidate_only": True})
        authority = case / "AUTHORITY_POINTER.json"
        self.write_json(
            authority,
            {
                "state": authority_state,
                "contract_state": "TEST_ONLY",
                "node_id": "taiji01",
                "formal_decision_authority": False,
                "formal_seal_authority": False,
            },
        )
        founder = case / "FOUNDER_AUTHORIZATION.json"
        self.write_json(founder, {"state": "TEST_ONLY", "founder": "江政隆", "authorized_effect": "TEST_VECTOR_ONLY"})
        request_path = case / "TOTAL_FIELD_SUCCESSOR_REBIND_REVIEW_REQUEST.json"
        created = created_at or self.now
        expires = expires_at or (self.now + timedelta(minutes=30))
        request = {
            "schema_version": reviewer.REQUEST_SCHEMA_VERSION,
            "packet_type": "TOTAL_FIELD_SUCCESSOR_REBIND_REVIEW_REQUEST",
            "request_id": f"request:{name}",
            "run_id": f"RUN_{name.upper().replace('-', '_')}",
            "canonical_ref": canonical.relative_to(self.root).as_posix(),
            "candidate_root": candidate.relative_to(self.root).as_posix(),
            "manifest_sha256": self.sha(manifest),
            "source_path_ref": "core/adi_native/verifier.py",
            "symbol_ref": "total_field_candidate_decision",
            "predecessor_commit": self.predecessor_commit,
            "predecessor_sha256": hashlib.sha256(self.predecessor_blob).hexdigest(),
            "current_commit": self.current_commit,
            "current_sha256": hashlib.sha256(self.current_blob).hexdigest(),
            "change_provenance": "feat(adi-native): enforce breakpoint reachability contract v1",
            "breakpoint_reachability_contract": "BREAKPOINT_REACHABILITY_CONTRACT_V1",
            "nonce": "nonce:sha256:" + hashlib.sha256(name.encode("utf-8")).hexdigest(),
            "created_at": reviewer.utc_text(created),
            "expires_at": reviewer.utc_text(expires),
            "replay_guard": {
                "single_use": True,
                "domain": f"test:{name}",
                "ledger_ref": "test:ledger",
                "on_replay": reviewer.DECISION_HOLD,
            },
            "authority_pointer_ref": authority.relative_to(self.root).as_posix(),
            "authority_pointer_sha256": self.sha(authority),
            "founder_authorization_ref": founder.relative_to(self.root).as_posix(),
            "founder_authorization_sha256": self.sha(founder),
            "requested_decision": reviewer.DECISION_APPROVED,
            "contract_mode": "CANDIDATE_CONTRACT_ONLY",
            "request_self_hash_algorithm": reviewer.REQUEST_SELF_HASH_ALGORITHM,
            "non_execution_assertions": self.non_execution(),
        }
        request["request_self_sha256"] = reviewer.sha256_bytes(reviewer.canonical_json_bytes(request))
        self.write_json(request_path, request)
        return {
            "case": case,
            "canonical": canonical,
            "candidate": candidate,
            "manifest": manifest,
            "authority": authority,
            "founder": founder,
            "request": request_path,
        }

    def review(self, package, output_name="output", replay_root=None):
        return reviewer.review_once(
            request_path=package["request"],
            repo_root=self.root,
            output_dir=self.root / "outputs" / output_name,
            replay_root=replay_root,
            now=self.now + timedelta(minutes=1),
            test_mode=True,
            source_loader=self.source_loader,
            subject_loader=self.subject_loader,
            tracked_checker=lambda _path: True,
        )

    def test_all_four_schemas_are_valid_and_decision_vocabulary_is_closed(self):
        for path in (self.root / "schemas" / "field").iterdir():
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
        decision_schema = json.loads(
            (self.root / "schemas/field/w7tp_total_field_successor_rebind_decision_v1.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            {reviewer.DECISION_APPROVED, reviewer.DECISION_REJECTED, reviewer.DECISION_HOLD},
            set(decision_schema["properties"]["decision"]["enum"]),
        )

    def test_pass_vector_emits_test_only_decision_receipt_and_test_seal(self):
        package = self.make_package("pass")
        result = self.review(package, "pass")
        self.assertEqual(reviewer.DECISION_APPROVED, result["decision"])
        self.assertFalse(result["formal"])
        output = self.root / "outputs" / "pass"
        decision_path = output / "TEST_TOTAL_FIELD_SUCCESSOR_REBIND_DECISION.json"
        receipt_path = output / "TEST_TOTAL_FIELD_SUCCESSOR_REBIND_RECEIPT.json"
        test_seal = seal_tool.create_seal(
            manifest_path=package["manifest"],
            manifest_sha256=self.sha(package["manifest"]),
            decision_path=decision_path,
            receipt_path=receipt_path,
            authority_pointer_path=package["authority"],
            authority_pointer_sha256=self.sha(package["authority"]),
            repo_root=self.root,
            now=self.now + timedelta(minutes=2),
            test_mode=True,
            tracked_checker=lambda _path: True,
        )
        self.assertEqual("TEST_SEAL_ONLY", test_seal["seal_state"])
        self.assertFalse(test_seal["formal"])
        self.assertFalse(test_seal["contract_approved"])

    def test_reject_vector_fails_closed_on_source_hash_drift(self):
        package = self.make_package("reject")
        request = json.loads(package["request"].read_text(encoding="utf-8"))
        request["current_sha256"] = "f" * 64
        self.write_json(package["request"], request)
        self.resign_request(package["request"])
        result = self.review(package, "reject")
        self.assertEqual(reviewer.DECISION_REJECTED, result["decision"])
        self.assertIn("REJECT_SOURCE_BINDING_HASH_DRIFT", result["reason_codes"])

    def test_expired_vector_holds(self):
        package = self.make_package(
            "expired",
            created_at=self.now - timedelta(hours=2),
            expires_at=self.now - timedelta(hours=1),
        )
        result = self.review(package, "expired")
        self.assertEqual(reviewer.DECISION_HOLD, result["decision"])
        self.assertIn("HOLD_REQUEST_EXPIRED", result["reason_codes"])

    def test_replay_vector_holds_second_use(self):
        package = self.make_package("replay")
        replay_root = self.root / "outputs"
        first = self.review(package, "replay-first", replay_root)
        self.assertEqual(reviewer.DECISION_APPROVED, first["decision"])
        second = self.review(package, "replay-second", replay_root)
        self.assertEqual(reviewer.DECISION_HOLD, second["decision"])
        self.assertIn("HOLD_NONCE_REPLAY", second["reason_codes"])

    def test_empty_manifest_hash_and_wrong_authority_fail_closed(self):
        empty = self.make_package("empty-manifest")
        request = json.loads(empty["request"].read_text(encoding="utf-8"))
        request["manifest_sha256"] = ""
        self.write_json(empty["request"], request)
        self.resign_request(empty["request"])
        result = self.review(empty, "empty-manifest")
        self.assertEqual(reviewer.DECISION_REJECTED, result["decision"])
        self.assertIn("REJECT_REQUEST_SCHEMA", result["reason_codes"])

        wrong = self.make_package("wrong-authority", authority_state="REQUEST_ONLY")
        result = self.review(wrong, "wrong-authority")
        self.assertEqual(reviewer.DECISION_HOLD, result["decision"])
        self.assertIn("HOLD_AUTHORITY_POINTER_REQUEST_ONLY", result["reason_codes"])

    def test_seal_rejects_hash_drift_and_null_manifest_hash(self):
        package = self.make_package("seal-drift")
        self.review(package, "seal-drift")
        output = self.root / "outputs" / "seal-drift"
        decision = output / "TEST_TOTAL_FIELD_SUCCESSOR_REBIND_DECISION.json"
        receipt = output / "TEST_TOTAL_FIELD_SUCCESSOR_REBIND_RECEIPT.json"
        with self.assertRaisesRegex(seal_tool.SuccessorRebindSealError, "REJECT_MANIFEST_SHA256_NULL_OR_INVALID"):
            seal_tool.create_seal(
                manifest_path=package["manifest"],
                manifest_sha256=None,
                decision_path=decision,
                receipt_path=receipt,
                authority_pointer_path=package["authority"],
                authority_pointer_sha256=self.sha(package["authority"]),
                repo_root=self.root,
                test_mode=True,
            )
        original_hash = self.sha(package["manifest"])
        self.write_json(package["manifest"], {"drift": True})
        with self.assertRaisesRegex(seal_tool.SuccessorRebindSealError, "REJECT_SOURCE_MANIFEST_HASH_DRIFT"):
            seal_tool.create_seal(
                manifest_path=package["manifest"],
                manifest_sha256=original_hash,
                decision_path=decision,
                receipt_path=receipt,
                authority_pointer_path=package["authority"],
                authority_pointer_sha256=self.sha(package["authority"]),
                repo_root=self.root,
                test_mode=True,
            )

    def test_formal_seal_rejects_untracked_inputs(self):
        package = self.make_package("untracked")
        self.review(package, "untracked")
        output = self.root / "outputs" / "untracked"
        decision_path = output / "TEST_TOTAL_FIELD_SUCCESSOR_REBIND_DECISION.json"
        receipt_path = output / "TEST_TOTAL_FIELD_SUCCESSOR_REBIND_RECEIPT.json"
        authority = {
            "state": "ACTIVE_TOTAL_FIELD_AUTHORITY",
            "contract_state": "ACTIVE_FORMAL",
            "node_id": "taiji01",
            "formal_decision_authority": True,
            "formal_seal_authority": True,
        }
        self.write_json(package["authority"], authority)
        authority_hash = self.sha(package["authority"])
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        decision["formal"] = True
        decision["authority_pointer_sha256"] = authority_hash
        decision.pop("decision_sha256")
        decision["decision_sha256"] = reviewer.sha256_bytes(reviewer.canonical_json_bytes(decision))
        self.write_json(decision_path, decision)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["formal"] = True
        receipt["authority_pointer_sha256"] = authority_hash
        receipt["decision_sha256"] = decision["decision_sha256"]
        receipt.pop("receipt_sha256")
        receipt["receipt_sha256"] = reviewer.sha256_bytes(reviewer.canonical_json_bytes(receipt))
        self.write_json(receipt_path, receipt)
        replay_root = self.root / "formal-replay"
        replay_root.mkdir()
        with self.assertRaisesRegex(seal_tool.SuccessorRebindSealError, "REJECT_UNTRACKED_FORMAL_INPUT"):
            seal_tool.create_seal(
                manifest_path=package["manifest"],
                manifest_sha256=self.sha(package["manifest"]),
                decision_path=decision_path,
                receipt_path=receipt_path,
                authority_pointer_path=package["authority"],
                authority_pointer_sha256=authority_hash,
                repo_root=self.root,
                replay_root=replay_root,
                now=self.now + timedelta(minutes=2),
                test_mode=False,
            )


if __name__ == "__main__":
    unittest.main()
