# W7TP System Error Correction Plan
2026-05-31T20:31:19+08:00

## 1. Host Truth
MSI
taiji_admin
/home/taiji_admin/Taiji_Hub

## 2. Known Error Classes
E01_FIELD_DRIFT=MSI OAuth source != taiji01 running Odoo
E02_RUNTIME_SOURCE_CONFUSION=Taiji_Runtime contains OAuth source but running carrier lacks pm3_runtime_sync
E03_DATABASE_TARGET_CONFUSION=postgres DB queried before Odoo business DB confirmed
E04_SECRET_CONFIG_SPLIT=MSI OAuth config exists; taiji01 config not confirmed

## 3. PM3 Source Candidates
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync
/home/taiji_admin/Taiji_Runtime/odoo_addons/pm3_runtime_sync
/mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync

## 4. OAuth Source Files
/home/taiji_admin/.cache/rclone/vfs/gdrive/Project_Backups/Wuchang_V5_Before_Container_20260129_0214/wuchang_os/addons/muk_web/muk_web_theme/models/res_users.py
/home/taiji_admin/.cache/rclone/vfs/gdrive/Project_Backups/Wuchang_V5_Before_Container_20260129_0214/wuchang_os/addons/wuchang_core/models/res_users.py
/home/taiji_admin/.cache/rclone/vfs/gdrive/Rollback_Points/Backup_20260204_044907/wuchang_core/models/res_users.py
/home/taiji_admin/.cache/rclone/vfs/gdrive/Rollback_Points/Point_20260204_0347/wuchang_core/models/res_users.py
/home/taiji_admin/.cache/rclone/vfs/gdrive/Rollback_Points/RP_20260204_0605/wuchang_core/models/res_users.py
/home/taiji_admin/.cache/rclone/vfs/gdrive/backups/wuchang V6.0.0/downloads/MemoryCard_Export/Secure_Backup/wuchang_os/addons/muk_web/muk_web_theme/models/res_users.py
/home/taiji_admin/.cache/rclone/vfs/gdrive/backups/wuchang V6.0.0/downloads/MemoryCard_Export/Secure_Backup/wuchang_os/addons/wuchang_core/models/res_users.py
/home/taiji_admin/.cache/rclone/vfs/gdrive/backups/wuchang V6.0.0/wuchang_os/addons/muk_web/muk_web_theme/models/res_users.py
/home/taiji_admin/.cache/rclone/vfs/gdrive/backups/wuchang V6.0.0/wuchang_os/addons/wuchang_core/models/res_users.py
/home/taiji_admin/.cache/rclone/vfsMeta/gdrive/Project_Backups/Wuchang_V5_Before_Container_20260129_0214/wuchang_os/addons/muk_web/muk_web_theme/models/res_users.py
/home/taiji_admin/.cache/rclone/vfsMeta/gdrive/Project_Backups/Wuchang_V5_Before_Container_20260129_0214/wuchang_os/addons/wuchang_core/models/res_users.py
/home/taiji_admin/.cache/rclone/vfsMeta/gdrive/Rollback_Points/Backup_20260204_044907/wuchang_core/models/res_users.py
/home/taiji_admin/.cache/rclone/vfsMeta/gdrive/Rollback_Points/Point_20260204_0347/wuchang_core/models/res_users.py
/home/taiji_admin/.cache/rclone/vfsMeta/gdrive/Rollback_Points/RP_20260204_0605/wuchang_core/models/res_users.py
/home/taiji_admin/.cache/rclone/vfsMeta/gdrive/backups/wuchang V6.0.0/downloads/MemoryCard_Export/Secure_Backup/wuchang_os/addons/muk_web/muk_web_theme/models/res_users.py
/home/taiji_admin/.cache/rclone/vfsMeta/gdrive/backups/wuchang V6.0.0/downloads/MemoryCard_Export/Secure_Backup/wuchang_os/addons/wuchang_core/models/res_users.py
/home/taiji_admin/.cache/rclone/vfsMeta/gdrive/backups/wuchang V6.0.0/wuchang_os/addons/muk_web/muk_web_theme/models/res_users.py
/home/taiji_admin/.cache/rclone/vfsMeta/gdrive/backups/wuchang V6.0.0/wuchang_os/addons/wuchang_core/models/res_users.py
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync.bak./controllers/google_auth.py
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/controllers/google_auth.py
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/controllers/line_auth.py
/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/wuchang_core/models/res_users.py
/home/taiji_admin/Taiji_Hub/runtime/build/odoo_extra_addons_clean/wuchang_core/models/res_users.py
/home/taiji_admin/Taiji_Hub/runtime/build/odoo_extra_addons_phase0/wuchang_core/models/res_users.py
/home/taiji_admin/Taiji_Hub/runtime/build/odoo_extra_addons_phase2_ui/wuchang_core/models/res_users.py
/home/taiji_admin/Taiji_Hub/runtime/build/odoo_extra_addons_phase2c_warning_fix/wuchang_core/models/res_users.py
/home/taiji_admin/Taiji_Hub/runtime/reports/wuchang_core_pre_file_fix_backup_20260526_004908/models/res_users.py
/home/taiji_admin/Taiji_Hub/runtime/reports/wuchang_core_pre_final_xml_fix_backup_20260526_005016/models/res_users.py
/home/taiji_admin/Taiji_Hub/runtime/reports/wuchang_core_pre_xml_brutefix_backup_20260526_005125/models/res_users.py
/home/taiji_admin/Taiji_Runtime/line_auth.py
/home/taiji_admin/Taiji_Runtime/res_users.py
/home/taiji_admin/Taiji_Runtime/setup_odoo_secret_refs.py
/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/res_users.py
/mnt/c/Taiji_Runtime/docs/project/res_users.py
/mnt/c/Taiji_Runtime/google_auth.py
/mnt/c/Taiji_Runtime/line_auth.py
/mnt/c/Taiji_Runtime/member_identity_mapper.py
/mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/controllers/google_auth.py
/mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/controllers/line_auth.py
/mnt/c/Taiji_Runtime/res_users.py
/mnt/c/Taiji_Runtime/setup_odoo_secret_refs.py

