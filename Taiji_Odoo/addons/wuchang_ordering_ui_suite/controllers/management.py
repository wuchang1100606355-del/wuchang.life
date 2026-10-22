"""Manager-only read surface; no external or Odoo mutation routes exist here."""

from odoo import http
from odoo.http import request

from ..services.management_state import management_snapshot


SUITES = {"a": "靛藍科技", "b": "暖米咖啡", "c": "墨韻典藏"}


def _manager_allowed():
    return request.env.user.has_group("point_of_sale.group_pos_manager")


class WuchangManagementController(http.Controller):
    @http.route(
        "/wuchang/ordering/management/<string:suite>",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def management_ui(self, suite, **_kwargs):
        if suite not in SUITES:
            return request.not_found()
        if not _manager_allowed():
            return request.make_response("店長管理權限不足", status=403)
        return request.render(
            "wuchang_ordering_ui_suite.management_ui",
            {"suite": suite, "suite_name": SUITES[suite]},
        )

    @http.route(
        "/wuchang/ordering/management/state",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def management_state(self, **_payload):
        if not _manager_allowed():
            return {"state": "HOLD_POS_MANAGER_CAPABILITY_REQUIRED", "formal_effect": False}
        return management_snapshot(request.env)
