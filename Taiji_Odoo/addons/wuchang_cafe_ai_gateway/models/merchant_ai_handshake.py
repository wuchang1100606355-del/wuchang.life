import hashlib
import json
import re

from odoo import _, api, models
from odoo.exceptions import AccessError


class WuchangCafeMerchantAIHandshakeService(models.AbstractModel):
    _name = "wuchang.cafe.merchant.ai.handshake.service"
    _description = "8DADI Customer AI to Merchant AI Handshake Service"

    @api.model
    def _sha256(self, value):
        encoded = str(value or "").encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @api.model
    def _stable_sha256(self, value):
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @api.model
    def _bounded_integer(self, value, *, default=0, minimum=0, maximum=0):
        try:
            parsed = int(value or default)
        except (TypeError, ValueError):
            parsed = default
        return max(minimum, min(parsed, maximum))

    @api.model
    def _parse_request(self, text, party_size=None, eta_minutes=None, product_query=None):
        normalized = str(text or "").strip()[:500]
        parsed_party_size = self._bounded_integer(
            party_size,
            default=0,
            minimum=0,
            maximum=20,
        )
        if not parsed_party_size:
            digit_match = re.search(r"(\d{1,2})\s*(?:位|人)", normalized)
            chinese_match = re.search(r"([一二兩三四五六七八九十])\s*(?:位|人)", normalized)
            chinese_numbers = {
                "一": 1,
                "二": 2,
                "兩": 2,
                "三": 3,
                "四": 4,
                "五": 5,
                "六": 6,
                "七": 7,
                "八": 8,
                "九": 9,
                "十": 10,
            }
            if digit_match:
                parsed_party_size = int(digit_match.group(1))
            elif chinese_match:
                parsed_party_size = chinese_numbers[chinese_match.group(1)]
            elif "我" in normalized:
                parsed_party_size = 1
        parsed_party_size = max(1, min(parsed_party_size or 1, 20))

        parsed_eta = self._bounded_integer(
            eta_minutes,
            default=0,
            minimum=0,
            maximum=24 * 60,
        )
        if not parsed_eta:
            eta_match = re.search(r"(\d{1,3})\s*分(?:鐘)?後", normalized)
            if eta_match:
                parsed_eta = int(eta_match.group(1))
        parsed_eta = max(0, min(parsed_eta, 24 * 60))

        return {
            "request_sha256": self._sha256(normalized),
            "text_present": bool(normalized),
            "party_size": parsed_party_size,
            "eta_minutes": parsed_eta or None,
            "product_query": str(product_query or "").strip()[:100] or None,
            "_normalized_text": normalized,
        }

    @api.model
    def _menu_state(self, parsed):
        model_name = "wuchang.cafe.readonly.menu.mapping.service"
        if model_name not in self.env.registry.models:
            return {
                "state": "HOLD_MENU_SERVICE_NOT_LOADED",
                "mapping_sha256": None,
                "matches": [],
            }
        try:
            snapshot = self.env[model_name].sudo().live_odo_menu_data_readonly_mapping_v1()
        except Exception:
            return {
                "state": "HOLD_MENU_SOURCE_UNAVAILABLE",
                "mapping_sha256": None,
                "matches": [],
            }

        items = (snapshot.get("catalog") or {}).get("menu_items") or []
        query = (parsed.get("product_query") or "").lower()
        text = parsed.get("_normalized_text", "").lower()
        matches = []
        for item in items:
            if not item.get("active", True):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            name_lower = name.lower()
            matched = bool(query and (query in name_lower or name_lower in query))
            matched = matched or bool(name_lower in text)
            if not matched and "拿鐵" in text and "拿鐵" in name:
                matched = True
            if matched:
                matches.append(
                    {
                        "code": item.get("code"),
                        "name": name,
                        "base_price": item.get("base_price"),
                        "category": item.get("category"),
                        "supply_status": item.get("supply_status"),
                    }
                )
        if len(matches) == 1:
            state = "MATCHED_REAL_MENU_ITEM"
        elif len(matches) > 1:
            state = "HOLD_MENU_VARIANT_SELECTION_REQUIRED"
        else:
            state = "HOLD_REAL_MENU_ITEM_NOT_MATCHED"
        return {
            "state": state,
            "mapping_sha256": snapshot.get("content_sha256"),
            "matches": matches[:8],
        }

    @api.model
    def _seat_state(self, gateway, party_size):
        if not gateway.pos_config_id:
            return {
                "state": "HOLD_POS_STORE_BINDING_REQUIRED",
                "available": None,
                "available_table_count": None,
            }
        if not gateway.seat_capacity_verified:
            return {
                "state": "HOLD_SEAT_SOURCE_ALIGNMENT_REQUIRED",
                "available": None,
                "available_table_count": None,
            }
        pos_config = gateway.pos_config_id.sudo()
        if "floor_ids" not in pos_config._fields:
            return {
                "state": "HOLD_RESTAURANT_SEAT_CAPABILITY_NOT_LOADED",
                "available": None,
                "available_table_count": None,
            }
        floors = pos_config.floor_ids
        tables = floors.mapped("table_ids").filtered("active")
        if not tables:
            return {
                "state": "HOLD_VERIFIED_SEAT_SOURCE_EMPTY",
                "available": None,
                "available_table_count": 0,
            }
        occupied_ids = set()
        order_model = self.env["pos.order"].sudo()
        if "table_id" in order_model._fields:
            occupied_ids = set(
                order_model.search(
                    [
                        ("config_id", "=", gateway.pos_config_id.id),
                        ("state", "=", "draft"),
                        ("table_id", "in", tables.ids),
                    ]
                ).mapped("table_id").ids
            )
        available_tables = tables.filtered(
            lambda table: table.id not in occupied_ids and table.seats >= party_size
        )
        return {
            "state": "OBSERVED_AVAILABLE" if available_tables else "OBSERVED_FULL",
            "available": bool(available_tables),
            "available_table_count": len(available_tables),
            "observed_table_count": len(tables),
        }

    @api.model
    def execute_v23(
        self,
        *,
        text=None,
        store_ref=None,
        party_size=None,
        eta_minutes=None,
        product_query=None,
    ):
        user = self.env.user
        if not user.share and not user.has_group("base.group_system"):
            raise AccessError(_("只有創辦人後台或入口使用者可呼叫商家 AI 握手。"))

        parsed = self._parse_request(text, party_size, eta_minutes, product_query)
        gateway_domain = [("active", "=", True)]
        if store_ref:
            gateway_domain.append(("store_node_ref", "=", str(store_ref).strip()))
        gateways = self.env["wuchang.cafe.gateway"].sudo().search(gateway_domain, limit=2)
        gateway = gateways[:1]

        owner_scope = "member" if user.share else "founder"
        binding_model = self.env["wuchang.ai.compute.binding"].sudo()
        direct_bindings = binding_model.search(
            [
                ("user_id", "=", user.id),
                ("owner_scope", "=", owner_scope),
                ("state", "=", "bound"),
            ]
        )
        identity_refs = direct_bindings.mapped("natural_identity_packet_ref")
        identity_state = (
            "BOUND_NATURAL_IDENTITY_PRESENT"
            if identity_refs
            else "HOLD_IDENTITY_PACKET_BINDING_REQUIRED"
        )
        identity_bindings = (
            binding_model.search(
                [
                    ("natural_identity_packet_ref", "in", identity_refs),
                    ("owner_scope", "=", owner_scope),
                    ("state", "=", "bound"),
                ]
            )
            if identity_refs
            else binding_model.browse()
        )
        provider_state = (
            "BOUND_REPLACEABLE_LLM_COMPUTE_PRESENT"
            if identity_bindings
            else "HOLD_BRING_YOUR_OWN_LLM_BINDING_REQUIRED"
        )
        provider_counts = {
            provider: len(identity_bindings.filtered(lambda item: item.provider_kind == provider))
            for provider in ("gemini", "openai", "other")
        }
        if not gateway:
            store_state = "HOLD_STORE_BINDING_REQUIRED"
            seat = {"state": store_state, "available": None, "available_table_count": None}
        elif len(gateways) > 1 and not store_ref:
            store_state = "HOLD_STORE_SELECTION_REQUIRED"
            seat = {"state": store_state, "available": None, "available_table_count": None}
        else:
            store_state = "BOUND"
            seat = self._seat_state(gateway, parsed["party_size"])
        menu = self._menu_state(parsed)

        holds = [
            state
            for state in (
                identity_state,
                provider_state,
                store_state,
                seat["state"],
                menu["state"],
            )
            if state.startswith("HOLD_")
        ]
        response = {
            "schema": "WUCHANG_8DADI_CUSTOMER_MERCHANT_AI_HANDSHAKE_V2_3",
            "state": holds[0] if holds else "READY_FOR_CUSTOMER_CONFIRMATION",
            "handshake_phase": "MERCHANT_AI_RESPONSE_NO_EXTERNAL_EFFECT",
            "d1_intent": {
                "kind": "visit_seat_and_order",
                "request_sha256": parsed["request_sha256"],
            },
            "d2_state": {
                "party_size": parsed["party_size"],
                "eta_minutes": parsed["eta_minutes"],
                "seat": seat,
                "menu": menu,
            },
            "d3_coordinate": {
                "store_ref": gateway.store_node_ref if gateway else None,
                "pos_config_ref": gateway.pos_config_id.id if gateway and gateway.pos_config_id else None,
                "network_route_policy": "LAN_FIRST_VPN_SECONDARY",
            },
            "d4_evidence": {
                "menu_mapping_sha256": menu.get("mapping_sha256"),
                "seat_source_verified": bool(gateway and gateway.seat_capacity_verified),
            },
            "d5_execution": {
                "reservation_written": False,
                "pos_order_created": False,
                "payment_captured": False,
                "customer_confirmation_required": True,
            },
            "d6_generative_transmission": {
                "minimum_delta_only": True,
                "raw_prompt_forwarded": False,
                "merchant_ai_handshake": True,
                "llm_route_order": [
                    "BROWSER_LOCAL",
                    "MEMBER_BOUND_PROVIDER",
                    "TOTAL_FIELD_QUOTA_POOL",
                    "CLOUD_COMPLETION_IF_AUTHORIZED",
                ],
            },
            "d7_risk": {
                "member_plaintext_transmitted": False,
                "founder_gpu_access": False,
                "founder_api_quota_access": False,
                "founder_compute_pool_policy": "TOTAL_FIELD_QUOTA_GOVERNED",
                "ai_resource_policy": "ADAPTIVE_BROWSER_BYO_TOTAL_FIELD_POOL",
                "holds": holds,
            },
            "d8_authority": {
                "google_login_grants_founder_authority": False,
                "model_is_authority": False,
                "external_effect_authorized": False,
            },
            "bindings": {
                "identity_packet": identity_state,
                "ai_provider": provider_state,
                "llm_compute_source_count": len(identity_bindings),
                "provider_counts": provider_counts,
                "same_natural_identity_multi_account": len(
                    identity_bindings.mapped("user_id")
                ) > 1,
            },
        }
        response["handshake_sha256"] = self._stable_sha256(response)
        return response
