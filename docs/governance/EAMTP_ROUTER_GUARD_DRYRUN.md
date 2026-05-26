# EAMTP Router Guard Dry-Run

Status: shadow / dry-run only
Scope: W7TP Router / Gateway governance layer


## Router Terminology Correction

In this system, Router has two layers:

1. Merlin router firmware / physical network router field:
   - LAN/WAN/VPN/firewall/DNS/guest network boundary
   - network-level segmentation and edge traffic governance

2. W7TP Router / Gateway / intent governance field:
   - EAMTP-7D packet translation
   - policy gate decision
   - pending_review
   - dead_letter
   - cloud redaction routing
   - memory/execution boundary

Dead-letter in this document refers to the W7TP intent governance layer, not the Merlin firmware itself.

Merlin may enforce network-level boundaries.
W7TP Router enforces intent-level boundaries.

## Purpose

This module tests the rule:

Dead-letter must be located at the W7TP Router / Gateway governance layer,
before packets enter memory field, execution field, Odoo, cloud compute, or LLM lanes.

## Flow

Entry input
→ EAMTP-7D Translator
→ EAMTP Policy Gate
→ decision:
  - allow_low_risk
  - pending_review
  - dead_letter
→ shadow JSONL ledger

## Dry-Run Boundary

This dry-run module does not:
- restart services
- intercept live traffic
- execute shell commands
- write Odoo / Postgres
- call cloud APIs
- write production memory
- send packets to external AI
- perform git add or commit

## Shadow Stores

runtime/router_guard_dryrun/eamtp_router_guard_dryrun.jsonl
runtime/router_guard_dryrun/allow_low_risk_shadow.jsonl
runtime/router_guard_dryrun/pending_review_shadow.jsonl
runtime/router_guard_dryrun/dead_letter_shadow.jsonl

## Governance Rule

Router decides.
Dead-letter store records.
Nothing executes from dead-letter.
Human review is required for recovery.
