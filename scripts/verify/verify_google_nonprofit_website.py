#!/usr/bin/env python3
"""Evidence-oriented Google for Nonprofits website policy verifier.

Google retains approval discretion. This tool separates directly testable
website requirements from facts that require human/legal evidence and from
external PageSpeed measurements; it never labels those unverified facts PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
CANONICAL_ORIGIN = "https://wuchang.life"
OFFICIAL_POLICY = "https://support.google.com/nonprofits/answer/1657899?hl=zh-Hant"
CORE_PATHS = (
    "/",
    "/about/",
    "/programs/",
    "/method/",
    "/medical_care_demo/",
    "/founder_manifesto/",
    "/member_recruitment/",
    "/contact/",
    "/transparency/",
)
BOUNDARY_AUDIT_PATHS = CORE_PATHS + (
    "/governance/",
    "/total_field_review/",
    "/total_field_review/envelope.html",
)
LEGACY_MAIN_DOMAIN_ROUTES = (
    "/property_management/",
    "/pos_promo_sandbox/",
)
EXPECTED_LEGACY_INTERNAL_LINKS = ("/method/->/pos_promo_sandbox/",)
COMMERCIAL_TEST_DISCLOSURE_MARKERS = (
    "專利技術如何落地：進入商業公開測試",
    "過渡公開測試路徑",
    "business.wuchang.life",
    "與協會非營利首頁分流",
)


MISSION_MARKERS = (
    "五常社區發展協會",
    "以 AI 科技抵禦 AI 時代的衝擊，以科技服務社區",
    "不募款",
    "婉謝捐款",
    "以商以智養公益",
)
COMMERCIAL_BOUNDARY_MARKERS = (
    "商業管理系統展示、除錯與優化驗證",
    "business.wuchang.life",
    "property.wuchang.life",
)
PLACEHOLDER_PATTERNS = (
    re.compile(r"(?i)lorem ipsum"),
    re.compile(r"(?i)under construction"),
    re.compile(r"(?i)placeholder"),
)
AD_PATTERNS = (
    re.compile(r"googlesyndication", re.I),
    re.compile(r"adsbygoogle", re.I),
    re.compile(r"doubleclick\.net", re.I),
    re.compile(r"affiliate[_-]?link", re.I),
)
HTTP_RESOURCE = re.compile(
    r"(?:src|href|content)=[\"']http://(?!www\.w3\.org|www\.sitemaps\.org)[^\"']+",
    re.I,
)
MEDIA_QUERY = re.compile(r"@media\s*\(", re.I)


class PublicPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.text: list[str] = []
        self.viewport = False
        self.canonical: str | None = None
        self.robots: set[str] = set()
        self.in_nav = 0
        self.nav_links: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        if tag == "meta" and values.get("name") == "viewport":
            self.viewport = True
        if tag == "meta" and values.get("name") == "robots":
            content = str(values.get("content") or "")
            self.robots.update(
                token.strip().lower() for token in content.split(",") if token.strip()
            )
        if tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href")
        if tag == "nav":
            self.in_nav += 1
        if tag == "a" and values.get("href"):
            href = str(values["href"])
            self.links.append(href)
            if self.in_nav:
                self.nav_links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
        if tag == "nav" and self.in_nav:
            self.in_nav -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            collapsed = " ".join(data.split())
            if collapsed:
                self.text.append(collapsed)


def _page_file(path: str) -> Path:
    parsed = urlsplit(path)
    relative = parsed.path.lstrip("/")
    if not relative:
        return WEB / "index.html"
    target = WEB / relative
    if parsed.path.endswith("/"):
        target /= "index.html"
    return target


def _load_page(path: str) -> tuple[str, PublicPageParser]:
    target = _page_file(path)
    try:
        source = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"MISSING_OR_INVALID_PAGE:{path}") from exc
    parser = PublicPageParser()
    parser.feed(source)
    return source, parser


def _result(
    requirement_id: str,
    requirement: str,
    status: str,
    evidence: list[str],
    *,
    verification_class: str = "AUTOMATED",
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "official_requirement": requirement,
        "status": status,
        "verification_class": verification_class,
        "evidence": evidence,
    }


def static_review() -> dict[str, Any]:
    pages: dict[str, tuple[str, PublicPageParser]] = {
        path: _load_page(path) for path in CORE_PATHS
    }
    home = pages["/"][0]
    boundary_pages: dict[str, tuple[str, PublicPageParser]] = {
        path: _load_page(path) for path in BOUNDARY_AUDIT_PATHS
    }
    legacy_pages: dict[str, tuple[str, PublicPageParser]] = {
        path: _load_page(path) for path in LEGACY_MAIN_DOMAIN_ROUTES
    }
    all_source = "\n".join(source for source, _parser in boundary_pages.values())
    broken: list[str] = []
    nav_counts: dict[str, int] = {}
    sitemap = (WEB / "sitemap.xml").read_text(encoding="utf-8")
    legacy_sitemap_entries = [
        route
        for route in LEGACY_MAIN_DOMAIN_ROUTES
        if f"{CANONICAL_ORIGIN}{route}" in sitemap
    ]
    legacy_internal_links: list[str] = []
    for page_path, (_source, parser) in boundary_pages.items():
        for href in parser.links:
            parsed = urlsplit(urljoin(CANONICAL_ORIGIN + page_path, href))
            if (
                parsed.hostname in {"wuchang.life", "www.wuchang.life"}
                and parsed.path in LEGACY_MAIN_DOMAIN_ROUTES
            ):
                legacy_internal_links.append(f"{page_path}->{parsed.path}")
    legacy_noindex_failures = [
        route
        for route, (_source, parser) in legacy_pages.items()
        if not {"noindex", "nofollow"}.issubset(parser.robots)
    ]
    text_lengths: dict[str, int] = {}
    text_hashes: set[str] = set()
    canonical_errors: list[str] = []
    mobile_errors: list[str] = []
    placeholder_hits: list[str] = []
    for path, (source, parser) in pages.items():
        visible = " ".join(parser.text)
        text_lengths[path] = len(visible)
        text_hashes.add(hashlib.sha256(visible.encode("utf-8")).hexdigest())
        nav_counts[path] = len(parser.nav_links)
        if not parser.viewport:
            mobile_errors.append(path)
        expected_canonical = CANONICAL_ORIGIN + path
        if parser.canonical != expected_canonical:
            canonical_errors.append(path)
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern.search(visible):
                placeholder_hits.append(f"{path}:{pattern.pattern}")
        for href in parser.links:
            absolute = urljoin(CANONICAL_ORIGIN + path, href)
            parsed = urlsplit(absolute)
            if parsed.scheme not in {"http", "https"}:
                continue
            if parsed.hostname not in {"wuchang.life", "www.wuchang.life"}:
                continue
            if not _page_file(parsed.path).exists():
                broken.append(f"{path}->{parsed.path}")

    stylesheet = (WEB / "assets/wuchang-site-design.css").read_text(encoding="utf-8")
    content_depth_pass = (
        min(text_lengths.values()) >= 700
        and len(text_hashes) == len(CORE_PATHS)
        and not placeholder_hits
    )
    criteria = [
        _result(
            "GNP-WEB-01",
            "The nonprofit owns and controls the ad destination domain.",
            "HOLD_MANUAL_OWNERSHIP_EVIDENCE_REQUIRED",
            ["Canonical domain is wuchang.life; legal/control evidence is not derivable from HTML."],
            verification_class="MANUAL_OR_ACCOUNT_EVIDENCE",
        ),
        _result(
            "GNP-WEB-02",
            "The site contains substantial, unique content related to the mission and activities.",
            "PASS_LOCAL_CONTENT_DEPTH_PROXY" if content_depth_pass else "HOLD_CONTENT_DEPTH_OR_PLACEHOLDER",
            [
                f"core_pages={len(CORE_PATHS)}",
                f"minimum_visible_characters={min(text_lengths.values())}",
                f"unique_visible_text_hashes={len(text_hashes)}",
                f"placeholder_hits={len(placeholder_hits)}",
                "Original authorship still requires organizational attestation.",
            ],
            verification_class="AUTOMATED_PROXY_PLUS_MANUAL_ORIGINALITY",
        ),
        _result(
            "GNP-WEB-03",
            "The mission, activities, services, and served audience are clear and prominent.",
            "PASS" if all(marker in home for marker in MISSION_MARKERS) else "HOLD_MISSION_CONTENT_MISSING",
            [f"marker:{marker}" for marker in MISSION_MARKERS if marker in home],
        ),
        _result(
            "GNP-WEB-04",
            "Navigation is clear and all links and buttons work.",
            "PASS_STATIC" if not broken and min(nav_counts.values()) >= 5 else "HOLD_STATIC_BROKEN_LINK_OR_NAVIGATION",
            [f"broken_internal_targets={len(broken)}", f"minimum_nav_links={min(nav_counts.values())}"] + broken[:20],
        ),
        _result(
            "GNP-WEB-05",
            "Pages load quickly across devices and connection speeds.",
            "HOLD_LIVE_PAGESPEED_EVIDENCE_REQUIRED",
            ["Static source cannot establish field performance; run --live and PageSpeed Insights mobile."],
            verification_class="EXTERNAL_MEASUREMENT_REQUIRED",
        ),
        _result(
            "GNP-WEB-06",
            "The site is mobile friendly and responsive.",
            "PASS_SOURCE_RESPONSIVE" if not mobile_errors and MEDIA_QUERY.search(stylesheet) else "HOLD_MOBILE_SOURCE_BOUNDARY",
            [f"viewport_missing={len(mobile_errors)}", f"responsive_media_query={bool(MEDIA_QUERY.search(stylesheet))}"] + mobile_errors,
            verification_class="AUTOMATED_SOURCE_PLUS_DEVICE_QA_REQUIRED",
        ),
        _result(
            "GNP-WEB-07",
            "The entire site uses HTTPS without mixed content.",
            "PASS_SOURCE_HTTPS" if not HTTP_RESOURCE.search(all_source) and not canonical_errors else "HOLD_HTTP_RESOURCE_OR_CANONICAL",
            [f"http_resource_literals={len(HTTP_RESOURCE.findall(all_source))}", f"canonical_errors={len(canonical_errors)}"] + canonical_errors,
        ),
        _result(
            "GNP-WEB-08",
            "Commercial activity is limited, mission-related, and not the site's primary focus; excessive ads and affiliate routing are prohibited.",
            "PASS_STATIC_BOUNDARY"
            if all(marker in home for marker in COMMERCIAL_BOUNDARY_MARKERS)
            and not any(pattern.search(all_source) for pattern in AD_PATTERNS)
            and not legacy_sitemap_entries
            and sorted(legacy_internal_links) == sorted(EXPECTED_LEGACY_INTERNAL_LINKS)
            and all(marker in pages["/method/"][0] for marker in COMMERCIAL_TEST_DISCLOSURE_MARKERS)
            and not legacy_noindex_failures
            else "HOLD_COMMERCIAL_OR_AD_BOUNDARY",
            [
                "homepage_primary_identity=五常社區發展協會",
                "commercial_operations=demo_debug_optimization_only",
                "commercial_subdomain_plan=business.wuchang.life,property.wuchang.life",
                f"legacy_main_domain_sitemap_entries={len(legacy_sitemap_entries)}",
                f"legacy_main_domain_internal_links={len(legacy_internal_links)}",
                f"legacy_main_domain_internal_link_sources={';'.join(sorted(legacy_internal_links))}",
                "patent_page_commercial_disclosure="
                f"{all(marker in pages['/method/'][0] for marker in COMMERCIAL_TEST_DISCLOSURE_MARKERS)}",
                f"legacy_main_domain_noindex_failures={len(legacy_noindex_failures)}",
                f"third_party_ad_markers={sum(bool(pattern.search(all_source)) for pattern in AD_PATTERNS)}",
            ],
        ),
        _result(
            "GNP-WEB-09",
            "Donation links, if present, work and lead to a dedicated secure donation page.",
            "NOT_APPLICABLE_NO_DONATION_SOLICITATION",
            ["Public policy states 不募款 and 婉謝捐款; no donation checkout is provided."],
        ),
        _result(
            "GNP-WEB-10",
            "Additional ad destination domains require Google Grants approval.",
            "HOLD_ACCOUNT_CONFIGURATION_REVIEW_REQUIRED",
            ["No Google Ads destination configuration was inspected; business/property subdomains are not active homepage links."],
            verification_class="GOOGLE_ACCOUNT_EVIDENCE_REQUIRED",
        ),
    ]
    hard_holds = [
        item["requirement_id"]
        for item in criteria
        if item["status"].startswith("HOLD_")
        and item["verification_class"] in {"AUTOMATED", "AUTOMATED_SOURCE_PLUS_DEVICE_QA_REQUIRED"}
    ]
    report: dict[str, Any] = {
        "schema_version": "WUCHANG-GOOGLE-NONPROFIT-WEBSITE-REVIEW/1.0",
        "official_policy_source": OFFICIAL_POLICY,
        "review_scope": list(CORE_PATHS),
        "state": "PASS_STATIC_WITH_EXTERNAL_EVIDENCE_PENDING" if not hard_holds else "HOLD_STATIC_REQUIREMENT_FAILED",
        "criteria": criteria,
        "hard_hold_ids": hard_holds,
        "disclaimer": "This evidence does not constitute Google approval; Google may approve or reject at its discretion.",
        "commercial_boundary_scope": list(BOUNDARY_AUDIT_PATHS),
    }
    report["content_sha256"] = hashlib.sha256(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return report


def _fetch(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Wuchang-Nonprofit-Website-Policy-Verifier/1.0"},
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(
            request, timeout=timeout, context=ssl.create_default_context()
        ) as response:
            body = response.read(5 * 1024 * 1024 + 1)
            result = {
                "requested_url": url,
                "final_url": response.geturl(),
                "status": response.status,
                "content_type": response.headers.get_content_type(),
                "bytes": len(body),
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "body": body.decode("utf-8", errors="replace"),
            }
    except (OSError, urllib.error.URLError) as exc:
        return {
            "requested_url": url,
            "state": "HOLD_FETCH_FAILED",
            "error_type": type(exc).__name__,
        }
    return result


def live_review(timeout: float = 15.0) -> dict[str, Any]:
    observations = [_fetch(CANONICAL_ORIGIN + path, timeout) for path in CORE_PATHS]
    redirect = _fetch("http://wuchang.life/", timeout)
    failures = [
        item
        for item in observations
        if item.get("status") != 200
        or not str(item.get("final_url", "")).startswith(CANONICAL_ORIGIN)
        or item.get("content_type") != "text/html"
        or HTTP_RESOURCE.search(str(item.get("body", "")))
    ]
    response_sizes = [item["bytes"] for item in observations if "bytes" in item]
    elapsed = [item["elapsed_ms"] for item in observations if "elapsed_ms" in item]
    redirect_pass = str(redirect.get("final_url", "")).startswith(CANONICAL_ORIGIN)
    report: dict[str, Any] = {
        "schema_version": "WUCHANG-GOOGLE-NONPROFIT-LIVE-REVIEW/1.0",
        "official_policy_source": OFFICIAL_POLICY,
        "state": "PASS_LIVE_TRANSPORT_AND_CORE_PAGES" if not failures and redirect_pass else "HOLD_LIVE_WEBSITE_REQUIREMENT",
        "https_redirect": "PASS" if redirect_pass else "HOLD",
        "core_page_failures": len(failures),
        "maximum_elapsed_ms": max(elapsed) if elapsed else None,
        "maximum_html_bytes": max(response_sizes) if response_sizes else None,
        "performance_status": "MEASURED_NOT_PAGESPEED_CERTIFIED",
        "pagespeed_mobile": "HOLD_EXTERNAL_TOOL_EVIDENCE_REQUIRED",
        "observations": [
            {key: value for key, value in item.items() if key != "body"}
            for item in observations
        ],
        "redirect_observation": {
            key: value for key, value in redirect.items() if key != "body"
        },
        "disclaimer": "Live timing is an observation, not a PageSpeed or Google approval result.",
    }
    report["content_sha256"] = hashlib.sha256(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = live_review(args.timeout) if args.live else static_review()
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["state"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
