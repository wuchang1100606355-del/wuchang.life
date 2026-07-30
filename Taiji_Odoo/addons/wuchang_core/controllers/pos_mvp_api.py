import hashlib
import json

from odoo import http
from odoo.http import request


def _landing_enabled(surface):
    try:
        return request.env["wuchang.community.feature.gate"].is_landing_enabled(
            surface
        )
    except KeyError:
        return False


class PosMvpApi(http.Controller):
    @http.route('/api/pos/v1/order', type='json', auth='user', methods=['POST'])
    def create_order(self, **kwargs):
        if not _landing_enabled("pos_order"):
            return {
                "status": "HOLD",
                "message": "HOLD_LANDING_CONTROL_DISABLED",
                "feature_key": "landing.pos_order",
            }
        forbidden = {
            "member_ref",
            "member_id",
            "lines",
            "items",
            "order",
            "payment",
            "inventory",
            "stock",
            "price",
            "unit_price",
        }
        if forbidden & set(kwargs):
            return {
                "status": "BLOCK",
                "message": "BLOCK_POS_BODY_AUTHORITY_OR_WRITE_FIELD",
                "candidate_only": True,
            }
        scene_binding = kwargs.get("scene_binding")
        if not isinstance(scene_binding, dict):
            return {
                "status": "HOLD",
                "message": "HOLD_P4_SCENE_BINDING_REQUIRED",
                "candidate_only": True,
            }
        binding = request.env["wuchang.member.external.auth"].search([
            ("member_user_id", "=", request.env.user.id),
            ("binding_status", "=", "bound"),
        ], limit=1)
        if not binding or request.env.su:
            return {
                "status": "HOLD",
                "message": "HOLD_AUTHENTICATED_MEMBER_BINDING_REQUIRED",
                "candidate_only": True,
            }
        expected_member_ref = (
            "member_ref:sha256:"
            + hashlib.sha256(
                f"member-user:{request.env.user.id}".encode("utf-8")
            ).hexdigest()
        )
        required = {
            "state": "PASS_SCENE_BINDING_CANDIDATE",
            "member_ref": expected_member_ref,
            "pos_mode": "DRY_RUN_CANDIDATE_ONLY",
            "formal_pos_write": False,
            "order_created": False,
            "payment_capture": False,
            "inventory_write": False,
            "price_write": False,
            "member_data_write": False,
            "runtime_released": False,
        }
        if any(scene_binding.get(key) != value for key, value in required.items()):
            return {
                "status": "HOLD",
                "message": "HOLD_P4_SCENE_BINDING_MISMATCH",
                "candidate_only": True,
            }
        binding_material = {
            key: value
            for key, value in scene_binding.items()
            if key != "binding_ref"
        }
        binding_hash = hashlib.sha256(
            json.dumps(
                binding_material,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        if scene_binding.get("binding_ref") != (
            "scene_binding_ref:sha256:" + binding_hash
        ):
            return {
                "status": "HOLD",
                "message": "HOLD_P4_SCENE_BINDING_HASH_MISMATCH",
                "candidate_only": True,
            }
        return {
            "status": "PASS_POS_DRY_RUN_CANDIDATE",
            "scene_binding_ref": scene_binding.get("binding_ref"),
            "p3_gate_ref": scene_binding.get("p3_gate_ref"),
            "verified_channel_binding_ref": scene_binding.get(
                "verified_channel_binding_ref"
            ),
            "action_hash": scene_binding.get("action_hash"),
            "member_ref": expected_member_ref,
            "node_ref": scene_binding.get("node_ref"),
            "capability_ref": scene_binding.get("capability_ref"),
            "d3_coordinate_ref": scene_binding.get("d3_coordinate_ref"),
            "carrier_ref": scene_binding.get("carrier_ref"),
            "formal_db_write": False,
            "formal_pos_write": False,
            "order_created": False,
            "payment_capture": False,
            "inventory_write": False,
            "price_write": False,
            "member_data_write": False,
            "candidate_only": True,
            "runtime_released": False,
        }
