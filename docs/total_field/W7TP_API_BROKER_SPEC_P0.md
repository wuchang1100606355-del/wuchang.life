# W7TP API Broker Spec P0

STATE=W7TP_API_BROKER_SPEC_P0_READY
SCOPE=PUBLIC_FILING_SAFE

## Purpose

The W7TP API Broker is a boundary component for converting local verified state into candidate-only cloud requests and returning candidate results for Total Field verification.

It does not grant cloud authority, payment authority, POS authority, member plaintext authority, or production execution authority.

## D1-D8 Fixed Chain

| Dimension | Name | Broker Role |
| --- | --- | --- |
| D1 | Intent | Declare the user/task intention in bounded symbolic form. |
| D2 | State | Capture current local state and allowed state transitions. |
| D3 | Coordinate | Bind request to local node, route, actor ref, time, and scope refs. |
| D4 | Evidence | Attach evidence refs, source refs, and hash refs, not raw secrets or member plaintext. |
| D5 | Execution | Mark requested action as candidate-only unless Total Field Verifier releases it. |
| D6 | Generative Transmission | Package state for model/cloud candidate generation without transferring final authority. |
| D7 | Risk | Include risk flags, stop conditions, and required human review gates. |
| D8 | Envelope | Seal candidate request with TTL, policy, hash, and verifier requirements. |

## Broker Contract

```text
local packet
→ W7TP API Broker
→ Cloud Candidate Packet
→ cloud/model candidate generation
→ Cloud Candidate Result Packet
→ Total Field Verifier
→ accept / revise / reject / hold / block
```

## Hard Rules

- Cloud must be candidate-only.
- Cloud result is never final authority.
- Total Field Verifier is final authority.
- Member plaintext is forbidden.
- Secrets, tokens, private keys, `.env`, and production credentials are forbidden.
- No POS order, payment, deployment, restart, or DB write may be triggered by the broker.

## Allowed References

| Ref | Meaning |
| --- | --- |
| `INTENT_REF` | Bounded intent hash/ref |
| `STATE_REF` | Local state hash/ref |
| `COORDINATE_REF` | Node/route/scope ref |
| `EVIDENCE_REF` | Source/evidence hash ref |
| `MEMBER_REF` | Pseudonymous member ref |
| `BENEFIT_REF` | Benefit or eligibility ref |
| `POLICY_REF` | Guard/policy ref |
| `PACKET_HASH` | Canonical packet hash |

## Forbidden Payload

- member names, phone numbers, addresses, identity numbers.
- raw audio, raw video, raw biometric data.
- secrets, tokens, private keys.
- production DB URI.
- Odoo write commands.
- payment capture instructions.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
D8_LOCAL_DB_WRITE=FALSE
PRODUCTION_DB_WRITE=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE
