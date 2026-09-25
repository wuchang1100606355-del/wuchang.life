from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.menu_change_governance import build_odoo_thing_code
from .menu_manager import (
    REMOTE_SUPPORT_GROUP,
    RESPONSIBLE_GROUP,
    build_human_menu_event_values,
    schedule_rejected_menu_event,
)


class WuchangCafeOptionGovernanceMixin(models.AbstractModel):
    _name = "wuchang.cafe.option.governance.mixin"
    _description = "WuChang Cafe Option Governance Mixin"

    _WUCHANG_THING_CLASS = None
    _WUCHANG_CREATE_FIELDS = set()
    _WUCHANG_WRITE_FIELDS = set()
    _WUCHANG_SNAPSHOT_FIELDS = ()

    @api.model
    def _wuchang_option_is_responsible(self):
        return self.env.user.has_group(RESPONSIBLE_GROUP)

    @api.model
    def _wuchang_option_is_remote_support(self):
        return self.env.user.has_group(REMOTE_SUPPORT_GROUP)

    def _wuchang_option_snapshot(self):
        self.ensure_one()
        snapshot = {"thing_code": self.w5c_code or ""}
        for field_name in self._WUCHANG_SNAPSHOT_FIELDS:
            field = self._fields[field_name]
            value = self[field_name]
            if field.type == "many2one":
                value = value.id or None
            elif field.type in {"one2many", "many2many"}:
                value = sorted(value.ids)
            snapshot[field_name] = value
        return snapshot

    @api.model
    def _wuchang_reject_option_operation(
        self, *, action, records=None, rejected_fields=None
    ):
        records = records or self
        before = [record._wuchang_option_snapshot() for record in records]
        schedule_rejected_menu_event(
            self.env,
            build_human_menu_event_values(
                actor_user_id=self.env.user.id,
                action=action,
                result="rejected",
                event_time=fields.Datetime.now(),
                where={"company_id": self.env.company.id, "entrypoint": "odoo_rpc"},
                target_model=self._name,
                target_record_id=",".join(str(record.id) for record in records) or "new",
                target_thing_code=records[:1].w5c_code if records else None,
                before=before,
                after=before,
                source="odoo_safe_menu_options",
                source_ref=f"{self._name}:rpc",
                detail={"rejected_fields": sorted(rejected_fields or [])}
                if rejected_fields
                else None,
            ),
        )

    @api.model
    def _wuchang_assert_option_values(self, values, *, creating=False):
        allowed = (
            self._WUCHANG_CREATE_FIELDS
            if creating
            else self._WUCHANG_WRITE_FIELDS
        )
        unknown = set(values) - allowed
        if unknown:
            self._wuchang_reject_option_operation(
                action="REJECT_UNAUTHORIZED_OPTION_FIELDS",
                rejected_fields=unknown,
            )
            raise UserError(
                _("The safe cafe specification surface does not allow these fields: %s")
                % ", ".join(sorted(unknown))
            )

    @api.model_create_multi
    def create(self, vals_list):
        internal = self.env.context.get("wuchang_option_internal_write") and self.env.su
        if self._wuchang_option_is_remote_support() and not self._wuchang_option_is_responsible() and not internal:
            self._wuchang_reject_option_operation(
                action="REJECT_REMOTE_SUPPORT_DIRECT_OPTION_CREATE"
            )
            raise UserError(_("Remote support cannot directly create formal cafe specifications."))
        if self._wuchang_option_is_responsible() and not internal:
            for values in vals_list:
                self._wuchang_assert_option_values(values, creating=True)
        records = super().create(vals_list)
        records._wuchang_ensure_option_identity()
        if not internal:
            for record in records:
                record._wuchang_log_option_event("CREATE_FORMAL_CAFE_SPECIFICATION", {})
        return records

    def write(self, values):
        internal = self.env.context.get("wuchang_option_internal_write") and self.env.su
        if internal:
            return super().write(values)
        if "w5c_code" in values and any(
            record.w5c_code and values.get("w5c_code") != record.w5c_code
            for record in self
        ):
            self._wuchang_reject_option_operation(
                action="REJECT_OPTION_THING_CODE_REWRITE",
                rejected_fields={"w5c_code"},
            )
            raise UserError(_("The Total Field specification thing code is immutable after creation."))
        if self._wuchang_option_is_remote_support() and not self._wuchang_option_is_responsible():
            self._wuchang_reject_option_operation(
                action="REJECT_REMOTE_SUPPORT_DIRECT_OPTION_WRITE"
            )
            raise UserError(_("Remote support cannot directly edit formal cafe specifications."))
        if self._wuchang_option_is_responsible():
            self._wuchang_assert_option_values(values)
        before = {record.id: record._wuchang_option_snapshot() for record in self}
        result = super().write(values)
        self._wuchang_ensure_option_identity()
        for record in self:
            record._wuchang_log_option_event(
                "CHANGE_FORMAL_CAFE_SPECIFICATION", before[record.id]
            )
        return result

    def unlink(self):
        if self and not self.env.context.get("module_uninstall"):
            self._wuchang_reject_option_operation(
                action="REJECT_DELETE_FORMAL_CAFE_SPECIFICATION"
            )
            raise UserError(
                _("Cafe specifications cannot be deleted. Archive them to preserve their code and history.")
            )
        return super().unlink()

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update({"w5c_code": False, "w5c_time_state": False})
        copied = super(
            WuchangCafeOptionGovernanceMixin,
            self.sudo().with_context(wuchang_option_internal_write=True),
        ).copy(default)
        copied._wuchang_ensure_option_identity()
        return copied.with_env(self.env)

    def _wuchang_ensure_option_identity(self):
        for record in self.sudo():
            values = {}
            if not record.w5c_code:
                values.update(
                    {
                        "w5c_code": build_odoo_thing_code(
                            record._WUCHANG_THING_CLASS,
                            record.env.company.id,
                            f"{record._name}:{record.id}",
                        ),
                        "w5c_domain": record.w5c_domain or "CAFE",
                        "w5c_entity": record.w5c_entity
                        or record._WUCHANG_THING_CLASS,
                        "w5c_topology": record.w5c_topology
                        or f"ODOO_COMPANY_{record.env.company.id}",
                        "w5c_authority": record.w5c_authority or "ODOO_MANAGER",
                    }
                )
            expected_state = "ACTIVE" if record.active else "RETIRED_EVIDENCE"
            if record.w5c_time_state != expected_state:
                values["w5c_time_state"] = expected_state
            if values:
                super(
                    WuchangCafeOptionGovernanceMixin,
                    record.with_context(wuchang_option_internal_write=True),
                ).write(values)

    def _wuchang_log_option_event(self, action, before):
        self.ensure_one()
        self.env["wuchang.cafe.ai.eventbook"].sudo().create(
            build_human_menu_event_values(
                actor_user_id=self.env.user.id,
                action=action,
                result="success",
                event_time=fields.Datetime.now(),
                where={"company_id": self.env.company.id, "entrypoint": "odoo_manager"},
                target_model=self._name,
                target_record_id=self.id,
                target_thing_code=self.w5c_code,
                before=before,
                after=self._wuchang_option_snapshot(),
                source="odoo_safe_menu_options",
                source_ref=f"{self._name}:{self.id}",
            )
        )


