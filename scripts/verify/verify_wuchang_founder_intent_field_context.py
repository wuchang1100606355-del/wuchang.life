#!/usr/bin/env python3
"""Verify founder intent context files and public routing."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    ROOT / "web/founder_manifesto/index.html",
    ROOT / "web/assets/homepage-intent-field-hero.png",
    ROOT / "web/assets/homepage-intent-field-hero.webp",
    ROOT / "docs/total_field/WUCHANG_FOUNDER_INTENT_FIELD_CONTEXT_PACKET.md",
    ROOT / "docs/total_field/WUCHANG_FOUNDER_INTENT_FIELD_CONTEXT_PACKET.json",
    ROOT / "web/about/index.html",
    ROOT / "web/sitemap.xml",
]

REQUIRED_SNIPPETS = {
    "web/founder_manifesto/index.html": [
        "平凡的意志，不凡的陣法",
        "本源意圖場 8 維度空間封包拓樸圖",
        "homepage-intent-field-hero.png",
        "PRE_SEAL=REPORT_ONLY",
        "pre_seal_report_only",
        "candidate_only",
    ],
    "docs/total_field/WUCHANG_FOUNDER_INTENT_FIELD_CONTEXT_PACKET.md": [
        "FOUNDER_CONTEXT_SOURCE",
        "總場與各分場",
        "封裝前 report-only",
        "FOUNDER_CONTEXT_ACCEPTED_AS_TOTAL_FIELD_CONTEXT_PACKET",
    ],
    "web/about/index.html": [
        "../founder_manifesto/",
        "創辦人意志",
    ],
    "web/sitemap.xml": [
        "http://wuchang.life/founder_manifesto/",
        "2026-07-04",
    ],
}

FORBIDDEN_PUBLIC_SNIPPETS = [
    "Route payload",
    "raw JSON",
    "safety_flags",
    "SECRET_READ=false",
    "ODOO_DB_WRITE=false",
    "runtime_ready",
    "HOLD_AUTH_PROVIDER_CONFIG_REQUIRED",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    errors: list[str] = []

    for path in REQUIRED_FILES:
        if not path.exists():
            errors.append(f"MISSING_FILE {rel(path)}")

    if errors:
        for error in errors:
            print(error)
        return 1

    for rel_path, snippets in REQUIRED_SNIPPETS.items():
        text = read_text(ROOT / rel_path)
        for snippet in snippets:
            if snippet not in text:
                errors.append(f"MISSING_SNIPPET {rel_path} :: {snippet}")

    founder_page = read_text(ROOT / "web/founder_manifesto/index.html")
    for snippet in FORBIDDEN_PUBLIC_SNIPPETS:
        if snippet in founder_page:
            errors.append(f"FORBIDDEN_PUBLIC_SNIPPET web/founder_manifesto/index.html :: {snippet}")

    about_page = read_text(ROOT / "web/about/index.html")
    for snippet in FORBIDDEN_PUBLIC_SNIPPETS:
        if snippet in about_page:
            errors.append(f"FORBIDDEN_PUBLIC_SNIPPET web/about/index.html :: {snippet}")

    packet = json.loads(read_text(ROOT / "docs/total_field/WUCHANG_FOUNDER_INTENT_FIELD_CONTEXT_PACKET.json"))
    if packet.get("ai_status") != "CANDIDATE_ONLY":
        errors.append("JSON_AI_STATUS_NOT_CANDIDATE_ONLY")
    if packet.get("pre_seal_policy") != "REPORT_ONLY":
        errors.append("JSON_PRE_SEAL_POLICY_NOT_REPORT_ONLY")
    if packet.get("output_gate", {}).get("db_write") != "HOLD":
        errors.append("JSON_DB_WRITE_GATE_NOT_HOLD")
    if packet.get("output_gate", {}).get("public_page_candidate") != "ALLOW_PRE_SEAL_REPORT_ONLY":
        errors.append("JSON_PUBLIC_PAGE_GATE_NOT_ALLOW_REPORT_ONLY")

    if errors:
        for error in errors:
            print(error)
        return 1

    print("STATE=FOUNDER_INTENT_FIELD_CONTEXT_VERIFY_PASS")
    print("FOUNDER_MANIFESTO_PAGE_PRESENT=true")
    print("TOTAL_FIELD_PACKET_PRESENT=true")
    print("MACHINE_PACKET_PRESENT=true")
    print("ABOUT_LINK_PRESENT=true")
    print("SITEMAP_ENTRY_PRESENT=true")
    print("PRE_SEAL_REPORT_ONLY=true")
    print("AI_CANDIDATE_ONLY=true")
    print("PUBLIC_DEBUG_PAYLOAD_REMOVED=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
