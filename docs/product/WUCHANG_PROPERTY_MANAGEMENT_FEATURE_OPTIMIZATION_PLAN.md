# Wuchang Property Management Feature Optimization Plan

STATE=PROPERTY_FEATURE_OPTIMIZATION_READY
RUN_ID=WUCHANG_PROPERTY_MANAGEMENT_TOTAL_FIELD_FEATURE_OPTIMIZATION_20260625

## Product Goal

Turn the existing Total Field property-management material into a product-grade feature plan for:

```text
五常整合式物業主權 AI 系統
```

The product must be useful to humans first:

- residents can understand what to do
- committee members can review and approve
- property managers can track work
- vendors can receive clear candidate tasks
- XiaoJ can help draft, translate, classify, and check evidence
- Total Field remains the final verifier before real action

## Product Level Standard

This is product-grade only if it is clear to ordinary humans.

Do not show raw engineering terms as the main UI.

Use visible cards, tables, status colors, and plain language:

| Human screen | Meaning |
| --- | --- |
| 社區總覽 | Today status, alerts, pending approvals |
| 報修卡 | What broke, where, photos/evidence, status |
| 公告卡 | Title, audience, publish state, review state |
| 會議卡 | Agenda, decision item, responsible person, evidence |
| 公文卡 | Number, direction, signer, seal status |
| 設備卡 | Device/facility health and maintenance state |
| 廠商卡 | Candidate quote, task scope, approval state |
| 證據卡 | Hash, attachment ref, seal, verifier result |
| AI 候選卡 | XiaoJ draft only, waiting for human approval |

## P0: Demonstration And Patent Evidence Layer

Purpose: show the system clearly without touching production.

### Features

1. Patent anchor card
   - Shows `M663678 / 113206785 / 整合式物業管理系統`.
   - Links to local evidence refs.
   - States legal boundary: candidate evidence, not legal enforcement.

2. 8D property virtual identity graph
   - Association node
   - Committee node
   - Resident node
   - Merchant/vendor node
   - Device node
   - Maintenance node
   - Evidence node
   - AI candidate node
   - Verifier node

3. Demo workflow cards
   - "Resident reports a leak"
   - "XiaoJ classifies and drafts"
   - "Committee reviews"
   - "Vendor candidate quote is compared"
   - "Verifier checks risk"
   - "Human approves final action"

4. Bilingual / multilingual text support
   - Chinese default
   - Vietnamese staff/resident support
   - English technical/pitch support

### Acceptance

- No Odoo DB write.
- No member plaintext.
- No payment.
- No deploy.
- Demo can explain the patent and product without overclaiming.

## P1: Staging Product Core

Purpose: create a staging-only implementation capsule after human approval.

### Core Modules

| Module | Feature scope |
| --- | --- |
| `wuchang_property_sovereign_base` | property, building, unit, facility, device, role refs |
| `wuchang_property_committee` | notices, meetings, agendas, resolutions, committee approvals |
| `wuchang_property_document` | public documents, official letters, signatures, archive refs |
| `wuchang_property_maintenance` | repair tickets, inspection, vendor candidate dispatch |
| `wuchang_property_evidence` | hash, seal, attachment metadata, audit records |
| `wuchang_property_resident_portal` | resident status view, request submit, notice read |
| `wuchang_property_ai_candidate` | XiaoJ draft/summary/translation/classification only |
| `wuchang_property_verifier_bridge` | D8 verifier status and HOLD/WARN/BLOCK routing |

### Key Data Refs

```text
property_ref
building_ref
unit_ref
facility_ref
device_ref
role_ref
committee_ref
resident_ref
vendor_ref
request_ref
document_ref
evidence_ref
packet_ref
verifier_status
handoff_status
ttl
```

### Acceptance

- Staging database only.
- Backup before install.
- No live resident/member plaintext.
- AI output stored as candidate.
- Verifier status required before action buttons become active.

## P2: Human-Ready Operations

Purpose: make it usable by a real committee / manager / resident.

### UX Optimization

1. Replace abstract lists with role dashboards:
   - 理事長 / 主委: pending approvals and risk items.
   - 總幹事 / 物業: work queue and evidence gaps.
   - 住戶: my requests and public notices.
   - 廠商: approved task scope only.

2. Make every action status obvious:
   - Draft
   - Candidate
   - Needs evidence
   - Waiting human review
   - Approved
   - Rejected
   - Archived

3. Use action gates:
   - AI draft: allowed
   - publish notice: human approval
   - vendor dispatch: human approval
   - payment: separate human approval
   - access/security change: separate legal/security review

4. Use picture/table first:
   - repair photos
   - facility map/table
   - meeting decision table
   - evidence timeline
   - verifier traffic-light summary

## P3: Advanced Integrations

Only after staging and governance approval:

- accounting references
- payment references
- vendor settlement workflow
- access/security system references
- public dashboard
- local merchant service marketplace
- Google Workspace document handoff
- router/device governance node

Do not activate face recognition, access-control writes, payments, or live dispatch from AI without a separate legal/privacy/security review.

## Feature Priority Matrix

| Priority | Feature | Why it matters | Risk gate |
| --- | --- | --- | --- |
| P0 | 8D demo graph | Explains the system and patent evidence | demo only |
| P0 | Evidence card | Shows why this is not generic SaaS | no secret content |
| P0 | AI candidate card | Shows XiaoJ value safely | candidate only |
| P1 | Notice/meeting/resolution | Committee daily workflow | human approval |
| P1 | Repair ticket | Resident-visible value | no member plaintext |
| P1 | Official letter workflow | Differentiates 物業腦 | signer/seal review |
| P1 | Device/facility inventory | Technical management base | no config secrets |
| P2 | Vendor quote comparison | Saves cost, improves accountability | no auto-dispatch |
| P2 | Multilingual resident/staff text | Better human usability | human verification |
| P3 | Payments/accounting | Operational completeness | separate payment gate |
| P3 | Access/security refs | Patent/security mapping | separate legal/security review |

## Product Homepage Content Blocks

1. Who is the主体
   - 新北市三重區五常社區發展協會 / 五常社區數位治理脈絡.
   - Product origin: community governance and property service experience.

2. Why this site exists
   - To make property, committee, resident, merchant, and device workflows accountable and auditable.

3. What exists now
   - Patent evidence.
   - 8D demo packet.
   - Product blueprint.
   - Candidate Odoo module references.
   - Total Field verifier and evidence workflow.

4. What comes next
   - Staging module capsule.
   - Human-facing dashboard.
   - Resident repair and notice portal.
   - Committee document workflow.
   - Evidence ledger.

5. What AI can and cannot do
   - Can draft, classify, translate, summarize, and check missing evidence.
   - Cannot approve, pay, dispatch, alter access, or read plaintext without explicit authority.

## Developer Guidance

Developers must preserve this chain:

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

Before implementation, developers should create:

- schema for refs
- view mockups
- staging install plan
- backup plan
- verifier hook
- redteam possible-alert rules
- human approval checklist

Do not start by installing a generic marketplace app into live Odoo.

## Forbidden Claims

Do not claim:

- AI autonomously manages buildings.
- Resident/member plaintext is used for AI.
- The demo is already a production property system.
- Patent scope is broader than verified documents.
- Government endorsement exists unless evidence is separately shown.
- Payment/access/legal actions can be completed without human approval.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
D8_LOCAL_DB_WRITE=TRUE
PRODUCTION_DB_WRITE=FALSE
ODOO_DB_WRITE=FALSE
ODOO_MODULE_UPGRADE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE
