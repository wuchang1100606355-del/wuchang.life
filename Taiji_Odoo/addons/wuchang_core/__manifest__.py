{
    'name': '五常核心模組 (Wuchang Core)',
    'version': '18.0.1.0.0',
    'summary': 'W7TP 五常志工管理與 POS API 核心',
    'depends': ['base'],
    'data': ['views/volunteer_point_views.xml'],
    'assets': {
        'web.assets_backend': [
            'wuchang_core/static/src/js/background_service.js',
        ],
    },
    'installable': True,
    'application': False,
}
