#!/usr/bin/env python3
"""Read-only verifier for W7TP Canonical V2.1 and its protected parent."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
PARENT_CANONICAL = (
    ROOT
    / "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"
)
CANONICAL = (
    ROOT
    / "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1.md"
)
PACKET_SCHEMA = (
    ROOT / "schemas/w7tp_8d_multipurpose_packet_canonical_v2_1.schema.json"
)
ADAPTER_SCHEMA = (
    ROOT / "schemas/field/w7tp_canonical_v2_to_v2_1_legacy_adapter_v1.schema.json"
)
ADAPTER = ROOT / "tools/total_field/w7tp_canonical_v2_1_legacy_adapter.py"

PARENT_SHA256 = "a5281f229ced0943072cce373125be16f0d361b9352a71094ad5450a6022d5d0"
CANONICAL_SHA256 = "e960d14254df083ffed711e2c44b76fc2075541716881bc3d1034cb26cffbaba"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contains_all(text: str, values: list[str]) -> bool:
    return all(value in text for value in values)


def canonical_locks(text: str) -> dict[str, bool]:
    return {
        "LOCK_01_D1_D8": contains_all(
            text,
            [
                "D1 Intent",
                "D2 State",
                "D3 Coordinate",
                "D4 Evidence",
                "D5 Execution",
                "D6 Generative Transmission",
                "D7 Risk Quarantine",
                "D8 Envelope Verification",
            ],
        ),
        "LOCK_02_COUPLED_STATE_FIELD": contains_all(
            text,
            ["彼此制約並共同閉合", "不是八個互不相干的平面欄位"],
        ),
        "LOCK_03_INTENT_NOT_SEMANTIC": contains_all(
            text,
            [
                "Intent Communication",
                "State-Field Packet Communication",
                "Semantic Communication",
                "不是語意通信",
            ],
        ),
        "LOCK_04_GENERATIVE_TRANSMISSION": contains_all(
            text,
            [
                "8D 狀態場封包",
                "引用",
                "查表鍵",
                "重構條件",
                "等價狀態生成",
                "TOTAL_FIELD_VERIFICATION",
            ],
        ),
        "LOCK_05_NOT_FILE_MOVEMENT": contains_all(
            text,
            [
                "檔案搬運",
                "COMPRESSION_ONLY",
                "BACKUP",
                "SYNC",
                "DOWNLOAD_DECRYPT",
            ],
        ),
        "LOCK_06_ADI_TWO_LAYER": contains_all(
            text,
            ["封包層", "系統層", "不可逆", "packet lineage", "邏輯時間"],
        ),
        "LOCK_07_CANDIDATE_EVIDENCE_ONLY": contains_all(
            text,
            [
                "LLM",
                "雲端",
                "候選解析",
                "候選證據",
                "不能取得執行權或最終驗證權",
            ],
        ),
        "LOCK_08_NON_FLOAT_DECISION": contains_all(
            text,
            [
                "FLOATING_POINT_INFERENCE_REQUIRED=NO",
                "NON_FLOAT_DETERMINISTIC_LOOKUP",
                "INTEGER_STATE_TRANSITION",
                "離散張量",
                "查表鍵",
                "確定性比較",
            ],
        ),
        "LOCK_09_H64_REFERENCE_ONLY": contains_all(
            text,
            ["H64-TD", "reference-only", "完整碼本", "恢復材料"],
        ),
        "LOCK_10_PATENT_CLAIMS": (
            re.search(r"10\s*項", text) is not None
            and re.search(r"21\s*項", text) is not None
            and "115127138" in text
        ),
        "LOCK_11_VERIFICATION_SPLIT": contains_all(
            text,
            ["Exact-byte", "effect-equivalent", "L1", "L2", "L3"],
        ),
        "LOCK_12_APPEND_ONLY": contains_all(
            text,
            ["append-only", "parent_ref", "禁止靜默覆寫"],
        ),
    }


def load_and_check_schema(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"schema is not an object: {path}")
    Draft202012Validator.check_schema(payload)
    return payload


def machine_contract_checks(
    packet_schema: dict[str, Any],
    adapter_schema: dict[str, Any],
) -> dict[str, bool]:
    packet_text = json.dumps(packet_schema, sort_keys=True)
    adapter_text = json.dumps(adapter_schema, sort_keys=True)
    verification = packet_schema["properties"]["verification"]
    return {
        "SCHEMA_DRAFT_2020_12": (
            packet_schema.get("$schema")
            == "https://json-schema.org/draft/2020-12/schema"
            and adapter_schema.get("$schema")
            == "https://json-schema.org/draft/2020-12/schema"
        ),
        "V2_1_BINDING": contains_all(
            packet_text,
            [CANONICAL_SHA256, PARENT_SHA256, "APPEND_ONLY_SUCCESSOR"],
        ),
        "COUPLED_8D": contains_all(
            packet_text,
            [
                "INTERACTIVE_COUPLED_8D_STATE_FIELD",
                "S_NEXT=T(S_CURRENT,I,C,E,A,G,R,V)",
                "D7_RISK_QUARANTINE",
                "D8_ENVELOPE_VERIFICATION",
            ],
        ),
        "L1_L2_L3_ONE_OF": (
            isinstance(verification.get("oneOf"), list)
            and len(verification["oneOf"]) == 3
            and contains_all(
                packet_text,
                [
                    "L1_EXACT_BYTE",
                    "L2_EFFECT_EQUIVALENT",
                    "L3_CANDIDATE",
                ],
            )
        ),
        "ADI_REPLAY_LINEAGE": contains_all(
            packet_text,
            [
                "OPAQUE_IRREVERSIBLE_PACKET_DECISION_INDEX",
                "USER_OWNED_SPATIOTEMPORAL_STATE_INDEX_NETWORK",
                "replay_protection",
                "logical_time",
                "append_only",
            ],
        ),
        "H64_REFERENCE_ONLY": contains_all(
            packet_text,
            ["H64_TD", "REFERENCE_ONLY", "trade_secret_ref"],
        ),
        "CLOUD_LLM_CANDIDATE_EVIDENCE": contains_all(
            packet_text,
            [
                "cloud_authority",
                "llm_authority",
                "CANDIDATE",
                "EVIDENCE",
                "LOCAL_TOTAL_FIELD",
            ],
        ),
        "LEGACY_PROJECTION_ONLY": contains_all(
            adapter_text,
            [
                "LEGACY_V2_READ_TO_V2_1_PROJECTION",
                "raw_sha256",
                "bytes_mutated",
                "projection_only",
                "source_content_embedded",
            ],
        ),
    }


def main() -> int:
    checks: dict[str, bool] = {
        "PARENT_EXISTS": PARENT_CANONICAL.is_file(),
        "CANONICAL_EXISTS": CANONICAL.is_file(),
        "PACKET_SCHEMA_EXISTS": PACKET_SCHEMA.is_file(),
        "ADAPTER_SCHEMA_EXISTS": ADAPTER_SCHEMA.is_file(),
        "LEGACY_ADAPTER_EXISTS": ADAPTER.is_file(),
    }
    parent_sha = raw_sha256(PARENT_CANONICAL) if checks["PARENT_EXISTS"] else "NOT_FOUND"
    canonical_sha = raw_sha256(CANONICAL) if checks["CANONICAL_EXISTS"] else "NOT_FOUND"
    checks["PARENT_RAW_SHA256"] = parent_sha == PARENT_SHA256
    checks["CANONICAL_RAW_SHA256"] = canonical_sha == CANONICAL_SHA256

    text = CANONICAL.read_text(encoding="utf-8") if checks["CANONICAL_EXISTS"] else ""
    locks = canonical_locks(text)
    checks.update(locks)

    try:
        packet_schema = load_and_check_schema(PACKET_SCHEMA)
        adapter_schema = load_and_check_schema(ADAPTER_SCHEMA)
    except (OSError, json.JSONDecodeError, ValueError):
        checks["SCHEMA_VALID"] = False
    else:
        checks["SCHEMA_VALID"] = True
        checks.update(machine_contract_checks(packet_schema, adapter_schema))

    state = (
        "PASS_W7TP_CANONICAL_V2_1_MACHINE_CONTRACT"
        if all(checks.values())
        else "HOLD_W7TP_CANONICAL_V2_1_MACHINE_CONTRACT"
    )
    print(f"STATE={state}")
    print(f"PARENT_CANONICAL_SHA256={parent_sha}")
    print(f"CANONICAL_SHA256={canonical_sha}")
    print(f"LOCKS_MATCHED={sum(locks.values())}/12")
    for key, value in checks.items():
        print(f"{key}={'PASS' if value else 'HOLD'}")
    return 0 if state.startswith("PASS_") else 1


if __name__ == "__main__":
    sys.exit(main())
