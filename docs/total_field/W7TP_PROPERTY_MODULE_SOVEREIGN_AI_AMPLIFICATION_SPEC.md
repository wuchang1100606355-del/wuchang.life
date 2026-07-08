# W7TP Property Module Sovereign AI Amplification Spec

STATE=W7TP_PROPERTY_MODULE_SOVEREIGN_AI_AMPLIFICATION_SPEC_READY
AUTHORITY=TOTAL_FIELD
MODE=CANDIDATE_ONLY_NO_LIVE_ODOO_WRITE

## Upgrade Name

W7TP 物業模組主權 AI 增幅層

This packet turns the high-privacy property management draft into an upgrade design for the existing Wuchang property module. It is a candidate landing packet only. It is not a public release packet, patent basis, Odoo module install plan, or live controller change.

## Existing Surface

Read-only reference points found in the current workspace:

- `Taiji_Odoo/addons/wuchang_core/models/property_management.py`
- `Taiji_Odoo/addons/wuchang_core/models/property_document.py`
- `Taiji_Odoo/addons/wuchang_core/data/property_structure_data.xml`
- `Taiji_Odoo/addons/wuchang_core/views/property_views.xml`
- `docs/total_field/WUCHANG_PROPERTY_SOVEREIGN_AI_DEMO_8D_PACKET.md`
- `docs/total_field/W7TP_XIAOJ_SERVICE_PERSONA_POLICY.md`
- `schemas/field/sovereign_ai_member_xiaoj_translator.schema.json`

No live Odoo controller, database table, router, service, or production setting is changed by this packet.

## Core Architecture

The upgrade layer combines:

- Integrated property management system.
- Local Total Field decision authority.
- ADI 5D metric index layer.
- Edge XiaoJ lobby and property gateway.
- Odoo property container for community, building, unit, committee, document, package, repair, and bulletin workflows.

The cloud role is limited to candidate wording, candidate copy, and candidate analysis. It cannot release a door, approve a visitor, read resident details, or change Total Field `PASS / HOLD / WARN / BLOCK`.

## Total Field Eight-Lane Model

The 8-in-1 Total Field is expressed as fields:

- 意圖場
- 狀態場
- 座標場
- 證據場
- 執行場
- 生成式傳輸場
- 風險禁錮場
- 封套驗證場

These are governance fields, not ordinary database columns.

## ADI 5D Boundary

ADI is a 5D metric index layer. It indexes resident refs, household refs, roles, devices, evidence refs, risk positions, and authority coordinates.

ADI is not a normal table, not an access-control owner, and not a field list for the 8-in-1 Total Field. It must not include full H64 mappings, complete lookup rules, weights, or generation rules in this public candidate packet.

## Property Organization Container

The property organization container uses ref-only boundaries:

- Management committee organization container.
- Property staff roles.
- Householder, resident, and family-member roles.
- Visitor role.
- Merchant and association links by ref only.

Cross-organization links cannot grant authority by themselves. Merchant, association, or committee context is a candidate relationship until the Total Field verifier and human review pass.

## Scene Functions

The upgrade layer can describe these candidate functions:

- Lobby greeting.
- Visitor registration.
- Door-access interaction.
- Work orders.
- Announcements.
- Meeting record refs.
- Public facility reservations.
- Emergency notices.
- Resident services.

Every function is a candidate workflow until local Total Field and the authorized human role approve the action.

## Image Governance

Image governance is local-first and ref-only:

- Raw image stays on the local edge device or approved local server only.
- Raw image does not enter Total Field packets.
- Raw image does not enter cloud candidates.
- Allowed evidence surfaces are `pHash_ref`, `morphology_ref`, `evidence_ref`, `hash`, and `seal`.

Door, visitor, camera, and lobby flows must use irreversible refs or sealed evidence refs in the candidate packet.

## DLQ Policy

The property DLQ policy is intentionally modest:

- append-only intent.
- hash chain.
- seal.
- permission isolation.
- optional external seal.

It must not claim that a privileged host administrator can never remove local files. The promise is evidence integrity, independent sealing, and reviewable tamper risk, not physical impossibility.

## Cloud Boundary

Cloud support is candidate-only:

- It may improve wording.
- It may draft candidate notices.
- It may summarize public or ref-only evidence.
- It may suggest safe alternatives.

Cloud support cannot:

- release access control.
- process resident details.
- become final authority.
- override local `PASS / HOLD / WARN / BLOCK`.
- receive raw images.
- receive raw credentials.

## Door And Visitor Rule

Any request to open another household's private door is blocked unless explicit authorization refs are present and local Total Field verification passes. XiaoJ may offer safe alternatives such as contacting the resident, ringing the bell, sending a message, or asking property staff for assistance.

## Management Committee Boundary

Management committee containers default to:

```text
management_committee_authorization_status=HOLD_UNTIL_AUTHORIZED
public_projection=STRUCTURE_ONLY
final_authority=total_field_verifier
```

The candidate packet must not project an unverified container as a real committee system.

## Safety Flags

```text
NO_SECRET=TRUE
NO_MEMBER_PLAINTEXT=TRUE
NO_RESIDENT_PLAINTEXT=TRUE
NO_RAW_IMAGE=TRUE
NO_RAW_KEY_TOKEN_PASSWORD=TRUE
NO_DB_WRITE=TRUE
NO_DEPLOY=TRUE
NO_RESTART=TRUE
NO_ROUTER_WRITE=TRUE
NO_OVERWRITE=TRUE
CANDIDATE_ONLY=TRUE
FINAL_AUTHORITY=total_field_verifier
```

## Next

Use the schema and samples in this packet for human review. Only after review should exact files be staged.
