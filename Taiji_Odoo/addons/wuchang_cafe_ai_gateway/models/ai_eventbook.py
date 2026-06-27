from odoo import fields, models


class WuchangCafeAiEventbook(models.Model):
    _name = "wuchang.cafe.ai.eventbook"
    _description = "WuChang Cafe AI Audit Eventbook"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, index=True)
    event_type = fields.Selection(
        [
            ("ai_read", "AI Read"),
            ("ai_action", "AI Action"),
            ("voice_order", "Voice Order"),
            ("wifi_auth", "WiFi Auth"),
            ("sunmi_event", "Sunmi Event"),
            ("clow_tool_call", "Clow Tool Call"),
            ("policy_reject", "Policy Reject"),
        ],
        required=True,
        default="ai_read",
        index=True,
    )
    source = fields.Char(index=True)
    session_ref = fields.Char(index=True)
    user_role = fields.Char(index=True)
    intent = fields.Char(index=True)
    tool_name = fields.Char(index=True)
    risk_level = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
            ("forbidden", "Forbidden"),
        ],
        default="low",
        index=True,
    )
    confirmation_required = fields.Boolean(default=False)
    confirmation_result = fields.Char()
    target_model = fields.Char(index=True)
    target_record_id = fields.Char(index=True)
    result = fields.Selection(
        [
            ("success", "Success"),
            ("rejected", "Rejected"),
            ("failed", "Failed"),
            ("pending", "Pending"),
        ],
        default="pending",
        index=True,
    )
    payload_json = fields.Text()
    note = fields.Text()
