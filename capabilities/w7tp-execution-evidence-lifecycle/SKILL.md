---
name: w7tp-execution-evidence-lifecycle
description: Capture a W7TP execution from request through result as a compact evidence receipt linked to prior state without turning the receipt into authority. Use after tool, process, model, service, device, file, deployment, or candidate execution to record coordinates, effect, result, hashes, traces, errors, approvals, and ADI-return evidence, or when FAST_LAND needs one final receipt instead of repeated pre-execution validation stages.
---

# W7TP Execution Evidence Lifecycle

Record what happened after execution. Do not use evidence generation as a substitute for effect authorization.

## Workflow

1. Reuse the exact execution request/effect coordinate already used by the effect gate.
2. Capture start/end time, target, effect, outcome, evidence references, artifact hashes, trace references, error state, and authority reference used for the effect.
3. Link the receipt to `previous_receipt_hash` when a prior receipt exists.
4. Use `scripts/build_execution_receipt.py` to create a canonical JSON receipt and optional append-only JSONL ledger entry.
5. Return the receipt hash and execution outcome.
6. In `FAST_LAND`, this is the single normal post-execution closeout. Do not reopen source analysis unless execution failed.

## Hard boundaries

- `RECEIPT != AUTHORITY`
- `AUDIT_PASS != W7TP_PASS`
- `TRACE != SEMANTIC_TRUTH`
- `EXECUTION_SUCCESS != CANONICAL_ACTIVATION`
- Never silently overwrite a prior receipt or history entry.

Read `references/receipt-contract.md` for receipt semantics.
