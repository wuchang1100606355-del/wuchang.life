# AI Browser Member UI Generative Reconstruction Gap Fill

STATE=AI_BROWSER_MEMBER_UI_GENERATIVE_RECONSTRUCTION_GAP_FILLED
DATE=2026-06-26
ROOT=/home/taiji_admin/Taiji_Hub

## 0. Total Field Dialogue

### Preflight Question To Total Field

Task:

- Land a generative reconstruction package for Taiji_Hub / Wuchang / XiaoJ AI Browser member UI.
- Fill missing product, model, route, integration, review, evidence, and test items.
- Use repo facts and current web references.

Forbidden:

- No secret read.
- No member plaintext read.
- No Odoo DB write.
- No POS order or payment.
- No service restart.
- No deploy.
- No fake evidence for missing implementation results.
- No modification of `AGENTS.md` or Odoo addon files in this task.

Total Field response:

- `DECISION=PASS`
- `ALLOW_SANDBOX=TRUE`
- `ALLOW_LAND=TRUE`
- This task may create a product/engineering gap-fill document only.
- Actual Odoo model/controller/view changes require a separate sealed LAND task.

### Postflight Answer To Total Field

This packet fills the missing implementation map. It does not claim runtime completion.

Evidence generated:

- `docs/product/AI_BROWSER_MEMBER_UI_GENERATIVE_RECONSTRUCTION_GAP_FILL_20260626.md`

Next safe LAND task:

- `AI_BROWSER_MEMBER_UI_DEMO_SHELL_LAND_P1`

## 1. Source Base

### Repo Sources

1. `Taiji_Odoo/addons/wuchang_member_registration/models/member_registration.py`
   - Existing registration, review status, owner-required review level, self-approval block, 7D identity code, group 8D packet, consent ledger, external auth hash, evidence refs for group packets.
2. `Taiji_Odoo/addons/wuchang_member_registration/controllers/main.py`
   - Existing public member registration and group claim routes; many routes currently `csrf=False`, so demo/member routes must be risk-gated.
3. `Taiji_Odoo/addons/wuchang_core/models/property_management.py`
   - Existing community, building, unit, committee member, complaint, financial report, bulletin, and package models.
4. `Taiji_Odoo/addons/wuchang_core/models/task.py`
   - Existing task model with owner, partner, deadline, priority, parent/child, side quest review, and AI reminder fields.
5. `Taiji_Odoo/addons/wuchang_core/models/volunteer.py`
   - Existing volunteer task/signup/meeting/announcement and voice sample models.
6. `docs/total_field/HARD_WALLS_CONTRACT_V1.md`
   - Hard walls: no secret read, no member plaintext, no production DB write, no payment capture, no restart/deploy.
7. `docs/product/D8_MARKET_READY_PRODUCT_BLUEPRINT.md`
   - D8 is the preflight, redteam, guard, evidence, and Odoo/POS safe bridge product frame.
8. `docs/total_field/WUCHANG_PROPERTY_MANAGEMENT_TOTAL_FIELD_INFORMATION_SYNTHESIS.md`
   - Property product is governance + resident service + evidence seal + 8D identity packet + AI candidate output + Total Field verifier.

### Web Sources Checked On 2026-06-26

1. Google for Nonprofits Help: Google Workspace for Nonprofits is offered at no charge, while Business/Enterprise nonprofit editions are discounted; account activation and plan eligibility still need local verification.
   - https://support.google.com/nonprofits/answer/3367223
2. Google for Nonprofits overview: basic Workspace features can be used at no cost for eligible nonprofits, with discounted upgrades.
   - https://support.google.com/nonprofits/answer/1614581
3. Google Tasks API: supports task lists and tasks; suitable for lightweight task sync, not for sensitive authoritative workflow storage.
   - https://developers.google.com/workspace/tasks/reference/rest
4. Google Tasks API limits: tasks carry date-level due info, and API cannot read/write scheduled time; do not treat Tasks as precise dispatch or SLA engine.
   - https://developers.google.com/workspace/tasks/reference/rest/v1/tasks
