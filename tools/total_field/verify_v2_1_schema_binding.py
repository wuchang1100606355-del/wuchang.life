#!/usr/bin/env python3
"""Verify V2.1 schema provenance without mutating canonical state."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
except ImportError:  # pragma: no cover
    Draft202012Validator = None
    SchemaError = Exception


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POINTER_REL = Path("runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json")
DEFAULT_RECEIPT_REL = Path(
    "runtime/total_field/w7tp_canonical_v2_1/"
    "W7TP_CANONICAL_V2_1_SUCCESSOR_ACTIVATION_20260803T211241Z/receipts/"
    "W7TP_CANONICAL_V2_1_SUCCESSOR_ACTIVATION_RECEIPT.json"
)
DEFAULT_MANIFEST_REL = Path(
    "docs/total_field/"
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1_"
    "FOUNDER_LOCKED_SUCCESSOR_20260728.manifest.json"
)
DEFAULT_SCHEMA_REL = Path("schemas/w7tp_8d_multipurpose_packet_canonical_v2_1.schema.json")
DEFAULT_CANONICAL_SHA256 = "383aba5b7a9f5d0e948d9b43b83e7dd6b6ec9c27f025fb9069e83810f0ae870d"
DEFAULT_CANONICAL_PATH = (
    "docs/total_field/"
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1_"
    "FOUNDER_LOCKED_SUCCESSOR_20260728.md"
)
DEFAULT_PARENT_SHA256 = "a5281f229ced0943072cce373125be16f0d361b9352a71094ad5450a6022d5d0"
DEFAULT_PARENT_PATH = (
    "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"
)
DEFAULT_CANONICAL_ID = "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1"
BOUNDED_EVIDENCE_DIRS = (
    Path("runtime/total_field/master_index"),
    Path("runtime/total_field/w7tp_canonical_v2_1"),
    Path("docs/total_field"),
    Path("schemas"),
)


class BindingResolutionError(RuntimeError):
    """Raised when canonical serialization rules are violated."""


def normalize_content(value: Any, path: str = "$") -> Any:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise BindingResolutionError(f"NON_FINITE_NUMBER_BLOCKED:{path}")
        raise BindingResolutionError(f"FLOAT_CONTENT_REQUIRES_STRING:{path}")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                raise BindingResolutionError(f"NON_STRING_KEY_BLOCKED:{path}")
            key = unicodedata.normalize("NFC", raw_key)
            if key in normalized:
                raise BindingResolutionError(f"NORMALIZED_KEY_COLLISION:{path}.{key}")
            normalized[key] = normalize_content(raw_value, f"{path}.{key}")
        return normalized
    if isinstance(value, (list, tuple)):
        return [normalize_content(item, f"{path}[{index}]") for index, item in enumerate(value)]
    raise BindingResolutionError(f"UNSUPPORTED_CONTENT_TYPE:{path}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        normalize_content(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_from_stat(path: Path) -> str:
    return path.stat().st_mtime_ns and (
        Path
    ) and __import__("datetime").datetime.fromtimestamp(  # pragma: no cover
        path.stat().st_mtime, tz=__import__("datetime").timezone.utc
    ).isoformat()


def run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )


def iter_text_files(root: Path, rel_dirs: Iterable[Path]) -> Iterable[Path]:
    for rel_dir in rel_dirs:
        directory = root / rel_dir
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file():
                yield path


def grep_hash_references(root: Path, hash_value: str) -> list[str]:
    references: list[str] = []
    for path in iter_text_files(root, BOUNDED_EVIDENCE_DIRS):
        try:
            for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                if hash_value in line:
                    references.append(f"{path.relative_to(root).as_posix()}:{line_number}")
        except OSError:
            continue
    return references


def machine_schema_validates(payload: dict[str, Any]) -> tuple[bool, str]:
    if payload.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        return False, "INVALID_META_SCHEMA"
    if Draft202012Validator is not None:
        try:
            Draft202012Validator.check_schema(payload)
        except SchemaError as exc:
            return False, f"SCHEMA_ERROR:{exc.__class__.__name__}"
    required_properties = payload.get("properties", {})
    canonical_binding = required_properties.get("canonical_binding", {}).get("properties", {})
    version_const = required_properties.get("version", {}).get("const")
    canonical_id_const = required_properties.get("canonical_id", {}).get("const")
    payload_hash_field = required_properties.get("envelope", {}).get("properties", {}).get(
        "payload_sha256", {}
    )
    canonical_hash_field = required_properties.get("envelope", {}).get("properties", {}).get(
        "canonical_json_sha256", {}
    )
    if version_const != "2.1":
        return False, "VERSION_NOT_V2_1"
    if canonical_id_const != DEFAULT_CANONICAL_ID:
        return False, "CANONICAL_ID_MISMATCH"
    if canonical_binding.get("canonical_sha256", {}).get("const") != DEFAULT_CANONICAL_SHA256:
        return False, "CANONICAL_SHA256_BINDING_MISMATCH"
    if canonical_binding.get("canonical_path", {}).get("const") != DEFAULT_CANONICAL_PATH:
        return False, "CANONICAL_PATH_BINDING_MISMATCH"
    if canonical_binding.get("parent_sha256", {}).get("const") != DEFAULT_PARENT_SHA256:
        return False, "PARENT_SHA256_MISMATCH"
    if canonical_binding.get("parent_path", {}).get("const") != DEFAULT_PARENT_PATH:
        return False, "PARENT_PATH_MISMATCH"
    if payload_hash_field.get("pattern") != "^[0-9a-f]{64}$":
        return False, "PAYLOAD_HASH_CONTRACT_MISSING"
    if canonical_hash_field.get("pattern") != "^[0-9a-f]{64}$":
        return False, "CANONICAL_HASH_CONTRACT_MISSING"
    return serialization_contract_valid(), "PASS"


def serialization_contract_valid() -> bool:
    normalized = canonical_json({"e\u0301": {"value": "A"}})
    if normalized != '{"é":{"value":"A"}}':
        return False
    try:
        canonical_json({"value": 1.25})
    except BindingResolutionError:
        return True
    return False


def git_schema_artifact(
    repo_root: Path,
    schema_rel: Path,
    expected_sha256: str,
) -> dict[str, str] | None:
    history = run_git(repo_root, "log", "--format=%H %cI", "--", schema_rel.as_posix())
    if history.returncode != 0:
        return None
    for line in history.stdout.decode("utf-8").splitlines():
        commit, committed_at = line.split(" ", 1)
        show_result = run_git(repo_root, "show", f"{commit}:{schema_rel.as_posix()}")
        if show_result.returncode != 0:
            continue
        digest = hashlib.sha256(show_result.stdout).hexdigest()
        if digest != expected_sha256:
            continue
        ls_tree = run_git(repo_root, "ls-tree", commit, schema_rel.as_posix())
        if ls_tree.returncode != 0:
            continue
        object_blob = ls_tree.stdout.decode("utf-8").strip().split()[2]
        return {
            "commit": commit,
            "committed_at": committed_at,
            "blob": object_blob,
            "path": schema_rel.as_posix(),
            "sha256": digest,
        }
    return None


def current_schema_lineage(repo_root: Path, schema_rel: Path, current_sha256: str) -> dict[str, Any]:
    path = repo_root / schema_rel
    status_result = run_git(repo_root, "status", "--short", "--", schema_rel.as_posix())
    head_history = run_git(repo_root, "log", "--format=%H %cI %s", "--", schema_rel.as_posix())
    head_line = head_history.stdout.decode("utf-8").splitlines()[0] if head_history.stdout else ""
    references = grep_hash_references(repo_root, current_sha256)
    status = "UNSEALED"
    if references:
        if any("ACTIVE_W7TP_CANONICAL_POINTER" in ref or "RECEIPT" in ref for ref in references):
            status = "SEALED_BY_SUCCESSOR_EVIDENCE"
        else:
            status = "REFERENCED_NON_AUTHORITATIVE"
    elif status_result.stdout.strip():
        status = "UNSEALED_DRIFT"
    return {
        "path": schema_rel.as_posix(),
        "sha256": current_sha256,
        "mtime_utc": __import__("datetime").datetime.fromtimestamp(
            path.stat().st_mtime,
            tz=__import__("datetime").timezone.utc,
        ).isoformat(),
        "git_status": status_result.stdout.decode("utf-8").strip() or "CLEAN",
        "head_history": head_line or "NONE",
        "hash_references": references,
        "status": status,
    }


def receipt_consistent(pointer: dict[str, Any], receipt: dict[str, Any]) -> bool:
    target = receipt.get("target", {})
    validation = receipt.get("validation", {})
    return (
        receipt.get("state") == "PASS_CANONICAL_SUCCESSOR_ACTIVATED_APPEND_ONLY"
        and target.get("successor_path") == pointer.get("canonical_path")
        and target.get("successor_sha256") == pointer.get("canonical_sha256")
        and target.get("active_pointer_path") == DEFAULT_POINTER_REL.as_posix()
        and validation.get("pointer_points_to_successor") is True
        and validation.get("pointer_object_sha256_match") is True
    )


def manifest_consistent(pointer: dict[str, Any], manifest: dict[str, Any]) -> bool:
    successor = manifest.get("successor_canonical", {})
    source = manifest.get("source_canonical", {})
    return (
        manifest.get("state") == "APPEND_ONLY_CANONICAL_SUCCESSOR_NOT_ACTIVATED"
        and successor.get("path") == pointer.get("canonical_path")
        and successor.get("sha256") == pointer.get("canonical_sha256")
        and source.get("unchanged") is True
        and manifest.get("adi_binding_receipt", {}).get("binding_verification") == "PASS"
    )


def resolve_schema_binding(
    repo_root: Path,
    *,
    pointer_rel: Path = DEFAULT_POINTER_REL,
    receipt_rel: Path = DEFAULT_RECEIPT_REL,
    manifest_rel: Path = DEFAULT_MANIFEST_REL,
    schema_rel: Path = DEFAULT_SCHEMA_REL,
) -> dict[str, Any]:
    pointer = load_json(repo_root / pointer_rel)
    receipt = load_json(repo_root / receipt_rel)
    manifest = load_json(repo_root / manifest_rel)
    schema_path = repo_root / schema_rel
    current_schema = load_json(schema_path)
    current_sha256 = sha256_file(schema_path)
    pointer_schema_sha256 = pointer.get("machine_schema_sha256", "UNRESOLVED")
    receipt_schema_sha256 = pointer_schema_sha256 if receipt_consistent(pointer, receipt) else "UNRESOLVED"
    current_valid, current_validation_reason = machine_schema_validates(current_schema)
    promoted_artifact = git_schema_artifact(repo_root, schema_rel, pointer_schema_sha256)
    current_lineage = current_schema_lineage(repo_root, schema_rel, current_sha256)
    promoted_payload_valid = False
    promoted_payload_reason = "PROMOTED_SCHEMA_ARTIFACT_NOT_RESOLVED"
    if promoted_artifact is not None:
        show_result = run_git(
            repo_root,
            "show",
            f"{promoted_artifact['commit']}:{schema_rel.as_posix()}",
        )
        promoted_payload = json.loads(show_result.stdout.decode("utf-8"))
        if isinstance(promoted_payload, dict):
            promoted_payload_valid, promoted_payload_reason = machine_schema_validates(promoted_payload)

    current_has_independent_receipt = (
        current_sha256 != pointer_schema_sha256
        and any(
            "ACTIVE_W7TP_CANONICAL_POINTER" in ref or "RECEIPT" in ref
            for ref in current_lineage["hash_references"]
        )
    )

    result: dict[str, Any] = {
        "canonical_sha256": pointer.get("canonical_sha256"),
        "pointer_schema_sha256": pointer_schema_sha256,
        "promotion_receipt_schema_sha256": receipt_schema_sha256,
        "current_schema_sha256": current_sha256,
        "authoritative_schema_sha256": "NONE",
        "promoted_schema_artifact": "NONE",
        "current_schema_lineage": current_lineage,
        "schema_validation": "PASS" if current_valid else "HOLD",
        "schema_validation_reason": current_validation_reason,
        "repair_direction": "NONE",
        "state": "SYSTEM_VALIDITY_HOLD",
        "hold_code": "PROMOTED_SCHEMA_ARTIFACT_NOT_RESOLVED",
    }

    if not receipt_consistent(pointer, receipt) or not manifest_consistent(pointer, manifest):
        result["hold_code"] = "POINTER_RECEIPT_OR_MANIFEST_MISMATCH"
        return result

    if current_has_independent_receipt and current_valid:
        result["state"] = "PASS_CURRENT_SCHEMA_SUCCESSOR_PROVEN"
        result["authoritative_schema_sha256"] = current_sha256
        result["promoted_schema_artifact"] = "CURRENT_SCHEMA_RECEIPT_BOUND"
        result["repair_direction"] = "CREATE_APPEND_ONLY_POINTER_SUCCESSOR_FROM_EXISTING_RECEIPT"
        return result

    if promoted_artifact is None:
        return result

    if not promoted_payload_valid:
        result["hold_code"] = promoted_payload_reason
        return result

    result["state"] = "PASS_PROMOTED_SCHEMA_ARTIFACT_RESOLVED"
    result["authoritative_schema_sha256"] = pointer_schema_sha256
    result["promoted_schema_artifact"] = {
        "path": promoted_artifact["path"],
        "commit": promoted_artifact["commit"],
        "blob": promoted_artifact["blob"],
        "committed_at": promoted_artifact["committed_at"],
        "sha256": promoted_artifact["sha256"],
    }
    result["repair_direction"] = "CREATE_APPEND_ONLY_SUCCESSOR_BINDING_TO_PROMOTED_SCHEMA_BYTES"
    result["current_4ac_status"] = (
        current_lineage["status"]
        if current_sha256 != pointer_schema_sha256
        else "SEALED_ACTIVE"
    )
    result.pop("hold_code", None)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--pointer-rel", default=DEFAULT_POINTER_REL.as_posix())
    parser.add_argument("--receipt-rel", default=DEFAULT_RECEIPT_REL.as_posix())
    parser.add_argument("--manifest-rel", default=DEFAULT_MANIFEST_REL.as_posix())
    parser.add_argument("--schema-rel", default=DEFAULT_SCHEMA_REL.as_posix())
    args = parser.parse_args()

    result = resolve_schema_binding(
        Path(args.repo_root),
        pointer_rel=Path(args.pointer_rel),
        receipt_rel=Path(args.receipt_rel),
        manifest_rel=Path(args.manifest_rel),
        schema_rel=Path(args.schema_rel),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["state"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
