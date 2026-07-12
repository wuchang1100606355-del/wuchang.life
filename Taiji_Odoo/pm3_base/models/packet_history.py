from odoo import models, fields


class PM3PacketHistory(models.Model):
    _name = "pm3.packet.history"
    _description = "PM3 Sovereign Tensor Packet History"
    _order = "timestamp desc"

    packet_id = fields.Char(required=True, index=True)
    node = fields.Char(required=True, index=True)
    source_layer = fields.Char(required=True)
    target_layer = fields.Char(required=True)
    five_d_code = fields.Char(required=True)
    governance_level = fields.Char(default="L1")
    memory_scope = fields.Char(default="ephemeral")
    audit_hash = fields.Char(required=True, index=True)
    payload_hash = fields.Char(required=True)
    timestamp = fields.Datetime(default=fields.Datetime.now, required=True)
