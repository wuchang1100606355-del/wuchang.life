"""Read-only Odoo projection for the three preserved ordering designs.

The QuickClick snapshot is used only as the immutable 64-source whitelist.
Names, prices, categories and option deltas are projected from the bound Odoo
records.  A partial or duplicate mapping fails closed; it is never repaired by
name matching.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from typing import Any

from odoo import fields
from odoo.tools import file_open


STORE_BINDING = {
    "company_id": 3,
    "company_name": "上品食品行",
    # Founder intent fixes the merchant company, but no current pos.config is
    # proven to be the Chongxin-HQ POS.  POS 2 belongs to the association and
    # POS 3 is only named "餐廳"; neither may be promoted by inference.
    "pos_config_id": None,
    "pos_config_name": "上品聊國咖啡館 重新總店",
    "store_ref": "store:liaoguo-chongxin-hq",
    "quickclick_menu_id": "M387676",
}
POS_CONFIG_PARAMETER = "liaoguo.chongxin.pos_config_id"


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=1)
def source_contract() -> dict[str, Any]:
    path = "wuchang_ordering_ui_suite/static/src/data/quickclick_web_data.json"
    with file_open(path, "r") as handle:
        data = json.load(handle)
    identity_path = "wuchang_ordering_ui_suite/static/src/data/SOURCE_TO_ODOO_IDENTITY_REVIEW.json"
    with file_open(identity_path, "r") as handle:
        identity = json.load(handle)
    web_by_source = {
        str(item.get("sourceProductId")): item for item in (data.get("products") or [])
    }
    products = []
    for item in identity.get("items") or []:
        source_id = str(item.get("source_product_id") or "")
        products.append(
            web_by_source.get(source_id)
            or {
                "sourceProductId": source_id,
                "name": item.get("source_product_name"),
                "price": item.get("source_base_price"),
                "category": item.get("source_category"),
                "optionGroupIds": item.get("source_option_group_ids") or [],
            }
        )
    source_ids = [str(item.get("sourceProductId") or "") for item in products]
    if len(source_ids) != 64 or len(set(source_ids)) != 64 or any(not item for item in source_ids):
        raise ValueError("QUICKCLICK_64_SOURCE_CONTRACT_INVALID")
    data["allProducts"] = products
    return data


def configured_pos_config_id(env) -> int | None:
    """Read the separately authorized target without guessing an existing POS."""

    raw = env["ir.config_parameter"].sudo().get_param(POS_CONFIG_PARAMETER, "")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def binding_receipt(env) -> dict[str, Any]:
    company = env["res.company"].sudo().browse(STORE_BINDING["company_id"]).exists()
    pos_config_id = configured_pos_config_id(env)
    pos_target_declared = isinstance(pos_config_id, int)
    pos = (
        env["pos.config"].sudo().browse(pos_config_id).exists()
        if pos_target_declared
        else env["pos.config"].browse()
    )
    checks = {
        "company_exists": bool(company),
        "company_name_matches": bool(company and company.name == STORE_BINDING["company_name"]),
        "pos_target_declared": pos_target_declared,
        "pos_exists": bool(pos),
        "pos_name_matches": bool(pos and pos.name == STORE_BINDING["pos_config_name"]),
        "pos_company_matches": bool(pos and pos.company_id.id == STORE_BINDING["company_id"]),
    }
    if not checks["company_exists"] or not checks["company_name_matches"]:
        state = "HOLD_EXACT_COMPANY_BINDING_MISMATCH"
    elif not pos_target_declared:
        state = "HOLD_EXACT_POS_CONFIG_TARGET_REQUIRED"
    else:
        state = "PASS_EXACT_CHONGXIN_BINDING" if all(checks.values()) else "HOLD_EXACT_POS_BINDING_MISMATCH"
    resolved_binding = {**STORE_BINDING, "pos_config_id": pos_config_id}
    material = {"binding": resolved_binding, "checks": checks}
    return {
        "state": state,
        "store_ref": STORE_BINDING["store_ref"],
        "binding": resolved_binding,
        "checks": checks,
        "receipt_ref": "sha256:" + _canonical_sha256(material),
        "database_write": False,
    }


def _question_projection(question) -> dict[str, Any]:
    options = []
    for item in question.item_ids.filtered("active").sorted(lambda row: (row.sequence, row.id)):
        option_ref = item.quickclick_item_code or f"odoo-option-item:{item.id}"
        options.append(
            {
                "label": item.display_name or item.name,
                "delta": float(item.price_delta or 0.0),
                "id": option_ref,
                "option_ref": option_ref,
            }
        )
    return {
        "name": question.display_name or question.name,
        "required": bool(question.required),
        "selection_mode": question.selection_type,
        "question_ref": question.quickclick_question_code or f"odoo-option-question:{question.id}",
        "options": options,
    }


def _group_projection(group) -> dict[str, Any]:
    return {
        "group_ref": group.code,
        "name": group.name,
        "questions": [
            _question_projection(question)
            for question in group.question_ids.filtered("active").sorted(lambda row: (row.sequence, row.id))
        ],
    }


def _integer_twd(value: float | int | Decimal) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def menu_projection(env) -> dict[str, Any]:
    binding = binding_receipt(env)
    if not binding["state"].startswith("PASS"):
        return {**binding, "formal_effect": False}

    contract = source_contract()
    expected = [str(item["sourceProductId"]) for item in contract["allProducts"]]
    products = env["product.template"].sudo().with_company(STORE_BINDING["company_id"]).search(
        [
            ("quickclick_menu_id", "=", STORE_BINDING["quickclick_menu_id"]),
            ("quickclick_product_id", "in", expected),
            ("active", "=", True),
        ]
    )
    by_source: dict[str, list[Any]] = {}
    for product in products:
        by_source.setdefault(str(product.quickclick_product_id or ""), []).append(product)
    missing = [source_id for source_id in expected if source_id not in by_source]
    duplicates = [source_id for source_id, rows in by_source.items() if len(rows) != 1]
    if missing or duplicates or len(products) != 64:
        material = {
            "expected_count": 64,
            "observed_count": len(products),
            "missing": missing,
            "duplicates": duplicates,
            "binding_receipt_ref": binding["receipt_ref"],
        }
        return {
            "state": "HOLD_QUICKCLICK_64_EXACT_MAPPING_REQUIRED",
            "store_ref": STORE_BINDING["store_ref"],
            "expected_count": 64,
            "observed_count": len(products),
            "missing_source_product_ids": missing,
            "duplicate_source_product_ids": duplicates,
            "source_contract_sha256": contract["source"]["sha256"],
            "projection_receipt_ref": "sha256:" + _canonical_sha256(material),
            "formal_effect": False,
            "database_write": False,
        }

    ordered = [by_source[source_id][0] for source_id in expected]
    categories: list[str] = []
    group_records: dict[str, Any] = {}
    product_rows = []
    for product in ordered:
        category = product.quickclick_raw_category or (
            product.pos_categ_ids[:1].name if product.pos_categ_ids else "未分類"
        )
        if category not in categories:
            categories.append(category)
        group = product.wuchang_option_group_id
        if group:
            group_records[group.code] = group
        product_rows.append(
            {
                "id": str(product.quickclick_product_id),
                "odoo_product_template_id": product.id,
                "name": product.name,
                "price": _integer_twd(product.list_price),
                "category": category,
                "groups": [group.code] if group else [],
                "image_url": f"/web/image/product.template/{product.id}/image_512",
            }
        )

    groups = {
        code: _group_projection(group)["questions"]
        for code, group in sorted(group_records.items())
    }
    projection_material = {
        "binding_receipt_ref": binding["receipt_ref"],
        "source_contract_sha256": contract["source"]["sha256"],
        "products": product_rows,
        "groups": groups,
    }
    return {
        "state": "PASS_ODOO_MENU_PROJECTION",
        "store_ref": STORE_BINDING["store_ref"],
        "menu_id": STORE_BINDING["quickclick_menu_id"],
        "source_sha256": contract["source"]["sha256"],
        "observed_at": fields.Datetime.now().isoformat(),
        "categories": categories,
        "products": product_rows,
        "groups": groups,
        "product_count": len(product_rows),
        "projection_receipt_ref": "sha256:" + _canonical_sha256(projection_material),
        "formal_effect": False,
        "database_write": False,
    }


def staff_pos_payload(projection: dict[str, Any]) -> dict[str, Any]:
    categories = list(projection["categories"])
    products = []
    size_data: dict[str, list[list[Any]]] = {}
    for index, product in enumerate(projection["products"]):
        products.append(
            {
                "key": index,
                "source_product_id": product["id"],
                "name": product["name"],
                "category": categories.index(product["category"]),
                "price": product["price"],
                "group": product["groups"][0] if product["groups"] else "",
            }
        )
    for group_ref, questions in projection["groups"].items():
        for question in questions:
            labels = {str(item["label"]).upper() for item in question["options"]}
            if labels & {"S", "M", "L"}:
                size_data[group_ref] = [
                    [item["label"], item["delta"]] for item in question["options"]
                ]
                break
    return {
        "categories": categories,
        "products": products,
        "size_data": size_data,
        "meta": {
            "source": "Odoo Company 3 / exact POS pending QuickClick projection",
            "source_sha256": projection["source_sha256"],
            "status": projection["state"],
            "projection_receipt_ref": projection["projection_receipt_ref"],
            "price_policy": "server-projected base and option deltas; no variant products",
        },
    }


def price_projection(env, payload: dict[str, Any]) -> dict[str, Any]:
    projection = menu_projection(env)
    if projection.get("state") != "PASS_ODOO_MENU_PROJECTION":
        return projection
    product_ref = str(payload.get("product_ref") or "")
    quantity = payload.get("quantity", 1)
    option_refs = payload.get("option_refs") or []
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1 or quantity > 30:
        return {"state": "HOLD_QUANTITY_OUT_OF_RANGE", "formal_effect": False}
    if not isinstance(option_refs, list) or any(not isinstance(item, str) for item in option_refs):
        return {"state": "HOLD_OPTION_REFS_ARRAY_REQUIRED", "formal_effect": False}
    product = next((row for row in projection["products"] if row["id"] == product_ref), None)
    if not product:
        return {"state": "HOLD_PRODUCT_OUTSIDE_QUICKCLICK_64", "formal_effect": False}

    questions = []
    for group_ref in product["groups"]:
        questions.extend(projection["groups"].get(group_ref, []))
    allowed: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for question in questions:
        for option in question["options"]:
            allowed[option["option_ref"]] = (question, option)
    if len(set(option_refs)) != len(option_refs):
        return {"state": "HOLD_DUPLICATE_OPTION_REF", "formal_effect": False}
    unknown = sorted(set(option_refs) - set(allowed))
    if unknown:
        return {"state": "HOLD_OPTION_OUTSIDE_PRODUCT_GROUP", "unknown_option_refs": unknown, "formal_effect": False}

    selected_by_question: dict[str, list[str]] = {}
    delta_total = Decimal("0")
    for option_ref in option_refs:
        question, option = allowed[option_ref]
        selected_by_question.setdefault(question["question_ref"], []).append(option_ref)
        delta_total += Decimal(str(option["delta"]))
    for question in questions:
        selected = selected_by_question.get(question["question_ref"], [])
        if question["required"] and not selected:
            return {"state": "HOLD_REQUIRED_OPTION_MISSING", "question_ref": question["question_ref"], "formal_effect": False}
        if question["selection_mode"] == "single" and len(selected) > 1:
            return {"state": "HOLD_SINGLE_SELECTION_EXCEEDED", "question_ref": question["question_ref"], "formal_effect": False}

    unit = Decimal(str(product["price"])) + delta_total
    total = _integer_twd(unit * quantity)
    material = {
        "product_ref": product_ref,
        "quantity": quantity,
        "option_refs": sorted(option_refs),
        "unit": str(unit),
        "grand_total": total,
        "projection_receipt_ref": projection["projection_receipt_ref"],
    }
    calculation_hash = "sha256:" + _canonical_sha256(material)
    return {
        "state": "PASS_SERVER_PRICE",
        "store_ref": STORE_BINDING["store_ref"],
        "product_ref": product_ref,
        "quantity": quantity,
        "currency": "TWD",
        "minor_unit": 1,
        "base_unit_price": product["price"],
        "option_delta_total": _integer_twd(delta_total),
        "unit_price": _integer_twd(unit),
        "grand_total": total,
        "calculation_hash": calculation_hash,
        "pricing_receipt_ref": "price:" + calculation_hash,
        "projection_receipt_ref": projection["projection_receipt_ref"],
        "formal_effect": False,
        "database_write": False,
        "order_created": False,
        "payment_capture": False,
    }