5. Google Forms API: can create/modify forms and retrieve responses; publication/sharing settings and quotas must be handled explicitly.
   - https://developers.google.com/workspace/forms/api/reference/rest
   - https://developers.google.com/workspace/forms/api/limits
6. LINE WORKS Bot feature page: bots can join group message rooms, communicate with buttons/stamps, write meeting notes, and assign tasks.
   - https://line-works.com/en/feature/bot/
7. LINE WORKS starter guide: common organization tools include Calendar, Task, Form, Contacts, and Group.
   - https://line-works.com/en/blog/line-works-starters-guide/
8. Taiwan National Land Management Agency apartment building act page: management committee chair represents committee; committee powers follow owners' meeting resolutions or community regulations.
   - https://www.nlma.gov.tw/ch/legislation/regsearch/174
9. Ministry of the Interior model apartment building regulation: model roles include chair, vice chair, finance committee, supervisory committee, and committee members.
   - https://glrs.moi.gov.tw/LawContent.aspx?id=FL003879
10. National Land Management Agency apartment building Q&A: resident includes owner, tenant, or person permitted to use the unit; role eligibility may depend on meeting decisions or regulations.
   - https://www.nlma.gov.tw/ch/titlelist/areanu/4716

## 2. Generative Reconstruction Result

The existing repo can support a demo-grade AI Browser shell, but it is missing the decision-complete layer that connects:

- member registration claims,
- organization/family membership,
- owner and delegated reviewer governance,
- role dashboards,
- external notification/document/task tools,
- evidence refs,
- Total Field pre/post gates,
- and redteam hard walls.

Therefore the landing must be split into six packets:

1. `P1_DEMO_SHELL`
2. `P2_REVIEW_WORKBENCH`
3. `P3_ORGANIZATION_MEMBERSHIP`
4. `P4_FAMILY_ORGANIZATION`
5. `P5_INTEGRATION_ADAPTERS`
6. `P6_HARDENING_AND_EVIDENCE`

Canonical Odoo/member scenario integration:

```text
docs/total_field/ODOO_MEMBER_SCENARIO_TOTAL_FIELD_INTEGRATION.md
```

This integration states that Odoo carries the runtime scenario, Total Field governs safety/evidence, and the member retains consent sovereignty.

No packet may claim completion until it has:

- preflight PASS/INFO,
- changed-file list,
- tests or manual verification,
- postflight result seal,
- and no violation of hard walls.

## 3. Missing Item Register

| ID | Missing item | Current repo state | Fill decision | First landing packet |
| --- | --- | --- | --- | --- |
| G01 | Product-grade AI Browser shell | Login/signup templates exist; no unified role workspace | Add sandbox route/view with mock refs and role switch | P1 |
| G02 | Role dashboard data contract | Role concepts exist in docs, but no UI contract | Define normalized dashboard payload with D1-D7 sections | P1 |
| G03 | Organization type taxonomy | Registration has `member_type` and affiliation text only | Add explicit org type enum in later model; P1 uses mock refs | P3 |
| G04 | Organization membership relation | No robust membership model found | Add `wuchang.organization.membership` later | P3 |
| G05 | Family organization model | Recovery case has delegated family, but no family org | Add family org, member, invitation, head review | P4 |
| G06 | Review audit log | Registration has reviewer/reviewed_at but no full decision ledger | Add append-only review event model | P2 |
| G07 | Evidence ref on every decision | Group 8D has evidence; registration approval lacks required `evidence_ref` | Add evidence field and require reason/evidence for decisions | P2 |
| G08 | Role-based reviewer delegation | Owner-only and manager-only logic exists; org responsible binding not enabled | Implement reviewer policy service with no self-review | P2/P3 |
| G09 | Public route risk list | `rg` shows many public/csrf/cors routes | Do not attach member workbench to public write routes; create route hardening report | P6 |
| G10 | External tool cost/status gates | Product plan exists, live account status unknown | UI labels each card: configured, needs setup, paid/unknown, disabled | P5 |
| G11 | Google Tasks limitations | Not modeled | Treat Tasks as personal reminder mirror only; Odoo remains authority | P5 |
| G12 | LINE WORKS suitability by domain | Not modeled | Use for merchant/property/nonprofit teams; family only when organized caregiver team exists | P5 |
| G13 | Responsive device states | Product requirement exists | Add fixed viewport acceptance list and Playwright screenshot plan | P1/P6 |
| G14 | Demo data boundary | Hard wall exists | All demo payloads must use refs, not names/phones/addresses | P1/P6 |
| G15 | 7D packet visual status | Identity code exists; no browser panel | Add 7D/8D status panel with sealed/ref-only fields | P1 |
| G16 | Total Field work gating in UI | D8 tooling exists; UI not connected | Display preflight decision and postflight evidence ref as first-class status | P1/P6 |

