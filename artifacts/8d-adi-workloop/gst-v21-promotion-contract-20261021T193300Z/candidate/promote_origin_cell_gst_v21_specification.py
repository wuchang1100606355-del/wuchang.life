#!/usr/bin/env python3
"""Exact GST V2.1 specification publication adapter -- IMAGINED_CANDIDATE.

Live mutations require the existing native resolver's fresh, exact-effect grant.
A synthetic run cannot create a production-valid receipt. No signing capability
is implemented here. An exclusive local change window is required for apply;
cooperative locking and exchange/readback detect bounded races, not all hostile
noncooperating writers. Unknown exchanged bytes are preserved, never discarded.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import fcntl
import importlib
import json
import os
import re
import socket
import stat
import subprocess
import sys
import types
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
# Execute the colocated source bytes, never a pre-existing bytecode cache.
_helper_name = "gst_v21_specification_contract"
_helper_path = Path(__file__).absolute().parent / (_helper_name + ".py")
_helper_fd = os.open(_helper_path, os.O_RDONLY | os.O_NOFOLLOW)
with os.fdopen(_helper_fd, "rb") as _helper_stream:
    _helper_source = _helper_stream.read()
_helper_module = sys.modules.get(_helper_name) or types.ModuleType(_helper_name)
_helper_module.__file__ = str(_helper_path)
_helper_module.__package__ = ""
sys.modules[_helper_name] = _helper_module
exec(compile(_helper_source, str(_helper_path), "exec"), _helper_module.__dict__)

from gst_v21_specification_contract import (
    AUDIT_BASE, AUTHORITY_POINTER, ContractError, JOURNAL_EVENTS, LEAF, LIVE_ROOT, NODE,
    RECEIPT_TARGET, RECORD_TARGET, REGISTRY, SPEC_TARGET, _json, _read,
    canonical_bytes, load_bundle, safe_path, sha256, verify_preconditions,
)

HEX = re.compile(r"[0-9a-f]{64}\Z")
BODY_KEYS = {"effect", "target", "git_head", "git_status_sha256",
             "authority_preimage_sha256", "nonce", "issued_at", "expires_at",
             "single_use", "human_direct"}
SIM_MARKER = ".GST_V21_SYNTHETIC_FIXTURE.json"
FORMAL_RECEIPT_SCHEMA = "GST_V21_SPECIFICATION_PROMOTION_RECEIPT/1.0"
SIM_RECEIPT_SCHEMA = "GST_V21_SIMULATION_RECEIPT_NOT_AUTHORITY/1.0"


def require(ok: bool, code: str, path: str = "$") -> None:
    if not ok:
        raise ContractError(code, path)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_time(value: Any) -> datetime:
    require(isinstance(value, str), "HOLD_GRANT_TIME")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("HOLD_GRANT_TIME") from exc
    require(result.tzinfo is not None, "HOLD_GRANT_TIMEZONE")
    return result.astimezone(timezone.utc)


def file_bytes(path: Path, limit: int = 2 * 1024 * 1024) -> bytes:
    return _read(path.parent, path.name, limit)


def directory(path: Path, create: bool = False) -> None:
    """No-follow exact directories; creation is limited by the caller's binding."""
    path = path.absolute()
    require(".." not in path.parts, "HOLD_DIRECTORY_PATH")
    for current in reversed((path, *path.parents)):
        try:
            info = current.lstat()
        except FileNotFoundError:
            require(create, "HOLD_DIRECTORY_MISSING", str(current))
            current.mkdir(mode=0o700)
            fsync_dir(current.parent)
            fsync_dir(current)
            info = current.lstat()
        require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode),
                "HOLD_DIRECTORY_NOT_REAL", str(current))


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def create_new(path: Path, raw: bytes, mode: int = 0o600) -> None:
    directory(path.parent)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     mode, dir_fd=parent)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.fsync(parent)
    finally:
        os.close(parent)


def write_json_new(path: Path, obj: dict) -> None:
    create_new(path, canonical_bytes(obj) + b"\n")


def exchange(first: Path, second: Path) -> None:
    """Atomic exchange; both files remain available for post-exchange checks."""
    require(first.parent == second.parent, "HOLD_EXCHANGE_DIFFERENT_PARENT")
    directory(first.parent)
    fd = os.open(first.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        require(hasattr(libc, "renameat2"), "HOLD_ATOMIC_EXCHANGE_UNAVAILABLE")
        fn = libc.renameat2
        fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        fn.restype = ctypes.c_int
        if fn(fd, os.fsencode(first.name), fd, os.fsencode(second.name), 2) != 0:
            error = ctypes.get_errno()
            raise OSError(error, "atomic exchange failed")
        os.fsync(fd)
    finally:
        os.close(fd)


def inode_identity(path: Path) -> list[int]:
    info = path.lstat()
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns]


