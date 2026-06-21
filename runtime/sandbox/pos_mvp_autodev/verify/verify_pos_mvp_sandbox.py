#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/taiji_admin/Taiji_Hub")
SANDBOX = ROOT / "runtime/sandbox/pos_mvp_autodev"
API = SANDBOX / "api/pos_mvp_api.py"
MENU_JSON = SANDBOX / "menu/menu.json"
PHOTO_PROMPTS_JSON = SANDBOX / "menu/product_photo_ai_prompts.json"
PHOTO_PROMPTS_MD = SANDBOX / "menu/product_photo_ai_prompts.md"
GEMINI_SINGLE_PROMPT_MD = SANDBOX / "menu/gemini_single_product_prompt.md"
ORDER_CANDIDATES = SANDBOX / "orders/order_candidates.jsonl"
CONFIRMED_ORDERS = SANDBOX / "orders/confirmed_orders.jsonl"
EVENTS = SANDBOX / "events/spacetime_events.jsonl"
DEAD_LETTER = SANDBOX / "dead_letter/dead_letter_queue.jsonl"
STANDBY_UI = SANDBOX / "ui/standby_xiaoj_menu.html"
PACKET = ROOT / "packets/pos_mvp/POS_MVP_SANDBOX_PACKET.json"
EVIDENCE = ROOT / "docs/evidence/pos_mvp/README.md"
MANIFEST = ROOT / "docs/evidence/pos_mvp/sha256_manifest.txt"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def stable_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    subprocess.run([sys.executable, str(API), "demo"], cwd=str(ROOT), check=True, stdout=subprocess.PIPE, text=True)

    menu = json.loads(MENU_JSON.read_text(encoding="utf-8"))
    prompt_pack = json.loads(PHOTO_PROMPTS_JSON.read_text(encoding="utf-8"))
    candidates = load_jsonl(ORDER_CANDIDATES)
    orders = load_jsonl(CONFIRMED_ORDERS)
    events = load_jsonl(EVENTS)
    dead_letters = load_jsonl(DEAD_LETTER)

    require(menu["state"] == "REAL_MENU_FROM_REPO_ODOO_XML", "menu must be generated from real Odoo XML")
    require(menu["photo_state"] in {"PHOTOBOOK_PRODUCT_PHOTOS_REQUIRED_NOT_ATTACHED", "PHOTOBOOK_PRODUCT_GRADE_READY"}, "photo state mismatch")
    require(menu["photo_policy"]["external_photo_fetch"] is False, "external photo fetch must remain blocked")
    require(menu["photo_policy"]["generated_photo_allowed"] is False, "generated product photo must remain blocked")
    require(menu["photo_policy"]["generated_photo_allowed_as_product_evidence"] is False, "generated product photo evidence must remain blocked")
    require(menu["photo_policy"]["photo_quality_tier_required"] == "PHOTOBOOK_PRODUCT_GRADE", "photobook tier missing")
    require(menu["photo_policy"]["local_product_photo_required_before_market_demo"] is True, "market demo photo gate missing")
    require(menu["photo_manifest"] == "runtime/sandbox/pos_mvp_autodev/menu/product_photos_manifest.json", "photo manifest path mismatch")
    require(menu["photobook_spec"] == "runtime/sandbox/pos_mvp_autodev/menu/product_photobook_spec.json", "photobook spec path mismatch")
    require(menu["photobook_ready_count"] <= menu["attached_photo_count"] <= menu["item_count"], "photo counts invalid")
    require(prompt_pack["state"] == "PHOTOBOOK_PRODUCT_GRADE_AI_PROMPT_CANDIDATES", "prompt pack state mismatch")
    require(prompt_pack["item_count"] == menu["item_count"], "prompt pack item count mismatch")
    require(prompt_pack["source_menu_hash"] == menu["menu_hash"], "prompt pack menu hash mismatch")
    require(prompt_pack["same_style_different_items_required"] is True, "same-style different-items gate missing")
    require(prompt_pack["angle_variation_allowed"] is True, "angle variation must be allowed")
    style_lock = prompt_pack["style_lock"]
    require(style_lock["style_id"] == "LIAOGUO_PHOTOBOOK_STANDBY_STYLE_V1", "style lock id mismatch")
    require("shot angle may vary" in style_lock["consistency_rule"], "style lock must allow angle variation")
    require("front_45_degree" in style_lock["allowed_angle_variation"], "allowed angle variation missing")
    require("top_down_30_degree" in style_lock["allowed_angle_variation"], "allowed angle variation missing")
    require(prompt_pack["google_account_action"] == "USER_MANUAL_ONLY", "Google generation must remain user-manual")
    require(prompt_pack["google_account_read"] is False, "Google account read must remain false")
    require(prompt_pack["google_api_call"] is False, "Google API call must remain false")
    require(prompt_pack["external_photo_fetch"] is False, "prompt pack external photo fetch drift")
    require(prompt_pack["generated_image_is_product_evidence"] is False, "generated image must not be product evidence")
    require(prompt_pack["staff_approval_required_before_market_use"] is True, "staff approval gate missing")
    for row in prompt_pack["prompts"]:
        require(row["quality_tier"] == "PHOTOBOOK_PRODUCT_GRADE", f"prompt quality tier drift: {row['item_code']}")
        require(row["style_id"] == style_lock["style_id"], f"prompt style id drift: {row['item_code']}")
        require(row["style_consistency_required"] is True, f"style consistency flag missing: {row['item_code']}")
        require(row["angle_variation_allowed"] is True, f"angle variation flag missing: {row['item_code']}")
        require(row["allowed_angle_variation"] == style_lock["allowed_angle_variation"], f"angle variation list drift: {row['item_code']}")
        require(row["evidence_label"] == "AI_IMAGE_PROMPT_CANDIDATE_NOT_PRODUCT_EVIDENCE", f"prompt evidence label drift: {row['item_code']}")
        require(row["google_manual_generation"] is True, f"manual Google flag missing: {row['item_code']}")
        for shot_type in ["hero_product", "menu_grid_thumbnail", "detail_texture", "serving_context"]:
            require(shot_type in row["prompts"], f"prompt missing shot type {shot_type}: {row['item_code']}")
            require(row["item_name"] in row["prompts"][shot_type], f"prompt missing item name: {row['item_code']}")
            require(style_lock["style_id"] in row["prompts"][shot_type], f"prompt missing shared style id: {row['item_code']}")
            require("必須保持同系列風格" in row["prompts"][shot_type], f"prompt missing same-series guard: {row['item_code']}")
        require("允許依 shot type 變換角度" in row["negative_prompt"], f"negative prompt missing angle allowance: {row['item_code']}")
        require("不要把 AI 圖說成真實實拍" in row["negative_prompt"], f"negative prompt missing evidence guard: {row['item_code']}")
    prompt_md = PHOTO_PROMPTS_MD.read_text(encoding="utf-8")
    for phrase in [
        "STATE=PHOTOBOOK_PRODUCT_GRADE_AI_PROMPT_CANDIDATES",
        "GOOGLE_ACCOUNT_ACTION=USER_MANUAL_ONLY",
        "GENERATED_IMAGE_IS_PRODUCT_EVIDENCE=FALSE",
        "SAME_STYLE_DIFFERENT_ITEMS_REQUIRED=TRUE",
        "ANGLE_VARIATION_ALLOWED=TRUE",
        "LIAOGUO_PHOTOBOOK_STANDBY_STYLE_V1",
        "hero_product",
        "serving_context",
    ]:
        require(phrase in prompt_md, f"prompt markdown missing phrase: {phrase}")
    single_prompt = GEMINI_SINGLE_PROMPT_MD.read_text(encoding="utf-8")
    for phrase in [
        "STATE=GEMINI_SINGLE_PRODUCT_PROMPT_READY",
        "每次只改 `品名`、`shot_type`、`角度` 三欄，一次只生成一張",
        "品名：{請填品名}",
        "STYLE_ID=LIAOGUO_PHOTOBOOK_STANDBY_STYLE_V1",
        "front_45_degree",
        "top_down_30_degree",
        "macro_detail_low_angle",
        "menu_grid_centered",
        "可用真實菜單品名",
        "拿鐵",
        "中式套餐",
    ]:
        require(phrase in single_prompt, f"single Gemini prompt missing phrase: {phrase}")
    require("GOOGLE_API_CALL=FALSE" in single_prompt, "single Gemini prompt must not call Google API")
    standby_html = STANDBY_UI.read_text(encoding="utf-8")
    for phrase in [
        "主播小J",
        "真實菜單同框",
        "上品聊國重新總店菜單",
        "DISPLAY_ONLY=TRUE",
        "PHOTO_SOURCE=LOCAL_ONLY",
        "PHOTO_TIER=PHOTOBOOK_PRODUCT_GRADE",
        "PHOTOBOOK_READY=",
        "data-state=\"SANDBOX_STANDBY_ONLY\"",
        "MENU_STATE=REAL_MENU_FROM_REPO_ODOO_XML",
    ]:
        require(phrase in standby_html, f"standby UI missing phrase: {phrase}")
    require("http://" not in standby_html and "https://" not in standby_html, "standby UI must not fetch external assets")
    require("Taiji_Odoo/addons/wuchang_core/data/breakfast_pos_menu.xml" in menu["source_files"], "breakfast menu source missing")
    require("Taiji_Odoo/addons/wuchang_core/data/menu_setup.xml" in menu["source_files"], "product menu source missing")
    require(menu["item_count"] >= 20, "real menu item count too low")
    item_names = {item["name"] for item in menu["items"]}
    for name in ["紅茶", "中式套餐", "拿鐵", "美式咖啡", "焦糖瑪奇朵"]:
        require(name in item_names, f"real menu item missing: {name}")
    source_models = {item["source_model"] for item in menu["items"]}
    require({"wuchang.menu.item", "product.template"}.issubset(source_models), "menu must include both Odoo menu models")

    flags = menu["safety_flags"]
    for key in [
        "SECRET_READ",
        "MEMBER_PLAINTEXT_READ",
        "DB_WRITE",
        "SERVICE_RESTART",
        "DEPLOY",
        "ODOO_CORE_MUTATION",
        "PRODUCTION_LINE_ACTION",
        "PRODUCTION_GOOGLE_ACTION",
    ]:
        require(flags.get(key) is False, f"safety flag drift: {key}")

    require(candidates, "order candidate missing")
    candidate = candidates[0]
    require(candidate["route_code"] == "ODOO_POS_ACTION", "route_code mismatch")
    require(candidate["lookup_key"] in {"odoo.pos.action.candidate.v1", "pos.local.reconstruct.v1"}, "lookup_key mismatch")
    require(candidate["candidate_only"] is True, "candidate_only must be true")
    require(candidate["cashier_confirm_required"] is True, "cashier confirm gate missing")
    require(candidate["land_allowed"] is False, "candidate must not be land_allowed")
    require(candidate["db_write"] is False and candidate["odoo_write"] is False, "candidate must not write DB/Odoo")
    require(candidate["local_reconstruction_required"] is True, "local reconstruction required missing")
    require(stable_hash({k: v for k, v in candidate.items() if k != "candidate_hash"}) == candidate["candidate_hash"], "candidate hash mismatch")

    require(orders, "confirmed order missing")
    order = orders[0]
    require(order["candidate_id"] == candidate["candidate_id"], "confirmed order candidate mismatch")
    require(order["candidate_hash"] == candidate["candidate_hash"], "confirmed order candidate hash mismatch")
    require(order["odoo_core_write"] is False and order["db_write"] is False, "confirmed order must remain local only")

    require(dead_letters, "dead_letter_queue did not receive invalid case")
    require(any(row["reason"] == "invalid_order_candidate_line" for row in dead_letters), "invalid line was not dead-lettered")
    require(all(row["silent_drop"] is False for row in dead_letters), "silent drop detected")
    require(all(row["retry_count"] <= row["max_retry_count"] <= 2 for row in dead_letters), "retry bound drift")

    require(events, "spacetime events missing")
    for previous, current in zip(events, events[1:]):
        require(current["parent_hash"] == previous["event_hash"], f"event hash chain break: {current['event_id']}")
    for event in events:
        expected = stable_hash({k: v for k, v in event.items() if k != "event_hash"})
        require(expected == event["event_hash"], f"event hash mismatch: {event['event_id']}")

    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    require(packet["state"] == "POS_MVP_SANDBOX_AUTODEV_PACKET", "packet state mismatch")
    require(packet["production_deploy"] is False, "packet deploy flag drift")
    require(packet["real_menu_required"] is True, "packet must require real menu")
    require(packet["external_mother_file_required"] is False, "external mother file must not be required")
    require(packet["external_mother_file_authority"] is False, "external mother file must not be authority")
    require(packet["external_mother_file_status"] == "KNOWN_INCORRECT_NOT_AUTHORITY", "external mother file status drift")
    require(packet["xlsx_export_required"] is False, "xlsx export must not be required")
    require(packet["menu_source"] == menu["source_files"], "packet menu source mismatch")
    photo_policy = packet["product_photo_policy"]
    require(photo_policy["local_product_photos_supported"] is True, "local product photos support missing")
    require(photo_policy["external_photo_fetch"] is False, "external photo fetch packet drift")
    require(photo_policy["generated_photo_allowed"] is False, "generated photo packet drift")
    require(photo_policy["generated_photo_allowed_as_product_evidence"] is False, "generated photo evidence packet drift")
    require(photo_policy["photo_quality_tier_required"] == "PHOTOBOOK_PRODUCT_GRADE", "packet photobook tier missing")
    require(photo_policy["market_demo_requires_local_photos"] is True, "market demo local photo gate missing")
    require(photo_policy["current_photo_state"] == menu["photo_state"], "packet photo state must match menu")
    prompt_policy = packet["product_photo_prompt_policy"]
    require(prompt_policy["same_style_different_items_required"] is True, "packet same-style gate missing")
    require(prompt_policy["angle_variation_allowed"] is True, "packet angle variation missing")
    require(prompt_policy["style_id"] == style_lock["style_id"], "packet style id mismatch")
    d8 = packet["d8_envelope"]
    require(d8["secret_read"] is False, "d8 secret flag drift")
    require(d8["member_plaintext_read"] is False, "d8 member plaintext flag drift")
    require(d8["db_write"] is False, "d8 db write flag drift")
    require(d8["service_restart"] is False, "d8 service restart flag drift")
    require(d8["deploy"] is False, "d8 deploy flag drift")
    standby_policy = packet["standby_display_policy"]
    require(standby_policy["xiaoj_anchor_with_menu"] is True, "standby xiaoj/menu policy missing")
    require(standby_policy["display_only"] is True, "standby must remain display-only")
    require(standby_policy["chrome_live_control"] is False, "standby must not control Chrome")
    require(standby_policy["external_asset_fetch"] is False, "standby external asset fetch must remain blocked")
    require(standby_policy["ui_file"] == "runtime/sandbox/pos_mvp_autodev/ui/standby_xiaoj_menu.html", "standby UI path mismatch")

    evidence = EVIDENCE.read_text(encoding="utf-8")
    for phrase in [
        "STATE=POS_MVP_SANDBOX_AUTODEV",
        "REAL_MENU_FROM_REPO_ODOO_XML",
        "External mother file is known to be incorrect",
        "Product photos must be local files",
        "standby_xiaoj_menu.html",
        "PHOTOBOOK_PRODUCT_PHOTOS_REQUIRED_NOT_ATTACHED",
        "PHOTOBOOK_PRODUCT_GRADE",
        "PRODUCTION_DEPLOY=FALSE",
    ]:
        require(phrase in evidence, f"evidence missing phrase: {phrase}")

    manifest_paths = [
        API,
        SANDBOX / "verify/verify_pos_mvp_sandbox.py",
        ROOT / "scripts/pos_mvp/run_pos_mvp_sandbox.py",
        ROOT / "scripts/pos_mvp/generate_pos_mvp_sandbox.py",
        ROOT / "scripts/verify/verify_pos_mvp_sandbox.sh",
        MENU_JSON,
        SANDBOX / "menu/product_photos_manifest.json",
        SANDBOX / "menu/product_photobook_spec.json",
        PHOTO_PROMPTS_JSON,
        PHOTO_PROMPTS_MD,
        GEMINI_SINGLE_PROMPT_MD,
        STANDBY_UI,
        PACKET,
        EVIDENCE,
    ]
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT)}\n" for path in manifest_paths),
        encoding="utf-8",
    )

    print("STATE=PASS_POS_MVP_SANDBOX")
    print(f"MENU_ITEMS={menu['item_count']}")
    print(f"ORDER_CANDIDATES={len(candidates)}")
    print(f"CONFIRMED_ORDERS={len(orders)}")
    print(f"SPACETIME_EVENTS={len(events)}")
    print(f"DEAD_LETTER_ROWS={len(dead_letters)}")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("DB_WRITE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
