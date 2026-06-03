# P0 XiaoJ Pre-Review Patch Candidates

2026-05-31T23:09:36+08:00

## Candidate Files

### W7TP_FIELD_ATLAS/plaintext_policies/W7TP_PLAINTEXT_CLAIM_REVIEW_POLICY_V1.yaml

NO_MATCH

### W7TP_FIELD_ATLAS/emergency_care/W7TP_EMERGENCY_CARE_DISCLOSURE_RULE_V1.yaml

26:  - next_human_review_step

### W7TP_FIELD_ATLAS/key_custody/W7TP_THREE_KEY_CUSTODY_OPERATION_RULE_V1.yaml

NO_MATCH

### W7TP_FIELD_ATLAS/runtime_landing_plans/W7TP_RUNTIME_LANDING_GATE_V1.yaml

NO_MATCH

### W7TP_FIELD_ATLAS/server_acceptance_reports/SERVER_ACCEPTANCE_REPORT_PM3_TO_TAIJI01_V1.yaml

NO_MATCH

### W7TP_FIELD_ATLAS/rollback_plans/W7TP_RUNTIME_ROLLBACK_POLICY_V1.yaml

NO_MATCH

### W7TP_FIELD_ATLAS/rollback_plans/TAIJI01_PM3_ROLLBACK_POINT_PLAN_V1.yaml

NO_MATCH

### W7TP_FIELD_ATLAS/node_enforcement/W7TP_NODE_ENFORCEMENT_POLICY_V1.yaml

35:      - bypass_human_review
55:    - board_or_human_review_for_high_impact_actions

## Decision

status: PATCH_PLAN_CREATED
auto_patch_now: false
next:
  - review_candidate_lines
  - then_run_targeted_patch_command
