# Distributed Governance Reconciliation

Distributed nodes may continue only approved local low-risk operations.

Reconciliation compares:

- audit journals
- SHA256 baselines
- topology state
- authority continuity
- replay continuity
- deadbox state

If local baseline and distributed node state diverge, route to `warn`, `quarantine`, or `deadbox` depending on mutation risk.
