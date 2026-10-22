#!/usr/bin/env python3
"""Prepare local candidate postimages; freeze only with explicit --finalize.

This builder never writes the production root. It creates new local bundle
files, refuses conflicting existing bytes, and does not issue authority.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from gst_v21_specification_contract import (
    AUDIT_BASE, AUTHORITY_POINTER, CAPABILITY_ID, ContractError, DERIVED_PATH_RULES, EFFECT_PREFIX,
    EXECUTOR_FILES, LEAF, LIVE_ROOT, NODE, NON_EFFECT_KEYS, PARENT_CONTRACT,
    PARENT_POINTER, RECEIPT_TARGET, RECEIPT_RULES, RECORD_TARGET, REGISTRY, ROLLBACK_RULES, SCHEMA, SOURCE_CODEC,
    SOURCE_SPEC, SPEC_TARGET, canonical_bytes, load_bundle, sha256,
)


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError("HOLD_BUILDER_OBJECT", str(path))
    return value


def create_exact(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != data:
            raise ContractError("HOLD_BUILDER_EXISTING_CONFLICT", str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def build(run: Path, project: Path, previous: Path, finalize: bool) -> dict:
    run = run.absolute()
    project = project.absolute()
    previous = previous.absolute()
    production = Path(LIVE_ROOT)
    if run == production or production in run.parents or run.is_symlink():
        raise ContractError("HOLD_BUILDER_LIVE_ROOT_FORBIDDEN")
    if not (run / "order.md").is_file():
        raise ContractError("HOLD_BUILDER_FROZEN_ORDER_MISSING")
    bindings = read_object(run / "evidence/CURRENT_BINDINGS.json")
    live = read_object(run / "evidence/LIVE_SNAPSHOT.json")
    if bindings.get("all_match") is not True or len(bindings.get("protected", {})) != 41:
        raise ContractError("HOLD_BUILDER_CURRENT_BINDINGS")
    immutable = {}
    for ref, entry in bindings["protected"].items():
        if entry.get("match") is not True or entry.get("symlink") is not False:
            raise ContractError("HOLD_BUILDER_SOURCE_BINDING", ref)
        if ref != REGISTRY:
            immutable[ref] = entry["actual"]
    request_raw = (previous / "PROMOTION_REQUEST.json").read_bytes()
    request = json.loads(request_raw)
    previous_ref = "artifacts/8d-adi-workloop/" + previous.name
    for suffix in ("PROMOTION_REQUEST.json", "evidence/NATIVE_CANDIDATE_REVIEW.json",
                   "evidence/REVIEW_DISPOSITION.json"):
        immutable[previous_ref + "/" + suffix] = sha256((previous / suffix).read_bytes())
    request_expected = live["files"][previous_ref + "/PROMOTION_REQUEST.json"]["sha256"]
    if sha256(request_raw) != request_expected:
        raise ContractError("HOLD_BUILDER_PREVIOUS_REQUEST_DRIFT")
    spec = request["review_material"]["text"].encode("utf-8")
    if sha256(spec) != immutable[SOURCE_SPEC] or len(spec) != request["objects"]["specification"]["bytes"]:
        raise ContractError("HOLD_BUILDER_SPECIFICATION_BYTES")
    registry_raw = (project / "source_snapshot" / REGISTRY).read_bytes()
    if sha256(registry_raw) != bindings["protected"][REGISTRY]["actual"]:
        raise ContractError("HOLD_BUILDER_REGISTRY_DRIFT")
    registry = json.loads(registry_raw)
    post_registry = copy.deepcopy(registry)
    selected = [row for row in post_registry["capabilities"] if row["capability_id"] == CAPABILITY_ID]
    if len(selected) != 1 or RECORD_TARGET in selected[0]["source_refs"]:
        raise ContractError("HOLD_BUILDER_ORIGIN_CELL_DELTA")
    selected[0]["source_refs"].append(RECORD_TARGET)
    non_effects = {key: False for key in sorted(NON_EFFECT_KEYS)}
    subject = {"source_ref": SOURCE_SPEC, "source_sha256": immutable[SOURCE_SPEC],
               "codec_ref": SOURCE_CODEC, "codec_sha256": immutable[SOURCE_CODEC],
               "scope": "SPECIFICATION_CANONICAL_IDENTITY_ONLY"}
    parent = {"canonical_id": "W7TP_8D_ADI_V2_3", "version": "2.3",
              "contract_ref": PARENT_CONTRACT, "contract_sha256": immutable[PARENT_CONTRACT],
              "pointer_ref": PARENT_POINTER, "pointer_sha256": immutable[PARENT_POINTER]}
    evidence_scope = copy.deepcopy(request["evidence_scope"])
    record = {
        "schema": "GST_V21_SPECIFICATION_IDENTITY_RECORD_CANDIDATE/1.0",
        "record_state": "REQUIRES_VERIFIED_NATIVE_PROMOTION_RECEIPT",
        "specification_id": "ORIGIN_CELL_GST_V2_1", "definition_authority": "江政隆",
        "record_is_self_authorizing": False, "specification": subject, "parent_canonical": parent,
        "formal_validity": {"receipt_ref": RECEIPT_TARGET,
                            "rule": "EXACT_NATIVE_AUTHORIZATION_AND_POSTIMAGE_VERIFICATION_REQUIRED",
                            "file_presence_is_authority": False},
        "evidence_scope": evidence_scope, "non_effects": non_effects,
    }
    payloads = {
        SPEC_TARGET: ("postimages/SPECIFICATION.md", spec),
        RECORD_TARGET: ("postimages/CANONICAL_RECORD.json", canonical_bytes(record) + b"\n"),
        REGISTRY: ("postimages/REGISTRY.json", canonical_bytes(post_registry) + b"\n"),
    }
    create_exact(run / "preimages/REGISTRY.json", registry_raw)
    writes = []
    for target, (ref, raw) in payloads.items():
        create_exact(run / ref, raw)
        writes.append({"path": target, "operation": "CAS_REPLACE" if target == REGISTRY else "CREATE",
                       "preimage_sha256": sha256(registry_raw) if target == REGISTRY else None,
                       "postimage_sha256": sha256(raw), "postimage_bytes": len(raw), "payload_ref": ref})
    if not finalize:
        return {"state": "CANDIDATE_POSTIMAGES_PREPARED_NOT_FROZEN", "static_writes": writes,
                "immutable_source_count": len(immutable), "final_contract_created": False,
                "formal_effect_authorized": False}
    executor_bindings = {}
    for name in sorted(EXECUTOR_FILES):
        path = run / "candidate" / name
        if not path.is_file() or path.is_symlink():
            raise ContractError("HOLD_BUILDER_EXECUTOR_NOT_READY", name)
        executor_bindings[name] = sha256(path.read_bytes())
    contract = {
        "schema": SCHEMA, "run_id": run.name,
        "task_id": "GST_V21_FORMAL_PROMOTION_CONTRACT_20261022",
        "lifecycle_state": "IMAGINED_CANDIDATE", "node": NODE, "root": LIVE_ROOT,
        "branch": live["branch"], "head": live["head"],
        "immutable_sources": dict(sorted(immutable.items())), "executor_bindings": executor_bindings,
        "static_writes": writes, "receipt_path": RECEIPT_TARGET, "audit_base": AUDIT_BASE,
        "authority": {
            "resolver_ref": "tools/total_field_authority_resolver.py#resolve_founder_signed_break_glass_effect",
            "effect_prefix": EFFECT_PREFIX, "signed_grant_schema": "W7TP_FOUNDER_SOVEREIGN_BREAK_GLASS/1.0",
            "max_ttl_seconds": 300, "receipt_derived_after_authorization": True,
        },
        "derived_paths": copy.deepcopy(DERIVED_PATH_RULES),
        "registry_delta": {"capability_id": CAPABILITY_ID, "append_source_ref": RECORD_TARGET,
                           "preimage_payload_ref": "preimages/REGISTRY.json",
                           "preimage_sha256": sha256(registry_raw), "all_other_fields_unchanged": True},
        "parent_canonical": parent, "specification": subject, "non_effects": non_effects,
        "evidence_scope": evidence_scope,
        "receipt_derivation": copy.deepcopy(RECEIPT_RULES),
        "rollback": copy.deepcopy(ROLLBACK_RULES),
        "order_binding": {"ref": "order.md", "sha256": sha256((run / "order.md").read_bytes())},
    }
    create_exact(run / "PROMOTION_CONTRACT.json", canonical_bytes(contract) + b"\n")
    checked = load_bundle(run)
    report = {
        "state": "PASS_CANDIDATE_CONTRACT_VALIDATION", "schema": "GST_V21_CONTRACT_VALIDATION/1.0",
        "contract_sha256": checked["contract_sha256"], "effect": checked["effect"],
        "schema_and_finite_write_set": "PASS", "static_payloads": "PASS_3_OF_3",
        "registry_delta": "EXACT_ONE_SOURCE_REFERENCE_APPEND",
        "executor_hashes": "PASS_2_OF_2", "immutable_source_count": len(immutable),
        "frozen_order_hash": "PASS", "specification_bytes": "EXACT_ORIGINAL_SHA256",
        "new_live_precondition_probe": "NOT_RUN_BY_LOCAL_BUILDER",
        "receipt": "DERIVED_ONLY_AFTER_REAL_NATIVE_AUTHORIZATION",
        "formal_effect_authorized": False, "runtime_activated": False,
    }
    create_exact(run / "evidence/CONTRACT_VALIDATION.json", canonical_bytes(report) + b"\n")
    return report


def main() -> int:
    here = Path(__file__).resolve().parent
    run = here.parent
    project = run.parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=run)
    parser.add_argument("--project-dir", type=Path, default=project)
    parser.add_argument("--previous-run", type=Path, default=project.parent /
                        "gst_v21_promotion_request_20261022/artifacts/8d-adi-workloop/"
                        "gst-v21-exact-promotion-20261022T190316Z")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    try:
        result = build(args.run_dir, args.project_dir, args.previous_run, args.finalize)
    except ContractError as exc:
        print(json.dumps({"state": "HOLD", "reason_code": exc.code, "path": exc.path}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
