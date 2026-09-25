#!/usr/bin/env python3
"""Verify the bounded SUNMI/HomePad inventory and container candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, NoReturn


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "WIFI_SUNMI_HOMEPAD_FIELD_INVENTORY_AND_CONTAINER_PROFILE_V0_1"
INVENTORY = Path("manifests/w7tp_field_device_inventory_v0_1/device_inventory.json")
CANDIDATE_DIR = Path("manifests/w7tp_sunmi_voice_container_candidate_v0_1")
CAPABILITY = CANDIDATE_DIR / "capability_manifest.json"
CONTAINER = CANDIDATE_DIR / "container_profile.json"
VOICE = CANDIDATE_DIR / "voice_license_profile.json"
REPORT = Path("docs/total_field/W7TP_WIFI_SUNMI_HOMEPAD_INVENTORY_REPORT.md")
TARGET_ROLES = frozenset({"SUNMI_POS", "HOME_PAD_1", "HOME_PAD_2"})
PROTECTED_FLAGS = (
    "remote_write",
    "deploy",
    "restart",
    "db_write",
    "router_write",
    "canonical_write",
    "pointer_write",
)
FORBIDDEN_SECRET_KEYS = frozenset(
    {
        "adc_json",
        "api_key",
        "client_secret",
        "google_credential",
        "oauth_token",
        "password",
        "private_key",
        "raw_credential",
        "token",
    }
)
FORBIDDEN_SECRET_MARKERS = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "sk-proj-",
    "AIza",
)


class VerificationFailure(ValueError):
    """Stable verifier failure with a non-sensitive reason code."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


def _fail(reason_code: str) -> NoReturn:
    raise VerificationFailure(reason_code)


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            _fail("DUPLICATE_JSON_MEMBER")
        value[key] = item
    return value


def load_json(path: Path) -> dict[str, Any]:
    """Load one repository JSON object without accepting duplicate keys."""

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=lambda _token: _fail("NON_FINITE_JSON_NUMBER"),
        )
    except VerificationFailure:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VerificationFailure("JSON_READ_FAILED") from error
    if not isinstance(value, dict):
        _fail("JSON_OBJECT_REQUIRED")
    return value


def _contains_secret(value: Any) -> bool:
    """Detect credential-shaped fields and high-signal raw secret markers."""

    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).casefold() in FORBIDDEN_SECRET_KEYS:
                return True
            if _contains_secret(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_secret(item) for item in value)
    elif isinstance(value, str):
        return any(marker in value for marker in FORBIDDEN_SECRET_MARKERS)
    return False


def _device_by_role(inventory: Mapping[str, Any], role: str) -> Mapping[str, Any]:
    devices = inventory.get("devices")
    if not isinstance(devices, list):
        _fail("DEVICES_LIST_REQUIRED")
    matches = [item for item in devices if isinstance(item, dict) and item.get("device_role") == role]
    if len(matches) != 1:
        _fail("TARGET_ROLE_CARDINALITY_INVALID")
    return matches[0]


def _validate_address_evidence(device: Mapping[str, Any]) -> None:
    refs = device.get("address_evidence_refs")
    if not isinstance(refs, dict):
        _fail("ADDRESS_EVIDENCE_MAP_REQUIRED")
    for field in ("tailscale_ipv4", "wifi_ipv4"):
        if device.get(field) is not None and not isinstance(refs.get(field), str):
            _fail("ADDRESS_EVIDENCE_REF_MISSING")


