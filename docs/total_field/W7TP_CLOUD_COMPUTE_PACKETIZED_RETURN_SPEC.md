# W7TP Cloud Compute Packetized Return Spec

STATE=W7TP_CLOUD_COMPUTE_PACKETIZED_RETURN_SPEC_READY
SCOPE=PUBLIC_FILING_SAFE

## Purpose

This spec defines how service-time cloud compute output is automatically converted into a candidate-only return packet before it can be shown, stored, or routed to Total Field verification.

The design answers:

> Can the service process automatically package cloud compute and return it?

Answer: yes. Cloud compute may return value as a sealed candidate packet, but it must not return authority.

## Flow

```text
local user/service request
-> W7TP cloud proxy request packet
-> local redaction / no-plaintext check
-> cloud or local-stub candidate compute
-> CLOUD_CANDIDATE_RETURN_PACKET
-> ASSOCIATION_USAGE_ADMISSION_PACKET
-> Total Field verifier
-> ALLOW / HOLD / BLOCK / DEAD_LETTER
```

## Return Packet Contract

Schema:

- `schemas/cloud_proxy/w7tp_cloud_candidate_return_packet_v1.schema.json`

Required constants:

- `schema_version=w7tp.cloud_candidate_return_packet.v1`
- `packet_type=CLOUD_CANDIDATE_RETURN_PACKET`
- `candidate_only=true`
- `must_not_execute=true`
- `requires_total_field_verify=true`
- `member_plaintext_transferred=false`
- `secret_transferred=false`
- `raw_audio_transferred=false`
- `cloud_received_packet_only=true`

## 8D Return Mapping

| Dimension | Return role |
| --- | --- |
| D1 Intent | Carries bounded intent and `INTENT_REF`, not raw prompt authority. |
| D2 State | Carries source packet state ref and candidate status. |
| D3 Coordinate | Binds source to `openwebui_cloud_proxy`, candidate-only cloud lane, `cloud_compute_ref`, provider ref, and compute cost bucket ref. |
| D4 Evidence | Carries source packet hash, candidate payload hash, evidence ref, `behavior_info_ref`, action trace ref, and member tendency ref. |
| D5 Execution | Sets `execution_allowed=false` and lists forbidden operations. |
| D6 Generative Transmission | Marks `packetized_candidate_result` and reconstruction hint ref. |
| D7 Risk | Carries risk flags plus HOLD/BLOCK candidate state. |
| D8 Envelope | Carries TTL, nonce, return packet hash, and verifier requirement. |

## Cloud Compute And Behavior Refs

The return packet must preserve the service value of cloud compute without returning sensitive context or authority.

Required no-plaintext refs:

- `cloud_compute_ref`: compute lane and candidate generation reference.
- `compute_provider_ref`: provider reference only, never credential or endpoint secret.
- `compute_cost_bucket_ref`: usage/cost bucket reference.
- `behavior_info_ref`: redacted behavior summary reference, not raw clickstream.
- `action_trace_ref`: verifier-readable trace reference for the candidate path.
- `member_tendency_ref`: preference/tendency bucket reference, not member identity or plaintext profile.

These fields allow Total Field to answer:

- which compute lane produced the candidate.
- which action path the browser controller proposed.
- whether member tendency influenced only service order/tone.
- whether the candidate must be held for human or staff confirmation.

## Association Use Admission

For association-governed member benefits, the cloud return packet is not sent as raw authority. The local gateway derives a narrower admission packet:

- schema: `schemas/browser/xiaoj_association_usage_admission_packet_v1.schema.json`
- packet type: `ASSOCIATION_USAGE_ADMISSION_PACKET`
- producer: `tools/member_browser/xiaoj_member_browser_gateway.py`

The association-facing packet includes only no-plaintext decision evidence:

- association ref, member ref, and device ref.
- consent scope ref, quota bucket ref, benefit ref, and service scope ref.
- `cloud_compute_ref`, `compute_provider_ref`, and `compute_cost_bucket_ref`.
- `behavior_info_ref`, `action_trace_ref`, and `member_tendency_ref`.
- source packet hash, browser return packet hash, and cloud return packet hash.
- `admission_decision=ALLOW|HOLD|BLOCK`.

It explicitly fixes:

- `execution_allowed=false`
- `candidate_only=true`
- `requires_total_field_verify=true`
- `member_plaintext_transferred=false`
- `secret_transferred=false`
- `raw_browser_page_transferred=false`
- `raw_api_key_transferred=false`
- `oauth_token_transferred=false`

This lets the association approve, hold, block, meter, and audit member AI welfare use without acquiring member plaintext, credentials, raw browser state, or cloud prompt content.

## Forbidden Return Authority

Cloud return packets must not authorize:

- DB write.
- Odoo DB write.
- production DB write.
- POS write.
- payment capture.
- deploy.
- service restart.
- member plaintext read.
- secret read.

## Service Integration

`tools/cloud_proxy/w7tp_openwebui_cloud_proxy.py` now builds a return packet during `process_messages`:

```text
candidate JSON
-> build_cloud_candidate_return_packet()
-> validate_cloud_candidate_return_packet()
-> cloud_candidate_return_packet local ledger row
```

This makes cloud compute packetization part of the service path rather than a manual post-processing step.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
PRODUCTION_DB_WRITE=FALSE
ODOO_DB_WRITE=FALSE
POS_WRITE=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE

Local runtime ledger writes may occur only inside the cloud proxy sandbox path when explicitly running proxy or smoke commands. They are not Odoo, POS, production DB, deployment, payment, or service authority.
