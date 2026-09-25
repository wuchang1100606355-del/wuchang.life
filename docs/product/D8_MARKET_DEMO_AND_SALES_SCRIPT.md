# D8 Market Demo And Sales Script

## 30-Second Pitch

D8 Total Field Agent Governance Console is a local-first safety console for AI coding agents and store operations. Before an AI task touches Odoo, POS, files, or reports, D8 checks local memory, redteam history, possible alerts, and guard rules, then returns PASS / INFO / WARN / HOLD / BLOCK with sealed evidence.

## 3-Minute Demo

1. Show D8 status: memory count, redteam events, possible alerts, and guard evals.
2. Run mandatory preflight for a sample task.
3. Show possible alerts and redteam history.
4. Show that redteam records are non-executable and isolated.
5. Show the Odoo/POS read-only evidence boundary.
6. Open the sealed report and seal.
7. Explain that failures are written back into future warnings.

Close with: this is not an AI that directly operates production; it is the local governance layer before any AI action.

## 10-Minute Technical Demo

1. Open the product package manifest.
2. Run `tools/d8_total_field_console.sh status`.
3. Run alerts/redteam/evals console views.
4. Show a preflight capsule from `tools/d8_codex_mandatory_workflow.sh`.
5. Show the material evidence map.
6. Show the Odoo eventbook DB-only status report proving DB-scoped reconciliation.
7. Show the secret containment and governance recovery trail without revealing any secret.
8. Explain the flags: `executable=false`, `redteam_only`, `pollution_guard=true`, `reverse_index_only=true`.
9. Explain the local-only launch boundary: no payment, no POS order, no member plaintext, no external API, no embedding.
10. End with the 30-day roadmap.

## Message For Cafe Owners

This is a safety counter for AI operations. It helps your team ask: what is the current store/system state, what mistakes have happened before, what warnings apply now, and can this action safely proceed? The first version is read-only: no orders, no payments, no member plaintext.

## Message For Small Development Teams

D8 gives AI coding teams a local governance loop: preflight, guard evaluation, redteam writeback, possible alerts, and sealed reports. It turns prior mistakes into future warnings without making those mistakes executable.

## Message For Investors / Partners

D8 targets a practical wedge: AI agent governance for local operations, starting with Odoo/POS/cafe workflows. It is differentiated by local-first evidence, mandatory preflight, sealed reports, and isolated redteam memory.

## Message For Patent / IP Review

The invention direction is not a generic chatbot. It is a generative transfer and governance workflow where state, evidence, guard decisions, redteam writeback, and recovery seals form a repeatable local operational safety system. Public prior art and patent search are still required before making formal IP claims.

## Forbidden Claims

- Do not claim absolute safety.
- Do not claim the system cannot be broken.
- Do not claim production readiness before formal testing.
- Do not expose secrets, internal-only dictionaries, sensitive implementation notes, or private weights.
- Do not claim the MVP can place orders, collect payments, or read member plaintext.
- Do not describe D8 as a normal chatbot, generic RAG UI, or generic Odoo addon.
