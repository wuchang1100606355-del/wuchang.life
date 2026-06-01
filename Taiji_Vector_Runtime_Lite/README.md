# Taiji Vector Runtime Lite

Local-only vector runtime skeleton for Taiji_Hub.

Design rules:

- No external API calls.
- No plaintext context persistence.
- No service account JSON.
- No OAuth tokens.
- Bind to `127.0.0.1` unless an approved Gateway policy says otherwise.
- Run preflight before execution.

Default dry run:

```bash
Taiji_AutoBuild/scripts/02_start_vector_lite.sh
```

Generate a local start plan:

```bash
Taiji_AutoBuild/scripts/02_start_vector_lite.sh --plan
```

This script does not start the service. A live local start must be performed by
a separate approved process after human decision, Gateway policy, audit, and
preflight checks.

Endpoints:

- `GET /health`
- `GET /policy`
- `POST /vectors/upsert`
- `POST /vectors/search`

The vector API accepts plaintext in request memory, derives a deterministic
local hash/vector, and discards the plaintext before storing anything.
