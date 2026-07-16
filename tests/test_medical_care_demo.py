from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "web/medical_care_demo/index.html"
SCRIPT = ROOT / "web/assets/medical-care-demo.js"
STYLE = ROOT / "web/assets/medical-care-demo.css"


class DemoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.buttons = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(str(values["id"]))
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if tag == "button":
            self.buttons += 1


class MedicalCareDemoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.script = SCRIPT.read_text(encoding="utf-8")
        cls.style = STYLE.read_text(encoding="utf-8")
        cls.parser = DemoParser()
        cls.parser.feed(cls.page)

    def test_product_case_and_partnership_markers_exist(self) -> None:
        for marker in (
            "一次交班，讓醫師、護理師與病人看見同一個照護事實",
            "出院後第 3 日：一個需要被理解、交班與覆核的訊號",
            "醫師視圖",
            "護理視圖",
            "病人視圖",
            "8D 候選封套",
            "ADI 狀態關係層",
            "TW Core IG／FHIR R4",
            "公開招募醫療與護理合作組織",
            "已取得專利相關技術及申請中研發成果",
            "先分清楚「誰正在做什麼」",
            "病人視角",
            "護理師視角",
            "醫師視角",
            "合成工作日：每一步都有負責的人",
            "現在真的可操作",
            "不包裝成已完成",
            "30／60／90 日寫實交付路徑",
            "責任 RACI",
            "授權收入公益回流原則",
            "學術界產學合作、技術移轉與利益回饋",
            "五常社區數位發展基金",
            "透過基金挹注社區",
            "協會依法可支配的淨收入",
            "內部專款、獨立核算、非對外募款",
            "基金專款制度：仍須協會正式決議",
            "LLM 僅限使用者設備",
            "裝置端推論、伺服器端總場",
            "模型只在醫師、護理師或病人實際使用且經授權的設備執行",
            "taiji01 與合作伺服器不執行 LLM",
            "DEVICE-ONLY INFERENCE",
            "目前不載入模型",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.page)

    def test_demo_uses_synthetic_data_and_blocks_clinical_claims(self) -> None:
        for marker in (
            "全合成資料",
            "非臨床服務",
            "不接受真實病人資料",
            "不診斷、不處方、不治療、不分流緊急個案",
            "不是募款、病人招募、臨床試驗招募",
            "第一階段不收真實病歷",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.page)
        for forbidden in (
            "已核准發明專利",
            "政府背書",
            "Google 背書",
            "任意檔案都能小封包下載",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.page)

    def test_demo_is_local_only_and_has_no_collection_surface(self) -> None:
        self.assertIn("connect-src 'none'", self.page)
        self.assertNotIn("<form", self.page)
        self.assertNotIn("fetch(", self.script)
        self.assertNotIn("XMLHttpRequest", self.script)
        self.assertNotIn("localStorage", self.script)
        self.assertNotRegex(self.script, r"https?://")

    def test_interaction_contract_and_accessibility_targets_exist(self) -> None:
        for element_id in (
            "role-doctor",
            "role-nurse",
            "role-patient",
            "role-panel",
            "content-hash",
            "simulate-offline",
            "restore-link",
            "demo-announcement",
            "care-redteam-monitor",
            "care-redteam-state",
            "care-redteam-cycle",
            "redteam-message",
        ):
            with self.subTest(element_id=element_id):
                self.assertIn(element_id, self.parser.ids)
        self.assertGreaterEqual(self.parser.buttons, 9)
        self.assertIn('role="tablist"', self.page)
        self.assertIn('aria-live="polite"', self.page)
        self.assertIn('id="role-patient" role="tab" aria-selected="true"', self.page)
        self.assertIn('let currentRole = "patient"', self.script)
        self.assertIn("link.dataset.perspectiveRole", self.script)
        self.assertIn("prefers-reduced-motion", (ROOT / "web/assets/wuchang-site-design.css").read_text(encoding="utf-8"))
        self.assertIn('data-state="MONITORING_CLEAR"', self.page)
        self.assertIn("常駐紅隊觀點", self.page)
        self.assertIn("不使用伺服器 LLM", self.page)
        for transition in (
            'evaluateRedteam("ROLE_TRANSITION")',
            'evaluateRedteam("EVENT_TRANSITION")',
            'evaluateRedteam(value ? "OFFLINE_QUEUE" : "RELINK_REVALIDATION")',
        ):
            self.assertIn(transition, self.script)

    def test_javascript_only_uses_known_dom_ids(self) -> None:
        referenced = set(re.findall(r'(?:byId|setText)\("([a-z0-9-]+)"', self.script))
        missing = sorted(referenced - self.parser.ids)
        self.assertEqual(missing, [])

    def test_local_links_resolve(self) -> None:
        for href in self.parser.links:
            if not href.startswith("../"):
                continue
            relative = href.split("#", 1)[0]
            target = (PAGE.parent / relative).resolve()
            if relative.endswith("/"):
                target /= "index.html"
            with self.subTest(href=href):
                self.assertTrue(target.exists(), f"missing local link target: {href}")


if __name__ == "__main__":
    unittest.main()
