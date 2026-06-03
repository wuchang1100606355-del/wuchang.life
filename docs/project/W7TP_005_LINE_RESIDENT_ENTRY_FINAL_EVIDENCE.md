# W7TP-005 LINE 小J居民入口最終證據包

Status：design_resident_flow_mock_done
Completion：65%
Priority：P1
Risk Level：L2
PII Level：redacted_or_association_controlled
Mode：PLANONLY / DESIGN + MOCK ONLY

## Evidence Files

- docs/design/XIAOJ_LINE_RESIDENT_ENTRY_MVP.md
- docs/design/XIAOJ_LINE_WEBHOOK_MOCK_FLOW.md
- docs/design/XIAOJ_LINE_RESIDENT_FLOW_TEST.md
- docs/project/W7TP_005_LINE_RESIDENT_ENTRY_STATUS.md
- schemas/xiaoj_line_resident_intent_draft.schema.json
- schemas/xiaoj_line_webhook_event_mock.schema.json
- runtime/mock/xiaoj_line_resident_intent_mock.json
- runtime/mock/xiaoj_line_webhook_event_mock.json
- runtime/mock/xiaoj_line_resident_flow_test.json

## Validation

- schemas/xiaoj_line_resident_intent_draft.schema.json: json_ok
- schemas/xiaoj_line_webhook_event_mock.schema.json: json_ok
- runtime/mock/xiaoj_line_resident_intent_mock.json: json_ok
- runtime/mock/xiaoj_line_webhook_event_mock.json: json_ok
- runtime/mock/xiaoj_line_resident_flow_test.json: json_ok

## Completed Controls

- LINE resident entry MVP
- LINE rich menu route design
- webhook event mock
- resident flow test
- W7TP-007 delivery handoff
- community_redacted_lane / personal_privacy_lane / staff_review_lane / dlq_lane
- PLANONLY hardwall

## Hardwall

- WiFi is not identity
- No raw PII to cloud
- No Odoo write
- No service start/restart
- AI cannot directly dispatch or close service
- Personal progress query requires login / consent / one-time verification

## Remaining Before Implementation

1. LINE webhook real endpoint design only.
2. Resident consent / one-time verification design.
3. Admin-blind privacy integration.
4. Open WebUI staff review connection.
5. Odoo module design only, not implementation.

## Consent / One-time Verification Update

- docs/design/XIAOJ_LINE_CONSENT_ONE_TIME_VERIFICATION.md
- schemas/xiaoj_line_one_time_verification.schema.json: json_ok
- runtime/mock/xiaoj_line_one_time_verification_mock.json: json_ok

## Updated Hardwall

- wifi_is_identity=false
- line_user_hash_is_not_full_identity=true
- personal_progress_query_requires_verification=true
- one_time_token_scope_limited=true
- raw_pii_to_cloud=false
- odoo_write=false
- plan_only=true

## Updated Status

Status：consent_one_time_verification_done
Completion：75%

## Consent / One-time Verification Update

- docs/design/XIAOJ_LINE_CONSENT_ONE_TIME_VERIFICATION.md
- schemas/xiaoj_line_one_time_verification.schema.json: json_ok
- runtime/mock/xiaoj_line_one_time_verification_mock.json: json_ok

## Updated Hardwall

- wifi_is_identity=false
- line_user_hash_is_not_full_identity=true
- personal_progress_query_requires_verification=true
- one_time_token_scope_limited=true
- raw_pii_to_cloud=false
- odoo_write=false
- plan_only=true

## Updated Status

Status：consent_one_time_verification_done
Completion：75%
