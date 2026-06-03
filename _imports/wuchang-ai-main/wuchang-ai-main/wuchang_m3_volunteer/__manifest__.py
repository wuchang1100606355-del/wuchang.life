{
    'name': 'Wuchang Volunteer Service',
    'version': '1.0',
    'summary': 'Volunteer management foundation for Wuchang community services',
    'category': 'Human Resources',
    'depends': ['hr', 'project'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/wuchang_skill_views.xml',
    ],
    'installable': True,
    'application': False,
}
