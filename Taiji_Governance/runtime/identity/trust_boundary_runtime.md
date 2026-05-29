# Trust Boundary Runtime

| Trust position | Allowed | Blocked |
| --- | --- | --- |
| trusted_local | governance files, schemas, local tests | raw secrets |
| trusted_local_ui | local chat, preview, human confirmation | production mutation without gateway |
| local_llm_backend | inference for governed packet or local draft | authority escalation, secret access |
| trusted_vpn | low-risk routing after preflight | authority escalation |
| limited_service | service-specific draft or read-only action | admin mutation |
| pending_identity | inventory only | production action |
| untrusted | no execution | all mutation |
| deadbox | audit only | runtime re-entry |

Trust position is part of the topology vector.

Local Windows/Ollama/OpenWebUI are trusted for operator convenience, not for unrestricted execution authority.
