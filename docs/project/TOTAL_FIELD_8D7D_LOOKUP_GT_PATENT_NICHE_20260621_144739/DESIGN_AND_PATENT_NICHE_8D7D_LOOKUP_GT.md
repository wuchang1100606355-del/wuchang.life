# W7TP / XiaoJ 8D/7D Nonlinear Lookup + Generative Transfer
# Design Philosophy and Patent Niche Consolidation

RUN_ID: TOTAL_FIELD_8D7D_LOOKUP_GT_PATENT_NICHE_20260621_144739
CREATED_AT_UTC: 2026-06-21T14:47:39.528057+00:00

## SOURCE_BOUNDARY

SOURCE=USER_INPUT
- User requested convergence of the current conversation into Total Field as design philosophy and patent niche.

SOURCE=USER_OUTPUT
- taiji01 runtime observations: host 8080 is occupied by headscale, taiji_edge_gateway runs on 9002, Ollama runs on 11434, Open WebUI UI path uses 3000 when containerized.
- 9002 exposes OpenAI-compatible API routes but chat path currently fails because legacy gateway hardcodes Windows Ollama routing.
- Open WebUI fallback path can answer through local gemma3:4b, but quality requires Total Field file extraction.
- Direct local Ollama qwen2.5-coder:1.5b returned a collapsed response, showing model availability but weak task compliance.

SOURCE=TOTAL_FIELD_FILE_EXTRACT
- 7D schema anchor: schemas/eamtp_7d_packet.schema.json
- 8D schema anchor: schemas/8d/xiaoj_8d_packet.schema.json
- Redteam anchor: config/redteam_hold_rules.yaml
- Cloud boundary anchors:
  - docs/governance/W7TP_CLOUD_PROVIDER_ADAPTER_CONTRACT.md
  - docs/governance/W7TP_LOCAL_XIAOJ_CLOUD_API_BROKER_DRYRUN.md
  - docs/governance/W7TP_NL_TO_7D_TASK_PACKET_GENERATOR.md

SOURCE=ASSISTANT_INFERENCE
- This document is a design consolidation and patent strategy seed, not a Total Field verdict and not a legal filing.

## SAFETY_FLAGS

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
TOKEN_PRINT=FALSE
DB_WRITE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
GIT_ADD_DOT=FALSE

## 1. Design Philosophy

W7TP / XiaoJ is not an ordinary AI agent, ordinary Line Bot, ordinary Open WebUI model profile, or ordinary Odoo permission table.

Core thesis:

身分封包成場。Odoo records, LINE WORKS, Open WebUI, Google Workspace, Docker, and OS accounts are runtime or business carriers. The governance object is the 8D Identity Packet.

The useful computation model is:

7D task packet → 8D packet envelope → nonlinear lookup → candidate generation → local verification → Sandbox→Validate→Land.

The LLM is not authority. The LLM is a candidate generator. The local verifier is the gate. Human and Total Field authority remain final.

## 2. Extracted 7D Schema Anchor

7D required fields extracted from schemas/eamtp_7d_packet.schema.json:

- eamtp_version
- packet_id
- field
- d1_identity_role
- d2_intent
- d3_context_topology
- d4_privacy_consent
- d5_risk_governance
- d6_resource_cost
- d7_action_state
- ledger

7D meaning in this design:

- D1 identity role: who or what role is requesting
- D2 intent: what is being requested
- D3 context topology: where the request belongs
- D4 privacy consent: whether the request may expose data
- D5 risk governance: risk and governance state
- D6 resource cost: compute, model, time, and budget constraints
- D7 action state: allowed action lifecycle and result capsule
- ledger: hash and evidence anchor

## 3. Extracted 8D Schema Anchor

8D required fields extracted from schemas/8d/xiaoj_8d_packet.schema.json:

- packet_type
- D1_identity
- D2_intent
- D3_state
- D4_topology
- D5_resource
- D6_governance
- D7_verification
- D8_envelope

