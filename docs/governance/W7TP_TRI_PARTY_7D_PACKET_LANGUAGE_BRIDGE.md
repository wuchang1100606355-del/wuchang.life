# W7TP Tri-Party 7D Packet Language Bridge

Status: `plan-only`

## Purpose

The tri-party 7D packet is a shared, redacted task-language envelope for:

1. `local_xiaoj_router`: local XiaoJ / W7TP Router / Gateway.
2. `code_agent`: CODE / Codex / local development agent.
3. `cloud_provider_lane`: OpenAI, Gemini, Google, or other cloud API lanes.

The same task intent can be parsed by all three parties, while each receives
only the fields required for its bounded role.

## Engineering Boundary

The 7D packet does not replace TCP/IP, HTTP, Docker, or VPN. It is a local
XiaoJ governance layer, task layer, state layer, and audit layer carried over
existing technical transports.

The cloud API is a provider lane only, not the governance authority. CODE is a
bounded development agent only, not an all-powerful administrator.
`local_xiaoj_router` retains intent judgment, redaction, routing, audit, and
dead-letter authority.

## Seven Dimensions

| Dimension | Purpose |
| --- | --- |
| `d1_identity_scope` | Name the authority and party roles without exposing member identity. |
| `d2_intent` | Describe the bounded task class and redacted task intent. |
| `d3_context_space` | Define allowed local context and provider-safe summary scope. |
| `d4_privacy_boundary` | Enforce non-PII and credential exclusion before any provider lane. |
| `d5_risk_policy` | Declare risk level, human review, and hardwall handling. |
| `d6_execution_lane` | Define local, code-agent, and provider lanes without authorizing execution. |
| `d7_audit_result` | Record audit hashing, decision state, and dead-letter routing. |

## Visibility Rules

### local_xiaoj_router

May see:

- Full local governance packet.
- Policy gate outcome.
- Redaction proof.
- Audit decision.
- Dead-letter route.

### code_agent

May see only the bounded development assignment:

- Task ID.
- Allowed files.
- Validation commands.
- Forbidden actions.
- Commit rule.
- Focused Git status rule.

### cloud_provider_lane

May see only provider-safe material:

- `redacted_intent_summary`.
- `provider_visible_summary`.
- Provider lane and task class.
- Non-PII constraints.
- No-credentials and no-raw-member-data rules.

Must not see token, password, private key, credentials, raw member PII,
router secret, local inventory, formal database write authority, member
plaintext, or private evidence-chain raw data.

## Control Rules

- `mode` remains `plan_only`.
- `authority` remains `local_xiaoj_router`.
- `cloud_allowed` defaults to `false`.
- High-risk packets require human review.
- Redaction and audit hash evidence are required before any separately approved provider action.
- Hardwall violations route to dead letter rather than being executed.

## Forbidden Actions

The packet must prohibit cloud-side Git commit or push, router writes, remote
shell commands, formal database writes, financial settlement, emergency
broadcast without review, credential export, and raw PII cloud upload.

## Current Task Assurance

This specification, template, schema, and linter perform local static
validation only. They make no cloud call, read no API key, save no secret, use
no SSH, and start no container.
