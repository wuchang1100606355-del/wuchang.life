from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


OVERLAY = Path(__file__).resolve().parents[2]
TOOLS = OVERLAY / "tools" / "total_field"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_reconstruct_isolated_v2_contract import resign, valid_request  # noqa: E402
from w7tp_reconstruct_isolated_contract import canonical_json_bytes, sha256_bytes  # noqa: E402
from w7tp_reconstruct_isolated_reviewer import review_request  # noqa: E402
from w7tp_reconstruct_isolated_runner_gate import validate_runner_gate  # noqa: E402
from w7tp_reconstruct_isolated_validator import ReconstructIsolatedValidationError  # noqa: E402


SCHEMA = OVERLAY / "schemas" / "field" / "w7tp_total_field_d8_review_request_v2.schema.json"


def write_authority(repo: Path, request: dict) -> None:
    pointer = {
        "node_id": "taiji01",
        "state": "ACTIVE_TOTAL_FIELD_AUTHORITY",
        "contract_state": "ACTIVE_FORMAL",
        "formal_decision_authority": True,
        "allowed_effects": ["AUTHORIZE_RECONSTRUCT_ISOLATED_REVIEW_ONLY"],
    }
    founder = {
        "state": "FOUNDER_AUTHORIZATION_APPROVED",
        "authorized_effect": "AUTHORIZE_RECONSTRUCT_ISOLATED_REVIEW_ONLY",
        "target_node": "taiji01",
        "target_field_snapshot_sha256": request["target"]["field_snapshot_sha256"],
        "target_base_state_sha256": request["target"]["base_state_sha256"],
        "target_successor_canonical_sha256": request["target"]["canonical_sha256"],
        "minimum_generative_delta_sha256": request["delta"]["sha256"],
        "exact_workspace": request["workspace"]["root"],
        "exact_targets": request["exact_targets"],
        "authorized_steps": request["authorized_steps"],
        "maximum_effect": request["maximum_effect"],
        "single_use": True,
        "created_at": "2026-08-21T18:00:00Z",
        "expires_at": "2026-08-21T18:30:00Z",
    }
    pointer_path = repo / request["authority"]["pointer_ref"]
    founder_path = repo / request["authority"]["founder_authorization_ref"]
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    founder_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_bytes(canonical_json_bytes(pointer))
    founder_path.write_bytes(canonical_json_bytes(founder))
    request["authority"]["pointer_sha256"] = sha256_bytes(pointer_path.read_bytes())
    request["authority"]["founder_authorization_sha256"] = sha256_bytes(founder_path.read_bytes())
    resign(request)


def test_reviewer_reuses_authority_and_gate_without_execution(tmp_path: Path) -> None:
    request, now = valid_request()
    write_authority(tmp_path, request)
    decision, receipt, evidence = review_request(request, repo_root=tmp_path, now=now, schema_path=SCHEMA)
    assert decision["decision"] == "ALLOW"
    assert receipt["final_decision"] == "ALLOW"
    assert evidence["side_effects_executed"] is False
    assert validate_runner_gate(decision, request, receipt, now=now, repo_root=tmp_path, schema_path=SCHEMA)["gate"] == "ALLOW"


def test_wrong_founder_effect_denies(tmp_path: Path) -> None:
    request, now = valid_request()
    write_authority(tmp_path, request)
    path = tmp_path / request["authority"]["founder_authorization_ref"]
    founder = json.loads(path.read_text(encoding="utf-8"))
    founder["authorized_effect"] = "AUTHORIZE_OTHER_EFFECT"
    path.write_bytes(canonical_json_bytes(founder))
    request["authority"]["founder_authorization_sha256"] = sha256_bytes(path.read_bytes())
    resign(request)
    with pytest.raises(ReconstructIsolatedValidationError):
        review_request(request, repo_root=tmp_path, now=now, schema_path=SCHEMA)


def test_authority_hash_mismatch_denies(tmp_path: Path) -> None:
    request, now = valid_request()
    write_authority(tmp_path, request)
    request["authority"]["pointer_sha256"] = "f" * 64
    resign(request)
    with pytest.raises(ReconstructIsolatedValidationError):
        review_request(request, repo_root=tmp_path, now=now, schema_path=SCHEMA)
