import json
import hashlib
from pathlib import Path

COMPANY_ID = 3
COMPANY_NAME = "上品食品行"
MENU_ID = "M387676"
POS_NAME = "上品聊國咖啡館 重新總店"
POS_PARAM = "liaoguo.chongxin.pos_config_id"
SOURCE_SHA = "c3f4a31ee60509dc6a75dad64c6c6be4de0089ff1ff5f00695467ae61b34c630"
IDENTITY_SHA = "539f24171492cb8c899c3173aff78af21409c39518de269f24037f595d01376e"
WEB_SHA = "fc91a33da01020dd8beb765db84fe09f30a752e87a80ce024b7787189379b11e"
DATA_ROOT = Path("/mnt/extra-addons/wuchang_ordering_ui_suite/static/src/data")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def hold(condition, code, detail=None):
    if not condition:
        raise RuntimeError(code + (":" + str(detail) if detail is not None else ""))

identity_path = DATA_ROOT / "SOURCE_TO_ODOO_IDENTITY_REVIEW.json"
web_path = DATA_ROOT / "quickclick_web_data.json"
hold(sha(identity_path) == IDENTITY_SHA, "HOLD_IDENTITY_SOURCE_HASH_MISMATCH")
hold(sha(web_path) == WEB_SHA, "HOLD_WEB_SOURCE_HASH_MISMATCH")
identity = json.loads(identity_path.read_text(encoding="utf-8"))
web = json.loads(web_path.read_text(encoding="utf-8"))
hold(web.get("source", {}).get("sha256") == SOURCE_SHA, "HOLD_SOURCE_SNAPSHOT_HASH_MISMATCH")
items = list(identity.get("items") or [])
source_ids = [str(row.get("source_product_id") or "") for row in items]
hold(len(source_ids) == 64 and len(set(source_ids)) == 64 and all(source_ids), "HOLD_QUICKCLICK_64_ID_CONTRACT")
hold(all(isinstance(row.get("source_base_price"), (int, float)) and not isinstance(row.get("source_base_price"), bool) and row.get("source_base_price") >= 0 for row in items), "HOLD_SOURCE_PRICE_INVALID")

web_products = {str(row.get("sourceProductId") or ""): row for row in (web.get("products") or [])}
contradictions = []
for row in items:
    sid = str(row["source_product_id"])
    wp = web_products.get(sid)
    if wp and (
        str(wp.get("name") or "") != str(row.get("source_product_name") or "")
        or float(wp.get("price")) != float(row.get("source_base_price"))
        or str(wp.get("sourceCategory") or "") != str(row.get("source_category") or "")
        or sorted(map(str, wp.get("optionGroupIds") or [])) != sorted(map(str, row.get("source_option_group_ids") or []))
    ):
        contradictions.append(sid)
hold(not contradictions, "HOLD_SOURCE_ITEM_CONTRADICTION", contradictions)

used_group_ids = []
for row in items:
    for code in row.get("source_option_group_ids") or []:
        code = str(code)
        if code not in used_group_ids:
            used_group_ids.append(code)
group_source = {str(row.get("id") or ""): row for row in (web.get("optionGroups") or [])}
hold(len(used_group_ids) == 20 and all(code in group_source for code in used_group_ids), "HOLD_USED_OPTION_GROUP_CONTRACT")
expected_groups = [group_source[code] for code in used_group_ids]
expected_question_count = sum(len(group.get("questions") or []) for group in expected_groups)
expected_item_count = sum(len(question.get("options") or []) for group in expected_groups for question in (group.get("questions") or []))
question_ids = [str(question.get("id") or "") for group in expected_groups for question in (group.get("questions") or [])]
item_ids = [str(item.get("id") or "") for group in expected_groups for question in (group.get("questions") or []) for item in (question.get("options") or [])]
hold(expected_question_count == 42 and len(question_ids) == len(set(question_ids)), "HOLD_OPTION_QUESTION_CONTRACT")
hold(expected_item_count == 201 and len(item_ids) == len(set(item_ids)), "HOLD_OPTION_ITEM_CONTRACT")