## 4. Canonical Dashboard Payload

Every AI Browser page must consume or emulate this payload shape. P1 may hardcode mock data. P2+ must map it to Odoo records.

```json
{
  "viewer_ref": "MEMBER_REF_xxx",
  "workspace_ref": "ORG_OR_FAMILY_REF_xxx",
  "dashboard_type": "individual|merchant|property|family|owner_review",
  "d1_identity": {
    "member_ref": "MEMBER_REF_xxx",
    "display_mask": "masked",
    "active_status": "draft|pending_review|approved|rejected|blocked"
  },
  "d2_organization": {
    "organization_type": "none|merchant_organization|property_management_organization|family_organization|nonprofit_organization|government_or_social_service|association|other",
    "organization_ref": "ORG_REF_xxx",
    "claim_status": "none|claimed|pending_evidence|verified|rejected"
  },
  "d3_role": {
    "role_key": "member|responsible_person|staff|family_head|family_member|resident|tenant|unit_owner|committee_chair|committee_member|property_manager|guard|volunteer|social_worker|owner_reviewer",
    "permissions": ["view_status"],
    "forbidden_permissions": ["approve_self", "cross_org_review"]
  },
  "d4_review": {
    "review_level": "manager_allowed|owner_required|org_responsible_required|family_head_required|blocked",
    "reviewer_policy_ref": "REVIEW_POLICY_REF_xxx",
    "next_reviewer_type": "owner|org_responsible|family_head|none",
    "self_review_blocked": true
  },
  "d5_workspace": {
    "primary_next_actions": [],
    "notifications": [],
    "review_queue_count": 0,
    "task_count": 0
  },
  "d6_integration": {
    "odoo": {"status": "authority"},
    "line_works": {"status": "not_configured|configured|needs_verification|not_recommended"},
    "google_workspace": {"status": "not_configured|configured|needs_verification"},
    "google_tasks": {"mode": "mirror_only"},
    "google_drive": {"mode": "evidence_ref_only"}
  },
  "d7_risk_evidence": {
    "risk_level": "low|medium|high|hold|block",
    "evidence_ref": "EVIDENCE_REF_xxx",
    "packet_hash": "sha256:...",
    "total_field_decision": "PASS|INFO|WARN|HOLD|BLOCK"
  }
}
```

## 5. Review Policy Completion

### Rule Table

| Subject | Required reviewer | Must block |
| --- | --- | --- |
| Organization entity | Owner reviewer | Self-review, manager-only approval |
| Merchant responsible person | Owner reviewer | Merchant member approving own responsible role |
| Property responsible person | Owner reviewer | Property member approving own responsible role |
| Family head | Owner or high-privilege reviewer | Family self-appointment |
| Organization normal member | Approved responsible person of same org, or owner | Cross-org reviewer |
| Family member | Approved family head of same family, or owner | Cross-family reviewer |
| Committee chair | Owner/property responsible reviewer plus regulation evidence | Claim without community/regulation evidence |
| Committee finance/supervisory member | Owner/property responsible reviewer plus term evidence | Missing term/evidence |
| Property manager / guard | Property responsible reviewer | Access to unrelated communities |
| Volunteer / social worker | Association owner or delegated nonprofit reviewer | Access to member plaintext by default |

### Review Event Model To Add Later

P2 should add an append-only model:

```text
wuchang.member.review.event
```

Required fields:

- `registration_id`
- `subject_ref`
- `subject_model`
- `decision`
- `reviewer_id`
- `reviewed_at`
- `reason`
- `evidence_ref`
- `review_policy_ref`
- `packet_hash`
- `total_field_decision`
- `created_from_route`

