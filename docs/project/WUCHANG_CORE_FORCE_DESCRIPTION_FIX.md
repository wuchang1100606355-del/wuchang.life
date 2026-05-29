# wuchang_core Force Description Fix

TIME=2026-05-26T01:29:55+08:00

## Locate

/mnt/extra-addons/wuchang_core/models/volunteer.py:73:    _name = 'wuchang.ai.supervisor.log'

## Patch



## Fresh Logs Since Restart

2026-05-25 17:28:32,067 1 INFO ? odoo.service.server: HTTP service (werkzeug) running on 05d5febb8401:8069 
2026-05-25 17:28:32,969 1 WARNING postgres odoo.models: The model wuchang.ai.supervisor.log has no _description 
2026-05-25 17:28:33,076 1 INFO postgres odoo.modules.registry: Registry loaded in 1.008s 
2026-05-25 17:29:46,419 1 INFO ? odoo.service.server: HTTP service (werkzeug) running on 05d5febb8401:8069 
2026-05-25 17:29:47,617 1 WARNING postgres odoo.models: The model wuchang.ai.supervisor.log has no _description 
2026-05-25 17:29:47,742 1 INFO postgres odoo.modules.registry: Registry loaded in 1.319s 

## Web

WEB_OK=true

## Boundary

DB_WRITE=false
MODULE_INSTALL=false
SERVICE_RESTART=true
RAW_PII_TO_CLOUD=false
SECRET_READ=false
PATCH_SCOPE=container_runtime_file_only
