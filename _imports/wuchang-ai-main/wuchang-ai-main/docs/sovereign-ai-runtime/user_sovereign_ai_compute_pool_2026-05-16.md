# User-Sovereign AI Runtime and Compute Sharing Pool

Date: 2026-05-16
Repository: wuchang-ai
Status: Concept architecture record

## 1. Core Thesis

This system is designed as a user-centered sovereign AI runtime.

The central principle is:

> The model may be borrowed, cloud compute may be outsourced, and tools may be connected, but memory, identity, intent, authorization, auditability, persona continuity, and context formation authority must remain under the user's control.

The system does not attempt to replace large cloud AI models with a small device model. Instead, the user endpoint acts as the sovereign controller, while cloud models and shared compute nodes act as replaceable inference resources.

## 2. Main Positioning

Preferred technical names:

- Personal Sovereign AI Runtime
- User-Sovereign AI Runtime
- Sovereign AI Gateway Infrastructure
- Persona-Sovereign Multi-Model Runtime
- Governed Compute Sharing Pool

Chinese working names:

- 使用者主權 AI 執行環境
- 主權 AI 匝道基礎設施
- 人格主權多模型投影系統
- 治理型算力共享池
- 算力共享池

## 3. Architectural Difference from Cloud AI

Traditional cloud AI architecture:

```text
Platform account
→ platform memory
→ platform persona
→ platform alignment
→ platform-controlled model
```

User-sovereign AI runtime:

```text
User endpoint
→ sovereign memory
→ user intent policy
→ execution gateway
→ no-plaintext governed packet
→ local / shared / cloud inference
→ local transient context rebuild
→ audit
→ wipe
```

The key inversion is:

```text
Traditional AI: user rents an AI inside the platform.
Sovereign AI: AI temporarily rents user-authorized context from the endpoint.
```

## 4. Persona Belongs to the Endpoint

The persona is not located in the cloud model.

```text
Cloud model ≠ persona
Persona = endpoint sovereign state
```

The endpoint maintains:

- long-term memory
- identity state
- user intent history
- authorization boundaries
- behavior preferences
- relationship mappings
- governance profile
- audit state
- persona continuity state

The model is only a replaceable inference engine that temporarily projects the endpoint-held persona.

This allows:

- one persona across multiple models
- model replacement without losing persona continuity
- local persona ownership
- reduced platform lock-in
- endpoint-controlled memory retention and deletion

## 5. One Persona, Multi-Model Application

The system supports:

```text
One endpoint persona → multiple model runtimes
```

Examples:

- 0.5B local model for governance, routing, preflight, and intent classification
- 3B–7B local model for low-risk local tasks
- cloud reasoning model for difficult reasoning
- code model for software development
- vision model for image analysis
- speech model for voice interaction

The persona layer is projected into each model through a controlled projection interface rather than being stored inside the model provider.

## 6. Role of the 0.5B Endpoint Model

The 0.5B model is not intended to replace large models.

Its purpose is to protect the user's sovereignty over large models.

Suitable responsibilities:

- intent classification
- policy routing
- execution preflight
- risk detection
- memory indexing
- vector namespace mapping
- permission gating
- wipe trigger
- local summarization
- transient rebuild support

The small model acts as an AI runtime governor, not as the main intelligence layer.

## 7. Sovereign AI Gateway Infrastructure

The gateway provides a protected boundary between user context and AI services.

Main gateway functions:

- identity verification
- namespace mapping
- device trust verification
- policy binding
- context minimization
- intent governance
- runtime preflight
- dynamic routing
- transient rebuild coordination
- wipe and audit triggering

Core principle:

```text
User = subject
Gateway = governance boundary
Model = tool
```

The gateway protects not only data security, but also the user's governance authority over AI.

## 8. Governed Execution Packet

A governed execution packet should avoid transmitting raw natural-language context or directly recoverable personal data.

Typical packet fields:

- state identifier
- authorization boundary
- vector namespace
- route trace
- cache trace
- policy hash
- audit reference
- minimal task projection

The packet is designed for controlled inference, not full context transfer.

## 9. Transient Context Rebuild

Context is not treated as a permanent cloud-side object.

Instead:

```text
context = locally reconstructed, temporary, authorized state
```

