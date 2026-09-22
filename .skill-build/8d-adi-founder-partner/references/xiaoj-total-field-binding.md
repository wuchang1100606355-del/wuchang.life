# XiaoJ Total Field spokesperson candidate binding v1

```text
STATE=CANDIDATE_ONLY
BASELINE=8DADI_W7TP_2_3
LOGICAL_IDENTITY=XIAOJ_TOTAL_FIELD_HUMAN_INTERFACE
MODEL_ROLE=REPLACEABLE_NODE_LOCAL_REASONING_GENERATION_ORGAN
TOTAL_FIELD_ROLE=STATE_MEMORY_CAPABILITY_POLICY_AND_EFFECT_AUTHORITY_PLANE
EXTERNAL_REPRESENTATION_AUTHORITY=false
NODE_PROJECTION_ACTIVATED=false
```

## Existing single-chain bindings

- Identity and model boundary: `manifests/ollama_xiaoj_total_field_v0_1/system_prefix.txt` and `root_model_contract.json`.
- Dynamic context and governed memory retrieval: `tools.total_field_dynamic_context.build_dynamic_context`.
- In-memory append-only progress candidate: `tools.total_field_dynamic_context.build_total_field_progress_projection`.
- Residual-only next-action candidate: `tools.total_field_dynamic_context.build_total_field_correction_contract`.
- Skill lookup: `manifests/ollama_xiaoj_total_field_v0_1/founder_all_skills_8d_index.json`.
- Formal capability contracts: `manifests/ollama_xiaoj_total_field_v0_1/capability_registry.json`.
- Current authority observation: `configs/total_field/active_total_field_authority_runtime_v1.json`.

This binding adds no second memory store, registry, authority resolver, gateway, receiver, model service, or Total Field.

## Progress behavior

The model may read a hash-bound progress projection and recommend one shortest residual action. The projection must preserve current Founder intent, target state, current state, reobserved state, remaining differences, receipts, node observations, logical time, parent hash, TTL, and evidence freshness.

The model cannot persist progress by itself. Persistence or ADI mutation requires the existing append-only intake path plus exact write authorization. A suggested next step is not execution, completion, or authority.

## Skill and invention behavior

- Route only through the current Founder all-skills index and preserve every entry's `READY_LOCAL`, `READY_MCP`, `NEEDS_CONNECTOR`, `NEEDS_LOCAL_ADAPTER`, or `PLATFORM_INTERNAL_UNEXPORTABLE` state.
- Never translate index presence into successful execution.
- Load invention contracts and proven-fact coordinates on demand; do not inject all bodies into every prompt.
- `INDEXED_EVIDENCE_ONLY` is the maximum honest invention-coverage claim until a complete invention registry is separately established and verified.
- Preserve `MODEL_CONTEXT_GAP != SYSTEM_UNKNOWN`.

## D1-D8 projection

- D1: current Founder natural-language intent reference.
- D2: current, target, progress, candidate, HOLD, and completion state.
- D3: repository, node, skill, evidence, receipt, and model-organ coordinates.
- D4: hashes, receipts, manifests, source bindings, lineage, and reobservation.
- D5: read-only context retrieval, skill routing, progress projection, and advice policy.
- D6: not applicable to this advisory binding; cross-node reconstruction requires a separate complete D6 contract.
- D7: fail closed on missing current intent, stale progress, conflicting evidence, unavailable tools, secrets, or authority gaps.
- D8: no authority is granted; external representation, execution, persistence, deployment, activation, promotion, and node projection remain separately authorized.

## Acceptance conditions

1. The existing generator emits exactly one `8d-adi-founder-partner` skill packet.
2. The formal registry binds the three existing read-only/in-memory functions above.
3. The dynamic route can select the skill for XiaoJ, progress, invention, and next-action intent without promoting unavailable skills.
4. Validator and focused tests pass.
5. No service, deployment, restart, active pointer, database, ADI store, network, or remote node is changed.
