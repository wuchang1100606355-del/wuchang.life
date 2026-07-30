# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


def _landing_enabled(surface):
    try:
        return request.env["wuchang.community.feature.gate"].is_landing_enabled(
            surface
        )
    except KeyError:
        return False


class WuchangOrderSite(http.Controller):

    @http.route('/order', type='http', auth='public', website=True)
    def order_page(self, **kw):
        ordering_enabled = request.env['ir.config_parameter'].sudo().get_param('wuchang.ordering_enabled', 'True')
        announcement = request.env['ir.config_parameter'].sudo().get_param('wuchang.announcement', '')
        allow_delivery = request.env['ir.config_parameter'].sudo().get_param('wuchang.allow_delivery', 'True')
        min_amount = request.env['ir.config_parameter'].sudo().get_param('wuchang.min_amount', '0')
        return request.render('wuchang_core.order_website_page', {
            'ordering_enabled': (
                ordering_enabled == 'True' and _landing_enabled("pos_order")
            ),
            'announcement': announcement,
            'allow_delivery': allow_delivery == 'True',
            'min_amount': float(min_amount or 0),
        })

    @http.route('/api/order/create', type='json', auth='public')
    def create_order(self, **payload):
        if not _landing_enabled("pos_order"):
            return {
                "ok": False,
                "state": "HOLD_LANDING_CONTROL_DISABLED",
                "feature_key": "landing.pos_order",
            }
        try:
            data = payload or {}
            items = data.get('items', [])
            total = float(data.get('total', 0))
            customer = data.get('customer_name')
            phone = data.get('phone')
            sale_mode = data.get('sale_mode') or 'takeout'
            table_no = data.get('table_no') or ''
            address = data.get('address') or ''
            schedule_time = data.get('schedule_time') or ''
            note = data.get('note') or ''
            delivery_platform = data.get('delivery_platform') or ''
            nonprofit_program = data.get('nonprofit_program') or ''
            delivery_fee = data.get('delivery_fee') or 0
            tip_amount = data.get('tip_amount') or 0
            lat = data.get('location_lat')
            lng = data.get('location_lng')
            try:
                lat = float(lat) if lat is not None else None
            except Exception:
                lat = None
            try:
                lng = float(lng) if lng is not None else None
            except Exception:
                lng = None
            order = request.env['wuchang.order'].sudo().create({
                'customer_name': customer,
                'phone': phone,
                'sale_mode': sale_mode,
                'table_no': table_no if sale_mode == 'dine_in' else False,
                'delivery_address': address if sale_mode in ['delivery_commercial', 'delivery_nonprofit'] else False,
                'delivery_time': schedule_time if sale_mode in ['delivery_commercial', 'delivery_nonprofit'] else False,
                'delivery_note': note if sale_mode in ['delivery_commercial', 'delivery_nonprofit'] else False,
                'delivery_platform': delivery_platform if sale_mode == 'delivery_commercial' else False,
                'nonprofit_program': nonprofit_program if sale_mode == 'delivery_nonprofit' else False,
                'delivery_fee': float(delivery_fee or 0) if sale_mode in ['delivery_commercial', 'delivery_nonprofit'] else 0,
                'tip_amount': float(tip_amount or 0),
                'location_lat': lat if sale_mode in ['delivery_commercial', 'delivery_nonprofit'] else False,
                'location_lng': lng if sale_mode in ['delivery_commercial', 'delivery_nonprofit'] else False,
                'total_amount': total,
                'items_json': json.dumps(items, ensure_ascii=False),
            })
            return {'ok': True, 'order_ref': order.name}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    @http.route('/payment/mock_callback', type='http', auth='public')
    def payment_mock(self, **kw):
        return http.Response(
            'BLOCK_DEMO_PAYMENT_CALLBACK_NOT_PRODUCT_AUTHORITY',
            status=410,
        )

    @http.route('/api/public_benefit/summary', type='json', auth='user')
    def public_benefit_summary(self, days=30):
        try:
            days = int(days or 30)
        except Exception:
            days = 30
        Order = request.env['wuchang.order'].sudo()
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(days=days)
        nonprofit = Order.search([('sale_mode', '=', 'delivery_nonprofit'), ('create_date', '>=', since.strftime('%Y-%m-%d %H:%M:%S'))])
        takeout = Order.search([('sale_mode', '=', 'takeout'), ('create_date', '>=', since.strftime('%Y-%m-%d %H:%M:%S'))])
        dinein = Order.search([('sale_mode', '=', 'dine_in'), ('create_date', '>=', since.strftime('%Y-%m-%d %H:%M:%S'))])
        def agg(recs):
            total = 0.0
            fee = 0.0
            tip = 0.0
            programs = set()
            for r in recs:
                try:
                    total += float(r.total_amount or 0)
                except Exception:
                    pass
                try:
                    fee += float(r.delivery_fee or 0)
                except Exception:
                    pass
                try:
                    tip += float(r.tip_amount or 0)
                except Exception:
                    pass
                p = getattr(r, 'nonprofit_program', '') or ''
                if p:
                    programs.add(p)
            return {'count': len(recs), 'total_amount': total, 'delivery_fee': fee, 'tip_amount': tip, 'programs': sorted(list(programs))}
        return {
            'ok': True,
            'window_days': days,
            'nonprofit': agg(nonprofit),
            'takeout': agg(takeout),
            'dine_in': agg(dinein),
        }

    @http.route('/wuchang/employee/order', type='http', auth='user', website=True)
    def employee_order_page(self, **kw):
        return request.render('wuchang_core.employee_order_page', {
            'store_name': '重新店',
        })

    @http.route('/wuchang/device/customer_display', type='http', auth='public', website=True)
    def customer_display_page(self, **kw):
        return request.render('wuchang_core.customer_display_page', {
            'store_name': '重新店',
            'order_url': '/order',
        })

