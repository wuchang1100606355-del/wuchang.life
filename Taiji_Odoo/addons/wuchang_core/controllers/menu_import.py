# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class WuchangMenuImport(http.Controller):

    @http.route('/api/menu/import', type='json', auth='none', csrf=False)
    def import_menu(self, **payload):
        items = payload.get('items') or []
        addons = payload.get('addons') or []
        links = payload.get('links') or {}
        attributes = payload.get('attributes') or []
        Item = request.env['wuchang.menu.item'].sudo()
        Addon = request.env['wuchang.menu.addon'].sudo()
        ItemAddon = request.env['wuchang.menu.item.addon'].sudo()
        Attr = request.env['wuchang.menu.attribute'].sudo()
        AttrVal = request.env['wuchang.menu.attribute.value'].sudo()
        ItemAttr = request.env['wuchang.menu.item.attribute'].sudo()

        code_to_item = {}
        code_to_addon = {}

        for it in items:
            name = it.get('name') or ''
            price = float(it.get('base_price') or 0.0)
            category = it.get('category') or ''
            draft = ('名稱:' + str(name)) + '\n' + ('價格:' + str(price)) + '\n' + ('類別:' + str(category))
            refined = request.env['wuchang.ai.logic'].sudo().satellite_refine(draft)
            desc = it.get('description') or ''
            if refined:
                desc = (desc + ('\n' if desc else '') + str(refined))
            rec = Item.create({
                'code': it.get('code') or '',
                'name': name,
                'base_price': price,
                'category': category,
                'description': desc,
            })
            code_to_item[rec.code] = rec

        for ad in addons:
            code = ad.get('code') or ''
            name = ad.get('name') or ''
            addon = Addon.search([('code', '=', code)], limit=1)
            if not addon and name:
                addon = Addon.search([('name', '=', name)], limit=1)
            if addon:
                code_to_addon[addon.code or code] = addon

        for item_code, ad_list in links.items():
            item = code_to_item.get(item_code)
            if not item:
                continue
            for ad in ad_list:
                addon = code_to_addon.get(ad.get('code'))
                if not addon:
                    continue
                ItemAddon.create({
                    'item_id': item.id,
                    'addon_id': addon.id,
                    'delta_price': float(ad.get('delta_price') or addon.delta_price or 0.0),
                })

        for attr in attributes:
            key = attr.get('key') or ''
            name = attr.get('name') or ''
            a = None
            if key:
                a = Attr.search([('technical_key', '=', key)], limit=1)
            if (not a) and name:
                a = Attr.search([('name', '=', name)], limit=1)
            if not a:
                continue
            vals = []
            for v in attr.get('values') or []:
                vname = v.get('name') or ''
                val = AttrVal.search([('attribute_id', '=', a.id), ('name', '=', vname)], limit=1)
                if val:
                    vals.append(val.id)
            for it_code in attr.get('apply_items') or []:
                item = code_to_item.get(it_code)
                if item:
                    ItemAttr.create({'item_id': item.id, 'attribute_id': a.id, 'allow_value_ids': [(6, 0, vals)]})

        return {'ok': True, 'items': len(items), 'addons': len(addons)}

    @http.route('/api/menu/items', type='json', auth='public')
    def list_items(self):
        Item = request.env['wuchang.menu.item']
        items = Item.search([('active', '=', True)], limit=200)
        res = []
        for it in items:
            res.append({'code': it.code, 'name': it.name, 'base_price': it.base_price, 'category': it.category})
        return {'items': res}

    @http.route('/api/menu/policy/fit', type='json', auth='public', csrf=False)
    def policy_fit(self, **payload):
        item_code = (payload or {}).get('item_code') or ''
        selections = (payload or {}).get('selections') or {}
        Item = request.env['wuchang.menu.item'].sudo()
        Addon = request.env['wuchang.menu.addon'].sudo()
        Attr = request.env['wuchang.menu.attribute'].sudo()
        AttrVal = request.env['wuchang.menu.attribute.value'].sudo()
        ItemAddon = request.env['wuchang.menu.item.addon'].sudo()
        ItemAttr = request.env['wuchang.menu.item.attribute'].sudo()
        it = Item.search([('code', '=', item_code)], limit=1)
        if not it and item_code:
            it = Item.search([('name', '=', item_code)], limit=1)
        base = float(it.base_price or 0.0) if it else 0.0
        total = base
        applied_addons = []
        applied_attrs = []
        ad_sel = selections.get('addons') or []
        for s in ad_sel:
            ad = Addon.search([('code', '=', s)], limit=1)
            if not ad:
                ad = Addon.search([('name', '=', s)], limit=1)
            if not ad:
                continue
            if it:
                link = ItemAddon.search([('item_id', '=', it.id), ('addon_id', '=', ad.id)], limit=1)
                delta = float(link.delta_price or ad.delta_price or 0.0) if link else float(ad.delta_price or 0.0)
            else:
                delta = float(ad.delta_price or 0.0)
            total += delta
            applied_addons.append({'code': ad.code, 'name': ad.name, 'delta_price': delta})
        attr_sel = selections.get('attributes') or {}
        for k, vname in attr_sel.items():
            a = Attr.search([('technical_key', '=', k)], limit=1)
            if not a:
                a = Attr.search([('name', '=', k)], limit=1)
            if not a:
                continue
            val = AttrVal.search([('attribute_id', '=', a.id), ('name', '=', vname)], limit=1)
            if not val:
                continue
            if it:
                ia = ItemAttr.search([('item_id', '=', it.id), ('attribute_id', '=', a.id)], limit=1)
                if ia:
                    ok_ids = set(ia.allow_value_ids.ids)
                    if val.id not in ok_ids:
                        continue
            total += float(val.delta_price or 0.0)
            applied_attrs.append({'key': (a.technical_key or a.name), 'name': a.name, 'value': vname, 'delta_price': float(val.delta_price or 0.0)})
        draft = '商品:' + (it.name if it else item_code) + '\n' + ('基價:' + str(base)) + '\n' + ('加購:' + str([x.get('name') for x in applied_addons])) + '\n' + ('屬性:' + str([{x.get('key'): x.get('value')} for x in applied_attrs]))
        refined = request.env['wuchang.ai.logic'].sudo().satellite_refine(draft)
        return {'ok': True, 'base_price': base, 'total_price': total, 'addons': applied_addons, 'attributes': applied_attrs, 'refined': str(refined or '')}
