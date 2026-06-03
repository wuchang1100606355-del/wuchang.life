# WUCHANG_UNIVERSE_MISPLACED_FILE_PACKET

D1_IDENTITY:
  owner: CHIANG_CHENG_LUNG
  mode: fault_tolerant_inventory
  action: classify_only
  no_move: true
  no_delete: true
  no_deploy: true
  no_restart: true
  no_secret_read: true

D2_INTENT:
  purpose: mark files/directories that are in the wrong universe position
  goal: prevent MSI / Taiji_Runtime / taiji01 / Odoo / router domains from being confused

D3_CURRENT_TRUTH:
  taiji01_running_odoo:
    path: /home/taiji_01/Taiji_Hub/Taiji_Odoo
    addons:
      - wuchang_core
      - wuchang_association_member_trust
      - wuchang_cafe_ai_gateway
      - wuchang_cafe_menu_options
    missing:
      - pm3_runtime_sync
      - google_auth.py
      - line_auth.py

  msi_runtime_oauth_source:
    path: /mnt/c/Taiji_Runtime
    observed_files:
      - google_auth.py
      - line_auth.py
      - res_users.py
      - member_identity_mapper.py
      - setup_odoo_secret_refs.py
    role: likely_oauth_source_universe

  msi_odoo_runtime:
    path: /home/taiji_admin/Taiji_Hub/Taiji_Odoo
    role: oauth_development_carrier

D4_UNIVERSE_MAP:
  U01_ROUTER_FIELD:
    path_or_host: 192.168.50.1
    role: network_boundary
    warning: do_not_treat_as_odoo_source

  U02_MSI_TAIJI_RUNTIME:
    path_or_host: /mnt/c/Taiji_Runtime
    role: runtime_source_and_oauth_seed
    canonical_status: candidate_source

  U03_MSI_TAIJI_HUB:
    path_or_host: /home/taiji_admin/Taiji_Hub
    role: MSI development hub
    canonical_status: candidate_development_hub

  U04_TAIJI01_TAIJI_HUB:
    path_or_host: /home/taiji_admin/Taiji_Hub
    role: taiji01 admin governance hub
    canonical_status: node_governance_hub

  U05_TAIJI01_RUNNING_ODOO:
    path_or_host: /home/taiji_01/Taiji_Hub/Taiji_Odoo
    role: currently running Odoo carrier
    canonical_status: running_carrier_without_oauth

D5_MISPLACED_FILE_RULES:
  misplaced_if:
    - oauth files exist in Taiji_Runtime but not in running Odoo addons
    - pm3_runtime_sync exists on MSI but not on taiji01
    - same container name points to different host paths
    - postgres database queried without confirming actual Odoo db name
    - router/NAT state is treated as application deployment proof

D6_GOVERNANCE:
  allowed:
    - readonly grep
    - readonly find
    - docker inspect
    - docker exec read-only shell checks
    - create governance markdown note
  forbidden:
    - moving files
    - deleting files
    - docker compose up
    - service restart
    - domain deployment
    - secret printing
    - DB write or wipe

D7_NEXT_VALIDATION:
  required_checks:
    - identify MSI pm3_runtime_sync source path
    - identify taiji01 missing addon gap
    - identify exact Odoo database name
    - compare MSI docker inspect vs taiji01 docker inspect
    - produce sync plan only

D8_TAMPER_BOUNDARY:
  status: evidence_preservation
  rule: any file relocation must be converted to plan-only until human approval
