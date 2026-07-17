"""Least-privilege Odoo product surface for cafe menu responsible persons."""

from __future__ import annotations

import hashlib
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.menu_change_governance import (
    build_odoo_product_thing_code,
    stable_sha256,
)


RESPONSIBLE_GROUP = "wuchang_cafe_menu_options.group_wuchang_cafe_menu_responsible"
REMOTE_SUPPORT_GROUP = "wuchang_cafe_menu_options.group_wuchang_cafe_remote_support"
GOVERNANCE_ADMIN_GROUP = "wuchang_member_registration.group_wuchang_member_admin"


class WuchangCafeAiEventbookMenuAction(models.Model):
    _inherit = "wuchang.cafe.ai.eventbook"

    event_type = fields.Selection(
        selection_add=[("human_menu_action", "Human Menu Action")],
        ondelete={"human_menu_action": "set default"},
    )

    @api.model_create_multi
    def create(self, vals_list):
        if any(
            values.get("event_type") == "human_menu_action"
            for values in vals_list
        ) and not self.env.su:
            raise UserError(_("Human menu audit events are created only by the governed menu workflow."))
        return super().create(vals_list)

    def write(self, values):
        if (
            any(record.event_type == "human_menu_action" for record in self)
            and not self.env.context.get("module_uninstall")
        ):
            raise UserError(_("Human menu audit events are immutable."))
        return super().write(values)

    def unlink(self):
        if (
            any(record.event_type == "human_menu_action" for record in self)
            and not self.env.context.get("module_uninstall")
        ):
            raise UserError(_("Human menu audit events cannot be deleted."))
        return super().unlink()


class WuchangMemberGroupRegistrationBatchMenuBinding(models.Model):
    _inherit = "wuchang.member.group.registration.batch"

    menu_company_id = fields.Many2one(
        "res.company",
        string="Menu Operating Company",
        index=True,
        help="Company whose Odoo POS menu is governed by this group onboarding record.",
    )
    responsible_menu_reviewer_user_id = fields.Many2one(
        "res.users",
        string="Single Operating Account",
        index=True,
        help=(
            "One Odoo account bound to the responsible natural person, including when that person holds multiple duties. "
            "Only a member governance admin can create or change this binding."
        ),
    )

    @api.model_create_multi
    def create(self, vals_list):
        if any(
            values.get("responsible_menu_reviewer_user_id")
            or values.get("menu_company_id")
            for values in vals_list
        ) and not self.env.user.has_group(GOVERNANCE_ADMIN_GROUP):
            raise UserError(
                _("Only a member governance admin can bind a menu responsible reviewer.")
            )
        return super().create(vals_list)

    def write(self, values):
        if {
            "responsible_menu_reviewer_user_id",
            "menu_company_id",
        } & set(values) and not self.env.user.has_group(GOVERNANCE_ADMIN_GROUP):
            raise UserError(
                _("Only a member governance admin can change the menu reviewer binding.")
            )
        return super().write(values)


