# Wuchang Integrated Property Sovereign AI System Blueprint

STATE=BLUEPRINT_READY
RUN_ID=ODOO_PROPERTY_SOVEREIGN_AI_SYSTEM_OPEN_SOURCE_MARKET_RESEARCH_20260625

## Product Name

五常整合式物業主權 AI 系統

## Patent Anchor

This blueprint is anchored to verified local evidence:

- Utility model patent: `新型第 M663678 號`
- Application number: `113206785`
- Title: `整合式物業管理系統`
- Patent owners / creators: `江政隆、蔣明諺`

The system must not claim additional patent scope beyond verified certificate, specification, claims, and human/legal review.

## Positioning

This is not a generic property app.

It is an Odoo-backed, W7TP-governed property sovereignty system for:

- committee operations
- resident service
- repair and maintenance
- public notices
- document evidence
- community commerce/service connection
- security and access references
- candidate-only AI assistance
- Total Field verifier-controlled actions

## Core Difference

Generic property modules manage objects.

The Wuchang system governs intent, authority, evidence, and action.

```text
State
→ Coordinate
→ Hash
→ Packet
→ Generative Transfer
→ Verify
→ Reconstruct
→ Evidence
→ Action
```

Every important operation must be a packeted, evidenced, authorized action.

## Domain Model

### Property Field

- `property_ref`
- `building_ref`
- `unit_ref`
- `floor_ref`
- `public_area_ref`
- `facility_ref`
- `device_ref`
- `vendor_ref`
- `committee_ref`

### Human/Organization Role Field

- `resident_ref`
- `owner_ref`
- `tenant_ref`
- `committee_member_ref`
- `manager_ref`
- `security_staff_ref`
- `maintenance_vendor_ref`
- `association_ref`

Member plaintext is not stored or sent to AI by default.

### Workflow Field

- announcement
- repair request
- emergency event
- meeting agenda
- resolution
- document approval
- vendor dispatch
- access request
- recurring fee reference
- public service request

### Evidence Field

- source document
- photo evidence
- quote
- work order
- approval record
- payment reference
- human review note
- seal
- hash

## Module Architecture

| Module | Responsibility | Odoo dependencies | AI boundary |
| --- | --- | --- | --- |
| `wuchang_property_sovereign_base` | property/unit/facility/device/role references | base, mail | no AI action |
| `wuchang_property_committee` | meeting, agenda, resolution, announcement, committee workflow | base, mail, documents if available | draft only |
| `wuchang_property_maintenance` | repair tickets, vendor dispatch candidates, maintenance evidence | project/helpdesk-like patterns | candidate dispatch only |
| `wuchang_property_evidence` | hash, seal, attachment metadata, audit trail | base, mail, documents | no raw sensitive output |
| `wuchang_property_resident_portal` | resident-facing portal for requests/status | website/portal | no plaintext leak |
| `wuchang_property_ai_candidate` | XiaoJ draft, summary, risk hints, translation | local D8 / W7TP bridge | candidate only; verifier required |
| `wuchang_property_odoo_bridge` | integration with accounting/POS/contacts when explicitly approved | account, sale, POS as optional bridges | no DB write without gate |

## AI Action Boundary

XiaoJ may:

- summarize public notices
- draft meeting minutes
- translate Chinese / Vietnamese / English
- classify repair requests
- suggest vendor dispatch candidate
- detect missing evidence
- produce human-review checklists

XiaoJ must not:

- read member plaintext without explicit authorization
- create payment
- create legal notice
- approve repairs
- dispatch vendor as final action
- modify access control
- issue warnings based on utility model patent without technical report/legal review
- bypass committee/human approval

## Open Source Reference Use

Odoo / OCA modules are references, not authorities.

- OCA/pms: reference for multi-property operations and board services.
- OCA/vertical-realestate: reference for real-estate object modeling.
- Advanced Property Management: reference for website/kanban/rental/sale UX.
- Odoo industry_real_estate: reference for lease, owner report, facility lifecycle.
- open-condo: reference for service marketplace and ticket resident model.

The final system must remain Wuchang-owned and W7TP-governed.

## P0 Development Path

1. Build a static module compatibility matrix.
2. Inspect existing Wuchang property/committee modules without modifying production.
3. Create a staging-only module skeleton.
4. Define core models with refs only.
5. Add portal read-only request/status flow.
6. Add evidence seal and hash trail.
7. Add XiaoJ candidate-only summary/classification.
8. Add Total Field verifier.
9. Run staging tests.
10. Human review before any production Odoo install.

## Product Homepage Wording

Safe public wording:

> 本系統以新型第 M663678 號「整合式物業管理系統」為技術佐證之一，結合 Odoo 開源 ERP、五常社區治理經驗與 W7TP / D8 總場驗證機制，建立可稽核、可交接、以人類授權為中心的物業主權 AI 系統。

Avoid:

- claiming guaranteed patent scope beyond the certificate
- claiming AI can autonomously perform legal/property/payment actions
- using resident/member plaintext for AI
- implying official government endorsement unless documents are shown
- presenting Odoo marketplace modules as the final Wuchang product

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
PRODUCTION_DB_WRITE=FALSE
ODOO_DB_WRITE=FALSE
ODOO_MODULE_UPGRADE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
EXTERNAL_API_CALL=TRUE
EMBEDDING_GENERATED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE
