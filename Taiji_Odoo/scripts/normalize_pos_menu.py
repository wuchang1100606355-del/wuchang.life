import csv
import json
import re
from html import unescape
from pathlib import Path

BASE = Path("import")
MENU = BASE / "quickclick_menu_raw.tsv"
GROUPS = BASE / "quickclick_option_groups.tsv"
ITEMS = BASE / "quickclick_option_items.tsv"
OUT_JSON = BASE / "wuchang_pos_menu_normalized.json"
OUT_PRODUCTS = BASE / "wuchang_pos_products_normalized.tsv"
OUT_OPTIONS = BASE / "wuchang_pos_options_normalized.tsv"
OUT_REPORT = BASE / "wuchang_pos_cleaning_report.tsv"

required = [MENU, GROUPS, ITEMS]
missing = [str(p) for p in required if not p.exists()]
if missing:
    raise SystemExit("缺少必要檔案：\n" + "\n".join(missing))

DATE_STATE = "20260509-ACTIVE"

DRINK_CATEGORIES = {"義式咖啡", "茶", "無咖啡因"}
MEAL_CATEGORY = "聊國簡餐"
BEAN_CATEGORY = "咖啡豆"

MEAL_GROUPS = {"O7835329", "O8701672"}
MEAL_OVERRIDE_GROUP = "WC_MEAL_DRINK_SIMPLE"
BEAN_445_870_GROUP = "WC_BEAN_445_870"
BEAN_445_870_NAMES = {"耶加雪夫", "肯亞AA"}

def read_tsv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))

def write_tsv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        w.writerows(rows)