class WuchangCafeOptionGroup(models.Model):
    _name = "wuchang.cafe.option.group"
    _inherit = "wuchang.cafe.option.governance.mixin"
    _description = "WuChang Cafe POS Option Group"
    _order = "sequence, code"

    _WUCHANG_THING_CLASS = "OPTION_GROUP"
    _WUCHANG_CREATE_FIELDS = {
        "sequence", "active", "code", "name", "note", "question_ids",
    }
    _WUCHANG_WRITE_FIELDS = {
        "sequence", "active", "name", "note", "question_ids",
    }
    _WUCHANG_SNAPSHOT_FIELDS = (
        "sequence", "active", "code", "name", "note", "question_ids",
    )

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    source = fields.Char(default="quickclick")
    note = fields.Text()

    w5c_code = fields.Char(index=True)
    w5c_domain = fields.Char(index=True, default="CAFE")
    w5c_entity = fields.Char(index=True, default="OPTION_GROUP")
    w5c_topology = fields.Char(index=True)
    w5c_time_state = fields.Char(index=True)
    w5c_authority = fields.Char(index=True)

    question_ids = fields.One2many("wuchang.cafe.option.question", "group_id")


class WuchangCafeOptionQuestion(models.Model):
    _name = "wuchang.cafe.option.question"
    _inherit = "wuchang.cafe.option.governance.mixin"
    _description = "WuChang Cafe POS Option Question"
    _order = "group_id, sequence, name"

    _WUCHANG_THING_CLASS = "OPTION_QUESTION"
    _WUCHANG_CREATE_FIELDS = {
        "sequence", "active", "group_id", "name", "display_name",
        "selection_type", "required", "item_ids",
    }
    _WUCHANG_WRITE_FIELDS = {
        "sequence", "active", "name", "display_name", "selection_type",
        "required", "item_ids",
    }
    _WUCHANG_SNAPSHOT_FIELDS = (
        "sequence", "active", "group_id", "name", "display_name",
        "selection_type", "required", "item_ids",
    )

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    group_id = fields.Many2one("wuchang.cafe.option.group", required=True, index=True, ondelete="cascade")
    name = fields.Char(required=True)
    display_name = fields.Char()
    selection_type = fields.Selection([
        ("single", "Single"),
        ("multiple", "Multiple"),
    ], default="single", required=True)
    required = fields.Boolean(default=True)
    quickclick_question_code = fields.Char(index=True)

    w5c_code = fields.Char(index=True)
    w5c_domain = fields.Char(index=True, default="CAFE")
    w5c_entity = fields.Char(index=True, default="OPTION_QUESTION")
    w5c_topology = fields.Char(index=True)
    w5c_time_state = fields.Char(index=True)
    w5c_authority = fields.Char(index=True)

    item_ids = fields.One2many("wuchang.cafe.option.item", "question_id")


