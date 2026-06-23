#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path("/home/taiji_admin/Taiji_Hub")
BASELINE_SANDBOX = ROOT / "runtime/sandbox/pos_mvp_autodev"
RUN_DIR = Path(os.environ.get("POS_MVP_RUN_DIR", str(ROOT / "runtime/sandbox/pos_mvp_autodev_run")))
MENU_JSON = BASELINE_SANDBOX / "menu/menu.json"
PHOTO_DIR = BASELINE_SANDBOX / "menu/product_photos"
PHOTO_MANIFEST = BASELINE_SANDBOX / "menu/product_photos_manifest.json"
PHOTOBOOK_SPEC = BASELINE_SANDBOX / "menu/product_photobook_spec.json"
PHOTO_PROMPTS_JSON = BASELINE_SANDBOX / "menu/product_photo_ai_prompts.json"
PHOTO_PROMPTS_MD = BASELINE_SANDBOX / "menu/product_photo_ai_prompts.md"
GEMINI_SINGLE_PROMPT_MD = BASELINE_SANDBOX / "menu/gemini_single_product_prompt.md"
ORDER_CANDIDATES = RUN_DIR / "orders/order_candidates.jsonl"
CONFIRMED_ORDERS = RUN_DIR / "orders/confirmed_orders.jsonl"
EVENTS = RUN_DIR / "events/spacetime_events.jsonl"
DEAD_LETTER = RUN_DIR / "dead_letter/dead_letter_queue.jsonl"

BREAKFAST_XML = ROOT / "Taiji_Odoo/addons/wuchang_core/data/breakfast_pos_menu.xml"
PRODUCT_XML = ROOT / "Taiji_Odoo/addons/wuchang_core/data/menu_setup.xml"
ROUTER = ROOT / "runtime/gt8d_lookup/gt8d_route_resolver.py"

SAFETY_FLAGS = {
    "SECRET_READ": False,
    "MEMBER_PLAINTEXT_READ": False,
    "DB_WRITE": False,
    "SERVICE_RESTART": False,
    "DEPLOY": False,
    "ODOO_CORE_MUTATION": False,
    "PRODUCTION_LINE_ACTION": False,
    "PRODUCTION_GOOGLE_ACTION": False,
}

MAX_QUEUE_ITEMS = 200
MAX_RETRY_COUNT = 2


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_hash(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ensure_dirs() -> None:
    for path in [ORDER_CANDIDATES.parent, CONFIRMED_ORDERS.parent, EVENTS.parent, DEAD_LETTER.parent]:
        path.mkdir(parents=True, exist_ok=True)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict) -> None:
    rows = read_jsonl(path)
    if len(rows) >= MAX_QUEUE_ITEMS:
        append_dead_letter("queue_full", {"target": str(path), "max_queue_items": MAX_QUEUE_ITEMS})
        raise SystemExit(f"queue full: {path}")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def reset_runtime_files() -> None:
    ensure_dirs()
    for path in [ORDER_CANDIDATES, CONFIRMED_ORDERS, EVENTS, DEAD_LETTER]:
        path.write_text("", encoding="utf-8")


def field_text(record: ET.Element, name: str) -> str:
    for field in record.findall("field"):
        if field.attrib.get("name") == name:
            return (field.text or "").strip()
    return ""


def field_ref(record: ET.Element, name: str) -> str:
    for field in record.findall("field"):
        if field.attrib.get("name") == name:
            return (field.attrib.get("ref") or "").strip()
    return ""


def parse_wuchang_menu_items() -> list[dict]:
    tree = ET.parse(BREAKFAST_XML)
    items = []
    for record in tree.findall(".//record[@model='wuchang.menu.item']"):
        code = field_text(record, "code")
        name = field_text(record, "name")
        price = float(field_text(record, "base_price") or 0)
        category = field_text(record, "category")
        if not code or not name:
            continue
        items.append({
            "code": code,
            "name": name,
            "category": category,
            "price": price,
            "currency": "TWD",
            "photo_ref": None,
            "photo_status": "PHOTO_REQUIRED_NOT_ATTACHED",
            "source_model": "wuchang.menu.item",
            "source_file": str(BREAKFAST_XML.relative_to(ROOT)),
            "available_in_pos": True,
        })
    return items


