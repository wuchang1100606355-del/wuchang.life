{
    'name': 'Taiji PM3 Runtime Sync',
    'version': '1.0',
    'category': 'Infrastructure',
    'summary': 'PM3 runtime sync, vector memory, behavior vector database, and desensitized realtime dashboard',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/pm3_memory_index_views.xml',
        'views/pm3_vector_state_window_views.xml',
        'views/pm3_fixed_vector_state_window_views.xml',
        'views/pm3_behavior_vector_database_views.xml',
        'views/pm3_desensitized_dashboard_views.xml',
        'views/web_login_templates.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
