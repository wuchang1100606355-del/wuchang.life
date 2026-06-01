# Tailnet Rollback Plan

Generated: 2026-05-10T11:18:36.931634+00:00
Manifest: `/mnt/c/Users/o0930/Taiji_Hub/Taiji_Governance/deployments/tailscale_deployment_manifest.json`

This plan contains no secrets.

## Rollback Principles

1. Do not delete data volumes automatically.
2. Stop only services that were started by an approved guarded deployment.
3. Restore previous systemd units from a recorded baseline.
4. Revert router and VPN changes only from their approved admin consoles or
   guarded automation path.
5. Record every rollback step in audit jsonl.

## Current Status

No live deployment was performed by this manifest generator, so no runtime
rollback command is required from this script.