def parse_product_templates() -> list[dict]:
    tree = ET.parse(PRODUCT_XML)
    category_by_xml_id = {}
    for record in tree.findall(".//record[@model='product.category']"):
        xml_id = record.attrib.get("id") or ""
        name = field_text(record, "name")
        if xml_id and name:
            category_by_xml_id[f"wuchang_core.{xml_id}"] = name
            category_by_xml_id[xml_id] = name

    items = []
    for record in tree.findall(".//record[@model='product.template']"):
        xml_id = record.attrib.get("id") or ""
        name = field_text(record, "name")
        price = float(field_text(record, "list_price") or 0)
        available = field_text(record, "available_in_pos") == "True"
        category = category_by_xml_id.get(field_ref(record, "categ_id"), "未分類")
        if not xml_id or not name or not available:
            continue
        items.append({
            "code": f"ODOO_{xml_id.upper()}",
            "name": name,
            "category": category,
            "price": price,
            "currency": "TWD",
            "photo_ref": None,
            "photo_status": "PHOTO_REQUIRED_NOT_ATTACHED",
            "source_model": "product.template",
            "source_file": str(PRODUCT_XML.relative_to(ROOT)),
            "available_in_pos": True,
        })
    return items


def load_photo_manifest() -> dict:
    if not PHOTO_MANIFEST.exists():
        return {
            "schema": "w7tp_pos_product_photo_manifest.v1",
            "state": "LOCAL_PRODUCT_PHOTO_MANIFEST_EMPTY",
            "authority": "taiji01_total_field_local_files",
            "photo_quality_tier_required": "PHOTOBOOK_PRODUCT_GRADE",
            "external_photo_fetch": False,
            "generated_photo_allowed": False,
            "items": {},
        }
    return json.loads(PHOTO_MANIFEST.read_text(encoding="utf-8"))


