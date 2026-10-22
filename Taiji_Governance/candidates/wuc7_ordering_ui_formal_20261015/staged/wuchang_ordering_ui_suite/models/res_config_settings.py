from odoo import fields, models


SUITE_SETTING_KEY = "liaoguo.ui.selected_suite.company_3.pos_unresolved"
SUITE_SELECTION = [
    ("a", "靛藍科技"),
    ("b", "暖米咖啡"),
    ("c", "墨韻典藏"),
]


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    liaoguo_ui_selected_suite = fields.Selection(
        selection=SUITE_SELECTION,
        string="重新總店三套介面",
        default="a",
        config_parameter=SUITE_SETTING_KEY,
        help="只切換上品食品行重新總店候選的既有三套視覺；精確 POS 未核定前不得啟用，不改商品、價格、會員或付款權威。",
    )
