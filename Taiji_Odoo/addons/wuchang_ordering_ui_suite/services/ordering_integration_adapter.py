"""Fail-closed map from the nine-screen contract to existing Odoo services.

This isolated adapter has no Odoo import and performs no effect.  A future
controller can call ``build_adapter_plan`` before invoking the referenced
existing model methods.  The registry deliberately distinguishes an existing
route from an existing service: unsafe or overly narrow routes are never
presented as drop-in endpoints.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping


STORE_SCOPE = {
    "company_id": 3,
    "pos_config_id": None,
    "store_ref": "store:liaoguo-chongxin-hq",
}

CORE_ROLES = {
    "staff_pos",
    "online_ordering",
    "in_store_self_service",
}

_COMMON_AUTHORITY_KEYS = {
    "amount_paid",
    "amount_total",
    "card_number",
    "client_price",
    "cvv",
    "grand_total",
    "member_id",
    "member_ref",
    "payment",
    "payment_token",
    "phone",
    "price",
    "price_subtotal",
    "price_subtotal_incl",
    "price_unit",
    "total",
    "total_amount",
    "unit_price",
    "voucher_ref",
}

OPERATION_PLANS = {
    "menu": {
        "requested_route": "/wuchang/ordering/menu",
        "allowed_roles": tuple(sorted(CORE_ROLES)),
        "allowed_keys": {"category_ref", "cursor", "locale"},
        "required_keys": set(),
        "reuse": (
            "product.template: exact quickclick_product_id whitelist/available_in_pos/list_price/wuchang_option_group_id",
            "wuchang.cafe.option.group -> question_ids",
            "wuchang.cafe.option.question -> item_ids",
            "wuchang.cafe.option.item -> price_delta/child_group_id",
        ),
        "existing_routes_not_drop_in": (
            "/jules/api/v1/list_pos_stores: API-key gated and does not prove the exact Chongxin-HQ POS under Company 3",
        ),
        "missing": (
            "formal module installation and exact 64-row binding apply",
        ),
    },
    "price": {
        "requested_route": "/wuchang/ordering/price",
        "allowed_roles": tuple(sorted(CORE_ROLES)),
        "allowed_keys": {
            "currency", "option_refs", "order_revision", "product_ref", "quantity",
        },
        "required_keys": {"option_refs", "product_ref", "quantity"},
        "reuse": (
            "product.template.list_price",
            "wuchang.cafe.option.item.price_delta",
            "wuchang.cafe.option.item.child_group_id",
            "existing 201-option / 641-case semantic pricing fixtures",
        ),
        "existing_routes_not_drop_in": (),
        "missing": (
            "server pricing service callable",
            "pricing_receipt_ref and calculation_hash",
            "integer-safe tax/rounding policy bound to the Odoo transaction",
        ),
    },
    "draft": {
        "requested_route": "/wuchang/ordering/draft",
        "allowed_roles": tuple(sorted(CORE_ROLES)),
        "allowed_keys": {
            "calculation_hash", "expected_order_revision", "idempotency_key", "items",
            "note", "option_refs", "pricing_receipt_ref", "product_ref", "quantity",
            "sale_mode", "session_ref",
        },
        "required_keys": {
            "calculation_hash", "expected_order_revision", "idempotency_key", "items",
            "pricing_receipt_ref", "session_ref",
        },
        "reuse": (
            "pos.session opened-session lookup",
            "pos.order draft record",
            "pos.order.line",
            "product.product identity and server price",
        ),
        "existing_routes_not_drop_in": (
            "/api/pos/v1/order: reference-only dry-run and explicitly forbids lines/order writes",
            "/api/order/create: trusts client total, accepts phone plaintext, no idempotency/revision",
            "/jules/api/v1/create_pos_online_order: no option delta, idempotency, revision, or proven Company 3/Chongxin POS scope",
        ),
        "missing": (
            "idempotency persistence or unique binding",
            "expected_order_revision compare-and-set",
            "pricing receipt revalidation in the same transaction",
            "bounded Company 3 / exact Chongxin POS session lookup",
        ),
    },
    "cancel": {
        "requested_route": "/wuchang/ordering/cancel",
        "allowed_roles": ("staff_pos",),
        "allowed_keys": {
            "expected_order_revision", "idempotency_key", "order_ref", "reason_code",
        },
        "required_keys": {"expected_order_revision", "idempotency_key", "order_ref"},
        "reuse": (
            "pos.order state and record identity after staged method verification",
            "wuchang.order state values new/paid/cancelled are evidence only, not the target POS service",
        ),
        "existing_routes_not_drop_in": (),
        "missing": (
            "verified installed Odoo 18 POS cancel method",
            "staff capability and server cancel policy binding",
            "cancel idempotency/revision receipt",
        ),
        "hold_after_validation": "HOLD_EXISTING_CANCEL_SERVICE_UNRESOLVED",
    },
    "member_lookup": {
        "requested_route": "/wuchang/ordering/member/lookup",
        "allowed_roles": ("staff_pos",),
        "allowed_keys": {"last_three", "organization_ref", "seat_ref"},
        "required_keys": {"last_three", "organization_ref", "seat_ref"},
        "reuse": (
            "wuchang.member.low.risk.lookup._match_for_staff",
            "phone_last3_hmac with configured server pepper",
            "wuchang.organization.capability.seat CAP_MEMBER_LOOKUP",
        ),
        "existing_routes_not_drop_in": (
            "/wuchang/xiaoj/api/staff-red-tea-voucher-preview: correct masked lookup but bounded to the red-tea sandbox",
        ),
        "missing": (
            "generic masked-candidate route over the existing lookup model",
            "generic lookup receipt outside the red-tea sandbox",
        ),
    },
    "voucher_confirm": {
        "requested_route": "/wuchang/ordering/voucher/confirm",
        "allowed_roles": ("online_ordering",),
        "allowed_keys": {"approve", "checkout_ref"},
        "required_keys": {"approve", "checkout_ref"},
        "reuse": (
            "wuchang.sovereign.voucher.checkout.confirm_for_current_member",
            "/wuchang/xiaoj/api/member-red-tea-voucher-confirm (auth=user)",
        ),
        "existing_routes_not_drop_in": (
            "/wuchang/xiaoj/api/member-voucher-redeem-dry-run: dry-run only, not owner confirmation",
            "/wuchang/xiaoj/api/member-red-tea-voucher-confirm: exact owner confirmation but red-tea sandbox only",
        ),
        "missing": (
            "generic product/voucher checkout binding",
            "generic owner-confirmed redemption receipt",
        ),
    },
}


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_payload_keys(item))
        return keys
    if isinstance(value, (list, tuple)):
        keys: set[str] = set()
        for item in value:
            keys.update(_payload_keys(item))
        return keys
    return set()


def build_adapter_plan(
    operation: str,
    *,
    company_id: int,
    pos_config_id: int | None,
    expected_pos_config_id: int | None = None,
    role: str,
    payload: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Validate one call and return a no-effect integration plan receipt."""

    if operation not in OPERATION_PLANS:
        return {"state": "HOLD_UNKNOWN_OPERATION", "formal_effect": False}
    plan = OPERATION_PLANS[operation]
    if company_id != STORE_SCOPE["company_id"]:
        return {"state": "HOLD_OUTSIDE_CHONGXIN_HQ_SCOPE", "formal_effect": False}
    if expected_pos_config_id is None:
        return {"state": "HOLD_EXACT_POS_CONFIG_TARGET_REQUIRED", "formal_effect": False}
    if pos_config_id != expected_pos_config_id:
        return {"state": "HOLD_EXACT_POS_BINDING_MISMATCH", "formal_effect": False}
    if role not in plan["allowed_roles"]:
        return {"state": "HOLD_ROLE_NOT_ALLOWED_FOR_OPERATION", "formal_effect": False}
    if not isinstance(payload, Mapping):
        return {"state": "HOLD_PAYLOAD_OBJECT_REQUIRED", "formal_effect": False}

    keys = _payload_keys(payload)
    forbidden = sorted(keys & _COMMON_AUTHORITY_KEYS)
    if forbidden:
        return {
            "state": "HOLD_CLIENT_AUTHORITY_OR_SENSITIVE_FIELD_FORBIDDEN",
            "forbidden_keys": forbidden,
            "formal_effect": False,
        }
    undeclared = sorted(keys - plan["allowed_keys"])
    if undeclared:
        return {
            "state": "HOLD_UNDECLARED_INPUT_FIELD",
            "undeclared_keys": undeclared,
            "formal_effect": False,
        }
    missing = sorted(plan["required_keys"] - set(payload))
    if missing:
        return {
            "state": "HOLD_REQUIRED_INPUT_MISSING",
            "missing_keys": missing,
            "formal_effect": False,
        }
    if operation == "member_lookup":
        suffix = payload.get("last_three")
        if not isinstance(suffix, str) or len(suffix) != 3 or not suffix.isdigit():
            return {"state": "HOLD_PHONE_LAST_THREE_FORMAT", "formal_effect": False}

    state = plan.get("hold_after_validation", "PASS_ISOLATED_ADAPTER_PLAN")
    receipt_material = {
        "operation": operation,
        "requested_route": plan["requested_route"],
        "company_id": company_id,
        "pos_config_id": pos_config_id,
        "role": role,
        "payload_keys": sorted(keys),
        "reuse": list(plan["reuse"]),
        "missing": list(plan["missing"]),
    }
    return {
        "state": state,
        "operation": operation,
        "requested_route": plan["requested_route"],
        "store_ref": STORE_SCOPE["store_ref"],
        "reuse": list(plan["reuse"]),
        "existing_routes_not_drop_in": list(plan["existing_routes_not_drop_in"]),
        "missing": list(plan["missing"]),
        "adapter_receipt_ref": "sha256:" + _canonical_sha256(receipt_material),
        "formal_effect": False,
        "database_write": False,
        "order_created": False,
        "payment_capture": False,
        "member_plaintext": False,
        "phone_last_three_is_authentication": False,
    }


def endpoint_matrix() -> dict[str, dict[str, object]]:
    """Return a serialization-safe view for reports and future controllers."""

    return {
        operation: {
            "requested_route": plan["requested_route"],
            "allowed_roles": list(plan["allowed_roles"]),
            "reuse": list(plan["reuse"]),
            "existing_routes_not_drop_in": list(plan["existing_routes_not_drop_in"]),
            "missing": list(plan["missing"]),
            "activation": False,
        }
        for operation, plan in OPERATION_PLANS.items()
    }
