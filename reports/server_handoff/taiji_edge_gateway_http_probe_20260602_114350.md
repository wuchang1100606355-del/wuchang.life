# Taiji Edge Gateway HTTP Probe

timestamp: 20260602_114350
head: 4f37d00

remote_log: evidence/server_handoff/systemd_takeover/taiji_edge_gateway_http_probe_20260602_114350.txt

interpretation:
- {"detail":"Not Found"} means HTTP server is alive.
- /docs not existing is not a runtime failure.
- liveness should be based on port 9002 responding, not only /docs.

boundary:
- no DB write
- no Docker restart
- no Odoo module update
- no service restart
- readonly probe only
