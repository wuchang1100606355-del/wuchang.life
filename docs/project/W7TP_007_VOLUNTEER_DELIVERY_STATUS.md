# W7TP-007 志工外送服務接單工程狀態

ID：W7TP-007
Title：志工外送服務接單
Status：volunteer_qualification_policy_done
Priority：P1
Risk Level：L3
PII Level：association_controlled
Completion：95%
Owner Lane：google_lane + codex_lane + human_review + renyi_store_staff

## Evidence

- docs/project/W7TP_007_VOLUNTEER_DELIVERY_FINAL_EVIDENCE.md
- docs/governance/XIAOJ_VOLUNTEER_QUALIFICATION_POLICY.md
- schemas/xiaoj_volunteer_qualification_record.schema.json: json_ok
- runtime/mock/xiaoj_volunteer_qualification_mock.json: json_ok

## Hard Condition

- 志工接單須有仁義店職員核定陪同。
- volunteer_self_accept_allowed=false
- renyi_store_staff_approval_required=true
- renyi_store_staff_accompaniment_required=true

## Next Action

- Human review of volunteer qualification policy.
- Later Odoo module design only, not implementation.

## Safety Rationale Update

- 仁義店職員具照服員資格。
- 仁義店職員核定陪同是高齡志工與高齡居民服務場景的安全硬條件。
- 志工不得自行接單。
