# TFCT Mathematics Candidate

Status: `CANDIDATE`

## 1. Purpose and proof boundary

This document gives a candidate mathematical language for TFCT. It separates definitions, assumptions, required theorems, and open problems. Definitions establish notation only; assumptions are declared premises; required theorems are proof obligations; open problems remain unresolved.

This document does **not** claim that the following four propositions have been proved:

1. existence of a fixed point;
2. uniqueness of a fixed point;
3. global finite-step convergence;
4. cross-node equivalence.

Each is marked `Required Theorem / UNPROVEN` below.

## 2. Primitive sets and objects

Let:

- \(\mathcal{E}\) be the set of events;
- \(\mathcal{S}\) be the set of admissible field states;
- \(\mathcal{O}\) be an Observation Domain index set;
- \(\mathcal{V}_i\) be the observation value space for domain \(i\in\mathcal{O}\);
- \(\mathcal{D}_k\) be the value space of field \(D_k\), for \(k\in\{1,\ldots,8\}\);
- \(\mathcal{C}\) be the set of constraints;
- \(\mathcal{P}\) be the set of priority policies;
- \(\mathcal{J}=\{\mathrm{ALLOW},\mathrm{HOLD},\mathrm{BLOCK},\mathrm{QUARANTINE}\}\) be the judgment set.

For an event \(e\in\mathcal{E}\), a domain \(i\in\mathcal{O}\) supplies a partial observation

\[
o_i(e)\in \mathcal{V}_i\cup\{\bot\},
\]

where \(\bot\) means unavailable or unresolved. It does not mean false, zero, or empty.

### Assumption A1 — Explicit domain identity

Every admitted observation identifies its domain \(i\). Domain identity is not inferred from the observation value alone.

### Open Problem OP1 — Observation Domain completeness

No complete universal set \(\mathcal{O}\) is asserted. A necessary and sufficient Observation Domain for each event class remains to be specified.

## 3. Projection functions

For each admitted relation from observation domain \(i\) to field \(D_k\), define a partial projection

\[
\pi_{i,k}:\mathcal{V}_i\rightharpoonup \mathcal{D}_k.
\]

For event \(e\), the projected contribution is

\[
d_{i,k}(e)=\pi_{i,k}(o_i(e))
\]

when both \(o_i(e)\neq\bot\) and \(\pi_{i,k}\) are defined. Undefined projections remain explicit and are not replaced by inferred values.

### Assumption A2 — Projection purity

For fixed declared inputs and fixed declared rules, \(\pi_{i,k}\) yields one result and does not alter its source observation.

### Assumption A3 — Projection provenance

Every projected value retains the relation \((i,k,e)\) needed to identify its observation domain, destination field, and event.

### Open Problem OP2 — Information preservation

The minimum information that each \(\pi_{i,k}\) must preserve for valid field judgment is not yet characterized.

## 4. The eight-field product space

Define the TRUE8D candidate field space as

\[
\mathcal{D}=\mathcal{D}_1\times\mathcal{D}_2\times\cdots\times\mathcal{D}_8.
\]

The eight field roles are:

| Field | Candidate role |
|---|---|
| \(D_1\) | Intent |
| \(D_2\) | State |
| \(D_3\) | Coordinate |
| \(D_4\) | Evidence |
| \(D_5\) | Execution |
| \(D_6\) | Privacy |
| \(D_7\) | Generative Transport / Router |
| \(D_8\) | Adjudication |

A field vector is

\[
x=(d_1,d_2,d_3,d_4,d_5,d_6,d_7,d_8)\in\mathcal{D}.
\]

The coordinate component \(d_3\) is a proposal space; the adjudication component \(d_8\) is not embedded into \(d_3\). Privacy judgment in \(d_6\), reference relations in \(d_7\), and adjudication in \(d_8\) remain distinct mathematical roles.

### Assumption A4 — Field separation

No component is identified with another solely because both influence the same judgment.