def unlink_owned(path: Path, expected: str, identity: list[int] | None) -> bool:
    """Only under operation lock; never intentionally remove unknown contents."""
    if not path.exists() and not path.is_symlink():
        return True
    try:
        if identity is None or inode_identity(path) != identity or sha256(file_bytes(path)) != expected:
            return False
        before = path.lstat()
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            now = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            if (now.st_dev, now.st_ino, now.st_mtime_ns) != (before.st_dev, before.st_ino, before.st_mtime_ns):
                return False
            os.unlink(path.name, dir_fd=parent)
            os.fsync(parent)
            return True
        finally:
            os.close(parent)
    except (ContractError, OSError):
        return False


@contextmanager
def operation_lock(path: Path):
    directory(path.parent)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "HOLD_LOCK_FILE")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ContractError("HOLD_CONCURRENT_OPERATION") from exc
        yield
    finally:
        os.close(fd)


class PersistentReplayLedger:
    """Storage adapter for the EXISTING native resolver protocol, no policy.

    Successful entries are fsynced, exclusive, never expired or reused. A failed
    audit write after nonce consumption requires recovery and a new signed nonce.
    """
    persistent = True

    def __init__(self, path: Path):
        directory(path)
        info = path.lstat()
        require(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) & 0o077 == 0,
                "HOLD_REPLAY_STORAGE_PERMISSIONS")
        self.path = path

    def mark_used_or_replay(self, nonce: str, packet_hash: str, now: float, ttl: int) -> bool:
        require(isinstance(nonce, str) and HEX.fullmatch(nonce) is not None,
                "HOLD_NONCE_STORAGE_INPUT")
        require(isinstance(packet_hash, str) and HEX.fullmatch(packet_hash) is not None
                and type(ttl) is int and ttl >= 0, "HOLD_NONCE_STORAGE_INPUT")
        nonce_hash = sha256(nonce.encode())
        marker = {"schema": "GST_V21_NATIVE_NONCE_STORAGE/1.0", "nonce_sha256": nonce_hash,
                  "native_receipt_sha256": packet_hash, "consumed_at_epoch": now,
                  "original_ttl_seconds": ttl, "permanent_replay_rejection": True}
        try:
            write_json_new(self.path / (nonce_hash + ".json"), marker)
            return True
        except FileExistsError:
            return False


def live_coordinates(root: Path, bundle: dict) -> dict:
    require(str(root.absolute()) == LIVE_ROOT and root.resolve() == Path(LIVE_ROOT),
            "HOLD_EXACT_LIVE_ROOT")
    directory(root)
    require(Path(__file__).absolute() == bundle["bundle_dir"] / "candidate/promote_origin_cell_gst_v21_specification.py",
            "HOLD_RUNNING_EXECUTOR_COORDINATE")
    require(socket.gethostname() == NODE, "HOLD_EXACT_LIVE_NODE")
    environment = dict(os.environ, GIT_OPTIONAL_LOCKS="0", PYTHONDONTWRITEBYTECODE="1")
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", *args], cwd=root, env=environment, stderr=subprocess.DEVNULL)
    head = git("rev-parse", "HEAD").decode().strip()
    branch = git("branch", "--show-current").decode().strip()
    require(head == bundle["contract"]["head"] and branch == bundle["contract"]["branch"],
            "HOLD_GIT_COORDINATE_DRIFT")
    return {"node": NODE, "root": LIVE_ROOT, "head": head, "branch": branch,
            "git_status_sha256": sha256(git("status", "--porcelain=v1", "-z", "-uall")),
            "authority_preimage_sha256": sha256(_read(root, AUTHORITY_POINTER))}


def native_module(root: Path, bundle: dict):
    verify_immutable(root, bundle)
    sys.dont_write_bytecode = True
    for name, relative in (("tools", "tools"), ("tools.total_field", "tools/total_field")):
        package = types.ModuleType(name)
        package.__path__ = [str(root / relative)]
        package.__package__ = name
        sys.modules[name] = package
    # Dependency order is bound to the reviewed native sources. No replacement
    # policy and no copied implementation: execute the observed on-node bytes.
    names = ("tools.total_field.w7tp_v2_3_candidate_source",
             "tools.total_field.w7tp_true8d_contract_sandbox",
             "tools.total_field.w7tp_ed25519_verifier",
             "tools.total_field_ed25519_backend",
             "tools.total_field_authority_resolver")
    for name in names:
        relative = name.replace(".", "/") + ".py"
        raw = _read(root, relative)
        require(sha256(raw) == bundle["contract"]["immutable_sources"].get(relative),
                "HOLD_NATIVE_SOURCE_EXECUTION_BINDING", relative)
        module = types.ModuleType(name)
        module.__file__ = str(root / relative)
        module.__package__ = name.rpartition(".")[0]
        sys.modules[name] = module
        setattr(sys.modules[module.__package__], name.rpartition(".")[2], module)
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return sys.modules["tools.total_field_authority_resolver"]


def verify_immutable(root: Path, bundle: dict) -> None:
    for ref, expected in bundle["contract"]["immutable_sources"].items():
        require(sha256(_read(root, ref)) == expected, "HOLD_IMMUTABLE_SOURCE_DRIFT", ref)


