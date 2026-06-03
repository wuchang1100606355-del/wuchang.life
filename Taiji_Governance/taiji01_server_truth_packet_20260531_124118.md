# TAIJI01 SERVER TRUTH PACKET
2026-05-31T12:41:18+00:00

## D1 Identity
taiji01
taiji_admin
/home/taiji_admin/Taiji_Hub

## D2 Server Plan
plan_id: SERVER_VIEW_CORRECTION_PLAN_V1

status: PLAN_ONLY

d1_identity:
  host_role: taiji01_stable_runtime_server
  mode: plan_only
  no_deploy: true
  no_restart: true
  no_db_write: true
  no_secret_read: true

d2_intent:
  goal:
    - confirm_server_state_from_taiji01_perspective
    - prevent_MSI_development_state_from_overwriting_taiji01
    - establish_server_acceptance_gates
    - treat_sync_as_inbound_candidate_not_command

d3_server_truth:
  server_identity:
    host: taiji01
    expected_admin_root: /home/taiji_admin/Taiji_Hub
    expected_runtime_carrier: /home/taiji_01/Taiji_Hub/Taiji_Odoo
  server_policy:
    stable_runtime_first: true
    inbound_sync_requires_validation: true
    no_dual_master: true

d4_server_correction_flow:
  - capture_server_startup_packet
  - inspect_running_odoo_container
  - inspect_running_addons
  - inspect_database_volume
  - compare_against_inbound_plan
  - create_server_acceptance_report
  - require_human_review_before_copy
  - require_backup_before_restart

d5_acceptance_gates:
  G1_SOURCE_DECLARED:
    required: true
    rule: inbound_package_must_declare_source_universe_and_hash_manifest
  G2_NO_SECRET_SYNC:
    required: true
    rule: secrets_and_raw_env_values_must_not_be_copied
  G3_ADDON_STATIC_PASS:
    required: true
    rule: manifest_python_xml_must_pass_sandbox_validation
  G4_DB_COMPATIBILITY:
    required: true
    rule: odoo_db_name_and_installed_modules_must_be_confirmed_before_module_install_or_update
  G5_ROLLBACK_READY:
    required: true
    rule: backup_or_restore_point_must_exist_before_runtime_change
  G6_HUMAN_APPROVAL:
    required: true
    rule: no_copy_restart_deploy_without_explicit_approval

d6_governance:
  allowed_now:
    - docker_inspect
    - docker_exec_readonly
    - find
    - grep
    - sha256sum
    - write_server_acceptance_report
  forbidden_now:
    - copy_into_runtime_addons
    - docker_compose_up
    - restart_odoo
    - change_db
    - read_or_print_secrets
    - domain_deploy

d7_server_outputs:
  - server_truth_packet
  - server_addon_inventory
  - server_db_volume_map
  - server_acceptance_gate_report
  - inbound_sync_risk_report

d8_red_team_reflection:
  negative_effects:
    - server_side_policy_may_slow_down_sync
    - MSI_available_features_may_not_go_live_immediately
    - taiji01_may_drift_further_if_never_accepts_updates
    - server_validation_does_not_guarantee_oauth_console_or_dns_readiness
  mitigation:
    - staged_acceptance
    - code_only_no_secret_sync
    - sandbox_first_no_runtime_copy
    - backup_before_runtime_copy
    - restart_requires_separate_approval

## D3 Docker Running Truth
NAMES                                      STATUS      PORTS
wuchang_os_pg                              Up 9 days   5432/tcp
wuchang_os_odoo_18                         Up 9 days   0.0.0.0:8069->8069/tcp, [::]:8069->8069/tcp, 8071-8072/tcp
quarantine_wuchang_os_pg_20260508_200520   Up 9 days   5432/tcp

## D4 Odoo Container Inspect
Name=/wuchang_os_odoo_18
ConfigFiles=/home/taiji_01/Taiji_Hub/Taiji_Odoo/docker-compose.yml
WorkingDir=/home/taiji_01/Taiji_Hub/Taiji_Odoo
Mounts=[{"Type":"bind","Source":"/home/taiji_01/Taiji_Hub/Taiji_Odoo/addons","Destination":"/mnt/extra-addons","Mode":"rw","RW":true,"Propagation":"rprivate"},{"Type":"bind","Source":"/home/taiji_01/Taiji_Hub/Taiji_Odoo/odoo_data","Destination":"/var/lib/odoo","Mode":"rw","RW":true,"Propagation":"rprivate"}]
Env=["USER=odoo","PASSWORD=***MASKED***","HOST=db","PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin","LANG=en_US.UTF-8","ODOO_VERSION=18.0","ODOO_RC=/etc/odoo/odoo.conf"]

## D5 DB Container Inspect
Name=/wuchang_os_pg
Mounts=[{"Type":"volume","Name":"taiji_odoo_odoo-db-data","Source":"/var/lib/docker/volumes/taiji_odoo_odoo-db-data/_data","Destination":"/var/lib/postgresql/data","Driver":"local","Mode":"rw","RW":true,"Propagation":""}]
Env=["POSTGRES_USER=odoo","POSTGRES_DB=postgres","POSTGRES_PASSWORD=***MASKED***","PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/lib/postgresql/15/bin","GOSU_VERSION=1.19","LANG=en_US.utf8","PG_MAJOR=15","PG_VERSION=15.17-1.pgdg13+1","PGDATA=/var/lib/postgresql/data"]

## D6 Running Addons In Container
/mnt/extra-addons/wuchang_association_member_trust/__manifest__.py
/mnt/extra-addons/wuchang_cafe_ai_gateway/__manifest__.py
/mnt/extra-addons/wuchang_cafe_menu_options/__manifest__.py
/mnt/extra-addons/wuchang_core/__manifest__.py

## D7 Runtime Carrier Host Addons
/home/taiji_01/Taiji_Hub/Taiji_Odoo/addons/wuchang_association_member_trust/__manifest__.py
/home/taiji_01/Taiji_Hub/Taiji_Odoo/addons/wuchang_cafe_ai_gateway/__manifest__.py
/home/taiji_01/Taiji_Hub/Taiji_Odoo/addons/wuchang_cafe_menu_options/__manifest__.py
/home/taiji_01/Taiji_Hub/Taiji_Odoo/addons/wuchang_core/__manifest__.py

## D8 PM3 Presence

### /home/taiji_01/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync
MISSING

### /home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/pm3_runtime_sync
MISSING

### /mnt/c/Taiji_Runtime/odoo_addons/pm3_runtime_sync
MISSING

## D9 Server Acceptance Gate
G1_SOURCE_DECLARED: PENDING
G2_NO_SECRET_SYNC: PASS_POLICY
G3_ADDON_STATIC_PASS: PENDING
G4_DB_COMPATIBILITY: PENDING
G5_ROLLBACK_READY: PENDING
G6_HUMAN_APPROVAL: PENDING

server_decision:
  status: DO_NOT_ACCEPT_RUNTIME_CHANGE_YET
  reason: server truth must be compared against inbound sync package first

## D10 Red Team Reflection
negative_effects:
  - taiji01 may remain behind MSI if acceptance gates are too strict
  - if server env differs from MSI, OAuth module may install but fail later
  - masking env prevents accidental secret leak but may hide missing variable details
mitigation:
  - produce hash diff packet
  - validate addon in sandbox first
  - do not sync secrets
  - require explicit approval before runtime copy or restart
