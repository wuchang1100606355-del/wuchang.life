# Taiji01 Topology Brain Transfer v0.1

Purpose: install the Taiji topology brain model name on node `taiji01` without transferring secrets or member plaintext.

Runtime model:
- model name: `metric-language-gateway-ai:latest`
- taiji01 base model: `llama3.1:8b`
- source: local metric-language gateway Modelfile prefix

Rules:
- no secret material included
- no service account JSON included
- no member plaintext included
- no Tailscale ACL changes
- no production Odoo write
- Ollama model creation only
