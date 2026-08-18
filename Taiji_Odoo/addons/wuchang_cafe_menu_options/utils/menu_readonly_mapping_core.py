from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from typing import Any


MENU_MAPPING_SCHEMA_REF = "LIVE_ODOO_MENU_DATA_READONLY_MAPPING_V1"
SOURCE_MODULES = (
    "wuchang_cafe_menu_options",
    "wuchang_core",
    "wuchang_cafe_ai_gateway",
)
SOURCE_MODELS = (
    "wuchang.menu.item",
    "wuchang.menu.addon",
    "wuchang.menu.attribute",
    "wuchang.menu.attribute.value",
    "wuchang.menu.item.addon",
    "wuchang.menu.item.attribute",
    "wuchang.cafe.option.group",
    "wuchang.cafe.option.question",
    "wuchang.cafe.option.item",
    "product.template",
)
MENU_FIELDS_MAPPED = (
    "wuchang.menu.item.code",
    "wuchang.menu.item.name",
    "wuchang.menu.item.base_price",
    "wuchang.menu.item.category",
    "wuchang.menu.item.active",
    "wuchang.menu.item.description",
    "wuchang.menu.item.addon_line_ids.delta_price",
    "wuchang.menu.item.attribute.technical_key",
    "wuchang.menu.item.attribute.value.delta_price",
    "wuchang.cafe.option.group.code",
    "wuchang.cafe.option.group.w5c_code",
    "wuchang.cafe.option.question.selection_type",
    "wuchang.cafe.option.item.price_delta",
    "wuchang.cafe.option.item.child_group_code",
    "wuchang.cafe.option.item.quickclick_item_code",
    "wuchang.cafe.option.item.quickclick_question_code",
    "product.template.quickclick_menu_id",
    "product.template.quickclick_product_id",
    "product.template.quickclick_product_code",
    "product.template.quickclick_sku",
    "product.template.quickclick_option_group_code",
    "product.template.quickclick_image_url",
    "product.template.quickclick_raw_category",
    "product.template.quickclick_raw_price",
    "product.template.normalized_price_basis",
    "product.template.normalized_price_note",
    "product.template.wuchang_pos_locked",
    "product.template.w5c_code",
)


def sha256_hex(data: Any) -> str:
    if isinstance(data, str):
        raw = data.encode("utf-8")
    elif isinstance(data, bytes):
        raw = data
    else:
        raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_bool(value: Any) -> bool:
    return bool(value)


