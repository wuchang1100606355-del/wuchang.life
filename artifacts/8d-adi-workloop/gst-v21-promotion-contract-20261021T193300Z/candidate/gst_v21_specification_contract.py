"""Candidate-only GST V2.1 publication contract and read-only verifier.

No function in this module writes files, loads an executor, resolves authority,
consumes a nonce, or infers authorization from a candidate artifact.  Coordinate
enforcement and all mutations belong to the separately bound transaction adapter.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "GST_V21_SPEC_PROMOTION_CONTRACT_CANDIDATE/1.0"
LIVE_ROOT = "/home/taiji_admin/Taiji_Hub"
NODE = "taiji01"
LEAF = "manifests/total_field/origin_cell_gst_v21_specification"
SPEC_TARGET = LEAF + "/SPECIFICATION.md"
RECORD_TARGET = LEAF + "/CANONICAL_RECORD.json"
RECEIPT_TARGET = LEAF + "/PROMOTION_RECEIPT.json"
REGISTRY = "configs/total_field/w7tp_capability_internalization_registry_v1.json"
CAPABILITY_ID = "CAP_INTERNAL_ORIGIN_CELL_V1"
INTAKE = "runtime/total_field/conversation_intake/ORIGIN_CELL_GST_V21_CANONICAL_PROMOTION_20261022"
SOURCE_SPEC = INTAKE + "/ORIGIN_CELL_GST_V21_CANONICAL_SPEC.md"
SOURCE_CODEC = "runtime/total_field/conversation_intake/universal_origin_cell_codec_v2.py"
PARENT_CONTRACT = "manifests/total_field/w7tp_8d_adi_v2_3_canonical/CONTRACT.json"
PARENT_POINTER = "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
AUTHORITY_POINTER = "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
PREVIOUS_RUN = "artifacts/8d-adi-workloop/gst-v21-exact-promotion-20261022T190316Z"
PREVIOUS_REQUEST = PREVIOUS_RUN + "/PROMOTION_REQUEST.json"
PREVIOUS_REVIEW = PREVIOUS_RUN + "/evidence/NATIVE_CANDIDATE_REVIEW.json"
PREVIOUS_DISPOSITION = PREVIOUS_RUN + "/evidence/REVIEW_DISPOSITION.json"
AUDIT_BASE = "/home/taiji_admin/w7tp_gst_v21_specification_audit"
EFFECT_PREFIX = "GST_V21_SPEC_PROMOTE:"
EXECUTOR_FILES = frozenset({
    "gst_v21_specification_contract.py",
    "promote_origin_cell_gst_v21_specification.py",
})
WRITE_SPEC = {
    SPEC_TARGET: ("CREATE", "postimages/SPECIFICATION.md"),
    RECORD_TARGET: ("CREATE", "postimages/CANONICAL_RECORD.json"),
    REGISTRY: ("CAS_REPLACE", "postimages/REGISTRY.json"),
}
NON_EFFECT_KEYS = frozenset({
    "runtime_activation", "runtime_consumer_replacement", "business_execution",
    "parent_canonical_switch", "authority_expansion", "evidence_maturity_promotion",
    "deploy", "restart", "git_commit", "git_push",
})
JOURNAL_EVENTS = (
    "01_LEAF_CREATE_INTENT", "02_LEAF_CREATED",
    "03_SPEC_CREATE_INTENT", "04_SPEC_CREATED",
    "05_RECORD_CREATE_INTENT", "06_RECORD_CREATED",
    "07_REGISTRY_STAGE_INTENT", "08_REGISTRY_STAGED",
    "09_REGISTRY_EXCHANGE_INTENT", "10_REGISTRY_EXCHANGED",
    "11_RECEIPT_CREATE_INTENT", "12_RECEIPT_CREATED",
)
DERIVED_PATH_RULES = {
    "operation_dir": "audit_base/<contract_raw_sha256>",
    "native_receipt_dir": "operation_dir/authority",
    "native_receipt": "operation_dir/authority/<sha256_raw_nonce>.json",
    "nonce_marker": "audit_base/replay/<sha256_raw_nonce>.json",
    "registry_stage": "configs/total_field/.gst-v21-<contract_raw_sha256>.registry-stage",
    "registry_stage_lifecycle": "RETAIN_EXCHANGED_PREIMAGE_ON_SUCCESS_OR_UNKNOWN_BYTES_ON_FAILURE",
    "private_grant": "operation_dir/private-grant.json",
    "transaction_attempt": "operation_dir/TRANSACTION_ATTEMPT.json",
    "journal_files": ["operation_dir/journal/" + event + ".json" for event in JOURNAL_EVENTS],
    "recovery": "operation_dir/RECOVERY.json",
    "operation_lock": "audit_base/operation.lock",
    "journal_creation_rule": "FINITE_EXCLUSIVE_CREATE_AND_FSYNC",
    "private_grant_rule": "PRIVATE_LOCAL_ONLY_MODE_0600",
    "raw_nonce_or_signature_in_output": False,
    "formal_audit_paths_created_in_candidate_run": False,
}
RECEIPT_RULES = {
    "rule_scope": "FORMAL_SPECIFICATION_PROMOTION",
    "formal_receipt_schema": "GST_V21_SPECIFICATION_PROMOTION_RECEIPT/1.0",
    "simulation_receipt_schema": "GST_V21_SIMULATION_RECEIPT_NOT_AUTHORITY/1.0",
    "after_native_authorization_only": True,
    "receipt_is_last_publication_step": True,
    "missing_receipt_is_hold": True,
    "fixed_postimage_hash_before_authorization": False,
    "required_bindings": ["contract_raw_sha256", "exact_effect", "native_authorization.path",
                          "native_authorization.sha256", "native_authorization.file_sha256",
                          "static_preimages", "static_postimages",
                          "immutable_source_verification", "published_at", "verification_result"],
    "authority_source": "EXISTING_TAIJI01_NATIVE_RESOLVER_ONLY",
    "caller_supplied_pass_is_authority": False,
    "simulation_can_claim_formal_authority": False,
}
ROLLBACK_RULES = {
    "before_receipt": "RESTORE_ONLY_OWNED_MATCHING_POSTIMAGES_UNDER_EXACT_CAS",
    "registry_backup_ref": "preimages/REGISTRY.json",
    "preserve_native_audit_and_replay": True,
    "partial_failure_requires_explicit_recovery_record": True,
    "after_receipt": "NEW_EXACT_WITHDRAWAL_AUTHORITY_AND_APPEND_ONLY_HISTORY",
    "delete_historical_receipts": False,
    "concurrency_boundary": "COOPERATIVE_LOCK_AND_EXCLUSIVE_LOCAL_CHANGE_WINDOW",
    "durable_ownership_journal_required": True,
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_PAYLOAD_BYTES = 8 * 1024 * 1024


class ContractError(ValueError):
    """Stable, bounded diagnostics; never include a source payload or secret."""
    def __init__(self, code: str, path: str = "$") -> None:
        self.code = code
        self.reason_code = code
        self.path = path
        super().__init__(f"{code}:{path}")


ContractHold = ContractError


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(condition: bool, code: str, path: str = "$") -> None:
    if not condition:
        raise ContractError(code, path)


def _digest(value: Any, path: str) -> str:
    _require(isinstance(value, str) and HEX64.fullmatch(value) is not None,
             "HOLD_CONTRACT_SHA256", path)
    return value


def _relative(rel: Any) -> str:
    _require(isinstance(rel, str) and bool(rel), "HOLD_CONTRACT_PATH")
    _require("\\" not in rel and "\x00" not in rel and ":" not in rel,
             "HOLD_CONTRACT_PATH", rel)
    parts = rel.split("/")
    _require(not PurePosixPath(rel).is_absolute()
             and all(part not in {"", ".", ".."} for part in parts),
             "HOLD_CONTRACT_PATH", rel)
    return rel


def _root(root: Path | str) -> Path:
    root = Path(root).absolute()
    _require(".." not in root.parts, "HOLD_ROOT_PATH", str(root))
    # Do not normalize away a symlink before checking the supplied coordinate.
    for item in reversed((root, *root.parents)):
        try:
            info = item.lstat()
        except OSError as exc:
            raise ContractError("HOLD_ROOT_UNAVAILABLE", str(item)) from exc
        _require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode),
                 "HOLD_ROOT_SYMLINK_OR_NOT_DIRECTORY", str(item))
    return root


def safe_path(root: Path | str, rel: str) -> Path:
    """Return an exact file coordinate; absent targets are allowed.

    All existing ancestors must be real directories. Existing endpoints must be
    ordinary, singly linked files. This is a preflight check, not a filesystem
    mutation primitive or a promise that later callers are immune to races.
    """
    base = _root(root)
    clean = _relative(rel)
    parts = clean.split("/")
    current = base
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ContractError("HOLD_PATH_UNAVAILABLE", clean) from exc
        _require(not stat.S_ISLNK(info.st_mode), "HOLD_PATH_SYMLINK", clean)
        if index < len(parts) - 1:
            _require(stat.S_ISDIR(info.st_mode), "HOLD_PATH_ANCESTOR_NOT_DIRECTORY", clean)
        else:
            _require(stat.S_ISREG(info.st_mode), "HOLD_PATH_NOT_REGULAR_FILE", clean)
            _require(info.st_nlink == 1, "HOLD_PATH_HARDLINK", clean)
    return base / clean


def _read(root: Path | str, rel: str, limit: int | None = None) -> bytes:
    """Read with no-follow directory descriptors and stable inode checks."""
    path = safe_path(root, rel)
    base = _root(root)
    descriptors: list[int] = []
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        fd = os.open(base, directory_flags)
        descriptors.append(fd)
        parts = _relative(rel).split("/")
        for part in parts[:-1]:
            fd = os.open(part, directory_flags, dir_fd=fd)
            descriptors.append(fd)
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        descriptors.append(file_fd)
        before = os.fstat(file_fd)
        _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                 "HOLD_PATH_NOT_SINGLE_REGULAR_FILE", rel)
        if limit is not None:
            _require(before.st_size <= limit, "HOLD_FILE_SIZE_LIMIT", rel)
        blocks: list[bytes] = []
        read_bytes = 0
        while True:
            block = os.read(file_fd, 65536)
            if not block:
                break
            read_bytes += len(block)
            if limit is not None:
                _require(read_bytes <= limit, "HOLD_FILE_SIZE_LIMIT", rel)
            blocks.append(block)
        after = os.fstat(file_fd)
        # Recheck ancestors after reading as well as checking the opened inode.
        current = safe_path(base, rel).lstat()
        expected = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        _require(expected == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                 and before.st_dev == current.st_dev and before.st_ino == current.st_ino
                 and after.st_nlink == 1 and current.st_nlink == 1,
                 "HOLD_FILE_CHANGED_DURING_READ", rel)
        return b"".join(blocks)
    except ContractError:
        raise
    except OSError as exc:
        raise ContractError("HOLD_FILE_READ", rel) from exc
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in items:
        _require(key not in value, "HOLD_JSON_DUPLICATE_KEY")
        value[key] = item
    return value


def _json(raw: bytes, path: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("HOLD_JSON_INVALID", path) from exc
    _require(isinstance(value, dict), "HOLD_JSON_OBJECT_REQUIRED", path)
    try:
        canonical_bytes(value)
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ContractError("HOLD_JSON_UNREPRESENTABLE", path) from exc
    return value


def _assert_no_effects(value: Any, path: str) -> None:
    _require(isinstance(value, dict) and set(value) == NON_EFFECT_KEYS,
             "HOLD_NON_EFFECT_CONTRACT", path)
    _require(all(item is False for item in value.values()),
             "HOLD_NON_EFFECT_EXPANSION", path)


def _registry_delta(before: dict[str, Any], after: dict[str, Any]) -> None:
    _require(before.get("canonical") is False, "HOLD_REGISTRY_AUTHORITY_WALL", REGISTRY)
    rows = before.get("capabilities")
    _require(isinstance(rows, list) and len(rows) == 8
             and all(isinstance(row, dict) and isinstance(row.get("capability_id"), str)
                     for row in rows),
             "HOLD_REGISTRY_CAPABILITY_COUNT", REGISTRY)
    selected = [row for row in rows if isinstance(row, dict)
                and row.get("capability_id") == CAPABILITY_ID]
    _require(len(selected) == 1, "HOLD_REGISTRY_ORIGIN_CELL_NOT_UNIQUE", REGISTRY)
    row = selected[0]
    _require(isinstance(row.get("source_refs"), list)
             and RECORD_TARGET not in row["source_refs"],
             "HOLD_REGISTRY_REFERENCE_ALREADY_PRESENT", REGISTRY)
    d8 = row.get("d8_authority", {})
    d5 = row.get("d5_execution", {})
    _require(isinstance(d8, dict) and isinstance(d5, dict)
             and d8.get("canonical") is False and d8.get("provider_authority") is False
             and d8.get("final_decision") is False
             and d8.get("requires_total_field_verify") is True
             and d5.get("mode") == "CANDIDATE_ONLY" and d5.get("direct_effect") is False,
             "HOLD_REGISTRY_ORIGIN_CELL_AUTHORITY", REGISTRY)
    expected = copy.deepcopy(before)
    next(item for item in expected["capabilities"]
         if item["capability_id"] == CAPABILITY_ID)["source_refs"].append(RECORD_TARGET)
    _require(canonical_bytes(after) == canonical_bytes(expected),
             "HOLD_REGISTRY_DELTA_OUTSIDE_SINGLE_REFERENCE", REGISTRY)


def load_bundle(bundle_dir: Path | str) -> dict[str, Any]:
    """Validate the immutable candidate bundle without importing its executor."""
    bundle = _root(bundle_dir)
    raw = _read(bundle, "PROMOTION_CONTRACT.json", MAX_JSON_BYTES)
    contract = _json(raw, "PROMOTION_CONTRACT.json")
    required = {
        "schema", "run_id", "task_id", "lifecycle_state", "node", "root", "branch", "head",
        "immutable_sources", "executor_bindings", "static_writes", "receipt_path", "audit_base",
        "authority", "derived_paths", "registry_delta", "parent_canonical", "specification",
        "receipt_derivation", "rollback", "non_effects", "evidence_scope", "order_binding",
    }
    _require(set(contract) == required, "HOLD_CONTRACT_FIELD_SET")
    _require(contract["schema"] == SCHEMA, "HOLD_CONTRACT_SCHEMA")
    _require(contract["lifecycle_state"] == "IMAGINED_CANDIDATE",
             "HOLD_CONTRACT_PREMATURE_AUTHORITY")
    _require(contract["node"] == NODE and contract["root"] == LIVE_ROOT,
             "HOLD_CONTRACT_COORDINATE")
    _require(isinstance(contract["branch"], str) and bool(contract["branch"])
             and isinstance(contract["head"], str)
             and re.fullmatch(r"[0-9a-f]{40}", contract["head"]) is not None,
             "HOLD_CONTRACT_GIT_COORDINATE")
    _require(all(isinstance(contract[k], str) and contract[k] for k in ("run_id", "task_id")),
             "HOLD_CONTRACT_TASK_COORDINATE")
    _require(raw == canonical_bytes(contract) + b"\n", "HOLD_CONTRACT_SERIALIZATION")
    _assert_no_effects(contract["non_effects"], "$.non_effects")
    _require(contract["receipt_path"] == RECEIPT_TARGET
             and contract["audit_base"] == AUDIT_BASE, "HOLD_CONTRACT_OUTPUT_BOUNDARY")
    authority = {
        "resolver_ref": "tools/total_field_authority_resolver.py#resolve_founder_signed_break_glass_effect",
        "effect_prefix": EFFECT_PREFIX,
        "signed_grant_schema": "W7TP_FOUNDER_SOVEREIGN_BREAK_GLASS/1.0",
        "max_ttl_seconds": 300,
        "receipt_derived_after_authorization": True,
    }
    _require(canonical_bytes(contract["authority"]) == canonical_bytes(authority),
             "HOLD_CONTRACT_AUTHORITY_ADAPTER")
    _require(canonical_bytes(contract["derived_paths"]) == canonical_bytes(DERIVED_PATH_RULES),
             "HOLD_CONTRACT_DERIVED_PATHS")
    sources = contract["immutable_sources"]
    _require(isinstance(sources, dict) and len(sources) == 43,
             "HOLD_IMMUTABLE_SOURCE_SET")
    required_sources = {SOURCE_SPEC, SOURCE_CODEC, PARENT_POINTER, PARENT_CONTRACT,
                        AUTHORITY_POINTER, "tools/total_field_authority_resolver.py",
                        "core/capability_internalization.py",
                        "schemas/field/w7tp_capability_internalization_registry.schema.json",
                        PREVIOUS_REQUEST, PREVIOUS_REVIEW, PREVIOUS_DISPOSITION}
    _require(required_sources <= set(sources) and REGISTRY not in sources
             and not (set(WRITE_SPEC) & set(sources)), "HOLD_IMMUTABLE_SOURCE_BOUNDARY")
    for ref, digest in sources.items():
        _relative(ref)
        _digest(digest, ref)
    executors = contract["executor_bindings"]
    _require(isinstance(executors, dict) and set(executors) == EXECUTOR_FILES,
             "HOLD_EXECUTOR_FILE_SET")
    for name, digest in executors.items():
        _digest(digest, name)
        _require(sha256(_read(bundle, "candidate/" + name, MAX_PAYLOAD_BYTES)) == digest,
                 "HOLD_EXECUTOR_HASH_DRIFT", name)
    writes = contract["static_writes"]
    _require(isinstance(writes, list) and len(writes) == 3,
             "HOLD_STATIC_WRITE_COUNT")
    payloads: dict[str, bytes] = {}
    write_map: dict[str, dict[str, Any]] = {}
    entry_keys = {"path", "operation", "preimage_sha256", "postimage_sha256",
                  "postimage_bytes", "payload_ref"}
    for entry in writes:
        _require(isinstance(entry, dict) and set(entry) == entry_keys, "HOLD_WRITE_SCHEMA")
        ref = entry["path"]
        _require(isinstance(ref, str) and ref in WRITE_SPEC and ref not in write_map,
                 "HOLD_WRITE_PATH_NOT_ALLOWED")
        operation, payload_ref = WRITE_SPEC[ref]
        _require(entry["operation"] == operation and entry["payload_ref"] == payload_ref,
                 "HOLD_WRITE_OPERATION_OR_PAYLOAD", ref)
        if operation == "CREATE":
            _require(entry["preimage_sha256"] is None, "HOLD_CREATE_PREIMAGE_NOT_ABSENT", ref)
        else:
            _digest(entry["preimage_sha256"], ref)
        _digest(entry["postimage_sha256"], ref)
        _require(type(entry["postimage_bytes"]) is int
                 and 0 < entry["postimage_bytes"] <= MAX_PAYLOAD_BYTES,
                 "HOLD_POSTIMAGE_SIZE", ref)
        data = _read(bundle, payload_ref, MAX_PAYLOAD_BYTES)
        _require(len(data) == entry["postimage_bytes"] and sha256(data) == entry["postimage_sha256"],
                 "HOLD_PAYLOAD_HASH_OR_SIZE", ref)
        payloads[ref] = data
        write_map[ref] = entry
    _require(set(write_map) == set(WRITE_SPEC), "HOLD_WRITE_SET_INCOMPLETE")
    delta = contract["registry_delta"]
    _require(isinstance(delta, dict) and delta == {
        "capability_id": CAPABILITY_ID, "append_source_ref": RECORD_TARGET,
        "preimage_payload_ref": "preimages/REGISTRY.json",
        "preimage_sha256": write_map[REGISTRY]["preimage_sha256"],
        "all_other_fields_unchanged": True,
    }, "HOLD_REGISTRY_DELTA_CONTRACT")
    before_raw = _read(bundle, "preimages/REGISTRY.json", MAX_PAYLOAD_BYTES)
    _require(sha256(before_raw) == delta["preimage_sha256"], "HOLD_REGISTRY_PREIMAGE_PAYLOAD")
    _registry_delta(_json(before_raw, "preimages/REGISTRY.json"),
                    _json(payloads[REGISTRY], "postimages/REGISTRY.json"))
    _require(sha256(payloads[SPEC_TARGET]) == sources[SOURCE_SPEC],
             "HOLD_SPECIFICATION_BYTES_CHANGED")
    subject = {"source_ref": SOURCE_SPEC, "source_sha256": sources[SOURCE_SPEC],
               "codec_ref": SOURCE_CODEC, "codec_sha256": sources[SOURCE_CODEC],
               "scope": "SPECIFICATION_CANONICAL_IDENTITY_ONLY"}
    _require(contract["specification"] == subject, "HOLD_SPECIFICATION_BINDING")
    parent = {"canonical_id": "W7TP_8D_ADI_V2_3", "version": "2.3",
              "contract_ref": PARENT_CONTRACT, "contract_sha256": sources[PARENT_CONTRACT],
              "pointer_ref": PARENT_POINTER, "pointer_sha256": sources[PARENT_POINTER]}
    _require(contract["parent_canonical"] == parent, "HOLD_PARENT_CANONICAL_BINDING")
    record = _json(payloads[RECORD_TARGET], "postimages/CANONICAL_RECORD.json")
    expected_record = {
        "schema": "GST_V21_SPECIFICATION_IDENTITY_RECORD_CANDIDATE/1.0",
        "record_state": "REQUIRES_VERIFIED_NATIVE_PROMOTION_RECEIPT",
        "specification_id": "ORIGIN_CELL_GST_V2_1",
        "definition_authority": "江政隆",
        "record_is_self_authorizing": False,
        "specification": subject, "parent_canonical": parent,
        "formal_validity": {"receipt_ref": RECEIPT_TARGET,
                            "rule": "EXACT_NATIVE_AUTHORIZATION_AND_POSTIMAGE_VERIFICATION_REQUIRED",
                            "file_presence_is_authority": False},
        "evidence_scope": contract["evidence_scope"], "non_effects": contract["non_effects"],
    }
    _require(canonical_bytes(record) == canonical_bytes(expected_record),
             "HOLD_CANONICAL_RECORD_CONTRACT")
    _require(isinstance(contract["evidence_scope"], dict)
             and isinstance(contract["evidence_scope"].get("tier_2"), dict)
             and contract["evidence_scope"]["tier_2"].get("state")
             == "REPORTED_EXTENSION_SOURCE_BINDING_PENDING", "HOLD_EVIDENCE_MATURITY_DRIFT")
    _require(canonical_bytes(contract["receipt_derivation"]) == canonical_bytes(RECEIPT_RULES),
             "HOLD_RECEIPT_DERIVATION_CONTRACT")
    _require(canonical_bytes(contract["rollback"]) == canonical_bytes(ROLLBACK_RULES),
             "HOLD_ROLLBACK_CONTRACT")
    order = contract["order_binding"]
    _require(isinstance(order, dict) and set(order) == {"ref", "sha256"}
             and order["ref"] == "order.md", "HOLD_ORDER_BINDING")
    _digest(order["sha256"], "order.md")
    _require(sha256(_read(bundle, "order.md", MAX_JSON_BYTES)) == order["sha256"],
             "HOLD_FROZEN_ORDER_DRIFT")
    digest = sha256(raw)
    return {"contract": contract, "contract_sha256": digest,
            "effect": EFFECT_PREFIX + digest, "payloads": payloads, "bundle_dir": bundle}


def verify_preconditions(root: Path | str, bundle_dir: Path | str,
                         phase: str = "PRE") -> dict[str, Any]:
    """Verify immutable inputs and optional PRE/POST images, without authority.

    Synthetic roots are permitted for isolated tests. The caller MUST separately
    enforce live node/root/branch/HEAD before effectful native authority use.
    POST intentionally does not adjudicate the derived receipt; its validator
    belongs to the transaction adapter and is mandatory for formal completion.
    """
    _require(phase in {"PRE", "POST", "IMMUTABLE"}, "HOLD_PRECONDITION_PHASE")
    base = _root(root)
    bundle = load_bundle(bundle_dir)
    contract = bundle["contract"]
    for ref, expected in contract["immutable_sources"].items():
        _require(sha256(_read(base, ref)) == expected, "HOLD_IMMUTABLE_SOURCE_DRIFT", ref)
    request = _json(_read(base, PREVIOUS_REQUEST, MAX_JSON_BYTES), PREVIOUS_REQUEST)
    _require(canonical_bytes(contract["evidence_scope"]) == canonical_bytes(request.get("evidence_scope")),
             "HOLD_PREVIOUS_EVIDENCE_SCOPE_DRIFT", PREVIOUS_REQUEST)
    checks: list[dict[str, Any]] = []
    for entry in contract["static_writes"] if phase != "IMMUTABLE" else []:
        ref = entry["path"]
        target = safe_path(base, ref)
        if phase == "PRE" and entry["operation"] == "CREATE":
            _require(not target.exists(), "HOLD_CREATE_TARGET_ALREADY_EXISTS", ref)
            observed: str | None = None
        else:
            observed = sha256(_read(base, ref))
            expected = entry["preimage_sha256"] if phase == "PRE" else entry["postimage_sha256"]
            _require(observed == expected, "HOLD_STATIC_IMAGE_DRIFT", ref)
        checks.append({"path": ref, "sha256": observed, "state": "MATCH"})
    receipt = safe_path(base, RECEIPT_TARGET) if phase != "IMMUTABLE" else None
    if phase == "PRE":
        _require(not receipt.exists(), "HOLD_RECEIPT_ALREADY_EXISTS", RECEIPT_TARGET)
    state = {"PRE": "PASS_CANDIDATE_PRECONDITIONS", "POST": "PASS_STATIC_POSTIMAGES_ONLY",
             "IMMUTABLE": "PASS_IMMUTABLE_SOURCES_ONLY"}[phase]
    return {"state": state,
            "phase": phase, "contract_sha256": bundle["contract_sha256"],
            "source_count": len(contract["immutable_sources"]), "target_checks": checks,
            "expected_coordinates": {key: contract[key] for key in ("node", "root", "branch", "head")},
            "actual_root": str(base), "coordinate_authority_verified": False,
            "receipt_exists": receipt.exists() if receipt is not None else None,
            "receipt_validated": False,
            "effect_authorized": False, "writes_performed": False}
