# Untracked Intent Field Scan - taiji01

- host: taiji01
- repo: /home/taiji_admin/Taiji_Hub
- branch: main
- head: 3616f09
- time: 20260607_043617
- mode: readonly_scan_only

## Intent Field Basis

- active_packet: configs/intent_field/active/w7tp_intent_field_update_20260607_wuchang_gts_igc.yaml
- rule: Wuchang / GTS / IGC / XiaoJ / runtime evidence / community AI related files are candidates.
- hardwall: no delete, no move, no commit, no execution.

## Raw Untracked Items

- DUAL_NODE_RUNTIME_V1.txt
- core/xiaoj/compiler/
- core/xiaoj/completion/
- core/xiaoj/discovery/
- core/xiaoj/mapping/
- core/xiaoj/reconstruction/
- core/xiaoj/redteam/
- core/xiaoj/runtime.py
- core/xiaoj/stp/
- evidence/intent_field/untracked_intent_scan_taiji01_20260607_043617.md
- evidence/runtime_audit_20260605/
- evidence_generative_transport_history_20260606_084323.txt
- evidence_generative_transport_history_20260606_084331.txt
- sandbox_state/
- tensor_8d/space/

## Classified Scan

### REVIEW_CANDIDATE: DUAL_NODE_RUNTIME_V1.txt
- reason: dual-node runtime may be related to distributed compute and runtime replica.
- action: inspect content; decide MSI canonical vs taiji01 runtime.

### INCLUDE_CANDIDATE: core/xiaoj/compiler/
- reason: XiaoJ core runtime / compiler / discovery / mapping / reconstruction / redteam / STP path.
- action: inspect before commit; likely belongs to XiaoJ execution architecture.

### INCLUDE_CANDIDATE: core/xiaoj/completion/
- reason: XiaoJ core runtime / compiler / discovery / mapping / reconstruction / redteam / STP path.
- action: inspect before commit; likely belongs to XiaoJ execution architecture.

### INCLUDE_CANDIDATE: core/xiaoj/discovery/
- reason: XiaoJ core runtime / compiler / discovery / mapping / reconstruction / redteam / STP path.
- action: inspect before commit; likely belongs to XiaoJ execution architecture.

### INCLUDE_CANDIDATE: core/xiaoj/mapping/
- reason: XiaoJ core runtime / compiler / discovery / mapping / reconstruction / redteam / STP path.
- action: inspect before commit; likely belongs to XiaoJ execution architecture.

### INCLUDE_CANDIDATE: core/xiaoj/reconstruction/
- reason: XiaoJ core runtime / compiler / discovery / mapping / reconstruction / redteam / STP path.
- action: inspect before commit; likely belongs to XiaoJ execution architecture.

### INCLUDE_CANDIDATE: core/xiaoj/redteam/
- reason: XiaoJ core runtime / compiler / discovery / mapping / reconstruction / redteam / STP path.
- action: inspect before commit; likely belongs to XiaoJ execution architecture.

### INCLUDE_CANDIDATE: core/xiaoj/runtime.py
- reason: XiaoJ core runtime / compiler / discovery / mapping / reconstruction / redteam / STP path.
- action: inspect before commit; likely belongs to XiaoJ execution architecture.

### INCLUDE_CANDIDATE: core/xiaoj/stp/
- reason: XiaoJ core runtime / compiler / discovery / mapping / reconstruction / redteam / STP path.
- action: inspect before commit; likely belongs to XiaoJ execution architecture.

### UNKNOWN_REVIEW: evidence/intent_field/untracked_intent_scan_taiji01_20260607_043617.md
- reason: not matched by current intent field rules.
- action: manual inspect.

### INCLUDE_CANDIDATE: evidence/runtime_audit_20260605/
- reason: runtime audit or generative transport evidence.
- action: preserve; likely patent/evidence-chain relevant.

### INCLUDE_CANDIDATE: evidence_generative_transport_history_20260606_084323.txt
- reason: runtime audit or generative transport evidence.
- action: preserve; likely patent/evidence-chain relevant.

### INCLUDE_CANDIDATE: evidence_generative_transport_history_20260606_084331.txt
- reason: runtime audit or generative transport evidence.
- action: preserve; likely patent/evidence-chain relevant.

### HOLD_REVIEW: sandbox_state/
- reason: sandbox state may contain temporary/runtime/generated files.
- action: do not commit until classified by manifest/hash.

### INCLUDE_CANDIDATE: tensor_8d/space/
- reason: 8D space/state coordinate layer; related to State -> Coordinate -> Hash -> Packet.
- action: inspect schema and hash before commit.

## Next Safe Action

Run targeted inspection only. Do not git add all.

Recommended next groups:

1. core/xiaoj/
2. tensor_8d/space/
3. evidence/runtime_audit_20260605/ and evidence_generative_transport_history_*
4. DUAL_NODE_RUNTIME_V1.txt
5. sandbox_state/ hold
