from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path


OVERLAY = Path(__file__).resolve().parents[2]
TOOLS = OVERLAY / "tools" / "total_field"
sys.path.insert(0, str(TOOLS))

from w7tp_reconstruct_isolated_contract import (  # noqa: E402
    CONTRACT_ID,
    REQUEST_HASH_ALGORITHM,
    canonical_json_bytes,
    make_request,
    scope_hash,
    self_hash,
    sha256_bytes,
)
from w7tp_reconstruct_isolated_receipt import build_post_execution_receipt  # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402


def valid_request(run_id: str = "STATIC_TEST_RUN") -> tuple[dict, datetime]:
    now = datetime(2026, 8, 21, 18, 0, tzinfo=timezone.utc)
    request = make_request(
        run_id,
        now.isoformat().replace("+00:00", "Z"),
        (now + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
    )
    return request, now + timedelta(minutes=1)


def resign(request: dict) -> dict:
    request["scope_sha256"] = scope_hash(request)
    request["request_self_sha256"] = self_hash(request, "request_self_sha256")
    return request


def test_canonicalization_reuses_p2_v1_rule() -> None:
    assert canonical_json_bytes({"b": 1, "a": "繁"}) == '{"a":"繁","b":1}'.encode("utf-8")


def test_request_hash_and_scope_hash_are_independent_and_exact() -> None:
    request, _ = valid_request()
    assert request["contract"] == CONTRACT_ID
    assert request["request_self_hash_algorithm"] == REQUEST_HASH_ALGORITHM
    assert request["scope_sha256"] == scope_hash(request)
    assert request["request_self_sha256"] == self_hash(request, "request_self_sha256")
    changed = deepcopy(request)
    changed["risks"].append("NEW_RISK")
    assert scope_hash(changed) != request["scope_sha256"]
    assert self_hash(changed, "request_self_sha256") != request["request_self_sha256"]


def test_schema_is_closed_and_typed() -> None:
    schema = json.loads((OVERLAY / "schemas" / "field" / "w7tp_total_field_d8_review_request_v2.schema.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert schema["properties"]["forbidden_effects"]["additionalProperties"] is False
    assert schema["properties"]["target"]["additionalProperties"] is False


def test_post_execution_receipt_is_hash_bound_to_three_evidence_objects(tmp_path: Path) -> None:
    request, now = valid_request()
    evidence_root = tmp_path / request["workspace"]["root"] / "evidence"
    evidence_root.mkdir(parents=True)
    common = {
        "request_sha256": request["request_self_sha256"],
        "scope_sha256": request["scope_sha256"],
        "target_field_snapshot_sha256": request["target"]["field_snapshot_sha256"],
        "target_base_state_sha256": request["target"]["base_state_sha256"],
        "target_successor_canonical_sha256": request["target"]["canonical_sha256"],
        "minimum_generative_delta_sha256": request["delta"]["sha256"],
    }
    execution = {
        **common,
        "state": "PASS",
        "reconstruction_base": request["reconstruction_base"]["callable"],
        "exact_targets": request["exact_targets"],
    }
    validation = {
        **common,
        "state": "PASS",
        "request_sha256_verified": True,
        "scope_sha256_verified": True,
        "target_hashes_verified": True,
        "exact_targets_verified": True,
        "existing_services_unchanged": True,
        "no_live_effect": True,
    }
    execution_path = evidence_root / "TARGET_NATIVE_RECONSTRUCTION_EVIDENCE.json"
    validation_path = evidence_root / "VALIDATION_REPORT.json"
    execution_path.write_bytes(canonical_json_bytes(execution))
    validation_path.write_bytes(canonical_json_bytes(validation))
    red_team = {
        "state": "PASS",
        "open_high_critical": 0,
        "execution_evidence_sha256": sha256_bytes(execution_path.read_bytes()),
        "validation_report_sha256": sha256_bytes(validation_path.read_bytes()),
    }
    (evidence_root / "RED_TEAM_POST_RECONSTRUCTION.json").write_bytes(canonical_json_bytes(red_team))
    receipt = build_post_execution_receipt(request, repo_root=tmp_path, now=now, schema_path=OVERLAY / "schemas" / "field" / "w7tp_total_field_d8_review_request_v2.schema.json")
    receipt_schema = json.loads((OVERLAY / "schemas" / "field" / "w7tp_total_field_d8_review_receipt_v2.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(receipt_schema).iter_errors(receipt)) == []
    assert receipt["receipt_self_sha256"] == self_hash(receipt, "receipt_self_sha256")
    assert receipt["single_use_consumed"] is True
    assert receipt["no_live_effect"] is True
