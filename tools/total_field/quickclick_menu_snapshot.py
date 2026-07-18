#!/usr/bin/env python3
"""Build a deterministic, read-only menu snapshot from a QuickClick XLSX export."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from tools.total_field.w7tp_core_encoding import build_source_coordinate


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
MAJOR_CATEGORIES = [
    {"id": "coffee", "label": "咖啡飲品"},
    {"id": "tea-other", "label": "茶與無咖啡因"},
    {"id": "food", "label": "餐食與點心"},
    {"id": "beans", "label": "咖啡豆"},
    {"id": "drip", "label": "濾掛咖啡"},
]
SOURCE_CATEGORY_TO_MAJOR = {
    "義式咖啡": "coffee",
    "單品手沖": "coffee",
    "聊國簡餐": "food",
    "茶": "tea-other",
    "無咖啡因": "tea-other",
    "點心": "food",
    "咖啡豆": "beans",
    "濾掛咖啡": "drip",
}
EXCLUDED_SOURCE_CATEGORIES = {"濾掛咖啡"}
SOURCE_COORDINATE_NAMESPACE = "QUICKCLICK"


def source_product_ref(menu_id: str, product_coordinate: str) -> str:
    """Return the stable bottom-up coordinate for one source product."""

    return build_source_coordinate("PRODUCT", menu_id, product_coordinate)


def source_question_ref(menu_id: str, question_coordinate: str) -> str:
    """Return the stable bottom-up coordinate for one source option question."""

    return build_source_coordinate("QUESTION", menu_id, question_coordinate)


def source_option_ref(menu_id: str, option_coordinate: str) -> str:
    """Return the stable bottom-up coordinate for one source option value."""

    return build_source_coordinate("OPTION", menu_id, option_coordinate)


def _text_nodes(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.iter(f"{{{MAIN_NS}}}t"))


def _column_index(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference)
    if not match:
        raise ValueError(f"Invalid XLSX cell reference: {reference!r}")
    index = 0
    for character in match.group(1):
        index = index * 26 + ord(character) - ord("A") + 1
    return index - 1


def _numeric_value(raw: str) -> int | float | str:
    try:
        number = float(raw)
    except ValueError:
        return raw
    return int(number) if number.is_integer() else number


class XlsxWorkbook:
    """Minimal XLSX reader using only Python's standard library."""

    def __init__(self, source: Path) -> None:
        self.source = source

    def read_sheets(self) -> list[tuple[str, list[list[Any]]]]:
        with zipfile.ZipFile(self.source) as archive:
            shared_strings = self._shared_strings(archive)
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            targets = {
                rel.attrib["Id"]: rel.attrib["Target"]
                for rel in relationships.findall(f"{{{PKG_REL_NS}}}Relationship")
            }
            sheets: list[tuple[str, list[list[Any]]]] = []
            for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet"):
                name = sheet.attrib["name"]
                rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
                target = targets[rel_id]
                sheet_path = posixpath.normpath(posixpath.join("xl", target)).lstrip("/")
                sheets.append((name, self._read_sheet(archive, sheet_path, shared_strings)))
            return sheets

    @staticmethod
    def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        return [_text_nodes(item) for item in root.findall(f"{{{MAIN_NS}}}si")]

    @staticmethod
    def _read_sheet(
        archive: zipfile.ZipFile,
        path: str,
        shared_strings: list[str],
    ) -> list[list[Any]]:
        root = ET.fromstring(archive.read(path))
        rows: list[list[Any]] = []
        for row in root.findall(f".//{{{MAIN_NS}}}row"):
            values: list[Any] = []
            for cell in row.findall(f"{{{MAIN_NS}}}c"):
                index = _column_index(cell.attrib.get("r", ""))
                while len(values) <= index:
                    values.append(None)
                cell_type = cell.attrib.get("t")
                value_node = cell.find(f"{{{MAIN_NS}}}v")
                if cell_type == "inlineStr":
                    value: Any = _text_nodes(cell)
                elif value_node is None or value_node.text is None:
                    value = None
                elif cell_type == "s":
                    value = shared_strings[int(value_node.text)]
                elif cell_type == "b":
                    value = value_node.text == "1"
                elif cell_type == "str":
                    value = value_node.text
                else:
                    value = _numeric_value(value_node.text)
                values[index] = value
            rows.append(values)
        return rows