def clean_html(s):
    s = s or ""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p\s*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = unescape(s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def to_float(v):
    v = (v or "").strip()
    if not v:
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0

def safe_code(s):
    s = str(s or "").strip()
    s = re.sub(r"\s+", "-", s)
    return s

menu_rows = read_tsv(MENU)
group_rows = read_tsv(GROUPS)
item_rows = read_tsv(ITEMS)

group_map = {
    (r.get("題型選項組合編號") or "").strip(): (r.get("題型選項組合名稱") or "").strip()
    for r in group_rows
    if (r.get("題型選項組合編號") or "").strip()
}

groups = {}
questions = {}
items = []
report = []
products = []

def ensure_group(code, name, note=""):
    if code not in groups:
        groups[code] = {
            "code": code,
            "name": name or code,
            "note": note,
            "w5c_code": f"W5C:CAFE:OPTION_GROUP:{safe_code(code)}:{DATE_STATE}:STAFF",
        }
    return groups[code]

def add_item(group_code, group_name, question_name, selection_type, required,
             item_name, display_name, price_delta, child_group_code="",
             item_code="", question_code="", note=""):
    ensure_group(group_code, group_name)
    q_key = (group_code, question_code or question_name, question_name)
    if q_key not in questions:
        questions[q_key] = {
            "group_code": group_code,
            "name": question_name,
            "display_name": question_name,
            "selection_type": selection_type or "single",
            "required": bool(required),
            "quickclick_question_code": question_code or "",
            "w5c_code": f"W5C:CAFE:OPTION_QUESTION:{safe_code(group_code)}.{safe_code(question_name)}:{DATE_STATE}:STAFF",
        }
    i_key = (group_code, question_code or question_name, question_name, display_name or item_name, float(price_delta))
    if i_key in {(x["group_code"], x["quickclick_question_code"] or x["question_name"], x["question_name"], x["display_name"], x["price_delta"]) for x in items}:
        return
    items.append({
        "group_code": group_code,
        "question_name": question_name,
        "name": item_name,
        "display_name": display_name or item_name,
        "price_delta": float(price_delta),
        "child_group_code": child_group_code or "",
        "quickclick_item_code": item_code or "",
        "quickclick_question_code": question_code or "",
        "note": note,
        "w5c_code": f"W5C:CAFE:OPTION_ITEM:{safe_code(group_code)}.{safe_code(question_name)}.{safe_code(display_name or item_name)}:{DATE_STATE}:STAFF",
    })

# 原始選項
for r in item_rows:
    g = (r.get("題型選項組合編號") or "").strip()
    if not g:
        continue

    # 簡餐巢狀飲品不吃原資料，後面用覆蓋規則重建
    if g in MEAL_GROUPS:
        continue

    q = (r.get("加購題型顯示名稱") or r.get("加購題型") or "").strip()
    if not q:
        q = "選項"

    single_multi = (r.get("選項題型(單/雙)") or "單").strip()
    selection_type = "multiple" if "雙" in single_multi or "多" in single_multi else "single"
    required = (r.get("是否必填(Y/N)") or "Y").strip().upper() == "Y"
    item_name = (r.get("加購選項") or "").strip()
    display_name = (r.get("加購選項顯示名稱") or item_name).strip()
    price_delta = to_float(r.get("加購選項價格"))
    child_group_code = (r.get("子選單菜單編號") or "").strip()
    item_code = (r.get("加購選項代碼") or "").strip()
    question_code = (r.get("加購題型代碼") or "").strip()

    add_item(
        g, group_map.get(g, g), q, selection_type, required,
        item_name, display_name, price_delta,
        child_group_code=child_group_code,
        item_code=item_code,
        question_code=question_code,
        note="raw_quickclick"
    )

# 簡餐覆蓋
ensure_group(MEAL_OVERRIDE_GROUP, "簡餐飲品標準單層選項", "原始簡餐巢狀飲品刪除，只保留四項")
for name, delta in [
    ("更改飲品", -20),
    ("錫蘭紅茶", 0),
    ("茉香綠茶", 0),
    ("伯爵紅茶", 5),
]:
    add_item(
        MEAL_OVERRIDE_GROUP, "簡餐飲品標準單層選項",
        "加購飲品", "single", True,
        name, name, delta,
        child_group_code="",
        item_code="",
        question_code="WC_MEAL_DRINK",
        note="meal_drink_override"
    )

# 精品豆 445/870 覆蓋
ensure_group(BEAN_445_870_GROUP, "精品豆半磅445一磅870", "耶加雪夫與肯亞AA咖啡豆專用")
for name, delta in [("半磅", 0), ("一磅", 425)]:
    add_item(
        BEAN_445_870_GROUP, "精品豆半磅445一磅870",
        "磅數", "single", True,
        name, name, delta,
        child_group_code="",
        item_code="",
        question_code="WC_BEAN_SIZE",
        note="bean_445_870_override"
    )

for r in menu_rows:
    menu_id = (r.get("主商品菜單編號") or "").strip()
    product_id = (r.get("主商品編號") or "").strip()
    raw_category = (r.get("主商品類別") or "").strip()
    raw_name = (r.get("主商品名稱") or "").strip()
    raw_price = to_float(r.get("主商品價格"))
    desc = clean_html(r.get("主商品描述"))
    image_url = (r.get("主商品圖片") or "").strip()
    product_code = (r.get("主商品代碼") or "").strip()
    sku = (r.get("主商品料號") or "").strip()
    original_group = (r.get("套用加購選單") or "").strip()

    display_name = raw_name
    option_group_code = original_group
    price_basis = "BASE"
    note = []

    if raw_category in DRINK_CATEGORIES:
        price_basis = "M"
        note.append("飲品以M中杯為基準價")

    if raw_category == BEAN_CATEGORY:
        price_basis = "HALF_POUND"
        note.append("咖啡豆以半磅為基準價")
        if raw_name in BEAN_445_870_NAMES:
            display_name = f"{raw_name}（豆）"
            option_group_code = BEAN_445_870_GROUP
            note.append("強制套用445/870咖啡豆覆蓋規則")
        elif original_group == "O8640678":
            note.append("警告：咖啡豆誤套手沖溫控，已移除原題型")
            option_group_code = ""

    if raw_category == MEAL_CATEGORY:
        price_basis = "MEAL_BASE"
        if original_group in MEAL_GROUPS:
            option_group_code = MEAL_OVERRIDE_GROUP
            note.append("簡餐飲品巢狀刪除，套用四項單層飲品")

    if not original_group:
        note.append("無加購選單")

    product_w5c = f"W5C:CAFE:PRODUCT:{safe_code(sku or product_id)}:{DATE_STATE}:PUBLIC"

    products.append({
        "quickclick_menu_id": menu_id,
        "quickclick_product_id": product_id,
        "quickclick_product_code": product_code,
        "quickclick_sku": sku,
        "raw_category": raw_category,
        "pos_category": raw_category,
        "raw_name": raw_name,
        "display_name": display_name,
        "raw_price": raw_price,
        "list_price": raw_price,
        "price_basis": price_basis,
        "original_option_group_code": original_group,
        "option_group_code": option_group_code,
        "description_sale": desc,
        "image_url": image_url,
        "w5c_code": product_w5c,
        "note": "；".join(note),
    })

    report.append({
        "quickclick_product_id": product_id,
        "raw_category": raw_category,
        "raw_name": raw_name,
        "display_name": display_name,
        "raw_price": raw_price,
        "list_price": raw_price,
        "price_basis": price_basis,
        "original_option_group_code": original_group,
        "final_option_group_code": option_group_code,
        "note": "；".join(note),
    })

data = {
    "groups": list(groups.values()),
    "questions": list(questions.values()),
    "items": items,
    "products": products,
}

OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

write_tsv(OUT_PRODUCTS, products, list(products[0].keys()) if products else [])
write_tsv(OUT_OPTIONS, items, list(items[0].keys()) if items else [])
write_tsv(OUT_REPORT, report, list(report[0].keys()) if report else [])

print("NORMALIZE_DONE")
print(f"products={len(products)}")
print(f"groups={len(groups)}")
print(f"questions={len(questions)}")
print(f"items={len(items)}")
print(f"json={OUT_JSON}")
print(f"report={OUT_REPORT}")
