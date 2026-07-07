{
    "name": "Wuchang Member Registration",
    "version": "1.0.0",
    "summary": "W7TP privacy-first member registration workflow",
    "category": "Wuchang/W7TP",
    "author": "Wuchang Smart Cloud",
    "license": "LGPL-3",
    "depends": ["base", "web", "auth_signup"],
    "data": [
        "security/wuchang_member_groups.xml",
        "security/ir.model.access.csv",
        "views/login_templates.xml",
        "views/signup_templates.xml",
        "views/error_templates.xml",
        "views/member_registration_views.xml",
        "views/group_member_registration_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "wuchang_member_registration/static/src/scss/portal.scss",
        ],
    },
    "installable": True,
    "application": False,
}
