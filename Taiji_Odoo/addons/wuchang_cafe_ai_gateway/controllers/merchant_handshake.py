import json

from odoo import http
from odoo.http import request


class WuchangCafeMerchantAIHandshakeController(http.Controller):
    @http.route(
        "/wuchang/xiaoj/api/merchant-handshake/v2.3",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def merchant_handshake_v23(self, **kwargs):
        params = dict(getattr(request, "jsonrequest", None) or {})
        params.update(kwargs)
        allowed = {
            "text",
            "store_ref",
            "party_size",
            "eta_minutes",
            "product_query",
        }
        return request.env["wuchang.cafe.merchant.ai.handshake.service"].execute_v23(
            **{key: value for key, value in params.items() if key in allowed}
        )

    @http.route(
        "/my/xiaoj",
        type="http",
        auth="user",
        website=True,
        methods=["GET", "POST"],
    )
    def xiaoj_portal(self, **post):
        response = None
        if request.httprequest.method == "POST":
            response = request.env[
                "wuchang.cafe.merchant.ai.handshake.service"
            ].execute_v23(
                text=post.get("intent"),
                store_ref=post.get("store_ref"),
            )
        return request.render(
            "wuchang_cafe_ai_gateway.portal_xiaoj_workspace",
            {
                "response": response,
                "response_json": json.dumps(response, ensure_ascii=False, indent=2)
                if response
                else None,
            },
        )
