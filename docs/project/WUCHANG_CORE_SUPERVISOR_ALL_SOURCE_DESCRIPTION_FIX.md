# wuchang_core Supervisor All Source Description Fix

TIME=2026-05-26T01:35:43+08:00

## Patch


## Source Verify
/mnt/extra-addons/wuchang_core/models/volunteer.py:73:    _name = 'wuchang.ai.supervisor.log'

## Registry Truth
REGISTRY_MODEL=wuchang.ai.supervisor.log
REGISTRY_DESCRIPTION=wuchang.ai.supervisor.log
REGISTRY_CLASS=<class 'odoo.api.wuchang.ai.supervisor.log'>
REGISTRY_MODULE=odoo.api
REGISTRY_SOURCE=/usr/lib/python3/dist-packages/odoo/api.py

## Fresh Logs
2026-05-25 17:35:23,199 1 INFO ? odoo.service.server: HTTP service (werkzeug) running on 05d5febb8401:8069 
2026-05-25 17:35:24,537 1 WARNING postgres odoo.models: The model wuchang.ai.supervisor.log has no _description 
2026-05-25 17:35:24,658 1 INFO postgres odoo.modules.registry: Registry loaded in 1.459s 

## Web
WEB_OK=true

## Boundary
DB_WRITE=false
MODULE_INSTALL=false
SERVICE_RESTART=true
RAW_PII_TO_CLOUD=false
SECRET_READ=false
PATCH_SCOPE=container_runtime_all_source_occurrences
