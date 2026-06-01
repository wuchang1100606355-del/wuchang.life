# TAIJI01 SERVER TRUTH PACKET
2026-05-31T21:08:53+08:00

## Host
MSI
taiji_admin
/home/taiji_admin/Taiji_Hub

## Docker
NAMES                             STATUS       PORTS
wuchang_os_odoo_18                Up 2 hours   127.0.0.1:8069->8069/tcp, 8071-8072/tcp
xiaoj-intent-field                Up 3 hours   0.0.0.0:9107->9107/tcp, [::]:9107->9107/tcp
wuchang_os_pg                     Up 3 hours   5432/tcp
taiji_syslog                      Up 3 hours   
taiji_worklist                    Up 3 hours   
taiji_audit                       Up 3 hours   
taiji_progress                    Up 3 hours   
taiji_voice_gateway               Up 3 hours   127.0.0.1:9201->9201/tcp
taiji_device_resilience_adapter   Up 3 hours   
taiji_pos_google_voice_tool       Up 3 hours   
taiji_claw_safe                   Up 3 hours   127.0.0.1:9004->9004/tcp
wuchang_gpu_brain                 Up 3 hours   11434/tcp

## Odoo Inspect
ConfigFiles=/home/taiji_admin/Taiji_Hub/Taiji_Odoo/docker-compose.yml
WorkingDir=/home/taiji_admin/Taiji_Hub/Taiji_Odoo
Mounts=[{"Type":"bind","Source":"/home/taiji_admin/Taiji_Hub/Taiji_Odoo/config/odoo.conf","Destination":"/etc/odoo/odoo.conf","Mode":"ro","RW":false,"Propagation":"rprivate"},{"Type":"bind","Source":"/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons","Destination":"/mnt/extra-addons","Mode":"rw","RW":true,"Propagation":"rprivate"},{"Type":"bind","Source":"/home/taiji_admin/Taiji_Hub/Taiji_Odoo/odoo_data","Destination":"/var/lib/odoo","Mode":"rw","RW":true,"Propagation":"rprivate"},{"Type":"bind","Source":"/mnt/c/Taiji_Runtime","Destination":"/mnt/taiji_runtime","Mode":"ro","RW":false,"Propagation":"rprivate"}]

## DB Volume
Mounts=[{"Type":"bind","Source":"/home/taiji_admin/Taiji_Hub/Taiji_Odoo/postgres_data","Destination":"/var/lib/postgresql/data","Mode":"rw","RW":true,"Propagation":"rprivate"}]

## Running Addons
/mnt/extra-addons/pm3_base/__manifest__.py
/mnt/extra-addons/pm3_runtime_sync.bak./__manifest__.py
/mnt/extra-addons/pm3_runtime_sync/__manifest__.py
/mnt/extra-addons/taiji_member_login/__manifest__.py
/mnt/extra-addons/wuchang_cafe_menu_options/__manifest__.py
/mnt/extra-addons/wuchang_core/__manifest__.py
/mnt/extra-addons/wuchang_fund_allocation/__manifest__.py
/mnt/extra-addons/wuchang_google_member_login/__manifest__.py
/mnt/extra-addons/wuchang_knowledge_sync/__manifest__.py
/mnt/extra-addons/wuchang_line_login/__manifest__.py
/mnt/extra-addons/wuchang_property_local_cloud/__manifest__.py
/mnt/extra-addons/wuchang_property_manpower_surface/__manifest__.py
/mnt/extra-addons/wuchang_wish_tree_coin/__manifest__.py

## PM3 Runtime Sync Check
### /home/taiji_01/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync
MISSING
### /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync
PRESENT
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/__init__.py
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/__manifest__.py
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/__pycache__/__init__.cpython-312.pyc
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/__pycache__/__manifest__.cpython-312.pyc
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/controllers/__init__.py
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/controllers/__pycache__/__init__.cpython-312.pyc
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/controllers/__pycache__/google_auth.cpython-312.pyc
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/controllers/__pycache__/line_auth.cpython-312.pyc
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/controllers/google_auth.py
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/controllers/line_auth.py
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/models/__init__.py
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/models/__pycache__/__init__.cpython-312.pyc
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/models/__pycache__/pm3_memory_index.cpython-312.pyc
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/models/__pycache__/res_users_proxy.cpython-312.pyc
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/models/pm3_memory_index.py
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/models/res_users_proxy.py
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/security/ir.model.access.csv
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_behavior_vector_database_views.xml
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_desensitized_dashboard_views.xml
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_fixed_vector_state_window_views.xml
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_memory_index_views.xml
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_vector_state_window_views.xml
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/web_login_templates.xml
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/web_login_templates.xml.disabled

## Server Decision
status: DO_NOT_ACCEPT_RUNTIME_CHANGE_YET
next_required:
  - compare_with_MSI_hash_ledger
  - produce_inbound_sync_plan
  - human_review_required
