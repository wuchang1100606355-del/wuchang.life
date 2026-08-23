---
name: w7tp-bounded-delegation-chain
description: Create or validate W7TP bounded capability delegation derived from a Founder-originated grant without privilege expansion. Use when granting a person, service, agent, model, device, node, or downstream capability a limited right to perform specific actions for a target, purpose, time window, or effect class, and when OAuth or external credential delegation must remain subordinate to W7TP authority.
---

# W7TP Bounded Delegation Chain

Delegate capability, never Founder identity.

## Rules

- The root grant must reference a Founder-originated grant artifact. A string saying `Founder` is not authenticity proof.
- Every child delegation must be equal to or narrower than its parent.
- A child must not add capabilities, targets, purposes, effect classes, delegation rights, or validity beyond its parent.
- External OAuth, service-account, API-token, platform-admin, or policy roles are transport/runtime credentials only.
- Revocation of a parent invalidates descendants according to the active W7TP contract.
- `delegation_allowed=false` stops the chain.

## Workflow

1. Reuse the supplied root grant and chain.
2. Validate monotonic attenuation with `scripts/validate_delegation_chain.py`.
3. If valid, emit the smallest downstream grant needed for the requested effect.
4. In `FAST_LAND`, do not add secondary approvals after the chain passes unless the requested effect itself requires a separate D8 authorization.
5. Preserve the chain reference in execution evidence.

Read `references/delegation-contract.md` before designing a new delegation object.