def validate_inventory(inventory: Mapping[str, Any], root: Path = ROOT) -> None:
    """Validate target cardinality, evidence, HOLD gates, and protected files."""

    if inventory.get("run_id") != RUN_ID:
        _fail("RUN_ID_INVALID")
    if inventory.get("status") not in {
        "PASS_WIFI_SUNMI_HOMEPAD_INVENTORY",
        "HOLD_DEVICE_IDENTITY_MAPPING_UNRESOLVED",
    }:
        _fail("INVENTORY_STATUS_INVALID")
    targets = inventory.get("target_roles")
    if not isinstance(targets, list) or frozenset(targets) != TARGET_ROLES:
        _fail("TARGET_ROLES_INVALID")
    if "taiji01" in targets:
        _fail("TAIJI01_TARGET_FORBIDDEN")
    excluded = inventory.get("excluded_targets")
    if not isinstance(excluded, list) or not any(
        isinstance(item, dict) and item.get("node_id") == "taiji01"
        for item in excluded
    ):
        _fail("TAIJI01_EXCLUSION_MISSING")
    devices = inventory.get("devices")
    if not isinstance(devices, list) or len(devices) != 3:
        _fail("DEVICE_CARDINALITY_INVALID")
    if {item.get("device_role") for item in devices if isinstance(item, dict)} != TARGET_ROLES:
        _fail("TARGET_DEVICE_ROLES_INVALID")
    sunmi = _device_by_role(inventory, "SUNMI_POS")
    direct_sunmi_evidence = (
        sunmi.get("manufacturer") == "Shanghai Sunmi Technology Co.,Ltd."
        and sunmi.get("identity_method")
        == "OWNER_CONFIRMED_TAILSCALE_MAPPING_PLUS_MAC_OUI_MANUFACTURER"
    )
    explicit_hold = isinstance(sunmi.get("hold_reason"), str) and sunmi.get(
        "deployment_eligibility"
    ) is False
    if not (direct_sunmi_evidence or explicit_hold):
        _fail("SUNMI_DIRECT_EVIDENCE_OR_HOLD_REQUIRED")
    expected_sunmi_mapping = {
        "node_id": "V3_MIX_EDLA_GL",
        "tailscale_machine_name": "V3_MIX_EDLA_GL",
        "tailscale_ipv4": "100.98.69.115",
        "os": "Android",
        "os_version": "13",
        "authority": "OWNER_CONFIRMED_DEVICE_MAPPING",
    }
    if any(sunmi.get(key) != expected for key, expected in expected_sunmi_mapping.items()):
        _fail("SUNMI_OWNER_MAPPING_INVALID")
    if sunmi.get("identity_method") == "HOSTNAME_ONLY":
        _fail("HOSTNAME_IDENTITY_GUESS_FORBIDDEN")
    for role in ("HOME_PAD_1", "HOME_PAD_2"):
        homepad = _device_by_role(inventory, role)
        if homepad.get("identity_confidence") == "UNRESOLVED":
            if homepad.get("hold_reason") != "HOLD_HOMEPAD_IDENTITY_UNRESOLVED":
                _fail("HOMEPAD_UNRESOLVED_HOLD_REQUIRED")
        if homepad.get("identity_method") == "HOSTNAME_ONLY":
            _fail("HOSTNAME_IDENTITY_GUESS_FORBIDDEN")
    for device in devices:
        if not isinstance(device, dict):
            _fail("DEVICE_OBJECT_REQUIRED")
        _validate_address_evidence(device)
        if device.get("online_state") in {"OFFLINE", "UNRESOLVED"} and device.get(
            "deployment_eligibility"
        ) is not False:
            _fail("OFFLINE_DEVICE_READY_FOR_DEPLOYMENT")
    unresolved = inventory.get("unresolved_devices")
    if not isinstance(unresolved, list):
        _fail("UNRESOLVED_DEVICES_LIST_REQUIRED")
    drallion = next(
        (
            item
            for item in unresolved
            if isinstance(item, dict)
            and item.get("tailscale_machine_name") == "drallion"
        ),
        None,
    )
    if (
        not isinstance(drallion, dict)
        or drallion.get("platform") != "ChromeOS"
        or drallion.get("tailscale_reported_os") != "android"
        or "SUNMI_POS" in drallion.get("candidate_roles", [])
        or "SUNMI_POS" not in drallion.get("excluded_roles", [])
    ):
        _fail("DRALLION_CHROMEOS_BOUNDARY_INVALID")
    for item in unresolved:
        if not isinstance(item, dict) or not isinstance(item.get("evidence_ref"), str):
            _fail("UNRESOLVED_DEVICE_EVIDENCE_REQUIRED")
        if item.get("online_state") == "OFFLINE" and item.get("deployment_eligibility") is True:
            _fail("OFFLINE_DEVICE_READY_FOR_DEPLOYMENT")
    boundaries = inventory.get("protected_boundaries")
    if not isinstance(boundaries, dict) or any(boundaries.get(flag) is not False for flag in PROTECTED_FLAGS):
        _fail("PROTECTED_BOUNDARY_INVALID")
    baselines = inventory.get("protected_file_baselines")
    if not isinstance(baselines, dict) or len(baselines) != 4:
        _fail("PROTECTED_BASELINE_INVALID")
    for relative, expected in baselines.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            _fail("PROTECTED_BASELINE_INVALID")
        try:
            actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        except OSError as error:
            raise VerificationFailure("PROTECTED_FILE_READ_FAILED") from error
        if actual != expected:
            _fail("PROTECTED_FILE_HASH_MISMATCH")


