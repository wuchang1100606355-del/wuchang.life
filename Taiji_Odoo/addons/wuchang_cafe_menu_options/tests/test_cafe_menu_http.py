from __future__ import annotations

import importlib
import json
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ..utils.menu_readonly_mapping_core import build_public_menu_payload, build_readonly_menu_snapshot, sha256_hex


class GuardedModel:
    def __init__(self, records):
        self._records = list(records)
        self.write_calls = 0
        self.create_calls = 0
        self.unlink_calls = 0

    def search(self, *args, **kwargs):
        return list(self._records)

    def create(self, *args, **kwargs):
        self.create_calls += 1
        raise AssertionError("create must not be called")

    def write(self, *args, **kwargs):
        self.write_calls += 1
        raise AssertionError("write must not be called")

    def unlink(self, *args, **kwargs):
        self.unlink_calls += 1
        raise AssertionError("unlink must not be called")


class GuardedService:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.calls = 0

    def sudo(self):
        return self

    def live_odo_menu_data_readonly_mapping_v1(self, limit=200):
        self.calls += 1
        return self.snapshot


class GuardedEnv:
    def __init__(self, models):
        self._models = dict(models)

    def __getitem__(self, model_name):
        return self._models[model_name]


class FakeRequest:
    def __init__(self, env):
        self.env = env


def _record(**fields):
    return SimpleNamespace(**fields)


class CafeMenuHttpTests(unittest.TestCase):
    def setUp(self):
        self.snapshot_source = {
            "menu_items": [
                {
                    "code": "DR_RED_TEA",
                    "name": "紅茶",
                    "base_price": 30,
                    "category": "飲料類",
                    "description": "公開菜單",
                    "active": True,
                    "normalized_price_basis": "base_price",
                    "normalized_price_note": "沿用既有菜單價",
                },
                {
                    "code": "INACTIVE_ITEM",
                    "name": "停用品項",
                    "base_price": 99,
                    "category": "飲料類",
                    "description": "不應公開",
                    "active": False,
                },
            ],
            "menu_attributes": [],
            "menu_attribute_values": [],
            "menu_item_attributes": [],
            "option_groups": [],
            "option_questions": [],
            "option_items": [],
            "product_templates": [],
        }
        self.snapshot = build_readonly_menu_snapshot(self.snapshot_source)
        self.public_payload = build_public_menu_payload(self.snapshot)

    def _install_fake_odoo(self):
        fake_http = SimpleNamespace(Controller=object, route=lambda *a, **k: (lambda f: f), request=None)
        fake_odoo = SimpleNamespace(http=fake_http)
        sys.modules["odoo"] = fake_odoo
        sys.modules["odoo.http"] = fake_http
        sys.modules["odoo.models"] = SimpleNamespace()
        return fake_http

    def test_get_route_returns_json_200_and_deterministic(self):
        fake_http = self._install_fake_odoo()
        service = GuardedService(self.snapshot)
        env = GuardedEnv({
            "wuchang.cafe.readonly.menu.mapping.service": service,
            "wuchang.menu.item": GuardedModel([]),
        })
        module = importlib.import_module("wuchang_cafe_menu_options.controllers.cafe_menu_http")
        module.request = FakeRequest(env)
        controller = module.WuchangCafeMenuReadonlyController()
        response1 = controller.cafe_menu_v1()
        response2 = controller.cafe_menu_v1()
        assert response1.status_code == 200
        assert response1.mimetype == "application/json"
        assert response2.data == response1.data
        payload = json.loads(response1.get_data(as_text=True))
        assert payload["state"] == "PASS"
        assert payload["schema"] == "LIVE_ODOO_MENU_DATA_READONLY_MAPPING_V1"
        assert payload["store_ref"] == "wuchang_cafe_menu_options"
        assert payload["mapping_sha256"] == self.snapshot["content_sha256"]
        assert payload["menu"]["items"][0]["code"] == "DR_RED_TEA"
        assert payload["menu"]["items"][0]["active"] is True
        assert payload["menu"]["items"][0]["base_price"] == 30
        assert payload["menu"]["items"][0]["description"] == "公開菜單"
        assert payload["menu"]["items"][0]["normalized_price_basis"] == "base_price"
        assert payload["menu"]["items"][0]["normalized_price_note"] == "沿用既有菜單價"
        assert all(item["active"] for item in payload["menu"]["items"])
        assert "INACTIVE_ITEM" not in json.dumps(payload, ensure_ascii=False)
        assert "secret" not in json.dumps(payload, ensure_ascii=False).lower()
        assert "member" not in json.dumps(payload, ensure_ascii=False).lower()
        assert service.calls == 2

    def test_fail_closed_when_mapping_service_raises(self):
        fake_http = self._install_fake_odoo()

        class BrokenService:
            def sudo(self):
                return self

            def live_odo_menu_data_readonly_mapping_v1(self, limit=200):
                raise RuntimeError("boom")

        env = GuardedEnv({"wuchang.cafe.readonly.menu.mapping.service": BrokenService()})
        module = importlib.import_module("wuchang_cafe_menu_options.controllers.cafe_menu_http")
        module.request = FakeRequest(env)
        controller = module.WuchangCafeMenuReadonlyController()
        response = controller.cafe_menu_v1()
        payload = json.loads(response.get_data(as_text=True))
        assert response.status_code == 503
        assert payload["state"] == "FAIL_CLOSED"
        assert payload["menu"]["items"] == []
        assert payload["mapping_sha256"] is None
        assert payload["error"]["code"] == "MAPPING_SERVICE_FAILED"

    def test_db_records_remain_unchanged(self):
        fake_http = self._install_fake_odoo()
        guarded_item = GuardedModel([
            _record(id=1, code="DR_RED_TEA", name="紅茶", base_price=30, category="飲料類", description="公開菜單", active=True, normalized_price_basis="base_price", normalized_price_note=""),
        ])
        guarded_addon = GuardedModel([])
        guarded_attr = GuardedModel([])
        guarded_value = GuardedModel([])
        guarded_item_attr = GuardedModel([])
        env = GuardedEnv({
            "wuchang.cafe.readonly.menu.mapping.service": GuardedService(self.snapshot),
            "wuchang.menu.item": guarded_item,
            "wuchang.menu.addon": guarded_addon,
            "wuchang.menu.attribute": guarded_attr,
            "wuchang.menu.attribute.value": guarded_value,
            "wuchang.menu.item.addon": guarded_item_attr,
            "wuchang.menu.item.attribute": guarded_item_attr,
        })
        module = importlib.import_module("wuchang_cafe_menu_options.controllers.cafe_menu_http")
        module.request = FakeRequest(env)
        controller = module.WuchangCafeMenuReadonlyController()
        before = (guarded_item.create_calls, guarded_item.write_calls, guarded_item.unlink_calls)
        controller.cafe_menu_v1()
        after = (guarded_item.create_calls, guarded_item.write_calls, guarded_item.unlink_calls)
        assert before == after == (0, 0, 0)

    def test_mapping_sha256_binding_verifies(self):
        assert self.snapshot["content_sha256"] == sha256_hex({k: v for k, v in self.snapshot.items() if k != "content_sha256"})
        assert self.public_payload["mapping_sha256"] == self.snapshot["content_sha256"]
        assert self.public_payload["response_sha256"] == sha256_hex({k: v for k, v in self.public_payload.items() if k != "response_sha256"})