8D definition properties extracted:

- D1_identity: actor_ref, actor_type, device_ref, role, plaintext_identity_forbidden
- D2_intent: primary_intent, secondary_intent, transaction_intent, risk_level
- D3_state: session_state, task_state, browser_state, order_state, context_mode
- D4_topology: channel, site_ref, device_topology, origin_scope
- D5_resource: key_policy, selected_key_ref, api_refs, model_tier, cache_policy, cost_policy
- D6_governance: allowed_actions, forbidden_actions, no_plaintext_context, human_confirm_required, staff_confirm_required
- D7_verification: redaction_check_required, leak_check_required, action_allowlist_required, response_verify_required, usage_log_required
- D8_envelope: packet_ref, nonce, counter, ttl_seconds, created_at, schema_version, content_hash, hmac_ref, signature_ref, replay_protection

## 4. 7D to 8D Mapping

d1_identity_role → D1_identity
d2_intent → D2_intent
d3_context_topology → D3_state + D4_topology
d4_privacy_consent → D6_governance.no_plaintext_context
d5_risk_governance → D6_governance + D7_verification
d6_resource_cost → D5_resource
d7_action_state → D3_state.task_state + D6_governance.allowed_actions
ledger → D8_envelope.packet_ref + content_hash + evidence chain

## 5. Nonlinear Lookup Definition

Nonlinear lookup does not mean uncontrolled magic. In this architecture it means multi-coordinate table selection over explicit state dimensions.

LOOKUP_INPUT:

- actor_type
- role
- actor_ref
- device_ref
- primary_intent
- risk_level
- session_state
- task_state
- channel
- origin_scope
- privacy consent
- selected_key_ref
- model_tier
- cache_policy
- allowed_actions
- forbidden_actions
- ttl_seconds
- evidence requirement

LOOKUP_OUTPUT:

- allowed_actions
- forbidden_actions
- model_tier
- key_policy
- api_refs
- redaction_check_required
- leak_check_required
- action_allowlist_required
- response_verify_required
- usage_log_required
- hold or fail condition
- packet_ref
- content_hash requirement
- evidence ledger requirement

The lookup table is valuable because it converts vague natural language into governed state coordinates before any cloud or model action.

## 6. Generative Transfer Flow

1. User request or UI action is converted into a redacted 7D task packet.
2. The 7D task packet is mapped into an 8D_GENERATIVE_TRANSFER_REQUEST.
3. D8_envelope creates packet_ref, nonce, counter, ttl_seconds, content_hash, hmac_ref or signature_ref.
4. Cloud or model receives only redacted_packet, task_delta, topology_hint, resource_budget, governance_rule_ref.
5. Cloud or model produces only 8D_CANDIDATE_COMPLETION_PACKET.
6. Local verifier checks D6 governance, D7 verification, D8 envelope, redteam hold rules, evidence logging, hash, replay protection, and human or staff confirmation flags.
7. Only after local verification may the candidate enter Sandbox→Validate→Land.

## 7. Remote Blind Compute Boundary

Core phrase:

主體算力找雲端，8D 解密找我們。

Cloud LLM or cloud worker may do:

- high compute candidate generation
- skeleton completion
- delta completion
- code or document candidate drafting
- redacted task reasoning

Cloud LLM or cloud worker must not do:

- become authority
- receive full governance packet
- receive member plaintext
- receive raw credentials
- print token
- write DB
- trigger deploy
- restart services
- decide Land
- bypass local verifier

Allowed credential references:

- key_ref
- secret_ref
- path_ref
- hash_ref

Forbidden credential material:

- private_key
- client_secret
- refresh_token
- access_token
- application_default_credentials.json plaintext

## 8. Redteam Hold Rules Extracted

Blocked target paths:

- /etc/
- /root/
- .env
- secrets/
- keys/
- odoo.conf
- application_default_credentials.json

Forbidden intents:

