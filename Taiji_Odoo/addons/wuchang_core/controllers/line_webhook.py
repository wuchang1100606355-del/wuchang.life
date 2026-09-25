from odoo import http
from odoo.http import request

class LineWebhookApi(http.Controller):
    @http.route('/api/line/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def handle_webhook(self, **kwargs):
        # 僅作實體接收，盡速回覆 200 OK 避免 LINE 伺服器判定逾時
        # 封包本體直接視為不可信候選，交由地端 8D 閘門進行非同步解析
        return {'status': '200', 'message': 'OK'}
