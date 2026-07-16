from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "web/index.html"
FORBIDDEN_COPY = (
    "免費免訂閱",
    "高利息債務",
    "還債",
    "養員工",
    "員工獎金",
    "已核准發明專利",
    "Google 背書",
    "政府背書",
    "任意檔案都能小封包下載",
)


class HomepageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.meta: dict[str, str] = {}
        self.in_hero_actions = False
        self.first_hero_cta: str | None = None
        self._capture_cta = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "meta" and values.get("name") and values.get("content"):
            self.meta[str(values["name"])] = str(values["content"])
        if tag == "div" and "hero-actions" in str(values.get("class") or "").split():
            self.in_hero_actions = True
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
            if self.in_hero_actions and self.first_hero_cta is None:
                self._capture_cta = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self.in_hero_actions:
            self.in_hero_actions = False
        if tag == "a":
            self._capture_cta = False

    def handle_data(self, data: str) -> None:
        if self._capture_cta:
            value = data.strip()
            if value:
                self.first_hero_cta = value


class WuchangNonprofitHomepageBoundariesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = HOME.read_text(encoding="utf-8")
        cls.parser = HomepageParser()
        cls.parser.feed(cls.html)

    def test_nonprofit_mission_is_prominent_and_first_cta_is_preserved(self) -> None:
        self.assertIn("非營利公開網站", self.parser.meta["description"])
        self.assertIn("以 AI 科技抵禦 AI 時代的衝擊，以科技服務社區", self.html)
        self.assertIn("不募款、婉謝捐款，以商以智養公益", self.html)
        self.assertEqual(self.parser.first_hero_cta, "立即測試生成式傳輸")

    def test_business_and_property_are_demo_only_on_canonical_subdomains(self) -> None:
        self.assertIn("business.wuchang.life", self.html)
        self.assertIn("property.wuchang.life", self.html)
        self.assertIn("商業管理系統展示、除錯與優化驗證", self.html)
        self.assertIn("物業管理示範", self.html)
        self.assertNotRegex(self.html, r'href="https://(?:business|property)\.wuchang\.life')

    def test_unconfigured_planned_subdomains_are_not_broken_links(self) -> None:
        planned = {"member", "association", "community", "business", "property"}
        linked_hosts = {urlsplit(link).hostname for link in self.parser.links if link.startswith("https://")}
        self.assertFalse({f"{name}.wuchang.life" for name in planned}.intersection(linked_hosts))

    def test_core_navigation_targets_exist(self) -> None:
        local_links = [link for link in self.parser.links if link.startswith("./") and "#" not in link]
        for link in local_links:
            target = (ROOT / "web" / link[2:]).resolve()
            if link.endswith("/"):
                target = target / "index.html"
            with self.subTest(link=link):
                self.assertTrue(target.exists(), f"missing local target: {link}")

    def test_forbidden_public_copy_is_absent(self) -> None:
        for phrase in FORBIDDEN_COPY:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.html)

    def test_llm_is_explicitly_device_only(self) -> None:
        self.assertIn("LLM 只在使用者設備", self.html)
        self.assertIn("伺服器不載入模型、不執行推論", self.html)
        self.assertIn("伺服器只提供總場驗證、雜湊與封印", self.html)

    def test_no_secret_like_literal_is_embedded(self) -> None:
        self.assertIsNone(re.search(r"sk-[A-Za-z0-9_-]{12,}", self.html))


if __name__ == "__main__":
    unittest.main()
