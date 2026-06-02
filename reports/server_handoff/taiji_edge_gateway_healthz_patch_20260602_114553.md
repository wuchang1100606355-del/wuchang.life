# Taiji Edge Gateway Healthz Patch

timestamp: 20260602_114553
target: legacy_core/taiji_unified_gateway_edge.py
backup: evidence/server_handoff/systemd_takeover/taiji_unified_gateway_edge_pre_healthz_20260602_114553.py

purpose:
- Add explicit /healthz route so HTTP liveness returns 200 instead of relying on 404 root response.

boundary:
- no DB write
- no Odoo module update
- no Docker restart
- only gateway python file patched
