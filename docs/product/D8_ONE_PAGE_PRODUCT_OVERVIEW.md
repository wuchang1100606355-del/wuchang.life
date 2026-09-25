# D8 One-Page Product Overview

## Product

D8 Total Field Agent Governance Console

D8 總場代理治理操作台

## One-Line Positioning

A local-first governance console that checks D8 memory, redteam history, possible alerts, and guard evaluations before AI agents touch code, Odoo/POS evidence, or local operations.

## First Wedge

AI Agent Safety / Governance for Odoo + POS + cafe/community local operations.

First pilot field:

聊國咖啡館重新總店 / Odoo POS / 主權 AI 營運安全操作台

## Problem

AI coding agents and store-operation assistants are powerful, but small teams often lack a practical local safety layer before an agent reads files, runs commands, inspects Odoo/POS state, creates reports, or escalates operational decisions.

## Solution

D8 creates a repeatable local governance loop:

1. Check total field state.
2. Run mandatory preflight.
3. Review possible alerts.
4. Review redteam history.
5. Decide PASS / INFO / WARN / HOLD / BLOCK.
6. Produce a sealed report.
7. Write failures back as non-executable future guardrails.

## Evidence Base

- `d8_memory`: 4741 local records.
- `d8_redteam_events`: 13 quarantined redteam records.
- `d8_possible_alerts`: 8 candidate alert records.
- Phase13 product blueprint ready.
- Phase14 external check recommends continuing with adjusted positioning.
- Odoo eventbook evidence is DB-scoped to `wuchang_odoo`.
- Safety flags across recovery seals: no secret read, no member plaintext, no Odoo DB write, no POS order, no payment.

## Core Modules

- Local D8 memory.
- Redteam quarantine.
- Possible alerts.
- Guard evaluator.
- Mandatory preflight.
- Operator console.
- Dashboard.
- Voice/text operator.
- Odoo/POS read-only safe bridge.
- Recovery and handoff seals.

## Buyer

- Cafe/community operators using Odoo/POS.
- Small development teams using AI coding agents.
- Local-first organizations with privacy constraints.
- SMB teams needing practical AI guardrails without enterprise GRC complexity.

## Why Now

The coding-agent market is crowded, but agent governance for local SMB operations is still under-served. D8 should not compete as another coding agent; it should govern agent use before action and preserve incident evidence after failure.

## Pilot Offer

Four-week local pilot:

- Install local D8 governance package.
- Configure cafe/Odoo/POS read-only evidence boundary.
- Run preflight + alerts + redteam + seal demo.
- Perform one operator dry-run.
- Deliver sealed pilot report and next-step recommendation.

## Commercial Model Draft

- Setup fee for local install and first safety boundary map.
- Monthly maintenance for backups, guard review, reports, and redteam/alert hygiene.
- Odoo/POS safe bridge add-on.
- Custom governance rules for cafe, association, committee, or merchant workflows.
- On-prem/local-first package for strict privacy teams.

## What Not To Claim

- Not an autonomous coding agent replacement.
- Not an Odoo AI or Odoo POS replacement.
- Not production-ready until formal release tests pass.
- Not legal compliance or patent novelty advice.
- Not absolute safety.
- No secrets, member plaintext, payment, or POS order writes in MVP.
