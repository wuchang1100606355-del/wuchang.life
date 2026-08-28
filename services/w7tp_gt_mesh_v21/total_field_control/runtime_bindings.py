"""Bindings to the established Total Field Ed25519 verifier; no private key path."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from w7tp_gt_mesh.core import MeshHold


EXPECTED_BACKEND = "tools.total_field_ed25519_backend:Ed25519DetachedSignatureBackend"


def build_production_signature_verifier(
    authority_profile: Mapping[str, object],
    *,
    repository_root: str | Path,
) -> object:
    signature = authority_profile.get("signature_verifier")
    if (
        not isinstance(signature, Mapping)
        or signature.get("algorithm") != "Ed25519"
        or signature.get("implementation") != EXPECTED_BACKEND
    ):
        raise MeshHold("HOLD_TOTAL_FIELD_ED25519_BINDING_INVALID")
    public_key_ref = signature.get("public_key_ref")
    trusted_refs = signature.get("trusted_verifier_refs")
    if not isinstance(public_key_ref, str) or not isinstance(trusted_refs, list) or not trusted_refs:
        raise MeshHold("HOLD_TOTAL_FIELD_ED25519_PROFILE_INVALID")
    root = Path(repository_root).resolve(strict=True)
    unresolved = root / public_key_ref
    if unresolved.is_symlink():
        raise MeshHold("HOLD_TOTAL_FIELD_PUBLIC_KEY_PATH_INVALID")
    candidate = unresolved.resolve(strict=True)
    if root not in candidate.parents:
        raise MeshHold("HOLD_TOTAL_FIELD_PUBLIC_KEY_PATH_INVALID")
    try:
        from tools.total_field_ed25519_backend import Ed25519DetachedSignatureBackend
    except (ImportError, AttributeError) as exc:
        raise MeshHold("HOLD_TOTAL_FIELD_ED25519_BACKEND_UNAVAILABLE") from exc
    try:
        return Ed25519DetachedSignatureBackend(
            candidate,
            trusted_verifier_refs=[str(item) for item in trusted_refs],
        )
    except (OSError, TypeError, ValueError) as exc:
        raise MeshHold("HOLD_TOTAL_FIELD_ED25519_BACKEND_INIT_FAILED") from exc
