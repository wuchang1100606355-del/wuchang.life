# Hardware-Bound One-Time Decrypt

Tool: `Taiji_AutoBuild/scripts/04_system_total_probe.py`

Purpose:

- Create a system total probe that binds to this local hardware without printing
  raw hardware identifiers.
- Support one-time decryption for local envelopes.
- Bind cryptographic envelopes to the local physical fingerprint and local
  authorization proof.
- Write audit records for probe, seal, decrypt success, and decrypt block.
- Write AI rescue snapshots for context-loss recovery without exposing secrets.

Rules:

- Every command invocation must be locally authorized with `--local-auth-env`,
  `--local-auth-file`, or an interactive local prompt.
- Every operational command also requires a human decision receipt. Without
  human decision, it is unavailable.
- Raw hardware IDs are never printed.
- Secret plaintext is never printed.
- Service account JSON, OAuth tokens, private keys, and passwords are not stored
  by this tool.
- Decryption output must be written to a new file with `0600` permissions.
- A used marker blocks repeated decrypt attempts for the same envelope.
- No SSH, SCP, system restart, Docker Compose mutation, or remote deployment is
  performed by this tool.

Commands:

```bash
python3 Taiji_AutoBuild/scripts/04_system_total_probe.py probe --local-auth-file /path/to/local-auth.txt
python3 Taiji_AutoBuild/scripts/04_system_total_probe.py self-test --local-auth-file /path/to/local-auth.txt --human-decision /path/to/decision.json
python3 Taiji_AutoBuild/scripts/04_system_total_probe.py rescue-snapshot --local-auth-file /path/to/local-auth.txt --human-decision /path/to/decision.json
```

For real local use, provide the passphrase through an environment variable or a
local passphrase file. Do not commit the passphrase or decrypted output.
