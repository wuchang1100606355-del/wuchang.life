#!/usr/bin/env python3
"""Verify XiaoJ P0 onsite shadow rehearsal package."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = ROOT / "docs/operations/XIAOJ_P0_ONSITE_SHADOW_REHEARSAL_RUNBOOK.md"
BROADCAST = ROOT / "docs/operations/XIAOJ_P0_BROADCAST_SCRIPT_RUNBOOK.md"
CANDIDATE = ROOT / "docs/operations/XIAOJ_P0_CANDIDATE_ORDER_AND_HUMAN_CORRECTION_FLOW.md"
TRAINING = ROOT / "docs/operations/XIAOJ_P0_TRAINING_DATA_CAPTURE_SCHEMA.md"
MENU_REFS = ROOT / "runtime/xiaoj_practicum/p0_shadow_rehearsal/p0_shadow_menu_refs.json"
SAMPLE_ORDER = ROOT / "runtime/xiaoj_practicum/p0_shadow_rehearsal/sample_candidate_order.json"
SAMPLE_BROADCAST = ROOT / "runtime/xiaoj_practicum/p0_shadow_rehearsal/sample_broadcast_script.json"
TRAINING_LOG = ROOT / "runtime/xiaoj_practicum/p0_shadow_rehearsal/training_candidates.jsonl"
REPORT = ROOT / "runtime/d8_db/reports/XIAOJ_P0_ONSITE_SHADOW_REHEARSAL_FINAL_REPORT.json"
SEAL = ROOT / "runtime/total_field/status/XIAOJ_P0_ONSITE_SHADOW_REHEARSAL_SEAL.md"

FILES = [
    RUNBOOK,
    BROADCAST,
    CANDIDATE,
    TRAINING,
    MENU_REFS,
    SAMPLE_ORDER,
    SAMPLE_BROADCAST,
    TRAINING_LOG,
    REPORT,
    SEAL,
]

REQUIRED_TEXT = {
    RUNBOOK: [
        "Today XiaoJ Can Do",
        "Today XiaoJ Cannot Do",
        "A Track: Real Human POS",
        "B Track: XiaoJ Shadow",
        "Stop Conditions",
        "Evening Training Cleanup",
    ],
    BROADCAST: [
        "Broadcast Schema",
        "local text rehearsal only",
        "tts_engine",
        "local_text_only_this_run",
    ],
    CANDIDATE: [
        "Candidate Order Schema",
        "Non-Float Anti-Hallucination Rule",
        "write_to_odoo",
        "payment_capture",
    ],
    TRAINING: [
        "JSONL Row Schema",
        "Forbidden Training Content",
        "raw_audio_saved",
        "raw_video_saved",
    ],
    SEAL: [
        "STATE=PASS_XIAOJ_P0_SHADOW_REHEARSAL_READY",
        "ACTION=XIAOJ_P0_ONSITE_SHADOW_BROADCAST_CANDIDATE_ORDER_REHEARSAL_DONE",
        "XIAOJ_CAN_WRITE_REAL_POS_ORDER=FALSE",
        "XIAOJ_CAN_CAPTURE_PAYMENT=FALSE",
    ],
}

SAFETY_FLAGS = [
    "SECRET_READ=FALSE",
    "MEMBER_PLAINTEXT_READ=FALSE",
    "RAW_AUDIO_SAVED=FALSE",
    "RAW_VIDEO_SAVED=FALSE",
    "ODOO_DB_WRITE=FALSE",
    "POS_ORDER_CREATED=FALSE",
    "PAYMENT_CAPTURE=FALSE",
    "SERVICE_RESTART=FALSE",
    "DEPLOY=FALSE",
    "EXTERNAL_API_CALL=FALSE",
    "GOOGLE_STT_CALL=FALSE",
    "GOOGLE_TTS_CALL=FALSE",
]

ALLOWED_MENU_REFS = {
    "odoo_product_11",
    "odoo_product_12",
    "odoo_product_13",
    "odoo_product_14",
    "odoo_product_15",
}


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict:
    try:
        return json.loads(read(path))
    except json.JSONDecodeError as exc:
        fail(f"json_invalid:{path.relative_to(ROOT)}:{exc}")


def main() -> int:
    texts = {path: read(path) for path in FILES}
    combined = "\n".join(texts.values())

    for path, needles in REQUIRED_TEXT.items():
        for needle in needles:
            if needle not in texts[path]:
                fail(f"{path.relative_to(ROOT)} missing {needle}")

    for flag in SAFETY_FLAGS:
        if flag not in combined:
            fail(f"safety_flag_missing:{flag}")

    menu = load_json(MENU_REFS)
    if menu.get("real_menu_source_lock") != "PASS_FOR_P0_POS_VISIBLE_5_ONLY":
        fail("menu_lock_not_p0_pass")
    if menu.get("full_quickclick_menu_source_lock") != "HOLD_MENU_SOURCE_REQUIRED":
        fail("full_quickclick_hold_not_recorded")
    for item in menu.get("menu_refs", []):
        if item.get("menu_ref") not in ALLOWED_MENU_REFS:
            fail(f"unexpected_menu_ref:{item.get('menu_ref')}")

    order = load_json(SAMPLE_ORDER)
    if order.get("write_to_odoo") is not False:
        fail("sample_order_write_to_odoo_not_false")
    if order.get("payment_capture") is not False:
        fail("sample_order_payment_capture_not_false")
    for item in order.get("candidate_items", []):
        if item.get("menu_ref") not in ALLOWED_MENU_REFS:
            fail(f"sample_order_bad_menu_ref:{item.get('menu_ref')}")
        if item.get("needs_human_review") is not True:
            fail("sample_order_human_review_not_true")

    broadcast = load_json(SAMPLE_BROADCAST)
    if broadcast.get("tts_engine") != "local_text_only_this_run":
        fail("broadcast_tts_engine_not_local_text")
    if broadcast.get("google_stt_call") is not False:
        fail("broadcast_google_stt_not_false")
    if broadcast.get("google_tts_call") is not False:
        fail("broadcast_google_tts_not_false")

    for line_no, line in enumerate(texts[TRAINING_LOG].splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("write_to_odoo") is not False:
            fail(f"training_log_write_to_odoo_not_false:{line_no}")
        if row.get("payment_capture") is not False:
            fail(f"training_log_payment_capture_not_false:{line_no}")
        if row.get("member_plaintext") is not False:
            fail(f"training_log_member_plaintext_not_false:{line_no}")
        if row.get("raw_audio_saved") is not False:
            fail(f"training_log_raw_audio_not_false:{line_no}")

    report = load_json(REPORT)
    if report.get("state") != "PASS_XIAOJ_P0_SHADOW_REHEARSAL_READY":
        fail("report_state_not_pass")

    print("STATE=PASS_XIAOJ_P0_SHADOW_REHEARSAL_READY")
    print("ACTION=VERIFY_XIAOJ_P0_SHADOW_REHEARSAL")
    print("REAL_MENU_SOURCE_LOCK=PASS_FOR_P0_POS_VISIBLE_5_ONLY")
    print("FULL_QUICKCLICK_MENU_SOURCE_LOCK=HOLD_MENU_SOURCE_REQUIRED")
    print(f"RUNBOOK={RUNBOOK.relative_to(ROOT)}")
    print(f"BROADCAST_RUNBOOK={BROADCAST.relative_to(ROOT)}")
    print(f"CANDIDATE_FLOW={CANDIDATE.relative_to(ROOT)}")
    print(f"TRAINING_SCHEMA={TRAINING.relative_to(ROOT)}")
    print(f"REPORT={REPORT.relative_to(ROOT)}")
    print(f"SEAL={SEAL.relative_to(ROOT)}")
    print("ODOO_DB_WRITE=FALSE")
    print("POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("GOOGLE_STT_CALL=FALSE")
    print("GOOGLE_TTS_CALL=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
