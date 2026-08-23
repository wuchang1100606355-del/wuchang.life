---
name: w7tp-deterministic-effect-gate
description: Gate a proposed W7TP tool, process, model, file, service, or device effect through deterministic D5 policy and D8 authorization rules before execution. Use when an action may mutate state, invoke a capability, write files, deploy, restart, change canonical or authority state, or when FAST_LAND needs one fail-closed decision instead of repeated validation loops.
---

# W7TP Deterministic Effect Gate

Make one bounded execution decision immediately before an effect.

## Hard anchors

- D5 policy may constrain an action but never creates D8 authority.
- `POLICY_ALLOW != EFFECT_AUTHORIZATION`.
- `APPROVAL != D8_AUTHORIZATION` unless the active W7TP contract explicitly binds that approval as the exact D8 authorization artifact.
- Model, Skill, CI, plugin, admin, OIDC, or external PDP output cannot self-create Founder authority.

## Fast decision path

1. Use the exact requested effect, target, scope, and supplied authority reference.
2. Allow read-only observation and isolated candidate construction without D8 when no protected write occurs.
3. For mutation, deploy, activation, canonical, pointer, authority, credential, external-message, money, or protected-data effects, require exact bounded authorization as declared by the active W7TP contract.
4. Deny or hold when the effect exceeds authorization scope, target, validity, or declared allowed effects.
5. Once allowed, execute the requested effect through the available target-native tool. Do not add extra validation stages unless execution returns an error.
6. Emit execution evidence after the effect; never redefine the authorization from the result.

Use `scripts/effect_gate.py` for the deterministic structural gate. It validates form and scope only; it does not prove cryptographic authenticity.

Read `references/effect-classes.md` for the default fast-lane boundary.