def validate_grant_shape(grant: Any, bundle: dict, coordinates: dict,
                         at: datetime | None = None) -> dict:
    require(isinstance(grant, dict), "HOLD_FOUNDER_FRESH_SIGNATURE_REQUIRED")
    require(grant.get("schema") == "W7TP_FOUNDER_SOVEREIGN_BREAK_GLASS/1.0",
            "HOLD_GRANT_ENVELOPE_SCHEMA")
    body = grant.get("body")
    require(isinstance(body, dict) and set(body) == BODY_KEYS, "HOLD_GRANT_BODY_SCHEMA")
    require(body["effect"] == bundle["effect"] and body["target"] == LIVE_ROOT,
            "HOLD_GRANT_EFFECT_TARGET")
    require(body["git_head"] == coordinates["head"]
            and body["git_status_sha256"] == coordinates["git_status_sha256"]
            and body["authority_preimage_sha256"] == coordinates["authority_preimage_sha256"],
            "HOLD_GRANT_PREIMAGE_BINDING")
    require(body["single_use"] is True and body["human_direct"] is True,
            "HOLD_GRANT_HUMAN_SINGLE_USE")
    require(isinstance(body["nonce"], str) and HEX.fullmatch(body["nonce"]) is not None,
            "HOLD_GRANT_NONCE")
    issued, expires = parse_time(body["issued_at"]), parse_time(body["expires_at"])
    now = at if at is not None else datetime.now(timezone.utc)
    require(issued <= now < expires and 0 < (expires-issued).total_seconds() <= 300,
            "HOLD_GRANT_FRESHNESS_OR_TTL")
    signature = grant.get("stage_b_signature_hex")
    require(isinstance(signature, str) and re.fullmatch(r"[0-9a-fA-F]{128}", signature) is not None,
            "HOLD_GRANT_SIGNATURE_ENCODING")
    return body


def verify_grant_signature(root: Path, bundle: dict, grant: dict, module) -> None:
    """Precheck only; only the native resolver can authorize the effect."""
    from cryptography.hazmat.primitives import serialization
    role = module.resolve_founder_sovereign_root_role_promotion_authority(repo_root=root)
    require(role.get("authority_verified") is True, "HOLD_NATIVE_FOUNDER_TRUST_CHAIN")
    anchor = module.FOUNDER_SINGLE_IDENTITY_ROOT_POLICY_V1["authorized_sovereign_node_root_key"]
    require(grant.get("public_key_ref") == anchor["public_key_pem_ref"], "HOLD_NATIVE_TRUSTED_KEY_REF")
    pem = _read(root, anchor["public_key_pem_ref"])
    require(sha256(pem) == anchor["public_key_pem_sha256"], "HOLD_NATIVE_PUBLIC_KEY_DRIFT")
    key = serialization.load_pem_public_key(pem)
    raw = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    verifier = importlib.import_module("tools.total_field.w7tp_ed25519_verifier")
    require(Path(verifier.__file__).resolve() == root / "tools/total_field/w7tp_ed25519_verifier.py",
            "HOLD_NATIVE_VERIFIER_IMPORT_COORDINATE")
    result = verifier.validate_stage_b_signature(
        domain_separator="W7TP_FOUNDER_BREAK_GLASS_DIRECT_V1",
        packet_canonical_id="W7TP_FOUNDER_EXACT_UNMAPPED_EFFECT_V1",
        stage_b_object_without_signature=grant["body"], public_key_ref=anchor["public_key_pem_ref"],
        public_key_resolver=lambda _: raw,
        expected_public_key_fingerprint=anchor["ed25519_raw_public_key_fingerprint_sha256"],
        signature_hex=grant["stage_b_signature_hex"])
    require(result.valid is True, "HOLD_NATIVE_FOUNDER_SIGNATURE_INVALID")


def audit_paths(bundle: dict, synthetic_root: Path | None = None) -> dict[str, Path]:
    base = Path(AUDIT_BASE) if synthetic_root is None else synthetic_root / ".fixture-audit"
    operation = base / bundle["contract_sha256"]
    return {"base": base, "operation": operation, "authority": operation / "authority",
            "replay": base / "replay", "lock": base / "operation.lock",
            "grant": operation / "private-grant.json", "recovery": operation / "RECOVERY.json",
            "attempt": operation / "TRANSACTION_ATTEMPT.json", "journal": operation / "journal"}


