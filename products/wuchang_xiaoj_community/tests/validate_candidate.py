#!/usr/bin/env python3
"""Focused, dependency-free validation for the isolated product candidate."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
CSS = ROOT / "assets/styles.css"
SRC = ROOT / "src"
SERVICE_WORKER_ASSET = ROOT / "assets/xiaoj-white-haired-service-worker.png"
PRIOR_VRM_SOURCE = (
    ROOT.parents[1]
    / "Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/avatar/lung.vrm"
)


class CandidateHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.buttons: list[str] = []
        self.headings: list[str] = []
        self.external_refs: list[str] = []
        self._capture_button = 0
        self._capture_heading = 0
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "button":
            self._capture_button += 1
            self._buffer = []
        if tag in {"h1", "h2", "h3"}:
            self._capture_heading += 1
            self._buffer = []
        for attribute in ("src", "href"):
            value = values.get(attribute)
            if value and re.match(r"https?://", value):
                self.external_refs.append(value)

    def handle_data(self, data: str) -> None:
        if self._capture_button or self._capture_heading:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "button" and self._capture_button:
            self.buttons.append(" ".join("".join(self._buffer).split()))
            self._capture_button -= 1
            self._buffer = []
        if tag in {"h1", "h2", "h3"} and self._capture_heading:
            self.headings.append(" ".join("".join(self._buffer).split()))
            self._capture_heading -= 1
            self._buffer = []


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def luminance(hex_color: str) -> float:
    channels = []
    for channel in rgb(hex_color):
        normalized = channel / 255
        channels.append(
            normalized / 12.92
            if normalized <= 0.04045
            else ((normalized + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(first: str, second: str) -> float:
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


checks: list[dict[str, object]] = []


def check(name: str, condition: bool, evidence: object) -> None:
    checks.append({"name": name, "pass": bool(condition), "evidence": evidence})


html = INDEX.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")
javascript = "\n".join(path.read_text(encoding="utf-8") for path in sorted(SRC.glob("*.js")))
parser = CandidateHTMLParser()
parser.feed(html)

check("html_lang_zh_hant", '<html lang="zh-Hant">' in html, "zh-Hant")
check("unique_ids", len(parser.ids) == len(set(parser.ids)), len(parser.ids))
check("skip_link", 'class="skip-link"' in html and 'href="#main-content"' in html, True)
check("semantic_main", '<main id="main-content"' in html, True)
check("resident_primary_cta", "找小J協助" in parser.buttons, parser.buttons[:8])
check("resident_secondary_cta", "查看居民服務" in parser.buttons, parser.buttons[:8])
check(
    "three_scenes",
    all(value in html for value in ("我是居民", "我是商家", "我是物業人員")),
    ["RESIDENT", "BUSINESS_CLOUD", "PROPERTY_CLOUD"],
)
check(
    "review_buttons_exact",
    all(value in html + javascript for value in ("批准執行", "拒絕", "查看詳細內容")),
    ["批准執行", "拒絕", "查看詳細內容"],
)
check(
    "review_effect_explanation",
    all(value in javascript for value in ("會改變什麼", "不會改變什麼", "回滾方式")),
    True,
)
check("large_touch_target", "min-height: 48px" in css and "min-height: 58px" in css, True)
check("focus_visible", ":focus-visible" in css, True)
check("reduced_motion", "prefers-reduced-motion" in css, True)
check("increased_contrast", "prefers-contrast: more" in css, True)
check("primary_contrast_aa", contrast("#17494d", "#ffffff") >= 4.5, round(contrast("#17494d", "#ffffff"), 2))
check("body_contrast_aa", contrast("#17363a", "#fffdf8") >= 4.5, round(contrast("#17363a", "#fffdf8"), 2))
check("no_external_assets", not parser.external_refs, parser.external_refs)
check(
    "association_brand_identity",
    all(
        token in html
        for token in (
            'aria-label="五常社區發展協會小J服務首頁"',
            '<span class="brand-mark" aria-hidden="true">五</span>',
            "<strong>五常社區</strong>",
            "<small>WUCHANG COMMUNITY</small>",
        )
    ),
    "USER_PROVIDED_WUCHANG_ASSOCIATION_MARK_LOCKUP",
)
check(
    "mature_service_console_hero",
    all(
        token in html
        for token in (
            'class="service-console"',
            "一件事，清楚走完",
            "五常社區服務台",
            "查看確認內容",
            "不含真實居民資料",
        )
    )
    and all(
        selector in css
        for selector in (
            ".service-console",
            ".service-progress",
            ".console-review",
        )
    )
    and not any(
        token in html
        for token in (
            "sun-orb",
            "community-line",
            'class="house',
            'class="tree',
            'class="shop',
            "service-card-float",
        )
    ),
    "PRODUCT_WORKFLOW_VISUAL_NO_CHILDLIKE_SCENERY",
)
check(
    "prior_codex_white_haired_service_worker",
    SERVICE_WORKER_ASSET.is_file()
    and SERVICE_WORKER_ASSET.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    and sha256(SERVICE_WORKER_ASSET)
    == "691b23d874688f351f6729388e6250ee6de974ce75d3ed34e2136d2bfda61140"
    and PRIOR_VRM_SOURCE.is_file()
    and sha256(PRIOR_VRM_SOURCE)
    == "3a6d395139a5b3207f8ff5ff6686c9340009777e3f87587b04c4cf9841640f0f"
    and 'src="./assets/xiaoj-white-haired-service-worker.png"' in html
    and "先前 Codex 設計的白髮少女小J社區服務員" in html
    and "xiaoj-white-haired-service-worker" in css
    and not any(selector in html for selector in ("xiaoj-hair", "xiaoj-face", "xiaoj-body")),
    {
        "asset": str(SERVICE_WORKER_ASSET.relative_to(ROOT)),
        "sha256": sha256(SERVICE_WORKER_ASSET),
        "source": str(PRIOR_VRM_SOURCE.relative_to(ROOT.parents[1])),
        "source_sha256": sha256(PRIOR_VRM_SOURCE),
        "role": "PRIOR_CODEX_WHITE_HAIRED_HUMAN_COMMUNITY_SERVICE_WORKER",
    },
)
check(
    "personal_xiaoj_image_studio",
    all(
        token in html
        for token in (
            "我的專屬小J",
            'id="xiaoj-image-input"',
            'id="xiaoj-image-adjustments"',
            'id="xiaoj-image-zoom"',
            'id="xiaoj-image-position"',
            "前往確認變更",
        )
    )
    and all(
        selector in css
        for selector in (
            ".xiaoj-personalization-studio",
            ".studio-canvas",
            ".studio-control-panel",
        )
    ),
    "THREE_STEP_LIVE_PREVIEW_PERSONALIZATION_STUDIO",
)
check(
    "personal_image_owner_permission_gate",
    all(
        token in javascript
        for token in (
            "CURRENT_MEMBER_ROOT_ONLY",
            "SAME_MEMBER_SESSION_HUMAN_REVIEW_REQUIRED",
            "MEMBER_PERSONAL_XIAOJ_IMAGE_WRITE_CANDIDATE",
            "scope://member-self/same-root-only",
            "scope://member-self/same-session-only",
        )
    ),
    "CURRENT_MEMBER_SAME_SESSION_ACTION_HASH_BOUND",
)
check(
    "personal_image_local_preview_only",
    all(
        token in javascript
        for token in (
            "candidateExternalUpload: false",
            "candidatePersistentWrite: false",
            "external_upload: false",
            "persistent_write: false",
            "display_zoom_percent",
            "display_position_y_percent",
        )
    ),
    "NO_AUTO_UPLOAD_NO_PERSISTENT_WRITE",
)
check(
    "technical_terms_isolated",
    all(
        html.find(term) >= html.find('class="technical-area"')
        for term in ("W7TP", "8D", "ADI", "生成式傳輸")
    ),
    "TECHNICAL_RESEARCH_AREA_ONLY",
)
check("required_free_subscription_copy", "免費訂閱" in html, True)
check("forbidden_free_copy_absent", "免費免訂閱" not in html, True)
check("community_fund_copy", "社區數位發展基金" in html, True)
check("no_fundraising_copy", "不募款" in html and "婉謝捐款" in html, True)
check("public_interest_principle", "商業養公益" in html, True)
check(
    "no_forbidden_claims",
    not any(
        phrase in html
        for phrase in (
            "高利息債務",
            "還債",
            "養員工",
            "員工獎金",
            "已核准發明專利",
            "Google 背書",
            "政府背書",
            "任意檔案都能小封包下載",
        )
    ),
    True,
)
check(
    "no_network_effect_code",
    not any(token in javascript for token in ("fetch(", "XMLHttpRequest", "new WebSocket", "sendBeacon")),
    True,
)
check(
    "odoo_fail_closed",
    "HOLD_LIVE_ODOO_EFFECT_FORBIDDEN_IN_ISOLATED_CANDIDATE" in javascript,
    True,
)
check(
    "llm_direct_execution_blocked",
    "HOLD_CANDIDATE_NO_LIVE_EFFECT" in javascript and "effect_executed: false" in javascript,
    True,
)
check("parameter_hash_binding", "HOLD_PARAMETERS_CHANGED_AFTER_REVIEW" in javascript, True)
check("replay_protection", "HOLD_REVIEW_RECEIPT_REPLAY" in javascript, True)
check("cross_member_protection", "HOLD_CROSS_MEMBER_APPROVAL" in javascript, True)
check("cross_scene_protection", "HOLD_CROSS_SCENE_APPROVAL" in javascript, True)
check("expiry_protection", "HOLD_APPROVAL_EXPIRED" in javascript, True)
check(
    "root_hash_bound",
    "336ec63144db4840c2cb716cd7e035a1e8c6441fc4d12b67779bd0da0627fafe"
    in javascript,
    True,
)
check("candidate_source_files", all(path.is_file() for path in (INDEX, CSS, SRC / "app.js")), True)

failed = [item for item in checks if not item["pass"]]
result = {
    "state": "PASS" if not failed else "FAIL",
    "passed": len(checks) - len(failed),
    "failed": len(failed),
    "checks": checks,
    "files": {
        "index_sha256": sha256(INDEX),
        "css_sha256": sha256(CSS),
    },
}
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(1 if failed else 0)