## 5. Hash Manifest

### /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync
4074365d0d6d59de5ebed6406848d5a14b9640e4c538834b0c369d12098bd330  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/__init__.py
45e0555077a2dba4d966581711035e1de6eb31edf5df0af52eccd4c0c3d4b045  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/models/pm3_memory_index.py
5542f29d0e085567b05c750c97683d79851bd9b90dc4057f578d4ae4378b077e  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/views/pm3_vector_state_window_views.xml
6208643d872a6f22910ccb1ed2077851ff8be3f673395cc2495835171e957429  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/views/pm3_behavior_vector_database_views.xml
8c6dae5992d6707194951a1bb838dc904be04e6932767fe1747c61a442aa879f  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/views/pm3_fixed_vector_state_window_views.xml
8d2dc1605199fcac3f184507e84b42e1803f2c4818b54ad25b2bdcd06b854fa9  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/views/web_login_templates.xml
9eaa74619a41b1366f65eb7ebbd483f4831c0d91f0d8b7b2e601a49e0eec19cc  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/__manifest__.py
a25338824cef084eed628b8e8bb6d6ab270308c08234a0f7e765cd452e9caf48  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/models/res_users_proxy.py
a3db0968b0a3d1cefc79ab335a7977bae63f985a6c9ad2ce4dcd49f92c15fa4a  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/views/pm3_memory_index_views.xml
b0cb80eedbab11aae492b7a404e707819d84f1193e1e8a94e9f89ac72fb5ccbd  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/controllers/__init__.py
c8484a60879f37bf69b33682f4259127f916ab97f61285703d38314185e3e16e  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/views/pm3_desensitized_dashboard_views.xml
ccff6da399e72df9c9827eef8179544605db75cdc24cc1c4716ad813205d7e7a  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/models/__init__.py
d8a06b3db75374645ceb0155e3d4458e20920f38f7974c9414818be7558b9b38  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/controllers/line_auth.py
ffe0449ecad6047d3a7d05886d57800b8090f2e5269fcc213295bd180957e042  /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync/controllers/google_auth.py

### /home/taiji_admin/Taiji_Runtime/odoo_addons/pm3_runtime_sync
025bdf9ff1936e258642106f7c5c9f9b7aeee18d5dc8a8e04c019210f6384671  /home/taiji_admin/Taiji_Runtime/odoo_addons/pm3_runtime_sync/views/pm3_fixed_vector_state_window_views.xml
3298e2cd0c7e5c477138d38fe6fafe59a6260a3651e1df9ca002363e23a351f6  /home/taiji_admin/Taiji_Runtime/odoo_addons/pm3_runtime_sync/__init__.py
3aeb543dc04f781d84e2c6fc31b471a65966d09d19af66da5a86ff3fc1d3e022  /home/taiji_admin/Taiji_Runtime/odoo_addons/pm3_runtime_sync/views/pm3_behavior_vector_database_views.xml
45e0555077a2dba4d966581711035e1de6eb31edf5df0af52eccd4c0c3d4b045  /home/taiji_admin/Taiji_Runtime/odoo_addons/pm3_runtime_sync/models/pm3_memory_index.py
6668deff8a68520b6acdee371c715883b74853e5bf2c4a7515c1f5750185382a  /home/taiji_admin/Taiji_Runtime/odoo_addons/pm3_runtime_sync/views/pm3_vector_state_window_views.xml
690f5f519f236010ec4fec779a0a237ec59c2073cb9bef568ad2ae484ab0046a  /home/taiji_admin/Taiji_Runtime/odoo_addons/pm3_runtime_sync/views/pm3_memory_index_views.xml
6c58188544ee082196ca2598af061d4a97db0582d9be1f41af6ea9311c8f86d2  /home/taiji_admin/Taiji_Runtime/odoo_addons/pm3_runtime_sync/__manifest__.py
ffd25042b91061320b01b3b1192ab6e1d0d9319603bf3aaab7e2316a181d51c4  /home/taiji_admin/Taiji_Runtime/odoo_addons/pm3_runtime_sync/views/pm3_desensitized_dashboard_views.xml

