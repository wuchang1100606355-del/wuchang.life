{
    "name": "Taiji Member Login Panel",
    "version": "0.1.0",
    "summary": "Show Wuchang/Taiji internal member status on Odoo login page",
    "category": "Tools",
    "author": "CHIANG CHENG LUNG",
    "depends": ["web"],
    "data": [
        "views/login_panel.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "taiji_member_login/static/src/css/taiji_member_login.css",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
