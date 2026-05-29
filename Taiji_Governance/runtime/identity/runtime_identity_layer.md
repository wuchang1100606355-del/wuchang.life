# Runtime Identity Layer

Runtime identity maps devices, services, and nodes into trust positions.

Known anchors:

- `TDI-NODE-admin-msi`
- `TDI-NODE-msi-win11-operator-console`
- `TDI-NODE-vpn-server-01`
- `TDI-NODE-display-02`
- `TDI-NODE-sunmi-pos`
- `TDI-SERVICE-odoo-runtime`
- `TDI-SERVICE-five-metric-engine`
- `TDI-SERVICE-local-ollama`
- `TDI-SERVICE-local-openwebui`

Pending identities must not receive production mutation authority.

## Local Machine Gateway Control

`TDI-NODE-admin-msi` is the Linux/WSL development and orchestration node.
`TDI-NODE-msi-win11-operator-console` is the Windows 11 Pro desktop/operator console.

Both are inside the local trust boundary, but neither may bypass Gateway/Five Metric Gate for system actions.

Direct local model use is limited to local chat, model testing, draft generation, and preview.
Any action that touches Odoo production state, Google organization settings, payment, secrets, member plaintext, router configuration, deployment, or system policy must be converted into a governed packet and routed through Taiji Gateway / Five Metric Gate / audit / human decision where required.
