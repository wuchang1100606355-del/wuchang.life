---
name: w7tp-stateful-information-flow
description: Carry W7TP security labels and disclosure constraints across multi-step agent, tool, session, model, and service operations. Use when data from one operation can affect what later operations may reveal, transmit, transform, or write, including taint propagation, write-down prevention, redaction, declassification, session security state, and cross-call privacy controls.
---

# W7TP Stateful Information Flow

Treat security state as explicit carried state, not model memory.

## Rules

- Never infer a security label from semantics when the active contract did not declare one.
- Propagate declared labels across operations deterministically.
- A transformation may reduce disclosure only when the declared policy says the transformation is sufficient.
- Declassification requires the exact authority artifact required by the active W7TP contract.
- Redaction output is evidence of a transformation, not proof that disclosure is safe.
- External policy engines may advise or enforce local flow rules; they never create W7TP D8 authority.

## Workflow

1. Read current session/security state and the requested source-to-destination flow.
2. Apply only the supplied `label_rank` and flow policy. Do not invent a universal classification lattice.
3. Use `scripts/apply_information_flow.py` for deterministic propagation and write-down checks.
4. Return `ALLOW`, `ALLOW_WITH_REDACTION`, or `DENY` plus the next carried state.
5. In `FAST_LAND`, use the decision immediately; do not run an additional policy round unless the operation changes target, label, or effect.
6. Preserve the resulting state and evidence reference for the execution receipt.

Read `references/information-flow-contract.md` when creating a new flow policy.
