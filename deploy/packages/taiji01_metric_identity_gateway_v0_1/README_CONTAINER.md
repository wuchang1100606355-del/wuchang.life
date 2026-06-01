# taiji01 Metric Identity Gateway Container

This container is the official taiji01 local identity gateway for Windows/WSL frontend LLM access.

Flow:

Windows / WSL frontend -> taiji01:11435 -> identity five-code allowlist from Odoo mapping -> taiji01 Ollama 127.0.0.1:11434.

Identity source:

- `/home/taiji_01/Taiji_Hub/Taiji_Odoo/identity_map/five_code_identity_allowlist.json`
- This file is the Odoo direct mapping export / projection point.
- The gateway treats it as read-only.

Container hardening:

- host network only for local Tailscale bind
- read-only filesystem
- no-new-privileges
- all Linux capabilities dropped
- memory databases mounted read-only
- audit log mounted read-write

No secrets, tokens, service account JSON, or member plaintext are included.
