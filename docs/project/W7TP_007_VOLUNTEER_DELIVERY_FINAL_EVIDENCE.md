# W7TP-007 志工外送服務接單最終證據包

Status：design_v3_1_staff_workflow_mock_done
Completion：90%
Risk Level：L3
PII Level：association_controlled
Mode：PLANONLY / DESIGN + MOCK ONLY

## Evidence Files

- docs/design/XIAOJ_VOLUNTEER_DELIVERY_ORDER_SERVICE.md
- docs/design/ODOO_RESERVED_MODELS_FOR_DELIVERY.md
- docs/design/XIAOJ_VOLUNTEER_DELIVERY_V3_1_PROGRESSIVE_PII.md
- docs/design/XIAOJ_VOLUNTEER_DELIVERY_REVIEW_UI_AND_LINE_COPY.md
- docs/design/XIAOJ_VOLUNTEER_DELIVERY_LINE_RICH_MENU_DRAFT.md
- docs/design/XIAOJ_VOLUNTEER_DELIVERY_STAFF_WORKFLOW_MOCK.md
- docs/project/W7TP_007_VOLUNTEER_DELIVERY_STATUS.md
- web/xiaoj_delivery_review_card/index.html

## Schema / Mock Validation

- schemas/xiaoj_delivery_request_draft.schema.json: json_ok
- schemas/xiaoj_volunteer_delivery_event.schema.json: json_ok
- schemas/xiaoj_dynamic_service_completion_token.schema.json: json_ok
- schemas/xiaoj_line_delivery_rich_menu_draft.json: json_ok
- runtime/mock/xiaoj_delivery_request_mock_v31.json: json_ok
- runtime/mock/xiaoj_delivery_event_mock_v31.json: json_ok
- runtime/mock/xiaoj_dynamic_completion_token_mock_v31.json: json_ok
- runtime/mock/xiaoj_delivery_staff_decision_mock_v31.json: json_ok

## Completed Controls

- Progressive PII Unlocking
- Dynamic Service Completion Token
- Staff Review Workflow Mock
- LINE Rich Menu Draft
- Open WebUI Review Card Mock
- Odoo Reserved Model Design Only
- DLQ / High-risk routing rules
- PLANONLY hardwall

## Hardwall

- No Odoo write
- No DB credential read
- No service start/restart
- No .env/logs/memory/vault/backup read
- No raw PII to cloud
- AI cannot directly dispatch or close service

## Remaining Before Implementation

1. Human review of workflow.
2. Odoo module design only, not implementation.
3. LINE webhook mock only.
4. Admin-blind privacy integration.
5. Volunteer qualification policy approval.

## Renyi Caregiver Safety Hardwall Update

- 志工接單須由具照服員資格之仁義店職員核定並陪同 / 監督。
- 仁義店職員具照服員資格，是高齡志工與高齡居民服務場景的安全理由。
- volunteer_self_accept_allowed=false
- renyi_store_staff_caregiver_qualified=true
- renyi_store_staff_safety_role=caregiver_qualified_safety_escort
- schemas/xiaoj_volunteer_qualification_record.schema.json: json_ok
- runtime/mock/xiaoj_volunteer_qualification_mock.json: json_ok