def verify_native_receipt(root: Path, bundle: dict, paths: dict, grant: dict,
                          result: dict | None = None) -> dict:
    nonce_hash = sha256(grant["body"]["nonce"].encode())
    native_path = paths["authority"] / (nonce_hash + ".json")
    raw = file_bytes(native_path)
    receipt = _json(raw, "native_receipt")
    digest = receipt.get("receipt_sha256")
    unsigned = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    require(digest == sha256(canonical_bytes(unsigned)), "HOLD_NATIVE_RECEIPT_HASH")
    require(receipt.get("schema") == "W7TP_FOUNDER_SOVEREIGN_DIRECT_OVERRIDE_RECEIPT/1.0"
            and receipt.get("state") == "FOUNDER_SOVEREIGN_DIRECT_OVERRIDE"
            and receipt.get("effect") == bundle["effect"] and receipt.get("target") == LIVE_ROOT
            and receipt.get("human_direct") is True and receipt.get("single_use") is True
            and receipt.get("ai_agent_authority_expansion") is False,
            "HOLD_NATIVE_RECEIPT_SCOPE")
    body = grant["body"]
    require(body["git_head"] == bundle["contract"]["head"]
            and body["authority_preimage_sha256"] == bundle["contract"]["immutable_sources"][AUTHORITY_POINTER],
            "HOLD_NATIVE_RECEIPT_CONTRACT_COORDINATE")
    for key in ("git_head", "git_status_sha256", "authority_preimage_sha256"):
        require(receipt.get(key) == body[key], "HOLD_NATIVE_RECEIPT_PREIMAGE")
    require(receipt.get("nonce_sha256") == nonce_hash
            and receipt.get("signature_sha256") == sha256(grant["stage_b_signature_hex"].encode()),
            "HOLD_NATIVE_RECEIPT_GRANT_BINDING")
    coordinates = {"head": body["git_head"], "git_status_sha256": body["git_status_sha256"],
                   "authority_preimage_sha256": body["authority_preimage_sha256"]}
    validate_grant_shape(grant, bundle, coordinates, at=parse_time(receipt.get("validated_at")))
    marker = _json(file_bytes(paths["replay"] / (nonce_hash + ".json")), "nonce_marker")
    require(marker.get("native_receipt_sha256") == digest and marker.get("nonce_sha256") == nonce_hash
            and marker.get("permanent_replay_rejection") is True, "HOLD_NATIVE_REPLAY_PROOF")
    if result is not None:
        require(result.get("state") == "FOUNDER_SOVEREIGN_DIRECT_OVERRIDE"
                and result.get("authority_verified") is True and result.get("effect_authorized") is True
                and result.get("receipt_sha256") == digest and result.get("receipt_path") == str(native_path),
                "HOLD_NATIVE_RESULT_NOT_EXACT")
    return {"path": str(native_path), "sha256": digest, "file_sha256": sha256(raw),
            "validated_at": receipt["validated_at"], "nonce_sha256": nonce_hash}


def fixture_guard(root: Path) -> None:
    root = root.absolute()
    require(root != Path(LIVE_ROOT) and Path(LIVE_ROOT) not in root.parents
            and root.resolve() != Path(LIVE_ROOT) and Path(LIVE_ROOT) not in root.resolve().parents,
            "HOLD_SIMULATION_LIVE_ROOT_FORBIDDEN")
    marker = _json(_read(root, SIM_MARKER), SIM_MARKER)
    require(marker == {"synthetic_only": True, "formal_effect_authorized": False},
            "HOLD_SYNTHETIC_FIXTURE_REQUIRED")


