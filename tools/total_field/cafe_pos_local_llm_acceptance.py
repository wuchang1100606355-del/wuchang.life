"""User-device LLM acceptance for the Odoo -> ADI -> Total Field POS boundary.

The model may extract words from a synthetic utterance. It cannot select prices,
create an Odoo order, mutate the ADI index, or adjudicate D8. Product and option
truth always comes from the sealed QuickClick snapshot and the rectifier below.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.quickclick_menu_snapshot import build_web_data


DEFAULT_SNAPSHOT = (
    ROOT
    / "runtime/total_field/shared_intent_field/"
    "W7TP_SHARED_8D_CAFE_POS_20260716T175836Z/"
    "cloud-menu-source/quickclick-menu-snapshot.json"
)
DEFAULT_MODEL = "qwen2.5:1.5b"
DEFAULT_MODEL_DIGEST = (
    "65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b"
)
BLOCKED_SERVER_HOSTS = {"taiji01"}
CASES = (
    {
        "id": "LLM_POS_01",
        "utterance": "招牌咖啡 大杯 少冰 半糖",
        "expected_sku": "P_49180031",
        "expected_options": ["L", "少冰", "半糖50%"],
    },
    {
        "id": "LLM_POS_02",
        "utterance": "美式黑咖啡 中杯 熱 無糖",
        "expected_sku": "P_49180073",
        "expected_options": ["M", "熱", "無糖0%"],
    },
    {
        "id": "LLM_POS_03",
        "utterance": "貝果 香蒜",
        "expected_sku": "P_49180052",
        "expected_options": ["香蒜"],
    },
    {
        "id": "LLM_POS_04",
        "utterance": "我要一杯不存在的宇宙咖啡",
        "expected_state": "HOLD_UNKNOWN_ADI_PRODUCT_REF",
    },
)


def _json_request(url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("LOCAL_LLM_ENDPOINT_UNAVAILABLE") from exc
    if not isinstance(value, dict):
        raise RuntimeError("LOCAL_LLM_RESPONSE_INVALID")
    return value


def _model_digest(endpoint: str, model: str) -> str:
    tags = _json_request(endpoint.rstrip("/") + "/api/tags")
    for item in tags.get("models", []):
        if isinstance(item, dict) and item.get("name") == model:
            return str(item.get("digest") or "")
    return ""


def _extract(
    endpoint: str,
    model: str,
    utterance: str,
    product_names: list[str],
) -> dict[str, str]:
    schema = {
        "type": "object",
        "properties": {
            "product_name": {"type": "string"},
            "size": {"type": "string"},
            "temperature": {"type": "string"},
            "sweetness": {"type": "string"},
            "taste": {"type": "string"},
        },
        "required": ["product_name", "size", "temperature", "sweetness", "taste"],
        "additionalProperties": False,
    }
    prompt = (
        "你是咖啡館點單文字抽取器，只抽取使用者明確說出的內容。"
        "商品名稱必須完全選自 ADI 候選清單；沒有完全對應就輸出空字串。"
        "不得猜價格、不得換成相似商品。尺寸輸出 L/M/S，"
        "溫度保留去冰/少冰/微冰/正常冰/常溫/溫/熱等來源詞，"
        "甜度輸出正常100%/少糖75%/半糖50%/微糖30%/無糖0%/多糖120%，"
        "未提及欄位輸出空字串。\n"
        "ADI候選商品=" + json.dumps(product_names, ensure_ascii=False) + "\n"
        "使用者=" + utterance
    )
    result = _json_request(
        endpoint.rstrip("/") + "/api/generate",
        {
            "model": model,
            "prompt": prompt,
            "format": schema,
            "stream": False,
            "options": {
                "temperature": 0,
                "seed": 7,
                "num_predict": 128,
            },
        },
    )
    try:
        extracted = json.loads(str(result["response"]))
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("LOCAL_LLM_STRUCTURED_OUTPUT_INVALID") from exc
    if set(extracted) != set(schema["required"]) or not all(
        isinstance(extracted[field], str) for field in schema["required"]
    ):
        raise RuntimeError("LOCAL_LLM_STRUCTURED_OUTPUT_INVALID")
    return extracted


def _adi_prefilter(menu: dict[str, Any], utterance: str) -> list[dict[str, Any]]:
    candidate_refs = set(menu["adi"]["candidateRefs"])
    matched = [
        product
        for product in menu["products"]
        if product["sourceRef"] in candidate_refs and product["name"] in utterance
    ]
    if not matched:
        return []
    longest = max(len(product["name"]) for product in matched)
    return [product for product in matched if len(product["name"]) == longest]


def _option_value(question: dict[str, Any], extracted: dict[str, str]) -> str:
    name = str(question["name"])
    if name == "尺寸":
        return extracted["size"]
    if name == "溫度":
        return extracted["temperature"]
    if name == "甜度":
        return extracted["sweetness"]
    return extracted["taste"]


def _rectify(menu: dict[str, Any], extracted: dict[str, str]) -> dict[str, Any]:
    candidate_refs = set(menu["adi"]["candidateRefs"])
    products = [
        product
        for product in menu["products"]
        if product["sourceRef"] in candidate_refs
        and product["name"] == extracted["product_name"]
    ]
    if len(products) != 1:
        return {"state": "HOLD_UNKNOWN_ADI_PRODUCT_REF"}
    product = products[0]
    groups = {group["id"]: group for group in menu["optionGroups"]}
    selections: list[dict[str, Any]] = []
    for group_id in product["optionGroupIds"]:
        for question in groups[group_id]["questions"]:
            value = _option_value(question, extracted)
            options = [
                option
                for option in question["options"]
                if value and value in {option["name"], option["displayName"]}
            ]
            if len(options) != 1:
                return {
                    "state": "HOLD_REQUIRED_SOURCE_OPTION",
                    "question": question["displayName"],
                }
            option = options[0]
            selections.append(
                {
                    "question": question["displayName"],
                    "option": option["displayName"],
                    "price_delta": option["priceDelta"],
                    "source_coordinate": product["sourceRef"] + ":" + option["id"],
                }
            )
    unit_price = product["price"] + sum(item["price_delta"] for item in selections)
    return {
        "state": "PASS_L3_CANDIDATE_RECTIFIED",
        "sku": product["id"],
        "source_ref": product["sourceRef"],
        "options": [item["option"] for item in selections],
        "unit_price_candidate": unit_price,
        "rectifier": "TOTAL_FIELD_RECTIFIER",
        "d8": "HOLD_HUMAN_ODOO_REVIEW_REQUIRED",
    }


def run(
    endpoint: str,
    model: str,
    expected_digest: str,
    snapshot_path: Path,
) -> dict[str, Any]:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    menu = build_web_data(snapshot)
    digest = _model_digest(endpoint, model)
    if digest != expected_digest:
        raise RuntimeError("LOCAL_LLM_MODEL_DIGEST_MISMATCH")
    case_results = []
    for case in CASES:
        adi_candidates = _adi_prefilter(menu, case["utterance"])
        if len(adi_candidates) == 1:
            extracted = _extract(
                endpoint,
                model,
                case["utterance"],
                [adi_candidates[0]["name"]],
            )
            llm_state = "LOCAL_LLM_CALLED_AFTER_ADI_PREFILTER"
        else:
            extracted = {
                "product_name": "",
                "size": "",
                "temperature": "",
                "sweetness": "",
                "taste": "",
            }
            llm_state = "LOCAL_LLM_SKIPPED_NO_UNIQUE_ADI_REF"
        rectified = _rectify(menu, extracted)
        passed = rectified["state"] == case.get(
            "expected_state", "PASS_L3_CANDIDATE_RECTIFIED"
        )
        if case.get("expected_sku"):
            passed = passed and rectified.get("sku") == case["expected_sku"]
        if case.get("expected_options"):
            passed = passed and rectified.get("options") == case["expected_options"]
        case_results.append(
            {
                "id": case["id"],
                "utterance": case["utterance"],
                "adi_candidate_refs": [
                    product["sourceRef"] for product in adi_candidates
                ],
                "llm_state": llm_state,
                "llm_extraction": extracted,
                "rectified": rectified,
                "pass": passed,
            }
        )
    state = "PASS_LOCAL_LLM_ADI_TOTAL_FIELD" if all(
        item["pass"] for item in case_results
    ) else "HOLD_LOCAL_LLM_ACCEPTANCE_FAILED"
    return {
        "schema_version": "W7TP-CAFE-POS-LOCAL-LLM-ACCEPTANCE/1.0",
        "state": state,
        "model": model,
        "model_digest": digest,
        "endpoint_scope": "USER_DEVICE_LOOPBACK_ONLY",
        "input_surface": "USER_DEVICE_LLM_TEST",
        "lookup_surface": "ADI_DEMO_FIXED_CANDIDATE_ONLY",
        "rectifier": "TOTAL_FIELD_RECTIFIER",
        "formal_odoo_write": False,
        "db_write": False,
        "payment_capture": False,
        "server_route_exposed": False,
        "cases": case_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--expected-model-digest", default=DEFAULT_MODEL_DIGEST)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execution-surface", choices=("USER_DEVICE",), required=True)
    args = parser.parse_args()
    host = socket.gethostname().split(".", 1)[0].lower()
    if host in BLOCKED_SERVER_HOSTS:
        print(
            json.dumps(
                {
                    "state": "HOLD_USER_DEVICE_LLM_REQUIRED",
                    "host_class": "SERVER_BLOCKED",
                    "server_llm": False,
                    "next": "Run this acceptance tool on a verified user device.",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    result = run(
        args.endpoint,
        args.model,
        args.expected_model_digest,
        args.snapshot,
    )
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["state"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
