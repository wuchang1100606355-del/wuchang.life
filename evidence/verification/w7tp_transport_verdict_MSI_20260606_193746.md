# W7TP Transport / Packaging Verification Verdict
host: MSI
time: 2026-06-06T19:37:46+08:00
source_report: runtime/reports/w7tp_transport_verify_MSI_20260606_193430.md
source_sha256: f9f39374c9b5abf2f12c601cd573adc0551b4674304864590b0afb6ed497924c
mode: readonly_verdict_only_no_ssh_no_service_change

## FINAL VERDICT
- MSI_LOCAL_TRANSPORT_PACKAGE: VERIFIED
- DEPLOY_PACKAGES: VERIFIED
- TOPOLOGY_BRAIN_TRANSFER_PACKAGE: VERIFIED
- FORMAL_TENSOR_RUNTIME_PACKAGE: VERIFIED
- STARTUP_STATE_PACKET: VERIFIED
- PATENT_POC_HELUO_D8: PROMOTED_TO_DIRECT_VERIFIED
- INTENT_DISCOVERY_NAMESPACE: VERIFIED_AS_SKELETON
- CORE_STP_NAMESPACE: NOT_PRESENT_ON_MSI
- BIN_WGTP_NAMESPACE: NOT_PRESENT_ON_MSI
- ROOT_XIAOJ_API_GATEWAY_FILES: NOT_PRESENT_ON_MSI

## REDTEAM NOTES
- docs/specs/7d_packet_v1.yaml and docs/specs/8d_encrypted_packet_v1.yaml are zero-byte files; treat as path placeholders, not content-complete specs.
- intent_discovery files are very small; treat as recovered skeleton modules until source logic is expanded or verified.
- SSH / 2222 is excluded from this verdict because transport packaging verification does not require remote ingress.
- Runtime ports and Docker containers prove local service surface is alive, not that every declared source path exists.

