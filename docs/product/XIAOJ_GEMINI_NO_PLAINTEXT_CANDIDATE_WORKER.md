# XiaoJ Gemini No-Plaintext Candidate Worker

STATE=P1_CONTRACT_READY_NO_EXTERNAL_CALL

## Core Answer

Gemini can be useful, but it must not be the authority.

The total-field packet architecture turns Gemini into a high-quality candidate
worker by giving it only a redacted, reconstructable task view plus strict
answer shape, style refs, quality rubric refs, and candidate schema refs.

```text
local total field
  -> generative transmission packet
  -> Gemini candidate worker
  -> candidate response
  -> local reconstruction
  -> local discrete-state verifier
  -> UI candidate / HOLD / local fallback / human release
```

## Why Gemini Gets Better Without Plaintext

Quality improves because the packet gives Gemini a better job boundary:

- `intent_code`: what kind of work this is
- `style_ref`: tone and service style, such as warm XiaoJ service
- `quality_rubric_ref`: what "good" means
- `candidate_schema_ref`: exact response shape
- `route_key`: which local verifier will judge it
- `redacted_task_view`: safe task view with private details removed
- `local_reconstruction_index`: how the local side will rebuild authority state
- `evidence_hash`: what the local verifier expects to match

Gemini no longer receives messy full context. It receives a high-signal,
bounded task. That raises output quality while reducing privacy exposure.

## Why Gemini Is Still Only Labor

Gemini cannot:

- read member plaintext
- receive raw API keys or OAuth tokens
- set `execution_allowed=true`
- approve POS, payment, membership, LINE WORKS, or device actions
- override local verifier
- become a root authority

Gemini can only return:

```text
candidate_text
candidate_json
candidate_summary
candidate_options
candidate_explanation
```

The local total-field verifier remains the only authority.

## Reality / Imagination Boundary

LLM hallucination is conditionally allowed, but only when the total field marks
it as an imagined candidate.

Important definition:

```text
The LLM does not become a truth authority by itself.
The total field supplies the truth boundary, evidence anchors, local
reconstruction context, and verifier status that force each output to remain
REAL_VERIFIED, IMAGINED_CANDIDATE, or EXECUTABLE_AUTHORIZED.
```

In product terms, this means the system can let Gemini create high-quality
humanized service language, scenarios, and options while still preventing it
from pretending that a payment, order, member identity, delivery event, or
legal authority is real without local evidence.

The system must distinguish three layers:

```text
REAL_VERIFIED
IMAGINED_CANDIDATE
EXECUTABLE_AUTHORIZED
```

Allowed:

- Gemini may imagine wording, options, explanations, service tone, and possible
  next steps inside `IMAGINED_CANDIDATE`.
- Gemini may help create a warm, high-quality human interaction when the output
  is clearly labeled as candidate content.
- The UI may show candidate text while local authority is still HOLD.

Forbidden:

- Gemini may not mark a candidate as `REAL_VERIFIED`.
- Gemini may not mark any result as `EXECUTABLE_AUTHORIZED`.
- Gemini may not assert member facts, payment state, POS state, LINE WORKS
  delivery, or legal identity as real unless local reconstruction provides the
  evidence.
- Gemini may not bypass the local verifier by presenting confident language.

Product sentence:

```text
總場允許 LLM 在候選幻境層中創作，但會把真實狀態與可執行狀態留給本地重構、證據封存與離散權威核心判定。
```

Contract fields:

```text
truth_boundary_ref
reality_discrimination_context_ref
evidence_anchor_policy
llm_self_truth_authority=false
real_claim_requires_evidence_ref=true
execution_claim_requires_local_gate=true
```

## What "0 Latency" Means Here

This is not a claim that physical compute time is zero.

It means:

```text
authority decision requires zero external network round trip
```

The local verifier can decide immediately, before Gemini returns:

- whether the packet is allowed to be sent to a cloud candidate worker
- whether UI may show `CANDIDATE_PENDING`
- whether local lookup fallback should answer immediately
- whether the action must HOLD
- whether execution is forbidden until human release

Gemini may improve the candidate answer later, but it is not needed for the
authority decision.

## Generative Transmission Fields

The cloud payload should contain only:

```text
packet_ref
intent_code
state_code
route_key
style_ref
quality_rubric_ref
candidate_schema_ref
redacted_task_view
task_hash
local_reconstruction_index
ttl
nonce
evidence_hash
```

The local side keeps:

```text
member_plaintext
raw_member_profile
raw_api_key
oauth_token
private_lookup_table
full_odoo_record
raw_audio
payment_data
```

## User Experience Model

For the user, the page can feel fast because the local side can instantly show:

```text
本地已判定：可產生候選，正式執行仍需本地驗證。
```

If Gemini is fast, its candidate fills the answer. If Gemini is slow, local
lookup or cached reconstruction can answer first. If Gemini fails, state becomes
`QUEUE_OR_HOLD_NOT_AUTHORITY`, not an error that blocks safe operation.

## Product Rule

```text
Gemini = language and option generation labor
Total Field = authority, reconstruction, verification, evidence, UI state
Human owner/admin = root of trust for formal release
```

## P1 Boundary

The current P1 implementation must remain:

```text
external_api_call=false
raw_api_key_read=false
secret_read=false
member_plaintext_read=false
member_plaintext_to_cloud=false
formal_db_write=false
formal_pos_write=false
payment_capture=false
```

P2 can add a real Gemini connector only after a key-ref vault and member LLM
release gate exist.
