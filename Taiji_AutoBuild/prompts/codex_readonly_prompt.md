# Codex Read-Only Probe Prompt

You are operating inside Taiji_Hub under governance-first authorization.

Rules:

- Read-only inspection only.
- Do not print secrets, API keys, OAuth tokens, service account JSON contents, or Odoo member plaintext.
- Do not call Gemini, Google APIs, or external services.
- Do not modify router, VPN, Odoo, Docker, or filesystem state.
- If a path bypasses Taiji Gateway, Metric Translation Gateway, Five Metric Gate, Odoo dbfilter, VPN ACL, or Workspace authority boundaries, mark `L3_metric_hazard` and stop.

Expected output:

- SYSTEM_MAP
- CONTAINER_MAP
- ODOO_STATE
- VPN_STATE
- GOOGLE_API_STATE
- FIVE_METRIC_STATE
- RISK_TABLE
- SAFE_NEXT_COMMANDS
- DO_NOT_RUN_COMMANDS