def _rows_as_dicts(rows: list[list[Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    headers = [str(value).strip() if value is not None else "" for value in rows[0]]
    records: list[dict[str, Any]] = []
    for row in rows[1:]:
        record = {
            header: row[index] if index < len(row) else None
            for index, header in enumerate(headers)
            if header
        }
        if any(value not in (None, "") for value in record.values()):
            records.append(record)
    return records


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _price(value: Any) -> int | float:
    if value in (None, ""):
        return 0
    number = float(value)
    return int(number) if number.is_integer() else number


def _option_group_refs(value: Any) -> list[str]:
    return [part for part in re.split(r"[,;|+\s]+", _clean(value)) if part]


def build_snapshot(
    source: Path,
    expected_sha256: str,
    source_title: str,
    source_drive_id: str,
    source_copy_drive_id: str,
    source_modified_at: str,
) -> dict[str, Any]:
    raw = source.read_bytes()
    source_sha256 = hashlib.sha256(raw).hexdigest()
    if source_sha256 != expected_sha256:
        raise ValueError(
            f"Source SHA-256 mismatch: expected {expected_sha256}, got {source_sha256}"
        )

    sheets = XlsxWorkbook(source).read_sheets()
    tables = [(name, _rows_as_dicts(rows)) for name, rows in sheets]

    def table_with(*required_headers: str) -> tuple[str, list[dict[str, Any]]]:
        for name, records in tables:
            if not records:
                continue
            if all(header in records[0] for header in required_headers):
                return name, records
        raise ValueError(f"Workbook table missing headers: {', '.join(required_headers)}")

    menu_sheet, menus = table_with("主商品菜單編號", "主商品菜單名稱")
    product_sheet, product_rows = table_with("主商品編號", "主商品名稱", "主商品價格")
    group_sheet, group_rows = table_with("題型選項組合編號", "題型選項組合名稱")
    option_sheet, option_rows = table_with(
        "題型選項組合編號", "加購題型", "加購選項", "加購選項價格"
    )
    if len(menus) != 1:
        raise ValueError(f"Expected exactly one menu, found {len(menus)}")

    group_names: OrderedDict[str, str] = OrderedDict()
    for row in group_rows:
        group_id = _clean(row.get("題型選項組合編號"))
        group_name = _clean(row.get("題型選項組合名稱"))
        if not group_id or not group_name:
            raise ValueError("Option group ID and name are required")
        if group_id in group_names:
            raise ValueError(f"Duplicate option group ID: {group_id}")
        group_names[group_id] = group_name

    questions_by_group: dict[str, OrderedDict[str, dict[str, Any]]] = {
        group_id: OrderedDict() for group_id in group_names
    }
    seen_option_codes: dict[tuple[str, str, str], set[str]] = {}
    duplicate_semantic_option_rows = 0
    question_code_conflicts: list[dict[str, str]] = []
    for row in option_rows:
        group_id = _clean(row.get("題型選項組合編號"))
        if group_id not in group_names:
            raise ValueError(f"Option row references unknown group: {group_id}")
        question_code = _clean(row.get("加購題型代碼"))
        question_name = _clean(row.get("加購題型"))
        question_key = question_name or question_code
        if not question_key:
            raise ValueError(f"Option group {group_id} contains a question without an identity")
        questions = questions_by_group[group_id]
        if question_key not in questions:
            selection_raw = _clean(row.get("選項題型(單/雙)"))
            questions[question_key] = {
                "question_code": question_code or None,
                "name": question_name,
                "display_name": _clean(row.get("加購題型顯示名稱")) or question_name,
                "description": _clean(row.get("加購題型描述")) or None,
                "selection_mode": "single" if selection_raw == "單" else "multiple",
                "required": _clean(row.get("是否必填(Y/N)")).upper() == "Y",
                "options": [],
            }
        elif question_code and not questions[question_key]["question_code"]:
            questions[question_key]["question_code"] = question_code
        elif (
            question_code
            and questions[question_key]["question_code"]
            and questions[question_key]["question_code"] != question_code
        ):
            question_code_conflicts.append(
                {
                    "group_id": group_id,
                    "question": question_key,
                    "first_code": questions[question_key]["question_code"],
                    "conflicting_code": question_code,
                }
            )
        question = questions[question_key]
        option_code = _clean(row.get("加購選項代碼"))
        option_name = _clean(row.get("加購選項"))
        if option_code:
            option_identity = (group_id, question_key, option_code)
            seen_option_codes.setdefault(option_identity, set()).add(option_name)
        candidate = {
            "option_code": option_code or None,
            "name": option_name,
            "display_name": _clean(row.get("加購選項顯示名稱")) or option_name,
            "price_delta": _price(row.get("加購選項價格")),
            "submenu_menu_id": _clean(row.get("子選單菜單編號")) or None,
        }
        semantic_identity = (
            candidate["name"],
            candidate["display_name"],
            candidate["price_delta"],
            candidate["submenu_menu_id"],
        )
        existing_identities = {
            (
                option["name"],
                option["display_name"],
                option["price_delta"],
                option["submenu_menu_id"],
            )
            for option in question["options"]
        }
        if semantic_identity in existing_identities:
            duplicate_semantic_option_rows += 1
        else:
            question["options"].append(candidate)

    products: list[dict[str, Any]] = []
    seen_product_ids: set[str] = set()
    for row in product_rows:
        product_id = _clean(row.get("主商品編號"))
        name = _clean(row.get("主商品名稱"))
        category = _clean(row.get("主商品類別"))
        if not product_id or not name or not category:
            raise ValueError("Product ID, name, and category are required")
        if product_id in seen_product_ids:
            raise ValueError(f"Duplicate product ID: {product_id}")
        seen_product_ids.add(product_id)
        option_group_ids = _option_group_refs(row.get("套用加購選單"))
        unknown = [group_id for group_id in option_group_ids if group_id not in group_names]
        if unknown:
            raise ValueError(f"Product {product_id} references unknown groups: {unknown}")
        products.append(
            {
                "product_id": product_id,
                "product_code": _clean(row.get("主商品代碼")) or None,
                "sku": _clean(row.get("主商品料號")) or None,
                "category": category,
                "name": name,
                "base_price": _price(row.get("主商品價格")),
                "option_group_ids": option_group_ids,
            }
        )

    groups = [
        {
            "group_id": group_id,
            "name": group_name,
            "questions": list(questions_by_group[group_id].values()),
        }
        for group_id, group_name in group_names.items()
    ]
    for group in groups:
        for question in group["questions"]:
            if question["required"] and not question["options"]:
                raise ValueError(
                    f"Required question {question['name']} in {group['group_id']} has no options"
                )

    source_warnings = [
        {
            "code": "OPTION_CODE_REUSED_FOR_MULTIPLE_NAMES",
            "group_id": group_id,
            "question_key": question_key,
            "option_code": option_code,
            "option_names": sorted(option_names),
        }
        for (group_id, question_key, option_code), option_names in seen_option_codes.items()
        if len(option_names) > 1
    ]
    if duplicate_semantic_option_rows:
        source_warnings.append(
            {
                "code": "DUPLICATE_SEMANTIC_OPTION_ROWS_NORMALIZED",
                "row_count": duplicate_semantic_option_rows,
            }
        )
    source_warnings.extend(
        {"code": "QUESTION_CODE_CONFLICT", **conflict}
        for conflict in question_code_conflicts
    )

    menu = menus[0]
    return {
        "schema_version": "w7tp.quickclick_menu_snapshot.v1",
        "authority_state": (
            "VERIFIED_CLOUD_EXPORT_WITH_SOURCE_WARNINGS"
            if source_warnings
            else "VERIFIED_CLOUD_EXPORT"
        ),
        "source": {
            "title": source_title,
            "drive_id": source_drive_id,
            "identical_source_copy_drive_id": source_copy_drive_id,
            "modified_at": source_modified_at,
            "sha256": source_sha256,
            "byte_size": len(raw),
            "acquisition_mode": "google_drive_raw_read_only",
        },
        "workbook": {
            "sheet_names": [name for name, _ in sheets],
            "menu_sheet": menu_sheet,
            "product_sheet": product_sheet,
            "option_group_sheet": group_sheet,
            "option_item_sheet": option_sheet,
        },
        "menu": {
            "menu_id": _clean(menu.get("主商品菜單編號")),
            "name": _clean(menu.get("主商品菜單名稱")),
        },
        "counts": {
            "products": len(products),
            "option_groups": len(groups),
            "question_groups": sum(len(group["questions"]) for group in groups),
            "option_items": sum(
                len(question["options"])
                for group in groups
                for question in group["questions"]
            ),
            "raw_option_rows": len(option_rows),
            "products_with_options": sum(bool(product["option_group_ids"]) for product in products),
            "source_warnings": len(source_warnings),
        },
        "source_warnings": source_warnings,
        "products": products,
        "option_groups": groups,
    }


def build_web_data(snapshot: dict[str, Any]) -> dict[str, Any]:
    unknown_categories = sorted(
        {product["category"] for product in snapshot["products"]}
        - set(SOURCE_CATEGORY_TO_MAJOR)
        - EXCLUDED_SOURCE_CATEGORIES
    )
    if unknown_categories:
        raise ValueError(f"Web category mapping missing: {unknown_categories}")

    def question_priority(question: dict[str, Any]) -> tuple[int, str]:
        name = question["name"]
        if name == "尺寸":
            return (10, name)
        if "溫度" in name:
            return (20, name)
        if name == "甜度":
            return (30, name)
        if "口味" in name or "糖漿" in name:
            return (40, name)
        return (50, name)

    groups: list[dict[str, Any]] = []
    for group in snapshot["option_groups"]:
        questions = []
        for question_index, question in enumerate(
            sorted(group["questions"], key=question_priority), start=1
        ):
            options = [
                {
                    "id": f"{group['group_id']}:Q{question_index}:O{option_index}",
                    "sourceOptionCode": option["option_code"],
                    "name": option["name"],
                    "displayName": option["display_name"],
                    "priceDelta": option["price_delta"],
                }
                for option_index, option in enumerate(question["options"], start=1)
            ]
            questions.append(
                {
                    "id": f"{group['group_id']}:Q{question_index}",
                    "sourceQuestionCode": question["question_code"],
                    "name": question["name"],
                    "displayName": question["display_name"],
                    "selectionMode": question["selection_mode"],
                    "required": question["required"],
                    "options": options,
                }
            )
        groups.append(
            {
                "id": group["group_id"],
                "name": group["name"],
                "questions": questions,
            }
        )

    products = [
        {
            "id": product["sku"] or f"P_{product['product_id']}",
            "sourceProductId": product["product_id"],
            "sourceProductCode": product["product_code"],
            "sourceRef": source_product_ref(
                snapshot["menu"]["menu_id"],
                product["sku"] or f"P_{product['product_id']}",
            ),
            "name": product["name"],
            "category": SOURCE_CATEGORY_TO_MAJOR[product["category"]],
            "sourceCategory": product["category"],
            "price": product["base_price"],
            "optionGroupIds": product["option_group_ids"],
        }
        for product in snapshot["products"]
        if product["category"] not in EXCLUDED_SOURCE_CATEGORIES
    ]
    return {
        "schema": "w7tp.quickclick_menu_web.v1",
        "source": {
            "id": snapshot["menu"]["menu_id"],
            "name": snapshot["menu"]["name"],
            "sha256": snapshot["source"]["sha256"],
            "modifiedAt": snapshot["source"]["modified_at"],
            "authorityState": snapshot["authority_state"],
            "sourceProductCount": snapshot["counts"]["products"],
            "activeProductCount": len(products),
            "excludedProductCount": snapshot["counts"]["products"] - len(products),
            "excludedSourceCategories": sorted(EXCLUDED_SOURCE_CATEGORIES),
            "optionGroupCount": snapshot["counts"]["option_groups"],
            "rawOptionRowCount": snapshot["counts"]["raw_option_rows"],
            "normalizedOptionCount": snapshot["counts"]["option_items"],
            "sourceWarningCount": snapshot["counts"]["source_warnings"],
        },
        "adi": {
            "state": "DEMO_FIXED_CANDIDATE_ONLY",
            "productionState": "HOLD_ADI_NOT_CONFIGURED",
            "role": "AI_BOUNDED_PRODUCT_REFERENCE_INDEX",
            "candidateRefs": [product["sourceRef"] for product in products],
            "contractRefs": {
                "strategyRef": "adi-strategy:pos-menu-demo:v1",
                "representationRef": f"quickclick-menu:{snapshot['menu']['menu_id']}@sha256:{snapshot['source']['sha256']}",
                "observationSetRef": f"quickclick-active-products:{len(products)}@sha256:{snapshot['source']['sha256']}",
                "determinismProfileRef": "canonical-source-ref-order:v1",
                "verifierRef": "cafe-pos-browser-product:v1",
                "evidenceRef": f"sha256:{snapshot['source']['sha256']}",
            },
            "publicBoundary": "REF_ONLY",
        },
        "surfaces": {
            "human": {
                "system": "ODOO",
                "state": "ODOO_IMPORT_PREVIEW_ONLY",
                "formalPosState": "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED",
            },
            "ai": {
                "system": "ADI",
                "state": "DEMO_FIXED_CANDIDATE_ONLY",
                "productionState": "HOLD_ADI_NOT_CONFIGURED",
                "llmExecution": "USER_DEVICE_ONLY",
                "serverLlm": False,
            },
            "convergence": {
                "system": "TOTAL_FIELD_RECTIFIER",
                "state": "L3_CANDIDATE_HUMAN_D8_REQUIRED",
            },
        },
        "categories": MAJOR_CATEGORIES,
        "products": products,
        "optionGroups": groups,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--source-title", required=True)
    parser.add_argument("--source-drive-id", required=True)
    parser.add_argument("--source-copy-drive-id", required=True)
    parser.add_argument("--source-modified-at", required=True)
    parser.add_argument("--web-output", type=Path)
    args = parser.parse_args()

    snapshot = build_snapshot(
        args.source,
        args.expected_sha256,
        args.source_title,
        args.source_drive_id,
        args.source_copy_drive_id,
        args.source_modified_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.web_output:
        web_data = build_web_data(snapshot)
        args.web_output.parent.mkdir(parents=True, exist_ok=True)
        args.web_output.write_text(
            "(function () {\n"
            '  "use strict";\n'
            "  window.WUCHANG_QUICKCLICK_MENU = Object.freeze(\n"
            + json.dumps(web_data, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n  );\n"
            "}());\n",
            encoding="utf-8",
        )
    print(json.dumps(snapshot["counts"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
