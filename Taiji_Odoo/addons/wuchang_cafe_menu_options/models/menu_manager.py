"""Least-privilege Odoo product surface for cafe menu responsible persons."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import secrets
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.exceptions import UserError
from odoo.modules.registry import Registry

from ..services.menu_change_governance import (
    MenuChangeGovernanceError,
    build_cafe_pos_intent_field_request,
    build_odoo_product_thing_code,
    project_cafe_pos_total_field_response,
    stable_sha256,
)


RESPONSIBLE_GROUP = "wuchang_cafe_menu_options.group_wuchang_cafe_menu_responsible"
REMOTE_SUPPORT_GROUP = "wuchang_cafe_menu_options.group_wuchang_cafe_remote_support"
GOVERNANCE_ADMIN_GROUP = "wuchang_member_registration.group_wuchang_member_admin"


class _WuchangNoRedirect(urllib_request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def build_human_menu_event_values(
    *,
    actor_user_id,
    action,
    result,
    event_time,
    where,
    target_model,
    target_record_id,
    target_thing_code,
    before,
    after,
    source,
    source_ref=None,
    candidate_ref=None,
    authorization_event_ref=None,
    detail=None,
    confirmation_required=False,
):
    """Build one deterministic, public-safe eventbook value mapping."""

    payload = {
        "schema_version": "W7TP-ODOO-CAFE-MENU-HUMAN-EVENT/2.0",
        "actor": f"odoo-user:{actor_user_id}",
        "where": where,
        "when": fields.Datetime.to_string(event_time).replace(" ", "T") + "Z",
        "what": action,
        "target_thing_code": target_thing_code or None,
        "before": before,
        "after": after,
        "source_ref": source_ref,
        "candidate_ref": candidate_ref,
        "authorization_event_ref": authorization_event_ref,
        "single_human_identity_single_account": True,
    }
    if detail:
        payload["detail"] = detail
    payload["content_sha256"] = stable_sha256(payload)
    event_ref = target_thing_code or candidate_ref or source_ref or payload["content_sha256"]
    return {
        "name": f"{action}:{payload['content_sha256'][:12]}",
        "event_type": "human_menu_action",
        "source": source,
        "session_ref": event_ref,
        "user_role": "SINGLE_ACCOUNT_MULTI_ROLE",
        "intent": action,
        "tool_name": "wuchang_cafe_menu_governance",
        "risk_level": "medium" if result != "success" else "low",
        "confirmation_required": confirmation_required,
        "confirmation_result": result.upper(),
        "target_model": target_model,
        "target_record_id": str(target_record_id),
        "result": result,
        "payload_json": json.dumps(
            payload, ensure_ascii=False, indent=2, sort_keys=True
        ),
    }


def schedule_rejected_menu_event(env, event_values):
    """Persist a true rejection only after the failed RPC transaction rolls back."""

    dbname = env.cr.dbname
    safe_values = dict(event_values)

    def _persist_after_rollback():
        with Registry(dbname).cursor() as cursor:
            callback_env = api.Environment(cursor, SUPERUSER_ID, {})
            callback_env["wuchang.cafe.ai.eventbook"].sudo().create(safe_values)
            cursor.commit()

    env.cr.postrollback.add(_persist_after_rollback)


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
            before = [record.wuchang_menu_snapshot() for record in self]
            schedule_rejected_menu_event(
                self.env,
                build_human_menu_event_values(
                    actor_user_id=self.env.user.id,
                    action="REJECT_UNAUTHORIZED_MENU_FIELDS",
                    result="rejected",
                    event_time=fields.Datetime.now(),
                    where={"company_id": self.env.company.id, "entrypoint": "odoo_rpc"},
                    target_model="product.template",
                    target_record_id=",".join(str(record.id) for record in self) or "new",
                    target_thing_code=self[:1].w5c_code if self else None,
                    before=before,
                    after=before,
                    source="odoo_safe_menu_manager",
                    source_ref="product.template:create" if creating else "product.template:write",
                    detail={"rejected_fields": sorted(unknown)},
                ),
            )
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
        if self.env.context.get("wuchang_menu_internal_write") and self.env.su:
            records = super().create(vals_list)
            records._wuchang_ensure_menu_identity()
            return records
        if (
            self._wuchang_menu_is_remote_support()
            and not self._wuchang_menu_is_responsible()
        ):
            schedule_rejected_menu_event(
                self.env,
                build_human_menu_event_values(
                    actor_user_id=self.env.user.id,
                    action="REJECT_REMOTE_SUPPORT_DIRECT_CREATE",
                    result="rejected",
                    event_time=fields.Datetime.now(),
                    where={"company_id": self.env.company.id, "entrypoint": "odoo_rpc"},
                    target_model="product.template",
                    target_record_id="new",
                    target_thing_code=None,
                    before={},
                    after={},
                    source="odoo_safe_menu_manager",
                    source_ref="remote-support:candidate-only",
                    confirmation_required=True,
                ),
            )
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
        if self.env.context.get("wuchang_menu_internal_write") and self.env.su:
            return super().write(values)
        if "w5c_code" in values and any(
            record.w5c_code and values.get("w5c_code") != record.w5c_code
            for record in self
        ):
            before = [record.wuchang_menu_snapshot() for record in self]
            schedule_rejected_menu_event(
                self.env,
                build_human_menu_event_values(
                    actor_user_id=self.env.user.id,
                    action="REJECT_THING_CODE_REWRITE",
                    result="rejected",
                    event_time=fields.Datetime.now(),
                    where={"company_id": self.env.company.id, "entrypoint": "odoo_rpc"},
                    target_model="product.template",
                    target_record_id=",".join(str(record.id) for record in self),
                    target_thing_code=self[:1].w5c_code if self else None,
                    before=before,
                    after=before,
                    source="odoo_safe_menu_manager",
                    source_ref="product.template:write",
                    detail={"rejected_fields": ["w5c_code"]},
                ),
            )
            raise UserError(_("The Total Field product thing code is immutable after creation."))
        if (
            self._wuchang_menu_is_remote_support()
            and not self._wuchang_menu_is_responsible()
        ):
            before = [record.wuchang_menu_snapshot() for record in self]
            schedule_rejected_menu_event(
                self.env,
                build_human_menu_event_values(
                    actor_user_id=self.env.user.id,
                    action="REJECT_REMOTE_SUPPORT_DIRECT_WRITE",
                    result="rejected",
                    event_time=fields.Datetime.now(),
                    where={"company_id": self.env.company.id, "entrypoint": "odoo_rpc"},
                    target_model="product.template",
                    target_record_id=",".join(str(record.id) for record in self),
                    target_thing_code=self[:1].w5c_code if self else None,
                    before=before,
                    after=before,
                    source="odoo_safe_menu_manager",
                    source_ref="remote-support:candidate-only",
                    confirmation_required=True,
                ),
            )
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
        managed = self.filtered(
            lambda record: record.available_in_pos
            or record.w5c_domain == "CAFE"
            or record.wuchang_option_group_id
        )
        if managed and not self.env.context.get("module_uninstall"):
            before = [record.wuchang_menu_snapshot() for record in managed]
            schedule_rejected_menu_event(
                self.env,
                build_human_menu_event_values(
                    actor_user_id=self.env.user.id,
                    action="REJECT_DELETE_MENU_ITEM",
                    result="rejected",
                    event_time=fields.Datetime.now(),
                    where={"company_id": self.env.company.id, "entrypoint": "odoo_rpc"},
                    target_model="product.template",
                    target_record_id=",".join(str(record.id) for record in managed),
                    target_thing_code=managed[:1].w5c_code,
                    before=before,
                    after=before,
                    source="odoo_safe_menu_manager",
                    source_ref="product.template:unlink",
                ),
            )
            raise UserError(
                _("Cafe menu items cannot be deleted from this surface. Archive the item to preserve its code and audit history.")
            )
        return super().unlink()

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update(
            {
                "w5c_code": False,
                "w5c_time_state": False,
                "w5c_authority": "ODOO_DUPLICATE",
            }
        )
        copied = super(
            ProductTemplateMenuGovernance,
            self.sudo().with_context(wuchang_menu_internal_write=True),
        ).copy(default)
        copied._wuchang_ensure_menu_identity()
        return copied.with_env(self.env)

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

    @api.model
    def _wuchang_total_field_endpoint(self):
        endpoint = str(
            self.env["ir.config_parameter"].sudo().get_param(
                "wuchang_cafe_menu_options.intent_field_endpoint", ""
            )
            or ""
        ).strip()
        try:
            parsed = urllib_parse.urlsplit(endpoint)
            host = parsed.hostname or ""
            port = parsed.port
            address = ipaddress.ip_address(host)
        except (ValueError, TypeError) as exc:
            raise UserError(_("The private Total Field endpoint is invalid.")) from exc
        if (
            parsed.scheme != "http"
            or port != 9107
            or parsed.path != "/api/intent-field"
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
            or address.is_unspecified
            or address.is_multicast
            or not (address.is_private or address.is_loopback)
        ):
            raise UserError(_("Only the exact private 9107 intent-field endpoint is allowed."))
        return endpoint

    @api.model
    def _wuchang_total_field_caller(self):
        caller_ref = str(
            self.env["ir.config_parameter"].sudo().get_param(
                "wuchang_cafe_menu_options.total_field_caller_ref", ""
            )
            or ""
        ).strip()
        prefix = "odoo-pos-config:"
        if not caller_ref.startswith(prefix):
            raise UserError(_("A configured Odoo POS caller reference is required."))
        pos_config = self.env.ref(
            caller_ref[len(prefix):], raise_if_not_found=False
        )
        if not pos_config or pos_config._name != "pos.config":
            raise UserError(_("The configured Odoo POS caller reference does not resolve."))
        return caller_ref, pos_config

    @api.model
    def _wuchang_post_intent_field(self, endpoint, payload):
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        outbound = urllib_request.Request(
            endpoint,
            data=encoded,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.build_opener(_WuchangNoRedirect).open(
                outbound, timeout=5
            ) as response:
                if response.status != 200:
                    raise UserError(_("Total Field returned a non-success status."))
                raw = response.read(256 * 1024 + 1)
        except (urllib_error.HTTPError, urllib_error.URLError, OSError) as exc:
            raise UserError(_("The private Total Field service is unavailable.")) from exc
        if len(raw) > 256 * 1024:
            raise UserError(_("The Total Field response exceeded the safe size limit."))
        try:
            result = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise UserError(_("The Total Field response is not valid JSON.")) from exc
        if not isinstance(result, dict):
            raise UserError(_("The Total Field response must be an object."))
        return result

    def action_wuchang_submit_cafe_pos_candidate(self):
        self.ensure_one()
        if not (self.env.su or self._wuchang_menu_is_responsible()):
            raise UserError(_("Only the cafe menu responsible person can submit a Total Field candidate."))
        if not self.available_in_pos:
            raise UserError(_("An existing POS menu item is required."))
        caller_ref, pos_config = self._wuchang_total_field_caller()
        if (
            self.company_id
            and pos_config.company_id
            and self.company_id != pos_config.company_id
        ):
            raise UserError(_("The menu item belongs to a different Odoo POS company."))
        product_thing_code = self.w5c_code or build_odoo_product_thing_code(
            self.company_id.id or self.env.company.id,
            self.id,
        )
        request_id = f"odoo-cafe:{secrets.token_hex(16)}"
        observation_domain_ref = (
            "observation-domain:odoo-cafe:"
            + stable_sha256({"caller_ref": caller_ref})[:24]
        )
        try:
            payload = build_cafe_pos_intent_field_request(
                request_id=request_id,
                caller_ref=caller_ref,
                observation_domain_ref=observation_domain_ref,
                product_thing_code=product_thing_code,
                product_snapshot_sha256=stable_sha256(
                    self.wuchang_menu_snapshot()
                ),
                pos_category_sha256=stable_sha256(
                    sorted(self.pos_categ_ids.ids)
                ),
            )
            response = self._wuchang_post_intent_field(
                self._wuchang_total_field_endpoint(), payload
            )
            projection = project_cafe_pos_total_field_response(
                response,
                request_id=request_id,
                caller_ref=caller_ref,
            )
        except MenuChangeGovernanceError as exc:
            raise UserError(_("Total Field candidate blocked: %s") % exc) from exc
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Total Field candidate receipt"),
                "message": _(
                    "Request %(request_id)s · decision %(decision)s · receipt %(receipt)s"
                )
                % {
                    "request_id": projection["request_id"],
                    "decision": projection["total_field_decision"],
                    "receipt": projection["receipt_sha256"],
                },
                "type": (
                    "success"
                    if projection["total_field_decision"] == "ALLOW"
                    else "warning"
                ),
                "sticky": True,
                "w7tp_projection": projection,
            },
        }

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
        self.env["wuchang.cafe.ai.eventbook"].sudo().create(
            build_human_menu_event_values(
                actor_user_id=self.env.user.id,
                action=action,
                result="success",
                event_time=event_time,
                where={
                    "group_ref": batch.group_ref,
                    "store_ref": batch.store_ref,
                    "company_id": batch.menu_company_id.id,
                },
                target_model="product.template",
                target_record_id=self.id,
                target_thing_code=self.w5c_code,
                before=before,
                after=after,
                source="odoo_safe_menu_manager",
                source_ref=f"product.template:{self.id}",
            )
        )