company = env["res.company"].sudo().browse(COMPANY_ID).exists()
hold(bool(company) and company.name == COMPANY_NAME, "HOLD_COMPANY_3_IDENTITY")
old_company_names = {row.id: row.name for row in env["res.company"].sudo().browse([1, 3, 5]).exists()}
old_pos = {}
for pos_id in (2, 3):
    pos = env["pos.config"].sudo().browse(pos_id).exists()
    hold(bool(pos), "HOLD_EXISTING_POS_MISSING", pos_id)
    old_pos[pos_id] = {
        "name": pos.name,
        "company_id": pos.company_id.id,
        "active": pos.active,
        "session_count": env["pos.session"].sudo().search_count([("config_id", "=", pos_id)]),
        "order_count": env["pos.order"].sudo().search_count([("config_id", "=", pos_id)]),
        "category_ids": sorted(pos.iface_available_categ_ids.ids),
        "limit_categories": bool(pos.limit_categories),
    }
hold(old_pos[2]["company_id"] == 1 and old_pos[3]["company_id"] == 3, "HOLD_EXISTING_POS_SCOPE_DRIFT")

all_existing_products = env["product.template"].sudo().search([])
preexisting_product_state = {row.id: (row.write_date, row.active, row.company_id.id or None, row.default_code) for row in all_existing_products}
legacy_count = len(all_existing_products)
hold(legacy_count == 107, "HOLD_FORMAL_PRODUCT_COUNT_DRIFT", legacy_count)
hold(env["product.template"].sudo().search_count([("quickclick_product_id", "!=", False)]) == 0, "HOLD_PREEXISTING_QUICKCLICK_MAPPING")

Group = env["wuchang.cafe.option.group"].sudo().with_context(wuchang_option_internal_write=True)
existing_used_groups = env["wuchang.cafe.option.group"].sudo().search([("code", "in", used_group_ids)])
hold(not existing_used_groups, "HOLD_PREEXISTING_OPTION_GROUP_COLLISION", existing_used_groups.mapped("code"))
group_records = {}
for g_index, source_group in enumerate(expected_groups, 1):
    question_commands = []
    for q_index, source_question in enumerate(source_group.get("questions") or [], 1):
        item_commands = []
        for i_index, source_item in enumerate(source_question.get("options") or [], 1):
            delta = source_item.get("priceDelta", 0)
            hold(isinstance(delta, (int, float)) and not isinstance(delta, bool), "HOLD_OPTION_DELTA_INVALID", source_item.get("id"))
            item_commands.append((0, 0, {
                "sequence": i_index * 10,
                "active": True,
                "name": str(source_item.get("name") or source_item.get("displayName") or "").strip(),
                "display_name": str(source_item.get("displayName") or source_item.get("name") or "").strip(),
                "price_delta": float(delta),
                "quickclick_item_code": str(source_item["id"]),
                "quickclick_question_code": str(source_question["id"]),
                "note": "sourceOptionCode=" + str(source_item.get("sourceOptionCode") or "") + "; source_sha256=" + SOURCE_SHA,
            }))
        question_commands.append((0, 0, {
            "sequence": q_index * 10,
            "active": True,
            "name": str(source_question.get("name") or source_question.get("displayName") or "").strip(),
            "display_name": str(source_question.get("displayName") or source_question.get("name") or "").strip(),
            "selection_type": "multiple" if source_question.get("selectionMode") == "multiple" else "single",
            "required": bool(source_question.get("required")),
            "quickclick_question_code": str(source_question["id"]),
            "item_ids": item_commands,
        }))
    group = Group.create({
        "sequence": g_index * 10,
        "active": True,
        "code": str(source_group["id"]),
        "name": str(source_group.get("name") or source_group["id"]).strip(),
        "source": "quickclick",
        "note": "QuickClick menu " + MENU_ID + "; source_sha256=" + SOURCE_SHA,
        "question_ids": question_commands,
    })
    group_records[group.code] = group

hold(len(group_records) == 20, "HOLD_CREATED_OPTION_GROUP_COUNT")
hold(env["wuchang.cafe.option.question"].sudo().search_count([("group_id", "in", [g.id for g in group_records.values()])]) == 42, "HOLD_CREATED_OPTION_QUESTION_COUNT")
hold(env["wuchang.cafe.option.item"].sudo().search_count([("question_id.group_id", "in", [g.id for g in group_records.values()])]) == 201, "HOLD_CREATED_OPTION_ITEM_COUNT")

PosCategory = env["pos.category"].sudo()
parent_candidates = PosCategory.search([("name", "=", "重新總店 QuickClick"), ("parent_id", "=", False)])
hold(len(parent_candidates) <= 1, "HOLD_POS_CATEGORY_PARENT_DUPLICATE")
parent_category = parent_candidates or PosCategory.create({"name": "重新總店 QuickClick"})
category_names = []
for row in items:
    name = str(row.get("source_category") or "").strip()
    hold(bool(name), "HOLD_SOURCE_CATEGORY_MISSING", row.get("source_product_id"))
    if name not in category_names:
        category_names.append(name)
