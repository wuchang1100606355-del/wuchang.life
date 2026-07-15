#!/usr/bin/env python3
"""Check and explicitly materialize the TFCT TRUE8D runtime candidate policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_DIR = (
    REPOSITORY_ROOT / "manifests" / "tfct_true8d_runtime_candidate_v0_1"
)
DEFAULT_RUNTIME_POLICY = (
    REPOSITORY_ROOT
    / "runtime"
    / "total_field"
    / "candidate"
    / "tfct_true8d_runtime_policy_v0_1.json"
)

_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "package_version",
        "status",
        "source_policy",
        "runtime_target",
        "policy_sha256",
        "materialization_mode",
        "canonical_promotion",
        "deploy",
        "restart",
    }
)
_MANIFEST_CONSTANTS = {
    "schema_version": "tfct_true8d_runtime_candidate_package_v0.1",
    "package_version": "v0.1",
    "status": "CANDIDATE",
    "source_policy": "policy.json",
    "runtime_target": (
        "runtime/total_field/candidate/"
        "tfct_true8d_runtime_policy_v0_1.json"
    ),
    "materialization_mode": "EXPLICIT_ONLY",
}


class PackageFailure(ValueError):
    """Represent one stable package validation failure."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        """Initialize the failure with a machine-stable reason code."""
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.detail = detail


@dataclass(frozen=True)
class CheckResult:
    """Describe the deterministic relationship between source and runtime policy."""

    status: str
    policy_sha256: str
    runtime_policy_sha256: str
    reason_code: str

    @property
    def canonical_equivalence(self) -> str:
        """Expose the overall package comparison as MATCH or MISMATCH."""
        return self.status

    @property
    def matched(self) -> bool:
        """Return whether the canonical source and runtime representations match."""
        return self.status == "MATCH"


@dataclass(frozen=True)
class MaterializeResult:
    """Describe a no-overwrite materialization attempt."""

    status: str
    target: Path
    policy_sha256: str
    reason_code: str

    @property
    def successful(self) -> bool:
        """Return whether the target was created or already equivalent."""
        return self.status in {"MATERIALIZED", "ALREADY_MATCH"}


def _pairs_to_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build an object while rejecting duplicate member names."""
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise PackageFailure("JSON_DUPLICATE_KEY", key)
        value[key] = item
    return value


def _reject_json_constant(value: str) -> Any:
    """Reject JSON extensions representing non-finite numeric values."""
    raise PackageFailure("JSON_NONFINITE_VALUE", value)


def _require_finite_numbers(value: Any) -> None:
    """Reject numeric overflow that the JSON decoder represents as infinity."""
    if isinstance(value, float) and not math.isfinite(value):
        raise PackageFailure("JSON_NONFINITE_VALUE")
    if isinstance(value, dict):
        for nested in value.values():
            _require_finite_numbers(nested)
    elif isinstance(value, list):
        for nested in value:
            _require_finite_numbers(nested)


def load_strict_json(path: str | Path) -> Any:
    """Load one UTF-8 JSON document with strict duplicate and number handling."""
    source = Path(path)
    try:
        raw = source.read_bytes()
    except FileNotFoundError as error:
        raise PackageFailure("JSON_FILE_NOT_FOUND", str(source)) from error
    except OSError as error:
        raise PackageFailure("JSON_FILE_READ_ERROR", str(source)) from error

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise PackageFailure("JSON_NOT_UTF8", str(source)) from error

    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_to_object,
            parse_constant=_reject_json_constant,
        )
        _require_finite_numbers(value)
        return value
    except PackageFailure:
        raise
    except (json.JSONDecodeError, RecursionError) as error:
        raise PackageFailure("INVALID_JSON", str(source)) from error


