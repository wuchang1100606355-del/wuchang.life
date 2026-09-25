#!/usr/bin/env python3
"""Founder identity and variable cognition package governance gate.

This module is local and side-effect free. It does not read secrets, write a
database, deploy, restart services, activate cloud models, or mutate packages.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from copy import deepcopy
from datetime import datetime
from typing import Any, Mapping, Sequence


ALLOW = "ALLOW"
BLOCK = "BLOCK"
HOLD = "HOLD"
QUARANTINED = "QUARANTINED"

# Compatibility names only. Neither value participates in authorization.
FOUNDER_LOCAL_ID = "DEPRECATED_NAME_OR_STRING_ONLY_NO_AUTHORITY"
FOUNDER_GOOGLE_ACCOUNT_BINDING_REF = "DEPRECATED_OPAQUE_ACCOUNT_STRING_NO_AUTHORITY"
FOUNDER_ROLE = "FOUNDER"
FOUNDER_ROOT_SCHEMA_VERSION = "w7tp.founder-dual-root/v1.0"
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
DEVICE_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")
SENSITIVE_IDENTITY_KEYS = frozenset(
    {
        "access_token",
        "authorization",
        "credential",
        "email",
        "id_token",
        "password",
        "refresh_token",
        "secret",
        "token",
    }
)
LEGACY_AUTHORITY_KEYS = frozenset(
    {
        "founder_natural_person",
        "google_account_binding_ref",
        "local_founder_id",
    }
)

FUTURE_IDENTITY_ADAPTERS = {
    "tw_moi_digital_natural_person_id": "DISABLED_NOT_CONFIGURED",
    "physical_natural_person_certificate_card": "DISABLED_NOT_CONFIGURED",
}
EXPECTED_IDENTITY_REQUEST_KEYS = {
    "device_principal_fingerprint",
    "google_oidc_issuer",
    "google_oidc_subject_sha256",
    "explicit_founder_command",
    "founder_command_ref",
    "d8_decision",
    "future_identity_adapters",
}

LIFECYCLE_STATES = (
    "DISCOVERED",
    "CANDIDATE",
    "VERIFIED",
    "ENABLED",
    "DISABLED",
    "QUARANTINED",
)
FOUNDER_ONLY_ACTIONS = {"install", "enable", "update", "disable", "remove"}
CANDIDATE_ACTORS = {"FOUNDER", "PERSONNEL", "ADMIN", "AI", "NODE"}
SAFE_PERMISSIONS = {
    "read_public_reference",
    "read_package_state",
    "emit_candidate",
    "execute_local_verified_reconstruction",
    "write_package_evidence",
}
FORBIDDEN_CAPABILITIES = {
    "modify_total_field_canonical",
    "modify_founder_identity_root",
    "modify_d8_rules",
    "self_elevate_permissions",
    "cloud_model_auto_enable",
}
REQUIRED_MANIFEST_FIELDS = {
    "package_id",
    "name",
    "version",
    "sha256",
    "source_ref",
    "capability_scope",
    "requested_permissions",
    "allowed_nodes",
    "compatibility",
    "reconstruction_conditions",
    "packet_carried_protocol",
    "packet_carried_validation",
    "evidence_refs",
    "risk_status",
    "installed_by",
    "founder_command_ref",
    "lifecycle_state",
    "created_at",
    "updated_at",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def state_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def _contains_sensitive_identity(value: Any) -> bool:
    """Detect prohibited credential/plaintext fields without retaining their values."""

    if isinstance(value, Mapping):
        return any(
            str(key).strip().casefold() in SENSITIVE_IDENTITY_KEYS
            or _contains_sensitive_identity(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_sensitive_identity(item) for item in value)
    return False


def build_sealed_founder_root(
    device_principal_fingerprint: str,
    google_oidc_issuer: str,
    google_oidc_subject_sha256: str,
) -> dict[str, Any]:
    """Build a content-sealed root record from already verified external factors.

    This helper does not prove, provision, or persist either identity factor. The
    returned record must be installed through an OS-protected local process
    outside this side-effect-free gate before it can be supplied as trusted root.
    """

    root: dict[str, Any] = {
        "schema_version": FOUNDER_ROOT_SCHEMA_VERSION,
        "device_principal_fingerprint": device_principal_fingerprint,
        "google_oidc_issuer": google_oidc_issuer,
        "google_oidc_subject_sha256": google_oidc_subject_sha256,
        "enabled": True,
        "future_identity_adapters": dict(FUTURE_IDENTITY_ADAPTERS),
    }
    root["root_sha256"] = state_sha256(root)
    return root


def _valid_founder_root(root: Mapping[str, Any] | None) -> bool:
    if not isinstance(root, Mapping):
        return False
    expected_keys = {
        "schema_version",
        "device_principal_fingerprint",
        "google_oidc_issuer",
        "google_oidc_subject_sha256",
        "enabled",
        "future_identity_adapters",
        "root_sha256",
    }
    if set(root) != expected_keys:
        return False
    fingerprint = root.get("device_principal_fingerprint")
    issuer = root.get("google_oidc_issuer")
    subject_hash = root.get("google_oidc_subject_sha256")
    supplied_hash = root.get("root_sha256")
    if (
        root.get("schema_version") != FOUNDER_ROOT_SCHEMA_VERSION
        or root.get("enabled") is not True
        or root.get("future_identity_adapters") != FUTURE_IDENTITY_ADAPTERS
        or not isinstance(fingerprint, str)
        or DEVICE_FINGERPRINT.fullmatch(fingerprint) is None
        or not isinstance(issuer, str)
        or not issuer.startswith("https://")
        or not isinstance(subject_hash, str)
        or SHA256_HEX.fullmatch(subject_hash) is None
        or not isinstance(supplied_hash, str)
        or SHA256_HEX.fullmatch(supplied_hash) is None
    ):
        return False
    unsigned = dict(root)
    unsigned.pop("root_sha256")
    return hmac.compare_digest(supplied_hash, state_sha256(unsigned))


def evaluate_founder_identity_gate(
    request: Mapping[str, Any],
    sealed_root: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Require a trusted device-bound root and Google OIDC subject binding."""

    sensitive_blocked = _contains_sensitive_identity(request)
    legacy_authority_attempt = bool(set(request).intersection(LEGACY_AUTHORITY_KEYS))
    root_valid = _valid_founder_root(sealed_root)
    root = sealed_root if root_valid else {}
    checks = {
        "request_shape": set(request) == EXPECTED_IDENTITY_REQUEST_KEYS,
        "sealed_root_valid": root_valid,
        "no_sensitive_identity_material": not sensitive_blocked,
        "no_legacy_name_or_string_authority": not legacy_authority_attempt,
        "device_principal_fingerprint": (
            root_valid
            and isinstance(request.get("device_principal_fingerprint"), str)
            and hmac.compare_digest(
                request["device_principal_fingerprint"],
                root["device_principal_fingerprint"],
            )
        ),
        "google_oidc_issuer": (
            root_valid
            and isinstance(request.get("google_oidc_issuer"), str)
            and hmac.compare_digest(
                request["google_oidc_issuer"], root["google_oidc_issuer"]
            )
        ),
        "google_oidc_subject_sha256": (
            root_valid
            and isinstance(request.get("google_oidc_subject_sha256"), str)
            and hmac.compare_digest(
                request["google_oidc_subject_sha256"],
                root["google_oidc_subject_sha256"],
            )
        ),
        "explicit_founder_command": request.get("explicit_founder_command") is True,
        "founder_command_ref": bool(str(request.get("founder_command_ref") or "").strip()),
        "d8_decision": request.get("d8_decision") == ALLOW,
        "future_identity_adapters": (
            request.get("future_identity_adapters") == FUTURE_IDENTITY_ADAPTERS
        ),
    }
    if not root_valid:
        decision = HOLD
        reason_code = "HOLD_FOUNDER_ROOT_NOT_PROVISIONED_OR_INVALID"
    elif all(checks.values()):
        decision = ALLOW
        reason_code = "VERIFIED_DUAL_ROOT_FOUNDER_AUTHORITY"
    else:
        decision = BLOCK
        reason_code = (
            "SENSITIVE_IDENTITY_MATERIAL_BLOCKED"
            if sensitive_blocked
            else "FOUNDER_DUAL_ROOT_VERIFICATION_FAILED"
        )
    return {
        "state": "FOUNDER_IDENTITY_GATE_EVALUATED",
        "decision": decision,
        "reason_code": reason_code,
        "checks": checks,
        "principal_ref": (
            f"founder-root-sha256:{root['root_sha256']}" if decision == ALLOW else None
        ),
        "future_identity_adapters": dict(FUTURE_IDENTITY_ADAPTERS),
        "admin_equivalence": BLOCK,
        "side_effects": {
            "secret_read": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
        },
    }


