# PM3 Runtime Sync Sandbox Validation
2026-05-31T20:39:05+08:00

## Source
/mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync

## Sandbox
runtime/sandbox/odoo_sync_validation/pm3_runtime_sync

## File Count
25

## Hash Manifest
4074365d0d6d59de5ebed6406848d5a14b9640e4c538834b0c369d12098bd330  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/__init__.py
45e0555077a2dba4d966581711035e1de6eb31edf5df0af52eccd4c0c3d4b045  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/models/pm3_memory_index.py
5542f29d0e085567b05c750c97683d79851bd9b90dc4057f578d4ae4378b077e  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/views/pm3_vector_state_window_views.xml
6208643d872a6f22910ccb1ed2077851ff8be3f673395cc2495835171e957429  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/views/pm3_behavior_vector_database_views.xml
8c6dae5992d6707194951a1bb838dc904be04e6932767fe1747c61a442aa879f  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/views/pm3_fixed_vector_state_window_views.xml
8d2dc1605199fcac3f184507e84b42e1803f2c4818b54ad25b2bdcd06b854fa9  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/views/web_login_templates.xml
9eaa74619a41b1366f65eb7ebbd483f4831c0d91f0d8b7b2e601a49e0eec19cc  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/__manifest__.py
a25338824cef084eed628b8e8bb6d6ab270308c08234a0f7e765cd452e9caf48  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/models/res_users_proxy.py
a3db0968b0a3d1cefc79ab335a7977bae63f985a6c9ad2ce4dcd49f92c15fa4a  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/views/pm3_memory_index_views.xml
b0cb80eedbab11aae492b7a404e707819d84f1193e1e8a94e9f89ac72fb5ccbd  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/controllers/__init__.py
c8484a60879f37bf69b33682f4259127f916ab97f61285703d38314185e3e16e  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/views/pm3_desensitized_dashboard_views.xml
ccff6da399e72df9c9827eef8179544605db75cdc24cc1c4716ad813205d7e7a  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/models/__init__.py
d8a06b3db75374645ceb0155e3d4458e20920f38f7974c9414818be7558b9b38  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/controllers/line_auth.py
ffe0449ecad6047d3a7d05886d57800b8090f2e5269fcc213295bd180957e042  runtime/sandbox/odoo_sync_validation/pm3_runtime_sync/controllers/google_auth.py

## Manifest Syntax
MANIFEST_PY_OK

## Python Syntax
PYTHON_SYNTAX_OK

## XML Syntax
XML_OK

## Red Team Reflection
negative_effects:
  - sandbox validation only proves syntax, not full Odoo install success
  - XML parse OK does not prove Odoo view inheritance correctness
  - secret refs are intentionally not validated here
  - taiji01 addon path and DB state may still differ

mitigation:
  - next step requires Odoo dry-run/import check
  - no copy to taiji01 yet
  - no restart
  - no DB write
