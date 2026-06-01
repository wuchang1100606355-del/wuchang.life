# AI Rescue Snapshots

Purpose:

- Provide a safe recovery anchor if an AI agent loses context, drifts from the
  governance rules, or needs to resume after compaction.

Rules:

- Every snapshot requires local authorization.
- Every snapshot requires a human decision receipt. Without human decision, the
  tool is unavailable.
- Snapshots include hashes, status booleans, redacted excerpts, and recovery
  instructions.
- Snapshots include the Taiji architecture profile for layers and standards:
  physical anchor, cryptographic envelope, tensor protocol, context runtime,
  event mesh, governance engine, community currency, ESG mapping, and sovereign
  AI nodes.
- Physical layer data is represented only as hashes and availability flags.
- Cryptographic layer data records the envelope schema, KDF, AEAD, and one-time
  marker policy without exposing plaintext or key material.
- Snapshots do not include raw hardware identifiers, secrets, service account
  JSON, OAuth tokens, Google private data, Odoo member plaintext, or ChatGPT
  export text.
- Snapshots do not perform remote execution.

Command:

```bash
python3 Taiji_AutoBuild/scripts/04_system_total_probe.py human-decision --scope rescue-snapshot --expires-at 2099-01-01T00:00:00+00:00 --local-auth-file /path/to/local-auth.txt --human-proof-file /path/to/human-proof.txt
python3 Taiji_AutoBuild/scripts/04_system_total_probe.py rescue-snapshot --local-auth-file /path/to/local-auth.txt --human-decision Taiji_Governance/human_decisions/<decision_id>.decision.json
```
