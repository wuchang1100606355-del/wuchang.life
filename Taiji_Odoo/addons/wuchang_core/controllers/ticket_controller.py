# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class TicketController(http.Controller):
    @http.route('/wuchang/tickets', type='http', auth='public', website=True)
    def ticket_page(self, **kwargs):
        return request.render('wuchang_core.ticket_page_template', {})

    @http.route('/wuchang/tickets/list', type='json', auth='public')
    def list_tickets(self):
        # The legacy catalogue has no authoritative price/payment/issuance binding.
        # Do not offer fabricated items or infer a selling price from voucher type.
        return {
            'items': [],
            'state': 'HOLD_TICKET_SALES_NOT_BOUND',
            'purchase_enabled': False,
            'message': '票券販售尚未開放；既有會員票券權益不受影響，請洽店員。',
        }

    @http.route('/wuchang/tickets/buy', type='json', auth='user')
    def buy_ticket(self, voucher_id=None):
        # A success response requires a real authorized transaction and issue receipt.
        # The sovereign member-voucher implementation owns those effects.
        return {
            'success': False,
            'state': 'HOLD_TICKET_PURCHASE_NOT_BOUND',
            'message': '本次未扣款、未發券。票券販售尚未開放，請洽店員。',
            'payment_capture': False,
            'voucher_issued': False,
        }
