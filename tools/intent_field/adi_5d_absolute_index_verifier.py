#!/usr/bin/env python3
"""Local verifier for ADI 5D absolute-index packets.

This is a dry-run verifier. It does not call cloud services, write databases,
deploy, restart services, or reveal internal ADI/H64/TD rules.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/home/taiji_admin/Taiji_Hub")
P10A_PATH = Path(
    "runtime/total_field/p10_technical_difference_matrix/"
    "P10_ADI_5D_ADDENDUM_P10A_20260706T194557Z/P10_ADI_5D_ADDENDUM_P10A.md"
)
P10A_SHA256 = "b3599e9f3fb2bd51e31e12186a36d1a23ca8cdb65cbe57157c653cd935927be1"
PACKET_TYPE = "adi_5d_absolute_index_packet"
NEXT_PACKET = "ADI_5D_ABSOLUTE_INDEX_SCHEMA_VERIFIER_MIN_LANDING"
ARCHITECTURE_ORDER = [
    "VPN_PRIVATE_CHANNEL",
    "8D_AUTHORITY_ENVELOPE",
    "ADI_5D_ABSOLUTE_INDEX",
    "LOOKUP_REFERENCE_RECONSTRUCTION_CONDITIONS",
    "7D_FUNCTIONAL_STATE_GENERATION",
    "TOTAL_FIELD_VERIFICATION_HOLD_SEAL",
]
REQUIRED_DIMENSIONS = [
    "time_coordinate",
    "space_coordinate",
    "state_coordinate",
    "evidence_coordinate",
    "authority_coordinate",
]
FORBIDDEN_SECRET_KEYS = {
    "access_token",
    "api_key",
    "client_secret",
    "oauth_token",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "token",
}
FORBIDDEN_MEMBER_KEYS = {
    "identifiable_person_plaintext",
    "member_plaintext",
    "plaintext_identity",
    "raw_address",
    "raw_browser_page",
    "raw_care_detail",
    "raw_health_detail",
    "raw_payment_data",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_ref(value: str) -> str:
    return "hash:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def payload_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def iter_keys(payload: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            keys.append(str(key))
            keys.extend(iter_keys(value))
    elif isinstance(payload, list):
        for item in payload:
            keys.extend(iter_keys(item))
    return keys


def find_key(payload: Any, target: str) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) == target:
                return True
            if find_key(value, target):
                return True
    elif isinstance(payload, list):
        return any(find_key(item, target) for item in payload)
    return False


def is_hash_ref(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"hash:[a-f0-9]{64}", value) is not None


def check_p10a(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ref = packet.get("p10a_addendum_ref", {})
    if ref.get("path_ref") != str(P10A_PATH):
        errors.append("P10A_REF_PATH_MISMATCH")
    if ref.get("sha256") != P10A_SHA256:
        errors.append("P10A_REF_SHA_MISMATCH")
    actual_path = ROOT / P10A_PATH
    if not actual_path.exists():
        errors.append("P10A_REF_FILE_MISSING")
    elif sha256_file(actual_path) != P10A_SHA256:
        errors.append("P10A_REF_FILE_SHA_MISMATCH")
    return errors


def check_architecture(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if packet.get("packet_type") != PACKET_TYPE:
        errors.append("PACKET_TYPE_INVALID")
    if packet.get("sandbox_only") is not True:
        errors.append("SANDBOX_ONLY_NOT_TRUE")
    if packet.get("next_packet_name") != NEXT_PACKET:
        errors.append("NEXT_PACKET_NAME_INVALID")
    if packet.get("generic_5d_schema_used") is not False:
        errors.append("GENERIC_5D_SCHEMA_USED")
    if packet.get("architecture_order") != ARCHITECTURE_ORDER:
        errors.append("ARCHITECTURE_ORDER_INVALID")

    envelope = packet.get("within_8d_envelope", {})
    if envelope.get("adi_5d_inside_8d") is not True:
        errors.append("ADI_5D_NOT_INSIDE_8D")
    if envelope.get("five_dimensions_do_not_replace_8d") is not True:
        errors.append("FIVE_DIMENSIONS_REPLACE_8D_DRIFT")
    auth = envelope.get("authority_envelope", {})
    if auth.get("seal_required") is not True:
        errors.append("8D_SEAL_REQUIRED_NOT_TRUE")
    if not is_hash_ref(auth.get("content_hash")):
        errors.append("8D_CONTENT_HASH_INVALID")
    if not isinstance(auth.get("ttl_seconds"), int) or auth.get("ttl_seconds") <= 0:
        errors.append("8D_TTL_INVALID")
    return errors


def check_adi(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    adi = packet.get("adi_absolute_index", {})
    if adi.get("actual_index_rules_disclosed") is not False:
        errors.append("ADI_ACTUAL_INDEX_RULES_DISCLOSED")
    if adi.get("h64_td_ref_only") is not True:
        errors.append("H64_TD_REF_ONLY_NOT_TRUE")
    for key in [
        "absolute_index_ref",
        "absolute_position_code",
        "lookup_route_ref",
        "state_position_ref",
        "reconstruction_condition_ref",
        "authority_anchor_ref",
        "conflict_resolution_ref",
        "route_weight_ref",
    ]:
        if not adi.get(key):
            errors.append(f"ADI_REQUIRED_REF_MISSING:{key}")
    if find_key(packet, "adi_index_rules"):
        errors.append("ADI_INDEX_RULES_KEY_PRESENT")
    return errors


def check_dimensions(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    dims = packet.get("five_dimensions", {})
    if sorted(dims.keys()) != sorted(REQUIRED_DIMENSIONS):
        errors.append("ADI_5D_DIMENSION_SET_INVALID")
        return errors
    for name in REQUIRED_DIMENSIONS:
        dimension = dims.get(name, {})
        for field in ["coordinate_role", "coordinate_ref", "coordinate_hash", "index_scope_ref"]:
            if not dimension.get(field):
                errors.append(f"ADI_5D_DIMENSION_FIELD_MISSING:{name}:{field}")
        if not is_hash_ref(dimension.get("coordinate_hash")):
            errors.append(f"ADI_5D_COORDINATE_HASH_INVALID:{name}")
    return errors


def check_lookup_and_verifier(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    conditions = packet.get("lookup_reference_reconstruction_conditions", {})
    for key in ["lookup_refs", "reference_refs", "reconstruction_condition_refs"]:
        value = conditions.get(key)
        if not isinstance(value, list) or not value or any(not item for item in value):
            errors.append(f"LOOKUP_RECONSTRUCTION_FIELD_INVALID:{key}")

    verifier = packet.get("verifier_contract", {})
    required_true = [
        "local_total_field_authority",
        "cloud_candidate_only",
        "requires_total_field_verify",
        "hold_on_definition_drift",
        "hold_on_generic_5d",
        "hold_on_adi_rule_disclosure",
    ]
    for key in required_true:
        if verifier.get(key) is not True:
            errors.append(f"VERIFIER_CONTRACT_NOT_TRUE:{key}")
    if verifier.get("final_decision_by_cloud") is not False:
        errors.append("CLOUD_FINAL_AUTHORITY_DRIFT")
    if set(verifier.get("allowed_decisions", [])) != {"PASS", "HOLD", "BLOCK"}:
        errors.append("ALLOWED_DECISIONS_INVALID")
    return errors


def check_safety(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    boundary = packet.get("safety_boundary", {})
    false_keys = [
        "db_write",
        "odoo_write",
        "deploy",
        "restart",
        "cloud_call_executed",
        "legal_patent_exclusivity_claimed",
    ]
    true_keys = ["no_secret", "no_member_plaintext", "h64_td_ref_only"]
    for key in false_keys:
        if boundary.get(key) is not False:
            errors.append(f"SAFETY_BOUNDARY_NOT_FALSE:{key}")
    for key in true_keys:
        if boundary.get(key) is not True:
            errors.append(f"SAFETY_BOUNDARY_NOT_TRUE:{key}")

    lower_keys = {key.lower() for key in iter_keys(packet)}
    secret_hits = sorted(lower_keys & FORBIDDEN_SECRET_KEYS)
    if secret_hits:
        errors.append("SECRET_FIELD_NAME_DETECTED:" + ",".join(secret_hits))
    member_hits = sorted(lower_keys & FORBIDDEN_MEMBER_KEYS)
    if member_hits:
        errors.append("MEMBER_PLAINTEXT_FIELD_NAME_DETECTED:" + ",".join(member_hits))

    text = payload_text(packet)
    cleaned = text.replace("h64_td_ref_only", "").replace("H64_TD_REF_ONLY", "")
    if re.search(r"(?i)H64[-_ ]?TD.*(mapping|table|rules|codebook)", cleaned):
        errors.append("H64_TD_DETAIL_DISCLOSURE_DETECTED")
    if re.search(r"(?i)(generic 5D schema|generic_5d_schema_used\": true)", text):
        errors.append("GENERIC_5D_TEXT_DRIFT")
    return errors


def check_hash_chain(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    chain = packet.get("hash_chain", {})
    previous_hash = chain.get("previous_record_hash")
    current_hash = chain.get("current_record_hash")
    if not is_hash_ref(previous_hash):
        errors.append("PREVIOUS_RECORD_HASH_INVALID")
    if not is_hash_ref(current_hash):
        errors.append("CURRENT_RECORD_HASH_INVALID")
    if previous_hash == current_hash:
        errors.append("HASH_CHAIN_NO_TRANSITION")
    return errors


def verify_packet(packet: dict[str, Any]) -> dict[str, Any]:
    check_errors = {
        "P10A_REF_CHECK": check_p10a(packet),
        "ARCHITECTURE_CHECK": check_architecture(packet),
        "ADI_ABSOLUTE_INDEX_CHECK": check_adi(packet),
        "ADI_5D_DIMENSION_CHECK": check_dimensions(packet),
        "LOOKUP_AND_VERIFIER_CHECK": check_lookup_and_verifier(packet),
        "SAFETY_BOUNDARY_CHECK": check_safety(packet),
        "HASH_CHAIN_CHECK": check_hash_chain(packet),
    }
    errors = [error for values in check_errors.values() for error in values]
    return {
        "STATE": "ADI_5D_ABSOLUTE_INDEX_SCHEMA_VERIFIER_RESULT",
        "PACKET_TYPE": packet.get("packet_type"),
        "NEXT": NEXT_PACKET,
        "DRY_RUN": "PASS" if not errors else "FAIL",
        "CHECKS": {name: "PASS" if not values else "FAIL" for name, values in check_errors.items()},
        "DB_WRITE": False,
        "ODOO_WRITE": False,
        "DEPLOY": False,
        "RESTART": False,
        "CLOUD_CALL_EXECUTED": False,
        "LEGAL_PATENT_EXCLUSIVITY": "NOT_CLAIMED_HERE",
        "ERRORS": errors,
    }


def base_pass_packet() -> dict[str, Any]:
    return {
        "packet_type": PACKET_TYPE,
        "sandbox_only": True,
        "run_id": "ADI_5D_ABSOLUTE_INDEX_SCHEMA_VERIFIER_MIN_LANDING_TEST",
        "p10a_addendum_ref": {"path_ref": str(P10A_PATH), "sha256": P10A_SHA256},
        "next_packet_name": NEXT_PACKET,
        "generic_5d_schema_used": False,
        "architecture_order": list(ARCHITECTURE_ORDER),
        "within_8d_envelope": {
            "packet_ref": "8d_packet_ref:adi_5d_absolute_index_min_landing",
            "adi_5d_inside_8d": True,
            "five_dimensions_do_not_replace_8d": True,
            "authority_envelope": {
                "ttl_seconds": 300,
                "nonce_ref": "nonce_ref:adi_5d_min_landing",
                "content_hash": hash_ref("adi-5d-content"),
                "authority_scope_ref": "authority_scope_ref:local_total_field",
                "seal_required": True,
            },
        },
        "adi_absolute_index": {
            "index_id": "adi_5d_absolute_index:p10a:min_landing",
            "index_version": "adi_5d.v1",
            "absolute_index_ref": "adi_absolute_index_ref:p10a_min",
            "absolute_position_code": "absolute_position_code:ref_only",
            "lookup_route_ref": "lookup_route_ref:adi_5d",
            "state_position_ref": "state_position_ref:adi_5d",
            "reconstruction_condition_ref": "reconstruction_condition_ref:adi_5d",
            "authority_anchor_ref": "authority_anchor_ref:local_total_field",
            "conflict_resolution_ref": "conflict_resolution_ref:adi_5d",
            "route_weight_ref": "route_weight_ref:adi_5d",
            "actual_index_rules_disclosed": False,
            "h64_td_ref_only": True,
        },
        "five_dimensions": {
            "time_coordinate": {
                "coordinate_role": "timestamp_coordinate",
                "coordinate_ref": "timestamp_coordinate:20260706T194804Z",
                "coordinate_hash": hash_ref("time"),
                "index_scope_ref": "index_scope_ref:time",
            },
            "space_coordinate": {
                "coordinate_role": "space_coordinate",
                "coordinate_ref": "space_coordinate:local_total_field",
                "coordinate_hash": hash_ref("space"),
                "index_scope_ref": "index_scope_ref:space",
            },
            "state_coordinate": {
                "coordinate_role": "state_coordinate",
                "coordinate_ref": "state_coordinate:candidate_pending_verify",
                "coordinate_hash": hash_ref("state"),
                "index_scope_ref": "index_scope_ref:state",
            },
            "evidence_coordinate": {
                "coordinate_role": "evidence_reference_coordinate",
                "coordinate_ref": "evidence_reference_coordinate:p10a",
                "coordinate_hash": hash_ref("evidence"),
                "index_scope_ref": "index_scope_ref:evidence",
            },
            "authority_coordinate": {
                "coordinate_role": "authority_reference_coordinate",
                "coordinate_ref": "authority_reference_coordinate:local_total_field",
                "coordinate_hash": hash_ref("authority"),
                "index_scope_ref": "index_scope_ref:authority",
            },
        },
        "lookup_reference_reconstruction_conditions": {
            "lookup_refs": ["lookup_ref:adi_5d_route"],
            "reference_refs": ["reference_ref:p10a_addendum", "reference_ref:clean_authority_index"],
            "reconstruction_condition_refs": ["reconstruction_condition_ref:equivalent_state_or_effect"],
        },
        "verifier_contract": {
            "local_total_field_authority": True,
            "cloud_candidate_only": True,
            "final_decision_by_cloud": False,
            "requires_total_field_verify": True,
            "allowed_decisions": ["PASS", "HOLD", "BLOCK"],
            "hold_on_definition_drift": True,
            "hold_on_generic_5d": True,
            "hold_on_adi_rule_disclosure": True,
        },
        "safety_boundary": {
            "db_write": False,
            "odoo_write": False,
            "deploy": False,
            "restart": False,
            "cloud_call_executed": False,
            "no_secret": True,
            "no_member_plaintext": True,
            "h64_td_ref_only": True,
            "legal_patent_exclusivity_claimed": False,
        },
        "hash_chain": {
            "previous_record_hash": hash_ref("previous-adi-5d-record"),
            "current_record_hash": hash_ref("current-adi-5d-record"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an ADI 5D absolute-index packet.")
    parser.add_argument("packet_json", nargs="?", help="Path to packet JSON. Omit with --emit-pass-fixture.")
    parser.add_argument("--emit-pass-fixture", action="store_true", help="Print a synthetic PASS fixture.")
    parser.add_argument("--output", help="Write verifier result to this path.")
    args = parser.parse_args()

    if args.emit_pass_fixture:
        print(json.dumps(base_pass_packet(), ensure_ascii=False, indent=2))
        return 0
    if not args.packet_json:
        parser.error("packet_json is required unless --emit-pass-fixture is used")

    packet = json.loads(Path(args.packet_json).read_text(encoding="utf-8"))
    result = verify_packet(packet)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["DRY_RUN"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
