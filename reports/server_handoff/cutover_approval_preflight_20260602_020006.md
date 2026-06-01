# W7TP Cutover Approval Preflight

timestamp: 20260602_020006
head: 80aa40d

transfer_status: PASS
real_copy: PASS
missing_count: 0
bad_hash_count: 0

not_executed_yet:
- deploy
- DB write
- service restart
- chmod/chown
- --delete

decision: HUMAN_APPROVAL_REQUIRED_BEFORE_RUNTIME_CUTOVER
