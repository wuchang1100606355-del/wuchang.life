#!/usr/bin/env python3
"""Verify XiaoJ real menu source-lock manifest.

This verifier ensures visual QuickClick candidate rows cannot be treated as live
POS order authority before source hashes and human conflict review exist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "runtime/total_field/xiaoj_p1_console/menu_source_lock.json"
CONSOLE_MANIFEST = ROOT / "runtime/total_field/xiaoj_p1_console/manifest.json"
ENGINE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/p1_intent_engine.py"


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"json_invalid:{path.relative_to(ROOT)}:{exc}")


def main() -> int:
    lock = load_json(LOCK)
    manifest = load_json(CONSOLE_MANIFEST)
    engine_source = ENGINE.read_text(encoding="utf-8")

    if lock.get("state") != "HOLD_REAL_MENU_SOURCE_LOCK":
        fail("lock_state_not_hold")
    authority = lock.get("authority", {})
    for key in [
        "current_menu_authority",
        "can_create_pos_order_from_this_manifest",
        "can_capture_payment_from_this_manifest",
    ]:
        if authority.get(key) is not False:
            fail(f"authority_flag_not_false:{key}")
    if authority.get("live_quickclick_export_required") is not True:
        fail("live_quickclick_export_required_not_true")

    rows = lock.get("candidate_rows", [])
    if len(rows) < 6:
        fail("candidate_rows_too_few")
    for row in rows:
        if row.get("orderable_now") is not False:
            fail(f"row_orderable_now_not_false:{row.get('id')}")
        if not str(row.get("review_status", "")).startswith("candidate_visual_only"):
            fail(f"row_review_status_not_candidate:{row.get('id')}")

    conflicts = lock.get("known_conflicts", [])
    if len(conflicts) < 3:
        fail("known_conflicts_too_few")

    forbidden_text = "\n".join(lock.get("forbidden_as_menu_authority", []) + lock.get("forbidden_invented_items", []))
    for expected in ["GPT prompt text", "三明治", "蛋餅", "local CSV rows contradicted"]:
        if expected not in forbidden_text:
            fail(f"forbidden_guard_missing:{expected}")

    linked = manifest.get("menu_source_lock", {})
    if linked.get("manifest") != str(LOCK.relative_to(ROOT)):
        fail("console_manifest_not_linked_to_source_lock")
    if linked.get("current_menu_authority") is not False:
        fail("console_manifest_current_menu_authority_not_false")

    for needle in [
        "HOLD_REAL_MENU_SOURCE_LOCK",
        "can_create_pos_order_from_current_menu",
        "live_quickclick_export_required",
    ]:
        if needle not in engine_source:
            fail(f"engine_source_lock_missing:{needle}")

    print("STATE=PASS_REAL_MENU_SOURCE_LOCK_MANIFEST_READY")
    print("ACTION=VERIFY_XIAOJ_REAL_MENU_SOURCE_LOCK")
    print(f"LOCK={LOCK.relative_to(ROOT)}")
    print(f"CANDIDATE_ROWS={len(rows)}")
    print(f"KNOWN_CONFLICTS={len(conflicts)}")
    print("CURRENT_MENU_AUTHORITY=FALSE")
    print("CAN_CREATE_POS_ORDER_FROM_CURRENT_MENU=FALSE")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("ODOO_DB_WRITE=FALSE")
    print("POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
