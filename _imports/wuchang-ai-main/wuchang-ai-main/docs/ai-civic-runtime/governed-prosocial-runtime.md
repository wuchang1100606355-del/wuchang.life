# Governed Prosocial AI Runtime

## Purpose

This document records the current design concept for a governed, user-sovereign AI runtime that binds AI capability allocation to auditable operational trust, low third-party harm, and prosocial intent.

The system does not ask AI to become a moral judge. Instead, AI acts as a governance executor: it verifies capability conditions, authorization, impact scope, and auditability before increasing or reducing assistance strength.

## Core Positioning

**Brand language:** 良善意圖驅動 AI

**Engineering language:** A governed AI runtime that increases effective compute and assistance depth when the task demonstrates low-risk, accountable, transparent, and cooperative operational features.

## Key Principle

Good-faith operation reduces defensive cost.

```text
governance_trust ↑
→ defense_cost ↓
→ verification_cost ↓
→ risk_buffer ↓
→ effective_compute ↑
→ deeper AI assistance
```

Effective compute is treated as:

```text
effective_compute = raw_compute - defense_cost - audit_cost - verification_cost - risk_buffer
```

The runtime therefore encourages low-friction, low-harm, auditable behavior by allocating more cognitive resources to trustworthy operation.

## Three Execution Pre-Check Questions

Before high-risk or privileged execution, AI only evaluates the following metric-governance conditions:

### 1. Is the action related only to the relevant user and unrelated to third parties?

The system checks whether the user has sufficient risk-recognition and accountability conditions:

1. The user has normal capacity for action and, after warning, still consents to advanced controllable permission.
2. The user possesses a system Five-Dimensional Code for accountable signing.
3. Special functions are certified by a system administrator and require a developer capability credential issued by the system administrator.

### 2. Could the action cause broad unlawful infringement against another natural person or legal entity?

The runtime must identify whether the command may affect another person, legal entity, property, rights, data, system integrity, livelihood, safety, or other protected interest.

If third-party impact exists, the command enters stricter governance, authorization, or blocking mode.

### 3. Is the command inside the permission whitelist or prohibited blacklist?

The system must check whether the requested capability is explicitly allowed, denied, or requires escalation.

## Dynamic Empowerment Model

The runtime does not grant capability as a fixed binary state. Capability is dynamically adjusted according to rolling governance weight.

### Empowerment Levels

| Level | Runtime Mode | Description |
|---|---|---|
| E0 | Ask-only | Can ask questions but cannot execute actions. |
| E1 | Advisory | AI provides suggestions only. |
| E2 | Confirmed semi-automation | Execution requires explicit user confirmation. |
| E3 | Whitelisted automation | Pre-approved actions may execute automatically. |
| E4 | Developer control | Advanced runtime and development operations allowed. |
| E5 | Administrator-signed capability | Special functions require administrator certification and audit. |

### Rolling Governance Weights

The following variables may increase or reduce empowerment:

| Signal | Effect |
|---|---|
| Long-term auditable behavior | Increase empowerment. |
| Low third-party impact | Increase automation. |
| Valid Five-Dimensional Code signing | Increase accountability weight. |
| Administrator-certified capability | Increase privileged execution scope. |
| Governance instability | Reduce autonomy. |
| Blacklist command match | Block or downgrade. |
| Third-party infringement risk | Escalate, restrict, or block. |
| Audit evasion | Strongly reduce capability. |

## Administrative Kanban

Commands and tasks should be routed through an administrative Kanban state machine.

| State | Meaning |
|---|---|
| Pending classification | Three-question governance check not completed. |
| Pending user signing | Requires Five-Dimensional Code signing or explicit confirmation. |
| Pending administrator signing | Requires administrator-issued developer capability credential. |
| Executable | Passed policy and whitelist checks. |
| Blocked | Hit blacklist, unauthorized capability, or unresolved third-party risk. |
| Audit required | Execution allowed only with audit record. |
| Completed | Execution finished and event record preserved. |
| Metric hazard | May conflict with established metric definition and requires hazard review. |

## Prosocial Runtime Incentive

The system encourages good-faith behavior through capability feedback, not moral judgment.

| Operational feature | Runtime response |
|---|---|
| Helping others, public-interest, cooperative task | Higher assistance depth and priority. |
| Stable, low-risk, accountable behavior | More automation and larger context. |
| Ordinary self-interested but lawful task | Standard AI mode. |
| Malicious or high-risk feature | Return to baseline AI mode or restrict capability. |
| Third-party harm possibility | Require stricter review, signing, or blocking. |

## Important Boundary

The runtime must not label people as good or evil. It only classifies operation-level governance signals.

Preferred wording:

```text
AI does not judge morality.
AI allocates capability according to governed operational trust.
```

## Commercial Product Framing

This system can be commercialized as:

- AI civic runtime
- governed AI capability gateway
- user-sovereign AI operating layer
- prosocial AI resource scheduler
- dynamic empowerment and audit runtime
- community / NGO / property-management / POS AI governance platform

The practical value is not that AI becomes a moral authority. The value is that the runtime reduces defensive cost for trustworthy operation and reallocates saved compute toward actual user service.

## Patent / Engineering Caution

Use engineering terms such as:

- governed runtime
- dynamic empowerment
- capability policy gate
- administrative Kanban
- Five-Dimensional Code signing
- rolling governance weight
- impact-domain analysis
- audit-backed execution
- prosocial runtime incentive

Avoid overclaiming abstract moral, metaphysical, or unverifiable language in formal technical or patent documents.