## VERIFIED SUMMARY
OK	configs/dev/w7tp_nl_to_7d_task_packet.template.json	bytes=1560 mtime=2026-05-28 00:20:57.110092492 +0800
OK	configs/packets/tri_party_7d_packet.template.json	bytes=3239 mtime=2026-05-27 13:43:03.394973990 +0800
OK	core/context/context_packet.py	bytes=1123 mtime=2026-05-03 22:39:14.558907277 +0800
OK	docs/specs/7d_packet_v1.yaml	bytes=0 mtime=2026-05-31 00:19:40.318499702 +0800
OK	docs/specs/8d_encrypted_packet_v1.yaml	bytes=0 mtime=2026-05-31 00:19:40.318499702 +0800
OK	docs/governance/W7TP_INDEXER_MANUAL_TRANSFER_CHECKLIST.md	bytes=1659 mtime=2026-05-27 13:31:48.454804382 +0800
OK	docs/governance/W7TP_NL_TO_7D_TASK_PACKET_GENERATOR.md	bytes=684 mtime=2026-05-28 00:20:57.110092492 +0800
OK	docs/governance/W7TP_TRI_PARTY_7D_PACKET_LANGUAGE_BRIDGE.md	bytes=3173 mtime=2026-05-27 13:43:03.152082926 +0800
OK	deploy/formal_runtime_pkg_v0_1/MANIFEST.md	bytes=2663 mtime=2026-05-11 20:29:47.564754300 +0800
OK	deploy/formal_runtime_pkg_v0_1/scripts/hash_manifest_v0_1.sh	bytes=1103 mtime=2026-05-11 20:29:47.561754000 +0800
OK	deploy/packages/taiji01_topology_brain_transfer_v0_1/README.md	bytes=507 mtime=2026-05-14 04:34:46.372712754 +0800
OK	deploy/packages/taiji01_topology_brain_transfer_v0_1/SHA256SUMS	bytes=443 mtime=2026-05-14 04:34:46.376712868 +0800
OK	deploy/packages/taiji01_topology_brain_transfer_v0_1/identity_allowlist.sample.json	bytes=554 mtime=2026-05-14 04:34:46.372712754 +0800
OK	deploy/packages/taiji_formal_tensor_runtime_v0_1_0/MANIFEST.json	bytes=1729 mtime=2026-05-11 20:33:46.544120600 +0800
OK	deploy/packages/taiji_formal_tensor_runtime_v0_1_0/HASH_SCRIPT.sh	bytes=637 mtime=2026-05-11 20:33:46.530120100 +0800
OK	jules_cloud_api.py	bytes=8904 mtime=2026-05-03 14:31:42.432812093 +0800
OK	jules_core_v21_2.py	bytes=4712 mtime=2026-04-30 03:06:29.036164200 +0800
OK	jules_core_v21_3.py	bytes=3851 mtime=2026-04-30 04:03:08.561087400 +0800
OK	jules_core_v21_4.py	bytes=3361 mtime=2026-04-30 09:10:42.240282300 +0800
OK	taiji_gateway.py	bytes=7616 mtime=2026-05-22 21:10:51.233259146 +0800
OK	eamtp_tipo_generator.py	bytes=14080 mtime=2026-05-27 10:26:27.081759177 +0800
OK	bin/w7tp_phase_sync_odoo.sh	bytes=1364 mtime=2026-06-03 16:39:53.446867640 +0800
OK	evidence/git/git_bundle_record_20260605_182104.md	bytes=247 mtime=2026-06-05 18:21:04.214949744 +0800
OK	W7TP_FIELD_ATLAS/runtime_status/latest_startup_state_packet.yaml	bytes=101 mtime=2026-06-06 10:43:19.414599337 +0800
OK	intent_discovery/coordinate_engine.py	bytes=78 mtime=2026-06-06 02:27:05.816377665 +0800
OK	intent_discovery/discovery_pipeline.py	bytes=84 mtime=2026-06-06 02:27:05.816377665 +0800
OK	intent_discovery/hash_engine.py	bytes=146 mtime=2026-06-06 02:27:05.816377665 +0800
OK	intent_discovery/intent_field_mapper.py	bytes=86 mtime=2026-06-06 02:23:18.722238396 +0800
OK	intent_discovery/intent_generation_system.py	bytes=298 mtime=2026-06-06 02:35:27.184169390 +0800
OK	intent_discovery/intent_goal_packet.py	bytes=85 mtime=2026-06-06 02:23:18.722238396 +0800
OK	intent_discovery/intent_goal_rebuild.py	bytes=86 mtime=2026-06-06 02:23:18.722238396 +0800
OK	intent_discovery/intent_state_coordinate.py	bytes=90 mtime=2026-06-06 02:23:18.722238396 +0800
OK	intent_discovery/intent_state_packet.py	bytes=86 mtime=2026-06-06 02:23:18.722238396 +0800
OK	intent_discovery/intent_state_rebuild.py	bytes=87 mtime=2026-06-06 02:23:18.722238396 +0800
OK	intent_discovery/tensor_feeder.py	bytes=77 mtime=2026-06-06 02:27:05.816377665 +0800
OK	intent_discovery/redteam_engine.py	bytes=96 mtime=2026-06-06 02:27:05.816377665 +0800
FOUND	patent_poc/w7tp_heluo_d8_packet_poc_v2.py	bytes=7253 mtime=2026-06-01 23:52:00.330488004 +0800

## REMAINING GAPS
GAP	core/stp/tensor_packet.py
GAP	core/stp/delta_packet.py
GAP	core/stp/packet_builder.py
GAP	core/stp/delta_reconstruction.py
GAP	XiaoJ_API_Gateway.py
GAP	XiaoJ_Local_Driver.py
GAP	bin/wgtp/wgtp-transfer
MISSING_DIR core/stp
MISSING_DIR bin/wgtp
