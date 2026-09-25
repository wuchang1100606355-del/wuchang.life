# D8 Cafe Pilot Proposal

## Pilot Name

D8 Total Field Agent Governance Console pilot for 聊國咖啡館重新總店.

## Pilot Objective

Demonstrate a local-first AI agent governance workflow for cafe/Odoo/POS operations without writing Odoo data, creating POS orders, capturing payments, reading member plaintext, deploying services, or exposing secrets.

## Pilot Scope

Included:

- Local D8 status dashboard.
- Operator console status, alerts, redteam, and guard evals.
- Mandatory preflight before agent tasks.
- Read-only Odoo/POS evidence manifest.
- Voice/text operator dry-run.
- Sealed pilot report.
- Incident recovery story based on Odoo eventbook governance recovery.

Excluded:

- Production Odoo writes.
- POS order creation.
- Payment capture.
- Member plaintext access.
- External API.
- Embedding generation.
- Production deploy.

## Participants

- Store owner / developer.
- Store staff.
- AI operator.
- Reviewer / auditor.
- Optional association manager.

## Week-by-Week Plan

### Week 1: Setup And Boundary Confirmation

- Confirm local D8 package status.
- Confirm no secret/member/payment/order-write boundaries.
- Prepare pilot task capsules.
- Prepare demo dashboard and console sequence.

### Week 2: Read-Only Evidence Walkthrough

- Run D8 status.
- Run alerts/redteam/evals.
- Show Odoo/POS read-only boundary.
- Show eventbook evidence from DB-only reconciliation.
- Record operator questions.

### Week 3: Operator Dry-Run

- Store operator runs a guided preflight.
- Operator reviews alerts.
- Operator reviews redteam history.
- Operator creates a sealed report.
- Reviewer checks safety flags.

### Week 4: Pilot Review

- Summarize outcomes.
- List confusion points.
- Refine warning language.
- Decide whether to proceed to paid local package.

## Success Criteria

- Operator can run status and preflight.
- Operator can understand PASS / WARN / HOLD / BLOCK.
- Operator can identify that redteam records are not executable.
- Operator can produce or locate a seal.
- No secret read.
- No member plaintext read.
- No Odoo DB write.
- No POS order.
- No payment.
- No deploy.

## Deliverables

- Pilot kickoff checklist.
- Dry-run task capsule.
- Read-only Odoo/POS evidence manifest.
- Operator feedback notes.
- Final sealed pilot report.
- Recommendation: continue / adjust / hold.

## Pilot Commercial Offer Draft

- Setup fee: local installation, safety boundary map, and first pilot package.
- Monthly maintenance: backup check, guard rule review, report/seal hygiene.
- Odoo/POS safe bridge add-on: read-only evidence and manifest generation.
- Custom governance rules: cafe, association, committee, merchant workflows.

## Pilot Decision Gate

Pilot may proceed only if:

- Human owner approves local-only read-only scope.
- No production action is required.
- No payment/order/member plaintext feature is requested.
- Every pilot run creates a seal.
