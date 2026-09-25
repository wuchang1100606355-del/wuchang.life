#!/usr/bin/env python3
"""Fail-closed verifier for the local XiaoJ Total Field skill registry."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import unicodedata


EXPECTED_SCHEMA = "XIAOJ_TOTAL_FIELD_SKILL_REGISTRY_V1"
EXPECTED_REGISTRY_STATE = "OPERABLE"


class RegistryError(RuntimeError):
    pass


def canonical_bytes(value: object) -> bytes:
    def normalize(item: object) -> object:
        if isinstance(item, str):
            return unicodedata.normalize("NFC", item)
        if isinstance(item, list):
            return [normalize(part) for part in item]
        if isinstance(item, dict):
            return {normalize(key): normalize(val) for key, val in item.items()}
        if isinstance(item, float):
            raise RegistryError("floating-point values are not allowed")
        return item

    return json.dumps(
        normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegistryError(message)


def verify_entry(entry: dict) -> None:
    required = (
        "skill_id",
        "version",
        "registration_state",
        "availability",
        "invocation",
        "role",
        "installed_path",
        "manifest_ref",
        "manifest_sha256",
        "registration_run_id",
    )
    missing = [key for key in required if key not in entry]
    require(not missing, f"entry missing fields: {','.join(missing)}")
    require(entry["registration_state"] == "REGISTERED", "entry is not REGISTERED")
    require(entry["availability"] == "AVAILABLE", "entry is not AVAILABLE")
    require(entry["invocation"] == f"${entry['skill_id']}", "invocation mismatch")
    require(entry.get("runtime_activation_required") is False, "unexpected runtime activation requirement")
    require(entry.get("runtime_activation_performed") is False, "runtime activation claim is not allowed")
    require(entry.get("canonical") is False, "registration cannot claim canonical")
    require(entry.get("final_authority") is False, "registration cannot claim final authority")

    installed_path = Path(entry["installed_path"])
    manifest_path = Path(entry["manifest_ref"])
    require(installed_path.is_absolute(), "installed_path must be absolute")
    require(manifest_path.is_absolute(), "manifest_ref must be absolute")
    require(installed_path.is_dir(), "installed skill directory is missing")
    require(not installed_path.is_symlink(), "installed skill directory cannot be a symlink")
    require(manifest_path.is_file(), "installed manifest is missing")
    require(not manifest_path.is_symlink(), "installed manifest cannot be a symlink")
    require(manifest_path.parent.resolve() == installed_path.resolve(), "manifest is outside installed skill")
    require(sha256_file(manifest_path) == entry["manifest_sha256"], "manifest file hash mismatch")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("skill_id") == entry["skill_id"], "manifest skill_id mismatch")
    require(manifest.get("version") == entry["version"], "manifest version mismatch")
    require(manifest.get("manifest_state") == "REGISTERED", "manifest is not REGISTERED")
    require(manifest.get("lifecycle", {}).get("state") == "REGISTERED", "manifest lifecycle is not REGISTERED")
    require(manifest.get("classification", {}).get("role") == entry["role"], "manifest role mismatch")
    require(manifest.get("classification", {}).get("complete_8d_claim") is False, "adapter cannot claim complete 8D")
    require(manifest.get("w7tp_contract", {}).get("claimed") is False, "adapter cannot claim W7TP core")
    require(manifest.get("lifecycle", {}).get("canonical_promotion") is False, "manifest cannot self-promote")

    supplied_manifest_self_hash = manifest.get("evidence_and_hashes", {}).get("manifest_self_hash")
    unsigned_manifest = json.loads(json.dumps(manifest))
    unsigned_manifest.get("evidence_and_hashes", {}).pop("manifest_self_hash", None)
    measured_manifest_self_hash = hashlib.sha256(canonical_bytes(unsigned_manifest)).hexdigest()
    require(supplied_manifest_self_hash == measured_manifest_self_hash, "manifest self hash mismatch")

    implementation_hashes = manifest.get("evidence_and_hashes", {}).get("implementation_sha256", {})
    require(bool(implementation_hashes), "implementation hash map is missing")
    for relative, expected_hash in implementation_hashes.items():
        relative_path = Path(relative)
        require(not relative_path.is_absolute() and ".." not in relative_path.parts, f"unsafe implementation path: {relative}")
        implementation_path = installed_path / relative_path
        require(implementation_path.is_file(), f"implementation file missing: {relative}")
        require(not implementation_path.is_symlink(), f"implementation symlink rejected: {relative}")
        require(sha256_file(implementation_path) == expected_hash, f"implementation hash mismatch: {relative}")


def verify_registry(path: Path) -> dict:
    require(path.is_file(), "registry file is missing")
    require(not path.is_symlink(), "registry file cannot be a symlink")
    registry = json.loads(path.read_text(encoding="utf-8"))
    require(registry.get("schema_id") == EXPECTED_SCHEMA, "registry schema mismatch")
    require(registry.get("registry_state") == EXPECTED_REGISTRY_STATE, "registry is not OPERABLE")
    require(registry.get("node") == "taiji01", "registry node mismatch")
    skills = registry.get("skills")
    require(isinstance(skills, list) and skills, "registry has no skills")
    skill_ids = [entry.get("skill_id") for entry in skills]
    require(len(skill_ids) == len(set(skill_ids)), "duplicate skill_id")
    for entry in skills:
        require(isinstance(entry, dict), "registry entry must be an object")
        verify_entry(entry)

    supplied_registry_hash = registry.get("registry_self_sha256")
    unsigned_registry = json.loads(json.dumps(registry))
    unsigned_registry.pop("registry_self_sha256", None)
    measured_registry_hash = hashlib.sha256(canonical_bytes(unsigned_registry)).hexdigest()
    require(supplied_registry_hash == measured_registry_hash, "registry self hash mismatch")
    return {
        "state": "PASS_TOTAL_FIELD_SKILL_REGISTRY",
        "registry": str(path),
        "registered_skill_count": len(skills),
        "registered_skill_ids": sorted(skill_ids),
    }


def main() -> int:
    default_registry = Path(__file__).resolve().parents[2] / "runtime/total_field/xiaoj/xiaoj_skill_registry.json"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=default_registry)
    args = parser.parse_args()
    try:
        result = verify_registry(args.registry.resolve())
    except (OSError, ValueError, json.JSONDecodeError, RegistryError) as exc:
        print(json.dumps({"state": "HOLD_TOTAL_FIELD_SKILL_REGISTRY", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
