# Global Universe Cutover Broadcast

timestamp: 20260602_022110
head: 23b344b

broadcast: W7TP_FIELD_ATLAS/global_broadcast/GLOBAL_UNIVERSE_BROADCAST_20260602_022110.yaml
packet: Taiji_Intent_Packets/global_broadcast/GLOBAL_UNIVERSE_CUTOVER_PACKET_20260602_022110.yaml
governance: Taiji_Governance/global_broadcast/GLOBAL_UNIVERSE_CUTOVER_GOVERNANCE_20260602_022110.yaml
sha256: evidence/server_handoff/global_broadcast/global_universe_broadcast_20260602_022110.sha256

result: GLOBAL_LOCAL_UNIVERSE_BROADCAST_WRITTEN

scope:
- W7TP_FIELD_ATLAS
- Taiji_Intent_Packets
- Taiji_Governance
- evidence/server_handoff
- reports/server_handoff

not_executed:
- DB write
- cloud push
- secret read
- personal data export
- Docker restart
- Odoo module update
