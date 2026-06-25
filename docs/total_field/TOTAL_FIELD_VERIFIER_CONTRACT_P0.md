# Total Field Verifier Contract P0

STATE=TOTAL_FIELD_VERIFIER_CONTRACT_P0_READY
SCOPE=PUBLIC_FILING_SAFE

## Authority

The Total Field Verifier is the final authority between candidate generation and any real action.

Cloud output, model confidence, transcript confidence, UI confidence, or broker confidence is never final authority.

## D1-D8 Verification

| Dimension | Required Check |
| --- | --- |
| D1 Intent | Intent is bounded and does not contain forbidden action. |
| D2 State | Input state and proposed output state are valid. |
| D3 Coordinate | Node, route, actor, and scope refs are allowed. |
| D4 Evidence | Evidence refs exist and do not expose raw secret/member data. |
| D5 Execution | Execution remains candidate-only unless separately released. |
| D6 Generative Transmission | Cloud/model output is candidate-only and non-authoritative. |
| D7 Risk | Risk flags are explicit; HOLD/BLOCK stops action. |
| D8 Envelope | Hash, TTL, pollution guard, and replay boundary are valid. |

## Decisions

| State | Meaning |
| --- | --- |
| `ACCEPTED` | Candidate passes verifier review and may proceed to the next non-executing review layer. |
| `REJECTED` | Candidate is invalid and must not proceed. |
| `HOLD` | Candidate requires human, legal, safety, policy, or evidence review before any next step. |
| `REDTEAM` | Candidate is routed to non-executable redteam evidence for boundary analysis. |
| `DEAD_LETTER` | Candidate is sealed as unresolved, expired, malformed, unsafe, or non-actionable. |

Human review is represented as:

```text
state=HOLD
reason_code=HOLD_FOR_HUMAN
```

## Non-Float Anti-Hallucination Rule

No floating model score can authorize execution.

Execution requires symbolic refs, evidence refs, policy refs, envelope hash validation, and human or approved verifier release.

## Member Boundary

Member GT packets may contain only:

- `MEMBER_REF`
- `MEMBER_PACKET`
- `BENEFIT_REF`
- role/permission/evidence/TTL refs

They must not contain member plaintext.

## Cloud Boundary

Cloud candidate packets and cloud result packets:

- are candidate-only.
- must set `must_not_execute=true`.
- must set `requires_total_field_verify=true`.
- are not committable.
- cannot write Odoo/POS/DB.
- cannot capture payment.
- cannot deploy or restart services.
- cannot become normal memory without verification.

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
