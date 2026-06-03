# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

# ==========================================
# 5. 系統治理與合規模組
# ==========================================
class WuchangLegalDoc(models.Model):
    _name = 'wuchang.legal.doc'
    name = fields.Char('文號')
    issuing_authority = fields.Selection([('ntp_court', '新北地院'), ('ntp_prosecutor', '地檢署')])
    digital_signature_hash = fields.Char()
    is_supreme_order = fields.Boolean(default=True)
    request_takeover = fields.Boolean()

    def _execute_takeover_protocol(self):
        _logger.warning("SYSTEM TAKEOVER INITIATED")
        # 執行接管邏輯：停機、移交權限

class WuchangAiConfig(models.Model):
    _name = 'wuchang.ai.config'
    _description = 'AI 總路由行為與價值觀配置'

    name = fields.Char(default='Global AI Configuration', required=True)
    active = fields.Boolean(default=True)
    
    # 行為模式
    behavior_mode = fields.Selection([
        ('strict', '嚴肅合規 (Strict & Compliant)'),
        ('friendly', '溫暖親切 (Friendly & Warm)'),
        ('efficient', '效率優先 (Efficiency First)')
    ], default='friendly', string='AI 回應風格')

    # 價值觀權重 (0.0 - 1.0)
    weight_public_interest = fields.Float('公益性權重', default=0.9)
    weight_efficiency = fields.Float('效率權重', default=0.5)
    weight_community_consensus = fields.Float('社區共識權重', default=0.8)
    weight_commercial_profit = fields.Float('商業利益權重', default=0.2)

    # 修改日誌
    last_modified_by = fields.Many2one('res.users', string='最後修改者')
    modification_note = fields.Text('修改理由')

    @api.constrains('weight_public_interest', 'weight_commercial_profit')
    def _check_weights(self):
        for r in self:
            if r.weight_commercial_profit > r.weight_public_interest:
                # 這是系統核心價值，不可違反
                # 但為了彈性，我們只給警告或需要最高權限覆核 (此處簡化為紀錄)
                _logger.warning(f"AI Config Warning: Commercial profit weight ({r.weight_commercial_profit}) is higher than Public Interest ({r.weight_public_interest}).")
