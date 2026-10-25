# Total Field skill taxonomy

## Product families

Assign one primary family and any necessary secondary families. A new capability must fit one of these before a new family is proposed.

| Code | Family | Product boundary |
|---|---|---|
| F01 | MEMBER_CONVERSATION | Natural-language chat, explanation, persona, and member experience; no action authority |
| F02 | IDENTITY_SEAT_CONSENT | Identity proof, member binding, role quota, Seat, consent, reauthentication, and session lifecycle |
| F03 | INTENT_PRODUCT_OUTPUT | Intent resolution, product/output contracts, acceptance criteria, and human response rendering |
| F04 | INFORMATION_CONTEXT | Identity-authorized D1-D8 retrieval, provenance, compaction, search, and de-identified evidence |
| F05 | LOCAL_CANDIDATE | Local LLM candidate generation, code/chat roles, and local resource scheduling |
| F06 | CLOUD_CANDIDATE | Explicitly authorized cloud completion, research, or candidate fragments; sanitized input only |
| F07 | CANDIDATE_CONVERGENCE | Local/cloud normalization, conflict detection, degradation policy, and `receive_candidate` |
| F08 | RESEARCH_ANALYSIS | Evidence-grounded research, comparison, valuation, recommendation, and report candidates |
| F09 | CONTENT_DOCUMENT | Text, document, spreadsheet, presentation, structured-data, and public-content candidates |
| F10 | SOFTWARE_DEVELOPMENT | Source, configuration, schema, test, package, and code-review candidates |
| F11 | SANDBOX_CANARY | Static validation, fixtures, transient isolation, canary, compatibility, and resource checks |
| F12 | GENERATIVE_TRANSMISSION | Protocol-bearing W7TP packet construction, receiving, reconstruction, and verification |
| F13 | REMOTE_RECONSTRUCTION | Cross-node intent-field construction and receiver evidence, with carrier separated from W7TP semantics |
| F14 | PRIVATE_MEDIA | Owner-only image/video/audio reconstruction with provenance and no public deceptive use |
| F15 | BUSINESS_WORKFLOW | Odoo, POS, menu, property, association, merchant, member, and operational workflow candidates |
| F16 | PUBLIC_EXPERIENCE | Website, member portal, public information, accessibility, and communication outputs |
| F17 | OBSERVABILITY | Read-only status, health, evidence, logs, monitoring, and collision detection |
| F18 | LIVE_CHANGE_ROLLBACK | Deploy, restart, DB, router, runtime configuration, rollback, and recovery under exact authority |
| F19 | IP_EVIDENCE_SEAL | Patent, claim/evidence mapping, formal packets, archives, manifests, and seal candidates |
| F20 | META_GOVERNANCE | Skill governance, policy, red-team, D8 review, canonical proposals, and lifecycle control |

## Maximum effect classes

| Class | Maximum effect | Required gate |
|---|---|---|
| E0 | Chat or presentation only; no external read or persistent artifact | Active identity/Seat and D8 policy receipt |
| E1 | Read-only retrieval, hashing, comparison, status, or evidence | Profile scope, member boundary, provenance, D8 receipt |
| E2 | Reversible candidate artifact or review packet | Candidate path, hashes, red-team pre-definition, Total Field review before promotion |
| E3 | Isolated transient execution or canary | Exact one-shot authorization, isolation, resource budget, auto-removal, post-operation red-team |
| E4 | Governed persistent non-protected state change | Separate Founder instruction, D8 decision, snapshot, health checks, rollback, final human confirmation |
| E5 | Protected/live/formal/authority-changing effect | Exact human decision, red-team pre-activation, strongest D8 envelope, reauthentication when applicable, audit receipt |

Classify by the strongest possible effect in the implementation, not the most benign example prompt. A skill capable of both read-only status and deployment is E4 or E5 unless split into separate skills with distinct manifests and tool boundaries.

## Effect examples

- Writing a code draft into a candidate workspace is E2.
- Running it once in a no-network, read-only, auto-removed container is E3.
- Updating a persistent service configuration is E4.
- Reading member plaintext, changing identity/Seat authority, payment, formal filing, canonical pointer change, or production DB mutation is E5.
- A carrier connection alone does not raise effect class; the operation carried through it does.

## Keep evidence maturity separate from effect class

Technology-identity evidence uses `EV0_UNSUPPORTED`, `EV1_ASSERTION`, `EV2_SECONDARY_SOURCE`, `EV3_PRIMARY_DOCUMENT`, `EV4_IMPLEMENTATION_EVIDENCE`, and `EV5_REPRODUCIBLE_CAUSAL_EVIDENCE`. These labels describe evidence maturity only. They never replace E0-E5 maximum effect classes, grant execution authority, or establish patentability.
