"""Fail-closed W7TP governed promotion capability. Importing this module has no effects."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

from tools.total_field_authority_runtime_bindings import NONCE_REF

SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUEST_SCHEMA = "W7TP_GOVERNED_PROMOTION_REQUEST_V1"
AUTH_SCHEMA = "W7TP_SINGLE_USE_PROMOTION_AUTHORIZATION_V1"
DECISION_SCHEMA = "W7TP_TOTAL_FIELD_FORMAL_CANDIDATE_DECISION_EVIDENCE_V1"
ACCEPTED_DECISION = "ALLOW_CANDIDATE_ACCEPTED"
REQUIRED_SCOPE = "PROMOTE_ACCEPTED_CANDIDATE"


class PromotionRejected(RuntimeError):
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
            raise PromotionRejected("FLOAT_NOT_ALLOWED")
        return item
    return json.dumps(clean(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_time(value: object) -> float:
    if not isinstance(value, str):
        raise PromotionRejected("INVALID_TIME")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PromotionRejected("INVALID_TIME") from exc
    if parsed.tzinfo is None:
        raise PromotionRejected("TIMEZONE_REQUIRED")
    return parsed.timestamp()


def safe_path(root: Path, value: object, *, promotion_output: bool = False) -> Path:
    if not isinstance(value, str) or not value:
        raise PromotionRejected("INVALID_PATH")
    rel = PurePosixPath(value)
    if rel.is_absolute() or ".." in rel.parts:
        raise PromotionRejected("PATH_ESCAPE")
    if promotion_output and (len(rel.parts) != 4 or rel.parts[:3] != ("runtime", "total_field", "promotions")):
        raise PromotionRejected("INVALID_PROMOTION_OUTPUT")
    current = root
    for part in rel.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise PromotionRejected("SYMLINK_PATH_REJECTED")
    return current


def read_bound(root: Path, ref: object, expected: object) -> tuple[Path, bytes]:
    if not isinstance(expected, str) or SHA256.fullmatch(expected) is None:
        raise PromotionRejected("INVALID_EXPECTED_SHA256")
    path = safe_path(root, ref)
    if not path.is_file() or path.is_symlink():
        raise PromotionRejected("BOUND_OBJECT_MISSING")
    data = path.read_bytes()
    if sha256(data) != expected:
        raise PromotionRejected("BOUND_OBJECT_HASH_DRIFT")
    return path, data


def read_json_bound(root: Path, ref: object, expected: object) -> tuple[Path, dict[str, Any]]:
    path, data = read_bound(root, ref, expected)
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromotionRejected("INVALID_JSON") from exc
    if not isinstance(value, dict):
        raise PromotionRejected("JSON_OBJECT_REQUIRED")
    return path, value


def formal_total_field_decision(evidence: Mapping[str, Any]) -> object:
    """Read the decision from the formal Total Field producer contract."""
    result = evidence.get("total_field_result")
    if not isinstance(result, Mapping):
        raise PromotionRejected("INVALID_TOTAL_FIELD_DECISION_EVIDENCE")
    decision = result.get("decision")
    if (
        decision != result.get("state")
        or decision != result.get("owner_receive_candidate_state")
    ):
        raise PromotionRejected("TOTAL_FIELD_DECISION_CONTRACT_MISMATCH")
    return decision


def write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def resolve_authority(resolver: Callable[[Mapping[str, Any]], Mapping[str, Any]], request: Mapping[str, Any]) -> Mapping[str, Any]:
    result = resolver(request)
    if not isinstance(result, Mapping):
        raise PromotionRejected("AUTHORITY_RESOLVER_INVALID")
    if result.get("state") != "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED" or result.get("authority_verified") is not True:
        raise PromotionRejected("ACTIVE_AUTHORITY_NOT_VERIFIED")
    scopes = result.get("scope")
    if not isinstance(scopes, list) or REQUIRED_SCOPE not in scopes:
        raise PromotionRejected("PROMOTION_SCOPE_NOT_GRANTED")
    return result


def consume_nonce(ledger: object, nonce: str, packet_hash: str, now: float, ttl: int) -> None:
    method = getattr(ledger, "mark_used_or_replay", None)
    if not callable(method):
        raise PromotionRejected("NONCE_LEDGER_INTERFACE_MISSING")
    try:
        fresh = method(nonce=nonce, packet_hash=packet_hash, now_epoch=now, ttl_seconds=ttl)
    except TypeError:
        fresh = method(nonce, packet_hash, now, ttl)
    if fresh is not True:
        raise PromotionRejected("AUTHORIZATION_NONCE_REPLAY")


def promote_accepted_candidate(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path,
    nonce_ledger: object,
    signature_verifier: object,
    authority_resolver: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    dry_run: bool = False,
    now_epoch: float | None = None,
) -> dict[str, Any]:
    """Validate and optionally commit exactly one accepted-candidate promotion."""
    no_effects = {
        "promotion": False,
        "activation": False,
        "canonical_mutation": False,
        "active_pointer_mutation": False,
        "final_authority_granted": False,
    }
    try:
        if not isinstance(request, Mapping):
            raise PromotionRejected("INVALID_REQUEST")
        if request.get("schema_id") != REQUEST_SCHEMA or request.get("state") != "REQUEST_SINGLE_PROMOTION":
            raise PromotionRejected("INVALID_REQUEST")
        if request.get("historical_receipt_reconstruction") is not False:
            raise PromotionRejected("HISTORICAL_RECEIPT_RECONSTRUCTION_FORBIDDEN")
        root = Path(repo_root).resolve()
        candidate_path, _ = read_bound(root, request.get("candidate_artifact_ref"), request.get("candidate_sha256"))
        decision_path, decision = read_json_bound(root, request.get("decision_evidence_ref"), request.get("decision_evidence_sha256"))
        if decision.get("schema_id") != DECISION_SCHEMA or decision.get("state") != "TOTAL_FIELD_DECISION_OBTAINED":
            raise PromotionRejected("INVALID_TOTAL_FIELD_DECISION_EVIDENCE")
        if decision.get("candidate_sha256") != request.get("candidate_sha256"):
            raise PromotionRejected("DECISION_CANDIDATE_BINDING_MISMATCH")
        if formal_total_field_decision(decision) != ACCEPTED_DECISION or request.get("total_field_decision") != ACCEPTED_DECISION:
            raise PromotionRejected("TOTAL_FIELD_DECISION_NOT_ACCEPTED")
        current_path, _ = read_bound(root, request.get("current_canonical_ref"), request.get("current_canonical_sha256"))
        target_path, _ = read_bound(root, request.get("target_canonical_ref"), request.get("target_canonical_sha256"))
        pointer_path, pointer = read_json_bound(root, request.get("active_pointer_ref"), request.get("active_pointer_sha256"))

        auth = request.get("promotion_authorization")
        if not isinstance(auth, Mapping) or auth.get("schema_id") != AUTH_SCHEMA or auth.get("state") != "AUTHORIZED_SINGLE_PROMOTION":
            raise PromotionRejected("INVALID_PROMOTION_AUTHORIZATION")
        bindings = {
            "scope": REQUIRED_SCOPE,
            "candidate_sha256": request.get("candidate_sha256"),
            "decision_evidence_sha256": request.get("decision_evidence_sha256"),
            "current_canonical_sha256": request.get("current_canonical_sha256"),
            "target_canonical_sha256": request.get("target_canonical_sha256"),
            "active_pointer_preimage_sha256": request.get("active_pointer_sha256"),
        }
        if any(auth.get(k) != v for k, v in bindings.items()):
            raise PromotionRejected("AUTHORIZATION_BINDING_MISMATCH")
        nonce = auth.get("nonce_ref")
        if not isinstance(nonce, str) or NONCE_REF.fullmatch(nonce) is None:
            raise PromotionRejected("INVALID_AUTHORIZATION_NONCE")
        issued = parse_time(auth.get("issued_at"))
        expires = parse_time(auth.get("expires_at"))
        now = time.time() if now_epoch is None else float(now_epoch)
        if not issued <= now < expires or expires - issued > 300:
            raise PromotionRejected("AUTHORIZATION_EXPIRED_OR_OVERSIZED")
        payload = {k: v for k, v in auth.items() if k not in {"payload_sha256", "signature"}}
        payload_sha = sha256(canonical_bytes(payload))
        if auth.get("payload_sha256") != payload_sha:
            raise PromotionRejected("AUTHORIZATION_PAYLOAD_HASH_MISMATCH")
        verifier = getattr(signature_verifier, "verify_detached", None)
        if not callable(verifier) or verifier(
            verifier_ref=auth.get("verifier_ref"),
            payload_sha256=payload_sha,
            signature=auth.get("signature"),
        ) is not True:
            raise PromotionRejected("AUTHORIZATION_SIGNATURE_INVALID")
        authority = resolve_authority(authority_resolver, request)
        if authority.get("authority_id") != auth.get("authority_id"):
            raise PromotionRejected("AUTHORITY_ID_MISMATCH")
        consume_nonce(nonce_ledger, nonce, payload_sha, now, max(1, int(expires - now)))

        output_dir = safe_path(root, request.get("promotion_output_ref"), promotion_output=True)
        if output_dir.exists():
            raise PromotionRejected("PROMOTION_OUTPUT_COLLISION")
        receipt_body = {
            "schema_id": "W7TP_APPEND_ONLY_PROMOTION_RECEIPT_V1",
            "state": "PROMOTED_PENDING_ACTIVATION",
            "candidate_ref": request["candidate_artifact_ref"],
            "candidate_sha256": request["candidate_sha256"],
            "decision_evidence_ref": request["decision_evidence_ref"],
            "decision_evidence_sha256": request["decision_evidence_sha256"],
            "total_field_decision": ACCEPTED_DECISION,
            "authority_id": auth["authority_id"],
            "authorization_payload_sha256": payload_sha,
            "authorization_nonce_ref": nonce,
            "current_canonical_sha256": request["current_canonical_sha256"],
            "target_canonical_sha256": request["target_canonical_sha256"],
            "active_pointer_preimage_sha256": request["active_pointer_sha256"],
            "promotion": True,
            "activation": False,
            "final_authority_granted": False,
            "canonical_content_mutated": False,
            "historical_receipt_reconstructed": False,
            "issued_at": datetime.fromtimestamp(now, timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        receipt_sha = sha256(canonical_bytes(receipt_body))
        receipt = dict(receipt_body, receipt_sha256=receipt_sha)
        next_pointer = dict(pointer)
        next_pointer["promotion_state"] = "PROMOTED_PENDING_ACTIVATION"
        next_pointer["pending_promotion"] = {
            "candidate_sha256": request["candidate_sha256"],
            "target_canonical_sha256": request["target_canonical_sha256"],
            "promotion_receipt_sha256": receipt_sha,
            "activation": False,
            "final_authority_granted": False,
        }
        preview = {
            "state": "PASS_GOVERNED_PROMOTION_DRY_RUN",
            **no_effects,
            "receipt_sha256": receipt_sha,
            "pointer_preimage_sha256": request["active_pointer_sha256"],
            "pointer_postimage_sha256": sha256(canonical_bytes(next_pointer) + b"\n"),
            "candidate_verified": candidate_path.relative_to(root).as_posix(),
            "decision_verified": decision_path.relative_to(root).as_posix(),
            "current_canonical_verified": current_path.relative_to(root).as_posix(),
            "target_canonical_verified": target_path.relative_to(root).as_posix(),
        }
        if dry_run:
            return preview

        output_dir.parent.mkdir(parents=True, exist_ok=True)
        lock_path = output_dir.parent / ".promotion.lock"
        with lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            if output_dir.exists() or sha256(pointer_path.read_bytes()) != request["active_pointer_sha256"]:
                raise PromotionRejected("PROMOTION_CAS_PRECONDITION_FAILED")
            staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
            write_new(staging / "PROMOTION_RECEIPT.json", canonical_bytes(receipt) + b"\n")
            write_new(staging / "STATE_TRANSITION.json", canonical_bytes({
                "schema_id": "W7TP_PROMOTION_STATE_TRANSITION_V1",
                "from": "CANDIDATE_ACCEPTED",
                "to": "PROMOTED_PENDING_ACTIVATION",
                "receipt_sha256": receipt_sha,
                "activation": False,
                "final_authority_granted": False,
            }) + b"\n")
            os.replace(staging, output_dir)
            pointer_tmp = pointer_path.with_name(f".{pointer_path.name}.{os.getpid()}.tmp")
            write_new(pointer_tmp, canonical_bytes(next_pointer) + b"\n")
            if sha256(pointer_path.read_bytes()) != request["active_pointer_sha256"]:
                pointer_tmp.unlink()
                raise PromotionRejected("PROMOTION_CAS_PRECONDITION_FAILED")
            os.replace(pointer_tmp, pointer_path)
        return {
            **preview,
            "state": "PASS_GOVERNED_PROMOTION",
            "promotion": True,
            "active_pointer_mutation": True,
            "promotion_receipt": (output_dir / "PROMOTION_RECEIPT.json").relative_to(root).as_posix(),
        }
    except PromotionRejected as exc:
        return {"state": "HOLD_GOVERNED_PROMOTION", "reason": str(exc), **no_effects}


__all__ = ["promote_accepted_candidate"]
