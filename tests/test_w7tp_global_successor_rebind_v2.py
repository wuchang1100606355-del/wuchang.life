from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shutil import copy2

from tools.total_field import w7tp_successor_rebind_reviewer_v1 as reviewer
from tools.total_field import w7tp_successor_rebind_seal_v1 as sealer

SOURCE_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = (
    "w7tp_total_field_successor_rebind_review_request_v2.schema.json",
    "w7tp_total_field_successor_rebind_decision_v2.schema.json",
    "w7tp_total_field_successor_rebind_receipt_v2.schema.json",
    "w7tp_total_field_successor_rebind_seal_v2.schema.json",
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GlobalSuccessorRebindV2Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        schema_dir = self.root / "schemas/field"
        schema_dir.mkdir(parents=True)
        for name in SCHEMAS:
            copy2(SOURCE_ROOT / "schemas/field" / name, schema_dir / name)
        self.now = datetime(2026, 10, 3, 17, 30, tzinfo=timezone.utc)
        self.request_path, self.atom = self._build_fixture()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _build_fixture(self) -> tuple[Path, dict]:
        pointer_ref = "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
        current_field_ref = "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_CANONICAL.json"
        router_ref = "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"
        authority_ref = "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
        write_json(self.root / pointer_ref, {"state": "ACTIVE_CANONICAL", "version": "2.1"})
        write_json(self.root / current_field_ref, {"state": "ACTIVE_LEGACY_FIELD"})
        write_json(self.root / router_ref, {"state": "ACTIVE_LEGACY_ROUTER_FIELD"})
        write_json(
            self.root / authority_ref,
            {"node_id": "taiji01", "state": "ACTIVE_TOTAL_FIELD_AUTHORITY"},
        )
        pointer_sha = sha(self.root / pointer_ref)
        field_sha = sha(self.root / current_field_ref)
        router_sha = sha(self.root / router_ref)
        authority_sha = sha(self.root / authority_ref)

        run_id = "T007_V23_GLOBAL_SUCCESSOR_TEST"
        candidate_rel = Path("Taiji_Governance/candidates/t007_test")
        candidate = self.root / candidate_rel
        directive = {
            "founder": "江政隆",
            "run_id": run_id,
            "state": "USER_EXPLICIT_FOUNDER_DIRECTIVE",
            "replacement_boundary": {
                "replace_active_v21_authority_consumption": True,
                "replace_active_v21_runtime_consumption": True,
                "replace_active_v21_skill_binding": True,
                "preserve_historical_v21_evidence": True,
            },
        }
        contract = {
            "state": "CANDIDATE_FOR_FORMAL_TOTAL_FIELD_REVIEW",
            "task_id": "T-007",
            "migration_mode": "APPEND_ONLY_SUCCESSOR",
            "predecessor": {
                "pointer_ref": pointer_ref,
                "pointer_sha256": pointer_sha,
                "version": "2.1",
            },
            "proposed_successor": {
                "canonical_id": "W7TP_8D_ADI_V2_3",
                "version": "2.3",
                "dimension_contract": {
                    "D1": "Intent",
                    "D2": "State",
                    "D3": "Coordinate",
                    "D4": "Evidence",
                    "D5": "Execution/Policy",
                    "D6": "Generative State Transmission",
                    "D7": "Risk/Isolation",
                    "D8": "Envelope/Authority",
                    "mode": "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD",
                    "sequential_pipeline_definition_forbidden": True,
                },
                "d6_contract": {"difference_analysis_is_transmission": False},
            },
        }
        field_successor = {
            "state": "CANDIDATE_NOT_ACTIVE",
            "activation": False,
            "semantics": "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD",
            "predecessor_ref": current_field_ref,
            "predecessor_sha256": field_sha,
            "difference_analysis": {"is_generative_transmission": False},
        }
        consumers = []
        for path in sorted(reviewer.GLOBAL_REQUIRED_ACTIVE_CONSUMERS):
            action = "REBIND_TO_V23"
            if path == "tools/total_field/w7tp_review_candidate_v2_3_adapter_v2_1.py":
                action = "RETIRE_FROM_ACTIVE_PATH; retain historical compatibility only"
            consumers.append({"path": path, "action": action})
        matrix = {
            "consumers": consumers,
            "history_policy": (
                "V2.1 strings in evidence, receipts, preimages, release archives, migration history, "
                "and legacy adapters are not rewritten merely to remove the version number."
            ),
        }
        authority_receipt = {
            "formal": False,
            "removed_effects": [],
            "successor": {"ref": authority_ref, "sha256": authority_sha},
            "checks": {
                "predecessor_effects_preserved": True,
                "gst_v23_formal_delivery_preserved": True,
            },
        }
        docs = {
            "00_FOUNDER_DIRECTIVE.json": directive,
            "01_V23_GLOBAL_SUCCESSOR_CONTRACT_CANDIDATE.json": contract,
            "02_CURRENT_8D_FIELD_V23_SUCCESSOR_CANDIDATE.json": field_successor,
            "03_ACTIVE_CONSUMER_REBIND_MATRIX.json": matrix,
            "04_AUTHORITY_POINTER_SUCCESSOR_RECEIPT_CANDIDATE.json": authority_receipt,
        }
        for name, value in docs.items():
            write_json(candidate / name, value)
        manifest = {
            "run_id": run_id,
            "files": {name: {"sha256": sha(candidate / name)} for name in docs},
        }
        write_json(candidate / "SHA256_MANIFEST.json", manifest)
        manifest_sha = sha(candidate / "SHA256_MANIFEST.json")

        founder_ref = "authority/TEST_FOUNDER_AUTHORIZATION.json"
        write_json(self.root / founder_ref, {"founder": "江政隆", "state": "TEST_ONLY"})
        package_map = {
            "founder_directive": "00_FOUNDER_DIRECTIVE.json",
            "successor_contract": "01_V23_GLOBAL_SUCCESSOR_CONTRACT_CANDIDATE.json",
            "current_field_successor": "02_CURRENT_8D_FIELD_V23_SUCCESSOR_CANDIDATE.json",
            "consumer_rebind_matrix": "03_ACTIVE_CONSUMER_REBIND_MATRIX.json",
            "authority_successor_receipt": "04_AUTHORITY_POINTER_SUCCESSOR_RECEIPT_CANDIDATE.json",
        }
        package_bindings = {
            key: {
                "ref": (candidate_rel / name).as_posix(),
                "sha256": sha(candidate / name),
            }
            for key, name in package_map.items()
        }
        record_id = "evidence:t007-v23-global-successor-bootstrap:20261003T173000Z"
        record_sha = "a" * 64
        atom = {
            "id": record_id,
            "record_sha256": record_sha,
            "time_slot": int(self.now.timestamp()),
            "payload": {
                "CURRENT_CONTEXT_ELIGIBLE": True,
                "DYNAMIC_CONTEXT_ELIGIBLE": True,
                "RUNTIME_DECISION_ELIGIBLE": True,
                "D1_INTENT": {"task_ref": "task:T-007"},
                "D2_STATE": {"active_machine_pointer_version": "2.1"},
                "D3_COORDINATE": {
                    "node": "taiji01",
                    "candidate_root": candidate_rel.as_posix(),
                    "canonical_pointer_ref": pointer_ref,
                },
                "D4_EVIDENCE": {
                    "candidate_manifest_sha256": manifest_sha,
                    "canonical_pointer_sha256": pointer_sha,
                    "current_field_sha256": field_sha,
                    "current_field_router_sha256": router_sha,
                    "total_field_authority_sha256": authority_sha,
                },
                "D5_EXECUTION": {"canonical_pointer_change": False},
                "D7_RISK": {"fail_closed_on_source_hash_drift": True},
                "D8_AUTHORITY": {
                    "candidate_only": True,
                    "canonical": False,
                    "promotion_authorized_by_this_record": False,
                },
            },
        }
        request = {
            "schema_version": reviewer.GLOBAL_REQUEST_SCHEMA_VERSION,
            "packet_type": "TOTAL_FIELD_SUCCESSOR_REBIND_REVIEW_REQUEST",
            "review_scope": reviewer.GLOBAL_REVIEW_SCOPE,
            "request_id": "request:T007:GLOBAL:UNIT",
            "run_id": run_id,
            "task_id": "T-007",
            "canonical_ref": pointer_ref,
            "predecessor_pointer_sha256": pointer_sha,
            "predecessor_version": "2.1",
            "successor_version": "2.3",
            "candidate_root": candidate_rel.as_posix(),
            "manifest_sha256": manifest_sha,
            "package_bindings": package_bindings,
            "live_bindings": {
                "current_field": {"ref": current_field_ref, "sha256": field_sha},
                "current_field_router": {"ref": router_ref, "sha256": router_sha},
                "total_field_authority": {"ref": authority_ref, "sha256": authority_sha},
            },
            "dynamic_context": {
                "adi_record_id": record_id,
                "record_sha256": record_sha,
                "maximum_age_seconds": 3600,
            },
            "nonce": "nonce:sha256:" + "b" * 64,
            "created_at": reviewer.utc_text(self.now),
            "expires_at": reviewer.utc_text(self.now + timedelta(minutes=30)),
            "replay_guard": {
                "single_use": True,
                "domain": "T007_GLOBAL_SUCCESSOR_UNIT",
                "ledger_ref": "test:ledger",
                "on_replay": reviewer.DECISION_HOLD,
            },
            "authority_pointer_ref": authority_ref,
            "authority_pointer_sha256": authority_sha,
            "founder_authorization_ref": founder_ref,
            "founder_authorization_sha256": sha(self.root / founder_ref),
            "requested_decision": reviewer.DECISION_APPROVED,
            "contract_mode": "CANDIDATE_CONTRACT_ONLY",
            "request_self_hash_algorithm": reviewer.REQUEST_SELF_HASH_ALGORITHM,
            "non_execution_assertions": {field: False for field in reviewer.NON_EXECUTION_FIELDS},
        }
        request["request_self_sha256"] = reviewer.sha256_bytes(reviewer.canonical_json_bytes(request))
        request_path = self.root / "request.json"
        write_json(request_path, request)
        return request_path, atom

    def _review(self) -> dict:
        return reviewer.review_once(
            request_path=self.request_path,
            repo_root=self.root,
            now=self.now,
            test_mode=True,
            tracked_checker=lambda _: True,
            native_adi_loader=lambda _: self.atom,
        )

    def test_global_mode_passes_candidate_only_and_keeps_formal_false(self) -> None:
        result = self._review()
        self.assertEqual(result["decision"], reviewer.DECISION_APPROVED)
        self.assertFalse(result["formal"])
        self.assertEqual(
            result["decision_document"]["review_scope"],
            reviewer.GLOBAL_REVIEW_SCOPE,
        )
        self.assertTrue(all(v == "PASS" for v in result["receipt_document"]["checks"].values()))

    def test_pointer_hash_drift_fails_closed(self) -> None:
        pointer = self.root / "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
        write_json(pointer, {"state": "ACTIVE_CANONICAL", "version": "2.1", "drift": True})
        result = self._review()
        self.assertEqual(result["decision"], reviewer.DECISION_HOLD)
        self.assertEqual(result["reason_codes"], ["HOLD_CANONICAL_PREIMAGE_HASH_OR_PATH"])

    def test_global_test_seal_preserves_package_and_dynamic_context_binding(self) -> None:
        result = self._review()
        decision_path = self.root / "decision.json"
        receipt_path = self.root / "receipt.json"
        write_json(decision_path, result["decision_document"])
        write_json(receipt_path, result["receipt_document"])
        request = json.loads(self.request_path.read_text(encoding="utf-8"))
        seal = sealer.create_seal(
            manifest_path=self.root / request["candidate_root"] / "SHA256_MANIFEST.json",
            manifest_sha256=request["manifest_sha256"],
            decision_path=decision_path,
            receipt_path=receipt_path,
            authority_pointer_path=self.root / request["authority_pointer_ref"],
            authority_pointer_sha256=request["authority_pointer_sha256"],
            repo_root=self.root,
            now=self.now + timedelta(seconds=10),
            test_mode=True,
            tracked_checker=lambda _: True,
        )
        self.assertEqual(seal["schema_version"], sealer.GLOBAL_SEAL_SCHEMA_VERSION)
        self.assertEqual(seal["seal_state"], "TEST_SEAL_ONLY")
        self.assertFalse(seal["formal"])
        self.assertEqual(
            seal["package_binding_sha256"],
            result["decision_document"]["package_binding_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
