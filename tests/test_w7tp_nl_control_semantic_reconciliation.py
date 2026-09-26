#!/usr/bin/env python3
"""T-008 semantic reconciliation tests for natural-language control."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / ".skill-build" / "w7tp-8d-adi-natural-language-control"
SKILL_PATH = SKILL_ROOT / "SKILL.md"
PRODUCT_PATH = SKILL_ROOT / "references" / "product-competitor-design.md"
LANDING_PATH = SKILL_ROOT / "references" / "hypothesis-design-landing.md"
CANONICAL_PATH = ROOT / "configs/total_field/w7tp_developer_intent_canonical_v1.json"


class NaturalLanguageSemanticReconciliationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")
        cls.product = PRODUCT_PATH.read_text(encoding="utf-8")
        cls.landing = LANDING_PATH.read_text(encoding="utf-8")
        cls.canonical = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))

    def test_8d_is_single_state_field_not_pipeline(self) -> None:
        self.assertIn("8_IN_1_SINGLE_STATE_FIELD", self.skill)
        self.assertIn("不得把本體退回 D1→D8 八步流水線", self.skill)

    def test_adi_exact_definition_remains_governing_contract_bound(self) -> None:
        self.assertIn("FI-023 ADI_EXACT_DEFINITION", self.skill)
        self.assertIn("不得把 ADI 硬編成單一「絕對距離索引」定義", self.skill)
        self.assertNotIn("以 ADI（絕對距離索引）作為座標定位引擎", self.skill)
        self.assertNotIn("以 ADI（絕對距離索引）作為定位基礎", self.product)

    def test_natural_language_is_primary_not_unique_human_interface(self) -> None:
        self.assertIn("自然語言對話是原生／主要人類執行介面", self.skill)
        self.assertNotIn("自然語言是唯一人類入口", self.skill)

    def test_d6_does_not_require_permanent_shared_base_or_minimum_delta(self) -> None:
        self.assertIn("不得升格為 GST 永久必要定義", self.skill)
        self.assertIn("不是永久必要定義", self.product)
        self.assertNotIn("目標基座＋最小新資訊＋座標＋重構／驗證規則閉合", self.skill)

    def test_auto_land_scope_excludes_independent_human_authority_effects(self) -> None:
        required = (
            "個資同意",
            "付款／扣款",
            "正式法律或組織效果",
            "角色／權限／身分升級",
            "帳號或付費變更",
            "對外公開",
            "不可逆或破壞性效果",
        )
        for phrase in required:
            self.assertIn(phrase, self.skill)
            self.assertIn(phrase, self.landing)
        self.assertIn("不等於模型、技能或 Provider 自行授予 D8", self.skill)

    def test_warn_remains_unresolved_gate_not_skill_normalization(self) -> None:
        self.assertIn("FI-024 D8_WARN_FINAL_STATUS", self.skill)
        self.assertIn("不得自行決定 WARN 應屬 D7 或 D8", self.skill)
        self.assertIn("不得自行把它轉成 PASS／HOLD／BLOCK", self.skill)

    def test_canonical_keeps_adi_and_warn_as_mandatory_gates(self) -> None:
        gates = {
            item["intent_id"]: item
            for item in self.canonical["mandatory_gates"]
        }
        self.assertEqual(gates["FI-023"]["status"], "UNRESOLVED")
        self.assertEqual(gates["FI-024"]["status"], "UNRESOLVED")
        self.assertIn("T-008", gates["FI-023"]["demand"])
        self.assertIn("T-008", gates["FI-024"]["demand"])

    def test_authority_spine_and_state_class_separation_are_explicit(self) -> None:
        self.assertIn(
            "Founder Intent → 8D/ADI Index → Current 8D Field → taiji01 Total Field",
            self.skill,
        )
        self.assertIn(
            "HYPOTHESIS、DESIGN、EVIDENCE、RUNTIME_EFFECT、ACTIVE、CANONICAL、AUTHORITY 必須分離",
            self.skill,
        )


if __name__ == "__main__":
    unittest.main()