### /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync
1e7b85f9537b1dfe61ede4aa53a6dbfaa49f540561f5b16e8efd65812a5ef9d4  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/controllers/line_auth.py
4074365d0d6d59de5ebed6406848d5a14b9640e4c538834b0c369d12098bd330  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/__init__.py
45e0555077a2dba4d966581711035e1de6eb31edf5df0af52eccd4c0c3d4b045  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/models/pm3_memory_index.py
5542f29d0e085567b05c750c97683d79851bd9b90dc4057f578d4ae4378b077e  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_vector_state_window_views.xml
6208643d872a6f22910ccb1ed2077851ff8be3f673395cc2495835171e957429  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_behavior_vector_database_views.xml
8c6dae5992d6707194951a1bb838dc904be04e6932767fe1747c61a442aa879f  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_fixed_vector_state_window_views.xml
8d2dc1605199fcac3f184507e84b42e1803f2c4818b54ad25b2bdcd06b854fa9  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/web_login_templates.xml
9eaa74619a41b1366f65eb7ebbd483f4831c0d91f0d8b7b2e601a49e0eec19cc  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/__manifest__.py
a25338824cef084eed628b8e8bb6d6ab270308c08234a0f7e765cd452e9caf48  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/models/res_users_proxy.py
a3db0968b0a3d1cefc79ab335a7977bae63f985a6c9ad2ce4dcd49f92c15fa4a  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_memory_index_views.xml
b0cb80eedbab11aae492b7a404e707819d84f1193e1e8a94e9f89ac72fb5ccbd  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/controllers/__init__.py
c8484a60879f37bf69b33682f4259127f916ab97f61285703d38314185e3e16e  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/views/pm3_desensitized_dashboard_views.xml
ccff6da399e72df9c9827eef8179544605db75cdc24cc1c4716ad813205d7e7a  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/models/__init__.py
ffe0449ecad6047d3a7d05886d57800b8090f2e5269fcc213295bd180957e042  /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync/controllers/google_auth.py

### /home/taiji_01/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync
MISSING

## 6. Running Odoo Carrier Check
Name=/wuchang_os_odoo_18
ConfigFiles=/home/taiji_admin/Taiji_Hub/Taiji_Odoo/docker-compose.yml
WorkingDir=/home/taiji_admin/Taiji_Hub/Taiji_Odoo
Mounts=[{"Type":"bind","Source":"/mnt/c/Taiji_Runtime","Destination":"/mnt/taiji_runtime","Mode":"ro","RW":false,"Propagation":"rprivate"},{"Type":"bind","Source":"/home/taiji_admin/Taiji_Hub/Taiji_Odoo/config/odoo.conf","Destination":"/etc/odoo/odoo.conf","Mode":"ro","RW":false,"Propagation":"rprivate"},{"Type":"bind","Source":"/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons","Destination":"/mnt/extra-addons","Mode":"rw","RW":true,"Propagation":"rprivate"},{"Type":"bind","Source":"/home/taiji_admin/Taiji_Hub/Taiji_Odoo/odoo_data","Destination":"/var/lib/odoo","Mode":"rw","RW":true,"Propagation":"rprivate"}]

## 7. Running Addons
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

## 8. Correction Plan Only
PLAN_ONLY:
  1_freeze_evidence: done_by_this_report
  2_choose_canonical_source: pending_human_review
  3_generate_sync_file_list: pending
  4_compare_before_copy: required
  5_no_copy_until_approved: true
  6_no_restart_until_approved: true

## 9. Red Team Reflection
negative_effects:
  - 可能把開發副本誤認為正式來源
  - 可能把 MSI OAuth 設定錯同步到 taiji01
  - 可能造成兩台 Odoo 模組版本不一致
  - 若未確認 DB，可能修到錯資料庫
  - 若直接部署，可能覆蓋 taiji01 現有穩定模組

mitigation:
  - 先做 hash manifest
  - 先做 universe_packet 標記
  - 只產出 sync plan
  - 人審後才允許 copy
  - copy 後仍需 sandbox/test，不直接正式啟用
