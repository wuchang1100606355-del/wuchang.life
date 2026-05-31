# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json

class TicketController(http.Controller):

    @http.route('/wuchang/tickets', type='http', auth='public', website=True)
    def ticket_page(self, **kwargs):
        """Render the ticket purchase page."""
        return request.render('wuchang_core.ticket_page_template', {})

    @http.route('/wuchang/tickets/list', type='json', auth='public')
    def list_tickets(self):
        """Return list of available vouchers."""
        vouchers = request.env['wuchang.voucher.product'].sudo().search([('stock_qty', '>', 0)])
        result = []
        for v in vouchers:
            result.append({
                'id': v.id,
                'name': v.name,
                'type': v.voucher_type,
                'price': 100 if v.voucher_type == 'discount_70' else 50, # Dummy pricing logic for now
                'merchant': v.merchant_id.name,
                'stock': v.stock_qty,
            })
        
        # If no vouchers exist, return some dummy data for demo purposes
        if not result:
            result = [
                {'id': 1, 'name': '通用餐飲折價券 $100', 'type': 'discount_70', 'price': 100, 'merchant': '五常社區', 'stock': 99},
                {'id': 2, 'name': '仁義店飲品兌換券', 'type': 'free', 'price': 50, 'merchant': '仁義店', 'stock': 50},
                {'id': 3, 'name': '公益外送抵用券', 'type': 'discount_60', 'price': 30, 'merchant': '五常外送', 'stock': 200},
            ]
            
        return {'items': result}

    @http.route('/wuchang/tickets/buy', type='json', auth='user')
    def buy_ticket(self, voucher_id):
        """Handle ticket purchase with happiness coins."""
        user = request.env.user
        partner = user.partner_id
        
        # Simplified logic: 
        # 1. Check balance (dummy check for now)
        # 2. Deduct coins
        # 3. Create user voucher record
        
        # For now, we just simulate success
        return {
            'success': True,
            'message': '購券成功！您已獲得一張新的票券。',
            'new_balance': partner.wish_credit_balance  # Assuming this field exists or similar
        }
