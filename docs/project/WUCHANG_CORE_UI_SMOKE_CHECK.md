# wuchang_core UI Smoke Check

TIME=2026-05-26T01:15:56+08:00

## Module State


## UI Counts


## Web
WEB_OK=true

## Relevant Logs
KeyError: 'website'
2026-05-25 17:10:45,750 1 ERROR postgres odoo.addons.base.models.ir_cron: Job 'Website Visitor : clean inactive visitors' (24) server action #476 failed 
Traceback (most recent call last):
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
2026-05-25 17:13:45,455 1 INFO postgres odoo.modules.registry: Registry loaded in 1.173s 

## Boundary
DB_READ=true
DB_WRITE=false
MODULE_INSTALL=false
SERVICE_RESTART=false
RAW_PII_TO_CLOUD=false
