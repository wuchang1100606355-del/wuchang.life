from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(data: str | bytes) -> str:
    payload = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha256(payload).hexdigest()


def canonical_hash(obj: Any) -> str:
    return sha256_hex(canonical_json(obj))


def _seal_hash(obj: Any) -> tuple[str, str]:
    key = os.getenv("W7TP_HMAC_KEY")
    payload = canonical_json(obj).encode("utf-8")
    if key:
        digest = hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return digest, "HMAC_SHA256"
    return hashlib.sha256(payload).hexdigest(), "UNKEYED_DEV_HASH"


def state_seal(
    packet: dict[str, Any] | None = None,
    state: str | None = None,
    node: str | None = None,
    timestamp: int | None = None,
    coordinate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    canonical = {
        "packet": packet or {},
        "state": state or "TRANSACTION_COMMITTED",
        "node": node or "MSI-WSL",
        "timestamp": timestamp or 0,
        "coordinate": coordinate or {},
    }
    packet_hash = canonical_hash(canonical["packet"])
    state_hash, mode = _seal_hash(
        {
            "packet_hash": packet_hash,
            "state": canonical["state"],
            "node": canonical["node"],
            "timestamp": canonical["timestamp"],
            "coordinate": canonical["coordinate"],
        }
    )
    coordinate_hash = canonical_hash(canonical["coordinate"])
    ledger_hash = canonical_hash(
        {
            "packet_hash": packet_hash,
            "state_hash": state_hash,
            "coordinate_hash": coordinate_hash,
        }
    )
    canonical["hash_mode"] = mode
    return {
        "ok": True,
        "packet_hash": packet_hash,
        "state_hash": state_hash,
        "coordinate_hash": coordinate_hash,
        "ledger_hash": ledger_hash,
        "canonical": canonical,
    }