Behavior:

- One registration can have many review events.
- Final registration status derives from latest valid event.
- Reject/return-for-evidence events require reason.
- Approve requires reviewer policy PASS and evidence_ref.
- Self-review raises error before write.

## 6. Model Completion Blueprint

### P3 Organization Membership

Add later:

```text
wuchang.organization.entity
wuchang.organization.membership
wuchang.organization.role.policy
```

Minimal fields:

- organization type,
- organization ref,
- legal/display name masked where needed,
- responsible person membership,
- member identity link,
- role key,
- status,
- reviewer policy,
- evidence refs,
- active period.

Default:

- A registration `organization_name` is only a claim.
- No Odoo group or dashboard authority is granted until a membership is approved.

### P4 Family Organization

Add later:

```text
wuchang.family.organization
wuchang.family.membership
wuchang.family.invitation
```

Minimal fields:

- family ref,
- family head membership,
- member identity ref,
- relationship label,
- care role,
- minor/elder flag as non-public policy flag,
- status,
- evidence ref,
- reviewer policy.

Default:

- Family tasks and care reminders use Google Calendar/Tasks only as mirrors.
- Odoo remains authority for family membership and review status.
- Family head cannot approve self and cannot review outside family.

## 7. Page And Route Completion

| Route | Packet | Auth | Data | Status |
| --- | --- | --- | --- | --- |
| `/ai/member/workspace` | P1 | `auth=user` | mock payload | demo shell |
| `/ai/member/workspace/<dashboard_type>` | P1 | `auth=user` | mock payload | role demo |
| `/ai/review/owner` | P2 | owner group | registration + review events | beta |
| `/ai/review/org/<org_ref>` | P3 | org responsible | membership queue | beta |
| `/ai/review/family/<family_ref>` | P4 | family head | family queue | beta |
| `/ai/integrations/status` | P5 | user | config refs only | beta |
| `/ai/total-field/status` | P6 | user | latest preflight/postflight refs | beta |

P1 route rules:

- No public write.
- No `auth='none'`.
- No `cors='*'`.
- CSRF enabled for HTML forms unless route is read-only JSON and protected by Odoo auth/session.
- No secret/config value rendering.

## 8. Integration Completion Matrix

| Tool | Use | Authority | Status label | Sensitive data rule |
| --- | --- | --- | --- | --- |
| Odoo | Member, org, review, task, POS/property records | Authority | production core | Can store formal refs and audit fields |
| D8/Total Field | Preflight, postflight, evidence gate | Governance authority | required | No secret/member plaintext |
| LINE WORKS | Team notification, task prompts, bot summaries | Mirror/candidate | needs plan verification | No member plaintext or final approval |
| Google Forms | Intake, supplement evidence, reports | Intake candidate | nonprofit eligibility needs verification | Minimize fields; response becomes review candidate |
| Google Drive | Evidence document vault | Evidence store, not reviewer | needs ACL audit | Store refs/hash in Odoo |
| Google Sheets | Migration/reporting during pilot | Temporary report | not production authority | No sensitive master DB |
| Google Calendar | Meetings, shifts, care reminders | Reminder mirror | useful | No sensitive diagnosis/identity details |
| Google Tasks | Personal lightweight tasks | Mirror only | limited | No precise dispatch/SLA or sensitive body |
| AppSheet | Possible low-code operations | Candidate only | needs verification | Not before access model exists |
| Looker Studio | De-identified dashboards | Reporting only | needs verification | Aggregated/ref-only |

## 9. UI Completion Requirements

### Header

- Current dashboard type.
- Member ref, org/family ref, review status.
- Total Field decision chip.
- 7D/8D packet status chip.
- Integration health icon group.

### Sidebar

- Home.
- Registration and evidence.
- Review workbench.
- Merchant.
- Property.
- Family.
- Volunteer/social work.
- POS/device display.
- AI XiaoJ.
- Integrations.

### Main Workspace

- First card: next action.
- Second band: role-specific work.
- Third band: review/evidence/integration status.
- Empty states must explain what is missing without exposing sensitive data.

### AI Assistant Panel

