# W3 User Stance Total Field Handhold Gate

RUN_ID=W3_USER_STANCE_TOTAL_FIELD_HANDHOLD_20260621
STATE=USER_STANCE_HANDHOLD_GATE

## Purpose
Keep all product landing work aligned with the user's position: Total Field first, no hallucinated facts, unified questions when information is missing, and W7TP/GT8D simplification whenever it safely shortens the path.

## Hard Rules
- readonly_total_field_query_first=true
- user_stance_priority=true
- cloud_codex_gpt_candidate_only=true
- taiji01_total_field_authority=true
- no_self_invented_fact=true
- unified_questions_required_on_gap=true
- fact_label_required=true
- simplification_alert_required=true

## Output Labels
Every product or architecture statement must be labeled as one of:

- FACT
- INFERENCE
- DESIGN_PROPOSAL
- NOT_YET_VERIFIED
- INFO_REQUIRED

## Unified Question Rule
If implementation needs missing facts, do not scatter guesses across the plan. Preserve unresolved issues in a single `NEXT_TOTAL_FIELD_QUERY` block with concrete choices or explicit `INFO_REQUIRED` entries.

## Simplification Rule
If W7TP, GT8D, Spacetime, or 8D packet can simplify the path and the plan does not use it, output:

STATE=SIMPLIFICATION_MISSED_ALERT

If the missed simplification alert is also omitted, output:

STATE=TRUST_BREACH_INTEGRITY_BREACH_ETHICS_BREACH

## Current Safe Next-Question Queue
NEXT_TOTAL_FIELD_QUERY=
請總場指定第一個最小可安全落地模組：
A. POS order_candidate API
B. cashier_confirm gate
C. kitchen_display
D. spacetime_event wrapper
E. Odoo sidecar candidate
F. 8D identity binding skeleton
G. GT8D route table POS expansion

## Stopline
If a statement lacks a label, invents an implementation fact without source, bypasses Total Field discovery, or splits unresolved gaps into scattered assumptions, output:

STATE=HOLD_USER_STANCE_INTEGRITY