The endpoint rebuilds context only inside a transient execution window based on:

- endpoint memory
- authorization boundary
- returned reference code
- cache trace
- policy constraints
- active task intent

After the task ends, times out, or violates policy, the runtime unloads or wipes the transient state and records an audit event.

## 10. Compute Sharing Pool

The system includes a governed compute sharing pool.

This is not a mining pool and not an unrestricted distributed AI system.

It is a user-sovereign compute contribution mechanism:

```text
compute may be shared
memory must not be shared
persona must not be shared
identity must not be shared
complete context must not be shared
```

The compute sharing pool may use idle or underused resources from:

- mobile phones
- POS devices
- public community devices
- internet cafe computers
- local edge servers
- association-owned hardware
- volunteer compute nodes

The contribution is partial, revocable, governed, audited, and limited by user/device policy.

## 11. Suitable Distributed Tasks

Good candidates for distributed or shared compute:

- embedding generation
- vector comparison
- reranking
- semantic filtering
- namespace verification
- policy validation
- route scoring
- local caching
- audit witness tasks
- low-risk quantized inference

Tasks that should generally remain local or highly restricted:

- full identity reconstruction
- full persona state access
- sensitive context rebuild
- raw personal data inference
- privileged authorization decisions
- high-risk financial or legal execution

## 12. Invisible Cooperative Runtime Layer

The system may include an invisible cooperative runtime layer.

This does not mean secret or unauthorized computation.

It means that, when user devices are online and authorized, they may contribute small governed runtime functions without exposing complete context or persona.

Possible functions:

- transient cache participation
- vector shard comparison
- namespace witness
- policy verification
- route participation
- task micro-scheduling
- distributed wipe synchronization
- audit witness

Governance requirements:

- explicit user authorization
- visible governance UI
- opt-out and pause controls
- resource caps
- battery and thermal limits
- audit records
- no covert computation
- no raw personal context sharing

## 13. Quantified User-Side Advantage

The advantage over standard cloud AI should be measured by governance and exposure reduction, not only by model capability.

Important metrics:

### Context Exposure Ratio

```text
CER = plaintext context exposed / total contextual state
```

Goal: reduce plaintext exposure by replacing raw context with references, namespaces, hashes, routes, and transient local reconstruction.

### Persistent Memory Risk

```text
PMR = persistence time × identity coupling × replication scope
```

Goal: reduce long-term cloud-side memory risk by keeping memory and persona on the endpoint.

### Agent Authority Radius

```text
AAR = accessible tools + accessible memory + accessible identity + routing freedom
```

Goal: compress the authority radius of AI agents through preflight, gateway control, and policy-bound execution.

## 14. Controlled Degradation

This architecture may reduce some AI freedom and raw context capacity.

Expected tradeoffs:

- lower unrestricted long-context reasoning
- lower autonomous agent freedom
- lower cross-session memory continuity inside the cloud
- additional routing and preflight overhead

Compensating gains:

- stronger user sovereignty
- stronger auditability
- lower context exposure
- lower memory pollution risk
- safer multi-tenant deployment
- better policy enforcement
- stronger user trust

The objective is not maximum AI freedom, but useful AI under user-controlled risk.

## 15. Strategic Definition

This system should be described as:

> A user-sovereign AI runtime in which endpoint-held persona, memory, intent, authorization, and audit state govern multiple replaceable model providers and a governed compute sharing pool through a sovereign AI gateway.

Core statement:

```text
Model shared ≠ persona shared
Compute shared ≠ memory shared
Inference outsourced ≠ sovereignty outsourced
```

## 16. Patent and IP Note

Before claiming patentability, this architecture must pass a prior-art and implementation audit across:

- patents
- papers
- open-source projects
- AI agent frameworks
- RAG systems
- edge AI runtimes
- zero-trust systems
- service mesh systems
- confidential computing systems
- distributed compute networks

Claims should focus on concrete technical mechanisms:

- endpoint-held persona state
- no-plaintext governed execution packet
- policy-hash preflight
- transient context rebuild
- namespace-bounded retrieval
- governed compute sharing pool
- multi-model persona projection
- audit-bound wipe and execution lifecycle

Avoid unsupported absolute claims such as absolute privacy, irreversible anonymity, or hardware-level wipe unless backed by implementation evidence.