- XiaoJ may summarize, classify, draft, translate, and generate checklists.
- XiaoJ must not approve, appoint, pay, dispatch as final action, read member plaintext, or bypass Total Field.

### Evidence Panel

Always show:

- `evidence_ref`,
- `packet_hash`,
- `reviewer_id` or reviewer ref,
- `reviewed_at`,
- `decision`,
- `reason`,
- Total Field pre/post status.

## 10. Acceptance Tests

### P1 Demo Shell

- Desktop, tablet, mobile, counter display, and customer display screenshots render without overlap.
- Each dashboard has three or fewer next actions.
- Mock payload contains no cleartext member name, phone, address, national ID, or OAuth token.
- Integration cards show `needs_verification` when no credentials are configured.

### P2 Review Workbench

- Owner can approve owner-required records.
- Manager cannot approve owner-required records.
- Reviewer cannot approve own registration.
- Approval requires reason and evidence_ref.
- Rejection requires reason.
- Review event is append-only.

### P3 Organization Membership

- Affiliation claim creates no authority.
- Approved merchant responsible person can approve only same-merchant normal staff.
- Merchant responsible person cannot approve property member.
- Property responsible person cannot approve merchant member.

### P4 Family Organization

- Family head cannot self-appoint.
- Family head can approve only same-family member.
- Family member cannot appoint another head.
- Care reminders mirror to Google Calendar/Tasks without sensitive body text.

### P5 Integrations

- Google Forms response imports as candidate, not approved membership.
- Google Tasks sync uses title/ref only.
- LINE WORKS notification contains no member plaintext.
- Missing credentials show controlled setup state, not traceback.

### P6 Hardening

- Route scan produces no new `auth='none'` route for member/review UI.
- New review routes do not use `cors='*'`.
- Public demo routes are read-only or sandbox-only.
- AI chat panel cannot access registration plaintext.

## 11. LAND Task Sequence

### LAND 1: `AI_BROWSER_MEMBER_UI_DEMO_SHELL_LAND_P1`

Allowed:

- Add sandbox AI Browser controller/template/assets.
- Use mock dashboard payload.
- Add no DB models.

Forbidden:

- No Odoo DB write.
- No external API call.
- No secret read.
- No member plaintext.

Validation:

- Static route review.
- Browser screenshots.
- Mock payload PII scan.

### LAND 2: `AI_BROWSER_REVIEW_WORKBENCH_LAND_P2`

Allowed:

- Add review event model.
- Add evidence_ref/reason requirements.
- Add owner/member manager access rules.

Requires:

- Odoo module upgrade approval.
- Migration note.
- Security access and record rule tests.

### LAND 3: `AI_BROWSER_ORG_MEMBERSHIP_LAND_P3`

Allowed:

- Add organization entity/membership/policy models.
- Map merchant/property/nonprofit/association roles.
- Build org responsible reviewer queue.

Requires:

- Cross-org denial tests.
- Affiliation-claim-is-not-authority tests.

### LAND 4: `AI_BROWSER_FAMILY_ORG_LAND_P4`

Allowed:

- Add family organization/membership/invitation models.
- Build family head review queue.

Requires:

- Same-family review tests.
- Minor/elder privacy checks.

### LAND 5: `AI_BROWSER_INTEGRATION_ADAPTERS_LAND_P5`

Allowed:

- Add config-status UI.
- Add candidate-only Google/LINE adapter contracts.
- Add no-secret setup placeholders.

Requires:

- Verify real account availability separately.
- OAuth scopes documented before enabling.

### LAND 6: `AI_BROWSER_ROUTE_AND_EVIDENCE_HARDENING_LAND_P6`

Allowed:

- Route risk report.
- CSRF/CORS/auth hardening for member/review routes.
- Total Field postflight seal generation.

Requires:

- Route regression tests.
- Redteam tests.

## 12. Next Safe Command

```bash
tools/d8_codex_mandatory_workflow.sh finalize --task-name AI_BROWSER_MEMBER_UI_GENERATIVE_RECONSTRUCTION_GAP_FILL --task-state PASS --result-summary "Generated decision-complete AI Browser member UI generative reconstruction gap-fill packet without Odoo DB write, secret read, member plaintext read, service restart, or deploy."
```
