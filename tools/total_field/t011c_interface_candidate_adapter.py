"""T-011C interface projection for Chrome sidepanel and Codex task packets.

This adapter never invokes Codex and never executes browser actions. It only
projects a Total-Field-reviewed T-011B local-LLM candidate into display and
engineering-task candidate forms.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tools.w7tp_codex_task_adapter import (
    DEFAULT_FORBIDDEN_ACTIONS,
    DEFAULT_FORBIDDEN_FILES,
    DEFAULT_REQUIRED_OUTPUTS,
    DEFAULT_RISK_SCAN_COMMANDS,
    DEFAULT_VERIFY_COMMANDS,
    build_packet as build_codex_packet,
)


ROOT = Path(__file__).resolve().parents[2]
T011B_RETURN_SCHEMA = (
    ROOT / "schemas/field/w7tp_local_llm_candidate_return_v1.schema.json"
)
T011C_SCHEMA = (
    ROOT / "schemas/field/w7tp_t011c_interface_candidate_v1.schema.json"
)


class T011CInterfaceHold(RuntimeError):
    """Fail-closed interface candidate rejection."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise T011CInterfaceHold(code)


def _load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise T011CInterfaceHold(code) from exc
    _require(isinstance(value, dict), code)
    return value


def _validate(value: Mapping[str, Any], schema_path: Path, code: str) -> None:
    schema = _load_json(schema_path, code)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(dict(value)),
        key=lambda item: list(item.path),
    )
    if errors:
        raise T011CInterfaceHold(code)


def _allowed_files(values: Sequence[str]) -> list[str]:
    _require(
        isinstance(values, Sequence) and not isinstance(values, (str, bytes)),
        "HOLD_T011C_ALLOWED_FILES_REQUIRED",
    )
    result: list[str] = []
    for raw in values:
        value = str(raw).strip().replace("\\", "/")
        _require(
            value
            and not value.startswith("/")
            and not value.startswith("../")
            and "/../" not in value,
            "HOLD_T011C_ALLOWED_FILE_INVALID",
        )
        if value not in result:
            result.append(value)
    _require(bool(result), "HOLD_T011C_ALLOWED_FILES_REQUIRED")
    return result


def build_t011c_interface_candidate(
    *,
    t011b_candidate_return: Mapping[str, Any],
    total_field_return_receipt: Mapping[str, Any],
    allowed_files: Sequence[str],
    title: str = "T-011C local-LLM engineering handoff candidate",
) -> dict[str, Any]:
    """Build display-only Chrome view plus non-invoked Codex task packet."""
    _require(
        isinstance(t011b_candidate_return, Mapping),
        "HOLD_T011C_T011B_PACKET_REQUIRED",
    )
    packet = copy.deepcopy(dict(t011b_candidate_return))
    _validate(
        packet,
        T011B_RETURN_SCHEMA,
        "HOLD_T011C_T011B_PACKET_SCHEMA_INVALID",
    )
    _require(
        packet.get("state") == "CANDIDATE_READY"
        and packet.get("candidate_only") is True
        and packet.get("must_not_execute") is True
        and packet.get("requires_total_field_verify") is True,
        "HOLD_T011C_T011B_PACKET_NOT_REVIEWABLE",
    )


    _require(
        isinstance(total_field_return_receipt, Mapping),
        "HOLD_T011C_TOTAL_FIELD_RECEIPT_REQUIRED",
    )
    receipt = copy.deepcopy(dict(total_field_return_receipt))
    _require(
        receipt.get("state") == "PASS_T011B_TOTAL_FIELD_CANDIDATE_RETURN"
        and receipt.get("candidate_sha256") == packet.get("candidate_sha256")
        and receipt.get("final_decision") == "ALLOW"
        and receipt.get("fixed_point_status") == "REACHED"
        and receipt.get("candidate_execution_allowed") is False
        and receipt.get("candidate_text_submitted_to_total_field") is False
        and receipt.get("formal_effect_boundary") == "TAIJI01_TOTAL_FIELD",
        "HOLD_T011C_TOTAL_FIELD_RECEIPT_INVALID",
    )

    files = _allowed_files(allowed_files)
    candidate_text = str(packet.get("candidate_text") or "")
    _require(candidate_text != "", "HOLD_T011C_EMPTY_CANDIDATE")
    computed_candidate_sha = hashlib.sha256(
        candidate_text.encode("utf-8")
    ).hexdigest()
    _require(
        packet.get("candidate_sha256") == computed_candidate_sha
        and packet.get("candidate_ref")
        == "candidate:sha256:" + computed_candidate_sha,
        "HOLD_T011C_CANDIDATE_HASH_MISMATCH",
    )
    codex_packet = build_codex_packet(
        title=title,
        intent=candidate_text,
        allowed_files=files,
        forbidden_files=list(DEFAULT_FORBIDDEN_FILES),
        required_outputs=list(DEFAULT_REQUIRED_OUTPUTS),
        verify_commands=list(DEFAULT_VERIFY_COMMANDS),
        risk_scan_commands=list(DEFAULT_RISK_SCAN_COMMANDS),
    )
    _require(
        codex_packet.get("codex_authority") is False
        and codex_packet.get("candidate_only") is True,
        "HOLD_T011C_CODEX_AUTHORITY_DRIFT",
    )
    safety = codex_packet.get("safety_flags") or {}
    _require(
        safety.get("CODEX_AUTHORITY") is False
        and safety.get("AUTO_STAGE") is False
        and safety.get("AUTO_COMMIT") is False
        and safety.get("DEPLOY") is False
        and safety.get("SERVICE_RESTART") is False,
        "HOLD_T011C_CODEX_SAFETY_DRIFT",
    )


    output = {
        "schema_version": "w7tp.t011c-interface-candidate.v1",
        "state": "PASS_T011C_INTERFACE_CANDIDATE",
        "candidate_only": True,
        "runtime_effect": False,
        "chrome_view": {
            "state": "TOTAL_FIELD_REVIEWED_CANDIDATE",
            "display_only": True,
            "execution_allowed": False,
            "candidate_sha256": packet["candidate_sha256"],
            "candidate_text": candidate_text,
            "provider_ref": packet["provider_ref"],
            "model_ref": packet["model_ref"],
            "total_field_decision": "ALLOW",
            "allowed_user_actions": [
                "review_candidate",
                "copy_candidate",
            ],
        },
        "codex_task_packet_candidate": codex_packet,
        "codex_invocation_performed": False,
        "authority": {
            "model_authority": False,
            "codex_authority": False,
            "browser_authority": False,
            "formal_effect_boundary": "TAIJI01_TOTAL_FIELD",
        },
    }
    _validate(
        output,
        T011C_SCHEMA,
        "HOLD_T011C_INTERFACE_SCHEMA_INVALID",
    )
    return output


__all__ = [
    "T011CInterfaceHold",
    "build_t011c_interface_candidate",
]
