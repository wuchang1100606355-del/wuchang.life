from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from ..utils.menu_readonly_mapping_core import (
    MENU_FIELDS_MAPPED,
    MENU_MAPPING_SCHEMA_REF,
    build_readonly_menu_snapshot,
    collect_readonly_menu_snapshot_from_env,
    sha256_hex,
)


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "live_odo_menu_data_readonly_mapping_v1.json"
SCHEMA_SHA256_PATH = Path(__file__).resolve().parents[1] / "schemas" / "live_odo_menu_data_readonly_mapping_v1.sha256"


class GuardedModel:
    def __init__(self, records):
        self._records = list(records)

    def search(self, *args, **kwargs):
        return list(self._records)

    def create(self, *args, **kwargs):
        raise AssertionError("create must not be called")

    def write(self, *args, **kwargs):
        raise AssertionError("write must not be called")

    def unlink(self, *args, **kwargs):
        raise AssertionError("unlink must not be called")


class GuardedEnv:
    def __init__(self, models):
        self._models = dict(models)

    def __getitem__(self, model_name):
        return self._models[model_name]


def _record(**fields):
    return SimpleNamespace(**fields)


class LiveOdooMenuReadonlyMappingTests(unittest.TestCase):
    def test_schema_is_present_and_pinned(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert schema["title"] == MENU_MAPPING_SCHEMA_REF
        assert schema["required"] == [
            "snapshot_ref",
            "source_modules",
            "source_models",
            "menu_fields_mapped",
            "catalog",
            "w5c_reused",
            "deterministic_output",
            "content_sha256",
        ]
        assert SCHEMA_SHA256_PATH.exists()

    def test_readonly_mapping_is_deterministic_and_reuses_existing_w5c(self):
        source = {
            "menu_items": [
                {
                    "code": "DR_RED_TEA",
                    "name": "紅茶",
                    "base_price": 30,
                    "category": "飲料類",
                    "description": "現場真實菜單",
                    "active": True,
                    "normalized_price_basis": "base_price",
                    "normalized_price_note": "沿用既有菜單價",
                }
            ],
            "menu_attributes": [
                {
                    "technical_key": "drink_size",
                    "name": "杯型",
                    "sequence": 10,
                    "active": True,
                }
            ],
            "menu_attribute_values": [
                {
                    "technical_key": "drink_size",
                    "name": "小杯",
                    "delta_price": 0,
                    "active": True,
                },
                {
                    "technical_key": "drink_size",
                    "name": "大杯",
                    "delta_price": 10,
                    "active": True,
                },
            ],
            "menu_item_attributes": [
                {
                    "item_code": "DR_RED_TEA",
                    "technical_key": "drink_size",
                    "attribute_name": "杯型",
                    "selection_type": "single",
                    "required": True,
                }
            ],
            "option_groups": [
                {
                    "code": "DRINK_SIZE",
                    "name": "杯型",
                    "sequence": 10,
                    "active": True,
                    "source": "wuchang.cafe.option.group",
                    "w5c_code": "CAFE-OPTION-GROUP-001",
                    "w5c_domain": "CAFE",
                    "w5c_entity": "OPTION_GROUP",
                }
            ],
            "option_questions": [
                {
                    "code": "DRINK_SIZE_Q1",
                    "group_code": "DRINK_SIZE",
                    "name": "杯型",
                    "display_name": "杯型",
                    "selection_type": "single",
                    "required": True,
                    "active": True,
                    "w5c_code": "CAFE-OPTION-QUESTION-001",
                    "w5c_domain": "CAFE",
                    "w5c_entity": "OPTION_QUESTION",
                }
            ],
            "option_items": [
                {
                    "code": "DRINK_SIZE_SMALL",
                    "question_code": "DRINK_SIZE_Q1",
                    "name": "小杯",
                    "display_name": "小杯",
                    "price_delta": 0,
                    "active": True,
                    "w5c_code": "CAFE-OPTION-ITEM-001",
                    "w5c_domain": "CAFE",
                    "w5c_entity": "OPTION_ITEM",
                }
            ],
            "product_templates": [
                {
                    "id": 10,
                    "name": "紅茶產品模板",
                    "quickclick_menu_id": "MENU-1",
                    "quickclick_product_code": "DR_RED_TEA",
                    "quickclick_image_url": "https://example.invalid/red-tea.png",
                    "quickclick_raw_category": "飲料類",
                    "quickclick_raw_price": 30,
                    "normalized_price_basis": "base_price",
                    "normalized_price_note": "沿用既有菜單價",
                    "wuchang_pos_locked": True,
                    "w5c_code": "CAFE-PRODUCT-001",
                    "w5c_domain": "CAFE",
                    "w5c_entity": "PRODUCT_TEMPLATE",
                }
            ],
        }
        snapshot1 = build_readonly_menu_snapshot(source)
        snapshot2 = build_readonly_menu_snapshot(source)
        assert snapshot1 == snapshot2
        assert snapshot1["snapshot_ref"] == MENU_MAPPING_SCHEMA_REF
        assert snapshot1["w5c_reused"] is True
        assert snapshot1["deterministic_output"] is True
        assert snapshot1["catalog"]["menu_items"][0]["code"] == "DR_RED_TEA"
        assert snapshot1["catalog"]["menu_items"][0]["options"][0]["code"] == "drink_size"
        assert snapshot1["catalog"]["option_groups"][0]["w5c"]["code"] == "CAFE-OPTION-GROUP-001"
        assert snapshot1["catalog"]["product_templates"][0]["image"]["reference"] == "https://example.invalid/red-tea.png"
        assert snapshot1["content_sha256"] == sha256_hex({k: v for k, v in snapshot1.items() if k != "content_sha256"})

    def test_env_collector_is_read_only_and_has_no_fake_menu(self):
        env = GuardedEnv(
            {
                "wuchang.menu.item": GuardedModel([
                    _record(id=1, code="DR_RED_TEA", name="紅茶", base_price=30, category="飲料類", description="", active=True, normalized_price_basis="base_price", normalized_price_note=""),
                ]),
                "wuchang.menu.addon": GuardedModel([]),
                "wuchang.menu.attribute": GuardedModel([
                    _record(id=11, technical_key="drink_size", name="杯型", sequence=10, active=True, note="", w5c_code="", w5c_domain="", w5c_entity="", w5c_topology="", w5c_time_state="", w5c_authority=""),
                ]),
                "wuchang.menu.attribute.value": GuardedModel([
                    _record(id=21, name="小杯", delta_price=0, active=True, w5c_code="", w5c_domain="", w5c_entity="", w5c_topology="", w5c_time_state="", w5c_authority="", attribute_id=_record(technical_key="drink_size", name="杯型")),
                ]),
                "wuchang.menu.item.addon": GuardedModel([]),
                "wuchang.menu.item.attribute": GuardedModel([
                    _record(id=31, item_id=_record(code="DR_RED_TEA"), attribute_id=_record(technical_key="drink_size", name="杯型"), quickclick_question_code="", w5c_code="", w5c_domain="", w5c_entity="", w5c_topology="", w5c_time_state="", w5c_authority=""),
                ]),
                "wuchang.cafe.option.group": GuardedModel([]),
                "wuchang.cafe.option.question": GuardedModel([]),
                "wuchang.cafe.option.item": GuardedModel([]),
                "product.template": GuardedModel([]),
            }
        )
        snapshot = collect_readonly_menu_snapshot_from_env(env)
        assert snapshot["catalog"]["menu_items"][0]["code"] == "DR_RED_TEA"
        assert snapshot["catalog"]["menu_items"][0]["name"] == "紅茶"
        assert snapshot["catalog"]["menu_items"][0]["options"][0]["code"] == "drink_size"
        assert "假菜單" not in json.dumps(snapshot, ensure_ascii=False)
        assert "secret" not in json.dumps(snapshot, ensure_ascii=False).lower()

