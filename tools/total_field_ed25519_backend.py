from __future__ import annotations

import base64
import binascii
import re
from pathlib import Path
from typing import Collection

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class Ed25519DetachedSignatureBackend:
    """Production detached-signature verifier for Total Field authority digests."""

    algorithm = "Ed25519"
    secret_material_access = False
    private_key_access = False

    def __init__(self, public_key_path: str | Path, *, trusted_verifier_refs: Collection[str]) -> None:
        path = Path(public_key_path)
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 8192:
            raise ValueError("public key path is invalid")
        key = serialization.load_pem_public_key(path.read_bytes())
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError("public key is not Ed25519")
        refs = tuple(sorted({str(item) for item in trusted_verifier_refs}))
        if not refs:
            raise ValueError("trusted verifier reference is required")
        self._public_key = key
        self.trusted_verifier_refs = refs

    def verify_detached(self, *, verifier_ref: str, payload_sha256: str, signature: str) -> bool:
        if verifier_ref not in self.trusted_verifier_refs or _SHA256.fullmatch(payload_sha256 or "") is None:
            return False
        if not isinstance(signature, str) or not signature.startswith("ed25519:"):
            return False
        encoded = signature.split(":", 1)[1]
        try:
            raw = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
            self._public_key.verify(raw, payload_sha256.encode("ascii"))
        except (ValueError, binascii.Error, InvalidSignature):
            return False
        return True


__all__ = ["Ed25519DetachedSignatureBackend"]