def authorize_governance_change(
    actor_role: str,
    identity_request: Mapping[str, Any],
    sealed_root: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    identity_gate = evaluate_founder_identity_gate(identity_request, sealed_root)
    authorized = actor_role == FOUNDER_ROLE and identity_gate["decision"] == ALLOW
    return {
        "decision": ALLOW if authorized else BLOCK,
        "actor_role": actor_role,
        "identity_gate": identity_gate,
        "governance_authority": "VERIFIED_FOUNDER_DUAL_ROOT_ONLY",
    }


def authorize_total_field_change(
    actor_role: str,
    identity_request: Mapping[str, Any],
    sealed_root: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = authorize_governance_change(actor_role, identity_request, sealed_root)
    result["target"] = "TOTAL_FIELD_CANONICAL"
    return result


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_package_manifest(
    manifest: Mapping[str, Any],
    package_payload: bytes,
    available_dependencies: Sequence[str] = (),
) -> dict[str, Any]:
    """Validate package integrity, scope, dependencies, and W7TP boundaries."""

    errors: list[str] = []
    missing = sorted(REQUIRED_MANIFEST_FIELDS.difference(manifest))
    errors.extend(f"MISSING_FIELD:{field}" for field in missing)

    supplied_sha256 = manifest.get("sha256")
    actual_sha256 = sha256_bytes(package_payload)
    if supplied_sha256 != actual_sha256:
        errors.append("PACKAGE_SHA256_MISMATCH")

    lifecycle_state = manifest.get("lifecycle_state")
    if lifecycle_state not in LIFECYCLE_STATES:
        errors.append("INVALID_LIFECYCLE_STATE")

    requested_permissions = set(manifest.get("requested_permissions") or [])
    unsupported_permissions = sorted(requested_permissions.difference(SAFE_PERMISSIONS))
    errors.extend(f"FORBIDDEN_PERMISSION:{permission}" for permission in unsupported_permissions)

    capability_scope = set(manifest.get("capability_scope") or [])
    forbidden_scope = sorted(capability_scope.intersection(FORBIDDEN_CAPABILITIES))
    errors.extend(f"FORBIDDEN_CAPABILITY:{capability}" for capability in forbidden_scope)

    compatibility = manifest.get("compatibility") or {}
    if compatibility.get("cpu_baseline_required") is not True:
        errors.append("CPU_BASELINE_NOT_PRESERVED")
    required_dependencies = set(compatibility.get("required_dependencies") or [])
    missing_dependencies = sorted(required_dependencies.difference(available_dependencies))
    errors.extend(f"MISSING_DEPENDENCY:{dependency}" for dependency in missing_dependencies)

    protocol = manifest.get("packet_carried_protocol") or {}
    expected_protocol = {
        "kind": "W7TP_8D_STATE_FIELD_PACKET",
        "protocol_native": True,
        "references": True,
        "lookup": True,
        "reconstruction_contract": True,
    }
    if any(protocol.get(key) != value for key, value in expected_protocol.items()):
        errors.append("INVALID_PACKET_CARRIED_PROTOCOL")

    validation = manifest.get("packet_carried_validation") or {}
    expected_validation = {
        "total_field_verification": True,
        "before_state_sha256": True,
        "after_state_sha256": True,
    }
    if any(validation.get(key) != value for key, value in expected_validation.items()):
        errors.append("INVALID_PACKET_CARRIED_VALIDATION")

    if not manifest.get("allowed_nodes"):
        errors.append("NO_ALLOWED_NODE")
    if not manifest.get("evidence_refs"):
        errors.append("NO_EVIDENCE_REF")
    if manifest.get("risk_status") != "CLEAR":
        errors.append("RISK_NOT_CLEAR")
    if not _valid_timestamp(manifest.get("created_at")) or not _valid_timestamp(manifest.get("updated_at")):
        errors.append("INVALID_TIMESTAMP")

    return {
        "decision": "VERIFIED" if not errors else QUARANTINED,
        "errors": errors,
        "expected_sha256": supplied_sha256,
        "actual_sha256": actual_sha256,
    }


def govern_package_action(
    action: str,
    actor_role: str,
    identity_request: Mapping[str, Any],
    manifest: Mapping[str, Any],
    package_payload: bytes,
    available_dependencies: Sequence[str] = (),
    sealed_root: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply the governance decision without installing or mutating a package."""

    checked_manifest = deepcopy(dict(manifest))
    validation = validate_package_manifest(checked_manifest, package_payload, available_dependencies)
    if validation["decision"] == QUARANTINED:
        checked_manifest["lifecycle_state"] = QUARANTINED
        checked_manifest["risk_status"] = QUARANTINED
        return {
            "decision": "QUARANTINE",
            "lifecycle_state": QUARANTINED,
            "manifest": checked_manifest,
            "validation": validation,
        }

    if action == "submit_candidate":
        if actor_role not in CANDIDATE_ACTORS:
            return {"decision": BLOCK, "lifecycle_state": checked_manifest["lifecycle_state"]}
        checked_manifest["lifecycle_state"] = "CANDIDATE"
        return {
            "decision": "CANDIDATE",
            "lifecycle_state": "CANDIDATE",
            "manifest": checked_manifest,
            "validation": validation,
        }

    if action not in FOUNDER_ONLY_ACTIONS:
        return {"decision": BLOCK, "reason": "UNKNOWN_OR_UNGOVERNED_ACTION"}

    authorization = authorize_governance_change(
        actor_role, identity_request, sealed_root
    )
    if authorization["decision"] != ALLOW:
        return {
            "decision": BLOCK,
            "lifecycle_state": checked_manifest["lifecycle_state"],
            "authorization": authorization,
            "validation": validation,
        }

    current_state = checked_manifest["lifecycle_state"]
    target_by_action = {
        "install": "VERIFIED",
        "enable": "ENABLED",
        "update": "VERIFIED",
        "disable": "DISABLED",
        "remove": QUARANTINED,
    }
    allowed_sources = {
        "install": {"CANDIDATE"},
        "enable": {"VERIFIED", "DISABLED"},
        "update": {"VERIFIED", "ENABLED", "DISABLED"},
        "disable": {"ENABLED"},
        "remove": {"DISABLED"},
    }
    if current_state not in allowed_sources[action]:
        return {
            "decision": BLOCK,
            "reason": f"INVALID_LIFECYCLE_TRANSITION:{current_state}:{action}",
            "lifecycle_state": current_state,
        }

    target_state = target_by_action[action]
    checked_manifest["lifecycle_state"] = target_state
    checked_manifest["installed_by"] = authorization["identity_gate"]["principal_ref"]
    checked_manifest["founder_command_ref"] = identity_request["founder_command_ref"]
    if action == "remove":
        checked_manifest["risk_status"] = QUARANTINED
    return {
        "decision": ALLOW,
        "action": action,
        "lifecycle_state": target_state,
        "manifest": checked_manifest,
        "authorization": authorization,
        "validation": validation,
    }


def compose_capability_candidate(
    source_packages: Sequence[tuple[Mapping[str, Any], bytes]],
    composite_manifest: Mapping[str, Any],
    composite_payload: bytes,
    available_dependencies: Sequence[str] = (),
) -> dict[str, Any]:
    """Stack enabled package capabilities into a new candidate without elevation."""

    if len(source_packages) < 2:
        return {"decision": BLOCK, "reason": "COMPOSITION_REQUIRES_TWO_ENABLED_PACKAGES"}

    source_refs: list[dict[str, Any]] = []
    source_permissions: set[str] = set()
    for source_manifest, source_payload in source_packages:
        validation = validate_package_manifest(
            source_manifest,
            source_payload,
            available_dependencies,
        )
        if validation["decision"] == QUARANTINED:
            return {
                "decision": "QUARANTINE",
                "reason": "SOURCE_PACKAGE_VALIDATION_FAILED",
                "validation": validation,
            }
        if source_manifest.get("lifecycle_state") != "ENABLED":
            return {
                "decision": BLOCK,
                "reason": "SOURCE_PACKAGE_NOT_ENABLED",
                "package_id": source_manifest.get("package_id"),
            }
        source_permissions.update(source_manifest.get("requested_permissions") or [])
        source_refs.append(
            {
                "package_id": source_manifest.get("package_id"),
                "version": source_manifest.get("version"),
                "sha256": source_manifest.get("sha256"),
            }
        )

    checked_manifest = deepcopy(dict(composite_manifest))
    checked_manifest["composition"] = {
        "mode": "STACK_AND_FUSE",
        "source_packages": source_refs,
        "permission_boundary": "NO_PERMISSION_EXPANSION",
        "output_state": "CANDIDATE",
        "total_field_verification_required": True,
    }
    checked_manifest["lifecycle_state"] = "CANDIDATE"
    checked_manifest["installed_by"] = None
    checked_manifest["founder_command_ref"] = None

    validation = validate_package_manifest(
        checked_manifest,
        composite_payload,
        available_dependencies,
    )
    if validation["decision"] == QUARANTINED:
        checked_manifest["lifecycle_state"] = QUARANTINED
        checked_manifest["risk_status"] = QUARANTINED
        return {
            "decision": "QUARANTINE",
            "reason": "COMPOSITE_PACKAGE_VALIDATION_FAILED",
            "manifest": checked_manifest,
            "validation": validation,
        }

    composite_permissions = set(checked_manifest.get("requested_permissions") or [])
    expanded_permissions = sorted(composite_permissions.difference(source_permissions))
    if expanded_permissions:
        checked_manifest["lifecycle_state"] = QUARANTINED
        checked_manifest["risk_status"] = QUARANTINED
        return {
            "decision": "QUARANTINE",
            "reason": "COMPOSITION_PERMISSION_EXPANSION",
            "expanded_permissions": expanded_permissions,
            "manifest": checked_manifest,
        }

    return {
        "decision": "CANDIDATE",
        "lifecycle_state": "CANDIDATE",
        "manifest": checked_manifest,
        "source_permission_boundary": sorted(source_permissions),
        "validation": validation,
    }


def build_execution_evidence(
    manifest: Mapping[str, Any],
    before_state: Any,
    after_state: Any,
) -> dict[str, Any]:
    if manifest.get("lifecycle_state") != "ENABLED":
        return {"decision": BLOCK, "reason": "PACKAGE_NOT_ENABLED"}
    return {
        "decision": ALLOW,
        "package_id": manifest.get("package_id"),
        "package_sha256": manifest.get("sha256"),
        "evidence_refs": list(manifest.get("evidence_refs") or []),
        "before_state_sha256": state_sha256(before_state),
        "after_state_sha256": state_sha256(after_state),
    }


def select_execution_path(
    msi_rtx_4070_online: bool,
    cloud_model_requested: bool = False,
    founder_identity_request: Mapping[str, Any] | None = None,
    sealed_root: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    identity_gate = evaluate_founder_identity_gate(
        founder_identity_request or {}, sealed_root
    )
    cloud_decision = "NOT_REQUESTED"
    if cloud_model_requested:
        cloud_decision = ALLOW if identity_gate["decision"] == ALLOW else BLOCK
    return {
        "cpu_baseline": "CPU_BASELINE_CONTINUES",
        "gpu_support": "GPU_SUPPORT" if msi_rtx_4070_online else "GPU_OFFLINE",
        "execution_mode": "GPU_SUPPORT" if msi_rtx_4070_online else "CPU_BASELINE_CONTINUES",
        "execution_nodes": (
            ["CPU_BASELINE", "FOUNDER_GPU_EXECUTION_NODE"]
            if msi_rtx_4070_online
            else ["CPU_BASELINE"]
        ),
        "cloud_model_decision": cloud_decision,
        "cloud_model_auto_enabled": False,
    }
