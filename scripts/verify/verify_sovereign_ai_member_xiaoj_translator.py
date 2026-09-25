#!/usr/bin/env python3
"""Static verifier for the sovereign AI member XiaoJ translator packet.

This verifier is read-only. It does not access secrets, member plaintext,
databases, routers, deployment targets, or live services.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "SOVEREIGN_AI_MEMBER_XIAOJ_TRANSLATOR_20260708T173010Z"

DOC = ROOT / "docs/total_field/W7TP_SOVEREIGN_AI_MEMBER_XIAOJ_TRANSLATOR_SPEC.md"
SCHEMAS = [
    ROOT / "schemas/field/sovereign_ai_member_xiaoj_translator.schema.json",
    ROOT / "schemas/field/xiaoj_cloud_packet_request.schema.json",
    ROOT / "schemas/field/xiaoj_cloud_candidate_return.schema.json",
    ROOT / "schemas/field/xiaoj_humanized_compliance_response.schema.json",
]
SAMPLE_DIR = ROOT / "runtime/total_field/sovereign_ai_member_xiaoj_translator" / RUN_ID / "samples"
SAMPLES = [
    SAMPLE_DIR / "sample_block_neighbor_door.json",
    SAMPLE_DIR / "sample_member_public_card.json",
    SAMPLE_DIR / "sample_byok_cloud_pull.json",
]

BAD_DEFINITION_TERMS = [
    "8欄位",
    "ADI裝8D",
    "雲端同步個資",
    "檔案搬運",
]
BAD_TRANSPORT_TERMS = [
    "file_copy",
    "cloud_sync",
]
FORBIDDEN_SCHEMA_KEYS = {
    "raw_api_key",
    "raw_token",
    "password",
    "plaintext_member_data",
}
RAW_CREDENTIAL_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{16,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*[A-Za-z0-9._-]{16,}"),
]


def fail(message: str) -> int:
    print("STATE=FAIL_SOVEREIGN_AI_MEMBER_XIAOJ_TRANSLATOR")
    print(f"REASON={message}")
    return 1


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            keys.append(str(key))
            keys.extend(walk_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.extend(walk_keys(item))
    return keys


def as_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def property_const(schema: dict[str, Any], key: str) -> Any:
    props = schema.get("properties", {})
    if not isinstance(props, dict):
        return None
    prop = props.get(key, {})
    if not isinstance(prop, dict):
        return None
    return prop.get("const")


def schema_has_transport_contract(schema: dict[str, Any]) -> bool:
    text = as_text(schema)
    required_parts = [
        "state_packet_ref_reconstruction_equivalent_state",
        "state_packet_ref",
        "reconstruction_ref",
        "equivalent_state_ref",
        "total_field_verify",
    ]
    return all(part in text for part in required_parts)


def check_doc() -> str | None:
    if not DOC.exists():
        return f"missing_doc:{DOC}"
    text = DOC.read_text(encoding="utf-8")
    for term in BAD_DEFINITION_TERMS:
        if term in text:
            return f"bad_definition_term:{term}"
    for pattern in RAW_CREDENTIAL_PATTERNS:
        if pattern.search(text):
            return "raw_credential_pattern_in_doc"
    required_text = [
        "ADI is a 5D metric-index layer",
        "state_packet + ref + reconstruction + equivalent_state + total_field_verify",
        "final authority",
        "key_ref",
        "provider_ref",
        "policy_ref",
    ]
    missing = [item for item in required_text if item not in text]
    if missing:
        return "doc_missing:" + ",".join(missing)
    return None


def check_schemas() -> str | None:
    for path in SCHEMAS:
        if not path.exists():
            return f"missing_schema:{path}"
        schema = load_json(path)
        keys = {key.lower() for key in walk_keys(schema)}
        forbidden = sorted(FORBIDDEN_SCHEMA_KEYS & keys)
        if forbidden:
            return f"forbidden_schema_keys:{','.join(forbidden)}"
        text = as_text(schema)
        for term in BAD_TRANSPORT_TERMS:
            if term in text:
                return f"bad_transport_term:{term}"
        if property_const(schema, "final_authority") != "total_field_verifier":
            return f"final_authority_not_total_field_verifier:{path.name}"
        if property_const(schema, "management_committee_authorization_status") != "HOLD_UNTIL_AUTHORIZED":
            return f"management_committee_not_hold_until_authorized:{path.name}"
        if not schema_has_transport_contract(schema):
            return f"generative_transport_contract_missing:{path.name}"

    for path in SCHEMAS[1:3]:
        schema = load_json(path)
        if property_const(schema, "candidate_only") is not True:
            return f"cloud_candidate_only_missing:{path.name}"
    return None


def check_samples() -> str | None:
    for path in SAMPLES:
        if not path.exists():
            return f"missing_sample:{path}"
        data = load_json(path)
        text = as_text(data)
        for pattern in RAW_CREDENTIAL_PATTERNS:
            if pattern.search(text):
                return f"raw_credential_pattern_in_sample:{path.name}"
        if "member_plaintext" in text and '"member_plaintext": false' not in text:
            return f"member_plaintext_not_false:{path.name}"

    block = load_json(SAMPLES[0])
    if block.get("total_field_decision") != "BLOCK":
        return "neighbor_door_not_blocked"
    if "小J問了總場小J前輩" not in block.get("humanized_response", ""):
        return "neighbor_door_humanized_response_missing"
    if len(block.get("safe_alternatives", [])) < 4:
        return "neighbor_door_safe_alternatives_insufficient"

    public_card = load_json(SAMPLES[1])
    if public_card.get("total_field_decision") != "PASS":
        return "public_card_not_pass_candidate"
    card = public_card.get("public_group_card", {})
    if not isinstance(card, dict):
        return "public_group_card_missing"
    for required in ("source_ref", "license_ref", "map_layer_ref", "total_field_risk_status"):
        if not card.get(required):
            return f"public_card_field_missing:{required}"

    byok = load_json(SAMPLES[2])
    if byok.get("key_ref_only") is not True:
        return "byok_key_ref_only_not_true"
    for required in ("key_ref", "provider_ref", "policy_ref"):
        if not byok.get(required):
            return f"byok_ref_missing:{required}"
    return None


def main() -> int:
    checks = [check_doc, check_schemas, check_samples]
    for check in checks:
        result = check()
        if result:
            return fail(result)
    print("STATE=PASS_SOVEREIGN_AI_MEMBER_XIAOJ_TRANSLATOR_VERIFY")
    print(f"RUN_ID={RUN_ID}")
    print("JSON_PARSE=PASS")
    print("REDTEAM_CHECK=PASS")
    print("SAFETY=NO_SECRET_NO_MEMBER_PLAINTEXT_NO_DB_WRITE_NO_DEPLOY_NO_RESTART_NO_ROUTER_WRITE_NO_OVERWRITE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
