from __future__ import annotations

import json

from odoo import http
from odoo.http import request

from ..utils.menu_readonly_mapping_core import build_public_menu_payload


try:
    from odoo.http import Response as OdooResponse  # type: ignore
except Exception:  # pragma: no cover - fallback for non-Odoo test environment
    OdooResponse = None


class _JsonResponse:
    def __init__(self, body: str, status: int = 200, mimetype: str = "application/json"):
        self.status_code = status
        self.mimetype = mimetype
        self._body = body.encode("utf-8")

    @property
    def data(self):
        return self._body

    def get_data(self, as_text: bool = False):
        return self._body.decode("utf-8") if as_text else self._body


class WuchangCafeMenuReadonlyController(http.Controller):
    @http.route(
        "/wuchang/api/cafe/menu/v1",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def cafe_menu_v1(self, **_kwargs):
        try:
            service = request.env["wuchang.cafe.readonly.menu.mapping.service"].sudo()
            snapshot = service.live_odo_menu_data_readonly_mapping_v1()
            payload = build_public_menu_payload(snapshot)
            status = 200
        except Exception as exc:
            payload = {
                "state": "FAIL_CLOSED",
                "schema": "LIVE_ODOO_MENU_DATA_READONLY_MAPPING_V1",
                "store_ref": "wuchang_cafe_menu_options",
                "menu": {"categories": [], "items": []},
                "mapping_sha256": None,
                "error": {
                    "code": "MAPPING_SERVICE_FAILED",
                    "message": str(exc),
                },
            }
            status = 503
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if OdooResponse is not None:
            return OdooResponse(body, status=status, mimetype="application/json")
        return _JsonResponse(body, status=status, mimetype="application/json")
