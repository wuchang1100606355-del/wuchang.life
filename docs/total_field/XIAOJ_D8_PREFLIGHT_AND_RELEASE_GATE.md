# XiaoJ D8 Preflight And Release Gate

STATE=XIAOJ_D8_PREFLIGHT_AND_RELEASE_GATE_READY
RUN_ID=D8_MANDATORY_TASK_20260624_133320_XIAOJ_SOVEREIGN_AV_ORDERING_RESEARCH_TO_ARCH_PACKET

## Purpose

Define the release gates required before XiaoJ can move from shadow / candidate mode into live POS operation.

## Current Binding State

Current safe state remains:

- Track A live operation: human-only POS.
- Track B XiaoJ shadow: candidate-only.
- POS order release: HOLD.
- Payment release: HOLD.

## Mandatory Discovery Before Runtime Action

Before any future runtime action:

```bash
tools/d8_codex_mandatory_workflow.sh start ...
tools/d8_total_field_console.sh status
tools/d8_total_field_console.sh alerts --limit 20
tools/d8_total_field_console.sh redteam --limit 20
tools/d8_total_field_console.sh evals --limit 20
```

Do not restart, deploy, write Odoo DB, create POS orders, or capture payment before the relevant release packet.

## Release Matrix

| Gate | Required PASS |
| --- | --- |
| Field observation | current runtime observed without secrets |
| Total Field consult | D8 status / alerts / redteam / evals reviewed |
| Menu source lock | real cafe menu only; no invented products |
| Auth route | LINE / Google / association route verified without member plaintext |
| Broker | local broker policy and ref-only schema verified |
| POS candidate | candidate order can be produced and rejected safely |
| Human confirmation | staff/customer confirmation UI or procedure verified |
| Rollback | soft, functional, and infra rollback documented |
| Payment | cash/payment path separately authorized |

## Rollback Levels

| Level | Action |
| --- | --- |
| Soft rollback | disable voice, keep touch/kiosk/manual POS |
| Functional rollback | disable XiaoJ candidate, return to human POS |
| Infra rollback | stop broker while Odoo/POS stays available |

## Stop Conditions

- `SECRET_VALUE_EXPOSED=TRUE`
- `MEMBER_PLAINTEXT_READ=TRUE` without explicit scope
- `ODOO_DB_WRITE=TRUE` without release
- `POS_ORDER_CREATED=TRUE` without release
- `PAYMENT_CAPTURE=TRUE` without release
- `SERVICE_RESTART=TRUE` without approval
- `DEPLOY=TRUE` without approval

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