### Open Problem OP3 — Field-space sufficiency

It remains unproved that these eight spaces are necessary and sufficient for every event class.

## 5. Constraint Hypergraph

For event \(e\), define a labeled Constraint Hypergraph

\[
H_e=(V_e,\mathcal{H}_e,\lambda_e),
\]

where:

- \(V_e\) contains admitted observations, projected values, field components, and relevant prior-state elements;
- \(\mathcal{H}_e\subseteq 2^{V_e}\setminus\{\varnothing\}\) is a set of hyperedges;
- \(\lambda_e:\mathcal{H}_e\to\mathcal{C}\) assigns a constraint to each hyperedge.

A constraint evaluation is a partial function

\[
\gamma_c: \prod_{v\in h_c}\mathrm{Val}(v)
\rightharpoonup
\{\mathrm{SAT},\mathrm{VIOLATED},\mathrm{UNRESOLVED}\}.
\]

`UNRESOLVED` is preserved as a distinct result. It is not automatically equivalent to either satisfaction or violation.

### Assumption A5 — Constraint visibility

Every constraint capable of changing adjudication appears as a labeled hyperedge in \(H_e\).

### Open Problem OP4 — Constraint completeness

There is no proof that a constructed \(H_e\) contains all materially relevant constraints.

## 6. Priority Policy

A Priority Policy is a declared function

\[
p:\mathcal{M}_e\to\mathcal{J},
\]

where \(\mathcal{M}_e\) is the set of evaluated constraint configurations for event \(e\). The policy resolves precedence among satisfied, violated, and unresolved constraints without deleting any input result.

For a fixed policy reference, version, event, prior state, observation family, projection family, and constraint hypergraph, the judgment is required to be single-valued.

### Assumption A6 — Fixed-policy determinism

If all declared mathematical inputs and rule versions are equal, repeated evaluation by \(p\) returns the same member of \(\mathcal{J}\).

### Open Problem OP5 — Policy composition

The algebra for composing several priority policies, including associativity, precedence, and conflict resolution, remains undefined.

### Required Theorem RT0 — Deterministic composition

A proof is required that the composition of projections, constraint evaluations, and a fixed priority policy is single-valued over its declared domain. Status: `UNPROVEN`.

## 7. Transition operator and stopping condition

Let the candidate transition operator for event \(e\) be

\[
F_e:\mathcal{S}\rightharpoonup\mathcal{S}\times\mathcal{J},
\qquad
F_e(s_n)=(\widehat{s}_{n+1},j_n).
\]

The committed-state sequence is defined by

\[
s_{n+1}=
\begin{cases}
\widehat{s}_{n+1}, & j_n=\mathrm{ALLOW},\\
s_n, & j_n\in\{\mathrm{HOLD},\mathrm{BLOCK},\mathrm{QUARANTINE}\}.
\end{cases}
\]

Thus only `ALLOW` changes the committed state. Every other judgment preserves the previous committed state.

Define the stopping predicate

\[
\mathrm{Stop}_e(s_n,j_n)\iff
\bigl(j_n\neq\mathrm{ALLOW}\bigr)
\lor
\bigl(F_e^{\mathcal{S}}(s_n)=s_n\bigr),
\]

where \(F_e^{\mathcal{S}}\) denotes the proposed-state component of \(F_e\). A non-allow judgment stops commitment for the current evaluation; it does not prove that a mathematical fixed point exists.

### Assumption A7 — Finite declared state space

Finite-step arguments may assume that the reachable subset \(\mathcal{S}_e\subseteq\mathcal{S}\) is finite. This assumption must be established separately for each event class.

### Assumption A8 — Stable declared inputs

During an iteration sequence, the event, observation family, projection family, constraint hypergraph, and priority policy remain fixed unless a new sequence is explicitly formed.

## 8. Fixed-point proof obligations

A fixed point for event \(e\) is a state \(s^*\in\mathcal{S}\) satisfying

