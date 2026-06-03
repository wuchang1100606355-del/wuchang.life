# -*- coding: utf-8 -*-
from odoo import models, fields


class WuchangMenuAttribute(models.Model):
    _name = 'wuchang.menu.attribute'
    _description = 'Menu Attribute'

    name = fields.Char(required=True)
    technical_key = fields.Char(required=True)
    value_ids = fields.One2many('wuchang.menu.attribute.value', 'attribute_id')


class WuchangMenuAttributeValue(models.Model):
    _name = 'wuchang.menu.attribute.value'
    _description = 'Menu Attribute Value'

    name = fields.Char(required=True)
    delta_price = fields.Float(default=0.0)
    attribute_id = fields.Many2one('wuchang.menu.attribute', required=True, ondelete='cascade')


class WuchangMenuAddon(models.Model):
    _name = 'wuchang.menu.addon'
    _description = 'Menu Addon'

    code = fields.Char(index=True)
    name = fields.Char(required=True)
    delta_price = fields.Float(default=0.0)
    addon_type = fields.Char()
    active = fields.Boolean(default=True)


class WuchangMenuItem(models.Model):
    _name = 'wuchang.menu.item'
    _description = 'Menu Item'

    code = fields.Char(index=True)
    name = fields.Char(required=True)
    base_price = fields.Float(required=True)
    category = fields.Char()
    description = fields.Text()
    active = fields.Boolean(default=True)
    addon_line_ids = fields.One2many('wuchang.menu.item.addon', 'item_id')
    attr_line_ids = fields.One2many('wuchang.menu.item.attribute', 'item_id')


class WuchangMenuItemAddon(models.Model):
    _name = 'wuchang.menu.item.addon'
    _description = 'Menu Item-Addon Link'

    item_id = fields.Many2one('wuchang.menu.item', required=True, ondelete='cascade')
    addon_id = fields.Many2one('wuchang.menu.addon', required=True, ondelete='cascade')
    delta_price = fields.Float(default=0.0)


class WuchangMenuItemAttribute(models.Model):
    _name = 'wuchang.menu.item.attribute'
    _description = 'Menu Item-Attribute Link'

    item_id = fields.Many2one('wuchang.menu.item', required=True, ondelete='cascade')
    attribute_id = fields.Many2one('wuchang.menu.attribute', required=True, ondelete='cascade')
    allow_value_ids = fields.Many2many('wuchang.menu.attribute.value')

