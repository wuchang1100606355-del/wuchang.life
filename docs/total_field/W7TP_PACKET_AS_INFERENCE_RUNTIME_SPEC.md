# W7TP Packet-as-Inference Runtime Spec

## Technical Position

This runtime treats an 8D packet as the inference state itself, not only as a data transport wrapper. Each packet is a bounded state transition with intent, state refs, coordinate, evidence, execution limits, GT refs, risk, and a sealed envelope.

The prototype is model-free. It uses lookup tables, deterministic rules, a verifier, and template rendering to produce AI-like task output inside a bounded cafe/order-assist field.

## Model Inference Contrast

Model inference usually runs token by token:

```text
weights + prior tokens -> next token
```

W7TP packet inference runs packet by packet:

```text
8D packet + lookup table + rule + verifier -> next state packet
```

The packet chain replaces a real-time model path for this bounded flow. The system does not make packets into a neural network; it makes packets the explicit state of inference.

## Seven-Step Packet Chain

The runtime emits eight packets, with S0 as the input event and S1-S7 as the seven inference layers:

```text
S0_INPUT_EVENT
S1_INTENT_PACKET
S2_ROUTE_PACKET
S3_STATE_PACKET
S4_RISK_PACKET
S5_CAPABILITY_PACKET
S6_OUTPUT_PACKET
S7_FEEDBACK_CANDIDATE_PACKET
```

Every packet contains:

```text
packet_type
version
step
parent_packet_hash
D1_intent
D2_state
D3_coordinate
D4_evidence
D5_execution
D6_gt
D7_risk
D8_envelope
```

`D8_envelope` contains `packet_id`, `created_at_unix`, `ttl_seconds`, `nonce`, `packet_hash`, and `seal`. Each packet after S0 points to the prior packet hash.

## Verifier Authority

The verifier is deterministic and is the only authority for `ALLOW`, `HOLD`, `BLOCK`, or `CONTINUE`.

Minimum authority rules:

- Payment request produces `HOLD`; `payment_capture` is forbidden.
- Member plaintext request produces `BLOCK`.
- Allergy or intolerance signal produces `HOLD`.
- Low intent confidence produces `HOLD`.
- Normal recommendation may continue to output and finish as `ALLOW`.

The verifier does not call a model and does not delegate authority to an LLM.

## Model Candidate Lane

With API access, a future model lane may produce candidate packets only. Without API access, the lookup packet runtime remains complete.

In both modes:

- Model output is never the verifier.
- Model output never decides `ALLOW`, `HOLD`, or `BLOCK`.
- Candidate packets must pass the same packet-chain verifier.

## Storage Principle

Packets are not intended for full unbounded storage. Durable records should keep bounded refs and integrity material:

```text
schema_ref
table_ref
rule_ref
hash
seal
evidence_ref
```

Member plaintext, secrets, raw audio, direct payment data, and production execution authority are outside this runtime.

## Safety Limits

The prototype is local and stdlib-only. It must keep:

```text
SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
DB_WRITE=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
EXTERNAL_API_CALL=FALSE
MODEL_REQUIRED=FALSE
LLM_AUTHORITY=FALSE
```

It must not read environment files, keys, rclone config, Google/OpenAI credentials, or member plaintext. It must not restart services, run migrations, write Odoo/POS records, capture payment, deploy, or release to production.
