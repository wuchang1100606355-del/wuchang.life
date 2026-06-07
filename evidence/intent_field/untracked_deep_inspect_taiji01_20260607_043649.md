# Untracked Deep Inspect - taiji01

- host: taiji01
- head: 3616f09
- mode: readonly_deep_inspect
- time: 20260607_043649

## 1. core/xiaoj inventory
```
core/xiaoj/compiler/__pycache__/tensor_compiler.cpython-312.pyc | lines=11 | bytes=990
core/xiaoj/compiler/tensor_compiler.py | lines=14 | bytes=483
core/xiaoj/completion/gap_analysis.py | lines=18 | bytes=296
core/xiaoj/completion/intent_completion.py | lines=65 | bytes=1224
core/xiaoj/completion/__pycache__/gap_analysis.cpython-312.pyc | lines=4 | bytes=659
core/xiaoj/completion/__pycache__/intent_completion.cpython-312.pyc | lines=17 | bytes=1831
core/xiaoj/discovery/__init__.py | lines=0 | bytes=0
core/xiaoj/discovery/intent_discovery.py | lines=18 | bytes=374
core/xiaoj/discovery/__pycache__/__init__.cpython-312.pyc | lines=1 | bytes=157
core/xiaoj/discovery/__pycache__/intent_discovery.cpython-312.pyc | lines=14 | bytes=914
core/xiaoj/__init__.py | lines=0 | bytes=0
core/xiaoj/intent_manager.py | lines=20 | bytes=572
core/xiaoj/mapping/intent_taxonomy.py | lines=15 | bytes=258
core/xiaoj/mapping/__pycache__/intent_taxonomy.cpython-312.pyc | lines=3 | bytes=462
core/xiaoj/mapping/__pycache__/w7tp_to_stp.cpython-312.pyc | lines=1 | bytes=594
core/xiaoj/mapping/w7tp_to_stp.py | lines=26 | bytes=338
core/xiaoj/__pycache__/__init__.cpython-312.pyc | lines=1 | bytes=147
core/xiaoj/__pycache__/runtime.cpython-312.pyc | lines=6 | bytes=816
core/xiaoj/reconstruction/intent_reconstruction.py | lines=32 | bytes=860
core/xiaoj/reconstruction/__pycache__/intent_reconstruction.cpython-312.pyc | lines=10 | bytes=1417
core/xiaoj/redteam/__pycache__/redteam_check.cpython-312.pyc | lines=9 | bytes=513
core/xiaoj/redteam/redteam_check.py | lines=10 | bytes=195
core/xiaoj/runtime.py | lines=11 | bytes=258
core/xiaoj/stp/__pycache__/stp_bridge.cpython-312.pyc | lines=13 | bytes=902
core/xiaoj/stp/stp_bridge.py | lines=25 | bytes=520
```

## 2. tensor_8d/space inventory
```
tensor_8d/space/coordinate.py | lines=24 | bytes=444
tensor_8d/space/__pycache__/coordinate.cpython-312.pyc | lines=13 | bytes=1015
```

## 3. evidence inventory
```
evidence/runtime_audit_20260605/runtime_scan.txt
-rw-rw-r-- 1 taiji_admin taiji_admin 56279 Jun  6 08:43 evidence_generative_transport_history_20260606_084323.txt
-rw-rw-r-- 1 taiji_admin taiji_admin 56400 Jun  6 08:43 evidence_generative_transport_history_20260606_084331.txt
```

## 4. DUAL_NODE_RUNTIME_V1 preview
```
DUAL_NODE_RUNTIME_V1
GovernanceNode=taiji01
ComputeNode=MSI
MSI_Tailscale=100.107.187.77
OLLAMA=http://100.107.187.77:11434
FrontBrain=OK
BackBrain=OK
RTX4070=OK
W7TP_Mode=Governance_Compute_Separation
```

## 5. sandbox_state inventory hold
```
sandbox_state/status.yaml | lines=1 | bytes=42
```

## 6. secret risk keyword scan
```
evidence/runtime_audit_20260605/runtime_scan.txt:71:4120178 4120154  0.0  0.4 /usr/bin/python3 /usr/bin/odoo --db_host db --db_port 5432 --db_user odoo --db_password taiji_secret
evidence/runtime_audit_20260605/runtime_scan.txt:81:4120178 4120154  0.0  0.4 /usr/bin/python3 /usr/bin/odoo --db_host db --db_port 5432 --db_user odoo --db_password taiji_secret
```

## 7. git status target
```
?? DUAL_NODE_RUNTIME_V1.txt
?? core/xiaoj/compiler/
?? core/xiaoj/completion/
?? core/xiaoj/discovery/
?? core/xiaoj/mapping/
?? core/xiaoj/reconstruction/
?? core/xiaoj/redteam/
?? core/xiaoj/runtime.py
?? core/xiaoj/stp/
?? evidence/runtime_audit_20260605/
?? evidence_generative_transport_history_20260606_084323.txt
?? evidence_generative_transport_history_20260606_084331.txt
?? sandbox_state/
?? tensor_8d/space/
```
