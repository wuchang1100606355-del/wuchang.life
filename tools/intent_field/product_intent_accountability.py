#!/usr/bin/env python3
"""Dry-run accountable record helpers for product intent field P0."""

from __future__ import annotations

import hashlib
import json
from typing import Any


GENESIS_HASH = "hash:" + ("0" * 64)


def canonical_record(record: dict[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key != "current_record_hash"}
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def record_hash(record: dict[str, Any]) -> str:
    return "hash:" + hashlib.sha256(canonical_record(record).encode("utf-8")).hexdigest()


def build_accountability_record(
    *,
    candidate_action_id: str,
    state_packet_id: str,
    rule_version: str,
    verifier_result: str,
    timestamp_coordinate: str,
    responsible_person_ref: str,
    previous_record_hash: str = GENESIS_HASH,
) -> dict[str, Any]:
    record = {
        "candidate_action_id": candidate_action_id,
        "state_packet_id": state_packet_id,
        "rule_version": rule_version,
        "verifier_result": verifier_result,
        "execution_result": "DRY_RUN_RESTRICTED_PREVIEW" if verifier_result == "PASS" else "DRY_RUN_HOLD_PACKET",
        "timestamp_coordinate": timestamp_coordinate,
        "responsible_person_ref": responsible_person_ref,
        "previous_record_hash": previous_record_hash,
    }
    record["current_record_hash"] = record_hash(record)
    return record