def canonical_json(value: Any) -> str:
    """Serialize a JSON value with the package's exact canonical settings."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except ValueError as error:
        raise PackageFailure("JSON_NONFINITE_VALUE") from error
    except (TypeError, RecursionError) as error:
        raise PackageFailure("JSON_NOT_CANONICALIZABLE") from error


def canonical_sha256(value: Any) -> str:
    """Return the lowercase SHA-256 digest of a canonical JSON value."""
    payload = canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_object(value: Any, reason_code: str) -> dict[str, Any]:
    """Require a parsed JSON root to be an object."""
    if not isinstance(value, dict):
        raise PackageFailure(reason_code)
    return value


def _validate_policy(value: Any, label: str) -> dict[str, Any]:
    """Validate the candidate lifecycle marker on one policy object."""
    policy = _require_object(value, f"{label}_POLICY_NOT_OBJECT")
    if policy.get("status") != "CANDIDATE":
        raise PackageFailure("POLICY_STATUS_NOT_CANDIDATE", label)
    return policy


def _validate_manifest(value: Any) -> dict[str, Any]:
    """Validate the closed candidate package manifest contract."""
    manifest = _require_object(value, "PACKAGE_MANIFEST_NOT_OBJECT")
    if frozenset(manifest) != _MANIFEST_FIELDS:
        raise PackageFailure("PACKAGE_MANIFEST_FIELDS_INVALID")
    for field, expected in _MANIFEST_CONSTANTS.items():
        if manifest.get(field) != expected:
            raise PackageFailure(f"PACKAGE_MANIFEST_{field.upper()}_INVALID")
    for field in ("canonical_promotion", "deploy", "restart"):
        if manifest.get(field) is not False:
            raise PackageFailure(f"PACKAGE_MANIFEST_{field.upper()}_INVALID")
    digest = manifest.get("policy_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise PackageFailure("PACKAGE_MANIFEST_POLICY_SHA256_INVALID")
    if any(character not in "0123456789abcdef" for character in digest):
        raise PackageFailure("PACKAGE_MANIFEST_POLICY_SHA256_INVALID")
    return manifest


def _read_source_package(
    package_dir: str | Path,
) -> tuple[dict[str, Any], str, bool]:
    """Read source policy and report whether its declared digest is current."""
    directory = Path(package_dir)
    manifest = _validate_manifest(load_strict_json(directory / "package_manifest.json"))
    policy = _validate_policy(load_strict_json(directory / "policy.json"), "TRACKED")
    digest = canonical_sha256(policy)
    return policy, digest, manifest["policy_sha256"] == digest


def _load_source_package(package_dir: str | Path) -> tuple[dict[str, Any], str]:
    """Load source policy while requiring its manifest digest to match."""
    policy, digest, manifest_hash_matches = _read_source_package(package_dir)
    if not manifest_hash_matches:
        raise PackageFailure("PACKAGE_MANIFEST_POLICY_HASH_MISMATCH")
    return policy, digest


def check_package(
    package_dir: str | Path = DEFAULT_PACKAGE_DIR,
    runtime_policy_path: str | Path = DEFAULT_RUNTIME_POLICY,
) -> CheckResult:
    """Compare the validated tracked policy with the runtime representation."""
    policy, digest, manifest_hash_matches = _read_source_package(package_dir)
    runtime_policy = _validate_policy(
        load_strict_json(runtime_policy_path),
        "RUNTIME",
    )
    runtime_digest = canonical_sha256(runtime_policy)
    if not manifest_hash_matches:
        return CheckResult(
            "MISMATCH",
            digest,
            runtime_digest,
            "PACKAGE_MANIFEST_POLICY_HASH_MISMATCH",
        )
    if canonical_json(policy) == canonical_json(runtime_policy):
        return CheckResult("MATCH", digest, runtime_digest, "POLICY_MATCH")
    return CheckResult(
        "MISMATCH",
        digest,
        runtime_digest,
        "POLICY_CONTENT_MISMATCH",
    )


def _target_is_protected(target: Path) -> bool:
    """Identify Active, Canonical, or Pointer destinations as protected."""
    resolved = target.resolve(strict=False)
    components = tuple(component.casefold() for component in resolved.parts)
    if "active" in components:
        return True
    return any(
        marker in component
        for component in components
        for marker in ("pointer", "canonical")
    )


def _compare_existing_target(
    target: Path,
    policy: dict[str, Any],
    digest: str,
) -> MaterializeResult:
    """Compare an existing target without changing its bytes."""
    try:
        existing = load_strict_json(target)
        equal = canonical_json(existing) == canonical_json(policy)
    except PackageFailure:
        equal = False
    if equal:
        return MaterializeResult("ALREADY_MATCH", target, digest, "TARGET_ALREADY_MATCH")
    return MaterializeResult(
        "HOLD_TARGET_CONFLICT",
        target,
        digest,
        "HOLD_TARGET_CONFLICT",
    )


def materialize(
    target: str | Path,
    package_dir: str | Path = DEFAULT_PACKAGE_DIR,
) -> MaterializeResult:
    """Create a missing candidate target and never replace an existing target."""
    destination = Path(target)
    if _target_is_protected(destination):
        raise PackageFailure("HOLD_PROTECTED_TARGET", str(destination))
    policy, digest = _load_source_package(package_dir)
    if destination.exists() or destination.is_symlink():
        return _compare_existing_target(destination, policy, digest)
    if not destination.parent.is_dir():
        raise PackageFailure("HOLD_TARGET_PARENT_MISSING", str(destination.parent))

    payload = canonical_json(policy) + "\n"
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        return _compare_existing_target(destination, policy, digest)
    except OSError as error:
        raise PackageFailure("HOLD_TARGET_WRITE_ERROR", str(destination)) from error
    return MaterializeResult("MATERIALIZED", destination, digest, "TARGET_MATERIALIZED")


def _build_argument_parser() -> argparse.ArgumentParser:
    """Build the small deterministic command-line interface."""
    parser = argparse.ArgumentParser(
        description="Check or explicitly materialize the TFCT TRUE8D candidate policy."
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="check",
        choices=("check", "canonical-hash", "materialize"),
    )
    parser.add_argument("target", nargs="?")
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE_DIR)
    parser.add_argument(
        "--runtime-policy",
        type=Path,
        default=DEFAULT_RUNTIME_POLICY,
    )
    return parser


def _run_check(package_dir: Path, runtime_policy: Path) -> int:
    """Run a read-only comparison and print stable result fields."""
    result = check_package(package_dir, runtime_policy)
    state = (
        "PASS_TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE_CHECK"
        if result.matched
        else "HOLD_RUNTIME_POLICY_PACKAGE_CONFLICT"
    )
    print(f"STATE={state}")
    print(f"CANONICAL_EQUIVALENCE={result.canonical_equivalence}")
    print(f"POLICY_SHA256={result.policy_sha256}")
    print(f"RUNTIME_POLICY_SHA256={result.runtime_policy_sha256}")
    print(f"REASON_CODE={result.reason_code}")
    return 0 if result.matched else 1


def _run_hash(package_dir: Path) -> int:
    """Print only the deterministic digest of the tracked policy."""
    _policy, digest = _load_source_package(package_dir)
    print(digest)
    return 0


def _run_materialize(target: str | None, package_dir: Path) -> int:
    """Run the explicit no-overwrite materialization operation."""
    if target is None:
        raise PackageFailure("MATERIALIZE_TARGET_REQUIRED")
    result = materialize(target, package_dir)
    print(f"STATE={result.status}")
    print(f"TARGET={result.target}")
    print(f"POLICY_SHA256={result.policy_sha256}")
    print(f"REASON_CODE={result.reason_code}")
    return 0 if result.successful else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch the check, canonical-hash, or materialize command."""
    arguments = _build_argument_parser().parse_args(argv)
    try:
        if arguments.command == "check":
            if arguments.target is not None:
                raise PackageFailure("TARGET_ONLY_VALID_FOR_MATERIALIZE")
            return _run_check(arguments.package_dir, arguments.runtime_policy)
        if arguments.command == "canonical-hash":
            if arguments.target is not None:
                raise PackageFailure("TARGET_ONLY_VALID_FOR_MATERIALIZE")
            return _run_hash(arguments.package_dir)
        return _run_materialize(arguments.target, arguments.package_dir)
    except PackageFailure as error:
        print("STATE=HOLD_RUNTIME_POLICY_PACKAGE_CONFLICT")
        print("CANONICAL_EQUIVALENCE=MISMATCH")
        print(f"REASON_CODE={error.reason_code}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
