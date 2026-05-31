{'name': 'Wuchang AI Task Force (Unified)',
 'summary': '五常 AI 特遣隊與核心系統 (Unified Core)',
 'description': '\n'
                '        五常指揮中心整合模組\n'
                '        ====================\n'
                '        整合原有 AI 代理人系統與新版特遣隊功能：\n'
                '        * AI Agents & Memory (Original)\n'
                '        * Finance & Property (Original)\n'
                '        * AI 特遣隊成員管理 (New)\n'
                '        * 時光 系 AI 增幅裝置 (New)\n'
                '        * 五常生活公約 (New)\n'
                '    ',
 'author': 'Odoo Chief Engineer & Sister',
 'website': 'http://www.wuchang.cloud',
 'category': 'Productivity',
 'version': '18.0.2.0.0',
 'depends': ['base', 'web', 'point_of_sale', 'website', 'hr', 'project', 'maintenance'],
 'data': ['security/security.xml',
          'security/ir.model.access.csv',
          'data/property_structure_data.xml',
          'views/wuchang_core_phase2_ui.xml'],
 'installable': True,
 'application': True,
 'auto_install': False,
 'assets': {'web.assets_backend': ['wuchang_core/static/src/js/delivery_rider.js',
                                   'wuchang_core/static/src/xml/delivery_interfaces.xml']},
 'license': 'LGPL-3'}
