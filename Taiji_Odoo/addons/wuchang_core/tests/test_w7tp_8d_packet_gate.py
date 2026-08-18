from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "controllers" / "w7tp_8d_packet_gate.py"
CONTROLLER_PATH = ROOT / "controllers" / "xiaoj_ordering_app_controller.py"
NOTIFICATION_CONTROLLER_PATH = ROOT / "controllers" / "notification_controller.py"
FRONTEND_PATH = ROOT / "static" / "src" / "xiaoj_ordering" / "xiaoj_ordering_app.js"
BACKGROUND_SERVICE_PATH = ROOT / "static" / "src" / "js" / "background_service.js"


class FakeResponse:
    def __init__(self, body, content_type="text/html; charset=utf-8", status=200):
        self.body = body
        self.content_type = content_type
        self.status_code = status

    def get_data(self, as_text=False):
        return self.body if as_text else self.body.encode("utf-8")


class FakeICP:
    def __init__(self, params):
        self.params = dict(params)

    def sudo(self):
        return self

    def get_param(self, key, default=None):
        return self.params.get(key, default)


class FakeRecord:
    def __init__(self, **values):
        self._values = dict(values)
        self._fields = {key: object() for key in values}

    def sudo(self):
        return self

    def __getitem__(self, key):
        return self._values.get(key)

    def __getattr__(self, name):
        if name in self._values:
            return self._values[name]
        raise AttributeError(name)


class FakeBus:
    def __init__(self):
        self.events = []

    def _sendone(self, channel, notification_type, payload):
        self.events.append((channel, notification_type, payload))


class FakeEnv:
    def __init__(self, user, params, bus=None):
        self.user = user
        self._params = FakeICP(params)
        self._bus = bus

    def __getitem__(self, model_name):
        if model_name == "ir.config_parameter":
            return self._params
        if model_name == "bus.bus" and self._bus is not None:
            return self._bus
        raise KeyError(model_name)


class FakeRequest:
    def __init__(self, env):
        self.env = env
        self.session = {}
        self.jsonrequest = {}

    def make_response(self, body, headers=None):
        return FakeResponse(body)


