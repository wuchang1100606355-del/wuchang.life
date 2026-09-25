#!/usr/bin/env python3
"""Candidate-only compatibility adapter for one combined identity static review.

This module verifies and normalizes two fixed evidence candidates, then submits
this adapter file itself to the existing Total Field static reviewer.  It does
not adjudicate schema identity, close runtime evidence, or grant authority.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.total_field import w7tp_static_review_entrypoint as native_reviewer


ADAPTER_VERSION = "w7tp-combined-identity-review-compat-adapter-candidate/1.0"
ADAPTER_STATE = "CANDIDATE_NOT_CANONICAL"
NATIVE_REVIEWER_REF = "tools/total_field/w7tp_static_review_entrypoint.py"
INPUT_BINDINGS = (
    (
        "W7TP_V2_1_SCHEMA_IDENTITY_EVIDENCE_CLOSURE_CANDIDATE.json",
        "93ec623056feae7f5bfd5c68cccb0a5dc840834acc3b133f8690c89b6de56d5d",
    ),
    (
        "XIAOJ_IDENTITY_PACKET_DEVICE_LOGIN_OPENWEBUI_CAPABILITY_ENVELOPE_CANDIDATE.json",
        "c08ef6da93862016813deac9383a75795cea548a888470aadd72a9bdd4402361",
    ),
)
NATIVE_THREE_OUTPUTS = frozenset(
    {
        "TOTAL_FIELD_STATIC_REVIEW_RESULT.json",
        "REVIEW_EVIDENCE.json",
        "SHA256_MANIFEST.json",
    }
)
FORMAL_PURPOSE = "W7TP_COMBINED_IDENTITY_REVIEW_ADAPTER_CANDIDATE_ONLY"
FORBIDDEN_OVERRIDE_KEYS = frozenset(
    {
        "activation",
        "active",
        "authority",
        "canonical_promotion",
        "db_write",
        "deploy",
        "final_decision",
        "runtime_authority",
        "schema_identity_decision",
    }
)


class AdapterBoundaryError(ValueError):
    """Fail-closed adapter validation error without decision authority."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AdapterBoundaryError(f"INVALID_JSON:{path}") from exc
    if not isinstance(value, dict):
        raise AdapterBoundaryError(f"OBJECT_REQUIRED:{path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def bound_repo_path(repo_root: Path, value: Path, label: str) -> Path:
    root = repo_root.resolve()
    candidate = value if value.is_absolute() else root / value
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AdapterBoundaryError(f"PATH_ESCAPE:{label}") from exc
    return resolved


def require(condition: bool, code: str) -> None:
    if not condition:
        raise AdapterBoundaryError(code)


def reject_authority_injection(value: Any, path: str = "$") -> None:
    """Reject any caller-supplied attempt to add decision or effect authority."""

    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in FORBIDDEN_OVERRIDE_KEYS:
                raise AdapterBoundaryError(f"AUTHORITY_INJECTION_REJECTED:{path}.{key}")
            reject_authority_injection(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_authority_injection(item, f"{path}[{index}]")


def verify_bound_inputs(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    loaded: list[dict[str, Any]] = []
    for relative, expected_sha256 in INPUT_BINDINGS:
        path = bound_repo_path(repo_root, Path(relative), relative)
        require(path.is_file(), f"BOUND_INPUT_MISSING:{relative}")
        require(sha256_file(path) == expected_sha256, f"BOUND_INPUT_SHA256_MISMATCH:{relative}")
        loaded.append(load_object(path))
    return loaded[0], loaded[1]


def normalize_inputs(repo_root: Path) -> dict[str, Any]:
    """Return a non-authoritative normalized view of the two exact candidates."""

    schema_evidence, capability_envelope = verify_bound_inputs(repo_root)
    recommendation = schema_evidence.get("recommendation")
    require(schema_evidence.get("state") == ADAPTER_STATE, "SCHEMA_EVIDENCE_NOT_CANDIDATE")
    require(
        recommendation
        in {
            "A_POINTER_SCHEMA_IDENTITY",
            "B_CURRENT_SCHEMA_PROMOTED",
            "C_UNRESOLVED",
        },
        "SCHEMA_RECOMMENDATION_VOCABULARY",
    )
    require(
        schema_evidence.get("recommendation_authority") == "CANDIDATE_ONLY",
        "SCHEMA_RECOMMENDATION_AUTHORITY_EXPANSION",
    )

    resource_limits = capability_envelope.get("execution_contract", {}).get("resource_limits", {})
    evidence_state = resource_limits.get("evidence_state", {})
    lifecycle = capability_envelope.get("lifecycle", {})
    quality_thresholds = capability_envelope.get("product_output_contract", {}).get(
        "quality_thresholds", []
    )
    prohibited_outputs = capability_envelope.get("product_output_contract", {}).get(
        "prohibited_outputs", []
    )
    require(
        capability_envelope.get("schema_version") == "w7tp-total-field-skill-manifest/1.0",
        "CAPABILITY_MANIFEST_SCHEMA_MISMATCH",
    )
    require(
        capability_envelope.get("manifest_state") == "CANDIDATE_FOR_TOTAL_FIELD_REVIEW",
        "CAPABILITY_MANIFEST_NOT_CANDIDATE",
    )
    require(resource_limits.get("current_operation_effect") == "E2", "CURRENT_EFFECT_NOT_E2")
    require(evidence_state.get("runtime_evidence_closed") is False, "RUNTIME_EVIDENCE_NOT_OPEN")
    require(
        evidence_state.get("w7tp_schema_identity") == "PENDING_TOTAL_FIELD_DECISION",
        "SCHEMA_IDENTITY_PREJUDGED",
    )
    require(
        lifecycle.get("state") == "CANDIDATE_FOR_TOTAL_FIELD_REVIEW",
        "CAPABILITY_LIFECYCLE_NOT_CANDIDATE",
    )
    require(lifecycle.get("total_field_decision_ref") is None, "TOTAL_FIELD_DECISION_ALREADY_INJECTED")
    require("OPENWEBUI_AUTHORITY_NONE" in quality_thresholds, "OPENWEBUI_AUTHORITY_NONE_MISSING")
    require(
        "FORMAL_TOTAL_FIELD_DECISION_OR_PASS" in prohibited_outputs,
        "FORMAL_DECISION_PROHIBITION_MISSING",
    )

    return {
        "adapter_version": ADAPTER_VERSION,
        "state": ADAPTER_STATE,
        "input_hash_binding": "VERIFIED",
        "schema_identity": {
            "recommendation": recommendation,
            "recommendation_class": "NON_AUTHORITY_EVIDENCE_ONLY",
            "decision": None,
        },
        "capability_envelope": {
            "current_operation_effect": "E2",
            "runtime_evidence_closed": False,
            "active": False,
            "openwebui_authority": "NONE",
        },
        "formal_decision": None,
        "decision_authority": "NATIVE_REVIEWER_ONLY",
    }


def self_test(repo_root: Path) -> dict[str, Any]:
    normalized = normalize_inputs(repo_root)
    require(normalized["schema_identity"]["decision"] is None, "RECOMMENDATION_BECAME_DECISION")
    require(normalized["capability_envelope"]["active"] is False, "RUNTIME_BECAME_ACTIVE")

    injection_rejected = False
    try:
        reject_authority_injection({"final_decision": "PASS"})
    except AdapterBoundaryError:
        injection_rejected = True
    require(injection_rejected, "AUTHORITY_INJECTION_NOT_REJECTED")

    reviewer_path = bound_repo_path(repo_root, Path(NATIVE_REVIEWER_REF), "native_reviewer")
    require(reviewer_path.is_file(), "NATIVE_REVIEWER_MISSING")
    require(callable(native_reviewer.review_once), "NATIVE_REVIEWER_NOT_CALLABLE")
    reviewer_source = reviewer_path.read_text(encoding="utf-8")
    for output_name in NATIVE_THREE_OUTPUTS:
        require(output_name in reviewer_source, f"NATIVE_OUTPUT_CONTRACT_MISSING:{output_name}")

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"), filename=__file__)
    local_functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    require("review_once" not in local_functions, "SECOND_REVIEW_CORE_DETECTED")
    require("decision_state" not in local_functions, "SECOND_REVIEW_CORE_DETECTED")

    return {
        "state": ADAPTER_STATE,
        "self_test": "PASS",
        "checks": {
            "dual_input_sha_binding": "PASS",
            "schema_recommendation_not_decision": "PASS",
            "runtime_false_not_active": "PASS",
            "authority_injection_rejected": "PASS",
            "native_three_output_contract": "PASS",
            "second_review_core_created": False,
        },
        "formal_decision": None,
    }


def build_native_package(
    repo_root: Path,
    run_id: str,
    intake_dir: Path,
    adapter_sha256: str,
) -> tuple[Path, Path, Path]:
    """Build transient native request artifacts bound only to this adapter."""

    adapter_path = Path(__file__).resolve()
    adapter_relative = adapter_path.relative_to(repo_root.resolve()).as_posix()
    manifest_path = intake_dir / "SOURCE_SHA256_MANIFEST.json"
    request_path = intake_dir / "TOTAL_FIELD_STATIC_REVIEW_REQUEST.json"
    seal_path = intake_dir / "OWNER_SEAL.json"
    created_at = native_reviewer.utc_now()
    request_expires_at = created_at + timedelta(minutes=30)
    seal_expires_at = created_at + timedelta(minutes=15)
    single_use_id = f"single-use:{run_id}:{adapter_sha256[:16]}"

    manifest = {
        "schema_version": native_reviewer.SOURCE_MANIFEST_SCHEMA_VERSION,
        "packet_type": "TOTAL_FIELD_STATIC_SOURCE_MANIFEST",
        "run_id": run_id,
        "purpose": FORMAL_PURPOSE,
        "manifest_self_hash_excluded": True,
        "files": [
            {
                "path": adapter_relative,
                "sha256": adapter_sha256,
                "size_bytes": adapter_path.stat().st_size,
                "role": "combined_identity_review_compat_adapter_candidate",
            }
        ],
        "file_count": 1,
    }
    write_json(manifest_path, manifest)

    request = {
        "schema_version": native_reviewer.REQUEST_SCHEMA_VERSION,
        "packet_type": "TOTAL_FIELD_STATIC_REVIEW_REQUEST",
        "run_id": run_id,
        "packet_id": f"packet:{run_id}",
        "event_id": f"event:{run_id}",
        "created_at": native_reviewer.utc_text(created_at),
        "expires_at": native_reviewer.utc_text(request_expires_at),
        "state": "PENDING_TOTAL_FIELD_STATIC_REVIEW",
        "requested_decision": native_reviewer.DECISION_ACCEPT,
        "only_request": native_reviewer.DECISION_ACCEPT,
        "purpose": FORMAL_PURPOSE,
        "single_use": True,
        "single_use_id": single_use_id,
        "request_self_hash_algorithm": native_reviewer.REQUEST_SELF_HASH_ALGORITHM,
        "source_manifest_path": manifest_path.relative_to(repo_root).as_posix(),
        "source_manifest_sha256": sha256_file(manifest_path),
        "owner_seal_path": seal_path.relative_to(repo_root).as_posix(),
        "non_execution_assertions": {
            key: False for key in native_reviewer.NON_EXECUTION_FIELDS
        },
    }
    request["request_self_sha256"] = native_reviewer.sha256_bytes(
        native_reviewer.canonical_json_bytes(request)
    )
    write_json(request_path, request)

    seal = {
        "schema_version": native_reviewer.OWNER_SEAL_SCHEMA_VERSION,
        "packet_type": "TOTAL_FIELD_STATIC_REVIEW_OWNER_SEAL",
        "seal_id": f"owner-seal:{run_id}:{adapter_sha256[:16]}",
        "run_id": run_id,
        "purpose": FORMAL_PURPOSE,
        "complete_manifest_sha256": sha256_file(manifest_path),
        "review_request_sha256": sha256_file(request_path),
        "single_use": True,
        "single_use_id": single_use_id,
        "issued_at": native_reviewer.utc_text(created_at),
        "expires_at": native_reviewer.utc_text(seal_expires_at),
        "founder_authority_ref": native_reviewer.FOUNDER_AUTHORITY_REF,
        "authorization": native_reviewer.OWNER_AUTHORIZATION,
        "owner_seal_self_hash_algorithm": native_reviewer.OWNER_SEAL_SELF_HASH_ALGORITHM,
        "non_execution_assertions": {
            key: False for key in native_reviewer.NON_EXECUTION_FIELDS
        },
    }
    seal["owner_seal_self_sha256"] = native_reviewer.sha256_bytes(
        native_reviewer.canonical_json_bytes(seal)
    )
    write_json(seal_path, seal)
    return request_path, manifest_path, seal_path


def submit_once(repo_root: Path, run_id: str, output_dir: Path) -> dict[str, Any]:
    """Submit exactly once through the native reviewer; return its response."""

    self_test(repo_root)
    output_dir = bound_repo_path(repo_root, output_dir, "output_dir")
    adapter_sha256 = sha256_file(Path(__file__).resolve())
    with tempfile.TemporaryDirectory(
        prefix=".w7tp-combined-review-intake-", dir=repo_root
    ) as temporary:
        intake_dir = Path(temporary)
        request_path, manifest_path, seal_path = build_native_package(
            repo_root, run_id, intake_dir, adapter_sha256
        )
        response = native_reviewer.review_once(
            request_path=request_path,
            manifest_path=manifest_path,
            owner_seal_path=seal_path,
            output_dir=output_dir,
            repo_root=repo_root,
            replay_root=output_dir.parent,
        )

    actual_outputs = {path.name for path in output_dir.iterdir() if path.is_file()}
    require(actual_outputs == NATIVE_THREE_OUTPUTS, "NATIVE_THREE_OUTPUT_CONTRACT_CHANGED")
    return response


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--self-test", action="store_true")
    action.add_argument("--submit", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--run-id")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--founder-authorized-single-use", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        if args.self_test:
            print(json.dumps(self_test(repo_root), ensure_ascii=False, sort_keys=True))
            return 0
        require(args.founder_authorized_single_use, "FOUNDER_SINGLE_USE_AUTHORIZATION_REQUIRED")
        require(isinstance(args.run_id, str) and bool(args.run_id), "RUN_ID_REQUIRED")
        require(args.output_dir is not None, "OUTPUT_DIR_REQUIRED")
        response = submit_once(repo_root, args.run_id, args.output_dir)
        return 0 if response.get("final_decision") == native_reviewer.DECISION_ACCEPT else 2
    except (AdapterBoundaryError, FileExistsError, OSError) as exc:
        print(
            json.dumps(
                {"state": "HOLD_SKILL_DEFINITION", "error": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
