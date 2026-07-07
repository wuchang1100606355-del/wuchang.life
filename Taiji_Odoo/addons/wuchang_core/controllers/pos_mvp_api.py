from odoo import http
from odoo.http import request

class PosMvpApi(http.Controller):
    @http.route('/api/pos/v1/order', type='json', auth='user', methods=['POST'])
    def create_order(self, **kwargs):
        lines = kwargs.get('lines', [])
        if not lines:
            return {'status': 'HOLD', 'message': '無餐點資料'}
        
        # 預留 W7TP 8D 總場閘門驗證斷點
        # 接收後僅為候選草稿，不直接寫入真實 DB
        return {'status': 'PASS_CANDIDATE', 'message': '候選訂單已接收，等待總場實體驗證'}
