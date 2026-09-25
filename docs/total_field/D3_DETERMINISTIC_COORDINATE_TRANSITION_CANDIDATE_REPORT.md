# D3 Deterministic Coordinate Transition Candidate Report

STATE=CANDIDATE_ONLY_NOT_CANONICAL
RUN_ID=D3_COORDINATE_TRANSITION_V0_3_CANDIDATE

## Scope

This candidate adds a deterministic D3 coordinate proposal and commit record. It does not modify Active Canonical, Pointer files, the existing packet schema, or the public API of `tools/w7tp_packet_inference_runtime.py`.

## Compatibility finding

The Active Canonical defines D3 as Coordinate Field, D6 as Sovereign Privacy Field, D7 as Generative Transmission & Resource Routing Field, and D8 as Red-Team Detour Alert & Quarantine Field. The existing packet runtime instead uses the legacy keys `D3_coordinate`, `D6_gt`, `D7_risk`, and `D8_envelope`; its envelope also owns packet identity, wall-clock time, nonce, packet hash, and seal.

The narrow adapter maps only legacy `D3_coordinate` into the candidate D3 state. Safe reference keys from legacy `D6_gt` may be copied to candidate `context.d7_reference`. Legacy `D7_risk` and `D8_envelope` are not remapped because their meanings differ from Active Canonical D7 and D8. The existing runtime remains unchanged.

## Candidate behavior

- Inputs are deep-copied and JSON-valid before calculation.
- Proposed coordinates use recursive dict merge; lists and non-dict values are replaced.
- D6 is a local candidate privacy gate and exposes no raw sensitive values.
- D7 is limited to `rule_ref`, `table_ref`, `template_ref`, `routing_ref`, and `reconstruction_condition` references.
- D8 returns `ALLOW`, `HOLD`, `BLOCK`, or `QUARANTINE` with a stable reason code.
- Only `ALLOW` commits `proposed`; all other decisions preserve `previous`.
- SHA-256 uses fixed canonical JSON serialization, binds the required inputs plus commit/decision outputs, and uses no clock, UUID, random value, or external runtime state.

## Known limitations

The rule registry and both gates remain candidate-only. The D6 stub detects explicitly sensitive key names but is not a production data-classification service. D8 policy is an interface with a conservative D6 enforcement path, not a promoted Total Field authority. No Luoshu, nine-palace, flying-star, geographic, Cartesian, or graph coordinate model is introduced.