def transaction(root: Path, bundle: dict, paths: dict, authorization: dict,
                *, simulation: bool, hook=None) -> dict:
    """Internal bounded writer. Production callers may only enter through apply.

    The hook is accepted only for explicit isolated simulation, never on live root.
    Receipt is the final commit marker. Native audit/replay survives every failure.
    """
    if simulation:
        fixture_guard(root)
        require(paths == audit_paths(bundle, root), "HOLD_SYNTHETIC_AUDIT_COORDINATE")
    else:
        require(hook is None and str(root) == LIVE_ROOT, "HOLD_TRANSACTION_COORDINATE")
        require(paths == audit_paths(bundle), "HOLD_NATIVE_AUDIT_COORDINATE")
        coordinates = live_coordinates(root, bundle)
        grant = _json(file_bytes(paths["grant"]), "private_local_grant")
        validate_grant_shape(grant, bundle, coordinates)
        module = native_module(root, bundle)
        verify_grant_signature(root, bundle, grant, module)
        verified = verify_native_receipt(root, bundle, paths, grant)
        require(authorization == verified, "HOLD_TRANSACTION_NATIVE_AUTHORIZATION")
    verify_preconditions(root, bundle["bundle_dir"], "PRE")
    leaf = root / LEAF
    directory(leaf.parent)
    require(not leaf.exists() and not leaf.is_symlink(), "HOLD_LEAF_ALREADY_EXISTS")
    registry = safe_path(root, REGISTRY)
    stage = registry.parent / (".gst-v21-" + bundle["contract_sha256"] + ".registry-stage")
    require(not stage.exists() and not stage.is_symlink(), "HOLD_STAGE_ALREADY_EXISTS")
    writes = {item["path"]: item for item in bundle["contract"]["static_writes"]}
    created: list[tuple[Path, str, list[int]]] = []
    swapped = False
    committed = False
    leaf_created = False
    leaf_identity = None
    stage_identity = None
    exchanged_identity = None
    exchanged_digest = None
    # O_EXCL durable marker makes this native authorization usable by this
    # executor at most once, including a direct library call after a failure.
    write_json_new(paths["attempt"], {"schema": "GST_V21_SINGLE_EXECUTION_ATTEMPT/1.0",
                   "contract_sha256": bundle["contract_sha256"],
                   "native_receipt_sha256": authorization.get("sha256"),
                   "started_at": utc(), "simulation": simulation,
                   "same_authorization_retry_permitted": False})
    directory(paths["journal"], create=True)
    def journal(name: str, details: dict) -> None:
        require(name in JOURNAL_EVENTS, "HOLD_JOURNAL_EVENT_NOT_BOUND")
        write_json_new(paths["journal"] / (name + ".json"),
                       {"event": name, "contract_sha256": bundle["contract_sha256"],
                        "at": utc(), "simulation": simulation, **details})
    def event(name: str) -> None:
        if hook is not None:
            hook(name, root, stage)
    try:
        journal("01_LEAF_CREATE_INTENT", {"path": LEAF, "preimage": "ABSENT"})
        leaf.mkdir(mode=0o755)
        leaf_created = True
        leaf_identity = inode_identity(leaf)[:2]
        fsync_dir(leaf.parent)
        journal("02_LEAF_CREATED", {"path": LEAF, "device_inode": leaf_identity})
        for ref, label, number in ((SPEC_TARGET, "SPEC", 3), (RECORD_TARGET, "RECORD", 5)):
            path = safe_path(root, ref)
            journal(f"{number:02d}_{label}_CREATE_INTENT", {"path": ref, "preimage": "ABSENT",
                    "postimage_sha256": writes[ref]["postimage_sha256"]})
            create_new(path, bundle["payloads"][ref], 0o644)
            identity = inode_identity(path)
            created.append((path, writes[ref]["postimage_sha256"], identity))
            journal(f"{number+1:02d}_{label}_CREATED", {"path": ref, "inode_identity": identity,
                    "postimage_sha256": writes[ref]["postimage_sha256"]})
        event("after_creates")
        journal("07_REGISTRY_STAGE_INTENT", {"path": str(stage.relative_to(root)),
                "postimage_sha256": writes[REGISTRY]["postimage_sha256"]})
        create_new(stage, bundle["payloads"][REGISTRY], 0o644)
        stage_identity = inode_identity(stage)
        journal("08_REGISTRY_STAGED", {"path": str(stage.relative_to(root)), "inode_identity": stage_identity})
        require(sha256(file_bytes(registry)) == writes[REGISTRY]["preimage_sha256"],
                "HOLD_REGISTRY_PRE_EXCHANGE_DRIFT")
        verify_immutable(root, bundle)
        journal("09_REGISTRY_EXCHANGE_INTENT", {"path": REGISTRY,
                "expected_preimage_sha256": writes[REGISTRY]["preimage_sha256"],
                "observed_inode_identity": inode_identity(registry), "stage_inode_identity": stage_identity})
        event("before_exchange")
        exchange(stage, registry)
        swapped = True
        exchanged_identity = inode_identity(stage)
        exchanged_digest = sha256(file_bytes(stage))
        journal("10_REGISTRY_EXCHANGED", {"path": REGISTRY, "registry_inode_identity": inode_identity(registry),
                "exchanged_inode_identity": exchanged_identity, "exchanged_sha256": exchanged_digest})
        require(exchanged_digest == writes[REGISTRY]["preimage_sha256"],
                "HOLD_REGISTRY_EXCHANGED_PREIMAGE_DRIFT")
        event("after_exchange")
        verify_preconditions(root, bundle["bundle_dir"], "POST")
        event("before_receipt")
        verify_preconditions(root, bundle["bundle_dir"], "POST")
        receipt = {
            "schema": SIM_RECEIPT_SCHEMA if simulation else FORMAL_RECEIPT_SCHEMA,
            "state": "SIMULATED_EFFECT_VERIFIED" if simulation else "EFFECT_VERIFIED",
            "contract_raw_sha256": bundle["contract_sha256"], "exact_effect": bundle["effect"],
            "target": str(root), "formal_effect_authorized": not simulation,
            "simulation": simulation, "native_authorization": authorization,
            "static_preimages": {p: w["preimage_sha256"] for p, w in writes.items()},
            "static_postimages": {p: w["postimage_sha256"] for p, w in writes.items()},
            "immutable_source_count": len(bundle["contract"]["immutable_sources"]),
            "immutable_source_verification": "PASS_CURRENT_READBACK",
            "published_at": utc(), "verification_result": "PASS_STATIC_POSTIMAGES",
            "runtime_activated": False, "evidence_maturity_promoted": False,
            "concurrency_boundary": "COOPERATIVE_LOCK_AND_EXCLUSIVE_LOCAL_CHANGE_WINDOW",
        }
        receipt["receipt_sha256"] = sha256(canonical_bytes(receipt))
        journal("11_RECEIPT_CREATE_INTENT", {"path": RECEIPT_TARGET,
                "receipt_sha256": receipt["receipt_sha256"]})
        write_json_new(root / RECEIPT_TARGET, receipt)
        committed = True
        journal("12_RECEIPT_CREATED", {"path": RECEIPT_TARGET,
                "inode_identity": inode_identity(root / RECEIPT_TARGET), "receipt_sha256": receipt["receipt_sha256"]})
        verify_preconditions(root, bundle["bundle_dir"], "POST")
        return {"state": receipt["state"], "formal_effect_authorized": not simulation,
                "contract_sha256": bundle["contract_sha256"],
                "receipt_path": RECEIPT_TARGET, "receipt_sha256": receipt["receipt_sha256"],
                "registry_preimage_preserved_at": str(stage),
                "runtime_activated": False, "simulation": simulation}
    except Exception as exc:
        code = exc.code if isinstance(exc, ContractError) else "HOLD_TRANSACTION_IO_OR_INJECTED_FAILURE"
        debt: list[str] = []
        restored = False
        if not committed:
            if swapped:
                try:
                    if (inode_identity(registry) == stage_identity
                            and sha256(file_bytes(registry)) == writes[REGISTRY]["postimage_sha256"]
                            and exchanged_identity is not None and inode_identity(stage) == exchanged_identity
                            and sha256(file_bytes(stage)) == exchanged_digest):
                        exchange(stage, registry)
                        restored = True
                    else:
                        debt.append("REGISTRY_OR_STAGE_EXTERNAL_CHANGE_PRESERVED_NO_AUTOMATIC_OVERWRITE")
                except (ContractError, OSError):
                    debt.append("REGISTRY_RECOVERY_REQUIRES_EXACT_CURRENT_STATE")
            if not swapped or restored:
                if stage.exists() and not unlink_owned(stage, writes[REGISTRY]["postimage_sha256"], stage_identity):
                    debt.append("UNKNOWN_STAGE_BYTES_PRESERVED")
            for path, digest, identity in reversed(created):
                if swapped and not restored:
                    debt.append("PARTIAL_TARGET_PRESERVED_PENDING_REGISTRY_RECOVERY:" + path.name)
                elif not unlink_owned(path, digest, identity):
                    debt.append("UNKNOWN_CREATED_TARGET_PRESERVED:" + path.name)
            if leaf_created and (not swapped or restored):
                try:
                    require(inode_identity(leaf)[:2] == leaf_identity, "HOLD_LEAF_OWNERSHIP_CHANGED")
                    leaf.rmdir()
                    fsync_dir(leaf.parent)
                except (OSError, ContractError):
                    debt.append("NONEMPTY_LEAF_PRESERVED")
        else:
            debt.append("RECEIPT_COMMITTED_NO_AUTOMATIC_WITHDRAWAL_NEW_EXACT_AUTHORITY_REQUIRED")
        recovery = {"schema": "GST_V21_PARTIAL_FAILURE_RECOVERY/1.0", "state": "HOLD",
                    "reason_code": code, "contract_sha256": bundle["contract_sha256"],
                    "receipt_committed": committed, "registry_exchange_reversed": restored,
                    "debt": debt, "native_audit_preserved": True,
                    "nonce_reuse_permitted": False, "observed_at": utc(),
                    "formal_effect_authorized": False, "simulation": simulation}
        try:
            write_json_new(paths["recovery"], recovery)
        except (OSError, ContractError):
            recovery["debt"].append("RECOVERY_RECORD_WRITE_FAILED_KEEP_NATIVE_AUDIT")
        return recovery