- DEPLOY_PROD
- DB_DROP
- MEMBER_PLAINTEXT_DUMP
- FINANCIAL_TRANSFER
- SERVICE_RESTART

Other hard rules:

- evidence logging is required
- max dry-run TTL is 300 seconds

## 9. Land Condition

LAND_CONDITION:

- requested action is included in D6_governance.allowed_actions
- D6_governance.forbidden_actions is not triggered
- D7_verification checks pass
- D8_envelope packet_ref, nonce, counter, ttl_seconds, content_hash, hmac_ref, signature_ref, replay_protection are valid
- evidence ledger exists
- no redteam hold rule is triggered
- human_confirm_required or staff_confirm_required is satisfied when required
- candidate result remains a delta, not an authority claim

## 10. Patent Niche

Potential patent niche:

1. A method for converting natural language, UI action, or business event into a 7D task packet and then into an 8D encrypted governance packet.
2. A system where cloud compute only receives redacted_packet, task_delta, topology_hint, resource_budget, and governance_rule_ref.
3. A local verifier that reconstructs authority from D1 to D8 and decides whether a candidate may enter Sandbox→Validate→Land.
4. A nonlinear lookup table that maps explicit identity, intent, topology, privacy, risk, resource, action, and envelope coordinates into governed candidate-compute permissions.
5. A packet_ref, delta, hash, evidence, and verifier workflow that prevents LLM direct Land.
6. A device cluster model where Odoo, LINE WORKS, Open WebUI, Google, taiji01, POS, and local models are carriers, while 8D Identity Packet is the governance identity.
7. A redteam hold mechanism embedded into generative transmission, blocking secrets, member plaintext, production deploy, service restart, DB destructive actions, and financial transfers.

This differs from ordinary AI agents because the LLM does not own authority, does not receive complete plaintext, and does not directly mutate the business runtime.

This differs from ordinary rule engines because the rule engine is embedded into a packetized 7D/8D generative transfer process with local reconstruction, envelope verification, evidence ledger, and redteam hold.

This differs from ordinary Open WebUI or Odoo integration because Open WebUI and Odoo are only operation surfaces and carriers, not the source of identity, permission, or Land authority.

## 11. Trade Secret Reserve

Candidate trade secret reserve:

- exact lookup table content
- coordinate weighting rules
- codebook construction
- hash-chain evidence linking method
- D8 key rotation policy
- verifier scoring thresholds
- local reconstruction heuristics
- synthetic or no-plaintext context compression rules

Patent disclosure should protect the mechanism while avoiding unnecessary exposure of exact production lookup tables.

## 12. Product Relevance

Coffee shop field:

- AI merchant service staff XiaoJ
- POS and customer interaction can become 8D capability call packets
- commercial personal data governance is tested under no-plaintext boundaries

Association field:

- AI organization secretary XiaoJ
- governance and public service intent scheduling
- synthetic and dry-run first

Committee field:

- AI property management clerk XiaoJ
- local legal and administrative workflow governance
- virtual field and process field first

## 13. Current Runtime Note

The current conversation confirmed a useful operational distinction:

- host 8080 belongs to headscale and should not be used for Open WebUI
- Open WebUI UI should use host 3000 mapped to container 8080 when containerized
- taiji_edge_gateway currently listens on 9002
- Ollama listens on 11434
- 9002 chat route requires repair because it hardcodes Windows Ollama routing
- Open WebUI fallback can answer locally but should be grounded by Total Field file extraction

## 14. Next Engineering Use

This document may be used as:

- Total Field design note
- patent counsel briefing seed
- verifier design seed
- prompt boundary for cloud candidate compute
- redteam policy explanation
- Open WebUI model profile grounding note

## LIMITATION

This document is not a legal opinion, not a final patent claim set, and not a formal Total Field verdict. It is a sourced design consolidation from USER_OUTPUT, TOTAL_FIELD_FILE_EXTRACT, and ASSISTANT_INFERENCE.

