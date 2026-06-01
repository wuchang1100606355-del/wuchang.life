{
    'name': 'Wuchang Community Incubator',
    'version': '1.0',
    'summary': 'Core module for WUCHANG-COMM-INCUB-2025 project',
    'author': 'Gemini',
    'website': 'https://wuchang.tw',
    'category': 'Uncategorized',
    'depends': ['base', 'portal', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/wuchang_views.xml',
        'data/product_categories.xml',
        'data/pos_part1/product.template.csv',
        'data/pos_part2/product.template.csv',
        'data/pos_part3/product.template.csv',
        'data/res.users.csv',
    ],
    'assets': {
        'web.assets_frontend': [
            'wuchang_comm_incub/static/src/css/login.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}