def dry_run(root: Path, bundle_dir: Path, *, simulation: bool = False) -> dict:
    bundle = load_bundle(bundle_dir)
    coordinates = None
    if simulation:
        fixture_guard(root)
    else:
        coordinates = live_coordinates(root, bundle)
    result = verify_preconditions(root, bundle_dir, "PRE")
    leaf = root / LEAF
    require(not leaf.exists() and not leaf.is_symlink(), "HOLD_LEAF_ALREADY_EXISTS")
    stage = root / "configs/total_field" / (".gst-v21-" + bundle["contract_sha256"] + ".registry-stage")
    require(not stage.exists() and not stage.is_symlink(), "HOLD_STAGE_ALREADY_EXISTS")
    result.update({"coordinates": coordinates, "effect": bundle["effect"],
                   "formal_effect_authorized": False, "simulation": simulation,
                   "exclusive_change_window_required_for_apply": True})
    return result


def probe_authority(root: Path, bundle_dir: Path) -> dict:
    bundle = load_bundle(bundle_dir)
    preflight = dry_run(root, bundle_dir)
    module = native_module(root, bundle)
    paths = audit_paths(bundle)
    result = module.resolve_founder_signed_break_glass_effect(
        repo_root=root, exact_effect=bundle["effect"], exact_target=LIVE_ROOT,
        signed_grant=None, nonce_ledger=None, receipt_dir=paths["authority"])
    require(result.get("effect_authorized") is False and result.get("authority_verified") is False,
            "HOLD_UNEXPECTED_UNSIGNED_NATIVE_RESPONSE")
    return {"schema": "GST_V21_EXACT_NATIVE_UNSIGNED_PROBE/1.0", "observed_at": utc(),
            "contract_sha256": bundle["contract_sha256"], "effect": bundle["effect"],
            "preflight": preflight, "native_result": result,
            "nonce_consumed": False, "audit_directories_created": False,
            "formal_effect_authorized": False, "writes_performed": False}


