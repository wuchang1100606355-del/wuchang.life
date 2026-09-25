from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.verify.verify_google_nonprofit_website import _page_file, static_review


ROOT = Path(__file__).resolve().parents[1]
METHOD = ROOT / "web/method/index.html"
CARE_DEMO = ROOT / "web/medical_care_demo/index.html"


class GoogleNonprofitWebsiteReviewTest(unittest.TestCase):
    def test_percent_encoded_internal_evidence_link_resolves_without_path_escape(self) -> None:
        target = _page_file(
            "/evidence/patents/877-24-0046.UTW_%E8%AD%89%E6%9B%B8(3).PDF"
        )
        self.assertEqual(
            target,
            ROOT / "web/evidence/patents/877-24-0046.UTW_證書(3).PDF",
        )
        self.assertTrue(target.is_file())
        self.assertEqual(
            _page_file("/%2e%2e/AGENTS.md"),
            ROOT / "web/__INVALID_INTERNAL_TARGET__",
        )

    def test_all_official_website_policy_criteria_are_individually_reported(self) -> None:
        report = static_review()
        criteria = {
            item["requirement_id"]: item for item in report["criteria"]
        }
        self.assertEqual(report["state"], "PASS_STATIC_WITH_EXTERNAL_EVIDENCE_PENDING")
        self.assertEqual(set(criteria), {f"GNP-WEB-{index:02d}" for index in range(1, 11)})
        self.assertEqual(
            criteria["GNP-WEB-03"]["status"],
            "PASS_MISSION_AND_TOTAL_FIELD_REGISTRATION_PROJECTION",
        )
        self.assertIn(
            "mission_content=PASS",
            criteria["GNP-WEB-03"]["evidence"],
        )
        self.assertIn(
            "legal_registration=PASS_TOTAL_FIELD_PUBLIC_SAFE_PROJECTION",
            criteria["GNP-WEB-03"]["evidence"],
        )
        self.assertIn(
            "annual_report=NOT_FOUND_IN_TOTAL_FIELD_SEARCH_SCOPE",
            criteria["GNP-WEB-03"]["evidence"],
        )
        self.assertEqual(criteria["GNP-WEB-04"]["status"], "PASS_STATIC")
        self.assertEqual(criteria["GNP-WEB-07"]["status"], "PASS_SOURCE_HTTPS")
        self.assertEqual(criteria["GNP-WEB-08"]["status"], "PASS_STATIC_BOUNDARY")
        boundary_evidence = set(criteria["GNP-WEB-08"]["evidence"])
        self.assertIn("legacy_main_domain_sitemap_entries=0", boundary_evidence)
        self.assertIn("legacy_main_domain_internal_links=1", boundary_evidence)
        self.assertIn(
            "legacy_main_domain_internal_link_sources=/method/->/pos_promo_sandbox/",
            boundary_evidence,
        )
        self.assertIn("patent_page_commercial_disclosure=True", boundary_evidence)
        self.assertIn("legacy_main_domain_noindex_failures=0", boundary_evidence)
        self.assertEqual(
            criteria["GNP-WEB-01"]["status"],
            "HOLD_MANUAL_OWNERSHIP_EVIDENCE_REQUIRED",
        )
        self.assertEqual(
            criteria["GNP-WEB-05"]["status"],
            "HOLD_LIVE_PAGESPEED_EVIDENCE_REQUIRED",
        )
        self.assertFalse(
            report["dns_policy_interpretation"][
                "blanket_dns_record_change_prohibition_found"
            ]
        )
        self.assertFalse(
            report["dns_policy_interpretation"]["dns_changed_by_verifier"]
        )

    def test_public_review_copy_matches_current_https_evidence(self) -> None:
        readiness = (ROOT / "web/nonprofit_readiness/index.html").read_text(
            encoding="utf-8"
        )
        transparency = (ROOT / "web/transparency/index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("HTTPS/443 已可公開讀取", readiness)
        self.assertIn("PUBLIC_HTTP_REDIRECT_EDGE_HOLD", readiness)
        self.assertNotIn("TLS/443 尚未配置", readiness)
        self.assertNotIn("仍需完成 HTTPS/TLS", transparency)

    def test_registration_projection_uses_total_field_source_chain(self) -> None:
        home = (ROOT / "web/index.html").read_text(encoding="utf-8")
        transparency = (ROOT / "web/transparency/index.html").read_text(
            encoding="utf-8"
        )
        profile = json.loads(
            (ROOT / "web/data/public_organization_profile.json").read_text(
                encoding="utf-8"
            )
        )
        registration = profile["organization"]["legal_registration"]
        self.assertEqual(registration["value"], "新北市社區補字第1100606355號")
        self.assertEqual(
            registration["status"],
            "VERIFIED_TOTAL_FIELD_PUBLIC_SAFE_PROJECTION",
        )
        self.assertEqual(
            registration["source_sha256"],
            "9b87af6ae15fabaee04e652dfb2eb66306939a886d50e787b942a33670bafef1",
        )
        self.assertIn("EVIDENCE_TOTAL_FIELD_ASSOCIATION_REGISTRATION", home)
        self.assertIn("id=\"legal-registration-evidence\"", transparency)
        self.assertIn("NOT_FOUND_IN_TOTAL_FIELD_SEARCH_SCOPE", transparency)

    def test_business_and_property_legacy_routes_are_not_nonprofit_entrypoints(self) -> None:
        sitemap = (ROOT / "web/sitemap.xml").read_text(encoding="utf-8")
        for route in ("/property_management/", "/pos_promo_sandbox/"):
            with self.subTest(route=route):
                self.assertNotIn(f"https://wuchang.life{route}", sitemap)

        for relative in ("web/property_management/index.html", "web/pos_promo_sandbox/index.html"):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn('content="noindex,nofollow,noarchive"', source)

        for relative in (
            "web/governance/index.html",
            "web/total_field_review/index.html",
            "web/total_field_review/envelope.html",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("../property_management/", source)
            self.assertNotIn("../pos_promo_sandbox/", source)

    def test_method_page_serves_zero_network_and_frontier_readers(self) -> None:
        source = METHOD.read_text(encoding="utf-8")
        for marker in (
            "完全不懂網路，也能先懂這四步",
            "L1／L2／L3 不是畫質等級",
            "把算力、傳輸與裁決權拆開",
            "離線 L3 edge 與 hash-chain queue",
            "電信業",
            "雲端產業",
            "政府與公共服務機構",
            "醫師專用 AI 服務",
            "ADI 張量狀態資料庫",
            "失敗案例成為紅隊告警",
            "註冊與本人病歷連結",
            "醫囑提醒",
            "詳細病程查找",
            "讓專業知識成為醫師與病人溝通的橋樑與基石",
            "TW Core IG／FHIR R4",
            "專利技術如何落地：進入商業公開測試",
            "操作上品聊國咖啡館 POS 公開測試",
            'href="../pos_promo_sandbox/"',
            "與協會非營利首頁分流",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)
        self.assertNotIn("政府背書", source)
        self.assertNotIn("已核准發明專利", source)

    def test_medical_care_demo_is_in_nonprofit_review_scope(self) -> None:
        report = static_review()
        self.assertIn("/medical_care_demo/", report["review_scope"])
        self.assertTrue(CARE_DEMO.exists())


if __name__ == "__main__":
    unittest.main()