hold(len(category_names) == 8, "HOLD_SOURCE_CATEGORY_COUNT", category_names)
category_records = {}
for sequence, name in enumerate(category_names, 1):
    found = PosCategory.search([("name", "=", name), ("parent_id", "=", parent_category.id)])
    hold(len(found) <= 1, "HOLD_POS_CATEGORY_DUPLICATE", name)
    category_records[name] = found or PosCategory.create({"name": name, "parent_id": parent_category.id, "sequence": sequence * 10})

financial_before = {
    "journals": env["account.journal"].sudo().search_count([("company_id", "=", COMPANY_ID)]),
    "payment_methods": env["pos.payment.method"].sudo().search_count([("company_id", "=", COMPANY_ID)]),
    "picking_types": env["stock.picking.type"].sudo().search_count([("company_id", "=", COMPANY_ID)]),
}
pos_matches = env["pos.config"].sudo().search([("company_id", "=", COMPANY_ID), ("name", "=", POS_NAME)])
hold(len(pos_matches) <= 1, "HOLD_TARGET_POS_DUPLICATE")
created_pos = not bool(pos_matches)
target_pos = pos_matches or env["pos.config"].sudo().with_company(company).create({"name": POS_NAME, "company_id": COMPANY_ID})
target_pos.sudo().write({
    "limit_categories": True,
    "iface_available_categ_ids": [(6, 0, [category_records[name].id for name in category_names])],
})
financial_after = {
    "journals": env["account.journal"].sudo().search_count([("company_id", "=", COMPANY_ID)]),
    "payment_methods": env["pos.payment.method"].sudo().search_count([("company_id", "=", COMPANY_ID)]),
    "picking_types": env["stock.picking.type"].sudo().search_count([("company_id", "=", COMPANY_ID)]),
}
hold(financial_before == financial_after, "HOLD_UNAUTHORIZED_FINANCIAL_SIDE_EFFECT", {"before": financial_before, "after": financial_after})
hold(bool(target_pos.picking_type_id and target_pos.journal_id and target_pos.payment_method_ids), "HOLD_TARGET_POS_DEFAULT_FINANCE_BINDING_MISSING")

Product = env["product.template"].sudo().with_context(wuchang_menu_internal_write=True).with_company(company)
existing_target_products = env["product.template"].sudo().search([("company_id", "=", COMPANY_ID), ("quickclick_menu_id", "=", MENU_ID)])
hold(not existing_target_products, "HOLD_PREEXISTING_TARGET_MENU_PARTIAL", len(existing_target_products))
product_values = []
for row in items:
    sid = str(row["source_product_id"])
    group_ids = [str(code) for code in (row.get("source_option_group_ids") or [])]
    hold(len(group_ids) <= 1, "HOLD_MULTI_OPTION_GROUP_UNSUPPORTED", sid)
    group = group_records[group_ids[0]] if group_ids else False
    web_row = web_products.get(sid) or {}
    category_name = str(row["source_category"])
    product_values.append({
        "name": str(row["source_product_name"]).strip(),
        "list_price": float(row["source_base_price"]),
        "type": "consu",
        "sale_ok": True,
        "purchase_ok": False,
        "available_in_pos": True,
        "active": True,
        "company_id": COMPANY_ID,
        "default_code": "CHX-QC-" + sid,
        "quickclick_menu_id": MENU_ID,
        "quickclick_product_id": sid,
        "quickclick_product_code": str(web_row.get("sourceProductCode") or "") or False,
        "quickclick_sku": "P_" + sid,
        "quickclick_option_group_code": group_ids[0] if group_ids else False,
        "quickclick_raw_category": category_name,
        "quickclick_raw_price": float(row["source_base_price"]),
        "normalized_price_basis": "QUICKCLICK_SOURCE_BASE_PRICE",
        "normalized_price_note": "source_sha256=" + SOURCE_SHA,
        "wuchang_option_group_id": group.id if group else False,
        "pos_categ_ids": [(6, 0, [category_records[category_name].id])],
    })
created_products = Product.create(product_values)
hold(len(created_products) == 64, "HOLD_CREATED_PRODUCT_COUNT")

