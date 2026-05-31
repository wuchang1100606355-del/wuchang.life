import os
from odoo import models, fields, api
import json

class AiGuard(models.Model):
    _inherit = 'wuchang.ai.hallucination.monitor'

    system_structure_index = fields.Text(string='System Structure Index', help='JSON map of all models and key fields.')
    last_index_time = fields.Datetime(string='Last Index Time')

    def action_build_system_index(self):
        """
        Scans system to build a Unified Cache Logic map (Body Memory).
        Includes Spatiotemporal Indexing (Space + Time).
        """
        # 1. System Structure (Schema)
        ir_models = self.env['ir.model'].search([])
        index_data = {}
        for model in ir_models:
            index_data[model.model] = {
                'name': model.name,
                'transient': model.transient,
                'modules': model.modules,
            }

        # 2. Spatiotemporal Index (Data)
        spatiotemporal_data = {}

        # 2a. Partners (Permanent Entities)
        partners_with_geo = self.env['res.partner'].search([('spatial_idx_lat', '!=', 0)])
        for p in partners_with_geo:
            key = p.spatial_ref_uuid or f'partner_{p.id}'
            spatiotemporal_data[key] = {
                'type': 'partner',
                'id': p.id,
                'name': p.name,
                'role': p.property_management_role,
                'coords': [p.spatial_idx_lat, p.spatial_idx_lng, p.spatial_idx_alt],
                'timestamp': p.create_date.isoformat() if p.create_date else None,
                'valid_period': 'permanent'
            }

        # 2b. AI Memories (Events/Logs)
        memories_with_geo = self.env['wuchang.ai.memory'].search([('spatial_idx_lat', '!=', 0)])
        for m in memories_with_geo:
            key = f'memory_{m.id}'
            spatiotemporal_data[key] = {
                'type': 'memory',
                'id': m.id,
                'name': m.name,
                'content_preview': m.content[:100] if m.content else '',
                'coords': [m.spatial_idx_lat, m.spatial_idx_lng, m.spatial_idx_alt],
                'timestamp': m.create_date.isoformat() if m.create_date else None,
                'valid_period': 'event'
            }

        # 3. Unified Cache Write
        full_index = {
            'system_structure': index_data,
            'spatiotemporal_index': spatiotemporal_data,
            'meta': {
                'generated_at': fields.Datetime.now().isoformat(),
                'version': '2.0-spatiotemporal'
            }
        }

        self.write({
            'system_structure_index': json.dumps(full_index, indent=2, ensure_ascii=False),
            'last_index_time': fields.Datetime.now()
        })
        return True
