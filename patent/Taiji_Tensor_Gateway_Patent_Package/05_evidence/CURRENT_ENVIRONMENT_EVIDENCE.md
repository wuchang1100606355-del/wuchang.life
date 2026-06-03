# Current Environment Evidence Summary

Observed deployment topology:

## MSI

- Open WebUI
- wuchang_gpu_brain / Ollama
- taiji_claw_safe
- taiji_voice_gateway
- taiji_device_resilience_adapter
- taiji_pos_google_voice_tool
- temporary GPU worker role

## taiji01

- Always-on anchor role
- Odoo 18
- PostgreSQL
- Ollama
- qwen2.5-coder:1.5b
- candidate tensor translator node

## penguin

- Ollama
- gemma3:4b
- lightweight worker role

## Completed Proof Points

- taiji01 Ollama endpoint is reachable.
- penguin Ollama endpoint is reachable.
- MSI is treated as a temporary/offline-capable GPU node.
- Initial metric compact evaluation has been performed.
- The product topology requires tensor routing, governance boundaries, deadbox routing, and replay protection.
