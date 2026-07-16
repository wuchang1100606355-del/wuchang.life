#!/usr/bin/env python3
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"

CORE_PAGES = [
    WEB / "index.html",
    WEB / "about" / "index.html",
    WEB / "programs" / "index.html",
    WEB / "method" / "index.html",
    WEB / "founder_manifesto" / "index.html",
    WEB / "member_recruitment" / "index.html",
    WEB / "contact" / "index.html",
]

REQUIRED_TEXT = [
    "五常社區發展協會｜小J主權AI服務",
    "首頁",
    "協會願景",
    "服務預告",
    "技術方法",
    "創辦人宣言",
    "會員招募",
    "聯絡我們",
    "系統資訊",
    "公開資訊",
    "內容持續更新",
    "服務狀態透明揭露",
]

FORBIDDEN_PUBLIC_PAYLOAD = [
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

REQUIRED_ASSETS = [
    WEB / "assets" / "wuchang-site-design.css",
    WEB / "assets" / "homepage-intent-field-hero.png",
    WEB / "assets" / "homepage-intent-field-hero.webp",
    WEB / "assets" / "community-vision-art.svg",
    WEB / "assets" / "community-vision-art-card.svg",
    WEB / "assets" / "founder-journey-night-study.svg",
    WEB / "assets" / "wuchang-og-card.png",
]


class SanityParser(HTMLParser):
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
    raise SystemExit(f"VERIFY_WUCHANG_PUBLIC_SITE_DESIGN_FAIL: {message}")


def check_page(path: Path) -> None:
    if not path.exists():
        fail(f"missing page: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    parser = SanityParser()
    parser.feed(text)
    if not parser.title_seen:
        fail(f"missing title: {path.relative_to(ROOT)}")
    if not parser.main_seen:
        fail(f"missing main: {path.relative_to(ROOT)}")
    if not parser.footer_seen:
        fail(f"missing footer: {path.relative_to(ROOT)}")
    if not any("wuchang-site-design.css" in href for href in parser.stylesheets):
        fail(f"missing shared stylesheet: {path.relative_to(ROOT)}")
    for required in REQUIRED_TEXT:
        if required not in text:
            fail(f"missing text {required!r}: {path.relative_to(ROOT)}")
    for forbidden in FORBIDDEN_PUBLIC_PAYLOAD:
        if forbidden in text:
            fail(f"forbidden public payload {forbidden!r}: {path.relative_to(ROOT)}")


def main() -> None:
    for asset in REQUIRED_ASSETS:
        if not asset.exists():
            fail(f"missing asset: {asset.relative_to(ROOT)}")
    for page in CORE_PAGES:
        check_page(page)
    sitemap = WEB / "sitemap.xml"
    if "https://wuchang.life/member_recruitment/" not in sitemap.read_text(encoding="utf-8"):
        fail("sitemap missing member_recruitment")
    print("VERIFY_WUCHANG_PUBLIC_SITE_DESIGN_PASS")
    print(f"CORE_PAGE_COUNT={len(CORE_PAGES)}")
    print("GIT_ADD_EXECUTED=false")
    print("COMMIT_EXECUTED=false")
    print("PUSH_EXECUTED=false")
    print("DEPLOY_EXECUTED=false")
    print("RESTART_EXECUTED=false")


if __name__ == "__main__":
    main()
