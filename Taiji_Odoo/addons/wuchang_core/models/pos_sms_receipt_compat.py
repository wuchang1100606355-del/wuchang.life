# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettingsWuchangPosSmsReceiptCompat(models.TransientModel):
    _inherit = "res.config.settings"

    # Non-stored compatibility field.
    # Purpose: satisfy POS settings view reference without requiring a SQL column
    # on res_config_settings.
    pos_sms_receipt_template_id = fields.Many2one(
        "mail.template",
        string="POS SMS Receipt Template",
        compute="_compute_pos_sms_receipt_template_id",
        inverse="_inverse_pos_sms_receipt_template_id",
        readonly=False,
        store=False,
    )

    def _compute_pos_sms_receipt_template_id(self):
        icp = self.env["ir.config_parameter"].sudo()
        value = icp.get_param("wuchang_core.pos_sms_receipt_template_id")
        template = False
        if value and str(value).isdigit():
            candidate = self.env["mail.template"].sudo().browse(int(value))
            if candidate.exists():
                template = candidate
        for rec in self:
            rec.pos_sms_receipt_template_id = template

    def _inverse_pos_sms_receipt_template_id(self):
        icp = self.env["ir.config_parameter"].sudo()
        for rec in self:
            icp.set_param(
                "wuchang_core.pos_sms_receipt_template_id",
                rec.pos_sms_receipt_template_id.id or 0,
            )
