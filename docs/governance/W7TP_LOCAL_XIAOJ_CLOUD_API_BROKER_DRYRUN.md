# W7TP Local XiaoJ Cloud API Broker Dry-Run

Status: `dry-run-only`

## Purpose

This contract defines a local dry-run broker for selecting a provider lane
from redacted, provider-visible packet fields. It validates routing policy,
redaction gates, audit requirements, dead-letter conditions, and the response
fusion return shape without performing any external API request.

## Authority Boundary

- `local_xiaoj_router` is the sole authority for policy gate, redaction,
  routing simulation, audit, dead-letter decisions, and response fusion.
- Cloud provider lanes are compute-only candidates; they are not governance
  authorities.
- Provider lanes may see only redacted provider-visible fields.
- A cloud provider must not receive the full governance packet, API keys,
  secrets, raw member PII, or formal database write authority.

## Dry-Run Flow

1. Validate the redacted intent summary and provider-visible summary.
2. Check privacy level, risk level, human-review requirement, and audit-hash requirement.
3. Simulate provider lane selection under local-first and deny-by-default rules.
4. Route secret, raw-PII, or unreviewed high-risk requests to dead letter.
5. Return a local response-fusion record without taking external action.

## Hardwalls

- No cloud call is authorized by this contract.
- No API key read or secret storage is authorized.
- No SSH, container execution, router write, formal database write, financial
  settlement, or unreviewed emergency broadcast is authorized.

## Promotion Rule

Passing dry-run validation does not authorize a real API call. Any real cloud
API use must be defined in a separate `M27` task and require
`cloud_allowed=true`, a redaction proof, an audit hash, and applicable human
review rules.
