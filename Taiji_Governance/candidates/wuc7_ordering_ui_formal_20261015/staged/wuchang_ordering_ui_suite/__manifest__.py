{
    "name": "Wuchang Ordering UI Suite (Odoo-Bound Candidate)",
    "version": "18.0.0.3.2",
    "category": "Point of Sale",
    "summary": "Three-style ordering and management surfaces bound to the Chongxin HQ Odoo scope",
    "depends": [
        "website",
        "point_of_sale",
        "wuchang_core",
        "wuchang_cafe_menu_options",
        "wuchang_cafe_ai_gateway",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/management_ui.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "wuchang_ordering_ui_suite/static/src/css/suite_tokens.css",
            "wuchang_ordering_ui_suite/static/src/js/suite_contract.js",
            "wuchang_ordering_ui_suite/static/src/js/order_flow_contract.js",
        ],
        "web.assets_frontend": [
            "wuchang_ordering_ui_suite/static/src/css/suite_tokens.css",
            "wuchang_ordering_ui_suite/static/src/css/management_ui.css",
            "wuchang_ordering_ui_suite/static/src/js/suite_contract.js",
            "wuchang_ordering_ui_suite/static/src/js/order_flow_contract.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
