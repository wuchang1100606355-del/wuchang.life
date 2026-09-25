from __future__ import annotations

import sys
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

import pytest


OVERLAY = Path(__file__).resolve().parents[2]
TOOLS = OVERLAY / "tools" / "total_field"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_reconstruct_isolated_v2_contract import resign, valid_request  # noqa: E402
from w7tp_reconstruct_isolated_validator import (  # noqa: E402
    ReconstructIsolatedValidationError,
    validate_request,
)


SCHEMA = OVERLAY / "schemas" / "field" / "w7tp_total_field_d8_review_request_v2.schema.json"


def assert_denied(request: dict, now, tmp_path: Path) -> None:
    with pytest.raises(ReconstructIsolatedValidationError):
        validate_request(request, now=now, repo_root=tmp_path, schema_path=SCHEMA)


def test_valid_exact_bounded_v2_request_passes(tmp_path: Path) -> None:
    request, now = valid_request()
    assert validate_request(request, now=now, repo_root=tmp_path, schema_path=SCHEMA) is request


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("target", "node"), "MSI"),
        (("target", "field_snapshot_sha256"), "1" * 64),
        (("target", "base_state_sha256"), "2" * 64),
        (("target", "canonical_sha256"), "3" * 64),
        (("delta", "sha256"), "4" * 64),
        (("workspace", "db_access"), True),
        (("workspace", "state_store_access"), True),
        (("reconstruction_base", "new_adapter_required"), True),
        (("forbidden_effects", "LIVE_9107_MUTATION"), True),
        (("forbidden_effects", "LIVE_REBIND"), True),
        (("forbidden_effects", "DB_WRITE"), True),
        (("forbidden_effects", "LIVE_STATE_STORE_WRITE"), True),
        (("forbidden_effects", "SERVICE_RESTART"), True),
        (("forbidden_effects", "DEPLOYMENT"), True),
        (("forbidden_effects", "CANONICAL_MUTATION"), True),
        (("forbidden_effects", "POINTER_MUTATION"), True),
        (("forbidden_effects", "PROMOTION"), True),
        (("forbidden_effects", "ACTIVATION"), True),
        (("forbidden_effects", "LANDING"), True),
        (("forbidden_effects", "9110_CREATION"), True),
        (("forbidden_effects", "UNDECLARED_ADAPTER_CREATION"), True),
    ],
)
def test_bound_or_forbidden_mutation_is_denied(path: tuple[str, str], value, tmp_path: Path) -> None:
    request, now = valid_request()
    request[path[0]][path[1]] = value
    resign(request)
    assert_denied(request, now, tmp_path)


@pytest.mark.parametrize(
    "root",
    [
        "/tmp/absolute",
        "runtime/isolated/../escape",
        "runtime/live/9107",
        "schemas/field/canonical",
        "runtime/isolated/live/consumer",
    ],
)
def test_workspace_escape_or_live_overlap_is_denied(root: str, tmp_path: Path) -> None:
    request, now = valid_request()
    request["workspace"]["root"] = root
    request["exact_targets"] = [f"{root}/TARGET_SUCCESSOR_SHADOW_BINDING_CANDIDATE.json", f"{root}/W7TP_9107_RECONSTRUCTION_CALL_EDGE_BINDING_CANDIDATE.json"]
    request["replay_root"] = f"{root}/evidence"
    resign(request)
    assert_denied(request, now, tmp_path)


def test_exact_target_outside_workspace_is_denied(tmp_path: Path) -> None:
    request, now = valid_request()
    request["exact_targets"][1] = "tools/live_9107_config.json"
    resign(request)
    assert_denied(request, now, tmp_path)


def test_symlink_escape_is_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request, now = valid_request("evil")
    original = Path.is_symlink

    def fake_is_symlink(path: Path) -> bool:
        return path.name == "evil" or original(path)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)
    assert_denied(request, now, tmp_path)


def test_expired_request_is_denied(tmp_path: Path) -> None:
    request, now = valid_request()
    assert_denied(request, now + timedelta(hours=1), tmp_path)


def test_ttl_above_reused_3600_second_bound_is_denied(tmp_path: Path) -> None:
    request, now = valid_request()
    request["expires_at"] = (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    resign(request)
    assert_denied(request, now, tmp_path)


def test_scope_hash_mismatch_is_denied(tmp_path: Path) -> None:
    request, now = valid_request()
    request["scope_sha256"] = "f" * 64
    request["request_self_sha256"] = "0" * 64
    request["request_self_sha256"] = __import__("w7tp_reconstruct_isolated_contract").self_hash(request, "request_self_sha256")
    assert_denied(request, now, tmp_path)


def test_additional_properties_injection_is_denied(tmp_path: Path) -> None:
    request, now = valid_request()
    request["execution_authority"] = True
    request["request_self_sha256"] = __import__("w7tp_reconstruct_isolated_contract").self_hash(request, "request_self_sha256")
    assert_denied(request, now, tmp_path)
