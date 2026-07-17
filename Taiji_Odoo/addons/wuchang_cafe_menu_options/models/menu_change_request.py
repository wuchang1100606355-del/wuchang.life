"""Human-reviewed remote support changes for one Odoo cafe menu item."""

from __future__ import annotations

import hashlib
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.menu_change_governance import (
    MenuChangeGovernanceError,
    build_menu_change_candidate,
    build_responsible_approval_seal,
    stable_sha256,
)
from .menu_manager import (
    GOVERNANCE_ADMIN_GROUP,
    REMOTE_SUPPORT_GROUP,
    RESPONSIBLE_GROUP,
)


class WuchangCafeMenuChangeRequest(models.Model):
    _name = "wuchang.cafe.menu.change.request"
    _description = "WuChang Cafe Menu Change Request"
    _order = "create_date desc, id desc"

    name = fields.Char(
        default="New Menu Change",
        required=True,
        readonly=True,
        copy=False,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending_responsible_review", "Pending Responsible Review"),
            ("applied", "Applied"),
            ("rejected", "Rejected"),
            ("dead_letter", "Dead Letter"),
        ],
        default="draft",
        readonly=True,
        index=True,
        copy=False,
    )
    origin = fields.Selection(
        [
            ("merchant_manager", "Merchant Manager"),
            ("remote_support", "Remote Support"),
        ],
        required=True,
        default="merchant_manager",
        index=True,
        copy=False,
    )
    change_type = fields.Selection(
        [
            ("create", "Create Item"),
            ("update", "Update Item"),
            ("archive", "Archive Item"),
            ("reactivate", "Reactivate Item"),
        ],
        required=True,
        default="update",
    )
    group_batch_id = fields.Many2one(
        "wuchang.member.group.registration.batch",
        string="Merchant Group",
        required=True,
        index=True,
        ondelete="restrict",
        domain="[('business_onboarding_enabled', '=', True), ('business_onboarding_state', '=', 'operational_ready')]",
    )
    company_id = fields.Many2one(
        "res.company",
        related="group_batch_id.menu_company_id",
        readonly=True,
        store=True,
        index=True,
    )
    requester_user_id = fields.Many2one(
        "res.users",
        readonly=True,
        index=True,
        copy=False,
    )
    responsible_reviewer_user_id = fields.Many2one(
        "res.users",
        readonly=True,
        index=True,
        copy=False,
    )
    responsible_person_ref = fields.Char(readonly=True, copy=False)
    product_template_id = fields.Many2one(
        "product.template",
        string="Menu Item",
        index=True,
        ondelete="restrict",
        domain="[('company_id', 'in', [False, company_id])]",
    )
    applied_product_template_id = fields.Many2one(
        "product.template",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )

    change_name = fields.Boolean(default=False)
    proposed_name = fields.Char()
    change_price = fields.Boolean(default=False)
    proposed_list_price = fields.Float(string="Proposed Price")
    change_pos_categories = fields.Boolean(default=False)
    proposed_pos_category_ids = fields.Many2many(
        "pos.category",
        "wuchang_cafe_menu_change_pos_category_rel",
        "request_id",
        "category_id",
        string="Proposed POS Categories",
    )
    change_option_group = fields.Boolean(default=False)
    proposed_option_group_id = fields.Many2one(
        "wuchang.cafe.option.group",
        string="Proposed Option Group",
        ondelete="restrict",
    )
    change_image = fields.Boolean(default=False)
    proposed_image_1920 = fields.Binary(string="Proposed Product Image")
    support_reason = fields.Text(
        help="Describe the observed problem and intended correction. Do not paste credentials, payment data, or member plaintext."
    )
    responsible_review_note = fields.Text()

    current_snapshot_json = fields.Text(readonly=True, copy=False)
    proposed_values_json = fields.Text(readonly=True, copy=False)
    candidate_packet_json = fields.Text(readonly=True, copy=False)
    current_snapshot_sha256 = fields.Char(readonly=True, index=True, copy=False)
    candidate_sha256 = fields.Char(readonly=True, index=True, copy=False)
    approval_seal_json = fields.Text(readonly=True, copy=False)
    approval_sha256 = fields.Char(readonly=True, index=True, copy=False)
    reviewed_by_user_id = fields.Many2one(
        "res.users", readonly=True, copy=False
    )
    reviewed_at = fields.Datetime(readonly=True, copy=False)
    applied_at = fields.Datetime(readonly=True, copy=False)
    submitted_at = fields.Datetime(readonly=True, copy=False)
    submitted_location_ref = fields.Char(readonly=True, copy=False)
    support_reason_sha256 = fields.Char(readonly=True, copy=False)

    remote_support_direct_write = fields.Boolean(default=False, readonly=True)
    single_account_multi_role = fields.Boolean(default=False, readonly=True)
    formal_pos_order = fields.Boolean(default=False, readonly=True)
    payment_capture = fields.Boolean(default=False, readonly=True)

    _INPUT_FIELDS = {
        "origin",
        "change_type",
        "group_batch_id",
        "product_template_id",
        "change_name",
        "proposed_name",
        "change_price",
        "proposed_list_price",
        "change_pos_categories",
        "proposed_pos_category_ids",
        "change_option_group",
        "proposed_option_group_id",
        "change_image",
        "proposed_image_1920",
        "support_reason",
    }
    _PROTECTED_FIELDS = {
        "state",
        "company_id",
        "requester_user_id",
        "responsible_reviewer_user_id",
        "responsible_person_ref",
        "applied_product_template_id",
        "current_snapshot_json",
        "proposed_values_json",
        "candidate_packet_json",
        "current_snapshot_sha256",
        "candidate_sha256",
        "approval_seal_json",
        "approval_sha256",
        "reviewed_by_user_id",
        "reviewed_at",
        "applied_at",
        "submitted_at",
        "submitted_location_ref",
        "support_reason_sha256",
        "remote_support_direct_write",
        "single_account_multi_role",
        "formal_pos_order",
        "payment_capture",
    }

    @api.model_create_multi
    def create(self, vals_list):
        is_remote = self.env.user.has_group(REMOTE_SUPPORT_GROUP)
        is_responsible = self.env.user.has_group(RESPONSIBLE_GROUP)
        if not is_remote and not is_responsible:
            raise UserError(
                _("Only a cafe menu responsible person or remote support operator can create a menu change request.")
            )
        safe_list = []
        for raw_values in vals_list:
            unknown = set(raw_values) - self._INPUT_FIELDS
            if unknown:
                raise UserError(
                    _("The safe menu request does not allow these fields: %s")
                    % ", ".join(sorted(unknown))
                )
            if self._PROTECTED_FIELDS & set(raw_values):
                raise UserError(_("Protected review fields cannot be supplied by the requester."))
            values = dict(raw_values)
            origin = values.get("origin") or (
                "merchant_manager" if is_responsible else "remote_support"
            )
            if origin == "merchant_manager" and not is_responsible:
                raise UserError(_("The merchant-manager action requires the cafe menu responsible-person permission."))
            if origin == "remote_support" and not is_remote:
                raise UserError(_("The remote-support action requires the remote support permission."))
            if origin not in {"merchant_manager", "remote_support"}:
                raise UserError(_("Choose a valid menu change action context."))
            batch = self.env["wuchang.member.group.registration.batch"].browse(
                values.get("group_batch_id")
            ).exists()
            if not batch or batch.business_onboarding_state != "operational_ready":
                raise UserError(_("An operational merchant group binding is required."))
            if not batch.menu_company_id or not batch.responsible_menu_reviewer_user_id:
                raise UserError(_("The merchant group has no menu company or responsible reviewer binding."))
            values.update(
                {
                    "origin": origin,
                    "requester_user_id": self.env.user.id,
                    "responsible_reviewer_user_id": batch.responsible_menu_reviewer_user_id.id,
                    "responsible_person_ref": batch.responsible_person_ref,
                }
            )
            safe_list.append(values)
        return super().create(safe_list)

    def write(self, values):
        if self.env.context.get("wuchang_menu_request_internal_write"):
            return super().write(values)
        unknown = set(values) - self._INPUT_FIELDS - {"responsible_review_note"}
        if unknown:
            raise UserError(
                _("The safe menu request does not allow these fields: %s")
                % ", ".join(sorted(unknown))
            )
        if self._PROTECTED_FIELDS & set(values):
            raise UserError(_("Review state and seal fields can only be changed by workflow actions."))
        for request in self:
            if request.state != "draft":
                if request.state != "pending_responsible_review":
                    raise UserError(_("Completed menu-change evidence is immutable."))
                if set(values) != {"responsible_review_note"}:
                    raise UserError(_("Submitted menu changes are immutable. Create a new request instead."))
                request._assert_responsible_reviewer()
            if request.state == "draft" and request.requester_user_id != self.env.user:
                raise UserError(_("Only the requester can edit a draft menu change."))
            if request.state == "draft" and "origin" in values:
                if values["origin"] == "merchant_manager" and not self.env.user.has_group(RESPONSIBLE_GROUP):
                    raise UserError(_("The merchant-manager action requires the cafe menu responsible-person permission."))
                if values["origin"] == "remote_support" and not self.env.user.has_group(REMOTE_SUPPORT_GROUP):
                    raise UserError(_("The remote-support action requires the remote support permission."))
        if "group_batch_id" in values:
            batch = self.env["wuchang.member.group.registration.batch"].browse(
                values["group_batch_id"]
            ).exists()
            if not batch or batch.business_onboarding_state != "operational_ready":
                raise UserError(_("An operational merchant group binding is required."))
            if not batch.menu_company_id or not batch.responsible_menu_reviewer_user_id:
                raise UserError(_("The merchant group has no menu company or responsible reviewer binding."))
        result = super().write(values)
        if "group_batch_id" in values:
            for request in self:
                batch = request.group_batch_id
                super(
                    WuchangCafeMenuChangeRequest,
                    request.with_context(wuchang_menu_request_internal_write=True),
                ).write(
                    {
                        "responsible_reviewer_user_id": batch.responsible_menu_reviewer_user_id.id,
                        "responsible_person_ref": batch.responsible_person_ref,
                    }
                )
        return result

    def unlink(self):
        raise UserError(_("Menu change requests are audit evidence and cannot be deleted."))

    @api.model
    def _image_sha256(self, value):
        if not value:
            return None
        raw = value.encode("ascii") if isinstance(value, str) else bytes(value)
        return hashlib.sha256(raw).hexdigest()

    @api.model
    def _event_time_utc(self, value):
        return fields.Datetime.to_string(value).replace(" ", "T") + "Z"

    def _log_eventbook_event(self, *, action, result, event_time, payload):
        self.ensure_one()
        event_ref = self.candidate_sha256 or f"menu-change-request:{self.id}"
        event_payload = {
            "schema_version": "W7TP-ODOO-CAFE-MENU-REVIEW-EVENT/1.0",
            "who": f"odoo-user:{self.env.user.id}",
            "where": {
                "group_ref": self.group_batch_id.group_ref,
                "store_ref": self.group_batch_id.store_ref,
                "company_id": self.company_id.id,
            },
            "when": self._event_time_utc(event_time),
            "what": action,
            "request_ref": self.name,
            "evidence": payload,
            "single_human_identity_single_account": True,
        }
        event_payload["content_sha256"] = stable_sha256(event_payload)
        self.env["wuchang.cafe.ai.eventbook"].sudo().create(
            {
                "name": f"{action}:{event_ref[-12:]}",
                "event_type": "human_menu_action",
                "source": "odoo_safe_menu_review",
                "session_ref": event_ref,
                "user_role": "SINGLE_ACCOUNT_MULTI_ROLE",
                "intent": action,
                "tool_name": "wuchang_cafe_menu_change_request",
                "risk_level": "medium" if self.origin == "remote_support" else "low",
                "confirmation_required": self.origin == "remote_support",
                "confirmation_result": result.upper(),
                "target_model": "product.template",
                "target_record_id": str(
                    self.product_template_id.id
                    or self.applied_product_template_id.id
                    or "new"
                ),
                "result": result,
                "payload_json": json.dumps(
                    event_payload, ensure_ascii=False, indent=2, sort_keys=True
                ),
            }
        )

    def _proposed_values(self):
        self.ensure_one()
        if self.change_type == "create":
            values = {
                "name": str(self.proposed_name or "").strip(),
                "list_price": self.proposed_list_price,
                "pos_category_ids": sorted(self.proposed_pos_category_ids.ids),
                "option_group_id": self.proposed_option_group_id.id or None,
                "available_in_pos": True,
                "active": True,
            }
            if self.proposed_image_1920:
                values["image_sha256"] = self._image_sha256(
                    self.proposed_image_1920
                )
            return values
        if self.change_type == "archive":
            return {"active": False, "available_in_pos": False}
        if self.change_type == "reactivate":
            return {"active": True, "available_in_pos": True}
        values = {}
        if self.change_name:
            values["name"] = str(self.proposed_name or "").strip()
        if self.change_price:
            values["list_price"] = self.proposed_list_price
        if self.change_pos_categories:
            values["pos_category_ids"] = sorted(self.proposed_pos_category_ids.ids)
        if self.change_option_group:
            values["option_group_id"] = self.proposed_option_group_id.id or None
        if self.change_image:
            values["image_sha256"] = self._image_sha256(
                self.proposed_image_1920
            )
        return values

    def _current_values(self):
        self.ensure_one()
        if self.change_type == "create":
            return {}
        product = self.product_template_id.sudo().exists()
        if not product:
            raise UserError(_("An existing menu item is required for this change type."))
        if product.company_id and product.company_id != self.company_id:
            raise UserError(_("The selected item belongs to a different operating company."))
        return product.wuchang_menu_snapshot()

    def action_submit_for_responsible_review(self):
        for request in self:
            if request.state != "draft":
                raise UserError(_("Only a draft request can be submitted."))
            if request.requester_user_id != self.env.user:
                raise UserError(_("Only the requester can submit this menu change."))
            if request.change_type != "create" and not request.product_template_id:
                raise UserError(_("Select one menu item to update, archive, or reactivate."))
            if request.change_type == "create" and request.product_template_id:
                raise UserError(_("A create request cannot target an existing menu item."))
            if request.origin == "remote_support" and not str(
                request.support_reason or ""
            ).strip():
                raise UserError(_("Describe the observed problem before submitting a remote-support correction."))
            current = request._current_values()
            proposed = request._proposed_values()
            submitted_at = fields.Datetime.now()
            submitted_at_utc = request._event_time_utc(submitted_at)
            support_reason_sha256 = hashlib.sha256(
                str(request.support_reason or "").strip().encode("utf-8")
            ).hexdigest()
            try:
                packet = build_menu_change_candidate(
                    change_type=request.change_type,
                    group_ref=request.group_batch_id.group_ref,
                    store_ref=request.group_batch_id.store_ref,
                    requester_ref=f"odoo-user:{request.requester_user_id.id}",
                    responsible_person_ref=request.responsible_person_ref,
                    same_principal_dual_role=(
                        request.requester_user_id
                        == request.responsible_reviewer_user_id
                    ),
                    action_at_utc=submitted_at_utc,
                    support_reason_sha256=support_reason_sha256,
                    current_values=current,
                    proposed_values=proposed,
                )
            except MenuChangeGovernanceError as exc:
                raise UserError(_("Menu change candidate blocked: %s") % exc) from exc
            super(
                WuchangCafeMenuChangeRequest,
                request.with_context(wuchang_menu_request_internal_write=True),
            ).write(
                {
                    "name": f"MENU-{request.change_type.upper()}-{packet['candidate_sha256'][:12]}",
                    "state": "pending_responsible_review",
                    "responsible_reviewer_user_id": request.group_batch_id.responsible_menu_reviewer_user_id.id,
                    "responsible_person_ref": request.group_batch_id.responsible_person_ref,
                    "current_snapshot_json": json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True),
                    "proposed_values_json": json.dumps(proposed, ensure_ascii=False, indent=2, sort_keys=True),
                    "candidate_packet_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "current_snapshot_sha256": packet["D2"]["current_sha256"],
                    "candidate_sha256": packet["candidate_sha256"],
                    "submitted_at": submitted_at,
                    "submitted_location_ref": request.group_batch_id.store_ref,
                    "support_reason_sha256": support_reason_sha256,
                    "remote_support_direct_write": False,
                    "single_account_multi_role": (
                        request.requester_user_id
                        == request.responsible_reviewer_user_id
                    ),
                    "formal_pos_order": False,
                    "payment_capture": False,
                }
            )
            request._log_eventbook_event(
                action="SUBMIT_ONE_MENU_ITEM_CHANGE_CANDIDATE",
                result="pending",
                event_time=submitted_at,
                payload={"candidate_sha256": packet["candidate_sha256"]},
            )
        return True

    def _assert_responsible_reviewer(self):
        self.ensure_one()
        if not self.env.user.has_group(RESPONSIBLE_GROUP):
            raise UserError(_("The cafe menu responsible-person role is required."))
        if self.responsible_reviewer_user_id != self.env.user:
            raise UserError(_("Only the responsible person bound to this merchant group can review this change."))
        if self.group_batch_id.responsible_menu_reviewer_user_id != self.env.user:
            raise UserError(_("The merchant responsible-person binding changed; submit a new request."))

    def _apply_values(self):
        self.ensure_one()
        proposed = self._proposed_values()
        values = {}
        if "name" in proposed:
            values["name"] = proposed["name"]
        if "list_price" in proposed:
            values["list_price"] = proposed["list_price"]
        if "pos_category_ids" in proposed:
            values["pos_categ_ids"] = [(6, 0, proposed["pos_category_ids"])]
        if "option_group_id" in proposed:
            values["wuchang_option_group_id"] = proposed["option_group_id"] or False
        if "image_sha256" in proposed:
            values["image_1920"] = self.proposed_image_1920 or False
        if "active" in proposed:
            values["active"] = proposed["active"]
        if "available_in_pos" in proposed:
            values["available_in_pos"] = proposed["available_in_pos"]
        return values

    def action_responsible_approve_and_apply(self):
        for request in self:
            if request.state != "pending_responsible_review":
                raise UserError(_("Only a pending request can be applied."))
            request._assert_responsible_reviewer()
            current = request._current_values()
            try:
                current_check = build_menu_change_candidate(
                    change_type=request.change_type,
                    group_ref=request.group_batch_id.group_ref,
                    store_ref=request.group_batch_id.store_ref,
                    requester_ref=f"odoo-user:{request.requester_user_id.id}",
                    responsible_person_ref=request.responsible_person_ref,
                    same_principal_dual_role=(
                        request.requester_user_id
                        == request.responsible_reviewer_user_id
                    ),
                    action_at_utc=request._event_time_utc(request.submitted_at),
                    support_reason_sha256=request.support_reason_sha256,
                    current_values=current,
                    proposed_values=request._proposed_values(),
                )
            except MenuChangeGovernanceError as exc:
                raise UserError(_("Menu change revalidation blocked: %s") % exc) from exc
            if current_check["D2"]["current_sha256"] != request.current_snapshot_sha256:
                raise UserError(
                    _("The menu item changed after this request was submitted. No values were applied; create a fresh request.")
                )
            if current_check["candidate_sha256"] != request.candidate_sha256:
                raise UserError(
                    _("The submitted event evidence no longer matches this request. No values were applied; create a fresh request.")
                )
            if request.origin == "remote_support" and not str(
                request.responsible_review_note or ""
            ).strip():
                raise UserError(
                    _(
                        "Record the responsible-person review conclusion before applying a remote support correction."
                    )
                )

            values = request._apply_values()
            if request.change_type == "create":
                values.update(
                    {
                        "company_id": request.company_id.id,
                        "sale_ok": True,
                        "purchase_ok": False,
                        "type": "consu",
                        "available_in_pos": True,
                        "w5c_authority": "GROUP_RESPONSIBLE_PERSON_APPROVED",
                        "w5c_topology": request.group_batch_id.group_ref,
                    }
                )
                product = (
                    self.env["product.template"]
                    .sudo()
                    .with_context(wuchang_menu_internal_write=True)
                    .create(values)
                )
            else:
                product = request.product_template_id.sudo().exists()
                if not product:
                    raise UserError(_("The target menu item no longer exists."))
                product.with_context(wuchang_menu_internal_write=True).write(values)
            product._wuchang_ensure_menu_identity()
            applied = product.wuchang_menu_snapshot()
            reviewed_at = fields.Datetime.now()
            try:
                seal = build_responsible_approval_seal(
                    candidate_sha256=request.candidate_sha256,
                    responsible_person_ref=request.responsible_person_ref,
                    product_thing_code=product.w5c_code,
                    applied_values=applied,
                    same_principal_dual_role=(
                        request.requester_user_id
                        == request.responsible_reviewer_user_id
                    ),
                    review_note_sha256=hashlib.sha256(
                        str(request.responsible_review_note or "").strip().encode(
                            "utf-8"
                        )
                    ).hexdigest(),
                    actor_ref=f"odoo-user:{self.env.user.id}",
                    action_location_ref=request.submitted_location_ref,
                    reviewed_at_utc=request._event_time_utc(reviewed_at),
                )
            except MenuChangeGovernanceError as exc:
                raise UserError(_("Approval seal blocked: %s") % exc) from exc
            super(
                WuchangCafeMenuChangeRequest,
                request.with_context(wuchang_menu_request_internal_write=True),
            ).write(
                {
                    "state": "applied",
                    "applied_product_template_id": product.id,
                    "approval_seal_json": json.dumps(seal, ensure_ascii=False, indent=2, sort_keys=True),
                    "approval_sha256": seal["approval_sha256"],
                    "reviewed_by_user_id": self.env.user.id,
                    "reviewed_at": reviewed_at,
                    "applied_at": reviewed_at,
                    "remote_support_direct_write": False,
                    "single_account_multi_role": (
                        request.requester_user_id
                        == request.responsible_reviewer_user_id
                    ),
                    "formal_pos_order": False,
                    "payment_capture": False,
                }
            )
            request._log_eventbook_event(
                action="APPROVE_AND_APPLY_ONE_MENU_ITEM_CHANGE",
                result="success",
                event_time=reviewed_at,
                payload={
                    "candidate_sha256": request.candidate_sha256,
                    "approval_sha256": seal["approval_sha256"],
                    "product_thing_code": product.w5c_code,
                },
            )
        return True

    def action_responsible_reject(self):
        for request in self:
            if request.state != "pending_responsible_review":
                raise UserError(_("Only a pending request can be rejected."))
            request._assert_responsible_reviewer()
            if not str(request.responsible_review_note or "").strip():
                raise UserError(_("Enter a review reason before rejecting the request."))
            super(
                WuchangCafeMenuChangeRequest,
                request.with_context(wuchang_menu_request_internal_write=True),
            ).write(
                {
                    "state": "rejected",
                    "reviewed_by_user_id": self.env.user.id,
                    "reviewed_at": fields.Datetime.now(),
                }
            )
            request._log_eventbook_event(
                action="REJECT_ONE_MENU_ITEM_CHANGE",
                result="rejected",
                event_time=request.reviewed_at,
                payload={"candidate_sha256": request.candidate_sha256},
            )
        return True

    def action_dead_letter(self):
        if not self.env.user.has_group(GOVERNANCE_ADMIN_GROUP):
            raise UserError(_("Only a member governance admin can dead-letter audit evidence."))
        if any(request.state == "applied" for request in self):
            raise UserError(_("Applied menu-change evidence cannot be dead-lettered."))
        event_time = fields.Datetime.now()
        result = super(
            WuchangCafeMenuChangeRequest,
            self.with_context(wuchang_menu_request_internal_write=True),
        ).write({"state": "dead_letter"})
        for request in self:
            request._log_eventbook_event(
                action="DEAD_LETTER_ONE_MENU_ITEM_CHANGE",
                result="rejected",
                event_time=event_time,
                payload={"candidate_sha256": request.candidate_sha256 or None},
            )
        return result
