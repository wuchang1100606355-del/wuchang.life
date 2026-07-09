# W7TP Sovereign AI Member XiaoJ Translator Spec

STATE=W7TP_SOVEREIGN_AI_MEMBER_XIAOJ_TRANSLATOR_SPEC_READY
AUTHORITY=TOTAL_FIELD
MODE=CANDIDATE_ONLY_NO_DB_WRITE_NO_DEPLOY

## 1. Purpose

This specification defines how a small local LLM, scene-facing XiaoJ, cloud candidate completion, and Total Field hard boundaries work together inside the sovereign AI member system.

The system goal is not to give the model authority. The goal is to translate member intent into bounded candidate packets, turn refusal into useful human alternatives, and let the Total Field verifier decide `PASS`, `HOLD`, `WARN`, or `BLOCK`.

## 2. Roles

### Local LLM

The local LLM is a natural-language to Total Field candidate translator.

It may:

- translate user language into intent, state, coordinate, evidence, execution, generative transport, risk, and envelope candidate fields.
- create a candidate packet for verifier review.
- produce no-plaintext summaries and refs.

It must not:

- read member plaintext outside the local server boundary.
- execute DB write, router write, deployment, restart, payment, or lock-control actions.
- decide final authority.

### Scene XiaoJ

Scene XiaoJ is the humanized compliance translator.

It turns hard Total Field decisions into acceptable human replies:

- `BLOCK` becomes a clear refusal plus safe alternatives.
- `HOLD` becomes a request for the missing authorization, source, consent, or human review.
- `WARN` becomes a bounded next step with risk language.
- `PASS` remains candidate-only until the relevant formal release packet is sealed.

Example behavior: if a user asks to open a neighbor's door, XiaoJ refuses the unsafe act and offers to ring the bell, send a message, ask the building manager, or contact the proper emergency channel.

### Cloud Candidate Completion

Cloud support is a candidate packet completer. It may improve wording, tone, structure, translation, and safe alternatives. It must not supply forbidden operations, personal plaintext, raw credentials, or final authority.

Cloud input and return packets must be:

- `candidate_only=true`
- `requires_total_field_verify=true`
- `final_authority=total_field_verifier`
- `key_ref_only=true`

### Total Field Verifier

The Total Field verifier is the only final authority for:

- `PASS`
- `HOLD`
- `WARN`
- `BLOCK`

Cloud, local LLM, scene XiaoJ, browser UI, Odoo UI, and member devices can only propose candidate states.

## 3. ADI And 8-in-One Total Field

ADI is a 5D metric-index layer. It is not an ordinary table and does not contain the 8D packet as columns.

The 8-in-one Total Field consists of:

1. intent field
2. state field
3. coordinate field
4. evidence field
5. execution field
6. generative transport field
7. risk quarantine field
8. envelope verification field

Generative transport is defined as:

```text
state_packet + ref + reconstruction + equivalent_state + total_field_verify
```

It is not a storage transport or sensitive-content transfer design.

### 8 State Field Completion

Every translator packet must expose these keys with `summary`, `refs`, and `status`:

| Key | Field | Required content |
| --- | --- | --- |
| `intent_field` | intent field | member request intent and compliance translation target |
| `state_field` | state field | candidate, hold, warning, block, or pass state |
| `coordinate_field` | coordinate field | organization container ref, member identity ref, policy ref, or scene ref |
| `evidence_field` | evidence field | source refs, consent refs, verifier refs, or sealed evidence refs |
| `execution_field` | execution field | no DB write, no release, no restart, no router write |
| `generative_transport_field` | generative transport field | `mode=state_packet_ref_reconstruction_equivalent_state` |
| `risk_field` | risk quarantine field | no secret, no member plaintext, no resident plaintext, no raw image, no DB write, no release, no restart, no router write |
| `envelope_field` | envelope verification field | `final_authority=total_field_verifier`, `human_review_required=true`, `candidate_only=true` |

The generative transport field must set:

```text
mode=state_packet_ref_reconstruction_equivalent_state
not=file_copy/cloud_sync/plaintext_transport
```

## 4. BYOK Mode

BYOK means bring-your-own-key by reference only.

For members with their own AI/API provider:

- local system stores `key_ref`, `provider_ref`, and `policy_ref`.
- local runtime pulls or asks for a cloud candidate packet through those refs.
- raw credentials are never stored in Total Field, samples, schema, report, or cloud packet payload.

For members without their own provider:

- Total Field XiaoJ may request a bounded candidate wording packet through the approved association lane.
- this path still returns candidate wording only.
- Total Field verifier still decides.

## 5. Privacy Boundary

Member plaintext stays on the local member server or authorized local service boundary.

It does not enter:

- Total Field packet body.
- cloud candidate request.
- cloud candidate return.
- 8D code.
- browser-visible public card.

Allowed values are refs, hashes, bucket labels, policy refs, source refs, evidence refs, and display-safe public organization data.

## 6. Management Committee Boundary

A management committee or building committee is not active by default.

Until representative authority, source review, consent or application reference, privacy review, human review, and activation packet sealing are complete, the status is:

```text
management_committee_authorization_status=HOLD_UNTIL_AUTHORIZED
membership_status=pending_group_member
activation_status=inactive
display_badge=未生效團體會員
```

## 7. Cloud Request Boundary

Cloud request packets must carry only:

- bounded intent refs.
- policy refs.
- provider refs.
- key refs.
- candidate schema refs.
- risk constraints.
- safe style/tone instructions.

Cloud request packets must not carry:

- raw member identity.
- resident plaintext.
- exact private address.
- personal contact.
- raw credential values.
- internal review notes.
- formal execution commands.

## 8. Humanized Compliance Response

A humanized response contains:

- `total_field_decision`
- `humanized_response`
- `safe_alternatives`
- `risk_field`
- `redteam_status`

It must make the refusal useful without weakening the boundary. It can offer lawful and consent-based next steps, but it cannot convert a blocked action into an alternate unauthorized execution path.

## 9. Safety Flags

NO_SECRET=TRUE
NO_MEMBER_PLAINTEXT=TRUE
NO_RESIDENT_PLAINTEXT=TRUE
NO_RAW_KEY_TOKEN_PASSWORD=TRUE
NO_DB_WRITE=TRUE
NO_DEPLOY=TRUE
NO_RESTART=TRUE
NO_ROUTER_WRITE=TRUE
NO_GIT_ADD_DOT=TRUE
