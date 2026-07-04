import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "Taiji_Odoo/addons/wuchang_core/models"
VIEW_PATH = ROOT / "Taiji_Odoo/addons/wuchang_core/views/order_views.xml"
MANIFEST_PATH = ROOT / "Taiji_Odoo/addons/wuchang_core/__manifest__.py"
MODEL_INIT_PATH = MODEL_DIR / "__init__.py"
ACCESS_PATH = ROOT / "Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv"
POLICY_PATH = ROOT / "docs/task_force/wuchang_task_force_dispatch_policy_zh.md"


def test_delivery_and_order_models_parse():
    ast.parse((MODEL_DIR / "delivery.py").read_text(encoding="utf-8"))
    ast.parse((MODEL_DIR / "order.py").read_text(encoding="utf-8"))


def test_odoo_module_loads_existing_delivery_and_order_design():
    init_text = MODEL_INIT_PATH.read_text(encoding="utf-8")
    manifest_text = MANIFEST_PATH.read_text(encoding="utf-8")
    assert "from . import order" in init_text
    assert "from . import pos_expense" in init_text
    assert "from . import delivery" in init_text
    assert "views/order_views.xml" in manifest_text
    assert "views/order_website.xml" in manifest_text
    assert "views/delivery_page.xml" in manifest_text
    assert "views/ticket_page.xml" in manifest_text


def test_property_commerce_care_fields_are_on_odoo_orders():
    delivery_text = (MODEL_DIR / "delivery.py").read_text(encoding="utf-8")
    order_text = (MODEL_DIR / "order.py").read_text(encoding="utf-8")
    for text in [delivery_text, order_text]:
        assert "property_community_id" in text
        assert "property_unit_id" in text
        assert "merchant_id" in text
        assert "delivery_team_id" in text
        assert "social_worker_partner_id" in text
        assert "caregiver_staff_id" in text
        assert "social_worker_governance_required" in text
        assert "caregiver_employee_required" in text
        assert "eight_dimensional_code_ref" in text
        assert "8D_SOVEREIGN_AI_COMMUNITY_XIAOJ" in text
        assert "sovereign_ai_persona" in text
        assert "community_xiaoj" in text


def test_views_and_access_expose_readonly_governed_relation():
    view_text = VIEW_PATH.read_text(encoding="utf-8")
    access_text = ACCESS_PATH.read_text(encoding="utf-8")
    assert "物業商業外送訂單" in view_text
    assert "property_community_id" in view_text
    assert "merchant_id" in view_text
    assert "social_worker_governance_required" in view_text
    assert "caregiver_employee_required" in view_text
    assert "eight_dimensional_code_ref" in view_text
    assert "sovereign_ai_persona" in view_text
    assert "model_wuchang_order" in access_text
    assert "model_wuchang_delivery_order" in access_text
    assert "model_wuchang_voucher_product" in access_text


def test_policy_states_social_worker_caregiver_and_elder_purpose():
    policy = POLICY_PATH.read_text(encoding="utf-8")
    assert "8D_SOVEREIGN_AI_COMMUNITY_XIAOJ" in policy
    assert "8維碼主權 AI 社區小J" in policy
    assert "社工不是被系統輔助的邊緣角色" in policy
    assert "意圖場的人類治理責任人與社區知能中樞" in policy
    assert "照服員不是外包臨時人力" in policy
    assert "退而不休" in policy
