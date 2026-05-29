# W7TP-004 Open WebUI 本地小J工作台最終證據包

Status：workspace_integration_design_done
Completion：75%
Priority：P1
Risk Level：L2
PII Level：redacted_or_association_controlled
Mode：PLANONLY / DESIGN + MOCK ONLY

## Evidence Files

- docs/design/XIAOJ_OPENWEBUI_LOCAL_WORKBENCH_MVP.md
- docs/design/XIAOJ_OPENWEBUI_WORKSPACE_INTEGRATION_DESIGN.md
- schemas/xiaoj_openwebui_staff_action_draft.schema.json
- schemas/xiaoj_openwebui_tool_manifest_draft.schema.json
- runtime/mock/xiaoj_openwebui_staff_action_mock.json
- runtime/mock/xiaoj_openwebui_tool_manifest_mock.json
- web/xiaoj_openwebui_workbench/index.html
- docs/project/W7TP_004_OPENWEBUI_LOCAL_WORKBENCH_STATUS.md
- docs/project/W7TP_004_005_007_HANDOFF_MAP.md

## Validation

- schemas/xiaoj_openwebui_staff_action_draft.schema.json: json_ok
- schemas/xiaoj_openwebui_tool_manifest_draft.schema.json: json_ok
- runtime/mock/xiaoj_openwebui_staff_action_mock.json: json_ok
- runtime/mock/xiaoj_openwebui_tool_manifest_mock.json: json_ok

## Completed Controls

- Open WebUI local workbench MVP
- Dashboard mock HTML
- Staff action draft schema
- Tool manifest draft schema
- Workspace integration design
- W7TP-005 / W7TP-007 handoff map
- PLANONLY hardwall

## Hardwall

- PLANONLY=true
- ODOO_WRITE=false
- RAW_PII_TO_CLOUD=false
- NO_SERVICE_RESTART=true
- NO_SECRET_READ=true
- SHELL_ACCESS=false
- AI_RESULT_IS_CANDIDATE_ONLY=true

## Remaining Before Implementation

1. Human review of Open WebUI workspace fields.
2. Actual Open WebUI plugin/workspace integration design only.
3. No production tool binding until explicit authorization.