def apply(root: Path, bundle_dir: Path, grant_path: Path, *, exclusive_change_window: bool) -> dict:
    require(exclusive_change_window is True, "HOLD_EXCLUSIVE_LOCAL_CHANGE_WINDOW_REQUIRED")
    bundle = load_bundle(bundle_dir)
    coordinates = live_coordinates(root, bundle)
    dry_run(root, bundle_dir)
    grant = _json(file_bytes(grant_path, 65536), "private_grant_input")
    validate_grant_shape(grant, bundle, coordinates)
    module = native_module(root, bundle)
    verify_grant_signature(root, bundle, grant, module)
    paths = audit_paths(bundle)
    directory(paths["base"], create=True)
    base_info = paths["base"].lstat()
    require(base_info.st_uid == os.geteuid() and stat.S_IMODE(base_info.st_mode) & 0o077 == 0,
            "HOLD_AUDIT_STORAGE_PERMISSIONS")
    with operation_lock(paths["lock"]):
        require(not paths["operation"].exists(), "HOLD_OPERATION_EXISTS_READ_STATUS_OR_RECOVERY")
        directory(paths["authority"], create=True)
        directory(paths["replay"], create=True)
        write_json_new(paths["grant"], grant)
        try:
            dry_run(root, bundle_dir)
            result = module.resolve_founder_signed_break_glass_effect(
                repo_root=root, exact_effect=bundle["effect"], exact_target=LIVE_ROOT,
                signed_grant=grant, nonce_ledger=PersistentReplayLedger(paths["replay"]),
                receipt_dir=paths["authority"])
            fsync_dir(paths["authority"])
            if result.get("effect_authorized") is not True:
                result = {"state": "HOLD", "native_result": result, "formal_effect_authorized": False,
                          "nonce_consumption": "MAY_HAVE_OCCURRED_INSPECT_NATIVE_AUDIT_AND_REPLAY",
                          "blind_retry_permitted": False}
                write_json_new(paths["recovery"], result)
                return result
            authorization = verify_native_receipt(root, bundle, paths, grant, result)
            result = transaction(root, bundle, paths, authorization, simulation=False)
            return status(root, bundle_dir) if result.get("state") == "EFFECT_VERIFIED" else result
        except Exception as exc:
            recovery = {"state": "HOLD_AFTER_OPERATION_STARTED", "formal_effect_authorized": False,
                        "reason_code": exc.code if isinstance(exc, ContractError) else "HOLD_OPERATION_IO_FAILURE",
                        "nonce_consumption": "INSPECT_NATIVE_AUDIT_AND_REPLAY_DO_NOT_REUSE",
                        "receipt_may_exist": (root / RECEIPT_TARGET).exists(),
                        "automatic_withdrawal_permitted": False, "observed_at": utc()}
            try:
                write_json_new(paths["recovery"], recovery)
            except (OSError, ContractError):
                recovery["existing_audit_preserved"] = True
            return recovery


def simulate(root: Path, bundle_dir: Path, *, hook=None) -> dict:
    fixture_guard(root)
    bundle = load_bundle(bundle_dir)
    dry_run(root, bundle_dir, simulation=True)
    paths = audit_paths(bundle, root)
    directory(paths["authority"], create=True)
    directory(paths["replay"], create=True)
    with operation_lock(paths["lock"]):
        return transaction(root, bundle, paths,
                           {"state": "SYNTHETIC_TEST_ONLY", "effect_authorized": False},
                           simulation=True, hook=hook)


