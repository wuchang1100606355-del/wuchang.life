#!/usr/bin/env python3
"""Verify the XiaoJ premium user manual and developer guide.

This verifier reads only docs. It does not read secrets, write Odoo DB, create
POS orders, capture payments, save raw audio, restart services, deploy,
generate embeddings, or call external APIs.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
USER_MANUAL = ROOT / "docs/operations/XIAOJ_PREMIUM_USER_MANUAL.md"
DEV_GUIDE = ROOT / "docs/total_field/XIAOJ_DEVELOPER_GUIDE.md"
INDEX = ROOT / "docs/product/XIAOJ_PREMIUM_MANUAL_PACKAGE_INDEX.md"


REQUIRED_FILES = [USER_MANUAL, DEV_GUIDE, INDEX]

REQUIRED_USER_TEXT = [
    "PREMIUM_USER_MANUAL_READY_RUNTIME_HOLD",
    "TRACK_A_LIVE_OPERATION=HUMAN_ONLY",
    "TRACK_B_XIAOJ_SHADOW=CANDIDATE_ONLY",
    "尺寸 → 溫度 → 甜度 → 品項",
    "大冰少糖拿鐵",
    "Vietnamese",
    "Xac nhan ban nhap",
    "HOLD_REAL_MENU_SOURCE_LOCK",
    "不可直接寫入真 POS",
    "不建立真 POS 訂單",
    "不 capture payment",
]

REQUIRED_DEV_TEXT = [
    "DEVELOPER_GUIDE_READY_RUNTIME_HOLD",
    "State → Coordinate → Hash → Packet → Generative Transfer → Verify → Reconstruct → Evidence → Action",
    "tools/d8_codex_mandatory_workflow.sh start",
    "verify_xiaoj_p1_intent_engine.py",
    "verify_xiaoj_p1_console_prototype.py",
    "verify_xiaoj_p1_local_rehearsal.py",
    "verify_xiaoj_field_practicum_dual_track.py",
    "HOLD_AUTH_ROUTE_GATE",
    "HOLD_REAL_MENU_SOURCE_LOCK",
    "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED",
    "HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED",
    "price_authority=false",
    "live_orderable=false",
    "XIAOJ_AV_ORDERING_AUTH_AND_STICKINESS_LAND_P1",
]

REQUIRED_INDEX_TEXT = [
    "PREMIUM_MANUAL_PACKAGE_READY_RUNTIME_HOLD",
    "docs/operations/XIAOJ_PREMIUM_USER_MANUAL.md",
    "docs/total_field/XIAOJ_DEVELOPER_GUIDE.md",
]

SAFETY_FALSE_FLAGS = [
    "SECRET_READ=FALSE",
    "MEMBER_PLAINTEXT_READ=FALSE",
    "RAW_AUDIO_SAVED=FALSE",
    "ODOO_DB_WRITE=FALSE",
    "POS_ORDER_CREATED=FALSE",
    "PAYMENT_CAPTURE=FALSE",
    "SERVICE_RESTART=FALSE",
    "DEPLOY=FALSE",
    "EXTERNAL_API_CALL=FALSE",
    "EMBEDDING_GENERATED=FALSE",
]

FORBIDDEN_TEXT = [
    "STATE=PRODUCTION_READY",
    "POS_ORDER_CREATED=TRUE",
    "PAYMENT_CAPTURE=TRUE",
    "ODOO_DB_WRITE=TRUE",
    "read .env",
    "print secret",
]


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require_all(text: str, required: list[str], label: str) -> None:
    for item in required:
        if item not in text:
            fail(f"{label}_required_text_missing:{item}")


def main() -> int:
    for path in REQUIRED_FILES:
        if not path.exists():
            fail(f"missing:{path.relative_to(ROOT)}")

    user_text = read(USER_MANUAL)
    dev_text = read(DEV_GUIDE)
    index_text = read(INDEX)
    combined = "\n".join([user_text, dev_text, index_text])

    require_all(user_text, REQUIRED_USER_TEXT, "user_manual")
    require_all(dev_text, REQUIRED_DEV_TEXT, "developer_guide")
    require_all(index_text, REQUIRED_INDEX_TEXT, "package_index")
    for flag in SAFETY_FALSE_FLAGS:
        if flag not in combined:
            fail(f"safety_flag_missing:{flag}")
    for forbidden in FORBIDDEN_TEXT:
        if forbidden in combined:
            fail(f"forbidden_text_present:{forbidden}")

    print("STATE=PASS_XIAOJ_PREMIUM_MANUALS_READY_RUNTIME_HOLD")
    print("ACTION=VERIFY_XIAOJ_PREMIUM_MANUALS")
    print(f"USER_MANUAL={USER_MANUAL.relative_to(ROOT)}")
    print(f"DEVELOPER_GUIDE={DEV_GUIDE.relative_to(ROOT)}")
    print(f"PACKAGE_INDEX={INDEX.relative_to(ROOT)}")
    print("TRACK_A_LIVE_OPERATION=HUMAN_ONLY")
    print("TRACK_B_XIAOJ_SHADOW=CANDIDATE_ONLY")
    print("VOICE_POS_EXAMPLE=大冰少糖拿鐵")
    print("AUTH_ROUTE_GATE=HOLD_AUTH_ROUTE_GATE")
    print("MENU_SOURCE_GATE=HOLD_REAL_MENU_SOURCE_LOCK")
    print("POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("ODOO_DB_WRITE=FALSE")
    print("SECRET_READ=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
