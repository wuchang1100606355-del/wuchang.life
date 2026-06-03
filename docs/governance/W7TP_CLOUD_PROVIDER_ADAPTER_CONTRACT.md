# W7TP Cloud Provider Adapter Contract

Status: `plan-only`

## Purpose

This contract defines a provider-facing lane for a future tri-party 7D packet
broker. OpenAI, Gemini, Google, or a custom provider may receive only a
redacted provider-visible packet after separate local review.

This is a plan-only contract, not an API client. It performs no cloud call and
does not authorize deployment or execution.

## Authority Boundary

- The provider lane is not a governance authority.
- Cloud APIs supply compute, inference, or external service capability only.
- `local_xiaoj_router` retains redaction, policy gate, routing, audit,
  dead-letter, and response-fusion authority.
- CODE and any cloud provider remain bounded agents and may not receive full
  governance authority.

## Provider-Visible Fields

The provider lane is limited to:

- `provider_lane`
- `redacted_intent_summary`
- `provider_visible_summary`
- `task_class`
- `non_pii_constraints`
- `output_format`
- `audit_hash_required`

## Local-Only Fields

The following remain local:

- `full_governance_packet`
- `policy_gate`
- `redaction_proof`
- `private_evidence_chain`
- `local_inventory`
- `credential_store`
- `formal_db_authority`

## Hardwall Rules

- No token, password, private key, credential, raw member PII, member
  plaintext, router secret, local inventory, or formal database write
  authority enters a provider-visible packet.
- No provider may directly commit or push Git changes, write router settings,
  issue remote shell commands, write a formal database, settle finances,
  issue emergency broadcasts without review, export credentials, or upload
  raw PII.
- Any provider response must return to `local_xiaoj_router` for local review,
  audit, and response fusion.

## Current Task Assurance

The contract template, schema, and linter are local static artifacts only.
They make no cloud call, read no API key, save no secret, use no SSH, and start
no container.
