#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DECISION = "safe_relative_identity_7d_code_spec"

REQUIRED_DIMENSIONS = {
    "d1_actor_scope",
    "d2_relationship_context",
    "d3_consent_and_session",
    "d4_privacy_boundary",
    "d5_service_intent",
    "d6_execution_authority",
    "d7_evidence_and_metrics"
}

REQUIRED_D8_FIELDS = {
    "node_id_hash",
    "git_head",
    "addon_version",
    "payload_hash",
    "timestamp",
    "ttl_seconds",
    "nonce",
    "packet_counter",
    "signature_type",
    "signature"
}

REQUIRED_FORBIDDEN = {
    "token",
    "password",
    "private_key",
    "credentials",
    "raw_member_pii",
    "user_cloud_key",
    "router_secret",
    "formal_db_write_authority"
}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="configs/odoo/relative_identity_7d_code_spec.v1.json")
    args = parser.parse_args()

    errors: list[str] = []
    obj: dict[str, Any] = {}

    try:
        obj = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid_json:{exc}")

    if obj.get("authority") != "local_xiaoj_router":
        errors.append("authority_must_be_local_xiaoj_router")

    if obj.get("identity_is_relative_not_absolute") is not True:
        errors.append("identity_must_be_relative")

    if obj.get("raw_pii_required_for_daily_operation") is not False:
        errors.append("raw_pii_required_for_daily_operation_must_be_false")

    dims = obj.get("dimensions", {})
    if not isinstance(dims, dict):
        errors.append("dimensions_must_be_object")
        dims = {}

    for dim in sorted(REQUIRED_DIMENSIONS - set(dims.keys())):
        errors.append(f"missing_dimension:{dim}")

    d8 = obj.get("d8_trust_envelope", {})
    fields = set(d8.get("fields", [])) if isinstance(d8, dict) else set()
    for item in sorted(REQUIRED_D8_FIELDS - fields):
        errors.append(f"missing_d8_field:{item}")

    forbidden = set(obj.get("forbidden_payload", []))
    for item in sorted(REQUIRED_FORBIDDEN - forbidden):
        errors.append(f"missing_forbidden_payload:{item}")

    result = {
        "decision": DECISION if not errors else "rejected",
        "errors": errors,
        "warnings": [],
        "raw_pii_required": False,
        "cloud_is_compute_only": True,
        "formal_db_write_authority": False
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
