# Taiji Edge Gateway Systemd Takeover

timestamp: 20260602_114221
head: 557436e

target: taiji01
service: taiji_edge_gateway.service
manual_pid_before: 3479109
remote_log: evidence/server_handoff/systemd_takeover/taiji_edge_gateway_systemd_takeover_20260602_114221.txt

boundary:
- no DB write
- no Odoo module update
- no Docker restart
- no --delete
- exact PID kill only if it owned port 9002
- rollback manual runtime included if systemd health failed

result_line:
SYSTEMD_TAKEOVER_RESULT=PASS_SYSTEMD_OWNERSHIP
