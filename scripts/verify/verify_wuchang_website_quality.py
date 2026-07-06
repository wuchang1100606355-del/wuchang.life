#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
ACTIVITY_JSON = WEB / "community_activities.json"

CORE_PAGES = [
    WEB / "index.html",
    WEB / "about" / "index.html",
    WEB / "programs" / "index.html",
    WEB / "method" / "index.html",
    WEB / "founder_manifesto" / "index.html",
    WEB / "member_recruitment" / "index.html",
    WEB / "contact" / "index.html",
]

REQUIRED_SITE_SNIPPETS = [
    "五常社區發展協會｜小J主權AI服務",
    "協會願景",
    "服務預告",
    "技術方法",
    "創辦人宣言",
    "會員招募",
    "聯絡我們",
    "系統資訊",
    "預告版",
    "招募中",
    "部分功能準備中",
]

REQUIRED_HOME_SNIPPETS = [
    "科技善用，在地共好",
    "AI 助力社區，讓生活更美好",
    "本源意圖場 8 維度空間封包拓樸圖",
    "候選服務",
    "verifier",
]

FORBIDDEN_PUBLIC_SNIPPETS = [
    "Route payload",
    "raw JSON",
    "safety_flags",
    "SECRET_READ=false",
    "SECRET_READ=FALSE",
    "ODOO_DB_WRITE=false",
    "ODOO_DB_WRITE=FALSE",
    "runtime_ready",
    "HOLD_AUTH_PROVIDER_CONFIG_REQUIRED",
    "必然核准",
    "已正式流通之金融型幸福幣",
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


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_seen = False
        self.main_seen = False
        self.footer_seen = False
        self.stylesheets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag == "title":
            self.title_seen = True
        if tag == "main":
            self.main_seen = True
        if tag == "footer":
            self.footer_seen = True
        if tag == "link" and attrs_map.get("rel") == "stylesheet":
            href = attrs_map.get("href")
            if href:
                self.stylesheets.append(href)


def fail(message: str) -> None:
    print(f"FAIL={message}")
    print("STATE=HOLD_WUCHANG_WEBSITE_QUALITY")
    print("SECRET_CONTENT_PRINTED=false")
    print("DB_WRITE_EXECUTED=false")
    print("PAYMENT_EXECUTED=false")
    print("DEPLOY_EXECUTED=false")
    sys.exit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def forbid_literals(label: str, text: str) -> None:
    for snippet in FORBIDDEN_PUBLIC_SNIPPETS:
        if snippet in text:
            fail(f"{label} forbidden public snippet: {snippet}")
    for regex, reason in FORBIDDEN_PATTERNS:
        match = regex.search(text)
        if match:
            masked = match.group(0)[:18] + "***"
            fail(f"{label} hard pattern: {reason}: {masked}")


def check_page(path: Path) -> None:
    text = read(path)
    parser = PageParser()
    parser.feed(text)
    label = path.relative_to(ROOT).as_posix()
    if not parser.title_seen:
        fail(f"{label} missing title")
    if not parser.main_seen:
        fail(f"{label} missing main")
    if not parser.footer_seen:
        fail(f"{label} missing footer")
    if not any("wuchang-site-design.css" in href for href in parser.stylesheets):
        fail(f"{label} missing shared stylesheet")
    missing = [snippet for snippet in REQUIRED_SITE_SNIPPETS if snippet not in text]
    if missing:
        fail(f"{label} missing snippets: {missing}")
    forbid_literals(label, text)


def check_activity_json() -> None:
    activity_text = read(ACTIVITY_JSON)
    forbid_literals("activity json", activity_text)
    try:
        activity_data = json.loads(activity_text)
    except json.JSONDecodeError as exc:
        fail(f"activity json invalid: {exc}")
    activities = activity_data.get("activities") or []
    if activity_data.get("public_only") is not True or activity_data.get("member_plaintext_required") is not False:
        fail("activity json public/no-plaintext flags invalid")
    hot_dance = next((item for item in activities if item.get("activity_ref") == "activity_ref:wuchang_park_hot_dance_weekday_2000"), None)
    if not hot_dance:
        fail("missing hot dance public activity seed")
    if hot_dance.get("candidate_only") is not True or hot_dance.get("requires_total_field_verify") is not True:
        fail("hot dance candidate verifier flags invalid")
    if hot_dance.get("member_plaintext_transferred") is not False or hot_dance.get("raw_audio_saved") is not False:
        fail("hot dance sensitive transfer flags invalid")


def main() -> None:
    for page in CORE_PAGES:
        check_page(page)
    home = read(WEB / "index.html")
    missing_home = [snippet for snippet in REQUIRED_HOME_SNIPPETS if snippet not in home]
    if missing_home:
        fail(f"index missing homepage snippets: {missing_home}")
    sitemap = read(WEB / "sitemap.xml")
    if "http://wuchang.life/member_recruitment/" not in sitemap:
        fail("sitemap missing member recruitment page")
    check_activity_json()
    print("STATE=PASS_WUCHANG_WEBSITE_QUALITY")
    print(f"CORE_PAGE_COUNT={len(CORE_PAGES)}")
    print("PUBLIC_ENTRY=web/index.html")
    print("PUBLIC_ACTIVITY_CACHE=web/community_activities.json")
    print("SECRET_CONTENT_PRINTED=false")
    print("DB_WRITE_EXECUTED=false")
    print("PAYMENT_EXECUTED=false")
    print("DEPLOY_EXECUTED=false")


if __name__ == "__main__":
    main()