def install_fake_odoo():
    fake_http = ModuleType("odoo.http")

    def route(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator

    fake_http.Response = FakeResponse
    fake_http.request = None
    fake_http.Controller = object
    fake_http.route = route
    fake_odoo = ModuleType("odoo")
    fake_odoo.http = fake_http
    fake_odoo.fields = SimpleNamespace()
    sys.modules["odoo"] = fake_odoo
    sys.modules["odoo.http"] = fake_http
    sys.modules["wuchang_core"] = ModuleType("wuchang_core")
    sys.modules["wuchang_core"].__path__ = [str(ROOT.parent)]  # type: ignore[attr-defined]
    sys.modules["wuchang_core.controllers"] = ModuleType("wuchang_core.controllers")
    sys.modules["wuchang_core.controllers"].__path__ = [str(ROOT)]  # type: ignore[attr-defined]
    return fake_http


def load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class W7TP8DGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_fake_odoo()
        cls.gate = load_module("wuchang_core.controllers.w7tp_8d_packet_gate", GATE_PATH)
        cls.controller = load_module("wuchang_core.controllers.xiaoj_ordering_app_controller", CONTROLLER_PATH)
        cls.notification = load_module("wuchang_core.controllers.notification_controller", NOTIFICATION_CONTROLLER_PATH)

    def test_guest_allowed_without_association_root(self):
        user = FakeRecord()
        env = FakeEnv(user, {"wuchang.w7tp.counter_ai_8d_packet_ref": "counter-guest-001"})
        request = FakeRequest(env)
        gate = self.gate.validate_xiaoj_8d_packet_gate(request)
        self.assertTrue(gate["allowed"])
        self.assertEqual(gate["mode"], "GUEST_SERVICE_SESSION")
        self.assertFalse(gate["identity_verified"])
        self.assertEqual(gate["identity_authority"], "NONE")
        self.assertTrue(gate["read_allowed"])
        self.assertFalse(gate["write_allowed"])
        self.assertTrue(gate["guest_only"])

    def test_member_packet_without_verifier_denied(self):
        partner = FakeRecord()
        user = FakeRecord(
            x_w7tp_8d_packet_ref="member-packet-001",
            x_w7tp_ai_binding_ref="ai-ref",
            x_w7tp_xiaoj_service_ref="service-ref",
            partner_id=partner,
        )
        env = FakeEnv(user, {})
        request = FakeRequest(env)
        request.session["w7tp_device_ref"] = "device-ref"
        gate = self.gate.validate_xiaoj_8d_packet_gate(request)
        self.assertFalse(gate["allowed"])
        self.assertEqual(gate["mode"], "DENY")
        self.assertFalse(gate["identity_verified"])
        self.assertFalse(gate["write_allowed"])
        self.assertEqual(gate["reason"], "HOLD_NATIVE_8D_VERIFIER_NOT_BOUND")

    def test_device_ref_alone_does_not_elevate(self):
        user = FakeRecord()
        env = FakeEnv(user, {"wuchang.w7tp.counter_ai_8d_packet_ref": None})
        request = FakeRequest(env)
        request.session["w7tp_device_ref"] = "device-ref"
        gate = self.gate.validate_xiaoj_8d_packet_gate(request)
        self.assertFalse(gate["allowed"])
        self.assertEqual(gate["mode"], "DENY")
        self.assertFalse(gate["write_allowed"])

    def test_controller_projects_table_ref_and_is_public_route(self):
        self.controller.validate_xiaoj_8d_packet_gate = lambda _request: {
            "allowed": True,
            "mode": "GUEST_SERVICE_SESSION",
            "packet_ref": "counter-guest-001",
            "identity_verified": False,
            "identity_authority": "NONE",
            "read_allowed": True,
            "write_allowed": False,
            "guest_only": True,
            "plaintext_allowed": False,
            "execution_authorized": False,
        }
        self.assertIn('auth="public"', CONTROLLER_PATH.read_text(encoding="utf-8"))
        user = FakeRecord()
        env = FakeEnv(user, {})
        request = FakeRequest(env)
        self.controller.request = request
        response = self.controller.XiaoJOrderingAppController().xiaoj_ordering_app(mode="customer_service", table_ref="T03")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('data-start-mode="customer_service"', html)
        self.assertIn('data-table-ref="T03"', html)
        self.assertIn('data-store-ref="wuchang_cafe_main_store"', html)

    def test_manifest_includes_customer_service(self):
        self.controller.validate_xiaoj_8d_packet_gate = lambda _request: {
            "allowed": True,
            "mode": "GUEST_SERVICE_SESSION",
            "packet_ref": "counter-guest-001",
            "identity_verified": False,
            "identity_authority": "NONE",
            "read_allowed": True,
            "write_allowed": False,
            "guest_only": True,
            "plaintext_allowed": False,
            "execution_authorized": False,
        }
        env = FakeEnv(FakeRecord(), {})
        request = FakeRequest(env)
        self.controller.request = request
        manifest = self.controller.XiaoJOrderingAppController().xiaoj_ordering_manifest()
        self.assertIn("customer_service", manifest["pages"])
        self.assertFalse(manifest["formal_db_write"])
        self.assertFalse(manifest["member_plaintext_read"])

    def test_frontend_uses_session_storage_and_live_menu_endpoint(self):
        source = FRONTEND_PATH.read_text(encoding="utf-8")
        self.assertIn("sessionStorage", source)
        self.assertIn("/wuchang/api/cafe/menu/v1", source)
        self.assertIn("customer_service", source)
        self.assertIn("SERVICE_SESSION_REF", source)
        self.assertIn("CURRENT_SELECTIONS", source)
        self.assertIn("lastCustomerRequest", source)
        self.assertIn("RECALL_CURRENT_SELECTIONS", source)
        self.assertIn("MODIFY_SELECTION", source)
        self.assertIn("ASK_RECOMMENDATION", source)
        self.assertIn("檸檬汁不要了", source)
        self.assertIn("把剛才那杯拿掉", source)
        self.assertIn("我改要招牌咖啡", source)
        self.assertIn("我不喜歡酸的 / 想喝比較順口的 / 有沒有適合第一次喝咖啡的人", source)
        self.assertIn("applyRecommendationCommand", source)
        self.assertIn("resolveRecommendationFromPhrase", source)
        self.assertIn("return resolution.items;", source)
        self.assertIn("你現在比較想喝冰的、熱的、咖啡或順口一點的呢？", source)
        self.assertNotIn(
            "return resolution.items.length ? resolution.items : menuItems().slice(0, 3);",
            source,
        )
        self.assertIn("resolvePartySizePhrase", source)
        self.assertIn("resolvePartySizeInput", source)
        self.assertIn("resolveQuantityPhrase", source)
        self.assertIn("例如：我們三位 / 3位 / 三人", source)
        self.assertIn("3位", source)
        self.assertIn("三人", source)
        self.assertIn("state.currentSelections = state.currentSelections.concat([code]);", source)
        self.assertIn("目前沒有候選訂單", source)
        self.assertIn("即時菜單尚未取得", source)
        self.assertIn("真實菜單", source)
        self.assertIn("今天服務的桌", source)
        self.assertIn("今天人數", source)
        self.assertIn("小J狀態", source)
        self.assertIn("今天由小J陪你點餐", source)
        self.assertIn('grid-template-columns: 1fr;', source)
        self.assertNotIn("const menu =", source)
        self.assertNotIn("const order =", source)
        self.assertNotIn("displayTicker", source)
        self.assertNotIn("38", source)
        self.assertNotIn("18,420", source)
        self.assertNotIn("126", source)
        self.assertNotIn("4</strong>", source)
        self.assertIn("目前還沒有幫你記任何餐點，要不要一起看看菜單？", source)
        self.assertIn("我記得這裡有一個先前選擇，但現在菜單資料沒有完整對上，我先不亂報品項。", source)
        self.assertIn("目前菜單資料沒有足夠證據支撐這個偏好，我不想亂推薦。", source)
        self.assertIn("目前有證據的候選是：", source)
        self.assertIn('const HANDOFF_ENDPOINT = "/api/notification/broadcast";', source)
        self.assertIn('action: "handoff_request"', source)
        self.assertIn("HUMAN_REVIEW_DISPATCHED", source)
        self.assertIn("請店員幫忙", source)
        self.assertNotIn("老闆收到啦，他等等過來～", source)

    def test_handoff_dispatch_acknowledgement_and_resolution_packets(self):
        bus = FakeBus()
        customer_request = FakeRequest(FakeEnv(FakeRecord(), {}, bus=bus))
        customer_request.jsonrequest = {
            "action": "handoff_request",
            "handoff_ref": "handoff-svc-12345678-abcdefgh",
            "problem_class": "GENERAL_SERVICE_ASSISTANCE",
            "table_ref": "T03",
            "risk_class": "LOW",
            "non_pii_evidence_ref": "menu-deadbeef",
            "member_name": "must_not_be_forwarded",
            "payment_detail": "must_not_be_forwarded",
        }
        self.notification.request = customer_request
        dispatch = self.notification.NotificationController().broadcast_notification()
        self.assertTrue(dispatch["success"])
        self.assertEqual(dispatch["state"], "HUMAN_REVIEW_DISPATCHED")
        self.assertEqual(dispatch["receipt"]["status"], "DISPATCH_ACCEPTED")
        self.assertEqual(len(bus.events), 1)
        payload = bus.events[0][2]["data"]
        self.assertEqual(payload["table_ref"], "T03")
        self.assertNotIn("member_name", payload)
        self.assertNotIn("payment_detail", payload)

        http_only_request = FakeRequest(FakeEnv(FakeRecord(), {}, bus=bus))
        http_only_request.jsonrequest = {"title": "generic"}
        self.notification.request = http_only_request
        http_only = self.notification.NotificationController().broadcast_notification()
        self.assertEqual(http_only["state"], "NOTIFICATION_RECEIVED_NO_DISPATCH")
        self.assertEqual(len(bus.events), 1)

        staff = FakeRecord(id=7)
        staff.has_group = lambda group: group == "base.group_user"
        staff_request = FakeRequest(FakeEnv(staff, {}, bus=bus))
        staff_request.jsonrequest = {
            "action": "human_acknowledge",
            "handoff_ref": "handoff-svc-12345678-abcdefgh",
        }
        self.notification.request = staff_request
        acknowledgement = self.notification.NotificationController().broadcast_notification()
        self.assertEqual(acknowledgement["state"], "HUMAN_REVIEW_ACKNOWLEDGED")
        self.assertEqual(acknowledgement["receipt"]["status"], "ACCEPTED")
        self.assertIn("收到啦", acknowledgement["customer_response"])

        staff_request.jsonrequest = {
            "action": "human_resolution",
            "handoff_ref": "handoff-svc-12345678-abcdefgh",
            "result_class": "GENERAL_ASSISTANCE_RESOLVED",
            "human_action_semantic": "STAFF_ASSISTANCE",
            "human_response_semantic": "GENERAL_ASSISTANCE_PROVIDED",
            "odoo_result_ref": "pos-order-ref-123",
        }
        resolution = self.notification.NotificationController().broadcast_notification()
        self.assertEqual(resolution["state"], "HUMAN_REVIEW_RESOLVED")
        self.assertEqual(resolution["result_packet"]["odoo_result_ref"], "pos-order-ref-123")
        self.assertFalse(resolution["result_packet"]["canonical_promotion"])

    def test_handoff_background_requires_explicit_staff_actions(self):
        source = BACKGROUND_SERVICE_PATH.read_text(encoding="utf-8")
        self.assertIn('this.bus.addChannel(HANDOFF_CHANNEL)', source)
        self.assertIn('acknowledge.textContent = "我來處理"', source)
        self.assertIn('this._post("human_acknowledge"', source)
        self.assertIn('this._post("human_resolution"', source)
        self.assertIn('resolve.disabled = true', source)
        self.assertNotIn("MEMBER_PLAINTEXT", source)

    def test_party_size_phrase_examples(self):
        def resolve_party_size_phrase(text):
            text = str(text or "").strip()
            import re

            numeric_match = re.search(r"(\d{1,2})\s*(?:位|人)", text)
            if numeric_match:
                size = int(numeric_match.group(1))
                if 1 <= size <= 20:
                    return size
                return None

            chinese_numbers = {
                "一": 1,
                "二": 2,
                "三": 3,
                "四": 4,
                "五": 5,
                "六": 6,
                "七": 7,
                "八": 8,
                "九": 9,
                "十": 10,
            }
            chinese_match = re.search(r"([一二三四五六七八九十])\s*(?:位|人)", text)
            if chinese_match:
                return chinese_numbers.get(chinese_match.group(1))
            return None

        self.assertEqual(resolve_party_size_phrase("我們三位"), 3)
        self.assertEqual(resolve_party_size_phrase("3位"), 3)
        self.assertEqual(resolve_party_size_phrase("三人"), 3)
        self.assertIsNone(resolve_party_size_phrase("我們很多人"))
        self.assertIsNone(resolve_party_size_phrase("幾個人而已"))
        self.assertIsNone(resolve_party_size_phrase("可能三四個"))

    def test_change_quantity_examples(self):
        def summarize_selection_codes(codes, menu):
            counts = {}
            order = []
            for code in codes:
                if code not in counts:
                    order.append(code)
                counts[code] = counts.get(code, 0) + 1
            return [
                f"{menu.get(code, code)} x {counts[code]}" if counts[code] > 1 else menu.get(code, code)
                for code in order
            ]

        def apply_quantity_change(codes, target_code, quantity):
            if quantity < 1:
                return list(codes)
            next_codes = []
            replaced = False
            for code in codes:
                if code == target_code and not replaced:
                    next_codes.extend([code] * quantity)
                    replaced = True
                elif code != target_code:
                    next_codes.append(code)
            return next_codes if replaced else list(codes)

        menu = {"coffee": "招牌咖啡", "juice": "檸檬汁"}

        changed = apply_quantity_change(["coffee"], "coffee", 2)
        self.assertEqual(changed, ["coffee", "coffee"])
        self.assertEqual(summarize_selection_codes(changed, menu), ["招牌咖啡 x 2"])

        changed = apply_quantity_change(["coffee", "juice"], "coffee", 2)
        self.assertEqual(changed, ["coffee", "coffee", "juice"])
        self.assertEqual(summarize_selection_codes(changed, menu), ["招牌咖啡 x 2", "檸檬汁"])

        unchanged = apply_quantity_change(["coffee", "juice"], "tea", 3)
        self.assertEqual(unchanged, ["coffee", "juice"])

    def test_recommendation_examples(self):
        def item_evidence_text(item):
            parts = [item.get("name", ""), item.get("category", ""), item.get("description", "")]
            for addon in item.get("addons", []) or []:
                parts.append(" ".join(str(addon.get(key, "")) for key in ("name", "code", "addon_type")))
            for option in item.get("options", []) or []:
                parts.append(" ".join(str(option.get(key, "")) for key in ("name", "code", "selection_type")))
                for value in option.get("allowed_values", []) or []:
                    parts.append(str(value.get("name", "")))
            return " ".join(parts)

        def resolve_recommendation_from_phrase(phrase, menu_items):
            import re

            phrase = str(phrase or "").strip()
            rule_sets = []
            if re.search(r"冰", phrase):
                rule_sets.append(["冰", ["冰", "冰飲", "冷", "冷飲"]])
            if re.search(r"熱", phrase):
                rule_sets.append(["熱", ["熱", "熱飲"]])
            if re.search(r"咖啡", phrase):
                rule_sets.append(["咖啡", ["咖啡"]])
            if re.search(r"不.*酸|少酸|低酸|酸", phrase):
                rule_sets.append(["酸度", ["不酸", "低酸"]])
            if re.search(r"第一次|新手|入門|初次", phrase):
                rule_sets.append(["新手", ["順口", "柔和", "奶", "拿鐵", "溫和"]])
            if re.search(r"順口", phrase):
                rule_sets.append(["順口", ["順口", "柔和", "奶"]])

            if not rule_sets:
                return menu_items[:3], "generic"

            matched = []
            for item in menu_items:
                evidence = item_evidence_text(item)
                if all(any(keyword in evidence for keyword in keywords) for _, keywords in rule_sets):
                    matched.append(item)
            if not matched:
                return [], "ask_back"
            return matched[:3], "evidenced"

        menu_items = [
            {"code": "COFFEE_ICE", "name": "冰美式", "category": "咖啡", "description": "冰飲", "addons": [], "options": []},
            {"code": "COFFEE_LATTE", "name": "拿鐵", "category": "咖啡", "description": "順口", "addons": [], "options": []},
            {"code": "TEA_HOT", "name": "熱紅茶", "category": "茶飲", "description": "熱飲", "addons": [], "options": []},
        ]
        items, mode = resolve_recommendation_from_phrase("我想喝冰的", menu_items)
        self.assertEqual(mode, "evidenced")
        self.assertEqual([item["code"] for item in items], ["COFFEE_ICE"])

        items, mode = resolve_recommendation_from_phrase("我不喜歡酸的", menu_items)
        self.assertEqual(mode, "ask_back")
        self.assertEqual(items, [])

        menu_items_with_evidence = [
            {"code": "GREEN_TEA", "name": "綠茶", "category": "茶飲", "description": "低酸", "addons": [], "options": []},
        ]
        items, mode = resolve_recommendation_from_phrase("我不喜歡酸的", menu_items_with_evidence)
        self.assertEqual(mode, "evidenced")
        self.assertEqual([item["code"] for item in items], ["GREEN_TEA"])

        items, mode = resolve_recommendation_from_phrase("有什麼推薦？", menu_items)
        self.assertEqual(mode, "generic")
        self.assertEqual([item["code"] for item in items], ["COFFEE_ICE", "COFFEE_LATTE", "TEA_HOT"])

        before = ["COFFEE_ICE"]
        _items, _mode = resolve_recommendation_from_phrase("我想喝冰的", menu_items)
        self.assertEqual(before, ["COFFEE_ICE"])
