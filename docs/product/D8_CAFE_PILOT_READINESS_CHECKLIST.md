# D8 Cafe Pilot Readiness Checklist

## Pilot Scope

Pilot product:

D8 Total Field Agent Governance Console for Odoo/POS local operations.

Pilot mode:

Local-only, read-only, human-reviewed.

## 7-Day Pilot Readiness

- Confirm local demo launcher status.
- Confirm dashboard can run on `127.0.0.1`.
- Confirm voice/text dry-run commands.
- Confirm POS bridge read-only dry-run.
- Confirm public-safe one-pager and Q&A.
- Confirm no secrets, member plaintext, Odoo writes, POS orders, or payments.

## 30-Day Pilot Readiness

- Prepare operator training session.
- Run one guided preflight.
- Run one alerts/redteam review.
- Run one read-only Odoo/POS evidence check.
- Create one sealed pilot report.
- Collect feedback from store owner, staff, AI operator, and reviewer.
- Decide continue / adjust / hold.

## Roles

- 店主 / 開發者: approves local pilot boundary and reviews final seal.
- 店員: observes status and read-only evidence flow.
- 協會管理者: checks governance language and member-safety boundary.
- AI operator: runs preflight, console, dashboard, and dry-run commands.
- reviewer: verifies safety flags and readiness scorecard.

## Hardware Assumptions

- One local machine with repo access.
- Terminal access.
- Local browser for dashboard.
- Audio device optional; dry-run text commands are sufficient.

## Network Assumptions

- Public demo can run without external API.
- Dashboard binds to `127.0.0.1`.
- No public network exposure is required.
- No production service is started.

## Odoo/POS Boundaries

- Read-only evidence only.
- No Odoo DB write.
- No module upgrade.
- No service restart.
- No direct POS control.

## No Payment / No Order Write

- Payment capture is out of scope.
- POS order creation is out of scope.
- Any request for payment/order automation requires separate human approval and a future safety packet.

## No Member Plaintext

- Member plaintext must not be read in the demo or pilot.
- If member evidence is needed later, use a new packet and human review.

## Incident Response

- If a safety flag fails, stop and issue BLOCK.
- If a tool fails without safety impact, issue HOLD and use fallback material.
- If a claim-safety issue appears, rewrite before public use.
- Preserve reports and seals.

## Success Criteria

- Operator can run status, doctor, smoke-test, voice/text dry-run, POS bridge dry-run, and dashboard local bind.
- Reviewer can inspect scorecard and seal.
- Public-safe language is clear.
- No forbidden claim appears in public demo docs.
- No runtime or production action is taken.

## HOLD Criteria

- Any required demo command fails.
- Dashboard binds to an unsafe host.
- Claim-safety scan finds unsafe public language.
- Operator cannot explain read-only/no-payment/no-order/no-member-plaintext boundary.