def validate_profiles(
    capability: Mapping[str, Any],
    container: Mapping[str, Any],
    voice: Mapping[str, Any],
) -> None:
    """Validate candidate-only voice and non-root container boundaries."""

    if any(_contains_secret(item) for item in (capability, container, voice)):
        _fail("RAW_SECRET_DETECTED")
    if capability.get("status") != "CANDIDATE" or capability.get("direct_commit") is not False:
        _fail("CAPABILITY_CANDIDATE_GATE_INVALID")
    if capability.get("node_id_ref") != "V3_MIX_EDLA_GL" or capability.get(
        "platform"
    ) != "Android 13":
        _fail("CAPABILITY_SUNMI_MAPPING_INVALID")
    if capability.get("allow_only_commit") is not True or capability.get(
        "total_field_gateway_required"
    ) is not True:
        _fail("CAPABILITY_TOTAL_FIELD_GATE_INVALID")
    required_container = {
        "status": "CANDIDATE",
        "node_id_ref": "V3_MIX_EDLA_GL",
        "platform": "Android 13",
        "non_root_required": True,
        "credential_embedded": False,
        "secret_mount_required": True,
        "network_listener_default": False,
        "db_write": False,
        "router_write": False,
        "canonical_write": False,
        "pointer_write": False,
        "allow_only_commit": True,
        "total_field_gateway_required": True,
    }
    if any(container.get(key) != expected for key, expected in required_container.items()):
        _fail("CONTAINER_SECURITY_PROFILE_INVALID")
    if not isinstance(container.get("supported_architecture"), list):
        _fail("CONTAINER_ARCHITECTURE_LIST_REQUIRED")
    if not isinstance(container.get("required_runtime"), dict) or not isinstance(
        container.get("required_storage"), dict
    ):
        _fail("CONTAINER_REQUIREMENTS_INVALID")
    for field in ("healthcheck_command", "self_test_command"):
        command = container.get(field)
        if not isinstance(command, list) or not command or not all(
            isinstance(item, str) and item for item in command
        ):
            _fail("CONTAINER_COMMAND_INVALID")
    required_voice = {
        "voice_provider": "GOOGLE_COMMERCIAL_VOICE",
        "node_id_ref": "V3_MIX_EDLA_GL",
        "platform": "Android 13",
        "google_commercial_voice_authorization": "YES",
        "voice_license_state": "OWNER_CONFIRMED",
        "voice_license_ref": "OPAQUE_REFERENCE_ONLY",
        "credential_embedded": False,
        "credential_read": False,
        "credential_output": False,
        "voice_candidate_state": "CANDIDATE_ONLY",
        "total_field_gateway_required": True,
        "d8_allow_required_for_playback": True,
        "direct_commit": False,
    }
    if any(voice.get(key) != expected for key, expected in required_voice.items()):
        _fail("VOICE_LICENSE_PROFILE_INVALID")


def validate_report(report: str) -> None:
    """Require the report to preserve the unresolved and no-write result."""

    required = (
        "HOLD_DEVICE_IDENTITY_MAPPING_UNRESOLVED",
        "74:F7:F6",
        "HOLD_HOMEPAD_IDENTITY_UNRESOLVED",
        "REMOTE_WRITE=NO",
        "DEPLOY=NO",
        "ACTIVE_CANONICAL_WRITE=NO",
        "POINTER_WRITE=NO",
    )
    if any(marker not in report for marker in required):
        _fail("REPORT_MARKER_MISSING")


def verify(root: Path = ROOT) -> None:
    """Verify only the seven explicitly requested candidate artifacts."""

    inventory = load_json(root / INVENTORY)
    capability = load_json(root / CAPABILITY)
    container = load_json(root / CONTAINER)
    voice = load_json(root / VOICE)
    validate_inventory(inventory, root)
    validate_profiles(capability, container, voice)
    try:
        report = (root / REPORT).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise VerificationFailure("REPORT_READ_FAILED") from error
    validate_report(report)
    if _contains_secret(inventory):
        _fail("RAW_SECRET_DETECTED")


def main() -> int:
    try:
        verify()
    except VerificationFailure as error:
        print("STATE=HOLD_DEVICE_IDENTITY_MAPPING_UNRESOLVED")
        print(f"RUN_ID={RUN_ID}")
        print(f"REASON_CODE={error.reason_code}")
        return 1
    print("STATE=PASS_VERIFY_W7TP_FIELD_DEVICE_INVENTORY")
    print(f"RUN_ID={RUN_ID}")
    print("TARGET_EXCLUDED=taiji01")
    print("REMOTE_WRITE=NO")
    print("DEPLOY=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
