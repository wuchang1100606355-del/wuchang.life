from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


OVERLAY = Path(__file__).resolve().parents[2]
TOOLS = OVERLAY / "tools" / "total_field"
sys.path.insert(0, str(TOOLS))

from w7tp_reconstruct_isolated_validator import ReconstructIsolatedValidationError, validate_request  # noqa: E402


SCHEMA = OVERLAY / "schemas" / "field" / "w7tp_total_field_d8_review_request_v2.schema.json"


def test_v1_coordinates_are_absent_from_overlay() -> None:
    assert not (OVERLAY / "schemas" / "field" / "w7tp_total_field_d8_review_request_v1.schema.json").exists()
    assert not (OVERLAY / "tools" / "total_field" / "w7tp_d8_reviewer_entrypoint.py").exists()


@pytest.mark.parametrize(
    "legacy_action",
    [
        "ALLOW_P2_ISOLATED_CANARY_EXECUTION_ONLY",
        "ALLOW_NO_NETWORK_OFFLINE_CANARY_IMAGE_BUILD_ONLY",
    ],
)
def test_legacy_v1_requests_are_not_auto_upgraded(legacy_action: str, tmp_path: Path) -> None:
    legacy = {
        "schema_version": "W7TP-D8-REVIEW-REQUEST/1.0",
        "packet_type": "D8_REVIEW_REQUEST",
        "requested_decision": legacy_action,
        "only_request": legacy_action,
    }
    with pytest.raises(ReconstructIsolatedValidationError):
        validate_request(
            legacy,
            now=datetime(2026, 8, 21, 18, 1, tzinfo=timezone.utc),
            repo_root=tmp_path,
            schema_path=SCHEMA,
        )


def test_v2_contract_has_no_import_or_write_to_v1() -> None:
    for path in (OVERLAY / "tools" / "total_field").glob("w7tp_reconstruct_isolated_*.py"):
        text = path.read_text(encoding="utf-8")
        assert "from w7tp_d8_reviewer_entrypoint import" not in text
        assert "w7tp_total_field_d8_review_request_v1.schema.json\").write" not in text
