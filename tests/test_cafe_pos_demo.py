from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "web/pos_promo_sandbox/index.html"
SCRIPT = ROOT / "web/assets/cafe-pos-demo.js"
DATA = ROOT / "web/assets/cafe-pos-menu-data.js"
STAFF_FLOW = ROOT / "web/assets/cafe-pos-staff-flow.js"
AI_INTENT = ROOT / "web/assets/cafe-pos-ai-intent.js"
STYLE = ROOT / "web/assets/cafe-pos-demo.css"

FORBIDDEN_PUBLIC_COPY = (
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


class CafePosParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.buttons = 0
        self.links: list[str] = []
        self.scripts: list[str] = []
        self.stylesheets: list[str] = []
        self.meta: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: str(value) for key, value in attrs if value is not None}
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "button":
            self.buttons += 1
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        if tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.stylesheets.append(values["href"])
        if tag == "meta":
            self.meta.append(values)


class CafePosDemoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.script = SCRIPT.read_text(encoding="utf-8")
        cls.data_script = DATA.read_text(encoding="utf-8")
        cls.staff_script = STAFF_FLOW.read_text(encoding="utf-8")
        cls.ai_script = AI_INTENT.read_text(encoding="utf-8")
        cls.menu_data = json.loads(
            cls.data_script.split("Object.freeze(\n", 1)[1].rsplit("\n  );", 1)[0]
        )
        cls.style = STYLE.read_text(encoding="utf-8")
        cls.parser = CafePosParser()
        cls.parser.feed(cls.page)

    def test_brand_product_and_business_boundary_are_explicit(self) -> None:
        for marker in (
            "上品聊國咖啡館",
            "商業管理系統展示、除錯與優化驗證",
            "business.wuchang.life",
            "雲端權威菜單 · 合成交易",
            "總場封印之 QuickClick 雲端原始匯出",
            "58 筆啟用／64 筆來源",
            "依商品策略停用 6 筆濾掛咖啡",
            "咖啡飲品細分為「義式咖啡」與「單品手沖」",
            "人說一句，系統只填來源候選",
            "人類端採 Odoo 操作契約",
            "AI 端採 ADI 固定候選索引展示",
            "兩者最後都送入同一總場整流器",
            "未載入 LLM、無網路傳送、無自動送單",
            "不建立真實訂單",
            "不扣款",
            "不讀會員明文",
            "不寫入 production DB",
            "8D 候選封套",
            "HOLD · FORMAL POS RELEASE",
            "L3 candidate reconstruction",
            "常駐紅隊觀點",
            "匿名記杯演練",
            "離線候選佇列",
            "未來 LLM 僅在使用者設備形成候選",
            "伺服器不執行 LLM",
            "這不是一般咖啡店促銷頁",
            "新北市三重區五常社區發展協會",
            "數位系統開發團隊所進行的公開測試場域",
            "待協會完成法人化",
            "少部分發明人授權金",
            "社區數位發展基金",
            "以商以智養公益、以商養公",
            "以 AI 科技抵禦 AI 時代的衝擊，以科技服務社區",
            "不是募款、投資邀請或收益保證",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.page)

    def test_page_is_not_a_nonprofit_landing_or_ad_destination(self) -> None:
        self.assertIn('<meta name="robots" content="noindex,nofollow,noarchive">', self.page)
        self.assertIn('<link rel="canonical" href="https://business.wuchang.life/">', self.page)
        self.assertNotIn('href="https://wuchang.life/"', self.page)
        self.assertNotIn("立即測試生成式傳輸", self.page)

    def test_no_collection_payment_or_server_runtime_surface(self) -> None:
        self.assertIn("connect-src 'none'", self.page)
        self.assertIn("form-action 'none'", self.page)
        for forbidden in (
            "<form",
            "fetch(",
            "XMLHttpRequest",
            "localStorage",
            "sessionStorage",
            "Date.now",
            "new Date",
            "Math.random",
            "onclick=",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    self.page + self.script + self.data_script + self.staff_script + self.ai_script,
                )
        self.assertNotRegex(self.script + self.data_script + self.staff_script + self.ai_script, r"https?://")
        self.assertNotRegex(
            self.page + self.script + self.data_script + self.staff_script + self.ai_script,
            r"sk-[A-Za-z0-9_-]{12,}",
        )

    def test_quickclick_cloud_menu_and_guardrails_are_deterministic(self) -> None:
        for marker in (
            "QUICKCLICK_RAW_XLSX_READ_ONLY",
            "source_row_count: MENU_DATA.source.sourceProductCount",
            "active_row_count: MENU_DATA.source.activeProductCount",
            "excluded_row_count: MENU_DATA.source.excludedProductCount",
            "SYN-SHIFT-07",
            "SYN-CUP-014",
            "formal_pos_order: false",
            "payment_capture: false",
            "member_plaintext: false",
            "db_write: false",
            "server_llm: false",
            "ai_auto_submit: false",
            "canonicalJson",
            'digest("SHA-256"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.script)
        source = self.menu_data["source"]
        self.assertEqual(source["sha256"], "18798f9fe998b68bbe1ff168110ef2521c03404ff0950730b729823e13086109")
        self.assertEqual(source["sourceProductCount"], 64)
        self.assertEqual(source["activeProductCount"], 58)
        self.assertEqual(source["excludedProductCount"], 6)
        self.assertEqual(source["excludedSourceCategories"], ["濾掛咖啡"])
        self.assertEqual(
            self.menu_data["categories"],
            [
                {"id": "coffee", "label": "咖啡飲品"},
                {"id": "tea-other", "label": "茶與無咖啡因"},
                {"id": "food", "label": "餐食與點心"},
                {"id": "beans", "label": "咖啡豆"},
                {"id": "drip", "label": "濾掛咖啡"},
            ],
        )
        products = self.menu_data["products"]
        self.assertEqual(len(products), 58)
        self.assertEqual(len({product["id"] for product in products}), 58)
        self.assertEqual(len({product["sourceRef"] for product in products}), 58)
        self.assertEqual(self.menu_data["adi"]["state"], "DEMO_FIXED_CANDIDATE_ONLY")
        self.assertEqual(self.menu_data["adi"]["productionState"], "HOLD_ADI_NOT_CONFIGURED")
        self.assertEqual(len(self.menu_data["adi"]["candidateRefs"]), 58)
        self.assertEqual(self.menu_data["surfaces"]["human"]["system"], "ODOO")
        self.assertEqual(self.menu_data["surfaces"]["ai"]["system"], "ADI")
        self.assertEqual(
            self.menu_data["surfaces"]["ai"]["llmExecution"],
            "USER_DEVICE_ONLY",
        )
        self.assertFalse(self.menu_data["surfaces"]["ai"]["serverLlm"])
        self.assertEqual(
            self.menu_data["surfaces"]["convergence"]["system"],
            "TOTAL_FIELD_RECTIFIER",
        )
        self.assertNotIn("濾掛咖啡", {product["sourceCategory"] for product in products})
        by_id = {product["id"]: product for product in products}
        self.assertEqual(by_id["P_49180031"]["name"], "招牌咖啡")
        self.assertEqual(by_id["P_49180031"]["optionGroupIds"], ["O7835309"])
        self.assertEqual(by_id["P_49180031"]["sourceRef"], "QUICKCLICK:M387676:P_49180031")
        self.assertEqual(by_id["P_49180073"]["name"], "美式黑咖啡")
        self.assertEqual(by_id["P_49180052"]["name"], "貝果")
        for unsupported in (
            "SYN-ESPRESSO",
            "SYN-LATTE",
            "SYN-TEA",
            "SYN-MILKTEA",
            "SYN-TOAST",
            "SYN-SANDWICH",
            "上品經典咖啡",
            "醇香拿鐵",
            "桂香紅茶",
            "田園三明治",
            "哥倫比亞",
            "巴西喜拉多",
            "瓜地馬拉",
            "薩爾瓦多",
        ):
            with self.subTest(unsupported=unsupported):
                self.assertNotIn(unsupported, self.data_script)
        groups = {group["id"]: group for group in self.menu_data["optionGroups"]}
        self.assertEqual(len(groups), 21)
        self.assertEqual([q["name"] for q in groups["O7835309"]["questions"]], ["尺寸", "溫度", "甜度"])
        self.assertIn("貝果口味", [q["name"] for q in groups["O7835315"]["questions"]])

    def test_staff_and_ai_files_converge_on_one_configuration_flow(self) -> None:
        for marker in (
            "WUCHANG_CAFE_POS_TOTAL_FIELD_RECTIFIER",
            'surface: "TOTAL_FIELD_RECTIFIER"',
            "normalizeConfiguration",
            'code: "SOURCE_CONFIGURATION_VERIFIED"',
            'code: "REQUIRED_OPTION_MISSING"',
            "lineKey",
        ):
            self.assertIn(marker, self.staff_script)
        for marker in (
            "WUCHANG_CAFE_POS_AI_INTENT",
            "productsFromAdi",
            'surface: "ADI_AI"',
            "NEEDS_HUMAN_SELECTION",
            "READY_FOR_HUMAN_CONFIRMATION",
            "product.sourceRef",
        ):
            self.assertIn(marker, self.ai_script)
        self.assertIn("AI_INTENT.resolve(textValue, MENU_DATA, RECTIFIER)", self.script)
        self.assertIn("RECTIFIER.normalizeConfiguration(MENU_DATA, product.id, rawSelections)", self.script)
        self.assertIn("total_field_rectifier", self.script)
        self.assertIn("questionCoordinate", self.staff_script)
        self.assertIn("optionCoordinate", self.staff_script)
        self.assertNotIn("state.cart.push", self.ai_script)
        self.assertNotIn("payment", self.ai_script.lower())

    def test_user_device_llm_guard_blocks_taiji01_execution_contract(self) -> None:
        source = (
            ROOT / "tools/total_field/cafe_pos_local_llm_acceptance.py"
        ).read_text(encoding="utf-8")
        for marker in (
            'BLOCKED_SERVER_HOSTS = {"taiji01"}',
            '"HOLD_USER_DEVICE_LLM_REQUIRED"',
            '"server_llm": False',
            '"USER_DEVICE_LOOPBACK_ONLY"',
            '"USER_DEVICE_LLM_TEST"',
        ):
            self.assertIn(marker, source)

    def test_all_product_transitions_recheck_redteam(self) -> None:
        for transition in (
            'evaluateRedteam("PRODUCT_ADD")',
            'evaluateRedteam("CATEGORY_VIEW")',
            'evaluateRedteam("CART_LINE_CHANGE")',
            'evaluateRedteam("MODIFIER_CHANGE")',
            'evaluateRedteam("OPTION_SELECTION")',
            'evaluateRedteam("INTENT_PARSE")',
            'evaluateRedteam("CANDIDATE_BUILD")',
            'evaluateRedteam("STAFF_REVIEW")',
            'evaluateRedteam("QUEUE_CANDIDATE")',
            'evaluateRedteam("PAYMENT_BOUNDARY_TEST", "HOLD_PAYMENT_CAPTURE_FORBIDDEN")',
            'evaluateRedteam("CUP_REDEEM_REQUEST")',
            'evaluateRedteam("CUP_REDEEM_CONFIRM")',
        ):
            with self.subTest(transition=transition):
                self.assertIn(transition, self.script)
        self.assertIn('evaluateRedteam(state.offline ? "OFFLINE_ENTER" : "LINK_RESTORED")', self.script)
        self.assertIn('data-state="MONITORING_CLEAR"', self.page)
        self.assertIn("DRIFT_ALERT", self.script)

    def test_interaction_contract_has_known_dom_targets(self) -> None:
        required = {
            "main",
            "menu-grid",
            "cart-lines",
            "cart-count",
            "cart-total",
            "build-candidate",
            "staff-review",
            "queue-candidate",
            "test-payment-boundary",
            "candidate-hash",
            "packet-d8",
            "cafe-redteam-monitor",
            "redteam-state",
            "redteam-cycle",
            "cup-remaining",
            "request-redeem",
            "confirm-redeem",
            "toggle-offline",
            "event-log",
            "announcement",
            "intent-input",
            "parse-intent",
            "intent-status",
            "item-configurator",
            "option-questions",
            "confirm-config",
            "cancel-config",
        }
        self.assertTrue(required.issubset(self.parser.ids))
        self.assertGreaterEqual(self.parser.buttons, 15)
        self.assertGreaterEqual(self.page.count('role="tablist"'), 2)
        self.assertIn('aria-live="polite"', self.page)
        referenced = set(re.findall(r'byId\("([a-z0-9-]+)"\)', self.script))
        self.assertEqual(sorted(referenced - self.parser.ids), [])

    def test_externalized_assets_exist_and_style_is_responsive(self) -> None:
        self.assertEqual(
            self.parser.scripts,
            [
                "../assets/cafe-pos-menu-data.js",
                "../assets/cafe-pos-staff-flow.js",
                "../assets/cafe-pos-ai-intent.js",
                "../assets/cafe-pos-demo.js",
            ],
        )
        self.assertEqual(self.parser.stylesheets, ["../assets/cafe-pos-demo.css"])
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(DATA.is_file())
        self.assertTrue(STAFF_FLOW.is_file())
        self.assertTrue(AI_INTENT.is_file())
        self.assertTrue(STYLE.is_file())
        for marker in (
            "@media (max-width: 1180px)",
            "@media (max-width: 760px)",
            "@media (prefers-reduced-motion: reduce)",
            ":focus-visible",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.style)

    def test_forbidden_public_copy_is_absent(self) -> None:
        for phrase in FORBIDDEN_PUBLIC_COPY:
            with self.subTest(phrase=phrase):
                self.assertNotIn(
                    phrase,
                    self.page + self.script + self.data_script + self.staff_script + self.ai_script,
                )


if __name__ == "__main__":
    unittest.main()
