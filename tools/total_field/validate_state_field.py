#!/usr/bin/env python3
"""Fail-closed validator for sanitized W7TP/8D ADI V2.3 observations.

This validator checks structure, strict boolean types, live file hashes, and
trusted producer bindings. It never issues D8 or authorizes an effectful action.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "w7tp-8d-adi-v23-verification/1.0"
EXPECTED_DIMENSIONS = [
    "Intent",
    "State",
    "Coordinate",
    "Evidence",
    "Execution/Policy",
    "Generative State Transmission",
    "Risk/Isolation",
    "Envelope/Authority",
]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HEAD_RE = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_READONLY_EFFECT_KEYWORDS = ("DEPLOY", "WRITE", "MUTATE", "COMMIT", "PUSH", "RESTART", "PROMOTE", "INSTALL")


def _get(doc: dict[str, Any], dotted: str, issues: list[str]) -> Any:
    value: Any = doc
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            issues.append(f"MISSING:{dotted}")
            return None
        value = value[part]
    return value


def _expect(doc: dict[str, Any], dotted: str, expected: Any, issues: list[str]) -> None:
    value = _get(doc, dotted, issues)
    if value is None:
        return
    if isinstance(expected, bool):
        if not isinstance(value, bool) or value is not expected:
            issues.append(f"MISMATCH:{dotted}")
        return
    if type(value) is not type(expected) or value != expected:
        issues.append(f"MISMATCH:{dotted}")


def _expect_sha(doc: dict[str, Any], dotted: str, issues: list[str]) -> Any:
    value = _get(doc, dotted, issues)
    if value is not None and (not isinstance(value, str) or not SHA256_RE.fullmatch(value)):
        issues.append(f"INVALID_SHA256:{dotted}")
    return value


def _parse_time(value: Any, issues: list[str]) -> dt.datetime | None:
    if not isinstance(value, str):
        issues.append("INVALID:observation.observed_at")
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        issues.append("INVALID:observation.observed_at")
        return None
    if parsed.tzinfo is None:
        issues.append("INVALID:observation.observed_at_timezone")
        return None
    return parsed.astimezone(dt.timezone.utc)


def classify(
    doc: dict[str, Any],
    *,
    now: dt.datetime | None = None,
    max_age_seconds: int = 900,
    verify_live_files: bool = False,
    repo_root: Path = Path("/home/taiji_admin/Taiji_Hub"),
) -> dict[str, Any]:
    issues: list[str] = []
    now_utc = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)

    _expect(doc, "schema_version", SCHEMA_VERSION, issues)
    _expect(doc, "observation.source_node", "taiji01", issues)
    _expect(doc, "observation.root", "/home/taiji_admin/Taiji_Hub", issues)
    _expect(doc, "observation.live_verified", True, issues)
    _expect(doc, "observation.core_paths_clean", True, issues)

    obs = doc.get("observation") if isinstance(doc.get("observation"), dict) else {}
    if "trusted_producer" in obs or verify_live_files:
        if obs.get("trusted_producer") is not True:
            issues.append("UNTRUSTED_PRODUCER:observation.trusted_producer")

    branch = _get(doc, "observation.branch", issues)
    if branch is not None and (not isinstance(branch, str) or not branch.strip()):
        issues.append("INVALID:observation.branch")
    head = _get(doc, "observation.head", issues)
    if head is not None and (not isinstance(head, str) or not HEAD_RE.fullmatch(head)):
        issues.append("INVALID:observation.head")
    observed_at = _parse_time(_get(doc, "observation.observed_at", issues), issues)
    if observed_at is not None:
        age = (now_utc - observed_at).total_seconds()
        if age > max_age_seconds:
            issues.append("STALE:observation.observed_at")
        if age < -300:
            issues.append("FUTURE:observation.observed_at")

    for pivot in ("pointer", "contract", "field", "authority"):
        base = f"canonical.{pivot}"
        _expect(doc, f"{base}.exists", True, issues)
        _expect(doc, f"{base}.tracked", True, issues)
        _expect(doc, f"{base}.git_status", "CLEAN", issues)
        _expect_sha(doc, f"{base}.sha256", issues)

    _expect(doc, "canonical.pointer.canonical_id", "W7TP_8D_ADI_V2_3", issues)
    _expect(doc, "canonical.pointer.version", "2.3", issues)
    _expect(doc, "canonical.pointer.state", "ACTIVE_CANONICAL", issues)
    _expect(doc, "canonical.contract.canonical_id", "W7TP_8D_ADI_V2_3", issues)
    _expect(doc, "canonical.contract.version", "2.3", issues)
    _expect(doc, "canonical.field.canonical_id", "W7TP_8D_ADI_V2_3", issues)
    _expect(doc, "canonical.field.version", "2.3", issues)
    _expect(doc, "canonical.field.state", "ACTIVE_TRUE8D_V23", issues)
    _expect(doc, "canonical.field.dimensions", EXPECTED_DIMENSIONS, issues)
    _expect(doc, "canonical.authority.state", "ACTIVE_TOTAL_FIELD_AUTHORITY", issues)
    _expect(doc, "canonical.authority.contract_state", "ACTIVE_FORMAL", issues)
    _expect(doc, "canonical.authority.formal_decision_authority", True, issues)
    _expect(doc, "canonical.authority.formal_seal_authority", True, issues)

    pointer_sha = _expect_sha(doc, "canonical.pointer.sha256", issues)
    contract_sha = _expect_sha(doc, "canonical.contract.sha256", issues)
    field_sha = _expect_sha(doc, "canonical.field.sha256", issues)
    authority_sha = _expect_sha(doc, "canonical.authority.sha256", issues)
    declared_contract_sha = _expect_sha(doc, "canonical.pointer.canonical_sha256", issues)
    if contract_sha and declared_contract_sha and contract_sha != declared_contract_sha:
        issues.append("BINDING:canonical_contract_sha256")

    receipt = _get(doc, "canonical.receipt", issues)
    if not isinstance(receipt, dict):
        if "MISSING:canonical.receipt" not in issues:
            issues.append("INVALID:canonical.receipt")
    else:
        _expect(doc, "canonical.receipt.reference_exists", True, issues)
        _expect(doc, "canonical.receipt.referenced_by_active_field", True, issues)
        _expect(doc, "canonical.receipt.exists", True, issues)
        _expect(doc, "canonical.receipt.tracked", True, issues)
        _expect(doc, "canonical.receipt.git_status", "CLEAN", issues)
        if receipt.get("exists") is True:
            _expect_sha(doc, "canonical.receipt.sha256", issues)
            _expect(doc, "canonical.receipt.state", "ACTIVATED", issues)
            _expect(doc, "canonical.receipt.loaded_canonical_id", "W7TP_8D_ADI_V2_3", issues)
            _expect(doc, "canonical.receipt.loaded_version", "2.3", issues)
            _expect(doc, "canonical.receipt.completion_mode", "CURRENT_FIELD_AFTER_ACTIVATION", issues)
            receipt_pointer_sha = _expect_sha(doc, "canonical.receipt.pointer_postimage_sha256", issues)
            receipt_field_sha = _expect_sha(doc, "canonical.receipt.field_postimage_sha256", issues)
            receipt_authority_sha = _expect_sha(doc, "canonical.receipt.authority_postimage_sha256", issues)
            if pointer_sha and receipt_pointer_sha and pointer_sha != receipt_pointer_sha:
                issues.append("BINDING:pointer_postimage_sha256")
            if field_sha and receipt_field_sha and field_sha != receipt_field_sha:
                issues.append("BINDING:field_postimage_sha256")
            if authority_sha and receipt_authority_sha and authority_sha != receipt_authority_sha:
                issues.append("BINDING:authority_postimage_sha256")

    field_receipt_ref = _get(doc, "canonical.field.activation_receipt_ref", issues)
    receipt_path = _get(doc, "canonical.receipt.path", issues)
    if not field_receipt_ref or not receipt_path:
        issues.append("MISSING:canonical.receipt.binding_path")
    elif field_receipt_ref != receipt_path:
        issues.append("BINDING:active_field_receipt_ref")

    if verify_live_files:
        for pivot in ("pointer", "contract", "field", "authority", "receipt"):
            rel_p = _get(doc, f"canonical.{pivot}.path", issues)
            decl_sha = _get(doc, f"canonical.{pivot}.sha256", issues)
            if isinstance(rel_p, str) and isinstance(decl_sha, str):
                fp = (repo_root / rel_p).resolve()
                if not fp.is_file():
                    issues.append(f"LIVE_FILE_MISSING:canonical.{pivot}")
                else:
                    actual_sha = hashlib.sha256(fp.read_bytes()).hexdigest()
                    if actual_sha != decl_sha:
                        issues.append(f"LIVE_SHA_MISMATCH:canonical.{pivot}")

    mode = _get(doc, "request.mode", issues)
    effect = _get(doc, "request.effect", issues)
    if mode not in {"READ_ONLY", "CANDIDATE_BUILD", "EFFECTFUL"}:
        issues.append("INVALID:request.mode")
    if not isinstance(effect, str) or not effect.strip():
        issues.append("INVALID:request.effect")
    elif mode == "READ_ONLY":
        upper_eff = effect.strip().upper()
        if any(k in upper_eff for k in FORBIDDEN_READONLY_EFFECT_KEYWORDS):
            issues.append("FORBIDDEN_EFFECT_IN_READ_ONLY:request.effect")

    if issues:
        decision = "HOLD_CONTRACT_OR_EVIDENCE_INVALID"
        authority = "NOT_GRANTED"
    elif mode == "EFFECTFUL":
        decision = "HOLD_D8_AUTHORITY_REQUIRED"
        authority = "EXTERNAL_TAIJI01_RESOLUTION_REQUIRED"
    elif mode == "CANDIDATE_BUILD":
        decision = "CANDIDATE_ONLY"
        authority = "NOT_GRANTED"
    else:
        decision = "PASS_READ_ONLY"
        authority = "NOT_APPLICABLE_READ_ONLY"

    return {
        "schema_version": "w7tp-8d-adi-v23-verification-result/1.0",
        "contract_validation": "PASS" if not issues else "HOLD",
        "decision": decision,
        "authority": authority,
        "issues": sorted(set(issues)),
        "plugin_can_self_authorize": False,
        "contains_member_plaintext": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Sanitized observation JSON path, or - for stdin")
    parser.add_argument("--max-age-seconds", type=int, default=900)
    args = parser.parse_args(argv)

    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        doc = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"decision": "HOLD_INPUT_INVALID", "error": type(exc).__name__}))
        return 2

    result = classify(doc, max_age_seconds=args.max_age_seconds)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["decision"] in {"PASS_READ_ONLY", "CANDIDATE_ONLY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
