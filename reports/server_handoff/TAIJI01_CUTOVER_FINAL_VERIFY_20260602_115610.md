# TAIJI01 Cutover Final Verify

timestamp: 20260602_115610
head: b32a5ebdea8d8462c27391ef8e3bb951f8664fcd
head_short: b32a5eb

tags:
TAIJI01_CUTOVER_PASS_20260602
TAIJI01_CUTOVER_TEMP_PASS_20260602
TAIJI01_GATEWAY_SYSTEMD_PASS_20260602

verify_log: evidence/server_handoff/final_cutover_verify/taiji01_final_verify_20260602_115610.txt
bundle: /home/taiji_admin/Taiji_Git_Bundles/20260602_115610_b32a5eb/taiji_hub_20260602_115610_b32a5eb.bundle
bundle_sha256: /home/taiji_admin/Taiji_Git_Bundles/20260602_115610_b32a5eb/taiji_hub_20260602_115610_b32a5eb.bundle.sha256
bundle_manifest: evidence/server_handoff/final_cutover_verify/git_bundle_manifest_20260602_115610.txt

status:
- taiji01 gateway systemd: PASS if healthz returns 200
- Odoo container: PASS if wuchang_os_odoo_18 running
- Postgres container: PASS if wuchang_os_pg running
- Git clean before bundle: PASS

not_executed:
- DB write
- Docker restart
- Odoo module update
- service restart
- secret read
