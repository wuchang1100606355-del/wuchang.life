from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from tools.total_field_authority_runtime_bindings import (
    AuthorityRuntimeBindings,
    build_authority_runtime_bindings,
)
from tools.total_field_dynamic_context import build_active_authority_receive_candidate
from tools.total_field_ed25519_backend import Ed25519DetachedSignatureBackend


GATE_CONFIG_REL = Path("configs/total_field/git_push_review_gate_v1.json")
RECEIVE_CANDIDATE_LEDGER_REL = Path(
    "runtime/total_field/runtime_state/receive_candidate_authority_nonce_ledger.sqlite3"
)
RECEIVE_CANDIDATE_SCOPE = "RECEIVE_CANDIDATE"
AUTHORITY_MODE = "D8_PASSKEY_PRIMARY_ACTIVE_AUTHORITY_COMPATIBILITY"


class FailClosedSignatureBackend:
    """Fallback backend used only when the compatibility verifier key is unavailable."""

    secret_material_access = False
    private_key_access = False

    def verify_detached(
        self,
        *,
        verifier_ref: str,
        payload_sha256: str,
        signature: str,
    ) -> bool:
        del verifier_ref, payload_sha256, signature
        return False


@dataclass
class CandidateIngressRuntime:
    bindings: AuthorityRuntimeBindings
    receiver: Callable[
        [Mapping[str, Any], Mapping[str, Any] | None, Any],
        dict[str, Any],
    ]
    authority_mode: str = AUTHORITY_MODE
    compatibility_signature_verifier_state: str = "FAIL_CLOSED"

    def close(self) -> None:
        self.bindings.close()


def _repo_relative_path(root: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"HOLD_CANDIDATE_INGRESS_{field.upper()}_MISSING")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"BLOCK_CANDIDATE_INGRESS_{field.upper()}_INVALID")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(
            f"BLOCK_CANDIDATE_INGRESS_{field.upper()}_OUTSIDE_REPO"
        ) from exc
    return resolved


def _load_gate_config(root: Path) -> dict[str, Any]:
    path = (root / GATE_CONFIG_REL).resolve()
    try:
        path.relative_to(root / "configs" / "total_field")
    except ValueError as exc:
        raise RuntimeError("BLOCK_CANDIDATE_INGRESS_CONFIG_PATH") from exc
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("HOLD_CANDIDATE_INGRESS_CONFIG_UNAVAILABLE")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("HOLD_CANDIDATE_INGRESS_CONFIG_INVALID") from exc
    if not isinstance(value, dict):
        raise RuntimeError("HOLD_CANDIDATE_INGRESS_CONFIG_INVALID")
    return value


def build_candidate_ingress_runtime(
    repo_root: str | Path,
) -> CandidateIngressRuntime:
    """
    Bind RECEIVE_CANDIDATE into the live runtime without granting execution
    authority. D8 passkey verification is the primary authority path. The signed
    ACTIVE_TOTAL_FIELD_AUTHORITY resolver remains compatibility-only and fails
    closed when its public verifier is unavailable.
    """
    root = Path(repo_root).resolve()
    gate = _load_gate_config(root)

    passkey_config = gate.get("passkey_verifier")
    if not isinstance(passkey_config, Mapping):
        raise RuntimeError("HOLD_CANDIDATE_INGRESS_PASSKEY_CONFIG_MISSING")
    allowed_scopes = passkey_config.get("allowed_effect_scopes") or []
    if (
        passkey_config.get("enabled") is not True
        or RECEIVE_CANDIDATE_SCOPE not in allowed_scopes
    ):
        raise RuntimeError("HOLD_CANDIDATE_INGRESS_PASSKEY_NOT_ACTIVE")

    signature_config = gate.get("signature_verifier")
    if not isinstance(signature_config, Mapping):
        raise RuntimeError("HOLD_CANDIDATE_INGRESS_SIGNATURE_CONFIG_MISSING")
    trusted_refs = tuple(
        str(item) for item in (signature_config.get("trusted_verifier_refs") or [])
    )
    if not trusted_refs:
        raise RuntimeError("HOLD_CANDIDATE_INGRESS_TRUSTED_VERIFIER_MISSING")

    backend: Any = FailClosedSignatureBackend()
    verifier_state = "FAIL_CLOSED_COMPATIBILITY_VERIFIER"
    public_key_path = _repo_relative_path(
        root,
        signature_config.get("public_key_ref"),
        "public_key_ref",
    )
    if public_key_path.is_file() and not public_key_path.is_symlink():
        try:
            backend = Ed25519DetachedSignatureBackend(
                public_key_path,
                trusted_verifier_refs=trusted_refs,
            )
            verifier_state = "ED25519_COMPATIBILITY_VERIFIER_READY"
        except (OSError, ValueError):
            backend = FailClosedSignatureBackend()
            verifier_state = "FAIL_CLOSED_COMPATIBILITY_VERIFIER"

    bindings = build_authority_runtime_bindings(
        ledger_path=root / RECEIVE_CANDIDATE_LEDGER_REL,
        signature_backend=backend,
        trusted_verifier_refs=trusted_refs,
    )
    try:
        receiver = build_active_authority_receive_candidate(
            repo_root=root,
            nonce_ledger=bindings.nonce_ledger,
            signature_verifier=bindings.signature_verifier,
            trusted_verifier_refs=bindings.trusted_verifier_refs,
        )
    except Exception:
        bindings.close()
        raise

    return CandidateIngressRuntime(
        bindings=bindings,
        receiver=receiver,
        compatibility_signature_verifier_state=verifier_state,
    )


__all__ = [
    "AUTHORITY_MODE",
    "CandidateIngressRuntime",
    "RECEIVE_CANDIDATE_SCOPE",
    "build_candidate_ingress_runtime",
]
