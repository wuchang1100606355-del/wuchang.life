from odoo import fields, models


class WuchangAssociationMerchantTenant(models.Model):
    _name = "wuchang.association.merchant.tenant"
    _description = "Association Merchant Tenant"
    _order = "name"

    name = fields.Char(required=True, index=True)
    merchant_code = fields.Char(index=True)
    company_id = fields.Many2one("res.company", string="Odoo Company")
    domain_name = fields.Char(string="Merchant Domain")
    contact_partner_id = fields.Many2one("res.partner", string="Merchant Contact")
    active = fields.Boolean(default=True)

    data_controller_note = fields.Text(
        string="Merchant Data Controller Note",
        help="Defines the merchant as the business-side controller of its member service data."
    )
    association_processor_note = fields.Text(
        string="Association Processor Note",
        help="Defines the association-domain role as delegated data steward / processor."
    )


class WuchangAssociationMemberConsent(models.Model):
    _name = "wuchang.association.member.consent"
    _description = "Association Member Consent Scope"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, default="Member Consent")
    merchant_id = fields.Many2one(
        "wuchang.association.merchant.tenant",
        required=True,
        index=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Member",
        required=True,
        index=True,
        ondelete="cascade",
    )

    consent_state = fields.Selection([
        ("draft", "Draft"),
        ("granted", "Granted"),
        ("revoked", "Revoked"),
        ("expired", "Expired"),
    ], default="draft", required=True, index=True)

    data_purpose = fields.Selection([
        ("member_service", "Member Service"),
        ("pos_order", "POS Order"),
        ("wifi_auth", "Wi-Fi Authorization"),
        ("invoice_service", "Invoice Service"),
        ("loyalty", "Loyalty"),
        ("ai_assistant", "AI Assistant"),
        ("security_audit", "Security Audit"),
    ], default="member_service", required=True, index=True)

    consent_scope = fields.Text(
        help="Human-readable scope of member data access and processing."
    )

    ai_read_allowed = fields.Boolean(default=True)
    ai_write_allowed = fields.Boolean(default=False)
    cross_merchant_allowed = fields.Boolean(default=False)

    valid_from = fields.Datetime()
    valid_until = fields.Datetime()
    token_ref = fields.Char(string="Metric Authority Token Reference", index=True)

    source = fields.Char(
        help="Consent source, such as LINE Login, Wi-Fi captive portal, POS terminal, or manual admin entry."
    )
    note = fields.Text()


class WuchangAssociationMemberDataRequest(models.Model):
    _name = "wuchang.association.member.data.request"
    _description = "Association Member Data Rights Request"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, default="Member Data Request")
    merchant_id = fields.Many2one("wuchang.association.merchant.tenant", required=True, index=True)
    partner_id = fields.Many2one("res.partner", string="Member", required=True, index=True)

    request_type = fields.Selection([
        ("access", "Access"),
        ("correction", "Correction"),
        ("deletion", "Deletion"),
        ("stop_processing", "Stop Processing"),
        ("export", "Export"),
    ], required=True, index=True)

    state = fields.Selection([
        ("draft", "Draft"),
        ("received", "Received"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("rejected", "Rejected"),
    ], default="draft", required=True, index=True)

    risk_level = fields.Selection([
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ], default="medium", index=True)

    request_source = fields.Char()
    description = fields.Text()
    result_note = fields.Text()
    ai_event_id = fields.Many2one("wuchang.cafe.ai.eventbook", string="Related AI Event")
