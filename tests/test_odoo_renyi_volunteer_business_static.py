import ast
import csv
from pathlib import Path
import xml.etree.ElementTree as ET


MODEL_PATH = Path("Taiji_Odoo/addons/wuchang_core/models/wuchang_matrix.py")
VIEW_PATH = Path("Taiji_Odoo/addons/wuchang_core/views/wuchang_views.xml")
ACCESS_PATH = Path("Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv")
POLICY_PATH = Path("docs/task_force/wuchang_task_force_dispatch_policy_zh.md")
MODULE_INIT_PATH = Path("Taiji_Odoo/addons/wuchang_core/__init__.py")


def test_odoo_model_file_parses():
    ast.parse(MODEL_PATH.read_text(encoding="utf-8"))


def test_odoo_module_imports_models():
    assert MODULE_INIT_PATH.exists()
    assert "from . import models" in MODULE_INIT_PATH.read_text(encoding="utf-8")


def test_renyi_volunteer_models_present():
    text = MODEL_PATH.read_text(encoding="utf-8")
    assert "_name = 'wuchang.renyi.volunteer.business'" in text
    assert "_name = 'wuchang.task.force.dispatch'" in text
    assert "_name = 'wuchang.renyi.volunteer.account'" in text
    assert "_name = 'wuchang.renyi.volunteer.account.line'" in text
    assert "_name = 'wuchang.volunteer.management.meeting'" in text
    assert "branch_scope" in text
    assert "renyi_store" in text
    assert "supervisor_role" in text
    assert "renyi_store_manager" in text
    assert "captain_role" in text
    assert "vacant" in text
    assert "payment_execution_allowed" in text
    assert "google_meet_url" in text
    assert "member_plaintext_included" in text
    assert "payment_or_refund_involved" in text


def test_views_parse_and_actions_present():
    ET.parse(VIEW_PATH)
    text = VIEW_PATH.read_text(encoding="utf-8")
    assert "action_renyi_volunteer_business" in text
    assert "action_task_force_dispatch" in text
    assert "action_renyi_volunteer_account" in text
    assert "action_renyi_volunteer_account_line" in text
    assert "action_volunteer_management_meeting" in text
    assert "menu_renyi_volunteer_business" in text
    assert "menu_task_force_dispatch" in text
    assert "menu_renyi_volunteer_account" in text
    assert "menu_volunteer_management_meeting" in text
    assert "supervisor_user_id" in text
    assert "captain_user_id" in text


def test_access_rights_disable_unlink():
    with ACCESS_PATH.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    target_models = {
        "model_wuchang_renyi_volunteer_business",
        "model_wuchang_task_force_dispatch",
        "model_wuchang_renyi_volunteer_account",
        "model_wuchang_renyi_volunteer_account_line",
        "model_wuchang_volunteer_management_meeting",
    }
    target_rows = [row for row in rows if row["model_id:id"] in target_models]
    assert target_rows
    assert {row["perm_unlink"] for row in target_rows} == {"0"}
    backend_rows = [
        row for row in target_rows
        if row["group_id:id"] == "wuchang_core.group_wuchang_volunteer_backend"
    ]
    assert len(backend_rows) == 5


def test_security_group_file_present():
    text = Path("Taiji_Odoo/addons/wuchang_core/security/wuchang_security.xml").read_text(encoding="utf-8")
    assert "group_wuchang_volunteer_backend" in text
    assert "五常志工管理後台" in text


def test_policy_mentions_odoo_mapping_and_no_live_dispatch():
    text = POLICY_PATH.read_text(encoding="utf-8")
    assert "wuchang.renyi.volunteer.business" in text
    assert "wuchang.task.force.dispatch" in text
    assert "wuchang.renyi.volunteer.account" in text
    assert "wuchang.renyi.volunteer.account.line" in text
    assert "wuchang.volunteer.management.meeting" in text
    assert "志工隊督導" in text
    assert "仁義店店長兼任" in text
    assert "志工隊隊長目前佔缺" in text
    assert "仁義店五常社區數位發展基金子帳戶" in text
    assert "Google Meet" in text
    assert "live_dispatch_enabled = false" in text
    assert "不寫 live Odoo DB" in text
