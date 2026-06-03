# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class SisterAgentController(http.Controller):
    @http.route('/wuchang/sister/poll', type='http', auth='none', methods=['POST', 'GET'], csrf=False)
    def sister_poll(self, **post):
        # 如果是 POST 且 Content-Type 是 application/json，手動解析
        if request.httprequest.content_type == 'application/json':
            try:
                data = json.loads(request.httprequest.data)
                device_type = data.get('device_type', 'UNKNOWN')
            except:
                device_type = 'UNKNOWN'
        else:
            device_type = post.get('device_type', 'UNKNOWN')

        _logger.info("Sister Poll (HTTP) received for device: %s", device_type)
        
        # 使用 sudo() 確保在 auth='none' 下可以訪問模型
        control = request.env['wuchang.sister.control'].sudo().search([], limit=1)

        if not control:
            return json.dumps({'commands': [], 'error': 'No control record found'})

        # 更新設備在線狀態
        if device_type == 'POS':
            control.pos_status = 'online'
        elif device_type == 'CUSTOMER':
            control.customer_display_status = 'online'

        queue = json.loads(control.command_queue or '{}')

        # 獲取該設備的指令
        my_cmds = queue.pop(device_type, [])
        global_cmds = queue.pop('ALL', [])

        all_cmds = my_cmds + global_cmds
        control.command_queue = json.dumps(queue)

        result = {
            'commands': all_cmds,
            'config': {
                'pos_url': control.pos_url,
                'customer_url': control.customer_url
            }
        }
        return request.make_response(json.dumps(result), headers=[('Content-Type', 'application/json')])