class ProductTemplateMenuGovernance(models.Model):
    _inherit = "product.template"

    _RESPONSIBLE_WRITE_FIELDS = {
        "name",
        "list_price",
        "pos_categ_ids",
        "image_1920",
        "wuchang_option_group_id",
        "available_in_pos",
        "active",
    }
    _RESPONSIBLE_CREATE_FIELDS = _RESPONSIBLE_WRITE_FIELDS | {
        "company_id",
        "sale_ok",
        "purchase_ok",
        "type",
    }
    _sql_constraints = [
        (
            "wuchang_w5c_code_unique",
            "unique(w5c_code)",
            "The Total Field product thing code must be unique.",
        ),
    ]

    @api.model
    def _wuchang_menu_is_responsible(self):
        return self.env.user.has_group(RESPONSIBLE_GROUP)

    @api.model
    def _wuchang_menu_is_remote_support(self):
        return self.env.user.has_group(REMOTE_SUPPORT_GROUP)

    @api.model
    def _wuchang_responsible_batch(self, company=None):
        company = company or self.env.company
        batches = self.env["wuchang.member.group.registration.batch"].sudo().search(
            [
                ("business_onboarding_enabled", "=", True),
                ("business_onboarding_state", "=", "operational_ready"),
                ("menu_company_id", "=", company.id),
                ("responsible_menu_reviewer_user_id", "=", self.env.user.id),
            ],
            limit=2,
        )
        if len(batches) != 1:
            raise UserError(
                _(
                    "This account needs exactly one operational business binding for the current company before it can maintain the cafe menu."
                )
            )
        return batches

    @api.model
    def _wuchang_assert_responsible_values(self, values, *, creating=False):
        allowed = (
            self._RESPONSIBLE_CREATE_FIELDS
            if creating
            else self._RESPONSIBLE_WRITE_FIELDS
        )
        unknown = set(values) - allowed
        if unknown:
            raise UserError(
                _("The safe cafe menu surface does not allow these fields: %s")
                % ", ".join(sorted(unknown))
            )
        if "list_price" in values:
            price = values["list_price"]
            if isinstance(price, bool) or not isinstance(price, (int, float)):
                raise UserError(_("Menu price must be a number."))
            if price < 0:
                raise UserError(_("Menu price cannot be negative."))
        if "name" in values and not str(values["name"] or "").strip():
            raise UserError(_("Menu item name is required."))

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("wuchang_menu_internal_write"):
            records = super().create(vals_list)
            records._wuchang_ensure_menu_identity()
            return records
        if (
            self._wuchang_menu_is_remote_support()
            and not self._wuchang_menu_is_responsible()
        ):
            raise UserError(
                _("Remote support must submit a menu change request; direct product creation is blocked.")
            )
        if self._wuchang_menu_is_responsible():
            batch = self._wuchang_responsible_batch()
            safe_values = []
            for values in vals_list:
                values = dict(values)
                self._wuchang_assert_responsible_values(values, creating=True)
                values.update(
                    {
                        "name": str(values.get("name") or "").strip(),
                        "company_id": batch.menu_company_id.id,
                        "sale_ok": True,
                        "purchase_ok": False,
                        "type": "consu",
                        "available_in_pos": True,
                        "w5c_authority": "GROUP_RESPONSIBLE_PERSON",
                        "w5c_topology": batch.group_ref,
                    }
                )
                safe_values.append(values)
            records = super(ProductTemplateMenuGovernance, self.sudo()).create(
                safe_values
            )
            records._wuchang_ensure_menu_identity()
            for record in records.with_env(self.env):
                record._wuchang_log_menu_event(
                    action="CREATE_ONE_MENU_ITEM",
                    batch=batch,
                    before={},
                )
            return records.with_env(self.env)
        records = super().create(vals_list)
        records._wuchang_ensure_menu_identity()
        return records

    def write(self, values):
        if self.env.context.get("wuchang_menu_internal_write"):
            return super().write(values)
        if (
            self._wuchang_menu_is_remote_support()
            and not self._wuchang_menu_is_responsible()
        ):
            raise UserError(
                _("Remote support must submit a menu change request; direct product editing is blocked.")
            )
        if self._wuchang_menu_is_responsible():
            self._wuchang_assert_responsible_values(values)
            events = []
            for record in self:
                batch = record._wuchang_responsible_batch(
                    record.company_id or self.env.company
                )
                if not (
                    record.available_in_pos
                    or record.w5c_domain == "CAFE"
                    or record.wuchang_option_group_id
                ):
                    raise UserError(
                        _("This safe surface can only change cafe POS menu items.")
                    )
                record._wuchang_ensure_menu_identity()
                before = record.wuchang_menu_snapshot()
                super(
                    ProductTemplateMenuGovernance,
                    record.sudo().with_context(wuchang_menu_internal_write=True),
                ).write(values)
                events.append((record, batch, before))
            self._wuchang_ensure_menu_identity()
            for record, batch, before in events:
                record._wuchang_log_menu_event(
                    action="CHANGE_ONE_MENU_ITEM",
                    batch=batch,
                    before=before,
                )
            return True
        result = super().write(values)
        self._wuchang_ensure_menu_identity()
        return result

    def unlink(self):
        if self._wuchang_menu_is_responsible() or self._wuchang_menu_is_remote_support():
            raise UserError(
                _("Cafe menu items cannot be deleted from this surface. Archive the item to preserve its code and audit history.")
            )
        return super().unlink()

    def _wuchang_ensure_menu_identity(self):
        for record in self.sudo():
            managed_menu = bool(
                record.available_in_pos
                or record.w5c_domain == "CAFE"
                or record.wuchang_option_group_id
            )
            if not managed_menu:
                continue
            values = {}
            if record.available_in_pos and not record.w5c_code:
                values.update(
                    {
                        "w5c_code": build_odoo_product_thing_code(
                            record.company_id.id or self.env.company.id,
                            record.id,
                        ),
                        "w5c_domain": record.w5c_domain or "CAFE",
                        "w5c_entity": record.w5c_entity or "PRODUCT",
                        "w5c_topology": record.w5c_topology
                        or f"ODOO_COMPANY_{record.company_id.id or self.env.company.id}",
                        "w5c_authority": record.w5c_authority or "ODOO_MANAGER",
                    }
                )
            expected_time_state = "ACTIVE" if record.active else "RETIRED_EVIDENCE"
            if record.w5c_time_state != expected_time_state:
                values["w5c_time_state"] = expected_time_state
            if values:
                super(
                    ProductTemplateMenuGovernance,
                    record.with_context(wuchang_menu_internal_write=True),
                ).write(values)

    def action_wuchang_menu_archive(self):
        self.ensure_one()
        if not self._wuchang_menu_is_responsible():
            raise UserError(_("Only the bound cafe menu responsible person can archive an item."))
        return self.write({"active": False, "available_in_pos": False})

    def action_wuchang_menu_reactivate(self):
        self.ensure_one()
        if not self._wuchang_menu_is_responsible():
            raise UserError(_("Only the bound cafe menu responsible person can reactivate an item."))
        return self.write({"active": True, "available_in_pos": True})

    def wuchang_menu_snapshot(self):
        self.ensure_one()
        image = self.image_1920 or b""
        if isinstance(image, str):
            image = image.encode("ascii")
        return {
            "thing_code": self.w5c_code or "",
            "name": self.name,
            "list_price": self.list_price,
            "pos_category_ids": sorted(self.pos_categ_ids.ids),
            "option_group_id": self.wuchang_option_group_id.id or None,
            "image_sha256": hashlib.sha256(bytes(image)).hexdigest() if image else None,
            "available_in_pos": bool(self.available_in_pos),
            "active": bool(self.active),
        }

    def _wuchang_log_menu_event(self, *, action, batch, before):
        self.ensure_one()
        after = self.wuchang_menu_snapshot()
        event_time = fields.Datetime.now()
        payload = {
            "schema_version": "W7TP-ODOO-CAFE-MENU-HUMAN-EVENT/1.0",
            "who": f"odoo-user:{self.env.user.id}",
            "where": {
                "group_ref": batch.group_ref,
                "store_ref": batch.store_ref,
                "company_id": batch.menu_company_id.id,
            },
            "when": fields.Datetime.to_string(event_time).replace(" ", "T") + "Z",
            "what": action,
            "before": before,
            "after": after,
            "single_human_identity_single_account": True,
        }
        payload["content_sha256"] = stable_sha256(payload)
        self.env["wuchang.cafe.ai.eventbook"].sudo().create(
            {
                "name": f"{action}:{self.w5c_code[-12:]}",
                "event_type": "human_menu_action",
                "source": "odoo_safe_menu_manager",
                "session_ref": self.w5c_code,
                "user_role": "SINGLE_ACCOUNT_MULTI_ROLE",
                "intent": action,
                "tool_name": "wuchang_cafe_menu_safe_manager",
                "risk_level": "low",
                "confirmation_required": False,
                "confirmation_result": "EXPLICIT_HUMAN_ACTION",
                "target_model": "product.template",
                "target_record_id": str(self.id),
                "result": "success",
                "payload_json": json.dumps(
                    payload, ensure_ascii=False, indent=2, sort_keys=True
                ),
            }
        )
