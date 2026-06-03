# taiji01 pre-domain inventory 20260531_112422

## host
taiji01
/home/taiji_admin/Taiji_Hub

## disk
Filesystem                         Size  Used Avail Use% Mounted on
/dev/mapper/ubuntu--vg-ubuntu--lv  226G  103G  113G  48% /
Filesystem                         Size  Used Avail Use% Mounted on
/dev/mapper/ubuntu--vg-ubuntu--lv  226G  103G  113G  48% /

## top level
d ./bin
d ./config
d ./node_inbox
d ./node_inbox/patent_v0_8_handoff_20260520
d ./sync_agents
d ./Taiji_Governance
d ./Taiji_Governance/inbox
d ./Taiji_Governance/logs
d ./Taiji_Governance/system_info
d ./Taiji_Odoo
d ./Taiji_Odoo/manifests
d ./Taiji_Odoo/pm3_base
f ./bin/taiji-distributed-admin-sync-check
f ./bin/taiji-new-boss-boot-check
f ./bin/taiji-new-boss-session
f ./config/distributed_admin_authority.env
f ./sync_agents/global_status_probe.sh
f ./Taiji_Governance/taiji01_pre_domain_inventory_20260531_112422.md
f ./Taiji_Odoo/pm3_reload.sh

## archived / backup / old candidates
2026-05-15 05:10 929 ./Taiji_Odoo/pm3_base/controllers/edge_api.py.bak

## compose / env / service candidates

## odoo files
d 2026-05-15 01:08 4096 Taiji_Odoo/pm3_base/views
d 2026-05-15 04:37 4096 Taiji_Odoo/pm3_base/security
d 2026-05-15 04:55 4096 Taiji_Odoo/pm3_base/models
d 2026-05-15 05:08 4096 Taiji_Odoo/pm3_base
d 2026-05-15 05:22 4096 Taiji_Odoo/pm3_base/controllers
d 2026-05-15 05:54 4096 Taiji_Odoo/manifests
d 2026-05-15 05:55 4096 Taiji_Odoo
f 2026-05-15 04:36 29 Taiji_Odoo/pm3_base/models/__init__.py
f 2026-05-15 04:36 714 Taiji_Odoo/pm3_base/models/packet_history.py
f 2026-05-15 04:37 297 Taiji_Odoo/pm3_base/security/ir.model.access.csv
f 2026-05-15 05:00 279 Taiji_Odoo/pm3_base/__manifest__.py
f 2026-05-15 05:10 929 Taiji_Odoo/pm3_base/controllers/edge_api.py
f 2026-05-15 05:10 929 Taiji_Odoo/pm3_base/controllers/edge_api.py.bak
f 2026-05-15 05:17 229 Taiji_Odoo/pm3_reload.sh
f 2026-05-15 05:40 23 Taiji_Odoo/pm3_base/controllers/__init__.py
f 2026-05-15 05:40 34 Taiji_Odoo/pm3_base/__init__.py
f 2026-05-15 05:54 305 Taiji_Odoo/manifests/pm3_base_manifest.txt
f 2026-05-15 05:54 833 Taiji_Odoo/manifests/pm3_base_sha256.txt

## docker ps
NAMES                                      STATUS      PORTS
wuchang_os_pg                              Up 8 days   5432/tcp
wuchang_os_odoo_18                         Up 8 days   0.0.0.0:8069->8069/tcp, [::]:8069->8069/tcp, 8071-8072/tcp
quarantine_wuchang_os_pg_20260508_200520   Up 8 days   5432/tcp

## docker compose labels
Name=/wuchang_os_odoo_18
Image=odoo:18.0
Created=2026-05-08T19:43:19.377289559Z
ConfigFiles=/home/taiji_01/Taiji_Hub/Taiji_Odoo/docker-compose.yml
WorkingDir=/home/taiji_01/Taiji_Hub/Taiji_Odoo
Service=web
Mounts=[{"Type":"bind","Source":"/home/taiji_01/Taiji_Hub/Taiji_Odoo/addons","Destination":"/mnt/extra-addons","Mode":"rw","RW":true,"Propagation":"rprivate"},{"Type":"bind","Source":"/home/taiji_01/Taiji_Hub/Taiji_Odoo/odoo_data","Destination":"/var/lib/odoo","Mode":"rw","RW":true,"Propagation":"rprivate"}]

## systemd user taiji/open/odoo

## ports
LISTEN 0      1024                      0.0.0.0:8069       0.0.0.0:*          
LISTEN 0      1024                         [::]:8069          [::]:*          
LISTEN 0      128                             *:8080             *:*          
LISTEN 0      1024                            *:11434            *:*          
