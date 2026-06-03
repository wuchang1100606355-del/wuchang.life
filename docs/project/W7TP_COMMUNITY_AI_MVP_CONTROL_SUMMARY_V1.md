# W7TP Community AI MVP Control Summary v1

狀態：PLANONLY / DESIGN + MOCK CONTROL SUMMARY

## Module Status

| ID | Module | Status | Completion | Critical Hardwall |
|---|---|---|---:|---|
| W7TP-004 | Open WebUI 本地小J工作台 | workspace_integration_design_done | 75% | no shell / no Odoo write / no raw PII |
| W7TP-005 | LINE 小J居民入口 | consent_one_time_verification_done | 75% | WiFi is not identity / one-time verification |
| W7TP-007 | 志工外送服務接單 | renyi_caregiver_hardwall_synced | 95% | 仁義店照服員資格職員核定陪同 |
| W7TP-016 | Admin-blind privacy + 三鑰制度 | cryptographic_design_only_done | 90% | single admin decrypt forbidden |

## Integrated Service Chain

LINE resident entry
-> Open WebUI staff workbench
-> staff action draft
-> volunteer delivery draft
-> Renyi caregiver-qualified staff approval/accompaniment
-> progressive PII unlock
-> dynamic completion token
-> admin-blind encrypted payload / three-key break-glass only when needed

## Validation

- OpenWebUI tool manifest schema: json_ok
- LINE one-time verification schema: json_ok
- Volunteer qualification schema: json_ok
- Encrypted payload envelope schema: json_ok
- OpenWebUI tool manifest mock: json_ok
- LINE one-time verification mock: json_ok
- Volunteer qualification mock: json_ok
- Encrypted payload envelope mock: json_ok

## Global Hardwall

- PLANONLY=true
- ODOO_WRITE=false
- RAW_PII_TO_CLOUD=false
- NO_SERVICE_RESTART=true
- NO_SECRET_READ=true
- WIFI_IS_NOT_IDENTITY=true
- SINGLE_ADMIN_DECRYPT_ALLOWED=false
- ROOT_ADMIN_IS_NOT_PRIVACY_ACCESS=true
- VOLUNTEER_SELF_ACCEPT_ALLOWED=false
- RENYI_STORE_STAFF_CAREGIVER_QUALIFIED=true
- RENYI_STORE_STAFF_APPROVAL_AND_ACCOMPANIMENT_REQUIRED=true

## Next Implementation-Ready Design Tasks

1. Odoo module design only：models / views / security / no implementation.
2. LINE real endpoint design only：webhook, signature verification, no live token.
3. Open WebUI actual workspace/plugin design only：no tool binding yet.
4. Cryptographic implementation design review：no real key generation yet.
5. Human governance review：volunteer policy, three-key custody, break-glass SOP.