def write_empty_photo_manifest() -> None:
    if PHOTO_MANIFEST.exists():
        manifest = load_photo_manifest()
    else:
        manifest = load_photo_manifest()
        PHOTO_MANIFEST.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if not PHOTOBOOK_SPEC.exists():
        PHOTOBOOK_SPEC.write_text(
            json.dumps(build_photobook_spec(manifest), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def build_photobook_spec(manifest: dict) -> dict:
    return {
        "schema": "w7tp_pos_product_photobook_spec.v1",
        "state": "PHOTOBOOK_PRODUCT_GRADE_REQUIRED",
        "authority": "taiji01_total_field_local_files",
        "photo_quality_tier": "PHOTOBOOK_PRODUCT_GRADE",
        "external_photo_fetch": False,
        "generated_photo_allowed_as_product_evidence": False,
        "minimum_long_edge_px": 1800,
        "preferred_aspect_ratios": ["4:5", "1:1", "16:9"],
        "required_shot_types": [
            "hero_product",
            "menu_grid_thumbnail",
            "detail_texture",
            "serving_context",
        ],
        "required_metadata_per_photo": [
            "item_code",
            "local_file",
            "sha256",
            "shot_type",
            "quality_tier",
            "evidence_label",
        ],
        "allowed_evidence_labels": [
            "LOCAL_REAL_PRODUCT_PHOTO",
            "STAFF_APPROVED_PRODUCT_PHOTO",
        ],
        "forbidden_evidence_labels": [
            "GENERATED_IMAGE",
            "STOCK_IMAGE",
            "WEB_SCRAPED_IMAGE",
            "UNKNOWN_SOURCE_IMAGE",
        ],
        "current_manifest_state": manifest.get("state"),
    }


def item_visual_context(item: dict) -> dict:
    category = item["category"]
    name = item["name"]
    if "咖啡" in category or "咖啡" in name or name in {"拿鐵", "美式咖啡", "卡布奇諾", "摩卡", "馥芮白"}:
        return {
            "subject_detail": "咖啡杯、細緻奶泡或咖啡 crema、少量咖啡豆點綴",
        }
    if "飲料" in category or name in {"紅茶", "綠茶", "豆漿"}:
        return {
            "subject_detail": "透明杯或簡潔杯具、飲品色澤清楚、可見冰塊或茶湯層次、冷凝水細節",
        }
    if "套餐" in category or "餐" in category or "早餐" in category:
        return {
            "subject_detail": "白色餐盤、餐具、少量配菜、食物熱度與層次清楚",
        }
    if "燒烤" in category:
        return {
            "subject_detail": "深色陶盤或鐵盤、炭烤紋理、油亮表面、少量蔥花或香料",
        }
    return {
        "subject_detail": "簡潔餐具與店內氛圍道具、產品輪廓清楚",
    }


def build_product_photo_prompts(menu: dict) -> dict:
    style_lock = {
        "style_id": "LIAOGUO_PHOTOBOOK_STANDBY_STYLE_V1",
        "camera": "85mm lens look, commercial food photography, shallow depth of field, crisp product edge",
        "lighting": "single large softbox from upper left plus subtle warm fill, consistent soft shadow direction",
        "background": "matte warm gray stone tabletop, soft dark cafe background, no visible brand logo",
        "palette": "warm neutral cafe palette, cream highlights, charcoal shadow, restrained amber accent",
        "composition": "consistent product scale and clean negative space for menu layout; shot angle may vary by item and shot type",
        "allowed_angle_variation": [
            "front_45_degree",
            "top_down_30_degree",
            "macro_detail_low_angle",
            "menu_grid_centered",
        ],
        "rendering": "photorealistic, high resolution, natural texture, product photobook editorial consistency",
        "aspect_ratio_lock": {
            "hero_product": "4:5",
            "menu_grid_thumbnail": "1:1",
            "detail_texture": "16:9",
            "serving_context": "16:9",
        },
        "consistency_rule": "Keep lighting system, background material, color palette, lens language, shadow softness, product scale, and editorial finish consistent across all menu items; the shot angle may vary by item and shot type.",
    }
    style_lock_text = (
        f"固定風格鎖 {style_lock['style_id']}：{style_lock['camera']}；{style_lock['lighting']}；"
        f"{style_lock['background']}；{style_lock['palette']}；{style_lock['composition']}；"
        f"{style_lock['rendering']}；一致性規則：{style_lock['consistency_rule']}"
    )
    prompts = []
    negative = (
        "不要出現錯字、不要出現品牌商標、不要出現 QR code、不要出現人臉、"
        "不要出現多餘文字、不要塑膠假食物質感、不要過度卡通化、不要低解析、"
        "不要把 AI 圖說成真實實拍、不要改變攝影棚背景、不要改變光線方向、"
        "不要改變鏡頭語彙、不要改變色彩基調、不要讓不同品項看起來像不同系列；允許依 shot type 變換角度"
    )
    for item in menu["items"]:
        context = item_visual_context(item)
        base = (
            f"上品聊國重新總店菜單品項「{item['name']}」，類別「{item['category']}」，"
            f"價格 TWD {item['price']:.0f}。產品寫真集等級商業攝影。{style_lock_text}。"
            f"本品項主體細節：{context['subject_detail']}。"
        )
        prompts.append({
            "item_code": item["code"],
            "item_name": item["name"],
            "category": item["category"],
            "price": item["price"],
            "source_model": item["source_model"],
            "style_id": style_lock["style_id"],
            "style_consistency_required": True,
            "angle_variation_allowed": True,
            "allowed_angle_variation": style_lock["allowed_angle_variation"],
            "quality_tier": "PHOTOBOOK_PRODUCT_GRADE",
            "evidence_label": "AI_IMAGE_PROMPT_CANDIDATE_NOT_PRODUCT_EVIDENCE",
            "google_manual_generation": True,
            "prompts": {
                "hero_product": base + " 構圖：45 度正面英雄角度，單一主產品佔畫面 70%，背景乾淨，4:5 直幅，必須保持同系列風格。",
                "menu_grid_thumbnail": base + " 構圖：近似俯視 30 度或置中角度、留白清楚、適合菜單格狀縮圖，1:1 正方形，必須保持同系列風格。",
                "detail_texture": base + " 構圖：低角度或微距特寫，強調表面質地、溫度、層次與新鮮感，16:9 橫幅，必須保持同系列風格。",
                "serving_context": base + " 構圖：可用斜側角度呈現店內桌面待機畫面氛圍，小J 主播可在旁邊同框但不可遮住商品，16:9 橫幅，必須保持同系列風格。",
            },
            "negative_prompt": negative,
        })
    return {
        "schema": "w7tp_pos_product_photo_ai_prompt_pack.v1",
        "state": "PHOTOBOOK_PRODUCT_GRADE_AI_PROMPT_CANDIDATES",
        "authority": "taiji01_total_field_menu_to_prompt",
        "generated_at": utc_now(),
        "source_menu_hash": menu["menu_hash"],
        "source_menu_state": menu["state"],
        "style_lock": style_lock,
        "same_style_different_items_required": True,
        "angle_variation_allowed": True,
        "item_count": len(prompts),
        "google_account_action": "USER_MANUAL_ONLY",
        "google_account_read": False,
        "google_api_call": False,
        "external_photo_fetch": False,
        "generated_image_is_product_evidence": False,
        "staff_approval_required_before_market_use": True,
        "prompts": prompts,
    }


def write_product_photo_prompts(menu: dict) -> dict:
    payload = build_product_photo_prompts(menu)
    PHOTO_PROMPTS_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# POS Product Photo AI Prompt Pack",
        "",
        "STATE=PHOTOBOOK_PRODUCT_GRADE_AI_PROMPT_CANDIDATES",
        "GOOGLE_ACCOUNT_ACTION=USER_MANUAL_ONLY",
        "GOOGLE_API_CALL=FALSE",
        "GENERATED_IMAGE_IS_PRODUCT_EVIDENCE=FALSE",
        "STAFF_APPROVAL_REQUIRED_BEFORE_MARKET_USE=TRUE",
        "SAME_STYLE_DIFFERENT_ITEMS_REQUIRED=TRUE",
        "ANGLE_VARIATION_ALLOWED=TRUE",
        "",
        "## Global Style Lock",
        "",
        payload["style_lock"]["style_id"],
        "",
        payload["style_lock"]["consistency_rule"],
        "",
    ]
    for prompt in payload["prompts"]:
        lines.extend([
            f"## {prompt['item_name']} / {prompt['item_code']}",
            "",
            f"category: {prompt['category']}",
            f"price: TWD {prompt['price']:.0f}",
            f"quality_tier: {prompt['quality_tier']}",
            f"style_id: {prompt['style_id']}",
            "style_consistency_required: TRUE",
            "",
        ])
        for shot_type, text in prompt["prompts"].items():
            lines.extend([f"### {shot_type}", "", text, ""])
        lines.extend(["### negative_prompt", "", prompt["negative_prompt"], ""])
    PHOTO_PROMPTS_MD.write_text("\n".join(lines), encoding="utf-8")
    write_gemini_single_product_prompt(menu, payload["style_lock"])
    return payload


def write_gemini_single_product_prompt(menu: dict, style_lock: dict) -> None:
    menu_lines = [
        f"- {item['name']} / {item['code']} / {item['category']} / TWD {item['price']:.0f}"
        for item in menu["items"]
    ]
    text = f"""# Gemini Single Product Prompt

STATE=GEMINI_SINGLE_PRODUCT_PROMPT_READY
STYLE_ID={style_lock['style_id']}
SAME_STYLE_DIFFERENT_ITEMS_REQUIRED=TRUE
ANGLE_VARIATION_ALLOWED=TRUE
GOOGLE_ACCOUNT_ACTION=USER_MANUAL_ONLY
GOOGLE_API_CALL=FALSE
GENERATED_IMAGE_IS_PRODUCT_EVIDENCE=FALSE

## 使用方式

把下面整段貼給 Gemini。每次只改 `品名`、`shot_type`、`角度` 三欄，一次只生成一張。

## 單張出圖提示語

```text
請依照固定風格鎖生成一張上品聊國重新總店產品寫真集等級圖片。

品名：{{請填品名}}
shot_type：hero_product
角度：front_45_degree

固定風格鎖：
STYLE_ID={style_lock['style_id']}
{style_lock['camera']}
{style_lock['lighting']}
{style_lock['background']}
{style_lock['palette']}
{style_lock['composition']}
{style_lock['rendering']}

一致性規則：
{style_lock['consistency_rule']}

角度可選：
- front_45_degree：45 度正面英雄角，適合主產品圖
- top_down_30_degree：近似俯視 30 度，適合菜單格狀縮圖
- macro_detail_low_angle：低角度或微距特寫，適合質地細節
- menu_grid_centered：置中留白，適合待機菜單牆

輸出要求：
- 產品寫真集等級，PHOTOBOOK_PRODUCT_GRADE
- 同一系列視覺，不可改變攝影棚背景、光線方向、色彩基調、鏡頭語彙
- 可依品項與 shot_type 變換角度
- 不要出現文字、Logo、QR code、人臉、錯字
- 不要低解析、不要塑膠假食物質感、不要過度卡通化
- 生成圖只是候選素材，不得宣稱為真實實拍
```

## 可用真實菜單品名

{chr(10).join(menu_lines)}
"""
    GEMINI_SINGLE_PROMPT_MD.write_text(text, encoding="utf-8")


def attach_product_photos(items: list[dict]) -> list[dict]:
    manifest = load_photo_manifest()
    refs = manifest.get("items", {})
    for item in items:
        ref = refs.get(item["code"])
        if not ref:
            continue
        if isinstance(ref, dict):
            local_file = ref.get("local_file") or ""
        else:
            local_file = str(ref)
            ref = {
                "local_file": local_file,
                "quality_tier": "UNSPECIFIED",
                "shot_type": "UNSPECIFIED",
                "evidence_label": "UNKNOWN_SOURCE_IMAGE",
            }
        path = PHOTO_DIR / local_file
        if path.exists() and path.is_file():
            item["photo_ref"] = str(path.relative_to(ROOT))
            item["photo_status"] = "LOCAL_PRODUCT_PHOTO_ATTACHED"
            item["photo_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            item["photo_quality_tier"] = ref.get("quality_tier")
            item["photo_shot_type"] = ref.get("shot_type")
            item["photo_evidence_label"] = ref.get("evidence_label")
        else:
            item["photo_ref"] = None
            item["photo_status"] = "PHOTO_MANIFEST_REF_MISSING_FILE"
            item["photo_quality_tier"] = "PHOTOBOOK_PRODUCT_GRADE_REQUIRED"
            item["photo_shot_type"] = "REQUIRED_NOT_ATTACHED"
            item["photo_evidence_label"] = "INFO_REQUIRED"
    return items


def build_menu() -> dict:
    write_empty_photo_manifest()
    raw_items = parse_wuchang_menu_items() + parse_product_templates()
    seen = set()
    items = []
    for item in raw_items:
        key = item["code"]
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    items = attach_product_photos(items)
    categories = sorted({item["category"] for item in items})
    attached_photo_count = sum(1 for item in items if item["photo_status"] == "LOCAL_PRODUCT_PHOTO_ATTACHED")
    photobook_ready_count = sum(
        1
        for item in items
        if item.get("photo_status") == "LOCAL_PRODUCT_PHOTO_ATTACHED"
        and item.get("photo_quality_tier") == "PHOTOBOOK_PRODUCT_GRADE"
        and item.get("photo_evidence_label") in {"LOCAL_REAL_PRODUCT_PHOTO", "STAFF_APPROVED_PRODUCT_PHOTO"}
    )
    payload = {
        "schema": "w7tp_pos_mvp_real_menu.v1",
        "state": "REAL_MENU_FROM_REPO_ODOO_XML",
        "photo_state": "PHOTOBOOK_PRODUCT_GRADE_READY" if photobook_ready_count == len(items) else "PHOTOBOOK_PRODUCT_PHOTOS_REQUIRED_NOT_ATTACHED",
        "attached_photo_count": attached_photo_count,
        "photobook_ready_count": photobook_ready_count,
        "photo_manifest": str(PHOTO_MANIFEST.relative_to(ROOT)),
        "photobook_spec": str(PHOTOBOOK_SPEC.relative_to(ROOT)),
        "photo_policy": {
            "external_photo_fetch": False,
            "generated_photo_allowed": False,
            "generated_photo_allowed_as_product_evidence": False,
            "photo_quality_tier_required": "PHOTOBOOK_PRODUCT_GRADE",
            "local_product_photo_required_before_market_demo": True,
        },
        "authority": "taiji01_total_field_repo_evidence",
        "generated_at": utc_now(),
        "source_files": [
            str(BREAKFAST_XML.relative_to(ROOT)),
            str(PRODUCT_XML.relative_to(ROOT)),
        ],
        "safety_flags": SAFETY_FLAGS,
        "item_count": len(items),
        "categories": categories,
        "items": items,
    }
    payload["menu_hash"] = canonical_hash({k: v for k, v in payload.items() if k != "generated_at"})
    write_product_photo_prompts(payload)
    return payload


def write_menu() -> dict:
    ensure_dirs()
    payload = build_menu()
    MENU_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def load_menu() -> dict:
    if not MENU_JSON.exists():
        raise SystemExit(f"baseline menu missing: {MENU_JSON}")
    return json.loads(MENU_JSON.read_text(encoding="utf-8"))


def route_order_candidate() -> dict:
    cmd = [sys.executable, str(ROUTER), "--route", "POS 點餐 菜單 訂單 本地還原 order_candidate"]
    proc = subprocess.run(cmd, cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    route = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            route[key] = value
    if not route.get("ROUTE_CODE") or not route.get("LOOKUP_KEY"):
        raise SystemExit("route resolver did not return route code and lookup key")
    return route


def append_event(action_ref: str, node_ref: str, payload_ref: str, claim_label: str = "FACT") -> dict:
    rows = read_jsonl(EVENTS)
    parent_hash = rows[-1]["event_hash"] if rows else "GENESIS"
    event = {
        "event_id": f"evt_{len(rows) + 1:06d}",
        "event_time": utc_now(),
        "parent_hash": parent_hash,
        "actor_ref": "sandbox_pos_mvp_autodev",
        "node_ref": node_ref,
        "action_ref": action_ref,
        "payload_ref": payload_ref,
        "claim_label": claim_label,
    }
    event["event_hash"] = canonical_hash(event)
    append_jsonl(EVENTS, event)
    return event


def append_dead_letter(reason, payload=None, source=None, **kwargs):
    """24h hash-only dead letter writer. No plaintext payload is stored."""
    from runtime.dead_letter.dead_letter_24h_hash_writer import append_24h_hash_dead_letter
    return append_24h_hash_dead_letter(
        reason=reason,
        payload=payload,
        source=source,
        **kwargs,
    )

def create_order_candidate(lines: list[dict], source: str = "sandbox_customer_order") -> dict:
    menu = load_menu()
    by_code = {item["code"]: item for item in menu["items"]}
    normalized_lines = []
    total = 0.0
    for line in lines:
        code = str(line.get("code") or "")
        qty = int(line.get("qty") or 0)
        if code not in by_code or qty <= 0:
            return append_dead_letter("invalid_order_candidate_line", {"line": line, "source": source})
        item = by_code[code]
        subtotal = item["price"] * qty
        total += subtotal
        normalized_lines.append({
            "code": code,
            "name": item["name"],
            "category": item["category"],
            "qty": qty,
            "unit_price": item["price"],
            "subtotal": subtotal,
            "source_model": item["source_model"],
        })
    route = route_order_candidate()
    candidate = {
        "schema": "w7tp_pos_order_candidate.v1",
        "candidate_id": f"cand_{len(read_jsonl(ORDER_CANDIDATES)) + 1:06d}",
        "created_at": utc_now(),
        "source": source,
        "route_code": route["ROUTE_CODE"],
        "lookup_key": route["LOOKUP_KEY"],
        "cloud_return_expected": route.get("CLOUD_RETURN_EXPECTED"),
        "local_reconstruction_required": route.get("LOCAL_RECONSTRUCTION_REQUIRED") == "TRUE",
        "candidate_only": True,
        "cashier_confirm_required": True,
        "land_allowed": False,
        "odoo_write": False,
        "db_write": False,
        "lines": normalized_lines,
        "total": total,
        "currency": "TWD",
    }
    candidate["candidate_hash"] = canonical_hash(candidate)
    append_jsonl(ORDER_CANDIDATES, candidate)
    append_event("order_candidate.create", "NODE_POS_MAINT", candidate["candidate_id"], "FACT")
    return candidate


def confirm_order(candidate_id: str, cashier_ref: str = "cashier_sandbox") -> dict:
    candidates = {row["candidate_id"]: row for row in read_jsonl(ORDER_CANDIDATES)}
    candidate = candidates.get(candidate_id)
    if not candidate:
        return append_dead_letter("candidate_not_found", {"candidate_id": candidate_id})
    if not candidate.get("cashier_confirm_required"):
        return append_dead_letter("candidate_missing_cashier_gate", candidate)
    order = {
        "schema": "w7tp_pos_confirmed_local_order.v1",
        "order_id": f"order_{len(read_jsonl(CONFIRMED_ORDERS)) + 1:06d}",
        "candidate_id": candidate_id,
        "candidate_hash": candidate["candidate_hash"],
        "confirmed_at": utc_now(),
        "cashier_ref": cashier_ref,
        "status": "confirmed",
        "kitchen_status": "preparing",
        "lines": candidate["lines"],
        "total": candidate["total"],
        "currency": candidate["currency"],
        "odoo_sidecar_candidate": True,
        "odoo_core_write": False,
        "db_write": False,
    }
    order["order_hash"] = canonical_hash(order)
    append_jsonl(CONFIRMED_ORDERS, order)
    append_event("cashier_confirm.local_order", "NODE_POS_MAINT", order["order_id"], "FACT")
    return order


def kitchen_display() -> dict:
    orders = read_jsonl(CONFIRMED_ORDERS)
    payload = {
        "schema": "w7tp_kitchen_display_snapshot.v1",
        "generated_at": utc_now(),
        "node_ref": "NODE_XIAOJ_DISPLAY_COMPUTE",
        "display_only": True,
        "orders": [
            {
                "order_id": order["order_id"],
                "status": order["kitchen_status"],
                "lines": order["lines"],
                "total": order["total"],
            }
            for order in orders
        ],
    }
    append_event("kitchen_display.snapshot", "NODE_XIAOJ_DISPLAY_COMPUTE", f"orders:{len(orders)}", "FACT")
    return payload


def write_ui_files() -> None:
    ui = BASELINE_SANDBOX / "ui"
    menu = load_menu()
    files = {
        "customer_order.html": "POS MVP Customer Order - reads runtime/sandbox/pos_mvp_autodev/menu/menu.json",
        "cashier_confirm.html": "POS MVP Cashier Confirm - local candidate confirmation only",
        "kitchen_display.html": "POS MVP Kitchen Display - display-only confirmed local orders",
    }
    for filename, title in files.items():
        (ui / filename).write_text(
            "<!doctype html>\n"
            "<meta charset=\"utf-8\">\n"
            f"<title>{title}</title>\n"
            f"<h1>{title}</h1>\n"
            "<p>STATE=SANDBOX_ONLY PRODUCTION_DEPLOY=FALSE DB_WRITE=FALSE</p>\n",
            encoding="utf-8",
        )
    by_category = {}
    for item in menu["items"]:
        by_category.setdefault(item["category"], []).append(item)
    category_blocks = []
    for category in sorted(by_category):
        rows = "\n".join(
            "<li>"
            f"<span class=\"item-name\">{escape(item['name'])}</span>"
            f"<span class=\"item-price\">TWD {item['price']:.0f}</span>"
            f"<span class=\"item-photo\">{escape(item['photo_status'])} · {escape(item.get('photo_quality_tier', 'PHOTOBOOK_PRODUCT_GRADE_REQUIRED'))}</span>"
            "</li>"
            for item in by_category[category]
        )
        category_blocks.append(f"<section class=\"menu-group\"><h2>{escape(category)}</h2><ul>{rows}</ul></section>")
    standby_html = f"""<!doctype html>
<html lang="zh-Hant">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>主播小J與真實菜單同框待機畫面</title>
<style>
  :root {{
    color-scheme: dark;
    --bg: #101418;
    --panel: #182026;
    --line: #2d3a42;
    --text: #f2efe6;
    --muted: #a9b4b8;
    --accent: #f0c85a;
    --ok: #74d49b;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    min-height: 100vh;
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  .standby {{
    min-height: 100vh;
    display: grid;
    grid-template-columns: minmax(280px, 34vw) 1fr;
    gap: 18px;
    padding: 18px;
  }}
  .anchor, .menu {{
    border: 1px solid var(--line);
    background: var(--panel);
    border-radius: 8px;
    overflow: hidden;
  }}
  .anchor {{
    display: grid;
    align-content: center;
    justify-items: center;
    text-align: center;
    padding: 28px;
  }}
  .xiaoj-mark {{
    width: min(260px, 70%);
    aspect-ratio: 1;
    border-radius: 50%;
    display: grid;
    place-items: center;
    border: 3px solid var(--accent);
    background: #202a2f;
    margin-bottom: 22px;
  }}
  .xiaoj-face {{
    font-size: clamp(64px, 11vw, 132px);
    line-height: 1;
    font-weight: 800;
    color: var(--accent);
  }}
  h1 {{
    margin: 0 0 10px;
    font-size: clamp(30px, 4vw, 58px);
    letter-spacing: 0;
  }}
  .status {{
    margin: 0;
    color: var(--ok);
    font-size: 18px;
    font-weight: 700;
  }}
  .guard {{
    margin-top: 22px;
    color: var(--muted);
    font-size: 14px;
    line-height: 1.6;
  }}
  .menu {{
    padding: 22px;
  }}
  .menu-head {{
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: baseline;
    border-bottom: 1px solid var(--line);
    padding-bottom: 14px;
    margin-bottom: 18px;
  }}
  .menu-title {{
    margin: 0;
    font-size: clamp(28px, 3vw, 46px);
  }}
  .menu-meta {{
    color: var(--muted);
    font-size: 14px;
    text-align: right;
  }}
  .menu-grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(240px, 1fr));
    gap: 14px;
  }}
  .menu-group {{
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 14px;
  }}
  h2 {{
    margin: 0 0 10px;
    color: var(--accent);
    font-size: 20px;
  }}
  ul {{ list-style: none; padding: 0; margin: 0; }}
  li {{
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 8px 12px;
    padding: 8px 0;
    border-top: 1px solid rgba(255,255,255,.08);
  }}
  li:first-child {{ border-top: 0; }}
  .item-name {{ font-weight: 700; }}
  .item-price {{ color: var(--text); }}
  .item-photo {{
    grid-column: 1 / -1;
    color: var(--muted);
    font-size: 12px;
  }}
  @media (max-width: 820px) {{
    .standby {{ grid-template-columns: 1fr; }}
    .menu-grid {{ grid-template-columns: 1fr; }}
    .menu-head {{ display: block; }}
    .menu-meta {{ text-align: left; margin-top: 8px; }}
  }}
</style>
<main class="standby" data-state="SANDBOX_STANDBY_ONLY" data-menu-state="{escape(menu['state'])}" data-photo-state="{escape(menu['photo_state'])}">
  <section class="anchor" aria-label="主播小J待機區">
    <div class="xiaoj-mark" aria-hidden="true"><div class="xiaoj-face">小J</div></div>
    <h1>主播小J</h1>
    <p class="status">待機中 · 真實菜單同框 · 寫真集產品照閘</p>
    <p class="guard">DISPLAY_ONLY=TRUE<br>PRODUCTION_DEPLOY=FALSE<br>DB_WRITE=FALSE<br>PHOTO_SOURCE=LOCAL_ONLY<br>PHOTO_TIER=PHOTOBOOK_PRODUCT_GRADE</p>
  </section>
  <section class="menu" aria-label="上品聊國重新總店菜單">
    <div class="menu-head">
      <h1 class="menu-title">上品聊國重新總店菜單</h1>
      <div class="menu-meta">MENU_STATE={escape(menu['state'])}<br>ITEMS={menu['item_count']} · PHOTOS={menu['attached_photo_count']} · PHOTOBOOK_READY={menu['photobook_ready_count']}</div>
    </div>
    <div class="menu-grid">
      {''.join(category_blocks)}
    </div>
  </section>
</main>
</html>
"""
    (ui / "standby_xiaoj_menu.html").write_text(standby_html, encoding="utf-8")


def init_sandbox() -> dict:
    reset_runtime_files()
    menu = load_menu()
    append_event("baseline.menu.real_source.load", "NODE_POS_MAINT", "menu/menu.json", "FACT")
    append_event("baseline.standby_xiaoj_menu.read", "NODE_XIAOJ_DISPLAY_COMPUTE", "ui/standby_xiaoj_menu.html", "FACT")
    return menu


def run_demo() -> dict:
    menu = init_sandbox()
    first_coffee = next(item for item in menu["items"] if item["name"] == "拿鐵")
    first_food = next(item for item in menu["items"] if item["name"] == "中式套餐")
    candidate = create_order_candidate([
        {"code": first_coffee["code"], "qty": 1},
        {"code": first_food["code"], "qty": 1},
    ])
    order = confirm_order(candidate["candidate_id"])
    invalid = create_order_candidate([{"code": "NOT_A_REAL_MENU_ITEM", "qty": 1}], "invalid_case_verifier")
    display = kitchen_display()
    return {
        "menu_hash": menu["menu_hash"],
        "candidate_id": candidate["candidate_id"],
        "order_id": order["order_id"],
        "invalid_case": invalid["dead_letter_id"],
        "display_order_count": len(display["orders"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init", "menu", "candidate", "confirm", "kitchen", "demo"])
    parser.add_argument("--lines", help="JSON array of {code, qty} lines")
    parser.add_argument("--candidate-id")
    args = parser.parse_args()
    if args.command == "init":
        result = init_sandbox()
    elif args.command == "menu":
        result = load_menu()
    elif args.command == "candidate":
        if not args.lines:
            raise SystemExit("--lines is required")
        result = create_order_candidate(json.loads(args.lines))
    elif args.command == "confirm":
        if not args.candidate_id:
            raise SystemExit("--candidate-id is required")
        result = confirm_order(args.candidate_id)
    elif args.command == "kitchen":
        result = kitchen_display()
    else:
        result = run_demo()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
