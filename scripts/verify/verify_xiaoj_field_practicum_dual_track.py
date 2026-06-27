#!/usr/bin/env python3
"""Verify XiaoJ field practicum dual-track rule.

This verifier reads only source/docs. It does not read secrets, write Odoo DB,
create POS orders, capture payments, save raw audio, restart services, deploy,
generate embeddings, or call external APIs.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RULE = ROOT / "docs/operations/XIAOJ_FIELD_PRACTICUM_DUAL_TRACK_RULE.md"


REQUIRED_TEXT = [
    "FIELD_PRACTICUM_DUAL_TRACK_DEFINED",
    "Track A",
    "Live Operation Track",
    "Track B",
    "XiaoJ Shadow Track",
    "candidate-only",
    "尺寸 → 溫度 → 甜度 → 品項",
    "大冰少糖拿鐵",
    "HOLD_REAL_MENU_SOURCE_LOCK",
    "Vietnamese Manager Rule",
    "Xac nhan ban nhap",
    "Khong ghi POS",
    "TRACK_A_LIVE_OPERATION=HUMAN_ONLY",
    "TRACK_B_XIAOJ_SHADOW=CANDIDATE_ONLY",
    "Real menu source is locked",
    "POS order create is human-approved",
    "Payment capture is human-approved",
]

FORBIDDEN_PHRASES = [
    "Track B may create real POS orders",
    "XiaoJ can capture payment",
    "save raw audio",
    "write Odoo DB automatically",
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


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def main() -> int:
    if not RULE.exists():
        fail("rule_missing")
    text = RULE.read_text(encoding="utf-8")
    for required in REQUIRED_TEXT:
        if required not in text:
            fail(f"required_text_missing:{required}")
    for flag in SAFETY_FALSE_FLAGS:
        if flag not in text:
            fail(f"safety_flag_missing:{flag}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            fail(f"forbidden_phrase_present:{phrase}")

    print("STATE=PASS_XIAOJ_FIELD_PRACTICUM_DUAL_TRACK_DEFINED")
    print("ACTION=VERIFY_XIAOJ_FIELD_PRACTICUM_DUAL_TRACK")
    print(f"RULE={RULE.relative_to(ROOT)}")
    print("TRACK_A_LIVE_OPERATION=HUMAN_ONLY")
    print("TRACK_B_XIAOJ_SHADOW=CANDIDATE_ONLY")
    print("VOICE_POS_EXAMPLE=大冰少糖拿鐵")
    print("MENU_SOURCE_GATE=HOLD_REAL_MENU_SOURCE_LOCK")
    print("POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("ODOO_DB_WRITE=FALSE")
    print("RAW_AUDIO_SAVED=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