param = env["ir.config_parameter"].sudo()
existing_pos_param = param.get_param(POS_PARAM, "")
hold(not existing_pos_param or str(existing_pos_param) == str(target_pos.id), "HOLD_POS_PARAMETER_CONFLICT", existing_pos_param)
param.set_param(POS_PARAM, str(target_pos.id))

formal_products = env["product.template"].sudo().search([("company_id", "=", COMPANY_ID), ("quickclick_menu_id", "=", MENU_ID)])
hold(len(formal_products) == 64, "HOLD_FORMAL_TARGET_PRODUCT_COUNT", len(formal_products))
by_source = {}
for product in formal_products:
    by_source.setdefault(str(product.quickclick_product_id or ""), []).append(product)
hold(set(by_source) == set(source_ids) and all(len(rows) == 1 for rows in by_source.values()), "HOLD_FORMAL_TARGET_SOURCE_ID_UNIQUENESS")
for row in items:
    sid = str(row["source_product_id"])
    product = by_source[sid][0]
    expected_group = (row.get("source_option_group_ids") or [False])[0]
    hold(product.name == str(row["source_product_name"]).strip(), "HOLD_FORMAL_NAME_MISMATCH", sid)
    hold(float(product.list_price) == float(row["source_base_price"]), "HOLD_FORMAL_PRICE_MISMATCH", sid)
    hold(product.default_code == "CHX-QC-" + sid, "HOLD_FORMAL_DEFAULT_CODE_MISMATCH", sid)
    hold((product.quickclick_option_group_code or False) == expected_group, "HOLD_FORMAL_OPTION_GROUP_MISMATCH", sid)
    hold(product.company_id.id == COMPANY_ID and product.available_in_pos and product.active, "HOLD_FORMAL_PRODUCT_SCOPE_MISMATCH", sid)
    hold(product.product_variant_count == 1 and not product.attribute_line_ids, "HOLD_PRODUCT_VARIANT_GENERATED", sid)

for product_id, state in preexisting_product_state.items():
    product = env["product.template"].sudo().browse(product_id).exists()
    hold(bool(product), "HOLD_LEGACY_PRODUCT_REMOVED", product_id)
    now_state = (product.write_date, product.active, product.company_id.id or None, product.default_code)
    hold(now_state == state, "HOLD_LEGACY_PRODUCT_CHANGED", product_id)

for company_id, name in old_company_names.items():
    hold(env["res.company"].sudo().browse(company_id).name == name, "HOLD_COMPANY_CHANGED", company_id)
for pos_id, state in old_pos.items():
    pos = env["pos.config"].sudo().browse(pos_id)
    now_state = {
        "name": pos.name,
        "company_id": pos.company_id.id,
        "active": pos.active,
        "session_count": env["pos.session"].sudo().search_count([("config_id", "=", pos_id)]),
        "order_count": env["pos.order"].sudo().search_count([("config_id", "=", pos_id)]),
        "category_ids": sorted(pos.iface_available_categ_ids.ids),
        "limit_categories": bool(pos.limit_categories),
    }
    hold(now_state == state, "HOLD_EXISTING_POS_CHANGED", {"pos_id": pos_id, "before": state, "after": now_state})

hold(not set(target_pos.iface_available_categ_ids.ids) & set(env["pos.config"].sudo().browse(3).iface_available_categ_ids.ids), "HOLD_POS3_CATEGORY_SCOPE_OVERLAP")
result = {
    "state": "PASS_FORMAL_MENU_APPLY",
    "company_id": COMPANY_ID,
    "pos_config_id": target_pos.id,
    "pos_config_created": created_pos,
    "pos_config_name": target_pos.name,
    "pos_category_parent_id": parent_category.id,
    "source_category_count": len(category_records),
    "product_count": len(formal_products),
    "unique_source_id_count": len(by_source),
    "option_group_count": len(group_records),
    "option_question_count": expected_question_count,
    "option_item_count": expected_item_count,
    "product_variant_attribute_line_count": sum(len(product.attribute_line_ids) for product in formal_products),
    "legacy_product_count_unchanged": legacy_count,
    "financial_objects_before": financial_before,
    "financial_objects_after": financial_after,
    "source_sha256": SOURCE_SHA,
    "source_warning_count": int(web.get("source", {}).get("sourceWarningCount") or 0),
    "source_warning_treatment": "normalized unique question/item IDs preserved; no invented prices",
    "pos2_unchanged": True,
    "pos3_unchanged": True,
    "company1_company5_unchanged": True,
}
env.cr.commit()
print("WUC7_RESULT=" + json.dumps(result, ensure_ascii=False, sort_keys=True))
