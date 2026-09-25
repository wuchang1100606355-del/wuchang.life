# TFCT / TRUE8D Engineering Candidate

Status: `CANDIDATE`

Run ID: `TFCT_TRUE8D_W7TP_8DGTE_SYSTEM_CONSOLIDATION_CANDIDATE_V0_1`

This document is an engineering mapping candidate. It does not promote, replace,
or amend any active definition, pointer, packet runtime, or D3 transition engine.

## 1. Normative candidate inputs

This mapping depends on, and does not restate, the two preceding layers:

- Theory: [`TFCT_THEORY_CANDIDATE.md`](TFCT_THEORY_CANDIDATE.md)
- Mathematics: [`TFCT_MATHEMATICS_CANDIDATE.md`](TFCT_MATHEMATICS_CANDIDATE.md)

The theory document supplies the meanings of Event, Observation, Projection,
Field, and TFS. The mathematics document supplies the formal candidates for the
projection function, Observation Domain, Constraint Hypergraph, Priority Policy,
fixed-point condition, and cross-node equivalence condition. An engineering
artifact MUST NOT be treated as evidence that an unproved mathematical claim is
true.

## 2. Status vocabulary

Every mapping in this document uses exactly one of these status values:

| Status | Meaning in this document |
|---|---|
| `Implemented` | There is accepted repository evidence for the stated engineering behavior. |
| `Candidate` | The interface or mapping is proposed here and has not been promoted. |
| `Legacy` | The item is retained only to describe an existing compatibility surface. |
| `Conflict` | Direct reuse would change the adopted TRUE8D semantics. |
| `Open Problem` | A required definition, proof, algorithm, or protocol is not yet settled. |

## 3. Theory to mathematics to engineering mapping

| Theory concept | Mathematical expression | Engineering expression | Status | Boundary |
|---|---|---|---|---|
| Event | Event identifier in the projection input | `event_ref` in an 8D-GTE candidate | `Candidate` | A reference is not an event implementation. |
| Observation | Member of an Observation Domain | `observation_domain_ref` plus locally resolved observations | `Candidate` | The domain is referenced opaquely until its full set is defined. |
| Projection | Projection function from prior field and observations to a proposal | Existing D3 coordinate transition proposal | `Implemented` | D3 proposes coordinates; it does not adjudicate its own proposal. |
| Field | Constraint-bearing state over the eight dimensions | D1-D8 reference set plus Constraint Hypergraph reference | `Candidate` | References do not assert that every constraint is implemented. |
| Priority | Priority Policy over competing constraints | `priority_policy_ref` consumed by a future validator/gateway | `Candidate` | No priority algorithm is introduced by this document. |
| Convergence | Finite-step fixed-point condition | `convergence_operator_ref` and `fixed_point_status` | `Candidate` | A reported status is not a proof of convergence. |
| TFS | Result admitted after valid convergence and governance | `tfs_result` admitted only for a committed `ALLOW` expression | `Candidate` | A candidate expression cannot create a new TFS result. |
| Cross-node equivalence | Equivalence relation over independently reconstructed results | Verification evidence referenced by the receiving contract | `Open Problem` | Consensus protocol and equivalence proof remain unspecified. |

## 4. Adopted TRUE8D dimension boundary

The active meanings below are preserved exactly at the engineering boundary:

| Dimension | Adopted meaning | Status | Engineering constraint |
|---|---|---|---|
| D6 | Privacy | `Implemented` | D6 is the sovereign-privacy gate interface. It does not perform routing or final adjudication. |
| D7 | Generative Transmission & Resource Routing | `Implemented` | D7 stores generative-transmission or routing references only. |
| D8 | Red-Team Detour Alert & Quarantine | `Implemented` | D8 is the final governance gate and yields `ALLOW`, `HOLD`, `BLOCK`, or `QUARANTINE`. |

Only `ALLOW` may commit a proposed state. `HOLD`, `BLOCK`, and `QUARANTINE`
preserve the prior committed state. D8 decision state MUST remain outside the D3
coordinate body.

