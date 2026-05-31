from odoo import fields, models


class WuchangCafeOptionGroup(models.Model):
    _name = "wuchang.cafe.option.group"
    _description = "WuChang Cafe POS Option Group"
    _order = "sequence, code"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    source = fields.Char(default="quickclick")
    note = fields.Text()

    w5c_code = fields.Char(index=True)
    w5c_domain = fields.Char(index=True, default="CAFE")
    w5c_entity = fields.Char(index=True, default="OPTION_GROUP")
    w5c_topology = fields.Char(index=True)
    w5c_time_state = fields.Char(index=True)
    w5c_authority = fields.Char(index=True)

    question_ids = fields.One2many("wuchang.cafe.option.question", "group_id")


class WuchangCafeOptionQuestion(models.Model):
    _name = "wuchang.cafe.option.question"
    _description = "WuChang Cafe POS Option Question"
    _order = "group_id, sequence, name"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    group_id = fields.Many2one("wuchang.cafe.option.group", required=True, index=True, ondelete="cascade")
    name = fields.Char(required=True)
    display_name = fields.Char()
    selection_type = fields.Selection([
        ("single", "Single"),
        ("multiple", "Multiple"),
    ], default="single", required=True)
    required = fields.Boolean(default=True)
    quickclick_question_code = fields.Char(index=True)

    w5c_code = fields.Char(index=True)
    w5c_domain = fields.Char(index=True, default="CAFE")
    w5c_entity = fields.Char(index=True, default="OPTION_QUESTION")
    w5c_topology = fields.Char(index=True)
    w5c_time_state = fields.Char(index=True)
    w5c_authority = fields.Char(index=True)

    item_ids = fields.One2many("wuchang.cafe.option.item", "question_id")


class WuchangCafeOptionItem(models.Model):
    _name = "wuchang.cafe.option.item"
    _description = "WuChang Cafe POS Option Item"
    _order = "question_id, sequence, name"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    question_id = fields.Many2one("wuchang.cafe.option.question", required=True, index=True, ondelete="cascade")
    name = fields.Char(required=True)
    display_name = fields.Char()
    price_delta = fields.Float(default=0.0)
    child_group_code = fields.Char(index=True)
    child_group_id = fields.Many2one("wuchang.cafe.option.group", string="Child Option Group")
    quickclick_item_code = fields.Char(index=True)
    quickclick_question_code = fields.Char(index=True)
    note = fields.Text()

    w5c_code = fields.Char(index=True)
    w5c_domain = fields.Char(index=True, default="CAFE")
    w5c_entity = fields.Char(index=True, default="OPTION_ITEM")
    w5c_topology = fields.Char(index=True)
    w5c_time_state = fields.Char(index=True)
    w5c_authority = fields.Char(index=True)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    quickclick_menu_id = fields.Char(index=True)
    quickclick_product_id = fields.Char(index=True)
    quickclick_product_code = fields.Char(index=True)
    quickclick_sku = fields.Char(index=True)
    quickclick_option_group_code = fields.Char(index=True)
    quickclick_image_url = fields.Char()
    quickclick_raw_category = fields.Char(index=True)
    quickclick_raw_price = fields.Float()
    normalized_price_basis = fields.Char(index=True)
    normalized_price_note = fields.Text()
    wuchang_pos_locked = fields.Boolean(default=False, index=True)
    wuchang_option_group_id = fields.Many2one("wuchang.cafe.option.group", string="WuChang POS Option Group")

    w5c_code = fields.Char(index=True)
    w5c_domain = fields.Char(index=True)
    w5c_entity = fields.Char(index=True)
    w5c_topology = fields.Char(index=True)
    w5c_time_state = fields.Char(index=True)
    w5c_authority = fields.Char(index=True)
