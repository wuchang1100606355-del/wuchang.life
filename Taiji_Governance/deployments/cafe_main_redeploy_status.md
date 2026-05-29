# Cafe Main Store Redeployment Status

Status date: 2026-05-10
Site label: Liaoguo Cafe main store
Governance mode: Taiji Gateway gated deployment

## Node Status

| Role | Digital identity | Current mapped node | VPN address | Status | Notes |
|---|---|---|---|---|---|
| VPN node server 01 | `TDI-NODE-vpn-server-01` | `taiji01` | `100.71.224.18` | inventory confirmed | Subnet router for `192.168.50.0/24`; approved route present in CSV |
| Admin workstation | `TDI-NODE-admin-msi` | `msi` | `100.107.187.77` | inventory confirmed | Likely current WSL runtime node based on host listener |
| Windows host | `TDI-NODE-admin-msi-win11` | `msi-win11-in` | `100.105.82.28` | inventory confirmed | Management host candidate |
| Customer display 02 | `TDI-NODE-display-02` | pending | pending | inventory required | Needs device hostname, LAN IP, and Tailscale identity |
| Sunmi POS | `TDI-NODE-sunmi-pos` | pending | pending | inventory required | Needs device hostname, LAN IP, Tailscale identity, and Odoo POS binding |
| Router | `TDI-NET-asus-rt-be86u` | ASUS RT-BE86U | LAN `192.168.50.1` | user-provided | Router admin plane must be restricted by ACL/Gateway policy |
| Odoo Runtime | `TDI-SERVICE-odoo-runtime` | `wuchang_os_odoo_18` | localhost `8069` | running | Database manager was reachable on localhost |
| Five Metric Engine | `TDI-SERVICE-five-metric-engine` | host service | port `8105` | running | Policy locked; observed listening on `0.0.0.0` |

## Deployment State

Current state: manifest preparation only.

No remote deployment has been executed by this task. No router, VPN, Odoo, Google,
or Gemini configuration has been changed.

## Safe Deployment Gate

Before any live deployment:

1. Run read-only probe.
2. Create SHA256 baseline.
3. Run `taiji-metric-preflight` against the deployment manifest.
4. Run live commands only through `taiji-guarded-run`.
5. Write audit jsonl.
6. Keep rollback instructions next to the manifest.

## Open Items

- Confirm customer display 02 device identity.
- Confirm Sunmi POS device identity.
- Confirm whether customer display and POS are LAN-only, Tailnet-only, or dual-homed.
- Define ACL that blocks ephemeral cloud nodes from router admin access.
- Bind Odoo POS access to Gateway-approved clients only.