\[
F_e^{\mathcal{S}}(s^*)=s^*
\]

under an `ALLOW` judgment. A stable preservation caused by `HOLD`, `BLOCK`, or `QUARANTINE` is not, by itself, evidence of a fixed point.

### Required Theorem RT1 — Fixed-point existence

For a stated admissible class of events and states, prove conditions under which at least one \(s^*\) exists. Status: `UNPROVEN`.

### Required Theorem RT2 — Fixed-point uniqueness

For a stated admissible class, prove conditions under which any fixed points \(s^*_1\) and \(s^*_2\) satisfy \(s^*_1=s^*_2\). Status: `UNPROVEN`.

### Required Theorem RT3 — Global finite-step convergence

For every admissible initial state \(s_0\), prove the existence of a finite \(N\) such that \(s_N=s^*\), with a bound on \(N\) stated in terms of declared properties of the reachable state space and operator. Status: `UNPROVEN`.

Finite state space alone is insufficient: an operator may enter a nontrivial cycle. A convergence proof therefore requires an additional well-founded order, strict descent measure, contraction property, or equivalent condition.

### Open Problem OP6 — Convergence measure

No generally valid well-founded measure or contraction structure has been selected.

## 9. Cross-node equivalence

Let two nodes \(a\) and \(b\) evaluate the same declared mathematical input tuple

\[
I=(e,s_0,\{o_i\},\{\pi_{i,k}\},H_e,p).
\]

Define an equivalence relation \(\sim\) over outcomes. Exact equality is one possible choice, but a weaker semantic equivalence may be admissible only if its criteria are declared before evaluation.

### Assumption A9 — Input agreement

Cross-node comparison assumes that nodes agree on every component of \(I\), including ordering rules and all referenced versions.

### Assumption A10 — Common equivalence relation

All compared nodes use the same declared relation \(\sim\).

### Required Theorem RT4 — Cross-node equivalence

Under explicit input-agreement and evaluation assumptions, prove that the terminal outcomes \(r_a\) and \(r_b\) satisfy

\[
r_a\sim r_b.
\]

Status: `UNPROVEN`.

### Open Problem OP7 — Agreement prerequisites

The agreement mechanism, admissible failures, and treatment of delayed or conflicting observations remain unspecified.

## 10. TFS candidate definition

For event \(e\), a state \(s^*\) is a **TFS candidate** only if all of the following hold:

1. the relevant Observation Domain and observation family are declared;
2. all required projections are defined or explicitly unresolved;
3. the Constraint Hypergraph is evaluated without hidden outcome-changing constraints;
4. the Priority Policy returns `ALLOW`;
5. the transition commits \(s^*\);
6. the stopping condition is satisfied by an allowed fixed point;
7. required equivalence and verification obligations for the stated event class are satisfied.

Because RT1–RT4 are unproved in the general case, this definition does not establish that a TFS candidate exists, is unique, is globally reachable, or is cross-node equivalent.

## 11. Open Problems summary

- `OP1`: complete Observation Domain by event class;
- `OP2`: projection information-preservation criteria;
- `OP3`: necessity and sufficiency of the eight field spaces;
- `OP4`: Constraint Hypergraph completeness;
- `OP5`: Priority Policy composition and conflict law;
- `OP6`: a valid finite-convergence measure;
- `OP7`: cross-node agreement prerequisites;
- formal characterization of admissible event and state classes;
- treatment of observation revision during an evaluation sequence;
- conditions under which semantic equivalence is substitutive across field judgment;
- a formal identity rule for accepted TFS results.

## 12. Status conclusion

The definitions above form a candidate mathematical vocabulary. Assumptions A1–A10 are premises requiring justification in each application. RT0 is an additional determinism obligation. RT1–RT4 are explicit unproved proof obligations, and the listed Open Problems remain unresolved. No existence, uniqueness, global finite convergence, or cross-node equivalence theorem is asserted as established.
