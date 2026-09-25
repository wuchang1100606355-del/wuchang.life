# Native ADI Source—Rule Matrix

STATE=`PASS_NATIVE_ADI_SOURCE_COMPLETE`  
BASE_RUN_ID=`W7TP_NATIVE_ADI_P1_20260722T171323Z`  
HISTORICAL_SOURCE_ROOT=`/mnt/d/時空/專利`  
CURRENT_IMPLEMENTATION_SOURCE=`docs/adi_native/FOUNDER_NATIVE_ADI_RULE_DECLARATION_V1.md`  
CURRENT_IMPLEMENTATION_SOURCE_SHA256=`c7328422b90411fa0aa61652c36efab11741515de2509d2a5265a9b100bbf8b1`

Historical evidence and the current Founder canonical are deliberately separate.
Current canonical rows are implementation authority but are not relabeled as
historical evidence.

| RULE_ID | STATUS | SOURCE_FILE | SOURCE_SHA256 | SOURCE_LINE_OR_SYMBOL | ORIGINAL_TEXT_OR_CODE | NORMALIZED_NATIVE_RULE | INPUTS | DETERMINISTIC_STEPS | OUTPUT | IMPLEMENTATION_TARGET | UNRESOLVED |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `TAU_F` | `CONFIRMED_HISTORICAL_TEXT` | `SPACETIME_PATENT_DRAFT.md`; `benchmark_spacetime.py` | `fd9b7c9b1f0267fbf927c9c17909f992dafdc3bedea921cf6bc417591d87b038`; `f9ca802ec5f8929a9e9024e2e8c88c39b9b5f34e4c6c47fa24feb164baddec6b` | MD L38-L45,L65-L70; Python `SpaceTimeSystem.__init__/insert` | `I=floor(((t-T_min)/(T_max-T_min))*N)` | Integer absolute-time slot projection | `t,T_min,T_max,N` | subtract, scale, divide, floor | non-negative time-slot integer | `index.py:tau_f` | None for scalar projection |
| `DIRECT_SLOT_F` | `CONFIRMED_HISTORICAL_TEXT` | Historical sources above; current declaration L13-L20 supplies present lookup signature | Historical hashes above; declaration `c7328422b90411fa0aa61652c36efab11741515de2509d2a5265a9b100bbf8b1` | declaration L15-L20 | Direct integer addressing is the storage projection, not complete ADI | Exact lookup by namespace/profile/time-slot/state-ref/versions | packet plus canonical lookup table | form bounded lookup key; require table hit; require UINT/BIGINT | non-negative storage address | `index.py:direct_slot_f` | None |
| `METRIC_SIGNATURE_F` | `PARTIALLY_DERIVED_HISTORICAL` | `SPACETIME_PATENT_DRAFT.md`; current declaration L37-L42 | `fd9b7c9b1f0267fbf927c9c17909f992dafdc3bedea921cf6bc417591d87b038`; declaration hash above | historical L25-L28,L58-L61; declaration L37-L42 | Historical adjacent time/hash metric; current ordered causal signature | Bind logical time, topology, parent root, evidence root, event hash and versions | packet causal fields | preserve declared order | reproducible metric signature | `projection.py:metric_signature_f` | Historical material alone was partial; current canonical completes interface |
| `X_F` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L22-L26 | `X_F(P_t)=<x_1,...,x_8>` exact integer rule-table codes | Eight exact integer dimension codes | D1-D8 lookup results | validate count and integer type | integer 8D tuple | `projection.py:project_8d_state` | None |
| `B_PLUS` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L28-L35 | intent/evidence/life/rights predicates; `+1/-1/0` polarity | All positive predicates yield +1; any negative predicate yields -1; unresolved yields 0 | exact predicate results per dimension | evaluate negative first, then all-positive | 8-value polarity tuple | `projection.py:positive_negative_boundaries` | None |
| `B_MINUS` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L28-L35 | life/rights harm or causal/hard-risk violation | Negative predicate wins; life/rights harm is absolute redline | exact predicate results | OR negative predicates | negative boundary and possible BLOCK | `projection.py`; `verifier.py` | None |
| `SIGMA_F` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L37-L42 | cross-section binds time slot, direct slot, X_F, polarity and metric | Declared ordered cross-section | packet and slot table | evaluate five ordered components | `StateCrossSection` | `projection.py:state_cross_section` | None |
| `TRANSITION_STEP_COST` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L44-L51 | transition rule has positive `step_cost_uint` and exact validity fields | Validate positive integer cost and exact rule/version/evidence/preconditions | transition rule table and packet context | filter exact valid rules | valid causal edges | `models.py`; `distance.py` | None |
| `THETA_F` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L53-L54 | direction is selected Founder rule code | Return rule direction code/path, never float angle | unique path | read direction codes in path order | direction-code tuple | `projection.py:direction_state/direction_path` | None |
| `DELTA_F` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L50-L58 | `delta_F=sum(step_cost_uint(e_k))`; identity is zero | Cost of the only valid simple canonical path | state pair, exact transition table | resolve all valid paths; HOLD on zero/multiple; sum costs | non-negative integer distance | `distance.py:resolve_canonical_path/delta_f` | None |
| `PHI_F` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L60-L70 | Complete ordered native ADI structure; hash is identifier only | Bind storage, 8D, polarity, metric, distance, direction and causal roots/versions/time | origin, target, transitions, slot table | evaluate declared components in order; canonical serialize; hash identifier | `NativeAdiIndex` | `index.py:phi_f` | None |
| `SPIRAL_SHELL_FORMATION` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L72-L75 | `S_r={P_j|delta_F(P_o,P_j)=r}` | Group candidates by integer canonical distance | origin, candidates, transitions | compute delta, group by exact radius | ordered shell set | `spiral.py:enumerate_shells` | None |
| `OMEGA_F` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L77-L86 | order by rule path bytes, direction bytes, logical time, lowercase hex root | Deterministic shell-local causal order | one shell and unique paths | form four-part key and sort | reproducible candidate tuple | `spiral.py:omega_f` | None |
| `SPIRAL_STOP_CONDITION` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L97-L107 | first fully checked shell with exactly one closed fixed point stops immediately | Process complete shells outward; no partial PASS | ordered shells, closure, validator, budget | fully inspect shell; count fixed points; HOLD divergence/budget | stop receipt | `spiral.py:evidence_closure_stop` | None |
| `EVIDENCE_CLOSURE` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L88-L95 | all evidence, metric, causal, root, 8D, polarity and rule conditions must hold | Fail-closed conjunction of declared evidence predicates | origin, candidate, transitions, authoritative parent | validate each declared condition | `EVIDENCE_CLOSED` or exact HOLD/BLOCK | `verifier.py:evidence_closed_f` | None |
| `UNIQUE_FIXED_POINT` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L97-L107 | `T_F(P*)=P*`; exactly one in first qualifying shell | Compare validated root to candidate root after closure | closed candidates and Total Field validator | count per complete shell; stop at first count=1 | unique fixed-point receipt | `spiral.py:evidence_closure_stop` | None |
| `STATE8D_ADI_IO` | `CURRENT_FOUNDER_CANONICAL` | Founder declaration | declaration hash above | L22-L42,L60-L70 | 8D state feeds complete ordered Φ_F and cross-section | Exact integer 8D input with causal/evidence bindings to ADI output | full packet and canonical tables | project, bind, resolve distance/direction, serialize | complete candidate index | `models.py`; `projection.py`; `index.py` | None |

## Historical classification retained

- `LEGACY_HASH_V1=CONFIRMED_HISTORICAL_CODE`
- `W7TP_EVIDENCE_HASH_V2=CONFIRMED_EXISTING_CANDIDATE`
- Historical positive/negative warp, digital spacetime interval and causal
  closure wording remains `CONCEPT_ONLY_HISTORICAL`; it is not used to invent
  the current rule.
- V2.2 remains non-runtime compatibility evidence and is not imported.

## Land gate

- `PHI_F=CURRENT_FOUNDER_CANONICAL`
- `DELTA_F=CURRENT_FOUNDER_CANONICAL`
- `OMEGA_F=CURRENT_FOUNDER_CANONICAL`
- `SOURCE_TRACEABILITY=PASS`
- `NATIVE_RUNTIME_DEPENDENCY=PYTHON_STANDARD_LIBRARY_ONLY`
