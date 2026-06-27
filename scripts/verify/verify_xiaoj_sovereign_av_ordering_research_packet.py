#!/usr/bin/env python3
"""Verify the docs-only XiaoJ sovereign AV ordering research packet."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs/total_field/XIAOJ_SOVEREIGN_AV_ORDERING_ARCH.md"
BROKER = ROOT / "docs/total_field/XIAOJ_GOOGLE_SPEECH_BROKER_SPEC.md"
GATE = ROOT / "docs/total_field/XIAOJ_D8_PREFLIGHT_AND_RELEASE_GATE.md"
ROADMAP = ROOT / "docs/product/XIAOJ_AV_ORDERING_MVP_ROADMAP.md"
REPORT = ROOT / "runtime/d8_db/reports/XIAOJ_SOVEREIGN_AV_ORDERING_RESEARCH_PACKET_FINAL_REPORT.json"
SEAL = ROOT / "runtime/total_field/status/XIAOJ_SOVEREIGN_AV_ORDERING_RESEARCH_PACKET_SEAL.md"

FILES = [ARCH, BROKER, GATE, ROADMAP, REPORT, SEAL]

REQUIRED = {
    ARCH: [
        "two-layer sovereignty architecture",
        "Ref-only",
        "candidate_action",
        "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED",
        "HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED",
    ],
    BROKER: [
        "association-authorized local broker",
        "must not directly hold primary cloud credentials",
        "transcript is never transaction truth by itself",
        "EXTERNAL_API_CALL=FALSE",
    ],
    GATE: [
        "Track A live operation: human-only POS",
        "Track B XiaoJ shadow: candidate-only",
        "Menu source lock",
        "Payment",
    ],
    ROADMAP: [
        "real menu source lock",
        "candidate order",
        "no live order",
        "no external API this run",
    ],
    SEAL: [
        "STATE=PASS_XIAOJ_SOVEREIGN_AV_ORDERING_RESEARCH_PACKET_READY",
        "ACTION=XIAOJ_SOVEREIGN_AV_ORDERING_RESEARCH_TO_ARCH_PACKET_DONE",
    ],
}

SAFETY_FLAGS = [
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


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def main() -> int:
    texts = {path: read(path) for path in FILES}
    combined = "\n".join(texts.values())

    for path, required_items in REQUIRED.items():
        text = texts[path]
        for item in required_items:
            if item not in text:
                fail(f"{path.relative_to(ROOT)} missing {item}")

    for flag in SAFETY_FLAGS:
        if flag not in combined:
            fail(f"safety flag missing:{flag}")

    try:
        json.loads(texts[REPORT])
    except json.JSONDecodeError as exc:
        fail(f"report json invalid:{exc}")

    print("STATE=PASS_XIAOJ_SOVEREIGN_AV_ORDERING_RESEARCH_PACKET_READY")
    print("ACTION=VERIFY_XIAOJ_SOVEREIGN_AV_ORDERING_RESEARCH_PACKET")
    print(f"ARCH={ARCH.relative_to(ROOT)}")
    print(f"BROKER={BROKER.relative_to(ROOT)}")
    print(f"GATE={GATE.relative_to(ROOT)}")
    print(f"ROADMAP={ROADMAP.relative_to(ROOT)}")
    print(f"REPORT={REPORT.relative_to(ROOT)}")
    print(f"SEAL={SEAL.relative_to(ROOT)}")
    print("ODOO_DB_WRITE=FALSE")
    print("POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("EXTERNAL_API_CALL=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
