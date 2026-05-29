# wuchang_core Phase2C Warning Fix

TIME=2026-05-26T01:27:25+08:00

DB_BACKUP=/home/taiji_admin/Taiji_Hub/runtime/backups/odoo_postgres_before_wuchang_core_phase2c_warning_fix_20260526_012701.dump
WEB_OK=true

## Patch

- Added model: wuchang.delivery.team
- Patched _description target: wuchang.ai.supervisor.log where source class was found
- Source write: false
- Runtime addon update: true

## Filtered Logs

KeyError: 'website.visitor'
2026-05-25 17:10:45,784 1 ERROR postgres odoo.addons.base.models.ir_cron: Job 'Mail: Email Queue Manager' (3) server action #133 failed 
Traceback (most recent call last):
KeyError: 'mail.mail'
2026-05-25 17:10:45,816 1 ERROR postgres odoo.addons.base.models.ir_cron: Job 'Users: Notify About Unregistered Users' (12) server action #159 failed 
Traceback (most recent call last):
AttributeError: 'res.users' object has no attribute 'send_unregistered_user_reminder'
Traceback (most recent call last):
    raise ValueError('%r while evaluating\n%r' % (e, expr))
ValueError: AttributeError("'res.users' object has no attribute 'send_unregistered_user_reminder'") while evaluating
2026-05-25 17:10:45,859 1 ERROR postgres odoo.addons.base.models.ir_cron: Job 'Partner Autocomplete: Sync with remote DB' (13) server action #211 failed 
Traceback (most recent call last):
KeyError: 'res.partner.autocomplete.sync'
2026-05-25 17:13:44,281 1 INFO ? odoo.service.server: HTTP service (werkzeug) running on 05d5febb8401:8069 
2026-05-25 17:13:45,307 1 WARNING postgres odoo.models: The model wuchang.ai.supervisor.log has no _description 
2026-05-25 17:13:45,427 1 WARNING postgres odoo.fields: Field wuchang.volunteer.meeting.team_id with unknown comodel_name 'wuchang.delivery.team' 
2026-05-25 17:13:45,427 1 WARNING postgres odoo.fields: Field wuchang.volunteer.announcement.team_id with unknown comodel_name 'wuchang.delivery.team' 
2026-05-25 17:13:45,455 1 INFO postgres odoo.modules.registry: Registry loaded in 1.173s 
2026-05-25 17:22:43,152 1 INFO ? odoo.service.server: HTTP service (werkzeug) running on 05d5febb8401:8069 
2026-05-25 17:22:44,189 1 WARNING postgres odoo.models: The model wuchang.ai.supervisor.log has no _description 
2026-05-25 17:22:44,307 1 WARNING postgres odoo.fields: Field wuchang.volunteer.meeting.team_id with unknown comodel_name 'wuchang.delivery.team' 
2026-05-25 17:22:44,307 1 WARNING postgres odoo.fields: Field wuchang.volunteer.announcement.team_id with unknown comodel_name 'wuchang.delivery.team' 
2026-05-25 17:22:44,337 1 INFO postgres odoo.modules.registry: Registry loaded in 1.183s 
2026-05-25 17:24:49,044 1 INFO ? odoo.service.server: HTTP service (werkzeug) running on 05d5febb8401:8069 
2026-05-25 17:24:50,398 1 WARNING postgres odoo.models: The model wuchang.ai.supervisor.log has no _description 
2026-05-25 17:24:50,495 1 WARNING postgres odoo.fields: Field wuchang.volunteer.meeting.team_id with unknown comodel_name 'wuchang.delivery.team' 
2026-05-25 17:24:50,495 1 WARNING postgres odoo.fields: Field wuchang.volunteer.announcement.team_id with unknown comodel_name 'wuchang.delivery.team' 
2026-05-25 17:24:50,513 1 INFO postgres odoo.modules.registry: Registry loaded in 1.469s 
2026-05-25 17:27:16,086 1 INFO ? odoo.service.server: HTTP service (werkzeug) running on 05d5febb8401:8069 
2026-05-25 17:27:16,540 1 WARNING postgres odoo.models: The model wuchang.ai.supervisor.log has no _description 
2026-05-25 17:27:16,656 1 INFO postgres odoo.modules.registry: Registry loaded in 0.569s 

## Boundary

DB_WRITE=true
MODULE_UPDATE=true
SERVICE_RESTART=true
RAW_PII_TO_CLOUD=false
SECRET_READ=false
