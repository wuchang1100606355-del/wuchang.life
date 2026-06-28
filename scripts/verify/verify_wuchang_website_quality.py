#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "web" / "index.html"
QUALITY_DOC = ROOT / "docs" / "website" / "WUCHANG_ASSOCIATION_WEBSITE_QUALITY_UPGRADE.md"
ROLE_MAP_DOC = ROOT / "docs" / "website" / "WUCHANG_ASSOCIATION_PLATFORM_ROLE_MAP.md"
ACTIVITY_JSON = ROOT / "web" / "community_activities.json"


REQUIRED_INDEX_SNIPPETS = [
    '<html lang="zh-Hant">',
    '<meta name="viewport"',
    'href="#main">跳到主要內容</a>',
    '讓社區成為守護家的公共力量',
    '協會願景形象頁',
    '六大平台入口',
    '商業聯合銷售平台',
    '物業管理平台',
    '會員登入平台',
    '社區許願樹平台',
    '社區幣/票券兌換平台',
    '社區活動平台',
    '熱舞社運動社團',
    '每週一至週五 20:00-21:00',
    '五常公園',
    '社區婦女',
    'SECRET_READ=FALSE',
    'MEMBER_PLAINTEXT_READ=FALSE',
    'RAW_API_KEY_OUTPUT=FALSE',
    'DB_WRITE=FALSE',
    'PAYMENT_CAPTURE=FALSE',
    'DEPLOY=FALSE',
]

REQUIRED_ROUTES = [
    'href="/shop"',
    'href="/web"',
    'href="/google/member/login"',
    'href="/wuchang/tickets"',
]

REQUIRED_DOC_SNIPPETS = [
    "Six Platform Roles",
    "Commercial joint sales",
    "Property management",
    "Member login",
    "Community wish tree",
    "Community coin / ticket exchange",
    "Community activity",
    "五常公園熱舞社運動社團",
    "每週一至週五 20:00-21:00",
]

REQUIRED_ROLE_MAP_SNIPPETS = [
    "協會願景形象首頁",
    "商業聯合銷售平台",
    "物業管理平台",
    "會員登入平台",
    "社區許願樹平台",
    "社區幣/票券兌換平台",
    "社區活動平台",
    "web/community_activities.json",
    "activity_rsvp_candidate",
    "candidate_only=true",
    "requires_total_field_verify=true",
    "member_plaintext_transferred=false",
]

FORBIDDEN_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_-]{12,}"), "openai-like secret literal"),
    (re.compile(r"(?i)(oauth|token|password|api[_ -]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]"), "secret assignment literal"),
    (re.compile(r"SECRET_READ=TRUE"), "SECRET_READ true"),
    (re.compile(r"MEMBER_PLAINTEXT_READ=TRUE"), "MEMBER_PLAINTEXT_READ true"),
    (re.compile(r"RAW_API_KEY_OUTPUT=TRUE"), "RAW_API_KEY_OUTPUT true"),
    (re.compile(r"RAW_AUDIO_SAVED=TRUE"), "RAW_AUDIO_SAVED true"),
    (re.compile(r"DB_WRITE=TRUE"), "DB_WRITE true"),
    (re.compile(r"PAYMENT_CAPTURE=TRUE"), "PAYMENT_CAPTURE true"),
    (re.compile(r"DEPLOY=TRUE"), "DEPLOY true"),
]


def fail(message: str) -> None:
    print(f"FAIL={message}")
    print("STATE=HOLD_WUCHANG_WEBSITE_QUALITY")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RAW_API_KEY_OUTPUT=FALSE")
    print("DB_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("DEPLOY=FALSE")
    sys.exit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require_snippets(label: str, text: str, snippets: list[str]) -> None:
    missing = [snippet for snippet in snippets if snippet not in text]
    if missing:
        fail(f"{label} missing snippets: {missing}")


def forbid_literals(label: str, text: str) -> None:
    for regex, reason in FORBIDDEN_PATTERNS:
        match = regex.search(text)
        if match:
            masked = match.group(0)[:18] + "***"
            fail(f"{label} hard pattern: {reason}: {masked}")


def main() -> None:
    index = read(INDEX)
    quality_doc = read(QUALITY_DOC)
    role_map = read(ROLE_MAP_DOC)
    activity_text = read(ACTIVITY_JSON)
    try:
        activity_data = json.loads(activity_text)
    except json.JSONDecodeError as exc:
        fail(f"activity json invalid: {exc}")

    require_snippets("index", index, REQUIRED_INDEX_SNIPPETS)
    require_snippets("index routes", index, REQUIRED_ROUTES)
    require_snippets("quality doc", quality_doc, REQUIRED_DOC_SNIPPETS)
    require_snippets("role map", role_map, REQUIRED_ROLE_MAP_SNIPPETS)

    forbid_literals("index", index)
    forbid_literals("quality doc", quality_doc)
    forbid_literals("role map", role_map)
    forbid_literals("activity json", activity_text)

    activities = activity_data.get("activities") or []
    if activity_data.get("public_only") is not True or activity_data.get("member_plaintext_required") is not False:
        fail("activity json public/no-plaintext flags invalid")
    hot_dance = next((item for item in activities if item.get("activity_ref") == "activity_ref:wuchang_park_hot_dance_weekday_2000"), None)
    if not hot_dance:
        fail("missing hot dance public activity seed")
    if hot_dance.get("title") != "五常公園熱舞社運動社團":
        fail("hot dance activity title mismatch")
    if hot_dance.get("location_label") != "五常公園":
        fail("hot dance location mismatch")
    if hot_dance.get("schedule_label") != "每週一至週五 20:00-21:00":
        fail("hot dance schedule mismatch")
    if hot_dance.get("candidate_only") is not True or hot_dance.get("requires_total_field_verify") is not True:
        fail("hot dance candidate verifier flags invalid")
    if hot_dance.get("member_plaintext_transferred") is not False or hot_dance.get("raw_audio_saved") is not False:
        fail("hot dance sensitive transfer flags invalid")

    if index.count("platformCard") < 6:
        fail("index has fewer than six platform cards")

    if "四大平台" in index or "五大平台" in index:
        fail("index still contains old platform count wording")

    print("STATE=PASS_WUCHANG_WEBSITE_QUALITY")
    print("PLATFORM_COUNT=6")
    print("PUBLIC_ENTRY=web/index.html")
    print("PUBLIC_ACTIVITY_CACHE=web/community_activities.json")
    print("ROLE_MAP=docs/website/WUCHANG_ASSOCIATION_PLATFORM_ROLE_MAP.md")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RAW_API_KEY_OUTPUT=FALSE")
    print("DB_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("DEPLOY=FALSE")


if __name__ == "__main__":
    main()
