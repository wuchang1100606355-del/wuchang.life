# D8 Market Ready Product Blueprint

## Product Name

D8 Total Field Agent Governance Console

D8 總場代理治理操作台

## First Landing Vertical

聊國咖啡館重新總店 / Odoo POS / 主權 AI 營運安全操作台

## One-Line Product Statement

讓 AI coding agent、店務 AI、Odoo/POS 接線任務，在執行前先查總場狀態、紅隊錯誤經驗與可能錯誤告警，再決定 PASS / INFO / WARN / HOLD / BLOCK，並把失敗回寫成未來防線。

## Evidence Base

This blueprint is grounded in local D8 material only:

- `d8_memory`: 4741 local records.
- `d8_redteam_events`: 13 quarantined redteam records.
- `d8_possible_alerts`: 8 candidate alert records.
- `d8_guard_evaluations`: 54 guard evaluation records.
- Product surface docs in `docs/product/`.
- Total Field docs in `docs/total_field/`.
- Odoo eventbook recovery/reconciliation reports and seals under `runtime/d8_db/reports/` and `runtime/total_field/status/`.

No web search, external API, or embedding was used for this blueprint.

## Target Customer

- Small development teams using Codex, Claude Code, or other AI coding agents.
- Small organizations with Odoo, POS, member, cafe, counter, accounting, marketing, or community operations.
- Community associations and cafe teams with multiple roles and limited technical staff.
- Teams that need an agent safety layer before allowing AI-assisted local operations.

## First Product Wedge

D8 should not be sold as generic AI, generic SaaS, or a normal chatbot.

The first wedge is:

AI Agent Safety / Governance for Odoo + POS + Local Operations

The first proof field is 重新店: a real local operations setting where agent tasks need preflight, sealed evidence, and strict no-payment/no-order/no-member-plaintext boundaries.

## Core Modules

- D8 local memory: the local evidence base for agent state, files, reports, and historical decisions.
- Redteam quarantine: failure records stay non-executable and isolated.
- Possible alerts: candidate warnings that can be checked before new work starts.
- Guard evaluator: PASS / INFO / WARN / HOLD / BLOCK task gating.
- Mandatory preflight: every task creates a bounded capsule before action.
- Task capsule: durable scope, allowed paths, forbidden paths, and expected output.
- Writeback loop: failures become future warnings and guardrails.
- Operator console: local command surface for status, alerts, redteam, and evals.
- Dashboard: local read-only overview for operators and reviewers.
- Voice/text operator: hands-free and accessibility-friendly local command surface.
- Odoo/POS read-only safe bridge: evidence collection without order/payment writes.
- Recovery / handoff seal: sealed state for audit, recovery, and agent handoff.

## Competitive Edge

D8 is not:

- A normal chatbot.
- A normal RAG dashboard.
- A normal Odoo addon.
- A tool that lets AI directly operate production.
- A generic prompt library.

D8's edge is the closed safety loop:

1. The agent checks local memory, redteam history, possible alerts, and guard rules before acting.
2. The task is bounded by a mandatory preflight capsule.
3. Unsafe or uncertain work becomes HOLD/BLOCK instead of hidden execution.
4. Failures are written back as quarantined, non-executable redteam records.
5. Redteam records do not pollute the main memory path and are reverse-indexed only.
6. Future agents inherit operational caution as searchable local evidence.

## MVP Landing

The first sellable MVP should stay local-only and read-only:

- Local dashboard at `127.0.0.1`.
- Voice/text command runner for safe operator queries.
- Mandatory preflight before every agent task.
- Odoo/POS read-only manifest.
- No payment capture.
- No POS order creation.
- No member plaintext.
- Sealed reports for every meaningful operation.
- Incident recovery runbook and governance seal.

## Revenue Model Draft

- Setup fee for local D8 governance install and first vertical configuration.
- Local agent governance package for AI coding agent teams.
- Monthly maintenance for guard updates, sealed reports, and backup checks.
- Odoo/POS safe bridge add-on for read-only operational evidence.
- Custom governance rules for cafe, association, committee, or merchant workflows.
- On-prem / local-first package for teams that cannot send operational context to cloud services.

## Market Proof Needed Later

These require later public research and human approval:

- Public competitor research.
- Patent prior art search.
- Odoo ecosystem comparison.
- AI coding agent safety comparison.
- Pricing validation.
- Customer willingness-to-pay interviews.

## What Not To Claim

- Do not claim absolute safety.
- Do not claim the system is unbreakable.
- Do not claim production readiness until formal tests and release gates pass.
- Do not publish secret values, internal dictionaries, weights, or sensitive implementation-only artifacts.
- Do not market redteam records as executable automation.
- Do not imply AI can place orders, collect payments, or read member plaintext in the MVP.

## Current Product Readiness

Market-ready blueprint status: ready for local demo and pilot proposal preparation.

Production release status: not released.

Recommended next action: package the local-only MVP demonstration around dashboard, console, preflight, redteam/alert review, Odoo/POS read-only evidence, and sealed recovery.