class WuchangCafeOptionItem(models.Model):
    _name = "wuchang.cafe.option.item"
    _inherit = "wuchang.cafe.option.governance.mixin"
    _description = "WuChang Cafe POS Option Item"
    _order = "question_id, sequence, name"

    _WUCHANG_THING_CLASS = "OPTION_ITEM"
    _WUCHANG_CREATE_FIELDS = {
        "sequence", "active", "question_id", "name", "display_name",
        "price_delta", "child_group_id", "note",
    }
    _WUCHANG_WRITE_FIELDS = {
        "sequence", "active", "name", "display_name", "price_delta",
        "child_group_id", "note",
    }
    _WUCHANG_SNAPSHOT_FIELDS = (
        "sequence", "active", "question_id", "name", "display_name",
        "price_delta", "child_group_id", "note",
    )

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    question_id = fields.Many2one("wuchang.cafe.option.question", required=True, index=True, ondelete="cascade")
    name = fields.Char(required=True)
    display_name = fields.Char()
    price_delta = fields.Float(default=0.0)
    child_group_code = fields.Char(index=True)
    child_group_id = fields.Many2one("wuchang.cafe.option.group", string="Child Option Group")
    quickclick_item_code = fields.Char(index=True)
    quickclick_question_code = fields.Char(index=True)
    note = fields.Text()

    w5c_code = fields.Char(index=True)
    w5c_domain = fields.Char(index=True, default="CAFE")
    w5c_entity = fields.Char(index=True, default="OPTION_ITEM")
    w5c_topology = fields.Char(index=True)
    w5c_time_state = fields.Char(index=True)
    w5c_authority = fields.Char(index=True)


class WuchangCafeAiVirtualVariant(models.Model):
    _name = "wuchang.cafe.ai.virtual.variant"
    _description = "WuChang Cafe AI W5C Virtual Variant"
    _order = "last_order_time desc, usage_count desc, id desc"

    active = fields.Boolean(default=True, index=True)
    product_template_id = fields.Many2one("product.template", required=True, index=True, ondelete="cascade")
    quickclick_product_id = fields.Char(index=True)
    quickclick_sku = fields.Char(index=True)
    option_group_code = fields.Char(index=True)
    selected_option_json = fields.Json()
    virtual_variant_signature = fields.Char(index=True)
    virtual_variant_hash = fields.Char(index=True)
    w5c_code = fields.Char(index=True)
    price_delta_total = fields.Float(default=0.0)
    price_total = fields.Float(default=0.0)
    usage_count = fields.Integer(default=0)
    last_order_time = fields.Datetime(index=True)
    ai_recommend_score = fields.Float(default=0.0)
    w5c_domain = fields.Char(index=True, default="CAFE")
    w5c_entity = fields.Char(index=True, default="VIRTUAL_VARIANT")
    w5c_topology = fields.Char(index=True)
    w5c_time_state = fields.Char(index=True)
    w5c_authority = fields.Char(index=True)
    note = fields.Text()


class ProductTemplate(models.Model):
    _inherit = "product.template"

    quickclick_menu_id = fields.Char(index=True)
    quickclick_product_id = fields.Char(index=True)
    quickclick_product_code = fields.Char(index=True)
    quickclick_sku = fields.Char(index=True)
    quickclick_option_group_code = fields.Char(index=True)
    quickclick_image_url = fields.Char()
    quickclick_raw_category = fields.Char(index=True)
    quickclick_raw_price = fields.Float()
    normalized_price_basis = fields.Char(index=True)
    normalized_price_note = fields.Text()
    wuchang_pos_locked = fields.Boolean(default=False, index=True)
    wuchang_option_group_id = fields.Many2one("wuchang.cafe.option.group", string="WuChang POS Option Group")

    w5c_code = fields.Char(index=True)
    w5c_domain = fields.Char(index=True)
    w5c_entity = fields.Char(index=True)
    w5c_topology = fields.Char(index=True)
    w5c_time_state = fields.Char(index=True)
    w5c_authority = fields.Char(index=True)
