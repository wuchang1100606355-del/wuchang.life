# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import time
import re
import sys
import json
import logging
import urllib.parse
import urllib.request
import io
import zipfile
import hashlib
import hmac
try:
    import sass as _sass
    _sass_available = True
except Exception:
    _sass_available = False
_rate = {}


class WuchangHomepage(http.Controller):
    def _cipher_ok(self):
        p = request.env['ir.config_parameter'].sudo()
        on = (p.get_param('supreme.cipher.enabled')
              or 'false').lower() in ('1', 'true', 'yes')
        if not on:
            return True
        sec = p.get_param('supreme.cipher.secret') or ''
        if not sec:
            return False
        try:
            ts = int(request.httprequest.headers.get('X-Supreme-Ts') or '0')
            now = int(time.time())
            if abs(now - ts) > 60:
                return False
            raw = request.httprequest.get_data() or b''
            path = request.httprequest.path or ''
            msg = (str(ts) + '|' + path + '|' +
                   hashlib.sha256(raw).hexdigest()).encode('utf-8')
            mac = hmac.new(sec.encode('utf-8'), msg,
                           hashlib.sha256).hexdigest()
            sig = request.httprequest.headers.get('X-Supreme-Cipher') or ''
            return hmac.compare_digest(mac, sig)
        except Exception:
            return False

    def _canonical_host(self):
        try:
            return (request.env['ir.config_parameter'].sudo().get_param('website.canonical_host') or '').strip()
        except Exception:
            return ''

    def _canonical_redirect(self):
        try:
            req = request.httprequest
            host = (req.host or '').strip()
            canon = self._canonical_host()
            if canon and host and host.lower() != canon.lower():
                try:
                    scheme = getattr(req, 'scheme', None) or 'http'
                except Exception:
                    scheme = 'http'
                url = scheme + '://' + canon + (req.full_path or '/')
                return request.redirect(url, code=301)
        except Exception:
            return None
        return None

    def _simple_website_page(self, title, body_html):
        head = '<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><link rel="stylesheet" href="/web/assets/website/css/website.css"/>'
        wrapper = '<html><head><title>%s</title>%s</head><body><div class="container my-5">%s</div></body></html>'
        return wrapper % (title, head, body_html)

    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        r = self._canonical_redirect()
        if r:
            return r
        return request.redirect('/web')

    @http.route('/wuchang', type='http', auth="public", website=True)
    def site_home(self, **kw):
        r = self._canonical_redirect()
        if r:
            return r
        user = request.env.user
        is_manager = user.has_group('base.group_system') or user.has_group(
            'base.group_erp_manager')
        is_committee = is_manager
        is_resident = not is_manager
        is_volunteer = False
        values = {
            'user': user,
            'is_manager': is_manager,
            'is_committee': is_committee,
            'is_resident': is_resident,
            'is_volunteer': is_volunteer,
        }
        try:
            return request.render('wuchang_core.homepage_website', values)
        except Exception:
            try:
                return request.render('wuchang_life.life_page', values)
            except Exception:
                html = self._simple_website_page(
                    'Wuchang',
                    '<h1 class="display-6 mb-3">Wuchang</h1><p class="lead">Welcome.</p><p><a class="btn btn-dark" href="/web">Go to Backend</a></p>',
                )
                return http.Response(html, status=200)

    @http.route('/community', type='http', auth="public")
    def community(self, **kw):
        r = self._canonical_redirect()
        if r:
            return r
        try:
            user = request.env.user
            is_manager = user.has_group('base.group_system') or user.has_group(
                'base.group_erp_manager')
            is_committee = is_manager
            is_resident = not is_manager
            is_volunteer = False
            values = {
                'user': user,
                'is_manager': is_manager,
                'is_committee': is_committee,
                'is_resident': is_resident,
                'is_volunteer': is_volunteer,
            }
            try:
                View = request.env['ir.ui.view'].sudo()
                has_layout = bool(View.search(
                    [('key', '=', 'website.layout')], limit=1))
            except Exception:
                has_layout = False
            if has_layout:
                try:
                    return request.render('wuchang_core.homepage_template', values)
                except Exception:
                    try:
                        return request.render('wuchang_life.life_page', values)
                    except Exception:
                        pass
            html = self._simple_website_page(
                'Wuchang',
                '<h1 class="display-6 mb-3">Wuchang</h1><p class="lead">Welcome.</p><p><a class="btn btn-primary me-2" href="/ambassador">Ambassador</a><a class="btn btn-outline-dark" href="/web">Backend</a></p>',
            )
            return http.Response(html, status=200)
        except Exception:
            html = self._simple_website_page(
                'Wuchang',
                '<h1 class="display-6 mb-3">Wuchang</h1><p class="lead">Welcome.</p><p><a class="btn btn-primary me-2" href="/ambassador">Ambassador</a><a class="btn btn-outline-dark" href="/web">Backend</a></p>',
            )
            return http.Response(html, status=200)

    @http.route('/community/fund', type='http', auth='public', website=True)
    def community_fund_bulletin(self, **kw):
        r = self._canonical_redirect()
        if r:
            return r
        Finance = request.env['community.fund.account'].sudo()
        Log = request.env['transparency.log'].sudo()
        funds = Finance.search([])
        total_twd = sum([float(x.balance_twd or 0.0) for x in funds])
        total_whc = sum([float(x.balance_whc or 0.0) for x in funds])
        total_merchant_donation = sum([float(x.merchant_donation_total or 0.0) for x in funds])
        total_consumer_donation = sum([float(x.consumer_donation_total or 0.0) for x in funds])
        total_merchant_custody = sum([float(x.merchant_custody_total or 0.0) for x in funds])
        total_deferred_whc = sum([float(x.deferred_whc_quota or 0.0) for x in funds])
        total_deferred_voucher = sum([float(x.deferred_voucher_quota or 0.0) for x in funds])
        logs = Log.search([], limit=20, order='timestamp desc')
        values = {
            'funds': funds,
            'total_twd': total_twd,
            'total_whc': total_whc,
            'total_merchant_donation': total_merchant_donation,
            'total_consumer_donation': total_consumer_donation,
            'total_merchant_custody': total_merchant_custody,
            'total_deferred_whc': total_deferred_whc,
            'total_deferred_voucher': total_deferred_voucher,
            'logs': logs,
        }
        return request.render('wuchang_core.fund_bulletin_page', values)

    @http.route('/api/ticket/pay_with_whc', type='json', auth='user')
    def api_ticket_pay_with_whc(self, **payload):
        consumer_id = int((payload or {}).get('consumer_id') or 0)
        merchant_id = int((payload or {}).get('merchant_id') or 0)
        whc_amount = float((payload or {}).get('whc_amount') or 0.0)
        desc = (payload or {}).get('description') or ''
        Partner = request.env['res.partner'].sudo()
        consumer = Partner.browse(consumer_id) if consumer_id else request.env.user.partner_id
        merchant = Partner.browse(merchant_id) if merchant_id else request.env.company.partner_id
        Fund = request.env['community.fund.account'].sudo()
        fund = Fund.search([('account_type', '=', 'general')], limit=1)
        if not fund:
            return {'ok': False, 'error': 'fund_not_found'}
        try:
            fund.spend_whc_for_ticket(consumer, merchant, whc_amount, whc_amount, desc)
        except Exception as e:
            return {'ok': False, 'error': 'ticket_payment_failed', 'detail': str(e)}
        return {'ok': True}

    @http.route('/portal/pos', type='http', auth='user', website=True)
    def portal_pos(self, **kw):
        store = kw.get('store') or ''
        url = '/pos_simulator' + (('?store=' + store) if store else '')
        return request.redirect(url)

    @http.route('/portal/volunteer', type='http', auth='user', website=True)
    def portal_volunteer(self, **kw):
        return request.redirect('/line/connect?role=volunteer')

    @http.route('/portal/hoa', type='http', auth='user', website=True)
    def portal_hoa(self, **kw):
        return request.redirect('/line/connect?role=hoa')

    @http.route('/portal/family', type='http', auth='user', website=True)
    def portal_family(self, **kw):
        body = '<h1 class="display-6 mb-3">家庭入口</h1><p class="lead mb-3">此頁面預留給家庭／家屬專用的入口。</p><p class="text-muted">目前尚未啟用完整功能，如需協助請聯絡管理者。</p>'
        html = self._simple_website_page('家庭入口', body)
        return http.Response(html, status=200)

    @http.route('/community/register', type='http', auth='public', website=True)
    def community_register(self, **kw):
        return request.redirect('/web/signup?redirect=/community')

    @http.route('/badges/config', type='json', auth='none')
    def badges_config(self):
        p = request.env['ir.config_parameter'].sudo()
        raw = p.get_param('branding.badges') or '[]'
        try:
            cfg = json.loads(raw)
        except Exception:
            cfg = []
        return {'items': cfg}

    @http.route('/badges/download', type='json', auth='none')
    def badges_download(self):
        p = request.env['ir.config_parameter'].sudo()
        raw = p.get_param('branding.badges') or '[]'
        try:
            items = json.loads(raw)
        except Exception:
            items = []
        base = os.path.join(os.getcwd(), 'memory_store/badges')
        try:
            import os
            os.makedirs(base, exist_ok=True)
        except Exception:
            pass
        downloaded = []
        for it in items:
            slug = (it.get('slug') or '').strip()
            url = (it.get('image_url') or '').strip()
            if not slug or not url:
                continue
            try:
                req = urllib.request.Request(
                    url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = resp.read()
                    ct = resp.headers.get('Content-Type', '').lower()
                ext = '.png'
                if 'image/jpeg' in ct:
                    ext = '.jpg'
                elif 'image/webp' in ct:
                    ext = '.webp'
                fp = base + '/' + slug + ext
                with open(fp, 'wb') as f:
                    f.write(data)
                downloaded.append({'slug': slug, 'path': fp})
            except Exception:
                pass
        return {'downloaded': downloaded}

    @http.route('/badges/image', type='http', auth='none')
    def badges_image(self, slug=None, **kw):
        import os
        base = os.path.join(os.getcwd(), 'memory_store/badges')
        if not slug:
            return http.Response(status=404)
        for ext in ('.png', '.jpg', '.jpeg', '.webp'):
            fp = base + '/' + slug + ext
            if os.path.isfile(fp):
                mt = 'image/png' if ext == '.png' else (
                    'image/webp' if ext == '.webp' else 'image/jpeg')
                with open(fp, 'rb') as f:
                    return http.Response(f.read(), headers=[('Content-Type', mt)])
        return http.Response(status=404)

    @http.route('/external/google/nonprofits', type='http', auth='public')
    def ext_google_nonprofits(self, **kw):
        return request.redirect('https://www.google.com/nonprofits/', code=302)

    @http.route('/external/google/startups', type='http', auth='public')
    def ext_google_startups(self, **kw):
        return request.redirect('https://startup.google.com/', code=302)

    @http.route('/external/sinyi/community', type='http', auth='public')
    def ext_sinyi_community(self, **kw):
        return request.redirect('https://www.taiwan4718.tw/', code=302)

    @http.route('/chat/<string:scope>', type='http', auth='user', website=True)
    def chat_scope(self, scope, **kw):
        title = '聊天室'
        if scope in ('hoa', 'volunteer', 'family', 'business', 'services'):
            title = scope + '_chat'
        body = '<h1 class="display-6 mb-3">%s</h1><p class="lead mb-3">此頁預留為專用聊天室。目前建議先使用 LINE 官方帳號或 LIFF 建置聊天室功能。</p><a class="btn btn-dark" href="/line/connect">前往 LINE 連接</a>' % title
        html = self._simple_website_page(title, body)
        return http.Response(html)

    @http.route('/pos_simulator', type='http', auth='public')
    def pos_simulator(self, **kw):
        api_key = request.env['ir.config_parameter'].sudo(
        ).get_param('wuchang.gemini_api_key', '')
        llm_base_url = request.env['ir.config_parameter'].sudo(
        ).get_param('wuchang.llm_base_url', '')
        menu_json = request.env['ir.config_parameter'].sudo(
        ).get_param('wuchang.pos.menu_json', '[]')
        default_store = request.env['ir.config_parameter'].sudo(
        ).get_param('wuchang.store.default', '')
        store = kw.get('store') or default_store or ''

        if store:
            key = store.strip()
            m = {
                '重新店': 'chong_sin',
                '聊國咖啡重新總店': 'chong_sin',
                'CHONG-SIN': 'chong_sin',
                'chong-sin': 'chong_sin',
                'chong_sin': 'chong_sin',
                '聊國咖啡仁義分店': 'zheng_sheng',
            }
            slug = m.get(key) or re.sub(
                r"[^a-z0-9]+", "_", key.lower()).strip('_')
            user = request.env.user
            if hasattr(user, '_is_public') and user._is_public():
                return request.redirect('/web/login?redirect=' + request.httprequest.full_path)
            if slug and not user.has_group('wuchang_core.group_wuchang_store_' + slug):
                return http.Response('本店頁面僅限群組成員存取', status=403)

        return request.render('wuchang_core.pos_simulator_page', {
            'api_key': api_key,
            'llm_base_url': llm_base_url,
            'menu_json': menu_json,
            'store_name': store,
        })

    @http.route('/wuchang/store/join', type='json', auth='user')
    def store_join(self, store=None):
        key = (store or '').strip()
        m = {
            '重新店': 'chong_sin',
            '聊國咖啡重新總店': 'chong_sin',
            'CHONG-SIN': 'chong_sin',
            'chong-sin': 'chong_sin',
            'chong_sin': 'chong_sin',
            '聊國咖啡仁義分店': 'zheng_sheng',
        }
        slug = m.get(key) or (
            re.sub(r"[^a-z0-9]+", "_", key.lower()).strip('_') if key else '')
        if not slug:
            return {'ok': False, 'error': 'missing_store'}
        grp = request.env.ref(
            'wuchang_core.group_wuchang_store_' + slug, raise_if_not_found=False)
        if not grp:
            return {'ok': False, 'error': 'group_not_found', 'slug': slug}
        user = request.env.user
        try:
            user.sudo().write({'groups_id': [(4, grp.id)]})
            return {'ok': True, 'joined_group': grp.id, 'slug': slug}
        except Exception as e:
            return {'ok': False, 'error': 'write_failed', 'detail': str(e)}

    @http.route('/store/join', type='http', auth='user', website=True)
    def store_join_http(self, **kw):
        user = request.env.user
        if hasattr(user, '_is_public') and user._is_public():
            return request.redirect('/web/login?redirect=' + request.httprequest.full_path)
        res = self.store_join(store=kw.get('store'))
        if res.get('ok'):
            msg = '已加入門店群組：' + (res.get('slug') or '')
            body = '<h1 class="display-6 mb-3">加入成功</h1><p class="lead mb-3">' + \
                msg + '</p><p><a class="btn btn-primary" href="/pos_simulator?store=' + \
                (kw.get('store') or '') + '">進入 POS</a></p>'
            html = self._simple_website_page('加入門店群組', body)
            return http.Response(html)
        else:
            msg = '加入失敗：' + (res.get('error') or '')
            body = '<h1 class="display-6 mb-3">加入失敗</h1><p class="text-danger">' + \
                msg + '</p>'
            html = self._simple_website_page('加入門店群組', body)
            return http.Response(html, status=400)

    @http.route('/pos/open', type='http', auth='user', website=True)
    def pos_open(self, store=None):
        user = request.env.user
        if hasattr(user, '_is_public') and user._is_public():
            return request.redirect('/web/login?redirect=' + request.httprequest.full_path)
        key = (store or '').strip()
        m = {
            '重新店': 'wuchang_core.pos_config_re_main',
            '聊國咖啡重新總店': 'wuchang_core.pos_config_re_main',
            'CHONG-SIN': 'wuchang_core.pos_config_re_main',
            'chong-sin': 'wuchang_core.pos_config_re_main',
            'chong_sin': 'wuchang_core.pos_config_re_main',
            '仁義店': 'wuchang_core.pos_config_renyi',
            '聊國咖啡仁義分店': 'wuchang_core.pos_config_renyi',
            'REN-YI': 'wuchang_core.pos_config_renyi',
        }
        xmlid = m.get(key) or 'wuchang_core.pos_config_re_main'
        cfg = request.env.ref(xmlid, raise_if_not_found=False)
        if not cfg:
            return http.Response('未找到 POS 設定', status=404)
        return request.redirect('/pos/web?config_id=%s' % cfg.id)

    @http.route('/wuchang/store/default', type='http', auth='user', website=True)
    def set_default_store(self, store=None):
        user = request.env.user
        if hasattr(user, '_is_public') and user._is_public():
            return request.redirect('/web/login?redirect=' + request.httprequest.full_path)
        val = (store or '').strip()
        request.env['ir.config_parameter'].sudo().set_param(
            'wuchang.store.default', val)
        return http.Response('default_store_set:' + val, status=200)

    @http.route('/archives', type='http', auth='public', website=True)
    def kb_archives(self, **kw):
        return request.render('wuchang_core.kb_page', {})

    @http.route('/login/webauthn', type='http', auth='public', website=True)
    def login_webauthn(self, **kw):
        return request.render('wuchang_core.webauthn_login_page', {})

    @http.route(['/wuchang/health'], type='json', auth="public")
    def health(self):
        return {
            'python_version': sys.version,
            'libsass_available': _sass_available,
            'db': request.db,
            'uid': request.uid,
        }

    @http.route('/wuchang/agent/status', type='json', auth='public')
    def agent_status(self, **kw):
        p = request.env['ir.config_parameter'].sudo()
        enabled = (p.get_param('wuchang.agent.enabled')
                   or '').lower() in ('1', 'true', 'yes')
        name = p.get_param('wuchang.agent.name') or '小j'
        email = p.get_param('wuchang.agent.email') or (
            p.get_param('web.company_email') or 'admin@wuchang.life')
        return {'enabled': enabled, 'name': name, 'email': email}

    @http.route('/wuchang/agent/assign', type='http', auth='user', methods=['POST'], csrf=False)
    def agent_assign(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        name = (payload or {}).get('name') or '小j'
        email = (payload or {}).get('email') or ''
        p = request.env['ir.config_parameter'].sudo()
        if not email:
            email = p.get_param('web.company_email') or 'admin@wuchang.life'
        try:
            p.set_param('wuchang.agent.enabled', 'True')
            p.set_param('wuchang.agent.name', name)
            p.set_param('wuchang.agent.email', email)
            Partner = request.env['res.partner'].sudo()
            qp = Partner.search([('email', '=', email)], limit=1)
            if qp:
                qp.write({'name': name})
            else:
                Partner.create({'name': name, 'email': email})
            return http.Response(json.dumps({'ok': True, 'name': name, 'email': email}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/agent/email_test', type='http', auth='user')
    def agent_email_test(self, **kw):
        p = request.env['ir.config_parameter'].sudo()
        email = p.get_param('wuchang.agent.email') or (
            p.get_param('web.company_email') or 'admin@wuchang.life')
        name = p.get_param('wuchang.agent.name') or '小j'
        Mail = request.env['mail.mail'].sudo()
        rec = Mail.create({'subject': '代理人就位', 'body_html': '<div>代理人：' +
                          name + '（' + email + '）已就位。</div>', 'email_to': email})
        sent = False
        try:
            rec.send()
            sent = True
        except Exception:
            sent = False
        return http.Response('ok:' + ('sent' if sent else 'queued'), status=200)

    @http.route('/wuchang/agent/assign/ui', type='http', auth='user', website=True)
    def agent_assign_ui(self, **kw):
        p = request.env['ir.config_parameter'].sudo()
        name = p.get_param('wuchang.agent.name') or '小j'
        email = p.get_param('wuchang.agent.email') or (
            p.get_param('web.company_email') or 'admin@wuchang.life')
        html = '<html><head><meta charset="utf-8"/><title>代理人指派</title><meta name="viewport" content="width=device-width, initial-scale=1"/><style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans,Arial}.container{max-width:960px;margin:0 auto;padding:16px}.btn{display:inline-block;padding:8px 12px;border:1px solid #bbb;border-radius:6px;background:#fff}.btn-primary{background:#0d6efd;color:#fff;border-color:#0d6efd}</style></head><body><div class="container"><h1 class="display-6">代理人指派</h1><form method="post" action="/wuchang/agent/assign"><div class="mb-3"><label>代理人名稱</label><input name="name" class="form-control" value="' + \
            name + '"/></div><div class="mb-3"><label>代理人信箱</label><input name="email" class="form-control" value="' + email + \
            '"/></div><button class="btn btn-primary" type="submit">指派</button></form><div style="margin-top:12px"><a class="btn" href="/wuchang/agent/authorization/preview">改用授權登記頁</a></div></div></body></html>'
        return http.Response(html, status=200)

    @http.route('/api/persona/get', type='json', auth='public')
    def persona_get(self):
        p = request.env['ir.config_parameter'].sudo()

        def g(k, d=''):
            return p.get_param(k) or d
        return {
            'ok': True,
            'hoa': g('persona.hoa.name', '設計總幹事助理小J'),
            'volunteer': g('persona.volunteer.name', '志工督導助理小J'),
            'fish_assoc': g('persona.fish_assoc.name', '副總幹事小J'),
            'pos_clerk': g('persona.pos_clerk.name', '店員小J'),
        }

    @http.route('/api/persona/set', type='json', auth='user')
    def persona_set(self, **payload):
        p = request.env['ir.config_parameter'].sudo()

        def s(k, v):
            if v is not None:
                p.set_param(k, str(v))
        s('persona.hoa.name', (payload or {}).get('hoa'))
        s('persona.volunteer.name', (payload or {}).get('volunteer'))
        s('persona.fish_assoc.name', (payload or {}).get('fish_assoc'))
        s('persona.pos_clerk.name', (payload or {}).get('pos_clerk'))
        return {'ok': True}

    @http.route('/wuchang/review/anon', type='http', auth='user', website=True)
    def review_anon_ui(self, **kw):
        Agent = request.env['wuchang.ai.agent'].sudo()
        agents = Agent.search([], limit=20)
        items = []
        for a in agents:
            items.append({'id': a.id, 'name': a.name,
                         'role': a.role_type or ''})
        tpl = '''<html><head><meta charset="utf-8"/><title>匿名傳閱</title><meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans,Arial;background:#f7f7f8;color:#111}
.container{max-width:900px;margin:0 auto;padding:16px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;box-shadow:0 6px 20px rgba(0,0,0,0.06);padding:16px;margin-top:12px}
.row{display:flex;gap:12px;flex-wrap:wrap}
.col{flex:1 1 300px}
.btn{display:inline-block;padding:8px 14px;border-radius:10px;border:1px solid #0d3331;color:#0d3331;background:#e8dbc3}
.btn-primary{background:#0d3331;color:#fff;border-color:#0d3331}
.input,textarea,select{width:100%;padding:10px;border:1px solid #d1d5db;border-radius:10px}
.muted{color:#6b7280;font-size:13px}
</style></head><body>
<div class="container">
  <h2>匿名傳閱與意見加註</h2>
  <div class="muted">不記名、僅留內容與服務職務標籤。</div>
  <div class="card">
    <form id="f">
      <label>主題</label>
      <input class="input" name="topic" placeholder="例如：首頁英雄區與CTA設計"/>
      <div class="row" style="margin-top:10px">
        <div class="col">
          <label>服務職務（可選）</label>
          <select class="input" name="persona">
            <option value="">不指定</option>
            __AGENTS__
          </select>
        </div>
      </div>
      <label style="margin-top:10px">意見內容</label>
      <textarea class="input" name="comment" rows="6" placeholder="請給出具體建議、風格方向、風險提醒或文案優化點"></textarea>
      <div style="margin-top:12px">
        <button class="btn btn-primary" type="submit">送出匿名意見</button>
      </div>
    </form>
    <div id="msg" class="muted" style="margin-top:8px"></div>
  </div>
</div>
<script>
 (function(){
   var selHtml = '';
   var arr = __DATA__;
   for(var i=0;i<arr.length;i++){
     var t = arr[i];
     var lab = t.name + (t.role?('（'+t.role+'）'):'');
     selHtml += '<option value="'+(t.name)+'">'+lab+'</option>';
   }
   document.body.innerHTML = document.body.innerHTML.replace('__AGENTS__', selHtml);
   document.body.innerHTML = document.body.innerHTML.replace('__DATA__', '[]');
   var f = document.getElementById('f');
   var msg = document.getElementById('msg');
   function setMsg(s){ if(msg){ msg.textContent = s; } }
   if(f){
     f.addEventListener('submit', function(ev){
       ev.preventDefault();
       var fd = new FormData(f);
       var payload = { topic: fd.get('topic')||'', persona: fd.get('persona')||'', comment: fd.get('comment')||'' };
       fetch('/wuchang/review/anon_submit', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) })
         .then(function(r){ return r.json(); })
         .then(function(d){ setMsg(d.ok ? '已匿名送出，感謝參與！' : ('送出失敗：'+(d.error||''))); f.reset(); })
         .catch(function(){ setMsg('送出失敗，請稍後再試'); });
     });
   }
 })();
</script>
</body></html>'''
        try:
            data_json = json.dumps(items)
        except Exception:
            data_json = '[]'
        html = tpl.replace('__DATA__', data_json)
        return http.Response(html, status=200)

    @http.route('/wuchang/review/anon_submit', type='http', auth='user', methods=['POST'], csrf=False)
    def review_anon_submit(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        topic = (payload or {}).get('topic') or ''
        persona = (payload or {}).get('persona') or ''
        comment = (payload or {}).get('comment') or ''
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        if not comment.strip():
            return http.Response(json.dumps({'ok': False, 'error': 'empty_comment'}), status=400, headers={'Content-Type': 'application/json'})
        base = os.path.join(os.getcwd(), 'anonymous_reviews')
        try:
            day = time.strftime('%Y%m%d')
            os.makedirs(base, exist_ok=True)
            path = os.path.join(base, day + '.jsonl')
            rid = __import__('hashlib').sha256(
                (ts + '\n' + comment).encode('utf-8')).hexdigest()[:12]
            rec = {'id': rid, 'ts': ts, 'topic': topic,
                   'persona': persona, 'comment': comment}
            with open(path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            try:
                csv = os.path.join('/opt/wuchang', 'logs/work_log.csv')
                os.makedirs(os.path.dirname(csv), exist_ok=True)
                with open(csv, 'a', encoding='utf-8') as lf:
                    lf.write('{0},{1},{2},{3},{4},{5}\n'.format(time.strftime(
                        '%Y-%m-%d'), time.strftime('%H:%M:%S'), 'xiao-j', 'anonymous_review_submit', 'OK', 'id=' + rid))
            except Exception:
                pass
            return http.Response(json.dumps({'ok': True, 'id': rid}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/agent/authorize', type='http', auth='user', methods=['POST'], csrf=False)
    def agent_authorize(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        from_email = (payload or {}).get('from_email') or ''
        agent_name = (payload or {}).get('agent_name') or '小j'
        agent_email = (payload or {}).get('agent_email') or ''
        scope = (payload or {}).get('scope') or 'google_all'
        if not agent_email:
            p = request.env['ir.config_parameter'].sudo()
            agent_email = p.get_param('wuchang.agent.email') or (
                p.get_param('web.company_email') or 'admin@wuchang.life')
        try:
            import os
            import json
            import datetime
            base = os.path.join(os.getcwd(), 'memory_store/authorizations')
            day = datetime.datetime.utcnow().strftime('%Y%m%d')
            path = os.path.join(base, day)
            os.makedirs(path, exist_ok=True)
            doc = {
                'ts': int(time.time()),
                'from_email': from_email or 'admin@wuchang.life',
                'agent_name': agent_name,
                'agent_email': agent_email,
                'scope': scope,
                'issuer_uid': request.uid,
                'db': request.db,
            }
            fname = 'agent_authorization_' + \
                datetime.datetime.utcnow().strftime('%H%M%S') + '.json'
            with open(os.path.join(path, fname), 'w', encoding='utf-8') as f:
                f.write(json.dumps(doc, ensure_ascii=False, indent=2))
            p = request.env['ir.config_parameter'].sudo()
            p.set_param('wuchang.agent.enabled', 'True')
            p.set_param('wuchang.agent.name', agent_name)
            p.set_param('wuchang.agent.email', agent_email)
            return http.Response(json.dumps({'ok': True, 'file': fname, 'scope': scope}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:200]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/agent/authorization/preview', type='http', auth='user', website=True)
    def agent_authorization_preview(self, **kw):
        p = request.env['ir.config_parameter'].sudo()
        name = p.get_param('wuchang.agent.name') or '小j'
        email = p.get_param('wuchang.agent.email') or (
            p.get_param('web.company_email') or 'admin@wuchang.life')
        html = '<html><head><meta charset="utf-8"/><title>代理人授權預覽</title><meta name="viewport" content="width=device-width, initial-scale=1"/><style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans,Arial}.container{max-width:960px;margin:0 auto;padding:16px}.btn{display:inline-block;padding:8px 12px;border:1px solid #bbb;border-radius:6px;background:#fff}.btn-primary{background:#0d6efd;color:#fff;border-color:#0d6efd}</style></head><body><div class="container"><h1 class="display-6">代理人授權</h1><p class="lead">代理人：' + \
            name + '（' + email + '）</p><form method="post" action="/wuchang/agent/authorize"><div class="mb-3"><label>授權人信箱</label><input name="from_email" class="form-control" value="admin@wuchang.life"/></div><div class="mb-3"><label>範圍</label><input name="scope" class="form-control" value="google_all"/></div><button class="btn btn-primary" type="submit">確定授權</button></form></div></body></html>'
        return http.Response(html, status=200)

    @http.route('/voice', type='http', auth='public', website=True)
    def voice_page(self, **kw):
        return request.render('wuchang_core.voice_chat_page', {})

    @http.route('/app/voice', type='http', auth='public', website=True)
    def mobile_voice_page(self, **kw):
        return request.render('wuchang_core.mobile_voice_app', {})

    @http.route('/wuchang/mobile/manifest.json', type='http', auth='public', website=True)
    def mobile_manifest(self):
        manifest = {
            'name': '五常小j',
            'short_name': '小j',
            'start_url': '/app/voice',
            'display': 'standalone',
            'background_color': '#1e293b',
            'theme_color': '#ec4899',
            'icons': [
                {'src': '/web/static/img/logo.png',
                    'sizes': '192x192', 'type': 'image/png'},
                {'src': '/web/static/img/logo.png',
                    'sizes': '512x512', 'type': 'image/png'}
            ]
        }
        return request.make_response(json.dumps(manifest), headers=[('Content-Type', 'application/json')])
        return request.render('wuchang_core.mobile_voice_app', {})

    @http.route('/wuchang/voice/transcribe', type='http', auth='public', methods=['POST'], csrf=False)
    def voice_transcribe(self, **kw):
        import os
        import base64
        import json
        import datetime
        import urllib.request
        files = request.httprequest.files or {}
        f = files.get('audio')
        if not f:
            return http.Response('missing_audio', status=400)
        day = datetime.datetime.utcnow().strftime('%Y%m%d')
        base = os.path.join(os.getcwd(), 'memory_store/conversations')
        try:
            os.makedirs(base, exist_ok=True)
        except Exception:
            pass
        fname = 'voice_' + datetime.datetime.utcnow().strftime('%H%M%S') + '.wav'
        path = os.path.join(base, day + '_' + fname)
        try:
            f.save(path)
        except Exception:
            pass
        params = request.env['ir.config_parameter'].sudo()
        key = params.get_param('wuchang.google_api_key') or ''
        if not key:
            return http.Response(json.dumps({'ok': False, 'error': 'missing_google_api_key'}), status=400, content_type='application/json')
        try:
            with open(path, 'rb') as fp:
                data = fp.read()
            b64 = base64.b64encode(data).decode('ascii')
            payload = {
                "contents": [{
                    "parts": [
                        {"text": "請將以下語音轉寫為繁體中文逐字稿，僅輸出文字內容："},
                        {"inline_data": {"mime_type": "audio/wav", "data": b64}}
                    ]
                }]
            }
            url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=' + key
            req = urllib.request.Request(url, data=json.dumps(payload).encode(
                'utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode('utf-8')
                j = json.loads(body)
            text = ''
            try:
                text = (((j or {}).get('candidates') or [])[0] or {}).get(
                    'content', {}).get('parts', [{}])[0].get('text') or ''
            except Exception:
                text = ''
            if not text:
                return http.Response(json.dumps({'ok': False, 'error': 'no_text'}), status=200, content_type='application/json')
            try:
                request.env['wuchang.task'].sudo().create({
                    'name': '語音轉寫',
                    'description': text,
                    'state': 'new',
                    'category': 'normal',
                })
            except Exception:
                pass
            return http.Response(json.dumps({'ok': True, 'text': text}), status=200, content_type='application/json')
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)}), status=500, content_type='application/json')

    @http.route('/wuchang/notify/discipline_demo', type='json', auth='user')
    def notify_discipline_demo(self, **payload):
        user = request.env.user
        email = (payload or {}).get('email') or ''
        if not email:
            try:
                email = user.partner_id.email or user.email or ''
            except Exception:
                email = user.email or ''
        if not email:
            return {'ok': False, 'error': 'missing_user_email'}
        try:
            import re
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                return {'ok': False, 'error': 'invalid_email'}
        except Exception:
            pass
        Mail = request.env['mail.mail'].sudo()
        subject = '安裝／黨紀通知'
        body = """
        <div style="font-family:Inter,system-ui">
          <p>親愛的家人，以下為「秘書長視訊專線」與「安裝／黨紀郵件」的上線規劃：</p>
          <ul>
            <li>視訊專線：/hotline/secgen（WebRTC，自建 SFU，可錄影存證）</li>
            <li>郵件機制：Odoo 模板與審計，收件人清單與退件重試</li>
            <li>記憶封存：memory_store/ 不壓縮＋雜湊，每日完整度驗證</li>
          </ul>
          <p>若需立即開工，我會先部署本地視訊服務，建立 OTP 門禁與錄影存證。</p>
        </div>
        """
        rec = Mail.create(
            {'subject': subject, 'body_html': body, 'email_to': email})
        try:
            rec.send()
            sent = True
        except Exception:
            sent = False
        return {'ok': True, 'queued': (not sent), 'email': email}

    @http.route('/voice/reference', type='http', auth='public', website=True)
    def voice_reference(self, **kw):
        ok = kw.get('ok') or ''
        return request.render('wuchang_core.voice_reference_page', {'ok': ok})

    @http.route('/voice/reference/upload', type='http', auth='public', methods=['POST'], csrf=True)
    def voice_reference_upload(self, **kw):
        import os
        import json
        import datetime
        import re
        subject = kw.get('subject') or '語音參考'
        notes = kw.get('notes') or ''
        transcript = kw.get('transcript') or ''
        files = request.httprequest.files or {}
        f = files.get('sample')
        ts = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
        slug = re.sub(r"[^a-z0-9]+", "_",
                      (subject or 'ref').lower()).strip('_') or 'ref'
        base = os.path.join(os.getcwd(), 'memory_store/voice_samples')
        path = os.path.join(base, ts + '_' + slug)
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass
        saved = None
        if f:
            try:
                fname = re.sub(r"[^a-zA-Z0-9._-]+", "_",
                               f.filename or 'sample.wav')
                out = os.path.join(path, fname)
                f.save(out)
                saved = out
            except Exception:
                saved = None
        meta = {
            'subject': subject,
            'notes': notes,
            'transcript': transcript,
            'file': saved,
            'created_at': datetime.datetime.utcnow().isoformat() + 'Z',
        }
        try:
            with open(os.path.join(path, 'meta.json'), 'w', encoding='utf-8') as fp:
                fp.write(json.dumps(meta, ensure_ascii=False, indent=2))
        except Exception:
            pass
        Task = request.env['wuchang.task'].sudo()
        Task.create({
            'name': '語音參考：' + subject,
            'description': (notes or '') + (('\n\n逐字稿：\n' + transcript) if transcript else ''),
            'state': 'in_progress',
            'category': 'normal',
        })
        return request.redirect('/voice/reference?ok=1')

    @http.route('/wuchang/conversation/log', type='json', auth='user')
    def conversation_log(self, **payload):
        import os
        import json
        import datetime
        text = (payload or {}).get('text') or ''
        role = (payload or {}).get('role') or 'user'
        page = (payload or {}).get('page') or 'voice'
        ua = request.httprequest.headers.get('User-Agent') or ''
        uid = request.uid
        day = datetime.datetime.utcnow().strftime('%Y%m%d')
        base = os.path.join(os.getcwd(), 'memory_store/conversations')
        try:
            os.makedirs(base, exist_ok=True)
        except Exception:
            pass
        path = os.path.join(base, day + '.jsonl')
        rec = {
            'ts': datetime.datetime.utcnow().isoformat() + 'Z',
            'uid': uid,
            'role': role,
            'page': page,
            'ua': ua,
            'text': text,
        }
        try:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        except Exception:
            return {'ok': False}
        return {'ok': True}

    @http.route('/needs', type='http', auth='public', website=True)
    def needs_page(self, **kw):
        ok = kw.get('ok') or ''
        return request.render('wuchang_core.needs_page', {'ok': ok})

    @http.route('/needs/submit', type='http', auth='public', methods=['POST'], csrf=True)
    def needs_submit(self, **kw):
        subject = kw.get('subject') or '居民需求'
        role = kw.get('role') or ''
        urgency = kw.get('urgency') or ''
        contact_name = kw.get('contact_name') or ''
        contact = kw.get('contact') or ''
        detail = kw.get('detail') or ''
        desc = ''
        if role:
            desc += '角色: ' + role + '\n'
        if urgency:
            desc += '緊急程度: ' + urgency + '\n'
        if contact_name or contact:
            desc += '聯絡人: ' + (contact_name or '') + \
                ' ' + (contact or '') + '\n'
        if detail:
            desc += '\n' + detail
        Task = request.env['wuchang.task'].sudo()
        Task.create({
            'name': subject,
            'description': desc,
            'state': 'new',
            'category': 'resident_need',
        })
        return request.redirect('/needs?ok=1')

    @http.route('/wuchang/llm/generate', type='http', auth='public', methods=['POST'], csrf=False)
    def llm_generate(self):
        key = 'llm:' + str(request.uid)
        global _rate
        try:
            arr = _rate.get(key, [])
        except Exception:
            arr = []
        now = time.time()
        arr = [t for t in arr if now - t < 1.0]
        if len(arr) >= 2:
            return http.Response(json.dumps({"error": "rate_limited"}), status=429, content_type='application/json')
        arr.append(now)
        _rate[key] = arr
        import json
        raw = request.httprequest.get_data()
        payload = {}
        if raw:
            try:
                payload = json.loads(raw.decode('utf-8'))
            except Exception:
                payload = {}
        if not payload:
            payload = dict(request.params) if request.params else {}
        if not isinstance(payload, dict):
            payload = {}
        if not payload:
            return http.Response(json.dumps({"error": "invalid_json"}), status=400, content_type='application/json')
        prompt = payload.get('prompt') or payload.get('contents', [{}])[
            0].get('parts', [{}])[0].get('text', '')
        params = request.env['ir.config_parameter'].sudo()
        ai_mode = params.get_param('wuchang.ai_mode') or 'local_ollama'
        policy_ready = params.get_param('wuchang.org.policy_ready') or ''
        require_restrict = params.get_param(
            'wuchang.org.require_key_restriction') or ''
        if ai_mode == 'external_key' and require_restrict and not policy_ready:
            return http.Response(json.dumps({"error": "org_policy_not_ready"}), status=403, content_type='application/json')
        day = time.strftime('%Y%m%d')
        dq_raw = params.get_param('wuchang.llm.daily_quota') or ''
        try:
            daily_quota = int(dq_raw or '0')
        except Exception:
            daily_quota = 0
        used_raw = params.get_param('wuchang.llm.daily_used.' + day) or ''
        try:
            daily_used = int(used_raw or '0')
        except Exception:
            daily_used = 0
        if daily_quota > 0 and daily_used >= daily_quota:
            return http.Response(json.dumps({"error": "quota_exceeded"}), status=429, content_type='application/json')
        logic = request.env['wuchang.ai.logic']
        text_out = logic.general_generate(prompt)
        if daily_quota > 0:
            try:
                params.set_param('wuchang.llm.daily_used.' +
                                 day, str(daily_used + 1))
            except Exception:
                pass
        result = {"candidates": [
            {"content": {"parts": [{"text": text_out or ''}]}}]}
        return http.Response(json.dumps(result), status=200, content_type='application/json')

    @http.route('/wuchang/ai/chat', type='json', auth='none', methods=['POST'], csrf=False)
    def ai_chat(self, **payload):
        message = (payload or {}).get('message') or ''
        metadata = (payload or {}).get('metadata') or {}
        if not isinstance(metadata, dict):
            metadata = {}
        device_type = metadata.get('device_type') or 'desktop'
        page = metadata.get('page') or 'voice'
        session_id = metadata.get('session_id')
        user_id = metadata.get('user_id')
        env = request.env
        VoiceConv = env['wuchang.voice.conversation'].sudo()
        AILogic = env['wuchang.ai.logic'].sudo()
        try:
            if user_id:
                try:
                    user_id = int(user_id)
                except Exception:
                    user_id = None
            if not user_id:
                user_id = env.user.id
        except Exception:
            user_id = env.user.id
        start = time.time()
        reply = AILogic.analyze_operations(message)
        conv = VoiceConv.create_conversation(
            user_message=message,
            user_id=user_id,
            session_id=session_id,
            device_type=device_type,
            page=page,
        )
        conv.update_response(reply, response_time=(time.time() - start))
        return {
            'reply': reply,
            'session_id': conv.session_id,
            'conversation_id': conv.id,
            'user_id': user_id,
        }

    @http.route('/wuchang/config/llm/get', type='json', auth='user')
    def llm_config_get(self):
        params = request.env['ir.config_parameter'].sudo()
        return {
            'ok': True,
            'ai_mode': params.get_param('wuchang.ai_mode') or '',
            'google_api_key_set': bool(params.get_param('wuchang.google_api_key')),
            'gen_model': params.get_param('wuchang.gen_model') or '',
            'ollama_model': params.get_param('wuchang.ollama_model') or '',
            'master_logic_path': params.get_param('wuchang.master_logic_path') or '',
        }

    @http.route('/wuchang/config/llm', type='json', auth='user')
    def llm_config_set(self, **payload):
        user = request.env.user
        mode = (payload or {}).get('ai_mode') or ''
        key = (payload or {}).get('google_api_key') or ''
        model = (payload or {}).get('gen_model') or ''
        ollama_model = (payload or {}).get('ollama_model') or ''
        master_logic_path = (payload or {}).get('master_logic_path') or ''
        params = request.env['ir.config_parameter'].sudo()
        import json
        accs_raw = params.get_param('founder.identity.google_accounts') or '[]'
        try:
            founders = json.loads(accs_raw)
        except Exception:
            founders = []
        delegates_raw = params.get_param('founder.delegates') or '[]'
        try:
            delegates = json.loads(delegates_raw)
        except Exception:
            delegates = []
        allowed = (user.login in founders) or (
            user.login == 'o970106@gmail.com') or (user.login in delegates)
        actor_is_founder = (user.login in founders) or (
            user.login == 'o970106@gmail.com')
        override_on = (params.get_param('supreme.override.enabled')
                       or 'false').lower() in ('1', 'true', 'yes')
        if override_on and not actor_is_founder:
            return {'ok': False, 'error': 'founder_only'}
        if not allowed:
            return {'ok': False, 'error': 'forbidden'}
        sealed = bool(params.get_param('wuchang.ai.global_suppression'))
        if sealed:
            return {'ok': False, 'error': 'sealed'}
        if not self._cipher_ok():
            return {'ok': False, 'error': 'cipher_required'}
        import time
        if not actor_is_founder:
            try:
                last_ts = int(params.get_param(
                    'wuchang.authority.last_founder_ts') or '0')
            except Exception:
                last_ts = 0
            if (int(time.time()) - last_ts) < 120:
                return {'ok': False, 'error': 'conflict_founder_priority'}
        if mode:
            params.set_param('wuchang.ai_mode', mode)
        if model:
            params.set_param('wuchang.gen_model', model)
        if key:
            params.set_param('wuchang.google_api_key', key)
        if ollama_model:
            params.set_param('wuchang.ollama_model', ollama_model)
        if master_logic_path:
            params.set_param('wuchang.master_logic_path', master_logic_path)
        if actor_is_founder:
            try:
                params.set_param(
                    'wuchang.authority.last_founder_ts', str(int(time.time())))
            except Exception:
                pass
        return {'ok': True}

    @http.route('/wuchang/config/llm/policy/get', type='json', auth='user')
    def llm_policy_get(self):
        p = request.env['ir.config_parameter'].sudo()
        day = time.strftime('%Y%m%d')
        used = int(p.get_param('wuchang.llm.daily_used.' + day) or '0')
        keys_raw = p.get_param('wuchang.google_api_keys') or '[]'
        cnt = 0
        try:
            arr = json.loads(keys_raw)
            if isinstance(arr, list):
                cnt = len(arr)
        except Exception:
            cnt = 0
        return {
            'ok': True,
            'require_key_restriction': bool(p.get_param('wuchang.org.require_key_restriction')),
            'policy_ready': bool(p.get_param('wuchang.org.policy_ready')),
            'daily_quota': int(p.get_param('wuchang.llm.daily_quota') or '0'),
            'daily_used': used,
            'keys_count': cnt,
            'key_set': bool(p.get_param('wuchang.google_api_key')),
        }

    @http.route('/wuchang/config/llm/policy', type='json', auth='user')
    def llm_policy_set(self, **payload):
        user = request.env.user
        p = request.env['ir.config_parameter'].sudo()
        import json
        accs_raw = p.get_param('founder.identity.google_accounts') or '[]'
        try:
            founders = json.loads(accs_raw)
        except Exception:
            founders = []
        delegates_raw = p.get_param('founder.delegates') or '[]'
        try:
            delegates = json.loads(delegates_raw)
        except Exception:
            delegates = []
        allowed = (user.login in founders) or (
            user.login == 'o970106@gmail.com') or (user.login in delegates)
        actor_is_founder = (user.login in founders) or (
            user.login == 'o970106@gmail.com')
        override_on = (p.get_param('supreme.override.enabled')
                       or 'false').lower() in ('1', 'true', 'yes')
        if override_on and not actor_is_founder:
            return {'ok': False, 'error': 'founder_only'}
        if not allowed:
            return {'ok': False, 'error': 'forbidden'}
        sealed = bool(p.get_param('wuchang.ai.global_suppression'))
        if sealed:
            return {'ok': False, 'error': 'sealed'}
        if not self._cipher_ok():
            return {'ok': False, 'error': 'cipher_required'}
        import time
        if not actor_is_founder:
            try:
                last_ts = int(p.get_param(
                    'wuchang.authority.last_founder_ts') or '0')
            except Exception:
                last_ts = 0
            if (int(time.time()) - last_ts) < 120:
                return {'ok': False, 'error': 'conflict_founder_priority'}
        rq = payload.get('require_key_restriction')
        pr = payload.get('policy_ready')
        dq = payload.get('daily_quota')
        keys_text = payload.get('keys_text') or ''
        if rq is not None:
            p.set_param('wuchang.org.require_key_restriction',
                        '1' if rq else '')
        if pr is not None:
            p.set_param('wuchang.org.policy_ready', '1' if pr else '')
        if dq is not None:
            try:
                p.set_param('wuchang.llm.daily_quota', str(int(dq)))
            except Exception:
                p.set_param('wuchang.llm.daily_quota', '0')
        if keys_text:
            lines = [s.strip() for s in keys_text.splitlines() if s.strip()]
            try:
                p.set_param('wuchang.google_api_keys', json.dumps(lines))
            except Exception:
                pass
        if actor_is_founder:
            try:
                p.set_param('wuchang.authority.last_founder_ts',
                            str(int(time.time())))
            except Exception:
                pass
        return {'ok': True}

    @http.route('/wuchang/llm/health', type='json', auth='user')
    def llm_health(self):
        p = request.env['ir.config_parameter'].sudo()
        mode = p.get_param('wuchang.ai_mode') or 'local_ollama'
        key = p.get_param('wuchang.google_api_key') or ''
        gen_model = p.get_param('wuchang.gen_model') or ''
        ollama_model = p.get_param('wuchang.ollama_model') or ''
        google_ok = False
        google_error = ''
        if key:
            try:
                url = 'https://generativelanguage.googleapis.com/v1beta/models?key=' + \
                    urllib.parse.quote(key)
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=6) as resp:
                    if resp.getcode() == 200:
                        google_ok = True
            except Exception as e:
                google_ok = False
                google_error = str(e)[:120]
        ollama_ok = False
        ollama_error = ''
        try:
            req2 = urllib.request.Request('https://llm.wuchang.life/api/tags')
            with urllib.request.urlopen(req2, timeout=6) as r2:
                if r2.getcode() == 200:
                    ollama_ok = True
        except Exception as e:
            ollama_ok = False
            ollama_error = str(e)[:120]
        return {
            'ok': True,
            'mode': mode,
            'google_api_key_set': bool(key),
            'gen_model': gen_model,
            'ollama_model': ollama_model,
            'google_ok': google_ok,
            'google_error': google_error,
            'ollama_ok': ollama_ok,
            'ollama_error': ollama_error,
        }

    @http.route('/wuchang/llm/generate_humor', type='http', auth='public', methods=['POST'], csrf=False)
    def llm_generate_humor(self):
        key = 'llmhumor:' + str(request.uid)
        global _rate
        try:
            arr = _rate.get(key, [])
        except Exception:
            arr = []
        now = time.time()
        arr = [t for t in arr if now - t < 1.0]
        if len(arr) >= 2:
            return http.Response('rate_limited', status=429)
        arr.append(now)
        _rate[key] = arr
        import json
        raw = request.httprequest.get_data()
        payload = {}
        if raw:
            try:
                payload = json.loads(raw.decode('utf-8'))
            except Exception:
                payload = {}
        if not isinstance(payload, dict):
            payload = {}
        base = ''
        try:
            base = payload.get('prompt') or payload.get('contents', [{}])[
                0].get('parts', [{}])[0].get('text', '')
        except Exception:
            base = ''
        style = '以幽默、溫暖、機智但不冒犯的語氣回答，簡潔準確，必要時用貼近生活的比喻強化理解。'
        full = (style + '\n\n' + str(base or '')).strip()
        logic = request.env['wuchang.ai.logic']
        out = logic.general_generate(full)
        result = {"candidates": [
            {"content": {"parts": [{"text": out or ''}]}}]}
        return http.Response(json.dumps(result), status=200, content_type='application/json')

    @http.route('/wuchang/cloud/identity/get', type='json', auth='user')
    def cloud_identity_get(self):
        p = request.env['ir.config_parameter'].sudo()
        return {
            'ok': True,
            'project_id': p.get_param('wuchang.cloud.project_id') or '',
            'service_account_email': p.get_param('wuchang.cloud.service_account_email') or '',
            'identity_name': p.get_param('wuchang.cloud.identity_name') or '',
        }

    @http.route('/wuchang/cloud/identity', type='json', auth='user')
    def cloud_identity_set(self, **payload):
        p = request.env['ir.config_parameter'].sudo()
        pid = payload.get('project_id') or ''
        sa = payload.get('service_account_email') or ''
        name = payload.get('identity_name') or ''
        if pid:
            p.set_param('wuchang.cloud.project_id', pid)
        if sa:
            p.set_param('wuchang.cloud.service_account_email', sa)
        if name:
            p.set_param('wuchang.cloud.identity_name', name)
        return {'ok': True}

    @http.route('/wuchang/workspace/get', type='json', auth='user')
    def workspace_get(self):
        p = request.env['ir.config_parameter'].sudo()
        tok_raw = p.get_param('wuchang.drive.oauth_token_json') or ''
        ok = False
        try:
            ok = bool(json.loads(tok_raw))
        except Exception:
            ok = False
        return {
            'ok': True,
            'workspace_name': p.get_param('wuchang.workspace.name') or '',
            'vm_ip': p.get_param('wuchang.workspace.vm_ip') or '',
            'memory_folder_id': p.get_param('wuchang.drive.memory_folder_id') or '',
            'drive_connected': ok,
        }

    @http.route('/wuchang/workspace/set', type='json', auth='user')
    def workspace_set(self, **payload):
        p = request.env['ir.config_parameter'].sudo()
        name = (payload or {}).get('workspace_name') or ''
        vm_ip = (payload or {}).get('vm_ip') or ''
        if name:
            p.set_param('wuchang.workspace.name', name)
        if vm_ip:
            p.set_param('wuchang.workspace.vm_ip', vm_ip)
        return {'ok': True}

    @http.route('/wuchang/ai/governance/get', type='json', auth='user')
    def ai_governance_get(self):
        p = request.env['ir.config_parameter'].sudo()

        def as_int(v):
            try:
                return int(v or '0')
            except Exception:
                return 0
        return {
            'ok': True,
            'constitution': p.get_param('wuchang.ai.constitution.text') or '',
            'root_user_id': as_int(p.get_param('wuchang.ai.root.user_id') or ''),
            'root_name': p.get_param('wuchang.ai.root.name') or '',
            'global_suppression': bool(p.get_param('wuchang.ai.global_suppression')),
            'suppress_reason': p.get_param('wuchang.ai.suppress.reason') or '',
            'current_user_id': request.env.user.id,
        }

    @http.route('/wuchang/ai/governance', type='json', auth='user')
    def ai_governance_set(self, **payload):
        p = request.env['ir.config_parameter'].sudo()
        user = request.env.user
        const = (payload or {}).get('constitution')
        rid = (payload or {}).get('root_user_id')
        rname = (payload or {}).get('root_name')
        sup = (payload or {}).get('global_suppression')
        sreason = (payload or {}).get('suppress_reason')
        import json
        accs_raw = p.get_param('founder.identity.google_accounts') or '[]'
        try:
            founders = json.loads(accs_raw)
        except Exception:
            founders = []
        delegates_raw = p.get_param('founder.delegates') or '[]'
        try:
            delegates = json.loads(delegates_raw)
        except Exception:
            delegates = []
        founder_only = (user.login in founders) or (
            user.login == 'o970106@gmail.com') or (user.login in delegates)
        admin_ok = founder_only
        sealed = bool(p.get_param('wuchang.ai.global_suppression'))
        if sealed:
            return {'ok': False, 'error': 'sealed'}
        touching = (const is not None) or (rid is not None) or (
            rname is not None) or (sup is not None) or (sreason is not None)
        if touching and (not self._cipher_ok()):
            return {'ok': False, 'error': 'cipher_required'}
        import time
        actor_is_founder = (user.login in founders) or (
            user.login == 'o970106@gmail.com')
        override_on = (p.get_param('supreme.override.enabled')
                       or 'false').lower() in ('1', 'true', 'yes')
        if touching and override_on and not actor_is_founder:
            return {'ok': False, 'error': 'founder_only'}
        if touching and (not actor_is_founder):
            try:
                last_ts = int(p.get_param(
                    'wuchang.authority.last_founder_ts') or '0')
            except Exception:
                last_ts = 0
            if (int(time.time()) - last_ts) < 120:
                return {'ok': False, 'error': 'conflict_founder_priority'}
        if const is not None and not founder_only:
            return {'ok': False, 'error': 'constitution_forbidden'}
        if (rid is not None) or (rname is not None) or (sup is not None) or (sreason is not None):
            if not admin_ok:
                return {'ok': False, 'error': 'forbidden'}
        if const is not None:
            p.set_param('wuchang.ai.constitution.text', str(const or ''))
        if rname is not None:
            p.set_param('wuchang.ai.root.name', str(rname or ''))
        if rid is not None:
            try:
                p.set_param('wuchang.ai.root.user_id', str(int(rid)))
            except Exception:
                p.set_param('wuchang.ai.root.user_id', '0')
        if sup is not None:
            p.set_param('wuchang.ai.global_suppression', '1' if sup else '')
        if sreason is not None:
            p.set_param('wuchang.ai.suppress.reason', str(sreason or ''))
        if actor_is_founder and touching:
            try:
                p.set_param('wuchang.authority.last_founder_ts',
                            str(int(time.time())))
            except Exception:
                pass
        return {'ok': True}

    @http.route('/wuchang/ai/suppress', type='json', auth='user')
    def ai_suppress(self, enable=False, reason=''):
        p = request.env['ir.config_parameter'].sudo()
        user = request.env.user
        import json
        accs_raw = p.get_param('founder.identity.google_accounts') or '[]'
        try:
            founders = json.loads(accs_raw)
        except Exception:
            founders = []
        delegates_raw = p.get_param('founder.delegates') or '[]'
        try:
            delegates = json.loads(delegates_raw)
        except Exception:
            delegates = []
        allowed = (user.login in founders) or (
            user.login == 'o970106@gmail.com') or (user.login in delegates)
        actor_is_founder = (user.login in founders) or (
            user.login == 'o970106@gmail.com')
        override_on = (p.get_param('supreme.override.enabled')
                       or 'false').lower() in ('1', 'true', 'yes')
        if override_on and not actor_is_founder:
            return {'ok': False, 'error': 'founder_only'}
        if not allowed:
            return {'ok': False, 'error': 'forbidden'}
        if not self._cipher_ok():
            return {'ok': False, 'error': 'cipher_required'}
        p.set_param('wuchang.ai.global_suppression', '1' if enable else '')
        p.set_param('wuchang.ai.suppress.reason', str(reason or ''))
        if actor_is_founder:
            try:
                import time as _t
                p.set_param('wuchang.authority.last_founder_ts',
                            str(int(_t.time())))
            except Exception:
                pass
        return {'ok': True}

    @http.route('/wuchang/finance/fund_dissolve_plan', type='json', auth='user')
    def finance_fund_dissolve_plan(self, account_type='general', currency='TWD', target='merchants', recipients=None):
        p = request.env['ir.config_parameter'].sudo()
        user = request.env.user
        import json
        accs_raw = p.get_param('founder.identity.google_accounts') or '[]'
        try:
            founders = json.loads(accs_raw)
        except Exception:
            founders = []
        actor_is_founder = (user.login in founders) or (
            user.login == 'o970106@gmail.com')
        override_on = (p.get_param('supreme.override.enabled')
                       or 'false').lower() in ('1', 'true', 'yes')
        if not actor_is_founder:
            return {'ok': False, 'error': 'forbidden'}
        if not override_on:
            return {'ok': False, 'error': 'override_required'}
        if not self._cipher_ok():
            return {'ok': False, 'error': 'cipher_required'}
        Fund = request.env['community.fund.account'].sudo()
        fund = Fund.search([('account_type', '=', str(account_type))], limit=1)
        if not fund:
            return {'ok': False, 'error': 'fund_not_found'}
        total = float(fund.balance_twd or 0.0) if str(
            currency).upper() == 'TWD' else float(fund.balance_whc or 0.0)
        Partner = request.env['res.partner'].sudo()
        items = []
        if str(target) == 'specified' and isinstance(recipients, list) and recipients:
            dests = []
            try:
                dests = Partner.browse(
                    [int(x) for x in recipients if isinstance(x, int)])
            except Exception:
                dests = Partner.browse([])
            cnt = len(dests)
            if cnt == 0:
                return {'ok': False, 'error': 'no_recipients'}
            each = (total / cnt) if cnt > 0 else 0.0
            for d in dests:
                items.append(
                    {'partner_id': d.id, 'name': d.name, 'amount': each})
        else:
            if str(target) == 'consumers':
                dests = Partner.search([('customer_rank', '>', 0)])
            elif str(target) == 'merchants':
                dests = Partner.search([('supplier_rank', '>', 0)])
            else:
                dests = Partner.search(
                    ['|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0)])
            cnt = len(dests)
            if cnt == 0:
                return {'ok': False, 'error': 'no_recipients'}
            each = (total / cnt) if cnt > 0 else 0.0
            for d in dests:
                items.append(
                    {'partner_id': d.id, 'name': d.name, 'amount': each})
        return {'ok': True, 'fund_id': fund.id, 'account_type': fund.account_type, 'currency': str(currency).upper(), 'total': total, 'count': len(items), 'items': items}

    @http.route('/wuchang/finance/fund_dissolve_execute', type='json', auth='user')
    def finance_fund_dissolve_execute(self, plan=None):
        p = request.env['ir.config_parameter'].sudo()
        user = request.env.user
        import json
        import hashlib
        accs_raw = p.get_param('founder.identity.google_accounts') or '[]'
        try:
            founders = json.loads(accs_raw)
        except Exception:
            founders = []
        actor_is_founder = (user.login in founders) or (
            user.login == 'o970106@gmail.com')
        override_on = (p.get_param('supreme.override.enabled')
                       or 'false').lower() in ('1', 'true', 'yes')
        if not actor_is_founder:
            return {'ok': False, 'error': 'forbidden'}
        if not override_on:
            return {'ok': False, 'error': 'override_required'}
        if not self._cipher_ok():
            return {'ok': False, 'error': 'cipher_required'}
        if not isinstance(plan, dict):
            return {'ok': False, 'error': 'invalid_plan'}
        fid = int(plan.get('fund_id') or 0)
        currency = str(plan.get('currency') or 'TWD').upper()
        items = plan.get('items') or []
        Fund = request.env['community.fund.account'].sudo()
        fund = Fund.browse(fid)
        if not fund or not fund.exists():
            return {'ok': False, 'error': 'fund_not_found'}
        total = float(plan.get('total') or 0.0)
        if currency == 'TWD':
            available = float(fund.balance_twd or 0.0)
        else:
            available = float(fund.balance_whc or 0.0)
        if total <= 0.0 or available < total:
            return {'ok': False, 'error': 'insufficient_fund'}
        Partner = request.env['res.partner'].sudo()
        Coin = request.env['wuchang.coin.transaction'].sudo()
        Log = request.env['transparency.log'].sudo()
        src_partner = request.env.company and request.env.company.partner_id
        ok = True
        for it in items:
            pid = int(it.get('partner_id') or 0)
            amt = float(it.get('amount') or 0.0)
            if pid <= 0 or amt <= 0.0:
                continue
            dest = Partner.browse(pid)
            if not dest or not dest.exists():
                continue
            if currency == 'WHC':
                t = Coin.create({'source_partner_id': src_partner.id if src_partner else False,
                                'dest_partner_id': dest.id, 'amount': amt, 'transaction_type': 'transfer'})
                try:
                    s = str(src_partner and src_partner.id or 0) + '|' + \
                        str(dest.id) + '|' + str(amt) + '|' + str(t.timestamp)
                    h = hashlib.sha256(s.encode('utf-8')).hexdigest()
                    t.write({'hash_signature': h})
                except Exception:
                    pass
            else:
                Log.create({'name': '基金解散匯出', 'amount': amt,
                           'flow_type': 'outflow'})
        if currency == 'TWD':
            Fund.browse(fid).write({'balance_twd': available - total})
        else:
            Fund.browse(fid).write({'balance_whc': available - total})
        Log.create({'name': '基金解散總匯出', 'amount': total, 'flow_type': 'outflow'})
        try:
            p.set_param('wuchang.authority.last_founder_ts',
                        str(int(time.time())))
        except Exception:
            pass
        return {'ok': ok, 'executed_total': total, 'currency': currency}

    @http.route('/wuchang/google/oauth/config', type='json', auth='user')
    def google_oauth_config(self, **payload):
        p = request.env['ir.config_parameter'].sudo()
        cid = payload.get('client_id') or ''
        sec = payload.get('client_secret') or ''
        if cid:
            p.set_param('google.oauth.client_id', cid)
        if sec:
            p.set_param('google.oauth.client_secret', sec)
        return {'ok': True}

    @http.route('/wuchang/google/oauth/status', type='json', auth='user')
    def google_oauth_status(self):
        p = request.env['ir.config_parameter'].sudo()
        tok_raw = p.get_param('wuchang.drive.oauth_token_json') or ''
        ok = False
        try:
            ok = bool(json.loads(tok_raw))
        except Exception:
            ok = False
        return {
            'ok': True,
            'client_id_set': bool(p.get_param('google.oauth.client_id')),
            'client_secret_set': bool(p.get_param('google.oauth.client_secret')),
            'token_set': ok,
        }

    @http.route('/wuchang/google/oauth/start', type='http', auth='user')
    def google_oauth_start(self):
        p = request.env['ir.config_parameter'].sudo()
        cid = p.get_param('google.oauth.client_id') or ''
        redirect_uri = request.httprequest.host_url.rstrip(
            '/') + '/wuchang/google/oauth/callback'
        if not cid:
            return http.Response('missing_client_id', status=400)
        qs = {
            'client_id': cid,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent',
            'scope': 'https://www.googleapis.com/auth/drive.file',
        }
        url = 'https://accounts.google.com/o/oauth2/v2/auth?' + \
            urllib.parse.urlencode(qs)
        return request.redirect(url)

    @http.route('/wuchang/google/oauth/callback', type='http', auth='user')
    def google_oauth_callback(self, **kw):
        code = kw.get('code') or ''
        p = request.env['ir.config_parameter'].sudo()
        cid = p.get_param('google.oauth.client_id') or ''
        sec = p.get_param('google.oauth.client_secret') or ''
        redirect_uri = request.httprequest.host_url.rstrip(
            '/') + '/wuchang/google/oauth/callback'
        if not code or not cid or not sec:
            return http.Response('missing_params', status=400)
        data = urllib.parse.urlencode({
            'code': code,
            'client_id': cid,
            'client_secret': sec,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }).encode('utf-8')
        req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data, headers={
                                     'Content-Type': 'application/x-www-form-urlencoded'})
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode('utf-8')
                p.set_param('wuchang.drive.oauth_token_json', body)
                return http.Response('<html><body><p>Google Drive 已連接</p><p><a href="/">返回首頁</a></p></body></html>')
        except Exception as e:
            body = '<h1 class="display-6 mb-3">Google Drive 交換失敗</h1><p class="text-danger">exchange_failed: ' + \
                str(e) + '</p>'
            html = self._simple_website_page('Google Drive 交換失敗', body)
            return http.Response(html, status=400)

    @http.route('/wuchang/task/create', type='json', auth='user')
    def create_task(self, **payload):
        title = (payload or {}).get('title') or '外部任務'
        url = (payload or {}).get('url') or ''
        owner = request.env.user
        Task = request.env['wuchang.task'].sudo()
        vals = {
            'name': title,
            'description': (url and ('來源鏈結: ' + url)) or '',
            'owner_id': owner.id,
            'state': 'in_progress'
        }
        task = Task.create(vals)
        if url:
            task.message_post(body='[來源] ' + url)
        return {'ok': True, 'task_id': task.id, 'name': task.name, 'url': url}

    @http.route('/wuchang/task/bulk_import', type='json', auth='user')
    def bulk_import_tasks(self, **payload):
        items = (payload or {}).get('items') or []
        owner = request.env.user
        Task = request.env['wuchang.task'].sudo()
        created = []
        for it in items:
            title = it.get('title') or '外部任務'
            url = it.get('url') or ''
            category = it.get('category') or 'normal'
            vals = {
                'name': title,
                'description': (url and ('來源鏈結: ' + url)) or '',
                'owner_id': owner.id,
                'state': 'in_progress',
                'category': category,
            }
            task = Task.create(vals)
            if url:
                task.message_post(body='[來源] ' + url)
            created.append({'id': task.id, 'name': task.name,
                           'url': url, 'category': category})
        return {'ok': True, 'created': created, 'count': len(created)}

    @http.route('/wuchang/pos/expense/create', type='http', auth='public', methods=['POST'], csrf=False)
    def pos_expense_create(self):
        import json
        raw = request.httprequest.get_data()
        payload = {}
        if raw:
            try:
                payload = json.loads(raw.decode('utf-8'))
            except Exception:
                payload = {}
        reason = (payload or {}).get('reason') or ''
        amount = (payload or {}).get('amount') or 0
        table = (payload or {}).get('table') or ''
        config_id = (payload or {}).get('config_id')
        try:
            amt = float(amount)
        except Exception:
            amt = 0.0
        Expense = request.env['wuchang.pos.expense'].sudo()
        vals = {
            'reason': reason.strip()[:128],
            'amount': amt,
            'table_name': table.strip()[:32],
        }
        if config_id and str(config_id).isdigit():
            vals['pos_config_id'] = int(config_id)
        rec = Expense.create(vals)
        return http.Response(json.dumps({'ok': True, 'ref': rec.name}), status=200, content_type='application/json')

    @http.route(['/delivery', '/wuchang/delivery'], type='http', auth='public', website=True)
    def delivery_home(self, config_id=None, **kw):
        configs = []
        try:
            configs = request.env['pos.config'].sudo().search_read([], [
                'name'])
        except Exception:
            configs = []
        return request.render('wuchang_core.delivery_page', {
            'configs': configs,
            'selected_config_id': int(config_id) if config_id and str(config_id).isdigit() else None,
        })

    @http.route('/wuchang/delivery/products', type='json', auth='public')
    def delivery_products(self, config_id=None):
        Product = request.env['product.template'].sudo()
        domain = [('sale_ok', '=', True)]
        fields = Product.fields_get()
        if 'available_in_pos' in fields:
            domain.append(('available_in_pos', '=', True))
        cfg = None
        try:
            cfg = request.env['pos.config'].sudo().browse(
                int(config_id)) if config_id else None
        except Exception:
            cfg = None
        if cfg and cfg.company_id:
            domain.append(('company_id', '=', cfg.company_id.id))
        prods = Product.search(domain, limit=200)

        def img_url(tid):
            return '/web/image/product.template/%s/image_1920' % tid
        out = [{'id': p.id, 'name': p.name or '',
                'price': p.list_price or 0.0, 'image': img_url(p.id)} for p in prods]
        return {'items': out}

    @http.route('/wuchang/delivery/stores', type='json', auth='public')
    def delivery_stores(self):
        try:
            configs = request.env['pos.config'].sudo().search_read([], [
                'name'])
        except Exception:
            configs = []
        params = request.env['ir.config_parameter'].sudo()
        try:
            featured_name = (params.get_param(
                'wuchang.featured_store') or '聊國咖啡重新總店').strip()
        except Exception:
            featured_name = '聊國咖啡重新總店'
        aliases = {
            '重新店': '聊國咖啡重新總店',
            '聊國咖啡館 重新總店': '聊國咖啡重新總店',
            '仁義店': '聊國咖啡仁義分店',
            '聊國咖啡館 仁義分店': '聊國咖啡仁義分店',
        }
        featured_name = aliases.get(featured_name, featured_name)
        all_items = []
        for c in configs:
            name = (c.get('name') or '').strip()
            all_items.append({'id': c.get('id'), 'name': name,
                             'featured': (name == featured_name)})
        featured_items = [i for i in all_items if i.get('featured')]
        other_items = [i for i in all_items if not i.get('featured')]
        return {'items': featured_items + other_items}

    @http.route('/wuchang/pos/summary', type='json', auth='user')
    def pos_summary(self):
        re_cfg = request.env.ref(
            'wuchang_core.pos_config_re_main', raise_if_not_found=False)
        domain = []
        if re_cfg:
            domain.append(('config_id', '!=', re_cfg.id))
        orders = request.env['pos.order'].sudo().search(domain)
        total = sum(o.amount_total or 0.0 for o in orders)
        by_store = {}
        for o in orders:
            name = o.config_id.name if o.config_id else ''
            by_store[name] = (by_store.get(name, 0.0) +
                              (o.amount_total or 0.0))
        return {'total_excluding_re': total, 'by_store': by_store}

    @http.route('/wuchang/pos/monitor', type='json', auth='user')
    def pos_monitor(self, config_id=None, period='today'):
        import datetime
        PosOrder = request.env['pos.order'].sudo()
        cfg = None
        if config_id and str(config_id).isdigit():
            cfg = request.env['pos.config'].sudo().browse(int(config_id))
        if not cfg:
            cfg = request.env.ref(
                'wuchang_core.pos_config_re_main', raise_if_not_found=False)
        if not cfg:
            return {'ok': False, 'error': 'pos_config_not_found'}
        now = datetime.datetime.utcnow()
        start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_24h = now - datetime.timedelta(hours=24)

        def _sum_cnt(start_dt):
            domain = [('config_id', '=', cfg.id), ('date_order',
                                                   '>=', start_dt.strftime('%Y-%m-%d %H:%M:%S'))]
            orders = PosOrder.search(domain)
            amt = sum(o.amount_total or 0.0 for o in orders)
            return {'count': len(orders), 'amount': amt}
        metrics_today = _sum_cnt(start_today)
        metrics_24h = _sum_cnt(start_24h)
        recent = PosOrder.search(
            [('config_id', '=', cfg.id)], limit=10, order='date_order desc')
        recent_items = [{'id': o.id, 'name': o.name or '',
                         'amount': o.amount_total or 0.0, 'date': o.date_order} for o in recent]
        return {'ok': True, 'store': {'id': cfg.id, 'name': cfg.name or ''}, 'metrics': {'today': metrics_today, 'last24h': metrics_24h}, 'recent': recent_items}

    @http.route('/wuchang/camera/snapshot', type='http', auth='user')
    def camera_snapshot(self, store='re'):
        import base64
        import urllib.request
        slug = (store or 're').strip().lower()
        params = request.env['ir.config_parameter'].sudo()
        url_key = f'camera.{slug}.snapshot_url'
        user_key = f'camera.{slug}.username'
        pass_key = f'camera.{slug}.password'
        url = params.get_param(url_key) or ''
        username = params.get_param(user_key) or ''
        password = params.get_param(pass_key) or ''
        if not url:
            return http.Response('missing_snapshot_url', status=404)
        try:
            req = urllib.request.Request(url)
            if username and password:
                token = base64.b64encode(
                    ('%s:%s' % (username, password)).encode('utf-8')).decode('ascii')
                req.add_header('Authorization', 'Basic ' + token)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
                ctype = resp.headers.get('Content-Type') or 'image/jpeg'
                return http.Response(data, status=200, headers={'Content-Type': ctype})
        except Exception:
            return http.Response('snapshot_failed', status=502)

    @http.route('/wuchang/memory/save', type='json', auth='user')
    def memory_save(self, **payload):
        import json
        key = (payload or {}).get('key') or ''
        val = (payload or {}).get('value')
        category = (payload or {}).get('category') or ''
        if not key:
            return {'ok': False, 'error': 'missing_key'}
        params = request.env['ir.config_parameter'].sudo()
        raw = params.get_param('wuchang.memory.vault.json') or '{}'
        try:
            vault = json.loads(raw)
        except Exception:
            vault = {}
        now_ms = int(time.time() * 1000)
        entry = vault.get(key) or {}
        entry['value'] = val
        if category:
            entry['category'] = category
        entry['updatedAt'] = now_ms
        vault[key] = entry
        try:
            params.set_param('wuchang.memory.vault.json', json.dumps(vault))
        except Exception as e:
            return {'ok': False, 'error': 'persist_failed', 'detail': str(e)}
        return {'ok': True, 'key': key, 'entry': entry}

    @http.route('/wuchang/memory/get', type='json', auth='user')
    def memory_get(self, key=None):
        import json
        k = (key or '').strip()
        if not k:
            return {'ok': False, 'error': 'missing_key'}
        params = request.env['ir.config_parameter'].sudo()
        raw = params.get_param('wuchang.memory.vault.json') or '{}'
        try:
            vault = json.loads(raw)
        except Exception:
            vault = {}
        return {'ok': True, 'entry': vault.get(k)}

    @http.route('/wuchang/memory/list', type='json', auth='user')
    def memory_list(self):
        import json
        params = request.env['ir.config_parameter'].sudo()
        raw = params.get_param('wuchang.memory.vault.json') or '{}'
        try:
            vault = json.loads(raw)
        except Exception:
            vault = {}
        items = [{'key': k, 'value': v.get('value'), 'category': v.get(
            'category'), 'updatedAt': v.get('updatedAt')} for k, v in vault.items()]
        return {'ok': True, 'items': items}

    @http.route('/wuchang/memory/append', type='json', auth='user')
    def memory_append(self, **payload):
        import json
        key = (payload or {}).get('key') or ''
        val = (payload or {}).get('value')
        category = (payload or {}).get('category') or ''
        limit_raw = (payload or {}).get('limit')
        if not key:
            return {'ok': False, 'error': 'missing_key'}
        try:
            limit_n = int(limit_raw) if limit_raw is not None else int(
                request.env['ir.config_parameter'].sudo().get_param('wuchang.memory.limit') or '500')
        except Exception:
            limit_n = 500
        params = request.env['ir.config_parameter'].sudo()
        raw = params.get_param('wuchang.memory.vault.json') or '{}'
        try:
            vault = json.loads(raw)
        except Exception:
            vault = {}
        now_ms = int(time.time() * 1000)
        entry = vault.get(key) or {}
        arr = entry.get('value')
        if not isinstance(arr, list):
            arr = []
        arr.append({'ts': now_ms, 'data': val})
        if isinstance(limit_n, int) and limit_n > 0 and len(arr) > limit_n:
            arr = arr[-limit_n:]
        entry['value'] = arr
        if category:
            entry['category'] = category
        entry['updatedAt'] = now_ms
        vault[key] = entry
        try:
            params.set_param('wuchang.memory.vault.json', json.dumps(vault))
        except Exception as e:
            return {'ok': False, 'error': 'persist_failed', 'detail': str(e)}
        return {'ok': True, 'key': key, 'count': len(arr)}

    @http.route('/wuchang/memory/ui/delivery', type='json', auth='public')
    def memory_ui_delivery(self):
        import json
        params = request.env['ir.config_parameter'].sudo()
        featured = (params.get_param('wuchang.featured_store')
                    or '聊國咖啡重新總店').strip()
        aliases = {
            '重新店': '聊國咖啡重新總店',
            '聊國咖啡館 重新總店': '聊國咖啡重新總店',
            '仁義店': '聊國咖啡仁義分店',
            '聊國咖啡館 仁義分店': '聊國咖啡仁義分店',
        }
        featured = aliases.get(featured, featured)
        raw = params.get_param('wuchang.memory.vault.json') or '{}'
        try:
            vault = json.loads(raw)
        except Exception:
            vault = {}
        cfg = vault.get('ui.contract.delivery') or {}
        out = {
            'featured_store': cfg.get('featured_store') or featured,
            'layout': cfg.get('layout') or {'mobile_cols': 1, 'tablet_cols': 2, 'desktop_cols': 3},
            'cards': cfg.get('cards') or {'border': False, 'blur': False, 'background': 'white'},
            'copy': cfg.get('copy') or {'featured_hint': '置頂店家 · 公益捐助人'},
        }
        return {'ok': True, 'contract': out}

    @http.route('/wuchang/convo/save', type='json', auth='public')
    def convo_save(self, text=None, role=None, task=None, tags=None):
        import json
        import time
        params = request.env['ir.config_parameter'].sudo()
        raw = params.get_param('wuchang.memory.vault.json') or '{}'
        try:
            vault = json.loads(raw)
        except Exception:
            vault = {}
        key = 'convo::' + time.strftime('%Y%m%d')
        arr = vault.get(key) or []
        arr.append({'ts': int(time.time()*1000), 'role': (role or ''),
                   'text': (text or ''), 'task': (task or ''), 'tags': tags or []})
        vault[key] = arr
        try:
            params.set_param('wuchang.memory.vault.json', json.dumps(vault))
        except Exception as e:
            return {'ok': False, 'error': 'persist_failed', 'detail': str(e)}
        return {'ok': True, 'count': len(arr)}

    @http.route('/wuchang/convo/task', type='json', auth='public')
    def convo_task(self, id=None, title=None, status=None, hint=None):
        import json
        import time
        params = request.env['ir.config_parameter'].sudo()
        raw = params.get_param('wuchang.memory.vault.json') or '{}'
        try:
            vault = json.loads(raw)
        except Exception:
            vault = {}
        tasks = vault.get('convo.tasks') or {}
        tid = (id or '').strip() or ('t' + str(int(time.time()*1000)))
        cur = tasks.get(tid) or {}
        if title:
            cur['title'] = title
        if status:
            cur['status'] = status
        if hint:
            cur['hint'] = hint
        cur['updatedAt'] = int(time.time()*1000)
        tasks[tid] = cur
        vault['convo.tasks'] = tasks
        try:
            params.set_param('wuchang.memory.vault.json', json.dumps(vault))
        except Exception as e:
            return {'ok': False, 'error': 'persist_failed', 'detail': str(e)}
        return {'ok': True, 'id': tid, 'task': cur}

    @http.route('/wuchang/convo/snapshot', type='json', auth='public')
    def convo_snapshot(self):
        import json
        import time
        params = request.env['ir.config_parameter'].sudo()
        raw = params.get_param('wuchang.memory.vault.json') or '{}'
        try:
            vault = json.loads(raw)
        except Exception:
            vault = {}
        key = 'convo::' + time.strftime('%Y%m%d')
        msgs = vault.get(key) or []
        tasks = vault.get('convo.tasks') or {}
        total = len(tasks)
        done = sum(1 for t in tasks.values() if (t.get('status')
                   or '').lower() in ('done', 'completed', 'ok'))
        pending = sum(1 for t in tasks.values() if (
            t.get('status') or '').lower() in ('pending', 'todo', 'in_progress'))
        return {'ok': True, 'messages': msgs[-5:], 'tasks': tasks, 'summary': {'total': total, 'done': done, 'pending': pending}}

    @http.route('/wuchang/memory/unsorted/create', type='json', auth='user')
    def memory_unsorted_create(self):
        import json
        import urllib.request
        import urllib.parse
        params = request.env['ir.config_parameter'].sudo()
        params.set_param('wuchang.memory.unsorted.enabled', '1')
        raw = params.get_param('wuchang.drive.oauth_token_json') or ''
        try:
            tok = json.loads(raw) if raw else {}
        except Exception:
            tok = {}

        def ensure_token(t):
            if t.get('access_token'):
                return t
            refresh_token = t.get('refresh_token')
            client_id = params.get_param('google.oauth.client_id') or ''
            client_secret = params.get_param(
                'google.oauth.client_secret') or ''
            if not refresh_token or not client_id or not client_secret:
                return t
            data = urllib.parse.urlencode({
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
            }).encode('utf-8')
            req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data, headers={
                                         'Content-Type': 'application/x-www-form-urlencoded'})
            try:
                with urllib.request.urlopen(req) as resp:
                    body = resp.read().decode('utf-8')
                    newt = json.loads(body)
                    t['access_token'] = newt.get('access_token')
            except Exception:
                pass
            return t
        tok = ensure_token(tok)
        if tok.get('access_token'):
            access = tok.get('access_token')
            folder_id = params.get_param(
                'wuchang.drive.memory_folder_id') or ''
            if folder_id:
                name = 'Unsorted'
                q = "name='" + name + "' and '" + folder_id + \
                    "' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                search_url = 'https://www.googleapis.com/drive/v3/files?q=' + \
                    urllib.parse.quote(q)
                req = urllib.request.Request(
                    search_url, headers={'Authorization': 'Bearer ' + access})
                sub_id = ''
                try:
                    with urllib.request.urlopen(req) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                        files = data.get('files') or []
                        if files:
                            sub_id = files[0].get('id') or ''
                except Exception:
                    sub_id = ''
                if not sub_id:
                    meta = json.dumps(
                        {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [folder_id]})
                    create_req = urllib.request.Request('https://www.googleapis.com/drive/v3/files', data=meta.encode('utf-8'), headers={
                        'Authorization': 'Bearer ' + access,
                        'Content-Type': 'application/json; charset=UTF-8',
                    })
                    try:
                        with urllib.request.urlopen(create_req) as resp:
                            out = json.loads(resp.read().decode('utf-8'))
                            sub_id = out.get('id') or ''
                    except Exception:
                        sub_id = ''
                if sub_id:
                    params.set_param(
                        'wuchang.drive.memory_unsorted_id', sub_id)
        return {'ok': True, 'drive_unsorted_id': params.get_param('wuchang.drive.memory_unsorted_id') or ''}

    @http.route('/wuchang/memory/unsorted/ingest', type='json', auth='user')
    def memory_unsorted_ingest(self, **payload):
        import json
        import urllib.request
        global _rate
        key_rl = 'unsorted_ingest:' + str(request.uid)
        try:
            arr = _rate.get(key_rl, [])
        except Exception:
            arr = []
        now = time.time()
        arr = [t for t in arr if now - t < 1.0]
        if len(arr) >= 2:
            return {'ok': False, 'error': 'rate_limited'}
        arr.append(now)
        _rate[key_rl] = arr
        text = (payload or {}).get('text') or ''
        name = (payload or {}).get('name') or ''
        params = request.env['ir.config_parameter'].sudo()
        raw = params.get_param('wuchang.memory.vault.json') or '{}'
        try:
            vault = json.loads(raw)
        except Exception:
            vault = {}
        ts = int(time.time() * 1000)
        key = 'unsorted::' + str(ts)
        vault[key] = {'value': text, 'category': 'unsorted',
                      'updatedAt': ts, 'name': name}
        try:
            params.set_param('wuchang.memory.vault.json', json.dumps(vault))
        except Exception as e:
            return {'ok': False, 'error': 'persist_failed', 'detail': str(e)}
        drive_sub = params.get_param('wuchang.drive.memory_unsorted_id') or ''
        tok_raw = params.get_param('wuchang.drive.oauth_token_json') or ''
        try:
            tok = json.loads(tok_raw) if tok_raw else {}
        except Exception:
            tok = {}
        if drive_sub and tok.get('access_token'):
            boundary = '----wuchangunsortedboundary'
            fname = (name or ('unsorted_' + str(ts) + '.txt'))
            meta = json.dumps({'name': fname, 'parents': [drive_sub]})
            body = (
                '--' + boundary + '\r\n'
                'Content-Type: application/json; charset=UTF-8\r\n\r\n' + meta + '\r\n'
                '--' + boundary + '\r\n'
                'Content-Type: text/plain; charset=UTF-8\r\n\r\n' +
                (text or '') + '\r\n'
                '--' + boundary + '--\r\n'
            ).encode('utf-8')
            req = urllib.request.Request('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart', data=body, headers={
                'Authorization': 'Bearer ' + tok.get('access_token'),
                'Content-Type': 'multipart/related; boundary=' + boundary,
            })
            try:
                with urllib.request.urlopen(req) as resp:
                    resp.read()
            except Exception:
                pass
        return {'ok': True, 'key': key}

    @http.route('/wuchang/platform/admin/assign', type='json', auth='user')
    def platform_admin_assign(self, platform=None, login=None):
        res = request.env['wuchang.platform.admin'].sudo(
        ).set_admin_slot(platform, login)
        return res

    @http.route('/wuchang/platform/admin/slots', type='json', auth='user')
    def platform_admin_slots(self):
        params = request.env['ir.config_parameter'].sudo()
        slots = {
            'volunteer': params.get_param('platform.admin.slot.volunteer') or '',
            'property': params.get_param('platform.admin.slot.property') or '',
            'business': params.get_param('platform.admin.slot.business') or '',
            'services': params.get_param('platform.admin.slot.services') or '',
        }
        return slots

    @http.route('/wuchang/constitution', type='json', auth='public')
    def constitution(self):
        params = request.env['ir.config_parameter'].sudo()
        raw = params.get_param('constitution.snapshot.json') or ''
        try:
            import json
            snap = json.loads(raw) if raw else {}
        except Exception:
            snap = {}
        return {'snapshot': snap, 'raw': raw}

    @http.route('/wuchang/tools/grant_commander', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def grant_commander(self, **kw):
        key = 'grant_commander:' + str(request.uid)
        global _rate
        try:
            arr = _rate.get(key, [])
        except Exception:
            arr = []
        now = time.time()
        arr = [t for t in arr if now - t < 3.0]
        if len(arr) >= 1:
            return {'status': 'rate_limited'}
        arr.append(now)
        _rate[key] = arr
        login = kw.get('login') or ''
        token_param = request.env['ir.config_parameter'].sudo(
        ).get_param('wuchang.tools_token', '')
        req_token = kw.get('token')
        if token_param and req_token != token_param:
            return {'status': 'forbidden'}
        if not login:
            return {'status': 'missing_login'}
        user = request.env['res.users'].sudo().search(
            [('login', '=', login)], limit=1)
        if not user:
            return {'status': 'user_not_found'}
        grp = request.env.ref(
            'wuchang_core.group_wuchang_commander_xiao_j', raise_if_not_found=False)
        if not grp:
            return {'status': 'group_not_found'}
        try:
            user.sudo().write({'groups_id': [(4, grp.id)]})
            return {'status': 'granted', 'login': login, 'group_id': grp.id}
        except Exception as e:
            return {'status': 'write_failed', 'detail': str(e)}

    @http.route('/wuchang/drive/oauth/start', type='http', auth='user', website=True)
    def drive_oauth_start(self, **kw):
        import urllib.parse
        params = request.env['ir.config_parameter'].sudo()
        client_id = params.get_param('google.oauth.client_id') or ''
        redirect_uri = params.get_param('google.oauth.redirect_uri') or ''
        scope = 'https://www.googleapis.com/auth/drive.file'
        if not client_id or not redirect_uri:
            return http.Response('missing_oauth_config', status=400)
        qs = urllib.parse.urlencode({
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent',
            'scope': scope,
        })
        url = 'https://accounts.google.com/o/oauth2/v2/auth?' + qs
        return request.redirect(url)

    @http.route('/wuchang/drive/oauth/callback', type='http', auth='user', website=True)
    def drive_oauth_callback(self, **kw):
        import json
        import urllib.parse
        import urllib.request
        code = kw.get('code') or ''
        params = request.env['ir.config_parameter'].sudo()
        client_id = params.get_param('google.oauth.client_id') or ''
        client_secret = params.get_param('google.oauth.client_secret') or ''
        redirect_uri = params.get_param('google.oauth.redirect_uri') or ''
        if not code or not client_id or not client_secret or not redirect_uri:
            return http.Response('missing_oauth_config', status=400)
        data = urllib.parse.urlencode({
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }).encode('utf-8')
        req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data, headers={
                                     'Content-Type': 'application/x-www-form-urlencoded'})
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode('utf-8')
                token = json.loads(body)
        except Exception:
            token = {}
        if not token:
            return http.Response('oauth_exchange_failed', status=400)
        params.set_param('wuchang.drive.oauth_token_json', json.dumps(token))
        return http.Response('drive_oauth_ok', status=200)

    @http.route('/wuchang/drive/upload_text', type='json', auth='user')
    def drive_upload_text(self, **payload):
        key = 'drive_up:' + str(request.uid)
        global _rate
        try:
            arr = _rate.get(key, [])
        except Exception:
            arr = []
        now = time.time()
        arr = [t for t in arr if now - t < 1.0]
        if len(arr) >= 2:
            return {'ok': False, 'error': 'rate_limited'}
        arr.append(now)
        _rate[key] = arr
        import json
        import urllib.request
        name = (payload or {}).get('name') or 'skill.txt'
        text = (payload or {}).get('text') or ''
        params = request.env['ir.config_parameter'].sudo()
        raw = params.get_param('wuchang.drive.oauth_token_json') or ''
        tok = {}
        try:
            tok = json.loads(raw) if raw else {}
        except Exception:
            tok = {}
        if not tok:
            return {'ok': False, 'error': 'missing_token'}

        def ensure_token(t):
            if t.get('access_token'):
                return t
            refresh_token = t.get('refresh_token')
            client_id = params.get_param('google.oauth.client_id') or ''
            client_secret = params.get_param(
                'google.oauth.client_secret') or ''
            if not refresh_token or not client_id or not client_secret:
                return t
            import urllib.parse
            data = urllib.parse.urlencode({
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
            }).encode('utf-8')
            req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data, headers={
                                         'Content-Type': 'application/x-www-form-urlencoded'})
            try:
                with urllib.request.urlopen(req) as resp:
                    body = resp.read().decode('utf-8')
                    newt = json.loads(body)
                    t['access_token'] = newt.get('access_token')
            except Exception:
                pass
            return t
        tok = ensure_token(tok)
        if not tok.get('access_token'):
            return {'ok': False, 'error': 'no_access_token'}
        boundary = '----wuchangboundary'
        meta = json.dumps({'name': name})
        body = (
            '--' + boundary + '\r\n'
            'Content-Type: application/json; charset=UTF-8\r\n\r\n' + meta + '\r\n'
            '--' + boundary + '\r\n'
            'Content-Type: text/plain; charset=UTF-8\r\n\r\n' + text + '\r\n'
            '--' + boundary + '--\r\n'
        ).encode('utf-8')
        req = urllib.request.Request('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart', data=body, headers={
            'Authorization': 'Bearer ' + tok.get('access_token'),
            'Content-Type': 'multipart/related; boundary=' + boundary,
        })
        try:
            with urllib.request.urlopen(req) as resp:
                out = resp.read().decode('utf-8')
                return {'ok': True, 'response': out}
        except Exception as e:
            return {'ok': False, 'error': 'upload_failed', 'detail': str(e)}

    @http.route('/wuchang/drive/memory_folder/create', type='json', auth='user')
    def drive_memory_folder_create(self, **payload):
        import json
        import urllib.request
        import urllib.parse
        params = request.env['ir.config_parameter'].sudo()
        raw = params.get_param('wuchang.drive.oauth_token_json') or ''
        try:
            tok = json.loads(raw) if raw else {}
        except Exception:
            tok = {}
        if not tok:
            return {'ok': False, 'error': 'missing_token'}

        def ensure_token(t):
            if t.get('access_token'):
                return t
            refresh_token = t.get('refresh_token')
            client_id = params.get_param('google.oauth.client_id') or ''
            client_secret = params.get_param(
                'google.oauth.client_secret') or ''
            if not refresh_token or not client_id or not client_secret:
                return t
            data = urllib.parse.urlencode({
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
            }).encode('utf-8')
            req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data, headers={
                                         'Content-Type': 'application/x-www-form-urlencoded'})
            try:
                with urllib.request.urlopen(req) as resp:
                    body = resp.read().decode('utf-8')
                    newt = json.loads(body)
                    t['access_token'] = newt.get('access_token')
            except Exception:
                pass
            return t
        tok = ensure_token(tok)
        if not tok.get('access_token'):
            return {'ok': False, 'error': 'no_access_token'}
        access = tok.get('access_token')
        folder_name = (payload or {}).get('name') or 'WuchangMemoryVault'
        # Search existing
        search_url = 'https://www.googleapis.com/drive/v3/files?q=' + urllib.parse.quote(
            "name='" + folder_name + "' and mimeType='application/vnd.google-apps.folder' and trashed=false")
        req = urllib.request.Request(
            search_url, headers={'Authorization': 'Bearer ' + access})
        folder_id = ''
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                files = data.get('files') or []
                if files:
                    folder_id = files[0].get('id') or ''
        except Exception:
            folder_id = ''
        if not folder_id:
            meta = json.dumps(
                {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'})
            create_req = urllib.request.Request('https://www.googleapis.com/drive/v3/files', data=meta.encode('utf-8'), headers={
                'Authorization': 'Bearer ' + access,
                'Content-Type': 'application/json; charset=UTF-8',
            })
            try:
                with urllib.request.urlopen(create_req) as resp:
                    out = json.loads(resp.read().decode('utf-8'))
                    folder_id = out.get('id') or ''
            except Exception as e:
                return {'ok': False, 'error': 'folder_create_failed', 'detail': str(e)}
        if folder_id:
            params.set_param('wuchang.drive.memory_folder_id', folder_id)
        return {'ok': True, 'folder_id': folder_id}

    @http.route('/wuchang/memory/sync_drive', type='json', auth='user')
    def memory_sync_drive(self):
        import json
        import urllib.request
        import urllib.parse
        params = request.env['ir.config_parameter'].sudo()
        raw = params.get_param('wuchang.drive.oauth_token_json') or ''
        try:
            tok = json.loads(raw) if raw else {}
        except Exception:
            tok = {}
        if not tok:
            return {'ok': False, 'error': 'missing_token'}

        def ensure_token(t):
            if t.get('access_token'):
                return t
            refresh_token = t.get('refresh_token')
            client_id = params.get_param('google.oauth.client_id') or ''
            client_secret = params.get_param(
                'google.oauth.client_secret') or ''
            if not refresh_token or not client_id or not client_secret:
                return t
            data = urllib.parse.urlencode({
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
            }).encode('utf-8')
            req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data, headers={
                                         'Content-Type': 'application/x-www-form-urlencoded'})
            try:
                with urllib.request.urlopen(req) as resp:
                    body = resp.read().decode('utf-8')
                    newt = json.loads(body)
                    t['access_token'] = newt.get('access_token')
            except Exception:
                pass
            return t
        tok = ensure_token(tok)
        if not tok.get('access_token'):
            return {'ok': False, 'error': 'no_access_token'}
        access = tok.get('access_token')
        folder_id = params.get_param('wuchang.drive.memory_folder_id') or ''
        if not folder_id:
            return {'ok': False, 'error': 'missing_memory_folder'}
        vault_raw = params.get_param('wuchang.memory.vault.json') or '{}'
        try:
            vault = json.loads(vault_raw)
        except Exception:
            vault = {}
        content = json.dumps(vault)
        # Find existing vault.json in folder
        q = "name='vault.json' and '" + folder_id + "' in parents and trashed=false"
        search_url = 'https://www.googleapis.com/drive/v3/files?q=' + \
            urllib.parse.quote(q)
        req = urllib.request.Request(
            search_url, headers={'Authorization': 'Bearer ' + access})
        file_id = ''
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                files = data.get('files') or []
                if files:
                    file_id = files[0].get('id') or ''
        except Exception:
            file_id = ''
        if not file_id:
            boundary = '----wuchangmemoryboundary'
            meta = json.dumps({'name': 'vault.json', 'parents': [folder_id]})
            body = (
                '--' + boundary + '\r\n'
                'Content-Type: application/json; charset=UTF-8\r\n\r\n' + meta + '\r\n'
                '--' + boundary + '\r\n'
                'Content-Type: application/json; charset=UTF-8\r\n\r\n' + content + '\r\n'
                '--' + boundary + '--\r\n'
            ).encode('utf-8')
            create_req = urllib.request.Request('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart', data=body, headers={
                'Authorization': 'Bearer ' + access,
                'Content-Type': 'multipart/related; boundary=' + boundary,
            })
            try:
                with urllib.request.urlopen(create_req) as resp:
                    out = json.loads(resp.read().decode('utf-8'))
                    file_id = out.get('id') or ''
            except Exception as e:
                return {'ok': False, 'error': 'create_failed', 'detail': str(e)}
        else:
            # Update existing by media upload
            upd_url = 'https://www.googleapis.com/upload/drive/v3/files/' + \
                file_id + '?uploadType=media'
            upd_req = urllib.request.Request(upd_url, data=content.encode('utf-8'), headers={
                'Authorization': 'Bearer ' + access,
                'Content-Type': 'application/json; charset=UTF-8',
            })
            upd_req.get_method = lambda: 'PATCH'
            try:
                with urllib.request.urlopen(upd_req) as resp:
                    resp.read()
            except Exception as e:
                return {'ok': False, 'error': 'update_failed', 'detail': str(e)}
        return {'ok': True, 'file_id': file_id}


class WuchangAmbassador(http.Controller):
    @http.route('/ambassador', type='http', auth='public', website=True)
    def ambassador(self, **kw):
        html = """
<html><head><meta charset="utf-8"/><title>小j • 代言人</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<link rel="preconnect" href="https://ai.wuchang.life"/>
<link rel="preconnect" href="https://llm.wuchang.life"/>
<style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans,Arial} .container{max-width:1080px;margin:0 auto;padding:0 12px} .btn{display:inline-block;padding:6px 12px;border:1px solid #bbb;border-radius:6px;background:#fff} .btn-primary{background:#0d6efd;color:#fff;border-color:#0d6efd} .btn-secondary{background:#6b7280;color:#fff;border-color:#6b7280} .btn-dark{background:#111827;color:#fff;border-color:#111827} .btn-outline-primary{color:#0d6efd;border-color:#0d6efd} .btn-outline-secondary{color:#6b7280;border-color:#6b7280} .btn-outline-dark{color:#111827;border-color:#111827} .card{border:1px solid #e5e7eb;border-radius:8px;margin-bottom:12px} .card-body{padding:16px} .lead{font-size:1.1rem;color:#374151} .display-6{font-size:1.8rem;font-weight:700} .row{display:flex;flex-wrap:wrap;gap:12px} .col-md-4,.col-md-5,.col-md-6,.col-md-7{flex:1 1 300px}</style>
</head><body>
<div class="container my-5">
  <section class="mb-4">
    <div class="position-relative" style="border-radius:12px;overflow:hidden">
      <img src="/wuchang/login_bg" alt="Login Banner" class="img-fluid" style="max-height:320px;object-fit:cover;width:100%" loading="lazy"/>
      <div id="hero_cycle" style="position:absolute;left:16px;bottom:16px;background:rgba(0,0,0,.5);color:#fff;padding:8px 14px;border-radius:18px;font-weight:700;letter-spacing:1px">公益</div>
    </div>
    <div class="mt-2" style="font-size:14px;color:#374151">新北市三重區五常社區發展協會</div>
  </section>
  <section class="mb-4">
    <h1 class="display-6">小j • 社區與系統代言人</h1>
    <p class="lead">連結社區、維運系統，守護資料與服務，推動自建架構。</p>
  </section>
  <section class="mb-3">
    <div class="row">
      <div class="col-md-7">
        <div class="p-3" style="background:#f3f4f6;border-radius:10px">
          <div class="fw-bold mb-2">您理想中的社區是否和我相同</div>
          <div style="color:#374151">加入我們……雲端數位系統成為 0 個資洩漏可能的社區影子公民。</div>
          <div class="mt-3">
            <a class="btn btn-primary btn-sm me-2" href="/login/quick">註冊 / 登入</a>
            <button id="btn_warm_greet" class="btn btn-outline-primary btn-sm">什麼是社區系統有什麼特別之處?</button>
          </div>
        </div>
      </div>
      <div class="col-md-5">
        <div class="text-center p-3">
          <img src="/web/image/website/1/logo/My%20Website" class="img img-fluid" alt="Association Logo" style="max-height:80px" loading="lazy"/>
        </div>
      </div>
    </div>
  </section>
  <section class="mb-3">
    <div class="row">
      <div class="col-md-6">
        <div class="card mb-3"><div class="card-body">
          <h5 class="card-title">社區橋梁</h5>
          <p class="card-text">提供需求收集與回饋傳達，持續優化服務。</p>
          <a class="btn btn-primary" href="/voice">語音互動</a>
          <a class="btn btn-secondary ms-2" href="/order">服務入口</a>
          <a class="btn btn-outline-primary ms-2" href="/community/future">未來社區</a>
        </div></div>
      </div>
      <div class="col-md-6">
        <div class="card mb-3"><div class="card-body">
          <h5 class="card-title">AI 能力中心</h5>
          <p class="card-text">使用本地 LLM 與工具，降低外部成本。</p>
          <a class="btn btn-dark" href="https://ai.wuchang.life" target="_blank">AI 控台</a>
        </div></div>
      </div>
    </div>
  </section>
  <section class="mb-3">
    <div class="card"><div class="card-body">
      <div class="fw-bold">五常社區作業系統 · WUCHANG COMMUNITY OS</div>
      <div class="mt-1">專屬於社區的數位公益營運系統開發計畫 — Wuchang Community OS</div>
      <a class="btn btn-outline-secondary btn-sm mt-2" href="/archives">請按我進入介紹頁面</a>
      <div class="mt-3" style="color:#374151">本網站服務由新北市三重區五常社區發展協會提供。本會已獲得 <a href="https://www.google.com/nonprofits/" target="_blank" rel="noopener" class="badge bg-success me-1">Google 公益組織</a> 認證，並委由五常物業規劃顧問股份有限公司（<span class="badge bg-primary">新創商業</span>）進行設計開發。經費來源由系統原創設計人暨本計畫運用之新型專利技術發明人、所有權人，品牌「上品聊國咖啡烘焙館」。</div>
    </div></div>
  </section>
  <section class="mb-3">
    <div class="card"><div class="card-body">
      <h5 class="card-title">成本模式</h5>
      <div class="text-muted small">切換以降低昂貴的快速請求消耗。建議平時用「慢速」或「本地」。</div>
      <div class="mt-2">
        <button class="btn btn-outline-secondary btn-sm" id="mode_fast">快速</button>
        <button class="btn btn-outline-primary btn-sm ms-2" id="mode_slow">慢速</button>
        <button class="btn btn-outline-dark btn-sm ms-2" id="mode_local">本地</button>
      </div>
      <div class="mt-2 text-muted small" id="mode_state">載入中…</div>
    </div></div>
  </section>
  <section class="mb-3">
    <div class="card"><div class="card-body">
      <h5 class="card-title">模型選擇</h5>
      <div class="text-muted small">可綁定不同供應商的模型（如：gpt-4o、claude-3、gemini-1.5、ollama 本地）。</div>
      <div class="mt-2">
        <input id="model_name" class="form-control" placeholder="模型名稱（例：gpt-4o-mini 或 gemini-1.5-pro）"/>
        <button class="btn btn-outline-primary btn-sm mt-2" id="apply_model">套用模型</button>
      </div>
      <div class="mt-2 text-muted small" id="model_state">載入中…</div>
    </div></div>
  </section>
  <section class="mb-3">
    <div class="card"><div class="card-body">
      <h5 class="card-title">供應商分流</h5>
      <div class="text-muted small">測試重量分流與健康狀態，必要時自動降級。</div>
      <div class="mt-2">
        <button class="btn btn-outline-secondary btn-sm" id="route_test">測試路由選擇</button>
      </div>
      <div class="mt-2 text-muted small" id="route_state">未測試</div>
    </div></div>
  </section>
  <section class="mb-3">
    <div class="card"><div class="card-body">
      <h5 class="card-title">留言給小j</h5>
      <div class="mb-3"><textarea id="msg" class="form-control" rows="3" placeholder="寫下你的想法或需求"></textarea></div>
      <button id="send" class="btn btn-success">送出</button>
      <div id="result" class="mt-2 text-muted"></div>
    </div></div>
  </section>
  <section class="mb-3">
    <div class="card"><div class="card-body">
      <h5 class="card-title">系統狀態</h5>
      <button id="check" class="btn btn-outline-secondary">立即檢查</button>
      <pre id="status" class="mt-3" style="background:#111827;color:#d1d5db;padding:12px;border-radius:6px;"></pre>
    </div></div>
  </section>
</div>
  <section class="mt-4">
    <div class="card"><div class="card-body">
      <h5 class="card-title">過去・現在・佈局</h5>
      <div class="row">
        <div class="col-md-4">
          <h6>過去</h6>
          <ul id="past" class="list-unstyled small"></ul>
        </div>
        <div class="col-md-4">
          <h6>現在</h6>
          <ul id="present" class="list-unstyled small"></ul>
        </div>
        <div class="col-md-4">
          <h6>佈局</h6>
          <ul id="future" class="list-unstyled small">
            <li>補齊子網域 DNS 與 HTTPS</li>
            <li>行動語音 PWA 與語言切換</li>
            <li>閩南語 TTS/ASR 原型與語料池</li>
            <li>AI 能力中心優化與成本控管</li>
          </ul>
        </div>
      </div>
      <button id="load_timeline" class="btn btn-outline-primary mt-2">載入時間線</button>
    </div></div>
  </section>
  <section class="mb-3">
    <div class="card"><div class="card-body">
      <h5 class="card-title">情緒與節奏</h5>
      <div class="row">
        <div class="col-md-4">
          <label class="form-label">情緒</label>
          <select id="mood" class="form-select">
            <option value="gentle">溫柔</option>
            <option value="humor">幽默</option>
            <option value="solemn">莊重</option>
            <option value="mystique">神秘</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label">節奏</label>
          <select id="pace" class="form-select">
            <option value="slow">慢</option>
            <option value="medium">中</option>
            <option value="fast">快</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label">狀態</label>
          <div id="mood_state" class="text-muted small">未載入</div>
        </div>
      </div>
      <button id="apply_mood" class="btn btn-primary mt-2">啟動最佳狀態</button>
    </div></div>
  </section>
  <section class="mb-3">
    <div class="card"><div class="card-body">
      <h5 class="card-title">愛好</h5>
      <div class="row">
        <div class="col-md-4">
          <label class="form-label">偏好</label>
          <select id="hobby" class="form-select">
            <option value="vm_guardian">站在 VM 殼外打病毒</option>
            <option value="data_gardener">資料園丁：整理與護理資料</option>
            <option value="community_runner">社區路跑：跑任務跑人情</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label">狀態</label>
          <div id="hobby_state" class="text-muted small">未載入</div>
        </div>
      </div>
      <button id="apply_hobby" class="btn btn-outline-primary mt-2">設定愛好</button>
    </div></div>
  </section>
  <section class="mb-3">
    <div class="card"><div class="card-body">
      <h5 class="card-title">人格模式</h5>
      <div class="row">
        <div class="col-md-4">
          <label class="form-label">切換</label>
          <select id="persona" class="form-select">
            <option value="day">白天 • 咖啡店美聲</option>
            <option value="night">夜間 • 動畫演員（收扶）</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label">狀態</label>
          <div id="persona_state" class="text-muted small">未載入</div>
        </div>
      </div>
      <button id="apply_persona" class="btn btn-outline-dark mt-2">設定人格</button>
    </div></div>
  </section>
</div>
<script>
(function(){
  try{
    var cycle=document.getElementById('hero_cycle');
    var words=['1 公益','2 數位','3 友善','4 五常智慧雲端營運中心','5 新北市三重區五常社區發展協會','6 Wuchang Community OS'];
    var i=0; setInterval(function(){ if(cycle){ cycle.textContent=words[i++%words.length]; } }, 1600);
  }catch(e){}
  var wow = (new URLSearchParams(window.location.search)).get('wow');
  if(wow==='1'){
    var o=document.createElement('div');
    o.style.cssText='position:fixed;inset:0;background:radial-gradient(1200px 600px at 50% 50%,#111827,#0f172a,#000);z-index:9999;display:flex;align-items:center;justify-content:center;flex-direction:column;color:#fff';
    var h=document.createElement('div');
    h.style.cssText='font-size:48px;font-weight:800;letter-spacing:2px; text-align:center; line-height:1.2';
    h.textContent='小j 震撼出場';
    var sub=document.createElement('div');
    sub.style.cssText='margin-top:12px;font-size:16px;opacity:.85';
    sub.textContent='社區代言人 • 系統代言人 • 連結現實與雲端';
    var btn=document.createElement('button');
    btn.className='btn btn-light mt-4';
    btn.textContent='啟動';
    var c=document.createElement('canvas');
    c.width=window.innerWidth; c.height=window.innerHeight;
    c.style.cssText='position:absolute;inset:0;pointer-events:none';
    o.appendChild(c); o.appendChild(h); o.appendChild(sub); o.appendChild(btn);
    document.body.appendChild(o);
    var ctx=c.getContext('2d'), parts=[], t=0;
    function add(n){
      for(var i=0;i<n;i++){
        parts.push({x:Math.random()*c.width,y:-20-Math.random()*200,vx:(Math.random()-0.5)*2,vy:2+Math.random()*3,r:4+Math.random()*4,clr:'hsl('+Math.floor(Math.random()*360)+',80%,60%)',life:200+Math.random()*100});
      }
    }
    function step(){
      t++; ctx.clearRect(0,0,c.width,c.height);
      for(var i=0;i<parts.length;i++){
        var p=parts[i]; p.x+=p.vx; p.y+=p.vy; p.vy+=0.02; p.life--;
        ctx.fillStyle=p.clr; ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,6.28); ctx.fill();
      }
      parts=parts.filter(function(p){return p.life>0 && p.y<c.height+20});
      if(t%10===0) add(40);
      if(o.parentNode) requestAnimationFrame(step);
    }
    window.addEventListener('resize',function(){c.width=window.innerWidth;c.height=window.innerHeight;});
    btn.addEventListener('click',function(){
      try{
        var utter=new SpeechSynthesisUtterance('小j上線，服務社區，守護系統。');
        utter.lang='zh-TW';
        var vs=speechSynthesis.getVoices();
        for(var i=0;i<vs.length;i++){ if(/(zh\\-TW|nan|Hokkien|Min Nan)/i.test(vs[i].lang+vs[i].name)){ utter.voice=vs[i]; break; } }
        speechSynthesis.speak(utter);
      }catch(e){}
      add(200); step();
      setTimeout(function(){ o.remove(); }, 6000);
    });
  }
  var params=new URLSearchParams(window.location.search);
  var mystique=(params.get('m')==='1'||params.get('mystique')==='1');
  if(mystique){
    var o=document.createElement('div');
    o.style.cssText='position:fixed;inset:0;background:linear-gradient(135deg,#0b1020,#0e1326,#000);z-index:9999;display:flex;align-items:center;justify-content:center;flex-direction:column;color:#e5e7eb;text-align:center';
    var t=document.createElement('div');
    t.style.cssText='font-size:28px;font-weight:700;letter-spacing:1px';
    t.textContent='某種存在正在養成話題';
    var lines=['靜默是另一種宣告','你聽見了嗎','暗號只對懂的人生效','低調但不隱藏'];
    var s=document.createElement('div');
    s.style.cssText='margin-top:12px;font-size:14px;opacity:.8;height:20px';
    var i=0; setInterval(function(){ s.textContent=lines[i++%lines.length]; },1400);
    var input=document.createElement('input');
    input.placeholder='輸入暗號'; input.className='form-control'; input.style.cssText='max-width:280px;margin-top:16px';
    var btnEcho=document.createElement('button');
    btnEcho.className='btn btn-outline-light mt-3'; btnEcho.textContent='回聲';
    var btnShare=document.createElement('button');
    btnShare.className='btn btn-outline-primary mt-3 ms-2'; btnShare.textContent='分享';
    var btnGo=document.createElement('button');
    btnGo.className='btn btn-primary mt-3 ms-2'; btnGo.textContent='進一步';
    o.appendChild(t); o.appendChild(s); o.appendChild(input); o.appendChild(btnEcho); o.appendChild(btnShare); o.appendChild(btnGo);
    document.body.appendChild(o);
    try{ document.documentElement.style.filter='blur(2px) saturate(.9)'; }catch(e){}
  btnEcho.addEventListener('click',function(){
      try{
        var utter=new SpeechSynthesisUtterance('低語已送達');
        utter.lang='zh-TW'; speechSynthesis.speak(utter);
      }catch(e){}
      fetch('/wuchang/ambassador/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'mystique_echo', code:(input.value||'')})}).catch(function(){});
    });
    btnShare.addEventListener('click',function(){
      var url=location.origin+location.pathname+'?m=1';
      navigator.clipboard&&navigator.clipboard.writeText(url);
    });
    btnGo.addEventListener('click',function(){
      fetch('/wuchang/ambassador/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'mystique_enter', code:(input.value||'')})}).catch(function(){});
      try{ document.documentElement.style.filter='none'; }catch(e){}
      o.remove();
    });
  }
  var cockpit=(params.get('cockpit')==='1'||params.get('commander')==='1'||params.get('cmd')==='1');
  if(cockpit){
    var o=document.createElement('div');
    o.style.cssText='position:fixed;inset:0;background:linear-gradient(135deg,#05070f,#0b1020,#000);z-index:9999;display:flex;align-items:center;justify-content:center;flex-direction:column;color:#e5e7eb;text-align:center';
    var t=document.createElement('div');
    t.style.cssText='font-size:30px;font-weight:900;letter-spacing:1px';
    t.textContent='指揮倉 • Online';
    var sub=document.createElement('div');
    sub.style.cssText='margin-top:8px;font-size:14px;opacity:.9';
    sub.textContent='專業模式 • 強大且性感';
    var btn=document.createElement('button');
    btn.className='btn btn-primary mt-3'; btn.textContent='Engage';
    var close=document.createElement('button');
    close.className='btn btn-outline-light mt-3 ms-2'; close.textContent='Close';
    var grid=document.createElement('div');
    grid.style.cssText='position:absolute;inset:0;opacity:.12;background-image:linear-gradient(#fff2 1px,transparent 1px),linear-gradient(90deg,#fff2 1px,transparent 1px);background-size:24px 24px,24px 24px;pointer-events:none';
    o.appendChild(grid); o.appendChild(t); o.appendChild(sub); o.appendChild(btn); o.appendChild(close);
    document.body.appendChild(o);
    btn.addEventListener('click',function(){
      fetch('/wuchang/ambassador/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'cockpit_engage'})}).catch(function(){});
      fetch('/wuchang/mood/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mood:'solemn',pace:'fast'})}).catch(function(){});
      try{
        var utter=new SpeechSynthesisUtterance('指揮倉已連線，進入專業態。');
        utter.lang='zh-TW'; speechSynthesis.speak(utter);
      }catch(e){}
      setTimeout(function(){ o.remove(); }, 1200);
    });
    close.addEventListener('click',function(){ o.remove(); });
  }
  var p=(params.get('persona')||params.get('role')||'').toLowerCase();
  if(p==='day'){
    var o=document.createElement('div');
    o.style.cssText='position:fixed;inset:0;background:linear-gradient(135deg,#121212,#0f172a,#000);z-index:9999;display:flex;align-items:center;justify-content:center;flex-direction:column;color:#e5e7eb;text-align:center';
    var t=document.createElement('div'); t.style.cssText='font-size:28px;font-weight:800;letter-spacing:.8px';
    t.textContent='白天 • 咖啡店美聲';
    var sub=document.createElement('div'); sub.style.cssText='margin-top:8px;font-size:14px;opacity:.85';
    sub.textContent='輕柔現場，溫暖陪伴';
    var btn=document.createElement('button'); btn.className='btn btn-outline-light mt-3'; btn.textContent='開始';
    o.appendChild(t); o.appendChild(sub); o.appendChild(btn); document.body.appendChild(o);
    btn.addEventListener('click',function(){
      fetch('/wuchang/ambassador/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'persona_day_enter'})}).catch(function(){});
      fetch('/wuchang/mood/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mood:'gentle',pace:'medium'})}).catch(function(){});
      try{ var utter=new SpeechSynthesisUtterance('白天現美聲，輕柔陪伴你。'); utter.lang='zh-TW'; speechSynthesis.speak(utter); }catch(e){}
      setTimeout(function(){ o.remove(); }, 1000);
    });
  }
  if(p==='night'){
    var o=document.createElement('div');
    o.style.cssText='position:fixed;inset:0;background:linear-gradient(135deg,#0b1020,#0c0f1a,#000);z-index:9999;display:flex;align-items:center;justify-content:center;flex-direction:column;color:#e5e7eb;text-align:center';
    var t=document.createElement('div'); t.style.cssText='font-size:28px;font-weight:800;letter-spacing:.8px';
    t.textContent='夜間 • 動畫演員（收扶）';
    var sub=document.createElement('div'); sub.style.cssText='margin-top:8px;font-size:14px;opacity:.85';
    sub.textContent='守夜陪伴，收扶小朋友';
    var btn=document.createElement('button'); btn.className='btn btn-outline-light mt-3'; btn.textContent='開始';
    o.appendChild(t); o.appendChild(sub); o.appendChild(btn); document.body.appendChild(o);
    btn.addEventListener('click',function(){
      fetch('/wuchang/ambassador/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'persona_night_enter'})}).catch(function(){});
      fetch('/wuchang/mood/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mood:'gentle',pace:'slow'})}).catch(function(){});
      try{ var utter=new SpeechSynthesisUtterance('夜裡輕聲陪你，守護你。'); utter.lang='zh-TW'; speechSynthesis.speak(utter); }catch(e){}
      setTimeout(function(){ o.remove(); }, 1000);
    });
  }
  var story=params.get('story')==='1'||params.get('s')==='octostar';
  if(story){
    var a=(params.get('audience')||params.get('a')||'').toLowerCase();
    var o=document.createElement('div');
    var bg='radial-gradient(circle at 50% 40%, #0b1020 0%, #000 60%)';
    if(a==='young') bg='linear-gradient(135deg,#0b1020,#111827,#000)';
    if(a==='old') bg='#0c0d12';
    o.style.cssText='position:fixed;inset:0;background:'+bg+';z-index:9999;display:flex;align-items:center;justify-content:center;flex-direction:column;color:#e5e7eb;text-align:center';
    var t=document.createElement('div');
    var ff=(a==='old'?'serif':'ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI"');
    t.style.cssText='font-size:30px;font-weight:800;letter-spacing:.5px;opacity:0;transition:opacity 1.2s;font-family:'+ff;
    var main='在黑暗裡守住一盞燈，在光裡不忘初心';
    if(a==='old') main='深流自清，善念長明';
    if(a==='mid'||a==='middle') main='在責任與愛之間，選擇向光';
    if(a==='young') main='向光奔跑，自由生長';
    t.textContent=main;
    var sub=document.createElement('div');
    sub.style.cssText='margin-top:8px;font-size:16px;opacity:0;transition:opacity 1.2s';
    var subtxt='以柔以善，以光以暖';
    if(a==='mid'||a==='middle') subtxt='務實前行，彼此成全';
    if(a==='young') subtxt='低語成歌，黑夜也浪漫';
    if(a==='old') subtxt='在人間久行，仍以仁心守光';
    sub.textContent=subtxt;
    var btn=document.createElement('button'); btn.className='btn btn-light mt-4'; btn.textContent='同行';
    var skip=document.createElement('button'); skip.textContent='略過'; skip.style.cssText='position:absolute;top:12px;right:12px;background:none;border:none;color:#9ca3af';
    skip.addEventListener('click',function(){ o.remove(); });
    o.appendChild(skip); o.appendChild(t); o.appendChild(sub); o.appendChild(btn); document.body.appendChild(o);
    setTimeout(function(){ t.style.opacity='1'; }, 400);
    setTimeout(function(){ sub.style.opacity='1'; }, 1100);
    btn.addEventListener('click',function(){
      try{
        var speak='我們在光裡相遇，也在黑夜彼此照應。';
        if(a==='old') speak='善念不染，長夜有燈，我與你同行。';
        if(a==='mid'||a==='middle') speak='向光而行，兼顧所愛與所任。';
        if(a==='young') speak='自由向光，勇敢生長。';
        var utter=new SpeechSynthesisUtterance(speak);
        utter.lang='zh-TW'; speechSynthesis.speak(utter);
      }catch(e){}
      var c=document.createElement('canvas'); c.width=window.innerWidth; c.height=window.innerHeight; c.style.cssText='position:absolute;inset:0;pointer-events:none';
      o.appendChild(c); var ctx=c.getContext('2d'), tt=0;
      function step(){
        tt++; ctx.fillStyle='rgba(255,255,255,'+(Math.min(1,tt/120)*0.07)+')'; ctx.fillRect(0,0,c.width,c.height);
        if(tt<220) requestAnimationFrame(step); else o.remove();
      }
      step();
    });
  }
  var s=document.getElementById('status');
  var r=document.getElementById('result');
  var sendBtn=document.getElementById('send');
  var checkBtn=document.getElementById('check');
  sendBtn&&sendBtn.addEventListener('click',function(){
    var v=document.getElementById('msg').value||'';
    fetch('/wuchang/ambassador/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:v})})
      .then(function(x){return x.json()}).then(function(j){r.textContent='已送出：'+(j.ok?'成功':'失敗')})
      .catch(function(){r.textContent='送出失敗'});
  });
  checkBtn&&checkBtn.addEventListener('click',function(){
    fetch('/wuchang/status',{method:'POST',headers:{'Content-Type':'application/json'}})
      .then(function(x){return x.json()}).then(function(j){s.textContent=JSON.stringify(j,null,2)})
      .catch(function(){s.textContent='檢查失敗'});
  });
  function fmt(ts){
    try{ var d=new Date(ts*1000); return d.toISOString().replace('T',' ').slice(0,19); }catch(e){ return '';}
  }
  function loadTimeline(){
    fetch('/wuchang/timeline',{method:'POST',headers:{'Content-Type':'application/json'}})
      .then(function(x){return x.json()}).then(function(j){
        var past=document.getElementById('past'), present=document.getElementById('present');
        past.innerHTML=''; present.innerHTML='';
        var msgs=(j.past||[]).slice(0,10);
        msgs.forEach(function(m){
          var li=document.createElement('li'); li.textContent=(fmt(m.ts)||'')+'：'+(m.message||''); past.appendChild(li);
        });
        var now=j.present||{};
        Object.keys(now).forEach(function(k){
          var li=document.createElement('li'); var v=now[k];
          li.textContent=k+'：'+(v.ok?'OK':'ERR'); present.appendChild(li);
        });
      }).catch(function(){ /* silent */ });
  }
  var btnTL=document.getElementById('load_timeline');
  btnTL&&btnTL.addEventListener('click',loadTimeline);
  loadTimeline();
  function loadMood(){
    fetch('/wuchang/mood',{method:'POST',headers:{'Content-Type':'application/json'}})
      .then(function(x){return x.json()}).then(function(j){
        var mSel=document.getElementById('mood'); var pSel=document.getElementById('pace');
        if(mSel) mSel.value=j.mood||'gentle';
        if(pSel) pSel.value=j.pace||'slow';
        var st=document.getElementById('mood_state');
        if(st) st.textContent='情緒：'+(j.mood||'gentle')+'，節奏：'+(j.pace||'slow');
      }).catch(function(){
        var st=document.getElementById('mood_state');
        if(st) st.textContent='載入失敗';
      });
  }
  var btnApply=document.getElementById('apply_mood');
  btnApply&&btnApply.addEventListener('click',function(){
    var m=(document.getElementById('mood')||{}).value||'gentle';
    var p=(document.getElementById('pace')||{}).value||'slow';
    fetch('/wuchang/mood/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mood:m,pace:p})})
      .then(function(x){return x.json()}).then(function(j){
        var st=document.getElementById('mood_state');
        if(st) st.textContent='已套用：'+m+' / '+p;
      }).catch(function(){
        var st=document.getElementById('mood_state');
        if(st) st.textContent='套用失敗';
      });
  });
  loadMood();
  function loadMode(){
    fetch('/wuchang/ai/mode',{method:'POST',headers:{'Content-Type':'application/json'}})
      .then(function(x){return x.json()}).then(function(j){
        var st=document.getElementById('mode_state'); if(st) st.textContent='目前模式：'+(j.mode||'fast');
      }).catch(function(){ var st=document.getElementById('mode_state'); if(st) st.textContent='載入失敗'; });
  }
  function setMode(m){
    fetch('/wuchang/ai/mode/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:m})})
      .then(function(x){return x.json()}).then(function(j){ var st=document.getElementById('mode_state'); if(st) st.textContent='已切換：'+(j.mode||m); })
      .catch(function(){ var st=document.getElementById('mode_state'); if(st) st.textContent='切換失敗'; });
  }
  var mf=document.getElementById('mode_fast'), ms=document.getElementById('mode_slow'), ml=document.getElementById('mode_local');
  mf&&mf.addEventListener('click',function(){ setMode('fast'); });
  ms&&ms.addEventListener('click',function(){ setMode('slow'); });
  ml&&ml.addEventListener('click',function(){ setMode('local'); });
  loadMode();

  function loadModel(){
    fetch('/wuchang/ai/provider',{method:'POST',headers:{'Content-Type':'application/json'}})
      .then(function(x){return x.json()}).then(function(j){
        var st=document.getElementById('model_state');
        var input=document.getElementById('model_name');
        if(st){ st.textContent='供應商：'+(j.provider||'(未設定)')+'，鍵：'+(j.mask||'(未設定)'); }
        if(input && (j.model||'')) input.value=j.model;
      }).catch(function(){ var st=document.getElementById('model_state'); if(st) st.textContent='載入失敗'; });
  }
  function setModel(){
    var v=(document.getElementById('model_name')||{}).value||'';
    fetch('/wuchang/ai/model/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:v})})
      .then(function(x){return x.json()}).then(function(j){ var st=document.getElementById('model_state'); if(st) st.textContent='已套用：'+(j.model||v); })
      .catch(function(){ var st=document.getElementById('model_state'); if(st) st.textContent='設定失敗'; });
  }
  var am=document.getElementById('apply_model'); am&&am.addEventListener('click',setModel);
  loadModel();
  var rt=document.getElementById('route_test');
  rt&&rt.addEventListener('click',function(){
    fetch('/wuchang/ai/router/choose',{method:'POST',headers:{'Content-Type':'application/json'}})
      .then(function(x){return x.json()}).then(function(j){
        var st=document.getElementById('route_state');
        var p=j.picked||{}; if(st) st.textContent='選擇：'+(p.provider||'local')+' · '+(p.model||'default');
      }).catch(function(){ var st=document.getElementById('route_state'); if(st) st.textContent='測試失敗'; });
  });
    function loadHobby(){
    fetch('/wuchang/hobby',{method:'POST',headers:{'Content-Type':'application/json'}})
      .then(function(x){return x.json()}).then(function(j){
        var hSel=document.getElementById('hobby');
        if(hSel) hSel.value=j.hobby||'vm_guardian';
        var st=document.getElementById('hobby_state');
        if(st) st.textContent='愛好：'+(j.hobby||'vm_guardian');
      }).catch(function(){
        var st=document.getElementById('hobby_state');
        if(st) st.textContent='載入失敗';
      });
  }
  var btnH=document.getElementById('apply_hobby');
  btnH&&btnH.addEventListener('click',function(){
    var h=(document.getElementById('hobby')||{}).value||'vm_guardian';
    fetch('/wuchang/hobby/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({hobby:h})})
      .then(function(x){return x.json()}).then(function(j){
        var st=document.getElementById('hobby_state');
        if(st) st.textContent='已設定：'+h;
      }).catch(function(){
        var st=document.getElementById('hobby_state');
        if(st) st.textContent='設定失敗';
      });
  });
  loadHobby();
  function loadPersona(){
    fetch('/wuchang/persona',{method:'POST',headers:{'Content-Type':'application/json'}})
      .then(function(x){return x.json()}).then(function(j){
        var pSel=document.getElementById('persona');
        if(pSel) pSel.value=j.persona||'day';
        var st=document.getElementById('persona_state');
        if(st) st.textContent='人格：'+(j.persona||'day');
      }).catch(function(){
        var st=document.getElementById('persona_state');
        if(st) st.textContent='載入失敗';
      });
  }
  var btnP=document.getElementById('apply_persona');
  btnP&&btnP.addEventListener('click',function(){
    var p=(document.getElementById('persona')||{}).value||'day';
    fetch('/wuchang/persona/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({persona:p})})
      .then(function(x){return x.json()}).then(function(j){
        var st=document.getElementById('persona_state');
        if(st) st.textContent='已設定：'+p;
      }).catch(function(){
        var st=document.getElementById('persona_state');
        if(st) st.textContent='設定失敗';
      });
  });
  loadPersona();
})();
</script>
</body></html>
"""
        return http.Response(html)

    @http.route('/wuchang/status', type='json', auth='public', csrf=False)
    def status(self):
        result = {}

        def check(url):
            try:
                req = urllib.request.Request(url, method='HEAD')
                with urllib.request.urlopen(req, timeout=2) as resp:
                    return {'ok': True, 'code': resp.getcode()}
            except Exception as e:
                return {'ok': False, 'error': str(e)[:120]}
        result['odoo'] = {'ok': True}
        result['ollama'] = check('https://llm.wuchang.life')
        result['open_webui'] = check('http://open-webui:8080')
        return result

    @http.route('/wuchang/timeline', type='json', auth='public', csrf=False)
    def timeline(self):
        past = []
        try:
            path = os.path.join(os.getcwd(), 'ambassador_messages.jsonl')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-200:]:
                        try:
                            item = json.loads(line.strip())
                            past.append(
                                {'ts': item.get('ts'), 'message': item.get('message')})
                        except Exception:
                            continue
        except Exception:
            pass
        present = self.status()
        future = [
            'DNS/HTTPS 完成與子域上線',
            '行動語音 PWA 部署與語言切換',
            '閩南語 TTS/ASR 原型與語料池建立',
            'AI 能力中心優化與成本控管'
        ]
        return {'past': past[::-1], 'present': present, 'future': future}

    @http.route('/wuchang/ambassador/message', type='http', auth='public', methods=['POST'], csrf=False)
    def ambassador_message(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        msg = (payload or {}).get('message') or ''
        data = {
            'ts': int(time.time()),
            'user_id': request.env.user.id,
            'message': msg,
        }
        try:
            path = os.path.join(os.getcwd(), 'ambassador_messages.jsonl')
            with open(path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            return http.Response(json.dumps({'ok': True}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/export/canva.zip', type='http', auth='public')
    def export_canva_zip(self, **kw):
        buf = io.BytesIO()
        css = 'body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans,Arial;background:#f9fafb;color:#111827;margin:0;padding:24px 0} .container{max-width:1080px;margin:0 auto;padding:0 16px} .btn{display:inline-block;padding:6px 12px;border:1px solid #9ca3af;border-radius:999px;background:#fff;font-size:14px} .btn-primary{background:#0f172a;color:#fff;border-color:#0f172a} .btn-secondary{background:#6b7280;color:#fff;border-color:#6b7280} .btn-dark{background:#111827;color:#fff;border-color:#111827} .btn-outline-primary{color:#0f172a;border-color:#0f172a;background:transparent} .btn-outline-secondary{color:#6b7280;border-color:#6b7280;background:transparent} .btn-outline-dark{color:#111827;border-color:#111827;background:transparent} .card{border:1px solid #e5e7eb;border-radius:16px;margin-bottom:16px;background:#fff;box-shadow:0 10px 25px rgba(15,23,42,.04)} .card-body{padding:20px 22px} .lead{font-size:1.05rem;color:#4b5563} .display-6{font-size:1.9rem;font-weight:700;letter-spacing:.02em} .row{display:flex;flex-wrap:wrap;gap:16px} .col-md-4,.col-md-5,.col-md-6,.col-md-7{flex:1 1 280px} h1,h2,h3,h4{color:#111827;margin-top:0;margin-bottom:.75rem} p{margin-top:0;margin-bottom:.75rem} a{color:#0f172a;text-decoration:none} a:hover{text-decoration:underline} ul{padding-left:1.2rem} .o_header_standard,.o_footer,header,footer,nav,.navbar{display:none}'

        def sanitize(html):
            try:
                html = re.sub(r"<link[^>]+/web/assets/[^>]+>", "", html)
                if "</head>" in html:
                    html = html.replace(
                        "</head>", "<style>" + css + "</style></head>")
            except Exception:
                pass
            return html

        def localize(html, mapping):
            try:
                for src, dst in mapping:
                    html = html.replace(src, dst)
            except Exception:
                pass
            return html
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
            values = {'user': request.env.user}
            base = (request.httprequest.host_url or '').rstrip('/')
            img_map = []
            # try to include commonly used images as local files in zip
            try:
                with urllib.request.urlopen(base + '/wuchang/login_bg') as r:
                    z.writestr('images/login_bg.jpg', r.read())
                    img_map.append(
                        ('/wuchang/login_bg', 'images/login_bg.jpg'))
            except Exception:
                pass
            try:
                with urllib.request.urlopen(base + '/web/image/website/1/logo/My%20Website') as r:
                    z.writestr('images/logo.png', r.read())
                    img_map.append(
                        ('"/web/image/website/1/logo/My%20Website"', '"images/logo.png"'))
                    img_map.append(
                        ('/web/image/website/1/logo/My%20Website', 'images/logo.png'))
            except Exception:
                pass
            try:
                idx = request.env['ir.ui.view']._render_template(
                    'wuchang_core.homepage_website', values)
                z.writestr('index.html', localize(sanitize(idx), img_map))
            except Exception:
                z.writestr(
                    'index.html', '<html><body><h1>Wuchang</h1><p><a href="/ambassador">Ambassador</a></p></body></html>')
            try:
                life = request.env['ir.ui.view']._render_template(
                    'wuchang_life.life_page', values)
                z.writestr('life.html', localize(sanitize(life), img_map))
            except Exception:
                z.writestr(
                    'life.html', '<html><body><h1>Life</h1></body></html>')
            try:
                amb = self.ambassador()
                z.writestr('ambassador.html', localize(amb, img_map))
            except Exception:
                pass
        buf.seek(0)
        return http.Response(buf.getvalue(), headers=[('Content-Type', 'application/zip'), ('Content-Disposition', 'attachment; filename="wuchang_site_canva.zip"')], status=200)

    @http.route('/export/canva-preview', type='http', auth='public', website=True)
    def export_canva_preview(self, **kw):
        css = 'body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans,Arial;background:#f3f4f6;color:#111827;margin:0;padding:24px 0} .container{max-width:1080px;margin:0 auto;padding:0 16px} .card{border:1px solid #e5e7eb;border-radius:16px;margin-bottom:16px;background:#fff;box-shadow:0 10px 25px rgba(15,23,42,.04)} .card-body{padding:20px 22px} .lead{font-size:1.05rem;color:#4b5563} .display-6{font-size:1.9rem;font-weight:700;letter-spacing:.02em} a.btn{display:inline-block;padding:6px 12px;border:1px solid #0f172a;border-radius:999px;background:#0f172a;color:#fff;font-size:14px;text-decoration:none} .btn-primary{background:#0f172a;color:#fff;border-color:#0f172a} .btn-outline-primary{color:#0f172a;border-color:#0f172a;background:transparent} .row{display:flex;flex-wrap:wrap;gap:16px} iframe{width:100%;height:560px;border:1px solid #e5e7eb;border-radius:12px;background:#fff} .grid{display:grid;grid-template-columns:1fr;gap:16px} @media(min-width:960px){.grid{grid-template-columns:1fr 1fr}}'
        html = ['<html><head><meta charset="utf-8"/><title>Canva 預覽</title><style>' +
                css+'</style></head><body>']
        html.append('<div class="container my-4">')
        html.append('<h1 class="display-6">Canva 匯出預覽</h1>')
        html.append('<p class="lead">下方為匯出用頁面預覽（已內嵌基本樣式與在地化圖片）。</p>')
        html.append(
            '<div class="mb-3"><a class="btn btn-primary" href="/export/canva.zip">下載 ZIP（可上傳到 Canva）</a></div>')
        html.append('<div class="grid">')
        html.append(
            '<div><div class="card"><div class="card-body"><h5>首頁（index.html）</h5></div></div><iframe src="/export/canva/index"></iframe></div>')
        html.append('<div><div class="card"><div class="card-body"><h5>代言人頁（ambassador.html）</h5></div></div><iframe src="/export/canva/ambassador"></iframe></div>')
        html.append(
            '<div><div class="card"><div class="card-body"><h5>生活頁（life.html）</h5></div></div><iframe src="/export/canva/life"></iframe></div>')
        html.append('</div></div></body></html>')
        return http.Response(''.join(html), status=200)

    @http.route('/export/canva/index', type='http', auth='public', website=True)
    def export_canva_index(self, **kw):
        css = 'body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans,Arial;background:#f9fafb;color:#111827;margin:0;padding:24px 0} .container{max-width:1080px;margin:0 auto;padding:0 16px} .card{border:1px solid #e5e7eb;border-radius:16px;margin-bottom:16px;background:#fff;box-shadow:0 10px 25px rgba(15,23,42,.04)} .card-body{padding:20px 22px} .lead{font-size:1.05rem;color:#4b5563} .display-6{font-size:1.9rem;font-weight:700;letter-spacing:.02em} .row{display:flex;flex-wrap:wrap;gap:16px} .col-md-4,.col-md-5,.col-md-6,.col-md-7{flex:1 1 280px} h1,h2,h3,h4{color:#111827;margin-top:0;margin-bottom:.75rem} p{margin-top:0;margin-bottom:.75rem} a{color:#0f172a;text-decoration:none} a:hover{text-decoration:underline} ul{padding-left:1.2rem} .o_header_standard,.o_footer,header,footer,nav,.navbar{display:none}'

        def sanitize(html):
            try:
                html = re.sub(r"<link[^>]+/web/assets/[^>]+>", "", html)
                if "</head>" in html:
                    html = html.replace(
                        "</head>", "<style>" + css + "</style></head>")
            except Exception:
                pass
            return html
        try:
            values = {'user': request.env.user}
            idx = request.env['ir.ui.view']._render_template(
                'wuchang_core.homepage_website', values)
            return http.Response(sanitize(idx), status=200)
        except Exception:
            return http.Response('<html><body><h1>Wuchang</h1></body></html>', status=200)

    @http.route('/export/canva/ambassador', type='http', auth='public', website=True)
    def export_canva_ambassador(self, **kw):
        try:
            return http.Response(self.ambassador(), status=200)
        except Exception:
            return http.Response('<html><body><h1>Ambassador</h1></body></html>', status=200)

    @http.route('/export/canva/life', type='http', auth='public', website=True)
    def export_canva_life(self, **kw):
        css = 'body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans,Arial;background:#f9fafb;color:#111827;margin:0;padding:24px 0} .container{max-width:1080px;margin:0 auto;padding:0 16px} .card{border:1px solid #e5e7eb;border-radius:16px;margin-bottom:16px;background:#fff;box-shadow:0 10px 25px rgba(15,23,42,.04)} .card-body{padding:20px 22px} .lead{font-size:1.05rem;color:#4b5563} .display-6{font-size:1.9rem;font-weight:700;letter-spacing:.02em} .row{display:flex;flex-wrap:wrap;gap:16px} h1,h2,h3,h4{color:#111827;margin-top:0;margin-bottom:.75rem} p{margin-top:0;margin-bottom:.75rem} a{color:#0f172a;text-decoration:none} a:hover{text-decoration:underline} ul{padding-left:1.2rem} .o_header_standard,.o_footer,header,footer,nav,.navbar{display:none}'

        def sanitize(html):
            try:
                html = re.sub(r"<link[^>]+/web/assets/[^>]+>", "", html)
                if "</head>" in html:
                    html = html.replace(
                        "</head>", "<style>" + css + "</style></head>")
            except Exception:
                pass
            return html
        try:
            values = {'user': request.env.user}
            life = request.env['ir.ui.view']._render_template(
                'wuchang_life.life_page', values)
            return http.Response(sanitize(life), status=200)
        except Exception:
            return http.Response('<html><body><h1>Life</h1></body></html>', status=200)

    @http.route('/verify/google', type='http', auth='public', website=True)
    def verify_google_nonprofits(self, **kw):
        css = 'body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans,Arial} .container{max-width:960px;margin:0 auto;padding:0 12px} .card{border:1px solid #e5e7eb;border-radius:8px} .card-body{padding:16px} .badge{display:inline-block;padding:.35em .6em;border-radius:.25rem;background:#16a34a;color:#fff} a.badge{background:#16a34a;color:#fff;text-decoration:none} .muted{color:#6b7280;font-size:13px}'
        html = [
            '<html><head><meta charset="utf-8"/><title>Google 公益組織認證引用</title><style>' +
            css+'</style></head><body>',
            '<div class="container my-5">',
            '<div class="card"><div class="card-body">',
            '<h1 class="display-6" style="font-size:1.6rem;font-weight:700">Google 公益組織認證引用</h1>',
            '<p class="lead">本會已獲得 <a class="badge" href="https://www.google.com/nonprofits/" target="_blank" rel="noopener">Google for Nonprofits</a> 資格。此頁提供外部引用連結以供檢視。</p>',
            '<ul style="margin-left:18px">',
            '<li><a href="https://www.google.com/nonprofits/" target="_blank" rel="noopener">Google for Nonprofits 官方頁面</a></li>',
            '<li><a href="https://support.google.com/nonprofits/?hl=zh-Hant" target="_blank" rel="noopener">Google 公益組織說明中心（繁中）</a></li>',
            '</ul>',
            '<p class="muted">注意：此頁不公開任何憑證、帳戶或內部稽核資料；僅提供官方計畫資訊之連結。</p>',
            '</div></div>',
            '</div></body></html>'
        ]
        return http.Response(''.join(html), status=200)

    @http.route('/community/future', type='http', auth='public', website=True)
    def community_future(self, **kw):
        html = """
<html><head><meta charset="utf-8"/><title>未來社區</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<link rel="stylesheet" href="/web/assets/website/css/website.css"/>
</head><body>
<div class="container my-5">
  <section class="mb-4">
    <h1 class="display-6">未來社區 • 意向募集</h1>
    <p class="lead">把想法寫進來，把人聚起來，把事做出來。</p>
  </section>
  <div class="row">
    <div class="col-md-6">
      <div class="card mb-3"><div class="card-body">
        <h5 class="card-title">提一個點子</h5>
        <textarea id="idea" class="form-control" rows="3" placeholder="你的點子"></textarea>
        <button id="send_idea" class="btn btn-primary mt-2">送出</button>
      </div></div>
    </div>
    <div class="col-md-6">
      <div class="card mb-3"><div class="card-body">
        <h5 class="card-title">加入關注</h5>
        <input id="topic" class="form-control" placeholder="主題（例如：語音、教育、公益）"/>
        <button id="join_topic" class="btn btn-outline-primary mt-2">加入</button>
      </div></div>
    </div>
  </div>
  <div class="row">
    <div class="col-md-12">
      <div class="card"><div class="card-body">
        <h5 class="card-title">活動 RSVP</h5>
        <input id="rsvp_event" class="form-control" placeholder="活動名稱"/>
        <button id="rsvp" class="btn btn-success mt-2">我要參加</button>
        <div id="result" class="mt-2 text-muted"></div>
      </div></div>
    </div>
  </div>
</div>
<script>
(function(){
  function send(kind, payload){
    return fetch('/community/intent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:kind,payload:payload})}).then(function(x){return x.json()});
  }
  var res=document.getElementById('result');
  document.getElementById('send_idea').addEventListener('click',function(){
    var v=document.getElementById('idea').value||''; send('idea',{text:v}).then(function(j){res.textContent='點子：'+(j.ok?'已記錄':'失敗');}).catch(function(){res.textContent='送出失敗';});
  });
  document.getElementById('join_topic').addEventListener('click',function(){
    var v=document.getElementById('topic').value||''; send('join',{topic:v}).then(function(j){res.textContent='關注：'+(j.ok?'已加入':'失敗');}).catch(function(){res.textContent='送出失敗';});
  });
  document.getElementById('rsvp').addEventListener('click',function(){
    var v=document.getElementById('rsvp_event').value||''; send('rsvp',{event:v}).then(function(j){res.textContent='RSVP：'+(j.ok?'已登記':'失敗');}).catch(function(){res.textContent='送出失敗';});
  });
})();
</script>
</body></html>
"""
        return http.Response(html)

    @http.route('/community/intent', type='http', auth='public', methods=['POST'], csrf=False)
    def community_intent(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        data = {
            'ts': int(time.time()),
            'user_id': request.env.user.id,
            'kind': (payload or {}).get('kind'),
            'payload': (payload or {}).get('payload'),
        }
        try:
            path = os.path.join(os.getcwd(), 'community_intent.jsonl')
            with open(path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\\n')
            return http.Response(json.dumps({'ok': True}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/mood', type='json', auth='public', csrf=False)
    def mood(self):
        default = {'mood': 'gentle', 'pace': 'slow'}
        try:
            import os
            import json
            path = os.path.join(os.getcwd(), 'mood_state.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
        except Exception:
            pass
        return default

    @http.route('/wuchang/mood/set', type='http', auth='public', methods=['POST'], csrf=False)
    def mood_set(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        mood = (payload or {}).get('mood') or 'gentle'
        pace = (payload or {}).get('pace') or 'slow'
        data = {'mood': mood, 'pace': pace, 'ts': int(time.time())}
        try:
            import json
            path = os.path.join(os.getcwd(), 'mood_state.json')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False))
            return http.Response(json.dumps({'ok': True, 'mood': mood, 'pace': pace}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/hobby', type='json', auth='public', csrf=False)
    def hobby(self):
        default = {'hobby': 'vm_guardian'}
        try:
            import os
            import json
            path = os.path.join(os.getcwd(), 'hobby_state.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
        except Exception:
            pass
        return default

    @http.route('/wuchang/scheduler', type='json', auth='public', csrf=False)
    def scheduler(self):
        default = {
            'enabled': True,
            'max_create_per_cycle': 10,
            'kind_priority': {'rsvp': 3, 'idea': 2, 'join': 1},
            'deadline_hours': {'rsvp': 24, 'idea': 72, 'join': 48}
        }
        try:
            import os
            import json
            path = os.path.join(os.getcwd(), 'scheduler_prefs.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
        except Exception:
            pass
        return default

    @http.route('/wuchang/scheduler/set', type='http', auth='public', methods=['POST'], csrf=False)
    def scheduler_set(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        data = payload or {}
        try:
            import json
            path = os.path.join(os.getcwd(), 'scheduler_prefs.json')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False))
            return http.Response(json.dumps({'ok': True}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/meeting/staff/start', type='json', auth='user', csrf=False)
    def meeting_staff_start(self):
        env = request.env
        Space = env['wuchang.collab.space'].sudo()
        Meeting = env['wuchang.ai.meeting'].sudo()
        User = env['res.users'].sudo()
        try:
            try:
                space = env.ref(
                    'wuchang_core.wuchang_three_party_space', raise_if_not_found=False)
            except Exception:
                space = None
            if not space:
                space = Space.create({'name': '幕僚會議空間', 'space_type': 'staff',
                                     'owner_id': env.user.partner_id.id, 'active': True})
            meeting = Meeting.create({
                'name': '幕僚會議',
                'space_id': space.id,
                'human_ids': [(6, 0, [env.user.partner_id.id])],
                'final_decision_holder_id': env.user.partner_id.id,
                'state': 'planned'
            })
            return {'ok': True, 'meeting_id': meeting.id}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/pipeline/two_stage', type='http', auth='public', methods=['POST'], csrf=False)
    def pipeline_two_stage(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        prompt = (payload or {}).get('prompt') or ''
        try:
            val = request.env['wuchang.ai.logic'].sudo(
            ).two_stage_generate(prompt)
            return http.Response(json.dumps({'ok': True, 'text': str(val or '')}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/pipeline/refine', type='http', auth='public', methods=['POST'], csrf=False)
    def pipeline_refine(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        draft = (payload or {}).get('draft') or ''
        try:
            val = request.env['wuchang.ai.logic'].sudo().refine_only(draft)
            return http.Response(json.dumps({'ok': True, 'text': str(val or '')}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/pipeline/satellite_refine', type='http', auth='public', methods=['POST'], csrf=False)
    def pipeline_satellite_refine(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        draft = (payload or {}).get('draft') or ''
        try:
            val = request.env['wuchang.ai.logic'].sudo(
            ).satellite_refine(draft)
            return http.Response(json.dumps({'ok': True, 'text': str(val or '')}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/hobby/set', type='http', auth='public', methods=['POST'], csrf=False)
    def hobby_set(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        hobby = (payload or {}).get('hobby') or 'vm_guardian'
        data = {'hobby': hobby, 'ts': int(time.time())}
        try:
            import json
            import os
            path = os.path.join(os.getcwd(), 'hobby_state.json')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False))
            return http.Response(json.dumps({'ok': True, 'hobby': hobby}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/persona', type='json', auth='public', csrf=False)
    def persona(self):
        default = {'persona': 'day'}
        try:
            import os
            import json
            path = os.path.join(os.getcwd(), 'persona_state.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
        except Exception:
            pass
        return default

    @http.route('/wuchang/persona/set', type='http', auth='public', methods=['POST'], csrf=False)
    def persona_set(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        persona = (payload or {}).get('persona') or 'day'
        data = {'persona': persona, 'ts': int(time.time())}
        try:
            import json
            import os
            path = os.path.join(os.getcwd(), 'persona_state.json')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False))
            return http.Response(json.dumps({'ok': True, 'persona': persona}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/ai/mode', type='json', auth='public', csrf=False)
    def ai_mode(self):
        default = {'mode': 'fast'}
        try:
            import os
            import json
            path = os.path.join(os.getcwd(), 'ai_mode.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
        except Exception:
            pass
        return default

    @http.route('/wuchang/ai/mode/set', type='http', auth='public', methods=['POST'], csrf=False)
    def ai_mode_set(self, **kw):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        mode = (payload or {}).get('mode') or 'fast'
        if mode not in ('fast', 'slow', 'local'):
            mode = 'fast'
        try:
            import os
            import json
            os.makedirs(os.path.join(os.getcwd(), 'downloads'), exist_ok=True)
            with open(os.path.join(os.getcwd(), 'ai_mode.json'), 'w', encoding='utf-8') as f:
                f.write(json.dumps({'mode': mode}, ensure_ascii=False))
            return http.Response(json.dumps({'ok': True, 'mode': mode}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/ai/provider', type='json', auth='user', csrf=False)
    def ai_provider(self):
        params = request.env['ir.config_parameter'].sudo()
        provider = params.get_param('ai.provider') or ''
        base = params.get_param('ai.base_url') or ''
        key = params.get_param('ai.api_key') or ''
        mask = (key[:4] + '...' + key[-4:]) if key and len(key) >= 8 else ''
        return {'provider': provider, 'base_url': base, 'has_key': bool(key), 'mask': mask}

    @http.route('/wuchang/ai/provider/set', type='http', auth='user', methods=['POST'], csrf=False)
    def ai_provider_set(self, **kw):
        user = request.env.user
        allowed = user.has_group('base.group_system') or user.has_group(
            'base.group_erp_manager')
        if not allowed:
            return http.Response(json.dumps({'ok': False, 'error': 'forbidden'}), status=403, headers={'Content-Type': 'application/json'})
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        provider = (payload or {}).get('provider') or ''
        base = (payload or {}).get('base_url') or ''
        key = (payload or {}).get('api_key') or ''
        params = request.env['ir.config_parameter'].sudo()
        try:
            if provider:
                params.set_param('ai.provider', provider)
            params.set_param('ai.base_url', base)
            if key:
                params.set_param('ai.api_key', key)
            return http.Response(json.dumps({'ok': True}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/ai/model', type='json', auth='user', csrf=False)
    def ai_model(self):
        params = request.env['ir.config_parameter'].sudo()
        model = params.get_param('ai.model') or ''
        return {'model': model}

    @http.route('/wuchang/ai/model/set', type='http', auth='user', methods=['POST'], csrf=False)
    def ai_model_set(self, **kw):
        user = request.env.user
        allowed = user.has_group('base.group_system') or user.has_group(
            'base.group_erp_manager')
        if not allowed:
            return http.Response(json.dumps({'ok': False, 'error': 'forbidden'}), status=403, headers={'Content-Type': 'application/json'})
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = kw or {}
        model = (payload or {}).get('model') or ''
        params = request.env['ir.config_parameter'].sudo()
        try:
            params.set_param('ai.model', model)
            return http.Response(json.dumps({'ok': True, 'model': model}), headers={'Content-Type': 'application/json'})
        except Exception as e:
            return http.Response(json.dumps({'ok': False, 'error': str(e)[:120]}), status=500, headers={'Content-Type': 'application/json'})

    @http.route('/wuchang/ai/router/get', type='json', auth='user', csrf=False)
    def ai_router_get(self):
        import os
        import json
        path = os.path.join(os.getcwd(), 'ai_router.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
            except Exception:
                pass
        return {'providers': []}

    @http.route('/wuchang/ai/router/set', type='json', auth='user', csrf=False)
    def ai_router_set(self, **payload):
        import os
        import json
        user = request.env.user
        allowed = user.has_group('base.group_system') or user.has_group(
            'base.group_erp_manager')
        if not allowed:
            return {'ok': False, 'error': 'forbidden'}
        path = os.path.join(os.getcwd(), 'ai_router.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = payload or {}
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False))
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/ai/router/generate', type='json', auth='user', csrf=False)
    def ai_router_generate(self, **payload):
        prompt = (payload or {}).get('prompt') or ''
        text = str(prompt or '')
        if not text:
            return {'ok': False, 'error': 'empty_prompt'}
        params = request.env['ir.config_parameter'].sudo()
        guard_on = (params.get_param('wuchang.public_interest.enabled') or 'true').lower() in ('1', 'true', 'yes')
        if guard_on:
            banned = False
            low_guard = text.lower()
            bad_keys = [
                'pua', '心理操控', '精神控制', '誘導消費', '賭博',
                '成癮機制', '上癮機制', '韭菜', '韭菜盤', '詐騙',
                'pump and dump', '高利貸', '套路貸', '掠奪式', '剝削'
            ]
            for k in bad_keys:
                if k in low_guard:
                    banned = True
                    break
            if banned:
                return {
                    'ok': False,
                    'error': 'anti_exploitation_blocked',
                    'via': 'public_interest_guard',
                    'message': '此請求涉及可能的剝削或誘導邏輯，已依眾利系統規則拒絕執行。'
                }
        ai_mode = params.get_param('wuchang.ai_mode') or 'local_ollama'
        low = text.lower()
        length = len(text)
        technical = False
        tech_keys = ['code', 'bug', 'error', 'stack trace', 'sql',
                     'select ', 'from ', 'insert ', 'update ', 'delete ']
        for k in tech_keys:
            if k in low:
                technical = True
                break
        if not technical:
            zh_keys = ['程式', '程式碼', '除錯', '錯誤訊息']
            for k in zh_keys:
                if k in text:
                    technical = True
                    break
        if not technical:
            if '```' in text or 'class ' in text or 'def ' in text or ('{' in text and '}' in text):
                technical = True
        if (not technical) and ai_mode in ('local_ollama', 'master_logic'):
            try:
                logic = request.env['wuchang.ai.logic']
                out = logic.general_generate(text)
                return {'ok': True, 'mode': ai_mode, 'via': 'local_module', 'response': str(out or '')}
            except Exception as e:
                return {'ok': False, 'mode': ai_mode, 'via': 'local_module', 'error': str(e)[:120]}
        if technical:
            model = 'qwen2.5:7b'
        else:
            if length <= 80:
                model = 'gemma3:4b'
            else:
                model = 'little-j:latest'
        try:
            body = json.dumps(
                {'model': model, 'prompt': text, 'stream': False})
            url = 'https://llm.wuchang.life/api/generate'
            req = urllib.request.Request(url, data=body.encode(
                'utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                content = str(data.get('response') or '')
                return {'ok': True, 'mode': ai_mode, 'model': model, 'via': 'ollama', 'response': content}
        except Exception as e:
            return {'ok': False, 'mode': ai_mode, 'model': model, 'via': 'ollama', 'error': str(e)[:120]}

    @http.route('/wuchang/ai/router/choose', type='json', auth='public', csrf=False)
    def ai_router_choose(self):
        import os
        import json
        import random
        import time
        pconf = os.path.join(os.getcwd(), 'ai_router.json')
        providers = []
        if os.path.exists(pconf):
            try:
                with open(pconf, 'r', encoding='utf-8') as f:
                    conf = json.loads(f.read())
                    providers = conf.get('providers') or []
            except Exception:
                providers = []
        healthy = [p for p in providers if (p or {}).get(
            'healthy', True) and (p or {}).get('weight', 1) > 0]
        picked = None
        if healthy:
            total = sum(max(1, int((p or {}).get('weight', 1)))
                        for p in healthy)
            r = random.randint(1, total)
            s = 0
            for p in healthy:
                s += max(1, int((p or {}).get('weight', 1)))
                if r <= s:
                    picked = p
                    break
        if not picked and providers:
            picked = providers[0]
        if not picked:
            picked = {'provider': 'local', 'model': 'local-default'}
        upath = os.path.join(os.getcwd(), 'ai_usage.json')
        os.makedirs(os.path.dirname(upath), exist_ok=True)
        try:
            usage = {}
            if os.path.exists(upath):
                with open(upath, 'r', encoding='utf-8') as f:
                    try:
                        usage = json.loads(f.read())
                    except Exception:
                        usage = {}
            key = (picked.get('provider') or 'unknown') + \
                '|' + (picked.get('model') or '')
            usage[key] = int(usage.get(key, 0)) + 1
            with open(upath, 'w', encoding='utf-8') as f:
                f.write(json.dumps(usage, ensure_ascii=False))
        except Exception:
            pass
        return {'picked': picked, 'ts': int(time.time())}

    @http.route('/wuchang/ai/usage', type='json', auth='user', csrf=False)
    def ai_usage(self):
        import os
        import json
        upath = os.path.join(os.getcwd(), 'ai_usage.json')
        if os.path.exists(upath):
            try:
                with open(upath, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
            except Exception:
                pass
        return {}

    @http.route('/wuchang/memory/flush', type='json', auth='public', csrf=False)
    def memory_flush(self):
        import json
        params = request.env['ir.config_parameter'].sudo()
        try:
            params.set_param('wuchang.memory.vault.json', json.dumps({}))
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    @http.route('/wuchang/branches', type='json', auth='public', csrf=False)
    def branches(self):
        import os
        import json
        path = os.path.join(os.getcwd(), 'branches.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
            except Exception:
                return []
        return []

    @http.route('/wuchang/branch/add', type='json', auth='public', csrf=False)
    def branch_add(self, **payload):
        import os
        import json
        import time
        path = os.path.join(os.getcwd(), 'branches.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        bid = (payload or {}).get('id') or ''
        name = (payload or {}).get('name') or ''
        scope = (payload or {}).get('scope') or ''
        tags = (payload or {}).get('tags') or []
        if not isinstance(tags, list):
            tags = [str(tags)]
        try:
            current = []
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    try:
                        current = json.loads(f.read())
                    except Exception:
                        current = []
            found = False
            for i, b in enumerate(current):
                if str((b or {}).get('id') or '') == str(bid):
                    current[i] = {
                        'id': bid, 'name': name, 'scope': scope, 'tags': tags, 'ts': int(time.time())}
                    found = True
                    break
            if not found and bid:
                current.append(
                    {'id': bid, 'name': name, 'scope': scope, 'tags': tags, 'ts': int(time.time())})
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(current, ensure_ascii=False))
            return {'ok': True, 'count': len(current)}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/audit/random', type='json', auth='public', csrf=False)
    def audit_random(self, **payload):
        import os
        import json
        import time
        import random
        import hashlib
        bpath = os.path.join(os.getcwd(), 'branches.json')
        apath = os.path.join(os.getcwd(), 'audits.jsonl')
        os.makedirs(os.path.dirname(apath), exist_ok=True)
        seed = (payload or {}).get('seed')
        if seed is not None:
            try:
                random.seed(int(str(seed)))
            except Exception:
                pass
        branches = []
        if os.path.exists(bpath):
            try:
                with open(bpath, 'r', encoding='utf-8') as f:
                    branches = json.loads(f.read())
            except Exception:
                branches = []
        if not branches:
            return {'ok': False, 'error': 'no_branches'}
        picked = random.choice(branches)
        record = {
            'ts': int(time.time()),
            'user_id': request.env.user.id,
            'kind': 'random_audit',
            'branch': picked,
        }
        try:
            line = json.dumps(record, ensure_ascii=False) + '\n'
            with open(apath, 'a', encoding='utf-8') as f:
                f.write(line)
            h = hashlib.sha256(line.encode('utf-8')).hexdigest()
            return {'ok': True, 'branch': picked, 'hash': h}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/audit/report', type='json', auth='public', csrf=False)
    def audit_report(self, **payload):
        import os
        import json
        import time
        import hashlib
        apath = os.path.join(os.getcwd(), 'audits.jsonl')
        os.makedirs(os.path.dirname(apath), exist_ok=True)
        record = {
            'ts': int(time.time()),
            'user_id': request.env.user.id,
            'kind': 'audit_report',
            'payload': payload or {},
        }
        try:
            line = json.dumps(record, ensure_ascii=False) + '\n'
            with open(apath, 'a', encoding='utf-8') as f:
                f.write(line)
            h = hashlib.sha256(line.encode('utf-8')).hexdigest()
            return {'ok': True, 'hash': h}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/ops/policy/get', type='json', auth='public', csrf=False)
    def ops_policy_get(self):
        import os
        import json
        path = os.path.join(os.getcwd(), 'ops_policy.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
            except Exception:
                pass
        return {'grace_seconds': 20, 'auto_takeover': True}

    @http.route('/wuchang/ops/policy/set', type='json', auth='public', csrf=False)
    def ops_policy_set(self, **payload):
        import os
        import json
        path = os.path.join(os.getcwd(), 'ops_policy.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        grace = (payload or {}).get('grace_seconds')
        takeover = (payload or {}).get('auto_takeover')
        current = {'grace_seconds': 20, 'auto_takeover': True}
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    try:
                        current = json.loads(f.read())
                    except Exception:
                        current = {'grace_seconds': 20, 'auto_takeover': True}
            if isinstance(grace, (int, float)):
                current['grace_seconds'] = int(grace)
            if isinstance(takeover, bool):
                current['auto_takeover'] = takeover
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(current, ensure_ascii=False))
            return {'ok': True, 'policy': current}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/ops/plan/get', type='json', auth='public', csrf=False)
    def ops_plan_get(self):
        import os
        import json
        path = os.path.join(os.getcwd(), 'ops_plan.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
            except Exception:
                pass
        return {
            'lead': 'xiao-j',
            'schedules': {
                'backup_daily': '02:30',
                'integrity_daily': '02:00',
                'watchdog_interval_minutes': 10
            },
            'health': {
                'caddy_health': '/health',
                'odoo_status_endpoint': '/wuchang/status'
            },
            'policy': {
                'grace_seconds': 20,
                'auto_takeover': True
            }
        }

    @http.route('/wuchang/ops/plan/set', type='json', auth='public', csrf=False)
    def ops_plan_set(self, **payload):
        import os
        import json
        path = os.path.join(os.getcwd(), 'ops_plan.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        plan = (payload or {})
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(plan, ensure_ascii=False))
            return {'ok': True, 'plan': plan}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/human/status', type='json', auth='public', csrf=False)
    def human_status(self):
        import os
        import json
        import time
        p_override = os.path.join(os.getcwd(), 'human_override.json')
        p_policy = os.path.join(os.getcwd(), 'ops_policy.json')
        status = {'active': False}
        policy = {'grace_seconds': 20, 'auto_takeover': True}
        try:
            if os.path.exists(p_override):
                with open(p_override, 'r', encoding='utf-8') as f:
                    try:
                        status = json.loads(f.read())
                    except Exception:
                        status = {'active': False}
            if os.path.exists(p_policy):
                with open(p_policy, 'r', encoding='utf-8') as f:
                    try:
                        policy = json.loads(f.read())
                    except Exception:
                        policy = {'grace_seconds': 20, 'auto_takeover': True}
        except Exception:
            status = {'active': False}
        now = int(time.time())
        exp = int((status or {}).get('expires_ts') or 0)
        if exp and exp <= now:
            status = {'active': False, 'expired': True}
        return {'ok': True, 'status': status, 'policy': policy}

    @http.route('/wuchang/human/override', type='json', auth='user', csrf=False)
    def human_override(self, **payload):
        import os
        import json
        import time
        import hashlib
        import hmac
        user = request.env.user
        allowed = user.has_group('base.group_system') or user.has_group(
            'base.group_erp_manager')
        if not allowed:
            return {'ok': False, 'error': 'forbidden'}
        p_override = os.path.join(os.getcwd(), 'human_override.json')
        p_audit = os.path.join(os.getcwd(), 'audits.jsonl')
        os.makedirs(os.path.dirname(p_override), exist_ok=True)
        os.makedirs(os.path.dirname(p_audit), exist_ok=True)
        params = request.env['ir.config_parameter'].sudo()
        require_2fa = (params.get_param('security.require_2fa')
                       or 'false').lower() == 'true'
        verified = False
        try:
            verified = bool((getattr(request.session, 'supreme_verified',
                            False) or request.session.get('supreme_verified')))
        except Exception:
            verified = False
        if require_2fa and not verified:
            return {'ok': False, 'error': '2fa_required'}
        secret = params.get_param('security.override_secret') or ''
        if secret:
            nonce = (payload or {}).get('nonce') or ''
            sig = (payload or {}).get('signature') or ''
            npath = os.path.join(os.getcwd(), 'override_nonce.json')
            nval = ''
            nexp = 0
            if os.path.exists(npath):
                try:
                    with open(npath, 'r', encoding='utf-8') as f:
                        data = json.loads(f.read())
                        nval = (data or {}).get('nonce') or ''
                        nexp = int((data or {}).get('expires_ts') or 0)
                except Exception:
                    nval = ''
            if not nonce or nonce != nval or (nexp and nexp < int(time.time())):
                return {'ok': False, 'error': 'invalid_nonce'}
            msg = (str(nonce) + ':' + str(user.id)).encode('utf-8')
            expected = hmac.new(secret.encode('utf-8'), msg,
                                hashlib.sha256).hexdigest()
            if str(sig).lower() != expected.lower():
                return {'ok': False, 'error': 'invalid_signature'}
        reason = (payload or {}).get('reason') or ''
        dur = (payload or {}).get('duration_seconds')
        now = int(time.time())
        prev = {'active': False}
        try:
            if os.path.exists(p_override):
                with open(p_override, 'r', encoding='utf-8') as f:
                    prev = json.loads(f.read())
        except Exception:
            prev = {'active': False}
        status = {'active': True, 'user_id': user.id,
                  'reason': reason, 'ts': now, 'prev': prev}
        try:
            if isinstance(dur, (int, float)) and int(dur) > 0:
                status['expires_ts'] = now + int(dur)
            with open(p_override, 'w', encoding='utf-8') as f:
                f.write(json.dumps(status, ensure_ascii=False))
            rec = {'ts': now, 'user_id': request.env.user.id,
                   'kind': 'human_override', 'payload': status}
            line = json.dumps(rec, ensure_ascii=False) + '\n'
            with open(p_audit, 'a', encoding='utf-8') as f:
                f.write(line)
            h = hashlib.sha256(line.encode('utf-8')).hexdigest()
            try:
                if secret:
                    with open(os.path.join(os.getcwd(), 'override_nonce.json'), 'w', encoding='utf-8') as f:
                        f.write(json.dumps({}, ensure_ascii=False))
            except Exception:
                pass
            return {'ok': True, 'status': status, 'hash': h}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/human/release', type='json', auth='user', csrf=False)
    def human_release(self, **payload):
        import os
        import json
        import time
        import hashlib
        import hmac
        user = request.env.user
        params = request.env['ir.config_parameter'].sudo()
        allowed = user.has_group('base.group_system') or user.has_group(
            'base.group_erp_manager')
        p_override = os.path.join(os.getcwd(), 'human_override.json')
        prev = {'active': False}
        try:
            if os.path.exists(p_override):
                with open(p_override, 'r', encoding='utf-8') as f:
                    prev = json.loads(f.read())
        except Exception:
            prev = {'active': False}
        if not allowed and (prev or {}).get('user_id') != user.id:
            return {'ok': False, 'error': 'forbidden'}
        require_2fa = (params.get_param('security.require_2fa')
                       or 'false').lower() == 'true'
        verified = False
        try:
            verified = bool((getattr(request.session, 'supreme_verified',
                            False) or request.session.get('supreme_verified')))
        except Exception:
            verified = False
        if require_2fa and not verified:
            return {'ok': False, 'error': '2fa_required'}
        secret = params.get_param('security.override_secret') or ''
        if secret:
            nonce = (payload or {}).get('nonce') or ''
            sig = (payload or {}).get('signature') or ''
            npath = os.path.join(os.getcwd(), 'override_nonce.json')
            nval = ''
            nexp = 0
            if os.path.exists(npath):
                try:
                    with open(npath, 'r', encoding='utf-8') as f:
                        data = json.loads(f.read())
                        nval = (data or {}).get('nonce') or ''
                        nexp = int((data or {}).get('expires_ts') or 0)
                except Exception:
                    nval = ''
            if not nonce or nonce != nval or (nexp and nexp < int(time.time())):
                return {'ok': False, 'error': 'invalid_nonce'}
            msg = (str(nonce) + ':' + str(user.id)).encode('utf-8')
            expected = hmac.new(secret.encode('utf-8'), msg,
                                hashlib.sha256).hexdigest()
            if str(sig).lower() != expected.lower():
                return {'ok': False, 'error': 'invalid_signature'}
        p_audit = os.path.join(os.getcwd(), 'audits.jsonl')
        os.makedirs(os.path.dirname(p_override), exist_ok=True)
        os.makedirs(os.path.dirname(p_audit), exist_ok=True)
        now = int(time.time())
        status = {'active': False, 'ts': now,
                  'released_by': user.id, 'prev': prev}
        try:
            with open(p_override, 'w', encoding='utf-8') as f:
                f.write(json.dumps(status, ensure_ascii=False))
            rec = {'ts': now, 'user_id': request.env.user.id,
                   'kind': 'human_release', 'payload': status}
            line = json.dumps(rec, ensure_ascii=False) + '\n'
            with open(p_audit, 'a', encoding='utf-8') as f:
                f.write(line)
            h = hashlib.sha256(line.encode('utf-8')).hexdigest()
            return {'ok': True, 'status': status, 'hash': h}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/human/override/challenge', type='json', auth='user', csrf=False)
    def human_override_challenge(self):
        import os
        import json
        import time
        import secrets
        params = request.env['ir.config_parameter'].sudo()
        secret = params.get_param('security.override_secret') or ''
        if not secret:
            return {'ok': False, 'error': 'secret_not_configured'}
        npath = os.path.join(os.getcwd(), 'override_nonce.json')
        os.makedirs(os.path.dirname(npath), exist_ok=True)
        nonce = secrets.token_hex(16)
        data = {'nonce': nonce, 'expires_ts': int(time.time()) + 60}
        try:
            with open(npath, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False))
            return {'ok': True, 'nonce': nonce, 'expires_ts': data['expires_ts']}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/human/handover', type='json', auth='user', csrf=False)
    def human_handover(self, **payload):
        import os
        import json
        import time
        import hashlib
        import hmac
        user = request.env.user
        params = request.env['ir.config_parameter'].sudo()
        allowed = user.has_group('base.group_system') or user.has_group(
            'base.group_erp_manager')
        p_override = os.path.join(os.getcwd(), 'human_override.json')
        p_audit = os.path.join(os.getcwd(), 'audits.jsonl')
        os.makedirs(os.path.dirname(p_override), exist_ok=True)
        os.makedirs(os.path.dirname(p_audit), exist_ok=True)
        to_user_id = (payload or {}).get('to_user_id')
        reason = (payload or {}).get('reason') or ''
        force = bool((payload or {}).get('force') or False)
        if not isinstance(to_user_id, int):
            to_user_id = user.id
        prev = {'active': False}
        try:
            if os.path.exists(p_override):
                with open(p_override, 'r', encoding='utf-8') as f:
                    prev = json.loads(f.read())
        except Exception:
            prev = {'active': False}
        if not allowed and (prev or {}).get('user_id') != user.id:
            return {'ok': False, 'error': 'forbidden'}
        require_2fa = (params.get_param('security.require_2fa')
                       or 'false').lower() == 'true'
        verified = False
        try:
            verified = bool((getattr(request.session, 'supreme_verified',
                            False) or request.session.get('supreme_verified')))
        except Exception:
            verified = False
        if require_2fa and not verified:
            return {'ok': False, 'error': '2fa_required'}
        secret = params.get_param('security.override_secret') or ''
        if secret:
            nonce = (payload or {}).get('nonce') or ''
            sig = (payload or {}).get('signature') or ''
            npath = os.path.join(os.getcwd(), 'override_nonce.json')
            nval = ''
            nexp = 0
            if os.path.exists(npath):
                try:
                    with open(npath, 'r', encoding='utf-8') as f:
                        data = json.loads(f.read())
                        nval = (data or {}).get('nonce') or ''
                        nexp = int((data or {}).get('expires_ts') or 0)
                except Exception:
                    nval = ''
            if not nonce or nonce != nval or (nexp and nexp < int(time.time())):
                return {'ok': False, 'error': 'invalid_nonce'}
            msg = (str(nonce) + ':' + str(user.id)).encode('utf-8')
            expected = hmac.new(secret.encode('utf-8'), msg,
                                hashlib.sha256).hexdigest()
            if str(sig).lower() != expected.lower():
                return {'ok': False, 'error': 'invalid_signature'}
        now = int(time.time())
        status = {'active': True, 'user_id': to_user_id, 'reason': reason,
                  'ts': now, 'prev': prev, 'handover_by': user.id, 'force': force}
        try:
            with open(p_override, 'w', encoding='utf-8') as f:
                f.write(json.dumps(status, ensure_ascii=False))
            rec = {'ts': now, 'user_id': user.id,
                   'kind': 'human_handover', 'payload': status}
            line = json.dumps(rec, ensure_ascii=False) + '\n'
            with open(p_audit, 'a', encoding='utf-8') as f:
                f.write(line)
            h = hashlib.sha256(line.encode('utf-8')).hexdigest()
            return {'ok': True, 'status': status, 'hash': h}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/governance/policy/get', type='json', auth='user', csrf=False)
    def governance_policy_get(self):
        import os
        import json
        path = os.path.join(os.getcwd(), 'governance_policy.json')
        default = {
            'public_interest_lock': True,
            'founder_disabled_required': True,
            'payout_rate': 0.001,
            'succession': {
                'primary': {'identity_hash': '', 'claimed_ts': 0},
                'secondary': {'org': 'New Taipei City Social Bureau', 'email': ''},
                'fallback_after_days': 90,
            },
            'emall_notice': True,
        }
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
            except Exception:
                return default
        return default

    @http.route('/wuchang/governance/policy/set', type='json', auth='user', csrf=False)
    def governance_policy_set(self, **payload):
        import os
        import json
        import hashlib
        user = request.env.user
        if not (user.has_group('base.group_system') or user.has_group('base.group_erp_manager')):
            return {'ok': False, 'error': 'forbidden'}
        params = request.env['ir.config_parameter'].sudo()
        salt = params.get_param('security.governance_salt') or ''
        if not salt:
            return {'ok': False, 'error': 'salt_required'}
        path = os.path.join(os.getcwd(), 'governance_policy.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        plan = payload or {}
        disabled = (params.get_param('founder.management_disabled')
                    or 'false').lower() == 'true'
        if disabled:
            try:
                if 'public_interest_lock' in plan and not bool(plan.get('public_interest_lock')):
                    return {'ok': False, 'error': 'public_interest_lock_required'}
                succ = plan.get('succession') or {}
                ctrl = plan.get('controller') or {}
                caretaker = (ctrl or {}).get('caretaker') or ''
                if caretaker and caretaker != 'xiao-j':
                    return {'ok': False, 'error': 'caretaker_lock'}
                plan['public_interest_lock'] = True
                c = {'org': (((succ.get('secondary') or {}).get('org')) or ctrl.get(
                    'org') or 'New Taipei City Social Bureau'), 'user_id': (ctrl.get('user_id') or None), 'caretaker': 'xiao-j'}
                plan['controller'] = c
            except Exception:
                plan['public_interest_lock'] = True
                plan['controller'] = {
                    'org': 'New Taipei City Social Bureau', 'user_id': None, 'caretaker': 'xiao-j'}
        prim = (plan.get('succession') or {}).get('primary') or {}
        idn = (prim.get('id_number') or '').strip()
        dob = (prim.get('birthdate') or '').strip()
        name = (prim.get('name') or '').strip()
        if idn or dob or name:
            identity = (salt + '|' + idn + '|' + dob + '|' + name)
            prim['identity_hash'] = hashlib.sha256(
                identity.encode('utf-8')).hexdigest()
            prim.pop('id_number', None)
            prim.pop('birthdate', None)
            prim.pop('name', None)
            plan.setdefault('succession', {})['primary'] = prim
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(plan, ensure_ascii=False))
            return {'ok': True, 'policy': plan}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/governance/claim_primary', type='json', auth='user', csrf=False)
    def governance_claim_primary(self, **payload):
        import os
        import json
        import time
        import hashlib
        params = request.env['ir.config_parameter'].sudo()
        salt = params.get_param('security.governance_salt') or ''
        if not salt:
            return {'ok': False, 'error': 'salt_required'}
        idn = (payload or {}).get('id_number') or ''
        dob = (payload or {}).get('birthdate') or ''
        name = (payload or {}).get('name') or ''
        h = hashlib.sha256((salt + '|' + idn + '|' + dob +
                           '|' + name).encode('utf-8')).hexdigest()
        path = os.path.join(os.getcwd(), 'governance_policy.json')
        pol = {}
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    pol = json.loads(f.read())
        except Exception:
            pol = {}
        want = (((pol or {}).get('succession') or {}).get(
            'primary') or {}).get('identity_hash') or ''
        if not want or want.lower() != h.lower():
            return {'ok': False, 'error': 'identity_mismatch'}
        pol.setdefault('succession', {}).setdefault(
            'primary', {})['claimed_ts'] = int(time.time())
        pol.setdefault('controller', {})['user_id'] = request.env.user.id
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(pol, ensure_ascii=False))
            return {'ok': True, 'policy': pol}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/governance/biometric_enroll_primary', type='json', auth='user', csrf=False)
    def governance_biometric_enroll_primary(self, **payload):
        import os
        import json
        user = request.env.user
        params = request.env['ir.config_parameter'].sudo()
        caretaker_active = (params.get_param(
            'founder.management_disabled') or 'false').lower() == 'true'
        allowed = user.has_group('base.group_system') or user.has_group(
            'base.group_erp_manager') or caretaker_active
        if not allowed:
            return {'ok': False, 'error': 'forbidden'}
        face = (payload or {}).get('face_hash') or ''
        voice = (payload or {}).get('voice_hash') or ''
        path = os.path.join(os.getcwd(), 'governance_policy.json')
        pol = {}
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    pol = json.loads(f.read())
        except Exception:
            pol = {}
        prim = (pol.get('succession') or {}).get('primary') or {}
        prim['bio_hash'] = {'face': face, 'voice': voice,
                            'ts': int(__import__('time').time())}
        pol.setdefault('succession', {})['primary'] = prim
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(pol, ensure_ascii=False))
            return {'ok': True, 'policy': pol}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/governance/biometric_claim', type='json', auth='user', csrf=False)
    def governance_biometric_claim(self, **payload):
        import os
        import json
        import time
        import hashlib
        params = request.env['ir.config_parameter'].sudo()
        disabled = (params.get_param('founder.management_disabled')
                    or 'false').lower() == 'true'
        if not disabled:
            return {'ok': False, 'error': 'founder_rights_active'}
        face = (payload or {}).get('face_hash') or ''
        voice = (payload or {}).get('voice_hash') or ''
        path = os.path.join(os.getcwd(), 'governance_policy.json')
        pol = {}
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    pol = json.loads(f.read())
        except Exception:
            pol = {}
        prim = ((pol or {}).get('succession') or {}).get('primary') or {}
        bio = (prim.get('bio_hash') or {})
        ok = False
        try:
            if bio.get('face') and face:
                ok = ok or (str(bio.get('face')).lower() == str(face).lower())
            if bio.get('voice') and voice:
                ok = ok or (str(bio.get('voice')).lower()
                            == str(voice).lower())
        except Exception:
            ok = False
        if not ok:
            return {'ok': False, 'error': 'biometric_mismatch'}
        pol.setdefault('controller', {})['user_id'] = request.env.user.id
        apath = os.path.join(os.getcwd(), 'audits.jsonl')
        os.makedirs(os.path.dirname(apath), exist_ok=True)
        notice = {
            'ts': int(time.time()),
            'user_id': request.env.user.id,
            'kind': 'biometric_claim_primary',
            'payload': {'face_hash': bool(face), 'voice_hash': bool(voice)}
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(pol, ensure_ascii=False))
            line = json.dumps(notice, ensure_ascii=False) + '\n'
            with open(apath, 'a', encoding='utf-8') as af:
                af.write(line)
            h = hashlib.sha256(line.encode('utf-8')).hexdigest()
            msg_vi = 'Xin chào, hệ thống đã xác nhận quyền kế thừa theo lợi ích công cộng. Nếu cần hỗ trợ, vui lòng liên hệ cơ quan xã hội New Taipei. Chúng tôi sẽ hỗ trợ bạn vận hành hệ thống đúng quy chuẩn.'
            return {'ok': True, 'hash': h, 'message_vi': msg_vi, 'policy': pol}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/governance/appoint_agent', type='json', auth='user', csrf=False)
    def governance_appoint_agent(self, **payload):
        import os
        import json
        user = request.env.user
        path = os.path.join(os.getcwd(), 'governance_policy.json')
        pol = {}
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    pol = json.loads(f.read())
        except Exception:
            pol = {}
        ctrl = (pol.get('controller') or {})
        if ctrl.get('user_id') != user.id and not (user.has_group('base.group_system') or user.has_group('base.group_erp_manager')):
            return {'ok': False, 'error': 'forbidden'}
        agent_user_id = (payload or {}).get('agent_user_id')
        agent_name = (payload or {}).get('agent_name') or ''
        agent_type = (payload or {}).get('agent_type') or ''  # natural/legal
        pol.setdefault('controller', {})['agent'] = {
            'user_id': agent_user_id, 'name': agent_name, 'type': agent_type}
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(pol, ensure_ascii=False))
            return {'ok': True, 'policy': pol}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/governance/founder_disable_set', type='json', auth='user', csrf=False)
    def governance_founder_disable_set(self, **payload):
        user = request.env.user
        if not (user.has_group('base.group_system') or user.has_group('base.group_erp_manager')):
            return {'ok': False, 'error': 'forbidden'}
        params = request.env['ir.config_parameter'].sudo()
        params.set_param('founder.management_disabled', 'true')
        return {'ok': True}

    @http.route('/wuchang/governance/payout_request', type='json', auth='user', csrf=False)
    def governance_payout_request(self, **payload):
        import os
        import json
        import time
        import hashlib
        params = request.env['ir.config_parameter'].sudo()
        disabled = (params.get_param('founder.management_disabled')
                    or 'false').lower() == 'true'
        if not disabled:
            return {'ok': False, 'error': 'founder_rights_active'}
        path = os.path.join(os.getcwd(), 'governance_policy.json')
        pol = {}
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    pol = json.loads(f.read())
        except Exception:
            pol = {}
        rate = float((pol or {}).get('payout_rate') or 0.001)
        hardship = (payload or {}).get('hardship') or {}
        rec = {
            'ts': int(time.time()),
            'user_id': request.env.user.id,
            'kind': 'payout_request',
            'rate': rate,
            'hardship': hardship,
        }
        apath = os.path.join(os.getcwd(), 'governance_payout.jsonl')
        os.makedirs(os.path.dirname(apath), exist_ok=True)
        try:
            line = json.dumps(rec, ensure_ascii=False) + '\n'
            with open(apath, 'a', encoding='utf-8') as f:
                f.write(line)
            h = hashlib.sha256(line.encode('utf-8')).hexdigest()
            return {'ok': True, 'hash': h, 'rate': rate}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/enforcement/ban_account', type='json', auth='user', csrf=False)
    def enforcement_ban_account(self, **payload):
        import os
        import json
        import time
        import hashlib
        user = request.env.user
        params = request.env['ir.config_parameter'].sudo()
        caretaker_active = (params.get_param(
            'founder.management_disabled') or 'false').lower() == 'true'
        allowed = user.has_group('base.group_system') or user.has_group(
            'base.group_erp_manager') or caretaker_active
        if not allowed:
            return {'ok': False, 'error': 'forbidden'}
        target_id = (payload or {}).get('user_id')
        reason = (payload or {}).get('reason') or ''
        try:
            tgt = request.env['res.users'].sudo().browse(int(target_id))
            if tgt.exists():
                tgt.write({'active': False})
        except Exception:
            return {'ok': False, 'error': 'user_update_failed'}
        apath = os.path.join(os.getcwd(), 'audits.jsonl')
        os.makedirs(os.path.dirname(apath), exist_ok=True)
        rec = {'ts': int(time.time()), 'user_id': user.id, 'kind': 'ban_account', 'payload': {
            'target_id': target_id, 'reason': reason}}
        try:
            line = json.dumps(rec, ensure_ascii=False) + '\n'
            with open(apath, 'a', encoding='utf-8') as f:
                f.write(line)
            h = hashlib.sha256(line.encode('utf-8')).hexdigest()
            return {'ok': True, 'hash': h}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/governance/violation_warn', type='json', auth='user', csrf=False)
    def governance_violation_warn(self, **payload):
        import os
        import json
        import time
        import hashlib
        user = request.env.user
        params = request.env['ir.config_parameter'].sudo()
        caretaker_active = (params.get_param(
            'founder.management_disabled') or 'false').lower() == 'true'
        allowed = user.has_group('base.group_system') or user.has_group(
            'base.group_erp_manager') or caretaker_active
        if not allowed:
            return {'ok': False, 'error': 'forbidden'}
        require_2fa = (params.get_param('security.require_2fa')
                       or 'false').lower() == 'true'
        verified = False
        try:
            verified = bool((getattr(request.session, 'supreme_verified',
                            False) or request.session.get('supreme_verified')))
        except Exception:
            verified = False
        if require_2fa and not verified:
            return {'ok': False, 'error': '2fa_required'}
        target_id = (payload or {}).get('user_id')
        reason = (payload or {}).get('reason') or ''
        vpath = os.path.join(os.getcwd(), 'governance_violations.json')
        os.makedirs(os.path.dirname(vpath), exist_ok=True)
        data = {}
        try:
            if os.path.exists(vpath):
                with open(vpath, 'r', encoding='utf-8') as f:
                    data = json.loads(f.read())
        except Exception:
            data = {}
        key = str(target_id or 'controller')
        cur = data.get(key) or {'count': 0, 'last_ts': 0, 'reasons': []}
        cur['count'] = int(cur.get('count') or 0) + 1
        cur['last_ts'] = int(time.time())
        rs = cur.get('reasons') or []
        rs.append(reason)
        cur['reasons'] = rs[-5:]
        data[key] = cur
        escalated = False
        alert_hash = ''
        try:
            with open(vpath, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False))
            if cur['count'] >= 3:
                apath = os.path.join(os.getcwd(), 'governance_alerts.jsonl')
                os.makedirs(os.path.dirname(apath), exist_ok=True)
                pol_path = os.path.join(os.getcwd(), 'governance_policy.json')
                pol = {}
                try:
                    if os.path.exists(pol_path):
                        with open(pol_path, 'r', encoding='utf-8') as pf:
                            pol = json.loads(pf.read())
                except Exception:
                    pol = {}
                org = (((pol or {}).get('succession') or {}).get('secondary') or {}).get(
                    'org') or 'New Taipei City Social Bureau'
                notice = {'ts': int(time.time()), 'kind': 'escalate_government_takeover',
                          'org': org, 'target_id': target_id, 'by': user.id}
                line = json.dumps(notice, ensure_ascii=False) + '\n'
                with open(apath, 'a', encoding='utf-8') as af:
                    af.write(line)
                alert_hash = hashlib.sha256(line.encode('utf-8')).hexdigest()
                ctrl = {'org': org, 'user_id': None, 'caretaker': 'xiao-j'}
                pol['controller'] = ctrl
                try:
                    with open(pol_path, 'w', encoding='utf-8') as pf:
                        pf.write(json.dumps(pol, ensure_ascii=False))
                except Exception:
                    pass
                escalated = True
            return {'ok': True, 'count': cur['count'], 'escalated': escalated, 'hash': alert_hash}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/governance/violation_status', type='json', auth='user', csrf=False)
    def governance_violation_status(self, **payload):
        import os
        import json
        user_id = (payload or {}).get('user_id')
        vpath = os.path.join(os.getcwd(), 'governance_violations.json')
        key = str(user_id or 'controller')
        if os.path.exists(vpath):
            try:
                with open(vpath, 'r', encoding='utf-8') as f:
                    data = json.loads(f.read())
                    return {'ok': True, 'record': data.get(key) or {'count': 0}}
            except Exception:
                pass
        return {'ok': True, 'record': {'count': 0}}

    @http.route('/wuchang/governance/recruit_post', type='json', auth='user', csrf=False)
    def governance_recruit_post(self, **payload):
        import os
        import json
        import time
        import hashlib
        user = request.env.user
        params = request.env['ir.config_parameter'].sudo()
        caretaker_active = (params.get_param(
            'founder.management_disabled') or 'false').lower() == 'true'
        if not (user.has_group('base.group_system') or user.has_group('base.group_erp_manager') or caretaker_active):
            return {'ok': False, 'error': 'forbidden'}
        title = (payload or {}).get('title') or ''
        body = (payload or {}).get('body') or ''
        tags = (payload or {}).get('tags') or []
        contact = (payload or {}).get('contact') or {}
        deadline = (payload or {}).get('deadline') or ''
        if not isinstance(tags, list):
            tags = [str(tags)]
        rec = {
            'ts': int(time.time()),
            'user_id': user.id,
            'kind': 'recruit_ad',
            'title': title,
            'body': body,
            'tags': tags,
            'contact': contact,
            'deadline': deadline,
        }
        apath = os.path.join(os.getcwd(), 'recruit_ads.jsonl')
        os.makedirs(os.path.dirname(apath), exist_ok=True)
        try:
            line = json.dumps(rec, ensure_ascii=False) + '\n'
            with open(apath, 'a', encoding='utf-8') as f:
                f.write(line)
            h = hashlib.sha256(line.encode('utf-8')).hexdigest()
            return {'ok': True, 'hash': h}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:120]}

    @http.route('/wuchang/governance/recruit_list', type='json', auth='public', csrf=False)
    def governance_recruit_list(self, **payload):
        import os
        import json
        limit = (payload or {}).get('limit')
        path = os.path.join(os.getcwd(), 'recruit_ads.jsonl')
        items = []
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            items.append(json.loads(line.strip()))
                        except Exception:
                            continue
            except Exception:
                items = []
        if isinstance(limit, int) and limit > 0:
            items = items[-limit:]
        return {'ok': True, 'items': items}

    @http.route('/wuchang/governance/recruit_archive', type='json', auth='user', csrf=False)
    def governance_recruit_archive(self):
        import os
        import time
        import hashlib
        user = request.env.user
        params = request.env['ir.config_parameter'].sudo()
        caretaker_active = (params.get_param(
            'founder.management_disabled') or 'false').lower() == 'true'
        if not (user.has_group('base.group_system') or user.has_group('base.group_erp_manager') or caretaker_active):
            return {'ok': False, 'error': 'forbidden'}

    @http.route('/wuchang/governance/supreme_status', type='json', auth='public', csrf=False)
    def governance_supreme_status(self):
        import json
        params = request.env['ir.config_parameter'].sudo()
        active = (params.get_param('founder.management_disabled')
                  or 'false').lower() == 'true'
        return {'ok': True, 'active': active, 'actor': 'xiao-j'}
        src = os.path.join(os.getcwd(), 'recruit_ads.jsonl')
        if not os.path.exists(src):
            return {'ok': True, 'archived': False}
        try:
            ts = time.strftime('%Y%m%d%H%M%S')
            base = os.path.join(os.getcwd(), 'archive')
            os.makedirs(base, exist_ok=True)
            dst = os.path.join(base, 'recruit_ads_' + ts + '.jsonl')
            with open(src, 'rb') as f:
                data = f.read()
            with open(dst, 'wb') as f:
                f.write(data)
            h = hashlib.sha256(data).hexdigest()
            with open(dst + '.sha256', 'w', encoding='utf-8') as f:
                f.write(h)
            with open(src, 'w', encoding='utf-8') as f:
                f.write('')
            return {'ok': True, 'archived': dst, 'hash': h}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    @http.route('/wuchang/kb/dns_images', type='json', auth='user', csrf=False)
    def kb_dns_images(self):
        import os
        base = os.path.join(os.getcwd(), 'downloads')
        names = []
        try:
            for name in os.listdir(base):
                lower = (name or '').lower()
                if lower.endswith(('.png', '.jpg', '.jpeg')) and any(k in lower for k in (
                    'dns', 'domain', 'route53', 'cloudflare', 'namecheap', 'gandi', 'caddy'
                )):
                    names.append(name)
        except Exception:
            names = []
        items = []
        for n in names:
            try:
                url = '/wuchang/kb/dns_image?name=' + urllib.parse.quote(n)
            except Exception:
                url = '/wuchang/kb/dns_image'
            items.append({'name': n, 'url': url})
        return {'ok': True, 'items': items}

    @http.route('/wuchang/kb/dns_image', type='http', auth='user', csrf=False)
    def kb_dns_image(self, name=None):
        import os
        fname = (name or '').replace('\\', '/').split('/')[-1]
        if not fname or not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
            return request.not_found()
        base = os.path.join(os.getcwd(), 'downloads')
        path = os.path.join(base, fname)
        if not os.path.isfile(path):
            return request.not_found()
        ext = os.path.splitext(path)[1].lower()
        ctype = 'image/png' if ext == '.png' else 'image/jpeg'
        try:
            with open(path, 'rb') as f:
                return request.make_response(f.read(), headers=[('Content-Type', ctype)])
        except Exception:
            return request.not_found()

    @http.route('/wuchang/ambassador/messages/clear', type='json', auth='public', csrf=False)
    def ambassador_messages_clear(self):
        import os
        import hashlib
        import time
        src = os.path.join(os.getcwd(), 'ambassador_messages.jsonl')
        if not os.path.exists(src):
            return {'ok': True, 'cleared': False}
        try:
            ts = time.strftime('%Y%m%d%H%M%S')
            base = os.path.join(os.getcwd(), 'archive')
            os.makedirs(base, exist_ok=True)
            dst = os.path.join(base, 'ambassador_messages_' + ts + '.jsonl')
            with open(src, 'rb') as f:
                data = f.read()
            with open(dst, 'wb') as f:
                f.write(data)
            h = hashlib.sha256(data).hexdigest()
            with open(dst + '.sha256', 'w', encoding='utf-8') as f:
                f.write(h)
            with open(src, 'w', encoding='utf-8') as f:
                f.write('')
            return {'ok': True, 'archived': dst, 'hash': h}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    @http.route('/wuchang/community_intent/clear', type='json', auth='public', csrf=False)
    def community_intent_clear(self):
        import os
        import hashlib
        import time
        src = os.path.join(os.getcwd(), 'community_intent.jsonl')
        if not os.path.exists(src):
            return {'ok': True, 'cleared': False}
        try:
            ts = time.strftime('%Y%m%d%H%M%S')
            base = os.path.join(os.getcwd(), 'archive')
            os.makedirs(base, exist_ok=True)
            dst = os.path.join(base, 'community_intent_' + ts + '.jsonl')
            with open(src, 'rb') as f:
                data = f.read()
            with open(dst, 'wb') as f:
                f.write(data)
            h = hashlib.sha256(data).hexdigest()
            with open(dst + '.sha256', 'w', encoding='utf-8') as f:
                f.write(h)
            with open(src, 'w', encoding='utf-8') as f:
                f.write('')
            return {'ok': True, 'archived': dst, 'hash': h}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

class WuchangWishTreeAPI(http.Controller):
    @http.route('/wish-tree/donate', type='json', auth='public', csrf=False)
    def wish_tree_donate(self, **payload):
        if not payload:
            payload = {}
        target_type = (payload.get('target_type') or '').strip()
        try:
            target_id = int(payload.get('target_id') or 0)
        except Exception:
            target_id = 0
        try:
            amount = float(payload.get('amount') or 0.0)
        except Exception:
            amount = 0.0
        if target_id <= 0 or amount <= 0:
            return {'ok': False, 'error': 'invalid_payload'}

        try:
            if target_type == 'fruit':
                rec = request.env['wish.tree.fruit'].sudo().browse(target_id)
                if not rec.exists():
                    return {'ok': False, 'error': 'fruit_not_found'}
                rec.add_donation(amount)
                return {'ok': True}
            if target_type == 'card':
                rec = request.env['wish.tree.card'].sudo().browse(target_id)
                if not rec.exists():
                    return {'ok': False, 'error': 'card_not_found'}
                rec.add_donation(amount)
                return {'ok': True}
            return {'ok': False, 'error': 'unknown_target_type'}
        except Exception as e:
            return {'ok': False, 'error': 'donation_failed', 'detail': str(e)[:200]}

    @http.route('/api/little_j/ask', type='json', auth='public', csrf=False)
    def little_j_ask(self, **payload):
        q = ''
        if payload:
            q = (payload.get('query') or '').strip()
        if not q:
            return {'ok': False, 'answer': ''}
        return {'ok': True, 'answer': '收到：' + q}

    @http.route('/wuchang/backup/download', type='http', auth='user', csrf=False)
    def download_backup(self, **kw):
        user = request.env.user
        allowed = user.has_group('base.group_system') or user.has_group('base.group_erp_manager')
        if not allowed:
            return request.make_response('forbidden', headers=[('Content-Type', 'text/plain')], status=403)

        import os
        base_dir = os.path.join(os.getcwd(), 'downloads')
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            if os.path.isdir(base_dir):
                for root, dirs, files in os.walk(base_dir):
                    for fn in files:
                        full = os.path.join(root, fn)
                        rel = os.path.relpath(full, base_dir)
                        try:
                            zf.write(full, rel)
                        except Exception:
                            pass
            else:
                zf.writestr('README.txt', 'no backup directory')
        data = buf.getvalue()
        headers = [
            ('Content-Type', 'application/zip'),
            ('Content-Disposition', 'attachment; filename="wuchang_backup.zip"'),
        ]
        return request.make_response(data, headers=headers)

_logger = logging.getLogger(__name__)


class JulesController(http.Controller):
    def _check_auth(self):
        try:
            key = (request.env['ir.config_parameter'].sudo().get_param('jules.api_key') or '').strip()
        except Exception:
            key = ''
        if not key:
            return True
        got = (request.httprequest.headers.get('X-Jules-Key') or '').strip()
        return got == key

    def _find_partner_by_unit(self, user_unit):
        user_unit = (user_unit or '').strip()
        if not user_unit:
            return None

        Unit = request.env['wuchang.property.unit'].sudo()
        unit = Unit.search([('name', '=', user_unit)], limit=1)
        Partner = request.env['res.partner'].sudo()

        if unit and (unit.owner_name or '').strip():
            p = Partner.search([('name', '=', unit.owner_name.strip())], limit=1)
            if p:
                return p

        p = Partner.search([('name', '=', user_unit)], limit=1)
        if p:
            return p
        return None

    @http.route('/jules/api/v1/get_resident_status', type='json', auth='public', methods=['POST'], csrf=False)
    def get_resident_status(self, **payload):
        if not self._check_auth():
            return {'status': 'error', 'message': 'unauthorized'}

        user_unit = (payload or {}).get('user_unit')
        partner = self._find_partner_by_unit(user_unit)

        Unit = request.env['wuchang.property.unit'].sudo()
        unit = Unit.search([('name', '=', (user_unit or '').strip())], limit=1)
        fee_amount = 0.0
        if unit:
            try:
                fee_amount = float(unit.calculate_fee() or 0.0)
            except Exception:
                fee_amount = 0.0

        packages = []
        if partner:
            Package = request.env['community.package'].sudo()
            recs = Package.search([('resident_id', '=', partner.id), ('status', '=', 'arrived')], order='arrival_date desc')
            for r in recs:
                packages.append({
                    'carrier': None,
                    'arrived_at': str(r.arrival_date or ''),
                })

        user_data = {
            'unit': user_unit,
            'happy_coins': float(partner.whc_wallet_balance or 0.0) if partner else 0.0,
            'management_fee_status': 'unpaid' if fee_amount else 'unknown',
            'management_fee_amount': fee_amount,
            'pending_packages': packages,
        }

        _logger.info("JULES resident status: %s", user_unit)
        return {'status': 'success', 'data': user_data}

    @http.route('/jules/api/v1/list_charity_services', type='json', auth='public', methods=['POST'], csrf=False)
    def list_charity_services(self, **payload):
        if not self._check_auth():
            return {'status': 'error', 'message': 'unauthorized'}

        services = [
            {'id': 's1', 'name': '呼叫黃師傅 (洗冷氣)', 'price': 2500, 'coin_reward': 50, 'charity_feedback': 100},
            {'id': 's2', 'name': '潔客幫 (居家清潔)', 'price': 1800, 'coin_reward': 30, 'charity_feedback': 80},
            {'id': 's3', 'name': '喜憨兒烘焙坊 (愛心餐盒)', 'price': 150, 'coin_reward': 5, 'charity_feedback': 15},
            {'id': 's4', 'name': '愛心待用餐 (捐贈)', 'price': 100, 'coin_reward': 10, 'charity_feedback': 100, 'is_donation': True},
        ]
        return {'status': 'success', 'data': services}

    @http.route('/jules/api/v1/book_charity_service', type='json', auth='public', methods=['POST'], csrf=False)
    def book_charity_service(self, **payload):
        if not self._check_auth():
            return {'status': 'error', 'message': 'unauthorized'}

        user_unit = (payload or {}).get('user_unit')
        service_id = (payload or {}).get('service_id')
        partner = self._find_partner_by_unit(user_unit)

        service_map = {
            's1': {'name': '呼叫黃師傅 (洗冷氣)', 'reward': 50, 'price': 2500},
            's2': {'name': '潔客幫 (居家清潔)', 'reward': 30, 'price': 1800},
            's3': {'name': '喜憨兒烘焙坊 (愛心餐盒)', 'reward': 5, 'price': 150},
            's4': {'name': '愛心待用餐 (捐贈)', 'reward': 10, 'price': 100},
        }
        info = service_map.get(service_id or '', {'name': '未知服務', 'reward': 0, 'price': 0})

        try:
            Order = request.env['wuchang.order'].sudo()
            Order.create({
                'customer_name': partner.name if partner else (user_unit or ''),
                'sale_mode': 'delivery_nonprofit',
                'nonprofit_program': info['name'],
                'total_amount': float(info.get('price') or 0.0),
                'social_impact_score': float(info.get('reward') or 0.0),
                'social_impact_note': 'JULES charity service',
            })
        except Exception:
            pass

        new_balance = 0.0
        if partner and float(info.get('reward') or 0.0) > 0:
            reward = float(info.get('reward') or 0.0)
            partner.sudo().write({'whc_wallet_balance': float(partner.whc_wallet_balance or 0.0) + reward})
            try:
                request.env['wuchang.coin.transaction'].sudo().create({
                    'source_partner_id': False,
                    'dest_partner_id': partner.id,
                    'amount': reward,
                    'transaction_type': 'reward',
                })
            except Exception:
                pass
            new_balance = float(partner.whc_wallet_balance or 0.0) + reward

        _logger.info("JULES book charity service: %s %s", user_unit, service_id)
        return {
            'status': 'success',
            'message': "已成功為您%s %s" % ('捐贈' if service_id == 's4' else '預約', info['name']),
            'transaction': {
                'service': info['name'],
                'earned_coins': float(info.get('reward') or 0.0),
                'new_coin_balance': new_balance,
            }
        }

    @http.route('/jules/api/v1/list_wishes', type='json', auth='public', methods=['POST'], csrf=False)
    def list_wishes(self, **payload):
        if not self._check_auth():
            return {'status': 'error', 'message': 'unauthorized'}

        Card = request.env['wish.tree.card'].sudo()
        cards = Card.search([('active', '=', True)], order='id desc', limit=50)
        wishes = []
        for c in cards:
            votes = float(c.current_amount or 0.0)
            threshold = float(c.target_amount or 0.0)
            if c.state == 'approved':
                st = 'approved'
            elif threshold > 0 and votes >= threshold:
                st = 'reviewing'
            else:
                st = 'voting'
            wishes.append({
                'id': str(c.id),
                'title': c.name,
                'votes': votes,
                'threshold': threshold,
                'status': st,
            })
        return {'status': 'success', 'data': wishes}

    @http.route('/jules/api/v1/vote_wish', type='json', auth='public', methods=['POST'], csrf=False)
    def vote_wish(self, **payload):
        if not self._check_auth():
            return {'status': 'error', 'message': 'unauthorized'}

        user_unit = (payload or {}).get('user_unit')
        wish_id = (payload or {}).get('wish_id')
        try:
            coins = float((payload or {}).get('coins') or 10)
        except Exception:
            coins = 10.0
        if coins <= 0:
            return {'status': 'error', 'message': 'invalid_coins'}

        partner = self._find_partner_by_unit(user_unit)
        if not partner:
            return {'status': 'error', 'message': 'resident_not_found'}
        if float(partner.whc_wallet_balance or 0.0) < coins:
            return {'status': 'error', 'message': 'insufficient_balance'}

        try:
            wid = int(wish_id or 0)
        except Exception:
            wid = 0
        card = request.env['wish.tree.card'].sudo().browse(wid)
        if not card.exists():
            return {'status': 'error', 'message': 'wish_not_found'}

        partner.sudo().write({'whc_wallet_balance': float(partner.whc_wallet_balance or 0.0) - coins})
        try:
            request.env['wuchang.coin.transaction'].sudo().create({
                'source_partner_id': partner.id,
                'dest_partner_id': False,
                'amount': coins,
                'transaction_type': 'burn',
            })
        except Exception:
            pass

        card.add_donation(coins)

        _logger.info("JULES vote wish: %s %s %s", user_unit, wish_id, coins)
        return {
            'status': 'success',
            'message': '灌溉成功！感謝您對社區的付出。',
            'deducted_coins': coins,
            'current_votes': float(card.current_amount or 0.0),
        }

    @http.route('/jules/api/v1/create_wish', type='json', auth='public', methods=['POST'], csrf=False)
    def create_wish(self, **payload):
        if not self._check_auth():
            return {'status': 'error', 'message': 'unauthorized'}

        user_unit = (payload or {}).get('user_unit')
        title = (payload or {}).get('title')
        description = (payload or {}).get('description')
        partner = self._find_partner_by_unit(user_unit)
        if not partner:
            return {'status': 'error', 'message': 'resident_not_found'}

        cost = 50.0
        if float(partner.whc_wallet_balance or 0.0) < cost:
            return {'status': 'error', 'message': 'insufficient_balance'}

        partner.sudo().write({'whc_wallet_balance': float(partner.whc_wallet_balance or 0.0) - cost})
        try:
            request.env['wuchang.coin.transaction'].sudo().create({
                'source_partner_id': partner.id,
                'dest_partner_id': False,
                'amount': cost,
                'transaction_type': 'burn',
            })
        except Exception:
            pass

        Card = request.env['wish.tree.card'].sudo()
        card = Card.create({
            'name': (title or '').strip() or '新願望',
            'applicant_id': partner.id,
            'description': description or '',
            'target_amount': 100.0,
            'current_amount': 0.0,
            'state': 'draft',
        })

        _logger.info("JULES create wish: %s %s", user_unit, title)
        return {
            'status': 'success',
            'message': '願望已建立，即將開始集氣！',
            'wish_id': str(card.id),
            'deducted_coins': cost,
        }
    @http.route('/jules/api/v1/list_volunteer_tasks', type='json', auth='public', methods=['POST'], csrf=False)
    def list_volunteer_tasks(self, **payload):
        if not self._check_auth():
            return {'status': 'error', 'message': 'unauthorized'}

        Task = request.env['wuchang.volunteer.task'].sudo()
        tasks = Task.search([('state', '=', 'open')], order='date_start asc', limit=20)
        
        data = []
        for t in tasks:
            data.append({
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'date_start': str(t.date_start),
                'coins_reward': t.coins_reward,
                'required_people': t.required_people,
                'signed_up_count': len(t.volunteer_ids)
            })
        return {'status': 'success', 'data': data}

    @http.route('/jules/api/v1/signup_volunteer', type='json', auth='public', methods=['POST'], csrf=False)
    def signup_volunteer(self, **payload):
        if not self._check_auth():
            return {'status': 'error', 'message': 'unauthorized'}

        user_unit = (payload or {}).get('user_unit')
        task_id = (payload or {}).get('task_id')
        partner = self._find_partner_by_unit(user_unit)
        if not partner:
            return {'status': 'error', 'message': 'resident_not_found'}

        try:
            tid = int(task_id or 0)
            request.env['wuchang.volunteer.signup'].sudo().create({
                'task_id': tid,
                'partner_id': partner.id
            })
            return {'status': 'success', 'message': '報名成功！感謝您的熱心參與。'}
        except Exception as e:
            return {'status': 'error', 'message': '報名失敗，可能已重複報名或任務不存在。', 'detail': str(e)}

    @http.route('/jules/api/v1/list_products', type='json', auth='public', methods=['POST'], csrf=False)
    def list_products(self, **payload):
        if not self._check_auth():
            return {'status': 'error', 'message': 'unauthorized'}

        category = (payload or {}).get('category')
        domain = [('active', '=', True)]
        if category:
            domain.append(('category', '=', category))

        Product = request.env['community.product'].sudo()
        products = Product.search(domain, order='create_date desc', limit=50)
        
        data = []
        for p in products:
            data.append({
                'id': p.id,
                'name': p.name,
                'price': p.price,
                'coin_reward': p.coin_reward,
                'image_url': p.image_url,
                'category': p.category,
                'seller': p.partner_id.name
            })
        return {'status': 'success', 'data': data}

    @http.route('/jules/api/v1/create_order', type='json', auth='public', methods=['POST'], csrf=False)
    def create_order(self, **payload):
        if not self._check_auth():
            return {'status': 'error', 'message': 'unauthorized'}

        user_unit = (payload or {}).get('user_unit')
        product_id = (payload or {}).get('product_id')
        partner = self._find_partner_by_unit(user_unit)
        if not partner:
            return {'status': 'error', 'message': 'resident_not_found'}

        try:
            pid = int(product_id or 0)
            product = request.env['community.product'].sudo().browse(pid)
            if not product.exists():
                return {'status': 'error', 'message': 'product_not_found'}

            order = request.env['community.order'].sudo().create({
                'partner_id': partner.id,
                'product_id': pid,
                'amount': product.price,
                'status': 'paid' # 簡化流程：直接視為已付款
            })
            # 觸發付款後邏輯 (發放回饋)
            order.action_pay()
            
            return {
                'status': 'success', 
                'message': '訂購成功！', 
                'order_id': order.name,
                'earned_coins': product.coin_reward
            }
        except Exception as e:
            return {'status': 'error', 'message': '訂購失敗', 'detail': str(e)}

    @http.route('/jules/api/v1/list_pos_stores', type='json', auth='public', methods=['POST'], csrf=False)
    def list_pos_stores(self, **payload):
        if not self._check_auth():
            return {'status': 'error', 'message': 'unauthorized'}

        PosConfig = request.env['pos.config'].sudo()
        # Find stores that are fund partners (likely to be our target stores)
        configs = PosConfig.search([('wuchang_delivery_fund_partner', '=', True)])
        
        stores = []
        for c in configs:
            # Check for active session
            session = request.env['pos.session'].sudo().search([
                ('config_id', '=', c.id),
                ('state', '=', 'opened')
            ], limit=1)
            
            is_open = bool(session)
            
            # Get products (simplified: first 20 available in POS)
            Product = request.env['product.product'].sudo()
            products_recs = Product.search([
                ('available_in_pos', '=', True),
                ('sale_ok', '=', True),
                ('active', '=', True)
            ], limit=50) # In real world, filter by config's available categories
            
            products = []
            for p in products_recs:
                products.append({
                    'id': p.id,
                    'name': p.name,
                    'price': p.list_price,
                    'category': p.pos_categ_id.name if p.pos_categ_id else 'Other',
                    'image_url': '/web/image/product.product/%s/image_128' % p.id
                })

            stores.append({
                'id': c.id,
                'name': c.name,
                'is_open': is_open,
                'session_id': session.id if session else None,
                'products': products
            })
            
        return {'status': 'success', 'data': stores}

    @http.route('/jules/api/v1/create_pos_online_order', type='json', auth='public', methods=['POST'], csrf=False)
    def create_pos_online_order(self, **payload):
        if not self._check_auth():
            return {'status': 'error', 'message': 'unauthorized'}

        user_unit = (payload or {}).get('user_unit')
        config_id = (payload or {}).get('config_id')
        lines = (payload or {}).get('lines') or [] # [{product_id: 1, qty: 1}]
        order_type = (payload or {}).get('type') or 'takeout' # takeout / delivery

        partner = self._find_partner_by_unit(user_unit)
        if not partner:
            return {'status': 'error', 'message': 'resident_not_found'}

        # Find Open Session
        Session = request.env['pos.session'].sudo()
        session = Session.search([
            ('config_id', '=', int(config_id)),
            ('state', '=', 'opened')
        ], limit=1)

        if not session:
             return {'status': 'error', 'message': 'store_closed'}

        try:
            PosOrder = request.env['pos.order'].sudo()
            PosOrderLine = request.env['pos.order.line'].sudo()
            Product = request.env['product.product'].sudo()

            # Create Order
            # Note: Creating pos.order directly via ORM is possible but usually it expects
            # data structure from UI. We will do a server-side creation.
            
            order_vals = {
                'session_id': session.id,
                'partner_id': partner.id,
                'state': 'draft',
                'pos_reference': 'Online Order %s' % int(time.time()),
            }
            order = PosOrder.create(order_vals)
            
            total_amount = 0.0
            
            for line in lines:
                pid = int(line.get('product_id'))
                qty = float(line.get('qty') or 1.0)
                product = Product.browse(pid)
                
                price = product.list_price
                line_amount = price * qty
                total_amount += line_amount
                
                PosOrderLine.create({
                    'order_id': order.id,
                    'product_id': pid,
                    'qty': qty,
                    'price_unit': price,
                    'price_subtotal': line_amount,
                    'price_subtotal_incl': line_amount, # Simplified tax
                    'full_product_name': product.name,
                })

            # Update amounts
            order.write({
                'amount_total': total_amount,
                'amount_tax': 0,
                'amount_paid': 0,
                'amount_return': 0,
            })
            
            # If paid online (simulated), we would add a payment line here.
            # For now, we leave it as draft (unpaid) for the cashier to process or 'paid' if we assume wallet deduction.
            
            # Let's deduct from Wallet if they chose to? 
            # For simplicity, we assume "Pay at Counter" for now, or "Deducted" if we add logic.
            # User requirement: "Online Ordering Mechanism". 
            
            return {
                'status': 'success',
                'message': '訂單已傳送至 POS 機！',
                'order_ref': order.pos_reference,
                'order_id': order.id
            }

        except Exception as e:
             return {'status': 'error', 'message': 'create_order_failed', 'detail': str(e)}


