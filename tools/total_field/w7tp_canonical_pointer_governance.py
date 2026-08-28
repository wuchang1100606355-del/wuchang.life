"""W7TP current-active-canonical-pointer governance. Importing has no effects."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import unicodedata
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

from tools.total_field_authority_runtime_bindings import NONCE_REF

POINTER_REL = "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
POINTER_SCHEMA = "W7TP_ACTIVE_CANONICAL_POINTER_V1"
RECEIPT_SCHEMA = "W7TP_CURRENT_POINTER_BOOTSTRAP_RECEIPT_V1"
REQUEST_SCHEMA = "W7TP_CURRENT_POINTER_BOOTSTRAP_REQUEST_V1"
AUTH_SCHEMA = "W7TP_CURRENT_POINTER_BOOTSTRAP_AUTHORIZATION_V1"
BOOTSTRAP_SCOPE = "BOOTSTRAP_CURRENT_ACTIVE_CANONICAL_POINTER"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
RECEIPT_REF = re.compile(
    r"^runtime/total_field/master_index/receipts/[^/]+/POINTER_BOOTSTRAP_RECEIPT\.json$"
)


class PointerGovernanceError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    def clean(item: Any) -> Any:
        if isinstance(item, str):
            return unicodedata.normalize("NFC", item)
        if isinstance(item, list):
            return [clean(v) for v in item]
        if isinstance(item, dict):
            return {unicodedata.normalize("NFC", str(k)): clean(v) for k, v in item.items()}
        if isinstance(item, float):
            raise PointerGovernanceError("FLOAT_NOT_ALLOWED")
        return item
    return json.dumps(clean(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_time(value: object) -> float:
    if not isinstance(value, str):
        raise PointerGovernanceError("INVALID_TIME")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PointerGovernanceError("INVALID_TIME") from exc
    if parsed.tzinfo is None:
        raise PointerGovernanceError("TIMEZONE_REQUIRED")
    return parsed.timestamp()


def safe_rel(root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise PointerGovernanceError("INVALID_PATH")
    rel = PurePosixPath(value)
    if rel.is_absolute() or ".." in rel.parts:
        raise PointerGovernanceError("PATH_ESCAPE")
    current = root
    for part in rel.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise PointerGovernanceError("SYMLINK_PATH_REJECTED")
    return current


def git_canonical_bytes(root: Path, commit: object, locator: object) -> bytes:
    if not isinstance(commit, str) or COMMIT.fullmatch(commit) is None:
        raise PointerGovernanceError("INVALID_CANONICAL_COMMIT")
    if not isinstance(locator, str) or PurePosixPath(locator).is_absolute() or ".." in PurePosixPath(locator).parts:
        raise PointerGovernanceError("INVALID_CANONICAL_LOCATOR")
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "blob", f"{commit}:{locator}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        raise PointerGovernanceError("CANONICAL_GIT_OBJECT_MISSING")
    return result.stdout


def write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def authority_is_valid(
    resolver: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    subject: Mapping[str, Any],
    authority_id: object,
    authority_sha: object,
) -> Mapping[str, Any]:
    result = resolver(subject)
    if not isinstance(result, Mapping):
        raise PointerGovernanceError("AUTHORITY_INVALID")
    if result.get("state") != "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED" or result.get("authority_verified") is not True:
        raise PointerGovernanceError("AUTHORITY_INVALID")
    scopes = result.get("scope")
    if not isinstance(scopes, list) or BOOTSTRAP_SCOPE not in scopes:
        raise PointerGovernanceError("AUTHORITY_SCOPE_INVALID")
    if result.get("authority_id") != authority_id or result.get("authority_sha256") != authority_sha:
        raise PointerGovernanceError("AUTHORITY_BINDING_MISMATCH")
    return result


def resolve_current_active_canonical_pointer(
    *,
    repo_root: str | Path,
    expected_pointer_sha256: str | None = None,
    authority_validator: Callable[[Mapping[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    path = root / POINTER_REL
    if not path.exists():
        return {"state": "MISSING", "pointer_path": POINTER_REL}
    if not path.is_file() or path.is_symlink():
        return {"state": "INVALID", "reason": "POINTER_NOT_REGULAR_FILE", "pointer_path": POINTER_REL}
    data = path.read_bytes()
    pointer_sha = sha256(data)
    if expected_pointer_sha256 is not None and pointer_sha != expected_pointer_sha256:
        return {"state": "HASH_MISMATCH", "pointer_path": POINTER_REL, "pointer_sha256": pointer_sha}
    try:
        pointer = json.loads(data)
        required = {
            "schema_id": POINTER_SCHEMA,
            "pointer_state": "ACTIVE_CURRENT",
            "current": True,
            "active": True,
            "expected_preimage": "ABSENT",
            "creation_mode": "CREATE_IF_ABSENT",
        }
        if not isinstance(pointer, dict) or any(pointer.get(k) != v for k, v in required.items()):
            raise PointerGovernanceError("POINTER_FIELDS_INVALID")
        for key in ("canonical_sha256", "authority_sha256"):
            if not isinstance(pointer.get(key), str) or SHA256.fullmatch(pointer[key]) is None:
                raise PointerGovernanceError("POINTER_HASH_INVALID")
        canonical = git_canonical_bytes(root, pointer.get("canonical_commit"), pointer.get("canonical_locator"))
        if sha256(canonical) != pointer["canonical_sha256"]:
            raise PointerGovernanceError("CANONICAL_HASH_MISMATCH")
        receipt_ref = pointer.get("creation_receipt_ref")
        receipt_path = safe_rel(root, receipt_ref)
        if not receipt_path.is_file() or receipt_path.is_symlink():
            raise PointerGovernanceError("RECEIPT_MISSING")
        receipt = json.loads(receipt_path.read_bytes())
        receipt_hash = receipt.get("receipt_sha256")
        body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
        if (
            receipt.get("schema_id") != RECEIPT_SCHEMA
            or receipt.get("pointer_sha256") != pointer_sha
            or receipt.get("canonical_sha256") != pointer["canonical_sha256"]
            or not isinstance(receipt_hash, str)
            or sha256(canonical_bytes(body)) != receipt_hash
        ):
            raise PointerGovernanceError("RECEIPT_BINDING_INVALID")
        if authority_validator is None or authority_validator(pointer) is not True:
            return {"state": "AUTHORITY_INVALID", "pointer_path": POINTER_REL, "pointer_sha256": pointer_sha}
        return {
            "state": "FOUND_ACTIVE_AND_CURRENT",
            "pointer_path": POINTER_REL,
            "pointer_sha256": pointer_sha,
            "canonical_locator": pointer["canonical_locator"],
            "canonical_commit": pointer["canonical_commit"],
            "canonical_sha256": pointer["canonical_sha256"],
            "authority_id": pointer["authority_id"],
            "authority_sha256": pointer["authority_sha256"],
            "logical_time": pointer["logical_time"],
            "receipt_ref": receipt_ref,
            "receipt_sha256": receipt_hash,
        }
    except (PointerGovernanceError, UnicodeDecodeError, json.JSONDecodeError, OSError, TypeError) as exc:
        return {"state": "INVALID", "reason": str(exc), "pointer_path": POINTER_REL, "pointer_sha256": pointer_sha}


def create_current_active_canonical_pointer_if_absent(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path,
    nonce_ledger: object,
    signature_verifier: object,
    authority_resolver: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    dry_run: bool = False,
    now_epoch: float | None = None,
) -> dict[str, Any]:
    no_effect = {"pointer_created": False, "receipt_created": False}
    try:
        if not isinstance(request, Mapping) or request.get("schema_id") != REQUEST_SCHEMA:
            raise PointerGovernanceError("INVALID_REQUEST")
        if request.get("state") != "REQUEST_POINTER_BOOTSTRAP":
            raise PointerGovernanceError("INVALID_REQUEST_STATE")
        if request.get("pointer_ref") != POINTER_REL:
            raise PointerGovernanceError("NON_CANONICAL_POINTER_LOCATOR")
        if request.get("expected_preimage") != "ABSENT" or request.get("create_if_absent") is not True:
            raise PointerGovernanceError("INVALID_CAS_CONTRACT")
        if request.get("fail_if_already_exists") is not True:
            raise PointerGovernanceError("OVERWRITE_PROTECTION_REQUIRED")
        receipt_ref = request.get("receipt_ref")
        if not isinstance(receipt_ref, str) or RECEIPT_REF.fullmatch(receipt_ref) is None:
            raise PointerGovernanceError("INVALID_RECEIPT_REF")
        root = Path(repo_root).resolve()
        pointer_path = root / POINTER_REL
        if pointer_path.exists() or pointer_path.is_symlink():
            return {"state": "FAIL_ALREADY_EXISTS", **no_effect}
        canonical_sha = request.get("canonical_sha256")
        if not isinstance(canonical_sha, str) or SHA256.fullmatch(canonical_sha) is None:
            raise PointerGovernanceError("INVALID_CANONICAL_SHA256")
        canonical = git_canonical_bytes(root, request.get("canonical_commit"), request.get("canonical_locator"))
        if sha256(canonical) != canonical_sha:
            raise PointerGovernanceError("CANONICAL_HASH_MISMATCH")

        auth = request.get("authorization")
        if not isinstance(auth, Mapping) or auth.get("schema_id") != AUTH_SCHEMA:
            raise PointerGovernanceError("INVALID_AUTHORIZATION")
        bindings = {
            "state": "AUTHORIZED_SINGLE_POINTER_BOOTSTRAP",
            "scope": BOOTSTRAP_SCOPE,
            "pointer_ref": POINTER_REL,
            "expected_preimage": "ABSENT",
            "canonical_locator": request.get("canonical_locator"),
            "canonical_commit": request.get("canonical_commit"),
            "canonical_sha256": canonical_sha,
            "receipt_ref": receipt_ref,
        }
        if any(auth.get(k) != v for k, v in bindings.items()):
            raise PointerGovernanceError("AUTHORIZATION_BINDING_MISMATCH")
        if not isinstance(auth.get("authority_sha256"), str) or SHA256.fullmatch(auth["authority_sha256"]) is None:
            raise PointerGovernanceError("AUTHORITY_HASH_INVALID")
        nonce = auth.get("nonce_ref")
        if not isinstance(nonce, str) or NONCE_REF.fullmatch(nonce) is None:
            raise PointerGovernanceError("NONCE_REF_INVALID")
        issued = parse_time(auth.get("issued_at"))
        expires = parse_time(auth.get("expires_at"))
        now = time.time() if now_epoch is None else float(now_epoch)
        if not issued <= now < expires or expires - issued > 300:
            raise PointerGovernanceError("AUTHORIZATION_EXPIRED_OR_OVERSIZED")
        payload = {k: v for k, v in auth.items() if k not in {"payload_sha256", "signature"}}
        payload_sha = sha256(canonical_bytes(payload))
        if auth.get("payload_sha256") != payload_sha:
            raise PointerGovernanceError("AUTHORIZATION_PAYLOAD_HASH_MISMATCH")
        verify = getattr(signature_verifier, "verify_detached", None)
        if not callable(verify) or verify(
            verifier_ref=auth.get("verifier_ref"),
            payload_sha256=payload_sha,
            signature=auth.get("signature"),
        ) is not True:
            raise PointerGovernanceError("AUTHORIZATION_SIGNATURE_INVALID")
        authority_is_valid(
            authority_resolver,
            request,
            auth.get("authority_id"),
            auth.get("authority_sha256"),
        )

        pointer = {
            "schema_id": POINTER_SCHEMA,
            "pointer_state": "ACTIVE_CURRENT",
            "canonical_locator": request["canonical_locator"],
            "canonical_sha256": canonical_sha,
            "canonical_commit": request["canonical_commit"],
            "canonical_identity": request["canonical_identity"],
            "logical_time": request["logical_time"],
            "authority_id": auth["authority_id"],
            "authority_sha256": auth["authority_sha256"],
            "authorization_ref": request["authorization_ref"],
            "creation_receipt_ref": receipt_ref,
            "expected_preimage": "ABSENT",
            "creation_mode": "CREATE_IF_ABSENT",
            "current": True,
            "active": True,
        }
        pointer_data = canonical_bytes(pointer) + b"\n"
        pointer_sha = sha256(pointer_data)
        receipt_body = {
            "schema_id": RECEIPT_SCHEMA,
            "state": "POINTER_BOOTSTRAP_AUTHORIZED_APPEND_ONLY",
            "pointer_ref": POINTER_REL,
            "pointer_sha256": pointer_sha,
            "canonical_locator": request["canonical_locator"],
            "canonical_commit": request["canonical_commit"],
            "canonical_sha256": canonical_sha,
            "authority_id": auth["authority_id"],
            "authority_sha256": auth["authority_sha256"],
            "authorization_ref": request["authorization_ref"],
            "logical_time": request["logical_time"],
            "nonce_ref": nonce,
            "historical_receipt": False,
            "overwrite": False,
        }
        receipt_sha = sha256(canonical_bytes(receipt_body))
        receipt = dict(receipt_body, receipt_sha256=receipt_sha)
        preview = {
            "state": "PASS_POINTER_BOOTSTRAP_DRY_RUN",
            **no_effect,
            "pointer_path": POINTER_REL,
            "pointer_sha256": pointer_sha,
            "receipt_ref": receipt_ref,
            "receipt_sha256": receipt_sha,
        }
        if dry_run:
            return preview

        pointer_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = pointer_path.parent / ".active_w7tp_pointer_bootstrap.lock"
        with lock_path.open("a+b") as lock:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            if pointer_path.exists() or pointer_path.is_symlink():
                return {"state": "FAIL_ALREADY_EXISTS", **no_effect}
            consume = getattr(nonce_ledger, "mark_used_or_replay", None)
            if not callable(consume) or consume(nonce, payload_sha, now, max(1, int(expires - now))) is not True:
                raise PointerGovernanceError("NONCE_REPLAY_OR_LEDGER_FAILURE")
            receipt_path = safe_rel(root, receipt_ref)
            if receipt_path.exists() or receipt_path.parent.exists():
                raise PointerGovernanceError("RECEIPT_COLLISION")
            receipt_path.parent.mkdir(parents=True, exist_ok=False)
            write_new(receipt_path, canonical_bytes(receipt) + b"\n")
            temp_path = Path(tempfile.mkstemp(prefix=".ACTIVE_W7TP_CANONICAL_POINTER.", dir=pointer_path.parent)[1])
            try:
                temp_path.write_bytes(pointer_data)
                with temp_path.open("rb") as stream:
                    os.fsync(stream.fileno())
                os.link(temp_path, pointer_path)
            except FileExistsError:
                return {"state": "FAIL_ALREADY_EXISTS", **no_effect}
            finally:
                temp_path.unlink(missing_ok=True)
        return {
            **preview,
            "state": "PASS_POINTER_BOOTSTRAP_CREATED",
            "pointer_created": True,
            "receipt_created": True,
        }
    except (PointerGovernanceError, OSError, TypeError, ValueError) as exc:
        return {"state": "HOLD_POINTER_BOOTSTRAP", "reason": str(exc), **no_effect}


__all__ = [
    "BOOTSTRAP_SCOPE",
    "POINTER_REL",
    "create_current_active_canonical_pointer_if_absent",
    "resolve_current_active_canonical_pointer",
]