Generative transmission means a protocol-native 8D intent-field packet whose
required result is reconstructed locally at the verification level required by
that packet. It is not file moving, cloud synchronization, backup, download, or
decryption. It does not imply that an arbitrary existing file can be obtained by
a small packet.

## 5. D3 implementation evidence and boundary

| Engineering item | Status | Candidate interpretation |
|---|---|---|
| Deterministic D3 coordinate transition engine | `Implemented` | Accepted focused tests establish deterministic transition behavior. |
| Packet-runtime D3 integration | `Implemented` | The existing runtime preserves the established `D3_coordinate` shape and exposes transition metadata separately. |
| Runtime deterministic replay | `Implemented` | Accepted replay evidence establishes matching coordinate, committed state, decision, and transition hash for fixed inputs. |
| D3 as D8 decision storage | `Conflict` | D8 decision data must not be written into `D3_coordinate`. |
| D3 as ADI | `Conflict` | A coordinate proposal and an index strategy are different responsibilities. |

These entries record previously accepted evidence only. This candidate creates no
new runtime behavior and does not rerun or alter the D3 implementation.

## 6. Legacy compatibility map

Legacy names are compatibility inputs, not aliases for adopted dimensions.

| Legacy surface | Status | Compatibility rule |
|---|---|---|
| `D6_gt` | `Legacy` | A narrow adapter may interpret its generative-transmission references for the adopted D7 interface. It MUST NOT rename or redefine adopted D6 Privacy. |
| `D7_risk` | `Legacy` | A narrow adapter may present risk evidence to D8 adjudication. It MUST NOT be treated as adopted D7. |
| `D8_envelope` | `Legacy` | A narrow adapter may preserve envelope metadata outside adopted dimension bodies. It MUST NOT be treated as adopted D8 adjudication state. |
| Direct `D6_gt` = D6 mapping | `Conflict` | It would replace Privacy with a different semantic. |
| Direct `D7_risk` = D7 mapping | `Conflict` | It would replace Generative Transmission & Resource Routing with risk state. |
| Direct `D8_envelope` = D8 mapping | `Conflict` | It would replace Red-Team Detour Alert & Quarantine with an envelope. |

The compatibility adapter, if separately authorized, must be one-way at the
boundary: read the legacy shape, emit explicit adopted references or evidence,
and retain provenance. It must not rewrite active definitions or mutate the
legacy source object.

## 7. `tensor_8d` legacy conflict record

| Observed legacy characteristic | Status | Decision |
|---|---|---|
| Dimension family `D1_identity` through `D8_commit` | `Legacy` | Preserve only as a documented legacy representation. |
| Treating that dimension family as adopted TRUE8D | `Conflict` | Names and meanings do not establish the adopted D6/D7/D8 boundary. |
| System time inside expression construction | `Conflict` | It cannot be an input to a deterministic core unless supplied as explicit, validated logical data. |
| LLM JSON extraction as structural authority | `Conflict` | Model output cannot replace a deterministic parser, schema validation, or governance decision. |
| Reusing `tensor_8d` as the 8D-GTE parser | `Conflict` | No parser basis is adopted from the legacy implementation. |

No migration, parser reuse, compatibility code, or legacy rewrite is performed
by this candidate.

## 8. Engineering contracts

| Contract | Status | Required behavior |
|---|---|---|
| 8D-GTE representation | `Candidate` | Carries versioned references, lifecycle, convergence status, verification, and TFS result under a closed schema. |
| Schema validation | `Candidate` | Rejects missing, unknown, or lifecycle-inconsistent data before reference resolution. |
| Reference resolution | `Open Problem` | Requires an authorized resolver, provenance rules, and failure semantics. |
| Constraint evaluation | `Open Problem` | Requires a defined Constraint Hypergraph and Priority Policy. |
| Submit Gateway | `Open Problem` | Requires an independently authorized implementation and trust boundary. |
| Consensus and TFID generation | `Open Problem` | Requires a protocol and a stable identity/hash contract. |

## 9. Promotion boundary

This document remains non-canonical. Promotion requires, in a separate and
explicitly authorized process, human review, a decision on the legacy adapter,
proof-status review, parser and gateway implementation evidence, complete
verification, and explicit permission to modify protected active material.

`CANONICAL_WRITE=NO`
