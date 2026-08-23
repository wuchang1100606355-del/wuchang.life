from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest


OVERLAY = Path(__file__).resolve().parents[2]
TOOLS = OVERLAY / "tools" / "total_field"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_reconstruct_isolated_v2_contract import valid_request  # noqa: E402
from w7tp_reconstruct_isolated_contract import (  # noqa: E402
    DECISION_CONTRACT_ID,
    DECISION_HASH_ALGORITHM,
    MAXIMUM_EFFECT,
    MINIMUM_GENERATIVE_DELTA_SHA256,
    TARGET_BASE_STATE_SHA256,
    TARGET_FIELD_SNAPSHOT_SHA256,
    TARGET_SUCCESSOR_CANONICAL_SHA256,
    self_hash,
)
from w7tp_reconstruct_isolated_runner_gate import (  # noqa: E402
    validate_runner_gate,
)
from w7tp_reconstruct_isolated_validator import ReconstructIsolatedValidationError  # noqa: E402


SCHEMA = OVERLAY / "schemas" / "field" / "w7tp_total_field_d8_review_request_v2.schema.json"


def make_allow_decision(request: dict) -> dict:
    decision = {
        "contract": DECISION_CONTRACT_ID,
        "decision_id": f"D8_ALLOW_{request['request_id']}",
        "decision": "ALLOW",
        "state": "PASS",
        "request_sha256": request["request_self_sha256"],
        "scope_sha256": request["scope_sha256"],
        "target_field_snapshot_sha256": TARGET_FIELD_SNAPSHOT_SHA256,
        "target_base_state_sha256": TARGET_BASE_STATE_SHA256,
        "target_successor_canonical_sha256": TARGET_SUCCESSOR_CANONICAL_SHA256,
        "minimum_generative_delta_sha256": MINIMUM_GENERATIVE_DELTA_SHA256,
        "exact_workspace": request["workspace"]["root"],
        "exact_targets": list(request["exact_targets"]),
        "authorized_steps": list(request["authorized_steps"]),
        "maximum_effect": MAXIMUM_EFFECT,
        "expires_at": request["expires_at"],
        "single_use": True,
        "review_request_single_use_consumed": True,
        "execution_single_use_consumed": False,
        "replay_disposition": "UNCONSUMED_FOR_EXECUTION",
        "decision_hash_algorithm": DECISION_HASH_ALGORITHM,
        "decision_sha256": "0" * 64,
    }
    decision["decision_sha256"] = self_hash(decision, "decision_sha256")
    return decision


def make_synthetic_review_receipt(request: dict, decision: dict) -> dict:
    receipt = {
        "contract": "W7TP-TOTAL-FIELD-RECONSTRUCT-ISOLATED-REVIEW-RECEIPT/2.0",
        "receipt_id": f"REVIEW_RECEIPT_{request['request_id']}",
        "reviewer_version": "w7tp-reconstruct-isolated-reviewer/2.0-candidate",
        "request_sha256": request["request_self_sha256"],
        "scope_sha256": request["scope_sha256"],
        "decision_sha256": decision["decision_sha256"],
        "review_evidence_sha256": "b" * 64,
        "final_decision": "ALLOW",
        "state": "PASS",
        "review_request_single_use_consumed": True,
        "execution_single_use_consumed": False,
        "replay_disposition": "UNCONSUMED_FOR_EXECUTION",
        "canary_started": False,
        "receipt_hash_algorithm": "SHA256_CANONICAL_JSON_EXCLUDING_RECEIPT_SHA256/1.0",
        "receipt_sha256": "0" * 64,
    }
    receipt["receipt_sha256"] = self_hash(receipt, "receipt_sha256")
    return receipt