def _as_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _get(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


def _record_list(source: dict[str, Any], key: str) -> list[dict[str, Any]]:
    items = source.get(key) or []
    return [item for item in items if isinstance(item, dict)]


def _sorted_dicts(rows: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: tuple(_as_text(row.get(key)) for key in keys))


def _image_descriptor(record: Any, source_reference: str | None = None) -> dict[str, Any]:
    reference = _as_text(source_reference or _get(record, "quickclick_image_url") or _get(record, "image_reference"))
    route = _as_text(_get(record, "image_route"))
    image_hash = _as_text(_get(record, "image_hash"))
    if not image_hash and (reference or route):
        image_hash = sha256_hex(f"{reference}|{route}")
    return {
        "reference": reference or None,
        "route": route or None,
        "hash": image_hash or None,
    }


def _w5c_payload(record: Any, fallback_entity: str) -> dict[str, Any]:
    return {
        "code": _as_text(_get(record, "w5c_code")) or None,
        "domain": _as_text(_get(record, "w5c_domain") or "CAFE") or "CAFE",
        "entity": _as_text(_get(record, "w5c_entity") or fallback_entity) or fallback_entity,
        "topology": _as_text(_get(record, "w5c_topology")) or None,
        "time_state": _as_text(_get(record, "w5c_time_state")) or None,
        "authority": _as_text(_get(record, "w5c_authority")) or None,
    }


def _menu_addons_by_item(source: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _record_list(source, "menu_item_addons"):
        item_code = _as_text(row.get("item_code"))
        if not item_code:
            continue
        grouped[item_code].append(
            {
                "code": _as_text(row.get("addon_code")) or None,
                "name": _as_text(row.get("addon_name")) or None,
                "delta_price": _as_float(row.get("delta_price")),
                "addon_type": _as_text(row.get("addon_type")) or None,
                "active": _as_bool(row.get("active", True)),
            }
        )
    for item_code in grouped:
        grouped[item_code] = _sorted_dicts(grouped[item_code], "code", "name")
    return grouped


def _menu_attributes_by_item(source: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    value_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _record_list(source, "menu_attribute_values"):
        technical_key = _as_text(row.get("technical_key"))
        if technical_key:
            value_index[technical_key].append(
                {
                    "name": _as_text(row.get("name")) or None,
                    "delta_price": _as_float(row.get("delta_price")),
                    "w5c": _w5c_payload(row, "OPTION_ITEM"),
                }
            )
    for key in value_index:
        value_index[key] = _sorted_dicts(value_index[key], "name")
    for row in _record_list(source, "menu_item_attributes"):
        item_code = _as_text(row.get("item_code"))
        technical_key = _as_text(row.get("technical_key"))
        if not item_code or not technical_key:
            continue
        grouped[item_code].append(
            {
                "code": technical_key,
                "name": _as_text(row.get("attribute_name")) or technical_key,
                "selection_type": _as_text(row.get("selection_type") or "single"),
                "required": _as_bool(row.get("required", True)),
                "allowed_values": value_index.get(technical_key, []),
                "w5c": _w5c_payload(row, "OPTION_QUESTION"),
            }
        )
    for item_code in grouped:
        grouped[item_code] = _sorted_dicts(grouped[item_code], "code", "name")
    return grouped


def _normalize_item(row: dict[str, Any], item_addons: dict[str, list[dict[str, Any]]], item_attributes: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    code = _as_text(row.get("code"))
    return {
        "source_model": "wuchang.menu.item",
        "code": code or None,
        "name": _as_text(row.get("name")) or None,
        "category": _as_text(row.get("category")) or None,
        "base_price": _as_float(row.get("base_price")),
        "description": _as_text(row.get("description")) or None,
        "active": _as_bool(row.get("active", True)),
        "supply_status": "active" if _as_bool(row.get("active", True)) else "inactive",
        "normalized_price_basis": _as_text(row.get("normalized_price_basis")) or None,
        "normalized_price_note": _as_text(row.get("normalized_price_note")) or None,
        "w5c": _w5c_payload(row, "ITEM"),
        "addons": item_addons.get(code, []),
        "options": item_attributes.get(code, []),
        "image": _image_descriptor(row),
    }


def _normalize_option_group(row: dict[str, Any]) -> dict[str, Any]:
    code = _as_text(row.get("code")) or _as_text(row.get("technical_key"))
    return {
        "source_model": row.get("source_model") or "wuchang.menu.attribute",
        "code": code or None,
        "name": _as_text(row.get("name")) or None,
        "sequence": int(row.get("sequence") or 0),
        "active": _as_bool(row.get("active", True)),
        "source": _as_text(row.get("source")) or None,
        "note": _as_text(row.get("note")) or None,
        "w5c": _w5c_payload(row, "OPTION_GROUP"),
    }


def _normalize_option_question(row: dict[str, Any]) -> dict[str, Any]:
    code = _as_text(row.get("code")) or _as_text(row.get("technical_key"))
    return {
        "source_model": row.get("source_model") or "wuchang.menu.attribute",
        "code": code or None,
        "group_code": _as_text(row.get("group_code")) or None,
        "name": _as_text(row.get("name")) or None,
        "display_name": _as_text(row.get("display_name")) or None,
        "selection_type": _as_text(row.get("selection_type") or "single"),
        "required": _as_bool(row.get("required", True)),
        "active": _as_bool(row.get("active", True)),
        "quickclick_question_code": _as_text(row.get("quickclick_question_code")) or None,
        "w5c": _w5c_payload(row, "OPTION_QUESTION"),
    }


def _normalize_option_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_model": row.get("source_model") or "wuchang.menu.attribute.value",
        "code": _as_text(row.get("code")) or None,
        "question_code": _as_text(row.get("question_code")) or None,
        "name": _as_text(row.get("name")) or None,
        "display_name": _as_text(row.get("display_name")) or None,
        "price_delta": _as_float(row.get("price_delta")),
        "child_group_code": _as_text(row.get("child_group_code")) or None,
        "active": _as_bool(row.get("active", True)),
        "quickclick_item_code": _as_text(row.get("quickclick_item_code")) or None,
        "quickclick_question_code": _as_text(row.get("quickclick_question_code")) or None,
        "w5c": _w5c_payload(row, "OPTION_ITEM"),
    }


def _normalize_product_template(row: dict[str, Any]) -> dict[str, Any]:
    image = _image_descriptor(row)
    image_route = image["route"] or (f"/web/image/product.template/{row.get('id')}/image_1920" if row.get("id") else None)
    if image_route and not image["route"]:
        image["route"] = image_route
        if not image["hash"]:
            image["hash"] = sha256_hex(image_route)
    return {
        "source_model": "product.template",
        "id": row.get("id"),
        "name": _as_text(row.get("name")) or None,
        "quickclick_menu_id": _as_text(row.get("quickclick_menu_id")) or None,
        "quickclick_product_id": _as_text(row.get("quickclick_product_id")) or None,
        "quickclick_product_code": _as_text(row.get("quickclick_product_code")) or None,
        "quickclick_sku": _as_text(row.get("quickclick_sku")) or None,
        "quickclick_option_group_code": _as_text(row.get("quickclick_option_group_code")) or None,
        "quickclick_image_url": _as_text(row.get("quickclick_image_url")) or None,
        "quickclick_raw_category": _as_text(row.get("quickclick_raw_category")) or None,
        "quickclick_raw_price": _as_float(row.get("quickclick_raw_price")),
        "normalized_price_basis": _as_text(row.get("normalized_price_basis")) or None,
        "normalized_price_note": _as_text(row.get("normalized_price_note")) or None,
        "wuchang_pos_locked": _as_bool(row.get("wuchang_pos_locked", False)),
        "w5c": _w5c_payload(row, "PRODUCT_TEMPLATE"),
        "image": image,
    }


def _normalize_option_group_rows(source: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in _record_list(source, "menu_attributes"):
        normalized = _normalize_option_group(
            {
                "source_model": "wuchang.menu.attribute",
                "code": _as_text(row.get("technical_key")),
                "technical_key": _as_text(row.get("technical_key")),
                "name": _as_text(row.get("name")),
                "sequence": row.get("sequence", 0),
                "active": row.get("active", True),
                "source": "wuchang_core.menu.attribute",
                "note": row.get("note"),
                "w5c_code": row.get("w5c_code"),
                "w5c_domain": row.get("w5c_domain"),
                "w5c_entity": row.get("w5c_entity"),
                "w5c_topology": row.get("w5c_topology"),
                "w5c_time_state": row.get("w5c_time_state"),
                "w5c_authority": row.get("w5c_authority"),
            }
        )
        key = (normalized["source_model"], normalized["code"] or "")
        if key not in seen:
            rows.append(normalized)
            seen.add(key)
    for row in _record_list(source, "option_groups"):
        normalized = _normalize_option_group(row)
        key = (normalized["source_model"], normalized["code"] or "")
        if key not in seen:
            rows.append(normalized)
            seen.add(key)
    return _sorted_dicts(rows, "source_model", "code", "name")


def _normalize_option_question_rows(source: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in _record_list(source, "menu_item_attributes"):
        normalized = _normalize_option_question(
            {
                "source_model": "wuchang.menu.item.attribute",
                "code": _as_text(row.get("technical_key")),
                "group_code": _as_text(row.get("technical_key")),
                "name": _as_text(row.get("attribute_name")) or _as_text(row.get("technical_key")),
                "display_name": _as_text(row.get("attribute_name")) or None,
                "selection_type": _as_text(row.get("selection_type") or "single"),
                "required": row.get("required", True),
                "quickclick_question_code": row.get("quickclick_question_code"),
                "w5c_code": row.get("w5c_code"),
                "w5c_domain": row.get("w5c_domain"),
                "w5c_entity": row.get("w5c_entity"),
                "w5c_topology": row.get("w5c_topology"),
                "w5c_time_state": row.get("w5c_time_state"),
                "w5c_authority": row.get("w5c_authority"),
            }
        )
        key = (normalized["source_model"], normalized["code"] or "")
        if key not in seen:
            rows.append(normalized)
            seen.add(key)
    for row in _record_list(source, "option_questions"):
        normalized = _normalize_option_question(row)
        key = (normalized["source_model"], normalized["code"] or "")
        if key not in seen:
            rows.append(normalized)
            seen.add(key)
    return _sorted_dicts(rows, "source_model", "code", "name")


def _normalize_option_item_rows(source: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in _record_list(source, "menu_attribute_values"):
        normalized = _normalize_option_item(
            {
                "source_model": "wuchang.menu.attribute.value",
                "code": _as_text(row.get("code")) or _as_text(row.get("technical_key")) or _as_text(row.get("name")),
                "question_code": _as_text(row.get("technical_key")),
                "name": _as_text(row.get("name")),
                "display_name": _as_text(row.get("name")) or None,
                "price_delta": row.get("delta_price"),
                "child_group_code": row.get("child_group_code"),
                "active": row.get("active", True),
                "quickclick_item_code": row.get("quickclick_item_code"),
                "quickclick_question_code": row.get("quickclick_question_code"),
                "w5c_code": row.get("w5c_code"),
                "w5c_domain": row.get("w5c_domain"),
                "w5c_entity": row.get("w5c_entity"),
                "w5c_topology": row.get("w5c_topology"),
                "w5c_time_state": row.get("w5c_time_state"),
                "w5c_authority": row.get("w5c_authority"),
            }
        )
        key = (normalized["source_model"], normalized["code"] or "")
        if key not in seen:
            rows.append(normalized)
            seen.add(key)
    for row in _record_list(source, "option_items"):
        normalized = _normalize_option_item(row)
        key = (normalized["source_model"], normalized["code"] or "")
        if key not in seen:
            rows.append(normalized)
            seen.add(key)
    return _sorted_dicts(rows, "source_model", "code", "name")


def _normalize_menu_items(source: dict[str, Any], item_addons: dict[str, list[dict[str, Any]]], item_attributes: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = [_normalize_item(row, item_addons, item_attributes) for row in _record_list(source, "menu_items")]
    return _sorted_dicts(rows, "code", "name")


def _normalize_product_templates(source: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in _record_list(source, "product_templates"):
        include = any(
            _as_text(row.get(field))
            for field in (
                "quickclick_menu_id",
                "quickclick_product_id",
                "quickclick_product_code",
                "quickclick_sku",
                "quickclick_option_group_code",
                "quickclick_image_url",
                "quickclick_raw_category",
                "normalized_price_basis",
                "normalized_price_note",
                "w5c_code",
            )
        ) or _as_bool(row.get("wuchang_pos_locked", False))
        if include:
            rows.append(_normalize_product_template(row))
    return _sorted_dicts(rows, "quickclick_menu_id", "quickclick_product_code", "name")


def build_readonly_menu_snapshot(source: dict[str, Any]) -> dict[str, Any]:
    source = copy.deepcopy(source or {})
    item_addons = _menu_addons_by_item(source)
    item_attributes = _menu_attributes_by_item(source)
    menu_items = _normalize_menu_items(source, item_addons, item_attributes)
    option_groups = _normalize_option_group_rows(source)
    option_questions = _normalize_option_question_rows(source)
    option_items = _normalize_option_item_rows(source)
    product_templates = _normalize_product_templates(source)
    w5c_reused = any(
        bool(record.get("w5c", {}).get("code"))
        for record in (
            *menu_items,
            *option_groups,
            *option_questions,
            *option_items,
            *product_templates,
        )
    )
    snapshot = {
        "snapshot_ref": MENU_MAPPING_SCHEMA_REF,
        "source_modules": list(SOURCE_MODULES),
        "source_models": list(SOURCE_MODELS),
        "menu_fields_mapped": list(MENU_FIELDS_MAPPED),
        "catalog": {
            "menu_items": menu_items,
            "option_groups": option_groups,
            "option_questions": option_questions,
            "option_items": option_items,
            "product_templates": product_templates,
        },
        "w5c_reused": w5c_reused,
        "deterministic_output": True,
    }
    snapshot["content_sha256"] = sha256_hex(snapshot)
    return snapshot


def build_public_menu_payload(snapshot: dict[str, Any], store_ref: str = "wuchang_cafe_menu_options") -> dict[str, Any]:
    snapshot = copy.deepcopy(snapshot or {})
    catalog = snapshot.get("catalog") or {}
    items = [
        {
            "source_model": item.get("source_model"),
            "code": item.get("code"),
            "name": item.get("name"),
            "category": item.get("category"),
            "base_price": item.get("base_price"),
            "active": item.get("active"),
            "description": item.get("description"),
            "supply_status": item.get("supply_status"),
            "addons": item.get("addons") or [],
            "options": item.get("options") or [],
            "w5c": item.get("w5c") or {},
            "image": item.get("image") or {},
            "normalized_price_basis": item.get("normalized_price_basis"),
            "normalized_price_note": item.get("normalized_price_note"),
        }
        for item in catalog.get("menu_items", [])
        if item.get("active", True)
    ]
    items = _sorted_dicts(items, "category", "code", "name")
    categories = []
    seen_categories: set[str] = set()
    for item in items:
        category = _as_text(item.get("category"))
        if category and category not in seen_categories:
            categories.append({"code": category, "name": category, "active": True})
            seen_categories.add(category)
    categories = _sorted_dicts(categories, "code", "name")
    response = {
        "state": "PASS",
        "schema": MENU_MAPPING_SCHEMA_REF,
        "store_ref": store_ref,
        "menu": {
            "categories": categories,
            "items": items,
        },
        "mapping_sha256": snapshot.get("content_sha256"),
    }
    response["response_sha256"] = sha256_hex(response)
    return response


def _record_to_dict(record: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: _get(record, field) for field in fields}


def collect_readonly_menu_snapshot_from_env(env: Any, limit: int = 200) -> dict[str, Any]:
    menu_items = env["wuchang.menu.item"].search([], limit=limit, order="code asc, name asc, id asc")
    menu_addons = env["wuchang.menu.addon"].search([], limit=limit, order="code asc, name asc, id asc")
    menu_attributes = env["wuchang.menu.attribute"].search([], limit=limit, order="technical_key asc, name asc, id asc")
    menu_attribute_values = env["wuchang.menu.attribute.value"].search([], limit=limit, order="attribute_id asc, name asc, id asc")
    menu_item_addons = env["wuchang.menu.item.addon"].search([], limit=limit, order="item_id asc, addon_id asc, id asc")
    menu_item_attributes = env["wuchang.menu.item.attribute"].search([], limit=limit, order="item_id asc, attribute_id asc, id asc")
    option_groups = env["wuchang.cafe.option.group"].search([], limit=limit, order="code asc, name asc, id asc")
    option_questions = env["wuchang.cafe.option.question"].search([], limit=limit, order="group_id asc, sequence asc, name asc, id asc")
    option_items = env["wuchang.cafe.option.item"].search([], limit=limit, order="question_id asc, sequence asc, name asc, id asc")
    product_templates = env["product.template"].search([], limit=limit, order="quickclick_menu_id asc, quickclick_product_code asc, name asc, id asc")

    source = {
        "menu_items": [
            _record_to_dict(
                record,
                (
                    "id",
                    "code",
                    "name",
                    "base_price",
                    "category",
                    "description",
                    "active",
                    "normalized_price_basis",
                    "normalized_price_note",
                ),
            )
            for record in menu_items
        ],
        "menu_addons": [
            _record_to_dict(record, ("id", "code", "name", "delta_price", "addon_type", "active"))
            for record in menu_addons
        ],
        "menu_attributes": [
            _record_to_dict(
                record,
                ("id", "technical_key", "name", "sequence", "active", "note", "w5c_code", "w5c_domain", "w5c_entity", "w5c_topology", "w5c_time_state", "w5c_authority"),
            )
            for record in menu_attributes
        ],
        "menu_attribute_values": [
            {
                **_record_to_dict(
                    record,
                    ("id", "name", "delta_price", "active", "w5c_code", "w5c_domain", "w5c_entity", "w5c_topology", "w5c_time_state", "w5c_authority"),
                ),
                "technical_key": _get(getattr(record, "attribute_id", None), "technical_key") or _get(getattr(record, "attribute_id", None), "name"),
            }
            for record in menu_attribute_values
        ],
        "menu_item_addons": [
            {
                "item_code": _get(getattr(record, "item_id", None), "code"),
                "addon_code": _get(getattr(record, "addon_id", None), "code"),
                "addon_name": _get(getattr(record, "addon_id", None), "name"),
                "delta_price": _get(record, "delta_price"),
                "addon_type": _get(getattr(record, "addon_id", None), "addon_type"),
                "active": _get(getattr(record, "addon_id", None), "active", True),
            }
            for record in menu_item_addons
        ],
        "menu_item_attributes": [
            {
                "item_code": _get(getattr(record, "item_id", None), "code"),
                "technical_key": _get(getattr(record, "attribute_id", None), "technical_key") or _get(getattr(record, "attribute_id", None), "name"),
                "attribute_name": _get(getattr(record, "attribute_id", None), "name"),
                "selection_type": "single",
                "required": True,
                "quickclick_question_code": _get(record, "quickclick_question_code"),
                "w5c_code": _get(record, "w5c_code"),
                "w5c_domain": _get(record, "w5c_domain"),
                "w5c_entity": _get(record, "w5c_entity"),
                "w5c_topology": _get(record, "w5c_topology"),
                "w5c_time_state": _get(record, "w5c_time_state"),
                "w5c_authority": _get(record, "w5c_authority"),
            }
            for record in menu_item_attributes
        ],
        "option_groups": [
            _record_to_dict(record, ("id", "code", "name", "sequence", "active", "source", "note", "w5c_code", "w5c_domain", "w5c_entity", "w5c_topology", "w5c_time_state", "w5c_authority"))
            for record in option_groups
        ],
        "option_questions": [
            {
                **_record_to_dict(
                    record,
                    ("id", "name", "display_name", "selection_type", "required", "active", "quickclick_question_code", "w5c_code", "w5c_domain", "w5c_entity", "w5c_topology", "w5c_time_state", "w5c_authority"),
                ),
                "code": _get(record, "code") or _get(getattr(record, "group_id", None), "code"),
                "group_code": _get(getattr(record, "group_id", None), "code"),
                "source_model": "wuchang.cafe.option.question",
            }
            for record in option_questions
        ],
        "option_items": [
            {
                **_record_to_dict(
                    record,
                    ("id", "name", "display_name", "price_delta", "child_group_code", "active", "quickclick_item_code", "quickclick_question_code", "w5c_code", "w5c_domain", "w5c_entity", "w5c_topology", "w5c_time_state", "w5c_authority"),
                ),
                "code": _get(record, "code") or _get(getattr(record, "question_id", None), "code") or _get(getattr(record, "question_id", None), "name"),
                "question_code": _get(getattr(record, "question_id", None), "code") or _get(getattr(record, "question_id", None), "name"),
                "source_model": "wuchang.cafe.option.item",
            }
            for record in option_items
        ],
        "product_templates": [
            _record_to_dict(
                record,
                (
                    "id",
                    "name",
                    "quickclick_menu_id",
                    "quickclick_product_id",
                    "quickclick_product_code",
                    "quickclick_sku",
                    "quickclick_option_group_code",
                    "quickclick_image_url",
                    "quickclick_raw_category",
                    "quickclick_raw_price",
                    "normalized_price_basis",
                    "normalized_price_note",
                    "wuchang_pos_locked",
                    "w5c_code",
                    "w5c_domain",
                    "w5c_entity",
                    "w5c_topology",
                    "w5c_time_state",
                    "w5c_authority",
                ),
            )
            for record in product_templates
        ],
    }
    return build_readonly_menu_snapshot(source)
