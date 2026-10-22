"""Read-only manager dashboard projection over the bound Odoo store."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from odoo import fields

from .eightd_analysis import locate_resources
from .live_odoo_projection import STORE_BINDING, configured_pos_config_id, menu_projection


def _discover_models(env, terms):
    model_refs = set()
    for term in terms:
        rows = env["ir.model"].sudo().search(
            ["|", ("model", "ilike", term), ("name", "ilike", term)], limit=20
        )
        model_refs.update(rows.mapped("model"))
    return sorted(model_refs)


def _connector_state(env, kind, terms):
    models = _discover_models(env, terms)
    return {
        "kind": kind,
        "state": "DISCOVERED_MODEL_NOT_PROVEN_CALLABLE" if models else "NOT_CONNECTED_NO_VERIFIED_CONNECTOR",
        "model_refs": models,
        "account_resource_ref": None,
        "permissions_verified": False,
        "last_sync": None,
        "external_write_authorized": False,
    }


def _order_snapshot(env):
    pos_config_id = configured_pos_config_id(env)
    if pos_config_id is None:
        return {
            "state": "HOLD_EXACT_POS_CONFIG_TARGET_REQUIRED",
            "order_count": None,
            "paid_order_count": None,
            "paid_amount_total": None,
            "gross_margin": None,
            "database_write": False,
        }
    model = env["pos.order"].sudo().with_company(STORE_BINDING["company_id"])
    cutoff = fields.Datetime.now() - timedelta(days=7)
    domain = [
        ("company_id", "=", STORE_BINDING["company_id"]),
        ("config_id", "=", pos_config_id),
        ("date_order", ">=", cutoff),
    ]
    orders = model.search(domain)
    paid_states = {"paid", "done", "invoiced"}
    paid = orders.filtered(lambda row: row.state in paid_states)
    result = {
        "period": {"from": cutoff.isoformat(), "to": fields.Datetime.now().isoformat(), "timezone": "UTC"},
        "order_count": len(orders),
        "paid_order_count": len(paid),
        "paid_amount_total": sum(paid.mapped("amount_total")),
        "unpaid_not_counted_as_revenue": len(orders - paid),
        "gross_margin": None,
        "gross_margin_state": "UNDETERMINED_COST_OR_RECIPE_EVIDENCE_MISSING",
        "sale_modes": {"dine_in": None, "takeout": None, "delivery": None},
        "sale_mode_state": "UNDETERMINED_NO_VERIFIED_ORDER_LEVEL_FIELD",
    }
    for candidate in ("wuchang_sale_mode", "sale_mode", "service_mode"):
        if candidate in model._fields:
            values = {"dine_in": 0, "takeout": 0, "delivery": 0}
            for order in orders:
                value = str(order[candidate] or "")
                if value in values:
                    values[value] += 1
            result["sale_modes"] = values
            result["sale_mode_state"] = f"PASS_ODOO_ORDER_FIELD:{candidate}"
            break
    return result


def _inventory_snapshot(env, menu):
    if menu.get("state") != "PASS_ODOO_MENU_PROJECTION":
        return {"state": "HOLD_MENU_MAPPING_REQUIRED", "items": []}
    ids = [row["odoo_product_template_id"] for row in menu["products"]]
    products = env["product.template"].sudo().browse(ids).exists()
    items = [
        {
            "source_product_id": row.quickclick_product_id,
            "name": row.name,
            "qty_available": row.qty_available,
            "forecasted_qty": row.virtual_available,
        }
        for row in products
    ]
    return {
        "state": "PASS_ODOO_STOCK_READONLY",
        "items": items,
        "low_stock_count": None,
        "low_stock_state": "UNDETERMINED_NO_APPROVED_THRESHOLD",
        "database_write": False,
    }


def management_snapshot(env):
    menu = menu_projection(env)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    google = _connector_state(env, "google_business_profile", ["google.business", "business.profile", "google.review"])
    social = _connector_state(env, "platform_neutral_social", ["social.connector", "social.post", "social.review"])
    nvr = _connector_state(env, "nvr_camera", ["nvr", "camera", "surveillance"])
    music = _connector_state(env, "store_music", ["music", "audio.player", "speaker"])
    observations = [
        {
            "resource_ref": "odoo:company-3:pos-unresolved",
            "kind": "odoo_pos_menu_orders_inventory",
            "source_ref": menu.get("projection_receipt_ref") or menu.get("receipt_ref", "UNAVAILABLE"),
            "observed_at": now.isoformat(),
            "version": "odoo-18",
            "capabilities": ["menu", "price", "orders", "inventory"],
            "loaded": True,
            "callable": menu.get("state") == "PASS_ODOO_MENU_PROJECTION",
            "effect_verified": menu.get("state") == "PASS_ODOO_MENU_PROJECTION",
            "authority_scope": "manager.read",
            "max_age_seconds": 300,
        },
        {
            "resource_ref": "w7tp:shared-intent-field:9107",
            "kind": "total_field_authority",
            "source_ref": "runtime/total_field/secondary_cloud/capability_registry.json",
            "observed_at": now.isoformat(),
            "version": "W7TP/8D-ADI-V2.3-candidate-source",
            "capabilities": ["8d analysis", "resource location", "authorization gate"],
            "loaded": False,
            "callable": False,
            "effect_verified": False,
            "authority_scope": "total_field.read",
            "required_authorization": "EXISTING_TOTAL_FIELD_GATE",
            "max_age_seconds": 60,
        },
    ]
    analysis = locate_resources(
        "定位重新總店 Odoo、8D、Google 商家、社群、音樂與 NVR 可用資源",
        observations,
        target_ref="node:03-manager",
        authorized_scopes={"manager.read", "total_field.read"},
        now=now,
    )
    return {
        "schema": "wuchang.manager-dashboard-readonly.v1",
        "state": (
            "PASS_READONLY_SNAPSHOT"
            if menu.get("state") == "PASS_ODOO_MENU_PROJECTION"
            else "HOLD_EXACT_STORE_BINDING_REQUIRED"
        ),
        "store_ref": STORE_BINDING["store_ref"],
        "binding": dict(STORE_BINDING),
        "observed_at": now.isoformat(),
        "timezone": "UTC",
        "menu": menu,
        "orders": _order_snapshot(env),
        "inventory": _inventory_snapshot(env, menu),
        "google_business": google,
        "social_collaboration": social,
        "nvr": nvr,
        "music": music,
        "eightd": analysis,
        "ai": {
            "state": "CANDIDATE_ONLY_TOTAL_FIELD_NOT_CALLED_FROM_ODOO",
            "source_requirements": ["source_ref", "observed_at", "version", "scope", "missing_evidence"],
            "automatic_price_change": False,
            "automatic_voucher_use": False,
            "automatic_external_publish": False,
            "automatic_permission_change": False,
        },
        "formal_effect": False,
        "database_write": False,
    }
