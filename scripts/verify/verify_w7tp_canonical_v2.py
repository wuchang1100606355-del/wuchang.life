#!/usr/bin/env python3
"""Verify the W7TP multipurpose packet canonical V2 without runtime writes."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"
SCHEMAS = [
    ROOT / "schemas/w7tp_8d_multipurpose_packet_canonical_v2.schema.json",
    ROOT / "schemas/w7tp_image_domain_profile_v1.schema.json",
    ROOT / "schemas/w7tp_audiovisual_domain_profile_v1.schema.json",
    ROOT / "schemas/w7tp_one_time_gateway_v1.schema.json",
]

REQUIRED_SECTIONS = [
    "0. 正典地位",
    "1. 核心技術定義",
    "2. 固定技術邊界",
    "3. 技術術語與排除定義",
    "4. 8D 固定維度",
    "5. 多用途封包核心",
    "6. 封包自帶傳輸協定",
    "7. 封包自帶重構契約",
    "8. 封包自帶驗證方法",
    "9. 非浮點確定性查表生成",
    "10. 重構資訊來源",
    "11. Generation Packet",
    "12. Transmission Packet",
    "13. 封包組合與嵌套",
    "14. 一次性重構閘道器",
    "15. 無資料端重構",
    "16. 按需物化",
    "17. 驗證與等價層級",
    "18. 文件資料域",
    "19. 圖像資料域",
    "20. 圖像修改",
    "21. 圖像重構",
    "22. 音訊資料域",
    "23. 影片與影音資料域",
    "24. 程式資料域",
    "25. 資料庫與系統資料域",
    "26. Odoo、POS、IoT 與路由資料域",
    "27. 多腦候選與總場",
    "28. 封包生命週期",
    "29. 風險與執行邊界",
    "30. 經濟門檻與傳輸模式選擇",
    "31. 技術成立條件",
    "32. 技術不成立之絕對主張",
    "33. Canonical Lock",
    "34. Technical Drift Check",
    "35. 專利文件引用基準",
    "36. 實作符合性要求",
    "37. 測試與驗證矩陣",
    "38. 術語字典",
    "39. 附錄",
]


def contains_all(text: str, values: list[str]) -> bool:
    return all(value in text for value in values)


def walk_schema(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_schema(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_schema(child)


def schema_contract_valid(schema: dict[str, Any]) -> bool:
    nodes = list(walk_schema(schema))
    return (
        schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        and schema.get("type") == "object"
        and schema.get("additionalProperties") is False
        and bool(schema.get("required"))
        and any("enum" in node and bool(node["enum"]) for node in nodes)
        and all(
            isinstance(node.get("required"), list) and bool(node["required"])
            for node in nodes
            if "required" in node
        )
    )


def main() -> int:
    canonical_exists = CANONICAL.is_file()
    text = CANONICAL.read_text(encoding="utf-8") if canonical_exists else ""
    schema_payloads: list[dict[str, Any]] = []
    schema_parse = True
    for path in SCHEMAS:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                schema_parse = False
                continue
            schema_payloads.append(payload)
        except (OSError, json.JSONDecodeError):
            schema_parse = False

    forbidden_positive_assertions = [
        r"MODEL_REQUIRED=YES",
        r"LLM_REQUIRED=YES",
        r"FLOATING_POINT_INFERENCE_REQUIRED=YES",
        r"DIFFUSION_REQUIRED=YES",
        r"W7TP_PACKET_CORE=(?!UNIFIED_MULTIPURPOSE_8D_PACKET|ONE_UNIFIED_CORE)",
    ]

    checks = {
        "CANONICAL_FILE_EXISTS": canonical_exists,
        "CANONICAL_REQUIRED_SECTIONS": contains_all(text, [f"## {section}" for section in REQUIRED_SECTIONS]),
        "MODEL_REQUIRED_NO": contains_all(text, ["MODEL_REQUIRED=NO", "LLM_REQUIRED=NO", "NEURAL_NETWORK_REQUIRED=NO"]),
        "FLOAT_REQUIRED_NO": "FLOATING_POINT_INFERENCE_REQUIRED=NO" in text,
        "PACKET_CARRIES_PROTOCOL_YES": "PACKET_CARRIES_TRANSPORT_PROTOCOL=YES" in text,
        "PACKET_CARRIES_RECONSTRUCTION_CONTRACT_YES": "PACKET_CARRIES_RECONSTRUCTION_CONTRACT=YES" in text,
        "PACKET_CARRIES_VERIFICATION_METHOD_YES": "PACKET_CARRIES_VERIFICATION_METHOD=YES" in text,
        "MULTIPURPOSE_PACKET_CORE_UNIFIED": contains_all(text, ["W7TP_PACKET_CORE=UNIFIED_MULTIPURPOSE_8D_PACKET", "W7TP_PACKET_CORE=ONE_UNIFIED_CORE"]),
        "IMAGE_PROFILE_PRESENT": contains_all(text, ["IMAGE_STATE", "INTEGER_TENSOR_STATE", "COLOR_VECTOR", "VERIFICATION_PROFILE"]),
        "IMAGE_EDITING_PRESENT": contains_all(text, ["SOURCE_IMAGE_STATE", "APPLY_STATE_DELTA", "RECONSTRUCT_IMAGE_STATE"]),
        "IMAGE_RECONSTRUCTION_PRESENT": contains_all(text, ["PIXEL_EXACT", "STRUCTURAL_EXACT", "STATE_EQUIVALENT"]),
        "AUDIOVISUAL_PROFILE_PRESENT": contains_all(text, ["AUDIO_VISUAL_SYNC", "TEMPORAL_STATE_TRANSITION", "MOTION_STATE"]),
        "ONE_TIME_GATEWAY_PRESENT": "ONE_TIME_EPHEMERAL_GENERATIVE_RECONSTRUCTION_GATEWAY" in text,
        "ZERO_PRIOR_CONTENT_PRESENT": "ZERO_PRIOR_CONTENT_RECEIVER=SUPPORTED" in text,
        "GENERATION_PACKET_PRESENT": contains_all(text, ["## 11. Generation Packet", "target_equivalence"]),
        "TRANSMISSION_PACKET_PRESENT": contains_all(text, ["## 12. Transmission Packet", "merge_condition", "delivery_state"]),
        "TOTAL_FIELD_ROLE_PRESENT": contains_all(text, ["PACKET_AUTHORITY", "EQUIVALENCE_DECISION_AUTHORITY", "FINAL_SEAL_AUTHORITY"]),
        "TECHNICAL_DRIFT_RULE_PRESENT": contains_all(text, ["TECHNICAL_DRIFT=TRUE", "FIX_BY_REFERENCE"]),
        "NO_COMPRESSION_EQUIVALENCE": "壓縮等同生成式傳輸" in text and "COMPRESSION_ONLY" in text,
        "NO_FILE_COPY_EQUIVALENCE": "file copy 等同生成式傳輸" in text and "FILE_COPY" in text,
        "NO_CLOUD_SYNC_EQUIVALENCE": "cloud sync／backup／download decrypt 等同生成式傳輸" in text,
        "SCHEMA_JSON_PARSE": schema_parse and len(schema_payloads) == len(SCHEMAS),
        "SCHEMA_CONTRACTS": schema_parse and len(schema_payloads) == len(SCHEMAS) and all(schema_contract_valid(schema) for schema in schema_payloads),
        "NO_FORBIDDEN_POSITIVE_ASSERTION": not any(re.search(pattern, text) for pattern in forbidden_positive_assertions),
    }

    state = "PASS_W7TP_CANONICAL_V2" if all(checks.values()) else "HOLD_W7TP_CANONICAL_V2"
    canonical_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest() if canonical_exists else "NOT_FOUND"

    print(f"STATE={state}")
    print(f"CANONICAL_FILE={CANONICAL.relative_to(ROOT)}")
    print(f"CANONICAL_SHA256={canonical_sha256}")
    for key, value in checks.items():
        print(f"{key}={'PASS' if value else 'HOLD'}")

    return 0 if state == "PASS_W7TP_CANONICAL_V2" else 1


if __name__ == "__main__":
    sys.exit(main())
