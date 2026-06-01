{
    'name': 'Wuchang Smart Property',
    'version': '1.0',
    'summary': 'Smart property maintenance requests integrated with volunteer services',
    'category': 'Services/Property',
    'depends': ['wuchang_m3_volunteer', 'project', 'maintenance', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/property_request_views.xml',
    ],
    'installable': True,
    'application': True,
}
