from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contract import KDF_ITERATIONS, KEY_BYTES
from .foundation import sha256_bytes


def derive_key(passphrase: str, fingerprint: str, salt: bytes) -> bytes:
    material = f"{fingerprint}\0{passphrase}".encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", material, salt, KDF_ITERATIONS, dklen=KEY_BYTES)


def envelope_id(envelope: dict[str, Any]) -> str:
    clone = dict(envelope)
    clone.pop("envelope_id", None)
    data = json.dumps(clone, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(data)


def used_marker_path(used_dir: Path, envelope: dict[str, Any]) -> Path:
    return used_dir / f"{envelope['envelope_id']}.used.json"
