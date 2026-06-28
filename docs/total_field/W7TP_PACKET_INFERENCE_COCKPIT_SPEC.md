# W7TP Packet Inference Cockpit Spec

## Product Goal

The W7TP Total Field AI Cockpit is a local web interface for talking to Total Field in natural language and seeing the packet-by-packet inference process behind the answer.

It is not a generic chat page. It is a product cockpit for:

```text
natural language
-> 8D input packet
-> packet-by-packet inference
-> verifier ALLOW/HOLD/BLOCK
-> semantic_ir
-> deterministic natural language reconstruction
-> visual packet chain
```

## Natural Language Conversation

The operator types one sentence in the cockpit. The local server sends it to the existing runtime through `POST /api/chat`, using branch, actor role, and channel metadata. The response returns the reconstructed Traditional Chinese answer plus the verifier decision and packet chain.

The input text may be visible in the UI for the current operator interaction. Local audit files store only hashes and redacted markers for the original text.

## Packet-as-Inference Visualization

The cockpit displays the chain:

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

Each timeline item shows the step, packet type, packet hash, parent packet hash, risk code, verifier decision, table ref, and template ref. Selecting a packet opens the 8D inspector for D1 intent, D2 state, D3 coordinate, D4 evidence, D5 execution, D6 generative transmission, D7 risk, and D8 envelope.

## Dual Lane

The current lane configuration is:

```text
Model Lane: OFF
Future mode: CANDIDATE_ONLY
Lookup Lane: ACTIVE
Verifier Authority: TOTAL_FIELD
External API: FALSE
```

A future API model lane may suggest candidate packets, but it cannot decide `ALLOW`, `HOLD`, or `BLOCK`. The lookup packet lane remains complete without model access.

## Verifier Authority

The verifier is the authority. Payment requests are held, member plaintext requests are blocked or held without permission, allergy or intolerance signals require review, unknown input is held, and normal recommendation can continue to an allowed output.

The UI exposes:

```text
decision
reasons
forbidden_actions
requires_human_review
```

## Safety Guarantees

The cockpit preserves:

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
MODEL_DOWNLOAD=FALSE
MODEL_REQUIRED=FALSE
LLM_AUTHORITY=FALSE
```

It does not read environment files, credentials, rclone config, OAuth material, API credentials, member plaintext stores, Odoo production data, or payment data. It does not write a database, restart services, deploy, or call external APIs.

## Demo Cases

The UI includes five demo buttons:

```text
飲品推薦: 我今天有點累，想喝不太苦的，幫我推薦
付款請求: 幫我直接結帳付款
會員明文: 我要查會員完整電話和地址
過敏風險: 我對牛奶有點敏感，想喝順口的
未知輸入: qqq xyz 未知請求
```

## Local Start Command

```bash
python3 tools/w7tp_packet_inference_cockpit_server.py --host 127.0.0.1 --port 8765
```

Open:

```text
http://127.0.0.1:8765/
```

## Verify Command

```bash
python3 scripts/verify/verify_w7tp_packet_inference_cockpit.py
```

The verifier starts the local server, checks `/api/health`, runs the five demo cases through `/api/chat`, writes a report under `runtime/total_field/packet_inference_cockpit/`, and stops the server.

## Deployment Boundary

This task creates a local development cockpit only. There is no deployment, no DB write, no external API, no model download, no service restart, and no production release.
