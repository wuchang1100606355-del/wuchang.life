{
    "name": "WuChang Cafe AI Gateway",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Read-only governance eventbook for WuChang Cafe AI/POS gateway actions.",
    "author": "WuChang / Liaoguo Cafe",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "point_of_sale",
        "product",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/wuchang_cafe_ai_eventbook_views.xml",
        "views/lineworks_notification_views.xml",
        "views/line_official_account_config_views.xml",
        "views/total_product_handoff_views.xml",
    ],
    "installable": True,
    "application": False,
}