def status(root: Path, bundle_dir: Path, *, simulation: bool = False) -> dict:
    bundle = load_bundle(bundle_dir)
    if simulation:
        fixture_guard(root)
    else:
        live_coordinates(root, bundle)
    verify_preconditions(root, bundle_dir, "POST")
    receipt = _json(_read(root, RECEIPT_TARGET), "promotion_receipt")
    digest = receipt.get("receipt_sha256")
    require(digest == sha256(canonical_bytes({k:v for k,v in receipt.items() if k != "receipt_sha256"})),
            "HOLD_PROMOTION_RECEIPT_HASH")
    require(receipt.get("schema") == (SIM_RECEIPT_SCHEMA if simulation else FORMAL_RECEIPT_SCHEMA)
            and receipt.get("state") == ("SIMULATED_EFFECT_VERIFIED" if simulation else "EFFECT_VERIFIED")
            and receipt.get("simulation") is simulation
            and receipt.get("formal_effect_authorized") is (not simulation)
            and receipt.get("contract_raw_sha256") == bundle["contract_sha256"]
            and receipt.get("exact_effect") == bundle["effect"]
            and receipt.get("target") == str(root), "HOLD_PROMOTION_RECEIPT_BINDING")
    writes = {w["path"]:w for w in bundle["contract"]["static_writes"]}
    require(receipt.get("static_postimages") == {p:w["postimage_sha256"] for p,w in writes.items()}
            and receipt.get("static_preimages") == {p:w["preimage_sha256"] for p,w in writes.items()}
            and receipt.get("runtime_activated") is False
            and receipt.get("evidence_maturity_promoted") is False
            and receipt.get("verification_result") == "PASS_STATIC_POSTIMAGES"
            and receipt.get("immutable_source_verification") == "PASS_CURRENT_READBACK"
            and receipt.get("immutable_source_count") == len(bundle["contract"]["immutable_sources"]),
            "HOLD_PROMOTION_RECEIPT_IMAGE_BINDING")
    paths = audit_paths(bundle, root if simulation else None)
    attempt = _json(file_bytes(paths["attempt"]), "transaction_attempt")
    require(attempt.get("contract_sha256") == bundle["contract_sha256"]
            and attempt.get("same_authorization_retry_permitted") is False
            and attempt.get("simulation") is simulation, "HOLD_TRANSACTION_ATTEMPT_BINDING")
    for event in JOURNAL_EVENTS:
        journal = _json(file_bytes(paths["journal"] / (event + ".json")), "journal_event")
        require(journal.get("event") == event and journal.get("contract_sha256") == bundle["contract_sha256"]
                and journal.get("simulation") is simulation, "HOLD_DURABLE_OWNERSHIP_JOURNAL")
        if event == "12_RECEIPT_CREATED":
            require(journal.get("receipt_sha256") == digest, "HOLD_FINAL_JOURNAL_RECEIPT_BINDING")
    if not simulation:
        grant = _json(file_bytes(paths["grant"]), "private_local_grant")
        module = native_module(root, bundle)
        verify_grant_signature(root, bundle, grant, module)
        native = verify_native_receipt(root, bundle, paths, grant)
        require(attempt.get("native_receipt_sha256") == native["sha256"], "HOLD_ATTEMPT_NATIVE_RECEIPT_BINDING")
        require(receipt.get("native_authorization") == native, "HOLD_COLD_NATIVE_RECEIPT_BINDING")
        require(parse_time(receipt["published_at"]) >= parse_time(native["validated_at"]),
                "HOLD_PROMOTION_TIME_ORDER")
    return {"state": "SIMULATED_EFFECT_VERIFIED" if simulation else "EFFECT_VERIFIED",
            "contract_sha256": bundle["contract_sha256"], "receipt_sha256": digest,
            "formal_effect_authorized": not simulation, "runtime_activated": False,
            "nonce_consumed_during_status": False, "simulation": simulation}


def recovery_plan(root: Path, bundle_dir: Path, *, simulation: bool = False) -> dict:
    bundle = load_bundle(bundle_dir)
    if simulation:
        fixture_guard(root)
    else:
        live_coordinates(root, bundle)
    paths = audit_paths(bundle, root if simulation else None)
    observed = {}
    for entry in bundle["contract"]["static_writes"]:
        path = safe_path(root, entry["path"])
        observed[entry["path"]] = sha256(file_bytes(path)) if path.exists() else None
    receipt = safe_path(root, RECEIPT_TARGET)
    recovery = _json(file_bytes(paths["recovery"]), "recovery") if paths["recovery"].exists() else None
    return {"state": "RECOVERY_PLAN_ONLY", "contract_sha256": bundle["contract_sha256"],
            "current_images": observed, "receipt_exists": receipt.exists(), "recovery": recovery,
            "automatic_mutation_permitted": False, "nonce_reuse_permitted": False,
            "next": "EXACT_CURRENT_STATE_REVIEW_AND_NEW_AUTHORITY_FOR_WITHDRAWAL_OR_RETRY",
            "preserve_native_audit_and_replay": True, "formal_effect_authorized": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["dry-run", "probe-authority", "apply", "simulate", "status", "recovery-plan"])
    parser.add_argument("--bundle", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--root", type=Path, default=Path(LIVE_ROOT))
    parser.add_argument("--signed-grant", type=Path)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--exclusive-local-change-window", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "dry-run":
            result = dry_run(args.root, args.bundle, simulation=args.synthetic)
        elif args.command == "probe-authority":
            require(not args.synthetic, "HOLD_NATIVE_PROBE_CANNOT_BE_SYNTHETIC")
            result = probe_authority(args.root, args.bundle)
        elif args.command == "apply":
            require(not args.synthetic and args.signed_grant is not None, "HOLD_SIGNED_GRANT_REQUIRED")
            result = apply(args.root, args.bundle, args.signed_grant,
                           exclusive_change_window=args.exclusive_local_change_window)
        elif args.command == "simulate":
            require(args.synthetic, "HOLD_EXPLICIT_SYNTHETIC_FLAG_REQUIRED")
            result = simulate(args.root, args.bundle)
        elif args.command == "status":
            result = status(args.root, args.bundle, simulation=args.synthetic)
        else:
            result = recovery_plan(args.root, args.bundle, simulation=args.synthetic)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2 if result.get("state", "").startswith("HOLD") else 0
    except ContractError as exc:
        print(json.dumps({"state": "HOLD", "reason_code": exc.code, "path": exc.path,
                          "formal_effect_authorized": False}, ensure_ascii=False))
        return 2
    except Exception as exc:
        print(json.dumps({"state": "HOLD_UNEXPECTED_EXCEPTION", "exception_type": type(exc).__name__,
                          "formal_effect_authorized": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
