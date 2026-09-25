---
name: w7tp-external-capability-gateway
description: Normalize an external tool, API, agent, protocol, or open-source capability into a W7TP-native capability gateway contract without copying its implementation or inheriting its runtime authority. Use when exposing, routing, registering, adapting, or reconstructing external capabilities for W7TP, MCP, A2A, REST, gRPC, local tools, cloud tools, or model receivers, especially when the user wants target-native capability reconstruction or FAST_LAND deployment without installing the source project.
---

# W7TP External Capability Gateway

Treat the external system as a capability source, never as the target runtime by default.

## Hard anchors

Keep these invariants:

- `SOURCE != TARGET`
- `CAPABILITY != IMPLEMENTATION`
- `REFERENCE != DEPENDENCY`
- `EXTERNAL_RUNTIME != W7TP_NATIVE_RUNTIME`
- `EXTERNAL_ADMIN != FOUNDER`
- `EXTERNAL_POLICY != W7TP_D8`
- `POLICY_ALLOW != EFFECT_AUTHORIZATION`

Do not install or run the source project unless the user explicitly asks to use that source runtime.

## Workflow

1. Reuse supplied source coordinates, hashes, capability evidence, and target state. Do not rescan when they already prove the needed input.
2. Extract only the neutral effect contract: inputs, outputs, state transition, side effects, failure behavior, evidence, dependencies, and protocol surface.
3. Bind the target coordinate and choose a target-native adapter or implementation shape.
4. Preserve W7TP D1-D8 semantics. Treat external identity, policy, approval, CI, and admin state as evidence only.
5. Build the smallest gateway contract needed for the target. Use `scripts/build_gateway_contract.py` for deterministic JSON construction.
6. In `FAST_LAND`, create the target-native candidate immediately after the minimum inputs are present. Do not create extra review stages. Stop only for a true hard risk or missing effect authority required by the requested write.

Read `references/gateway-contract.md` when defining a gateway contract.

## Output

Return a compact result containing:

- source capability reference;
- W7TP-native capability ID;
- accepted protocol surfaces;
- target adapter/receiver coordinate;
- input/output/state/effect contract;
- evidence requirements;
- source runtime dependency (`false` by default);
- authority inheritance (`none`);
- next executable target-native action.

Never claim semantic equivalence solely from matching names or protocols.
