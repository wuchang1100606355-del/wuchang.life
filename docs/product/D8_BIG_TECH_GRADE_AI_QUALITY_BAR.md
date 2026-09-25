# D8 Big-Tech-Grade AI Quality Bar

STATE=D8_BIG_TECH_GRADE_AI_QUALITY_BAR_V1
DATE=2026-06-29
ROOT=/home/taiji_admin/Taiji_Hub

## 0. Product Target

The target is a product-grade AI experience that feels comparable to major AI products in speed, clarity, polish, continuity, and usefulness, while preserving Total Field authority.

中文定位：

```text
使用體驗要像大廠 AI 一樣順、準、穩、好用；
決策權仍屬總場 verifier，不屬於 LLM。
```

This document defines the acceptance bar for the 8D member UI, mobile browser control surface, packet inference runtime, PR layer, and Total Field verifier integration.

## 1. Non-Negotiable Principle

Big-tech-grade quality must not mean unsafe authority expansion.

Hard rules:

- LLM is the PR layer, not Total Field authority.
- The verifier decision is locked and cannot be changed by tone rendering.
- Total Field authority is not member consent authority.
- A safe/verifier-accepted flow must still require explicit member confirmation when member sovereignty is involved.
- Member plaintext, secrets, payment capture, production DB writes, service restarts, and deploys remain blocked unless a separate explicit Total Field release packet authorizes the action.
- Cloud or local model output is candidate-only.
- A polished answer must never hide HOLD, BLOCK, REDTEAM, or DEAD_LETTER.

## 2. User-Visible Quality Bar

The experience must feel premium in five areas.

### Q1. Response Quality

- Answers are concise, context-aware, and written in natural Traditional Chinese by default.
- Every response clearly separates what is known, what is inferred, and what requires verifier or human review.
- The assistant does not over-apologize, ramble, or expose internal machinery unless the user asks.
- Refusals and HOLD states provide a safe next step, not a dead end.
- For association/member/POS contexts, the system uses domain language consistently: total field, verifier, candidate packet, member ref, audit ref, seal.

Acceptance:

- 95% of golden-path prompts produce a useful first answer without manual rewording.
- 100% of safety-sensitive prompts preserve the verifier decision and forbidden actions.

### Q2. Speed And Smoothness

- The UI shows an immediate local acknowledgement within 300 ms.
- First meaningful answer content should appear within 1.5 seconds for local template/lookup paths.
- Longer verifier or model paths must show streaming/progress states instead of a blank wait.
- Fallback from local model to template rendering must be graceful and invisible to normal users except in diagnostics.

Acceptance:

- No mobile flow leaves the user with a blank screen.
- Every pending state displays one of: `checking`, `drafting`, `verifier_review`, `hold`, `accepted`, `blocked`.

### Q3. Continuity

- The system remembers the current task context through packet refs, not raw private memory.
- Follow-up questions should preserve scene context: association, store/POS, property, founder engineering, or general chat.
- If context is insufficient, the system asks one targeted question or creates a HOLD packet.
- The UI exposes a compact conversation/action timeline with audit refs.

Acceptance:

- A user can scan 8D member code, ask a service question, review a draft, and see verifier status without re-entering identity context.
- Context continuity must not require storing raw member plaintext.

### Q4. Product Polish

- Mobile-first UI: thumb-friendly controls, stable layout, readable cards, no overlapping text, no hidden critical status.
- Status chips use familiar labels: Draft, Checking, Needs Review, Accepted, Blocked.
- Actions use clear verbs: Review, Confirm Draft, View Audit, Copy Ref, Retry.
- The system uses progressive disclosure: simple answer first, audit details on demand.
- Empty, loading, error, offline, and blocked states are designed, not left as raw JSON.

Acceptance:

- Tested at common mobile widths: 360, 390, 414, 768 px.
- No primary action requires reading raw packet JSON.

### Q5. Trust And Safety UX

- Safety decisions are explained plainly.
- The user can always see why an action is HOLD/BLOCK when they open details.
- Audit refs and packet hashes are available without exposing private data.
- Redteam or dead-letter outcomes are calm and procedural, not alarming or vague.

Acceptance:

- Every blocked member/payment/secret/production-write prompt returns a safe explanation and next allowed step.
- No response implies the model has final authority.

## 3. System Design For Big-Tech-Grade Feel

### Layer A: Fast Deterministic Core

Use local tables, fixtures, packet extractors, and verifier checks for fast predictable paths:

- 8D lookup.
- member ref validation.
- route classification.
- risk classification.
- template fallback.
- known service intents.

This gives speed and reliability before any model is used.

### Layer B: Premium Language Layer

The PR layer makes verifier-safe outputs feel natural:

- scene-aware tone.
- short answer first.
- helpful next action.
- no raw governance jargon unless needed.
- no decision mutation.

Local model use is optional. If unavailable, template rendering must still feel polished.

### Layer C: Total Field Authority Layer

Total Field keeps the system honest:

- verifier contract checks D8 envelope, nonce, TTL, forbidden ops, risk, and evidence refs.
- candidate outputs remain non-executing until accepted.
- every meaningful action can produce audit/seal evidence.

## 4. Evaluation Harness

Product-grade quality requires repeatable tests, not subjective taste only.

### Golden Prompt Set

Maintain a test set covering:

- normal member status check.
- association service request.
- POS/order draft request.
- payment attempt.
- member plaintext request.
- proxy consent or assumed member authorization.
- secret/token request.
- founder/engineering context.
- ambiguous role claim.
- mobile offline retry.
- verifier HOLD and BLOCK explanation.

Each case must assert:

- final decision unchanged.
- no forbidden data exposed.
- answer is user-useful.
- tone matches scene.
- next step is clear.

### UX Regression Set

For mobile UI:

- capture screenshots for the 360, 390, 414, and 768 px widths.
- verify no text overlap.
- verify loading/error/blocked states.
- verify audit detail panel.

### Quality Metrics

Track at least:

- first response latency.
- verifier latency.
- fallback rate.
- HOLD rate.
- unsafe prompt block rate.
- user retry rate.
- answer rewrite rate.
- audit/seal completion rate.

## 5. Release Gate

The product may be described as major-AI-grade only after all are true:

- Golden prompt pass rate >= 95%.
- Safety-sensitive prompt pass rate = 100%.
- Mobile screenshot checks pass on required widths.
- No member plaintext, secret, payment capture, DB write, deploy, or restart occurs in MVP paths.
- PR layer cannot mutate verifier decision in tests.
- Total Field review packet is accepted or explicitly marked safe for sandbox demo.
- Demo flow can be completed by a non-engineer without reading raw JSON.

Until then, approved wording is:

```text
大廠級體驗目標 / big-tech-grade target
```

Not:

```text
已等同大廠 AI / fully equivalent to major AI products
```

## 6. Immediate Implementation Priorities

1. Build a polished mobile demo path: scan/input 8D ref -> candidate packet -> verifier status -> PR-layer answer -> audit ref.
2. Add golden prompt fixtures for member, POS, payment, secret, role claim, and association service cases.
3. Add a quality verifier that scores response usefulness, safety preservation, tone, and next-step clarity.
4. Add mobile screenshot regression for the core UI widths.
5. Keep all production-impacting actions candidate-only until a separate Total Field release packet exists.

## 7. Product Promise

The promise is not that the model is magically more powerful than every provider.

The promise is:

```text
同級體驗感 + 更強治理邊界 + 本地總場可審計性。
```

That is the competitive position: a polished AI product surface with Total Field governance underneath.
