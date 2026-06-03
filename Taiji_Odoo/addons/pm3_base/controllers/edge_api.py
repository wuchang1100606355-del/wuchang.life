from odoo import http
from odoo.http import request

class PM3EdgeAPI(http.Controller):

    @http.route(
        '/pm3/tensor_ingest',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def tensor_ingest(self, **body):

        packet = request.env['pm3.packet.history'].sudo().create({
            'packet_id': body.get('packet_id'),
            'node': body.get('node'),
            'source_layer': body.get('source_layer'),
            'target_layer': body.get('target_layer'),
            'five_d_code': str(body.get('five_d_code')),
            'governance_level': body.get('governance_level', 'L1'),
            'memory_scope': body.get('memory_scope', 'ephemeral'),
            'audit_hash': body.get('audit_hash'),
            'payload_hash': body.get('payload_hash'),
        })

        return {
            'status': 'ok',
            'record_id': packet.id,
        }
