# Wuchang Property Sovereign AI Demo 8D Packet

STATE=DEMO_PACKET_READY
RUN_ID=WUCHANG_PROPERTY_SOVEREIGN_AI_DEMO_8D_PACKET_WRITEBACK_20260625

## Purpose

This packet writes the property-sovereign-AI research result into Total Field as a future demo path.

The demo must show the patented property system as an 8D packetized virtual-identity field, not as a generic property app.

## Patent Anchor

- Utility model certificate: `新型第 M663678 號`
- Application number: `113206785`
- Title: `整合式物業管理系統`
- Evidence:
  - `runtime/evidence/patent/877-24-0046.UTW_證書.PDF`
  - `runtime/evidence/patent/877-24-0046.UTW-核准處分書.pdf`
  - `runtime/evidence/patent/877-24-0046.UTW-中文本.pdf`

## D1 Intent

Show an integrated property sovereign AI system that can expand from a virtual group-member identity into committee, resident, merchant, device, repair, announcement, evidence, and governance workflows.

## D2 State

Initial state:

- demo mode only
- no live Odoo write
- no resident/member plaintext
- no payment
- no service restart
- no deployment

Target state:

- 8D packet demo can be displayed
- virtual identities can be expanded
- group-member relationship can be explained
- candidate AI output is gated by Total Field verifier

## D3 Coordinate

Demo coordinate:

```text
association_ref = WUCHANG_ASSOCIATION
property_system_ref = PROPERTY_SOVEREIGN_AI_M663678
demo_field_ref = WUCHANG_PROPERTY_DEMO_FIELD
group_member_packet_ref = DEMO_GROUP_MEMBER_PROPERTY_FIELD
verifier_ref = D8_TOTAL_FIELD_VERIFIER
```

## D4 Evidence

Evidence inputs:

- Patent certificate and specification.
- Odoo/open-source property module market research.
- Wuchang property sovereign AI system blueprint.
- Existing Total Field committee/property documents.

## D5 Execution

Demo execution remains non-executing by default.

Allowed:

- display virtual role graph
- display candidate workflow
- display packet expansion
- display evidence chain
- display human approval gates

Forbidden without later approval:

- install Odoo module
- write Odoo DB
- create resident/member plaintext
- create invoice/payment/order
- restart service
- deploy production

## D6 Generative Transmission

The demo uses generative transfer as:

```text
property problem
→ 8D packet
→ virtual identity coordinate
→ candidate workflow
→ verifier review
→ human-approved action preview
```

Cloud or AI output is candidate-only. The local Total Field verifier remains final authority.

## D7 Risk

Key risks:

- generic property module replacing W7TP method
- member plaintext entering AI context
- Odoo DB write before human review
- patent claim overstated beyond certificate/specification
- demo mistaken as production-ready deployment

Mitigation:

- packet-only demo
- no plaintext
- no install
- no payment
- no Odoo DB write
- explicit verifier/human gate

## D8 Envelope

```yaml
executable: false
demo_only: true
candidate_ai_only: true
virtual_identity_only: true
group_member_expandable: true
requires_total_field_verify: true
member_plaintext_transferred: false
odoo_db_write: false
payment_capture: false
service_restart: false
deploy: false
```

## Demo Expansion Model

### Root Virtual Identity

```text
DEMO_GROUP_MEMBER_PROPERTY_FIELD
```

This is the top-level virtual group member. It is not a real person and contains no member plaintext.

### Expandable Nodes

| Node | Meaning | Demo examples |
| --- | --- | --- |
| `ASSOCIATION_NODE` | association governance | charter, rule, seal, review |
| `COMMITTEE_NODE` | committee workflow | agenda, announcement, resolution |
| `RESIDENT_NODE` | resident-facing service | repair request, notice read status |
| `MERCHANT_NODE` | local merchant/service | quote, dispatch candidate, service marketplace |
| `DEVICE_NODE` | property device | camera ref, access ref, router ref, sensor ref |
| `MAINTENANCE_NODE` | repair workflow | request, evidence, vendor candidate |
| `EVIDENCE_NODE` | immutable trail | attachment hash, seal, report |
| `AI_CANDIDATE_NODE` | XiaoJ draft only | summary, translation, risk checklist |
| `VERIFIER_NODE` | final authority | PASS/WARN/HOLD/BLOCK |

## Display Flow

1. Visitor sees patent anchor and system purpose.
2. Visitor opens `8D virtual identity packet`.
3. The packet expands into group-member nodes.
4. Each node shows refs, not plaintext.
5. XiaoJ provides candidate summaries.
6. D8 verifier shows whether an action is allowed.
7. Human approval is required before real Odoo/property action.

## Future Implementation Capsule

Future implementation should create a staging-only capsule before touching live Odoo:

- `wuchang_property_sovereign_base`
- `wuchang_property_committee`
- `wuchang_property_maintenance`
- `wuchang_property_evidence`
- `wuchang_property_resident_portal`
- `wuchang_property_ai_candidate`
- `wuchang_property_odoo_bridge`

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
