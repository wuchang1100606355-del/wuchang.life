# Red / Blue Exchange

Status: available locally for system design review only.

Core rule:

- Red/blue team review is available.
- Cloud plaintext is unavailable.
- Red/blue team review is not a daily runtime mechanism.
- Red/blue team review must not be scheduled, daemonized, or triggered by
  production services.

This workflow:

- Requires local authorization.
- Requires human decision receipt with scope `red-blue-exchange` or `all`.
- Is limited to architecture, packaging, and pre-release hardening review.
- Does not call OpenAI, Google, Gemini, Vertex AI, or external APIs.
- Does not read secret directories.
- Does not store source-line plaintext evidence in reports; findings store
  file path, line number, rule, risk, and line SHA256 only.

Authority context:

OpenAI / Google super-admin / Ultra subscription and service-account authority
may be represented as non-secret governance metadata. Live cloud use requires
Gateway, Audit, Policy, and no plaintext context transfer.
