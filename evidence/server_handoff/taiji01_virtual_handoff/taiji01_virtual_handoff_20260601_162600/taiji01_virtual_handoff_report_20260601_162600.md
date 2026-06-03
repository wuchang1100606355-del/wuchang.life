# taiji01 虛擬交接回報包

timestamp: 2026-06-01T16:26:00+00:00
host: taiji01
whoami: taiji_admin
pwd: /home/taiji_admin/Taiji_Node_Evidence_Outbox/server_handoff

## Governance
virtual_handoff_from_taiji01: PASS
runtime_promotion: NO_GO
db_write: NO_GO
service_restart: NO_GO
secret_read: NO_GO
docker_mutation: NO_GO

## Admin Identity
uid=1002(taiji_admin) gid=1003(taiji_admin) groups=1003(taiji_admin),27(sudo),988(docker),1005(taiji_full_admins)

## Community User Boundary
uid=1000(taiji_01) gid=1000(taiji_01) groups=1000(taiji_01),4(adm),24(cdrom),30(dip),46(plugdev),987(ollama),1002(autologin),1004(taiji_community_writers)

## Docker Runtime Readonly Snapshot
NAMES                                      STATUS       PORTS
wuchang_os_pg                              Up 10 days   5432/tcp
wuchang_os_odoo_18                         Up 10 days   0.0.0.0:8069->8069/tcp, [::]:8069->8069/tcp, 8071-8072/tcp
quarantine_wuchang_os_pg_20260508_200520   Up 10 days   5432/tcp

## Container Safe Inspect
Name=/wuchang_os_odoo_18 Status=running StartedAt=2026-05-22T12:51:43.192405357Z RestartCount=0
Name=/wuchang_os_pg Status=running StartedAt=2026-05-22T12:51:43.19403772Z RestartCount=0

## Git Detection
not_git_repository

## System Resource
Filesystem                         Size  Used Avail Use% Mounted on
/dev/mapper/ubuntu--vg-ubuntu--lv  226G  103G  113G  48% /
               total        used        free      shared  buff/cache   available
Mem:            23Gi       1.7Gi        14Gi       199Mi       7.8Gi        21Gi
Swap:          4.0Gi          0B       4.0Gi
