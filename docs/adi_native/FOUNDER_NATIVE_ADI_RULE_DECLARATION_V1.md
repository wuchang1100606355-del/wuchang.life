# Founder Native ADI Rule Declaration V1

STATUS=`CURRENT_FOUNDER_CANONICAL`  
HISTORICAL_SOURCE=`NO`  
IMPLEMENTATION_SOURCE=`YES`  
FOUNDER_AUTHORITY=`CHIANG_CHENG_LUNG`  
EXTERNAL_SUBSTITUTION=`FORBIDDEN`

This declaration records the current Founder canonical supplied for
`W7TP_NATIVE_ADI_P1_20260722T171323Z`. It does not claim to be an early
historical source.

## Direct storage projection

`tau_F(t) = floor(((t - T_min) / (T_max - T_min)) * N)`.

`DIRECT_SLOT_F(P_t) = SLOT_LOOKUP_F(namespace, state_profile, tau_F(t),
native_state_ref, canonical_version, rule_version)` and returns a non-negative
integer. It is an O(1) storage projection, not complete `PHI_F` and not an
authoritative state.

## 8D state, polarity, metric and cross-section

`P_t=<D1_t,...,D8_t>` and `X_F(P_t)=<x_1,...,x_8>`, where each `x_i` is an
integer selected by the Founder canonical rule table. No floating confidence,
similarity or model scoring is permitted.

`B_F_plus` requires intent satisfied, evidence valid, life safe and other-rights
safe. `B_F_minus` is reached by intent violation, causal-order violation, life
harm, other-rights harm or hard risk. Life or other-rights harm is
`BLOCK_ABSOLUTE_REDLINE`.

For each dimension, `boundary_state_F` is `+1` for the positive predicate,
`-1` for the negative predicate, and `0` when unresolved. Negative takes
precedence when predicates conflict.

`METRIC_SIGNATURE_F(P_t)=<logical_time,topology_coordinate_ref,
previous_state_root,evidence_root,event_hash_ref,canonical_version,
rule_version>`.

`SIGMA_F(P_t)=<tau_F(t),DIRECT_SLOT_F(P_t),X_F(P_t),boundary_state_F(P_t),
METRIC_SIGNATURE_F(P_t)>`.

## Founder transitions, direction and absolute distance

Every transition rule contains `transition_rule_id`, `from_state_code`,
`to_state_code`, `preconditions`, `required_evidence_refs`, `polarity`,
`direction_code`, positive `step_cost_uint`, and `rule_version`.

Missing valid rule/path is `HOLD_TRANSITION_RULE_MISSING`. Multiple valid paths
that canonical rules cannot eliminate are `HOLD_CANONICAL_PATH_DIVERGENCE`.

`THETA_F(P_a,P_b)=direction_code(selected_transition_rule_id)` and
`THETA_PATH_F=<direction_code_1,...,direction_code_m>`.

For the unique Founder-canonical path `GAMMA_F=<e_1,...,e_m>`,
`delta_F(P_a,P_b)=sum(step_cost_uint(e_k))`. Therefore `delta_F(P,P)=0`.
Distance is not a direct-slot difference or a geometric/similarity proxy.

## Complete native ADI

`PHI_F(P_o,P_t)` is the ordered structure:

`<namespace,origin_state_root,DIRECT_SLOT_F(P_t),tau_F(t),X_F(P_t),
boundary_state_F(P_t),METRIC_SIGNATURE_F(P_t),delta_F(P_o,P_t),
THETA_PATH_F(P_o,P_t),parent_state_root,evidence_root,canonical_version,
rule_version,logical_time>`.

Canonical serialization may be hashed as `adi_ref`; the hash is only an
identifier and not the ADI mathematical object.

## Shells and native spiral

`S_r^F(P_o)={P_j | delta_F(P_o,P_j)=r}`. `S_0` is the exact authoritative
shell; `r>0` is reconstruction-only.

For a candidate `P_j`, `ORDER_KEY_F=<PATH_F(P_o,P_j),THETA_PATH_F(P_o,P_j),
logical_time(P_j),state_root(P_j)>`. Ordering is, in sequence:

1. transition-rule-id path in canonical UTF-8 byte order;
2. direction-code path in canonical UTF-8 byte order;
3. ascending logical time;
4. lowercase hexadecimal state-root byte order.

`OMEGA_F(S_r)` sorts one shell by that key. `SPIRAL_F` concatenates complete
shells from radius zero outward.

## Evidence closure, unique fixed point and stop

`EVIDENCE_CLOSED_F(P)=1` only when all required evidence references resolve and
their digests match, the metric signature reproduces, logical time and topology
are causally consistent, the parent root is current-authoritative, the candidate
root reproduces, all eight dimensions are cross-field consistent, the packet is
not negative, every positive condition holds, every required transition is
present and unique, and D7 has no hard risk.

`T_F(P)=TOTAL_FIELD_VALIDATE_F(P)`. A fixed point satisfies `T_F(P_star)=P_star`.
The first acceptable shell is the smallest completely checked shell containing
exactly one evidence-closed fixed point, with no fixed point in smaller shells
and no unresolved mutually exclusive candidate in the same shell. Multiple
fixed points are `HOLD_CONSENSUS_DIVERGENCE`.

`STOP_F(r)=1` only after shells zero through `r` are fully checked in native
spiral order, the above unique fixed point exists, smaller shells contain none,
same-shell conflicts are resolved, and the query budget is not exceeded. Stop
immediately at the first such shell. Budget exhaustion is
`HOLD_QUERY_BUDGET_EXCEEDED` and never a partial pass.

## Dependency and drift boundary

The native calculation path is standard-library-only and must not depend on
space-filling curves, geometric proxy distances, similarity/nearest-neighbor
search, model voting, model averaging, decoding optimizers, inference caches, or
external research/runtime frameworks. Historical V2.2 compatibility evidence
must never be imported into the native runtime.
