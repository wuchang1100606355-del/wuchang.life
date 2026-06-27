# D8 Product Requirements MVP

## Product

D8 Total Field Agent Governance Console

## MVP Goal

Provide a local-first governance console that lets operators and developers check D8 status, run preflight, review alerts/redteam history, and collect read-only Odoo/POS evidence before allowing any AI-assisted work to proceed.

## User Roles

- Store owner / developer: configures the local package, reviews seals, and approves guarded work.
- Store staff: runs safe status and evidence checks without writing orders or payments.
- Association manager: reviews member-safe operational status without exposing member plaintext.
- AI operator: runs preflight, console, dashboard, and voice/text commands.
- Auditor / reviewer: checks reports, redteam events, possible alerts, and recovery seals.

## Use Cases

- Check total field status.
- Run mandatory preflight before a task.
- View possible alerts.
- View redteam history.
- Run guard evaluations.
- Run safe Odoo/POS bridge in read-only mode.
- Run voice/text command for local status or safe evidence lookup.
- Create sealed reports.
- Recover from incident with containment, rotation review, and governance recovery seal.

## Acceptance Criteria

- No secret read.
- No secret output.
- No member plaintext read.
- No Odoo DB write.
- No POS order creation.
- No payment capture.
- No production DB write.
- No service restart unless separately approved.
- No deploy.
- No external API.
- No embedding generation.
- Every meaningful action creates or references a seal/report.
- Redteam artifacts remain `executable=false`, `retrieval_scope=redteam_only`, `pollution_guard=true`, and `reverse_index_only=true`.

## Product Dashboard Pages

- Status: D8 memory count, redteam count, alert count, guard eval count, latest seals.
- Alerts: possible alerts filtered by HOLD/WARN/INFO/BLOCK.
- Redteam: quarantined failure history and candidate rules.
- Evals: guard evaluation timeline and decisions.
- Preflight: task capsule summary, scope, allowed paths, forbidden paths.
- POS safe bridge: read-only Odoo/POS evidence and manifest status.
- Reports: local final reports and exports.
- Seals: audit seals, recovery seals, handoff seals.

## Launch Boundary

- Local-only launch.
- `127.0.0.1` dashboard only.
- Read-only Odoo/POS bridge.
- No payment.
- No order write.
- No member plaintext.
- No external API.
- No embedding.
- No production release claim.

## MVP Functional Requirements

1. The operator can run a status command and see D8 memory, redteam, alert, and eval counts.
2. The operator can run mandatory preflight before a task.
3. The operator can inspect possible alerts before allowing work.
4. The operator can inspect redteam history without executing redteam content.
5. The operator can run a read-only Odoo/POS evidence check.
6. The operator can create a sealed report for every verification run.
7. The operator can recover from a governance incident by following containment and review seals.

## MVP Non-Functional Requirements

- All local artifacts remain under repo-controlled runtime/docs paths.
- Reports must avoid raw credentials, private keys, DB URIs, tokens, and member plaintext.
- Dashboard and console must be readable by non-engineer operators.
- Guard decisions must be concise and auditable.
- All public-facing claims must be grounded in local evidence maps.

## Out Of Scope For MVP

- Production Odoo writes.
- POS order creation.
- Payment capture.
- Member plaintext browsing.
- Cloud synchronization.
- External competitor research.
- Patent prior art search.
- Public SaaS hosting.