def test_exact_decision_request_binding_passes_without_execution(tmp_path: Path) -> None:
    request, now = valid_request()
    decision = make_allow_decision(request)
    receipt = make_synthetic_review_receipt(request, decision)
    result = validate_runner_gate(decision, request, receipt, now=now, repo_root=tmp_path, schema_path=SCHEMA)
    assert result["gate"] == "ALLOW"
    assert result["no_execution_performed"] is True
    assert result["execution_single_use_consumed"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("decision", "DENY"),
        ("state", "HOLD"),
        ("request_sha256", "1" * 64),
        ("scope_sha256", "2" * 64),
        ("target_field_snapshot_sha256", "3" * 64),
        ("target_base_state_sha256", "4" * 64),
        ("target_successor_canonical_sha256", "5" * 64),
        ("minimum_generative_delta_sha256", "6" * 64),
        ("exact_workspace", "runtime/isolated/wrong"),
        ("maximum_effect", "EXPANDED"),
        ("execution_single_use_consumed", True),
        ("replay_disposition", "CONSUMED_EXACTLY_ONCE"),
    ],
)
def test_any_decision_request_mismatch_denies(field: str, value, tmp_path: Path) -> None:
    request, now = valid_request()
    decision = make_allow_decision(request)
    decision[field] = value
    decision["decision_sha256"] = self_hash(decision, "decision_sha256")
    receipt = make_synthetic_review_receipt(request, decision)
    with pytest.raises(ReconstructIsolatedValidationError):
        validate_runner_gate(decision, request, receipt, now=now, repo_root=tmp_path, schema_path=SCHEMA)


def test_runner_without_v2_scope_denies(tmp_path: Path) -> None:
    request, now = valid_request()
    legacy_request = {
        "schema_version": "W7TP-D8-REVIEW-REQUEST/1.0",
        "requested_decision": "ALLOW_P2_ISOLATED_CANARY_EXECUTION_ONLY",
        "c1_c9_execution_authorized": True,
    }
    decision = make_allow_decision(request)
    receipt = make_synthetic_review_receipt(request, decision)
    with pytest.raises(ReconstructIsolatedValidationError):
        validate_runner_gate(decision, legacy_request, receipt, now=now, repo_root=tmp_path, schema_path=SCHEMA)


def test_replayed_request_denies(tmp_path: Path) -> None:
    request, now = valid_request()
    decision = make_allow_decision(request)
    receipt = make_synthetic_review_receipt(request, decision)
    replay_root = tmp_path / "replay"
    replay_root.mkdir()
    (replay_root / "TOTAL_FIELD_RECONSTRUCT_ISOLATED_RECEIPT.json").write_text(
        json.dumps({"request_sha256": request["request_self_sha256"], "single_use_consumed": True}),
        encoding="utf-8",
    )
    with pytest.raises(ReconstructIsolatedValidationError):
        validate_runner_gate(
            decision,
            request,
            receipt,
            now=now,
            repo_root=tmp_path,
            replay_root=replay_root,
            schema_path=SCHEMA,
        )


def test_decision_additional_property_injection_denies(tmp_path: Path) -> None:
    request, now = valid_request()
    decision = make_allow_decision(request)
    decision["fallback"] = "ALLOW_ANYWAY"
    decision["decision_sha256"] = self_hash(decision, "decision_sha256")
    receipt = make_synthetic_review_receipt(request, decision)
    with pytest.raises(ReconstructIsolatedValidationError):
        validate_runner_gate(decision, request, receipt, now=now, repo_root=tmp_path, schema_path=SCHEMA)


def test_missing_or_mismatched_total_field_review_receipt_denies(tmp_path: Path) -> None:
    request, now = valid_request()
    decision = make_allow_decision(request)
    with pytest.raises(ReconstructIsolatedValidationError):
        validate_runner_gate(decision, request, {}, now=now, repo_root=tmp_path, schema_path=SCHEMA)
    receipt = make_synthetic_review_receipt(request, decision)
    receipt["request_sha256"] = "f" * 64
    receipt["receipt_sha256"] = self_hash(receipt, "receipt_sha256")
    with pytest.raises(ReconstructIsolatedValidationError):
        validate_runner_gate(decision, request, receipt, now=now, repo_root=tmp_path, schema_path=SCHEMA)
