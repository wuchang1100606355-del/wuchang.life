# wuchang_core Supervisor Description Hard Replace

TIME=2026-05-26T01:32:15+08:00

## Before
    65	class WuchangVolunteerAnnouncement(models.Model):
    66	    _name = 'wuchang.volunteer.announcement'
    67	    _description = '專勤隊公告'
    68	    name = fields.Char('標題')
    69	    content = fields.Html('內容')
    70	    team_id = fields.Many2one('wuchang.delivery.team')
    71	    
    72	class WuchangAiSupervisorLog(models.Model):
    73	    _name = 'wuchang.ai.supervisor.log'
    74	    name = fields.Char('督導事項')
    75	    target_volunteer_id = fields.Many2one('res.partner')
    76	    type = fields.Selection([('praise', '表揚'), ('reminder', '提醒'), ('warning', '警告')])
    77	    content = fields.Text()

## Patch


## After
    65	class WuchangVolunteerAnnouncement(models.Model):
    66	    _name = 'wuchang.volunteer.announcement'
    67	    _description = '專勤隊公告'
    68	    name = fields.Char('標題')
    69	    content = fields.Html('內容')
    70	    team_id = fields.Many2one('wuchang.delivery.team')
    71	    
    72	class WuchangAiSupervisorLog(models.Model):
    73	    _name = 'wuchang.ai.supervisor.log'
    74	    name = fields.Char('督導事項')
    75	    target_volunteer_id = fields.Many2one('res.partner')
    76	    type = fields.Selection([('praise', '表揚'), ('reminder', '提醒'), ('warning', '警告')])
    77	    content = fields.Text()

## Registry Truth
REGISTRY_MODEL=wuchang.ai.supervisor.log
REGISTRY_DESCRIPTION=wuchang.ai.supervisor.log

## Fresh Logs
2026-05-25 17:30:47,727 1 INFO ? odoo.service.server: HTTP service (werkzeug) running on 05d5febb8401:8069 
2026-05-25 17:30:50,050 1 WARNING postgres odoo.models: The model wuchang.ai.supervisor.log has no _description 
2026-05-25 17:30:50,403 1 INFO postgres odoo.modules.registry: Registry loaded in 2.675s 
2026-05-25 17:32:00,014 1 INFO ? odoo.service.server: HTTP service (werkzeug) running on 05d5febb8401:8069 
2026-05-25 17:32:00,894 1 WARNING postgres odoo.models: The model wuchang.ai.supervisor.log has no _description 
2026-05-25 17:32:01,011 1 INFO postgres odoo.modules.registry: Registry loaded in 0.997s 

## Web
WEB_OK=true

## Boundary
DB_WRITE=false
MODULE_INSTALL=false
SERVICE_RESTART=true
RAW_PII_TO_CLOUD=false
SECRET_READ=false
PATCH_SCOPE=container_runtime_file_only
