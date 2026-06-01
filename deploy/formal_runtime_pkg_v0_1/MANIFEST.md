# Taiji Formal Runtime Package v0.1 Manifest

Mode: conservative additive deployment artifact

## Files

- `runtime_adapters/formal_tensor_runtime_adapter_v0_1.py`
- `deploy/formal_runtime_pkg_v0_1/runtime_entry_v0_1.py`
- `deploy/formal_runtime_pkg_v0_1/env.example`
- `deploy/formal_runtime_pkg_v0_1/Dockerfile`
- `deploy/formal_runtime_pkg_v0_1/docker-compose.yml`
- `deploy/formal_runtime_pkg_v0_1/systemd/taiji-formal-runtime-pkg-v0-1.service`
- `deploy/formal_runtime_pkg_v0_1/scripts/preflight_v0_1.sh`
- `deploy/formal_runtime_pkg_v0_1/scripts/start_v0_1.sh`
- `deploy/formal_runtime_pkg_v0_1/scripts/health_v0_1.sh`
- `deploy/formal_runtime_pkg_v0_1/scripts/stop_v0_1.sh`
- `deploy/formal_runtime_pkg_v0_1/scripts/rollback_v0_1.sh`
- `deploy/formal_runtime_pkg_v0_1/scripts/hash_manifest_v0_1.sh`
- `deploy/formal_runtime_pkg_v0_1/MANIFEST.md`

## Runtime Contract

- Uses Python standard library HTTP server.
- Attempts to import `services.gateway.policies.formal_tensor_validator`.
- Falls back to fail-closed validation when validator import or invocation fails.
- Provides `GET /health`.
- Provides `POST /tensor/validate`.
- Provides `POST /tensor/route`.
- Binds to `127.0.0.1` by default.
- Does not auto-start production services.
- Does not include secrets.

## Fail-Closed Rules

- `payment_allowed=true` is blocked.
- `plaintext_context_stored=true` is blocked.
- missing `tau` is blocked.
- `replay_safe=false` routes to deadbox.
- payment/refund/discount/manager override/credential/live deploy intents are blocked.

## Local Commands

Preflight:

```bash
bash deploy/formal_runtime_pkg_v0_1/scripts/preflight_v0_1.sh
```

Start:

```bash
bash deploy/formal_runtime_pkg_v0_1/scripts/start_v0_1.sh
```

Health:

```bash
bash deploy/formal_runtime_pkg_v0_1/scripts/health_v0_1.sh
```

Stop:

```bash
bash deploy/formal_runtime_pkg_v0_1/scripts/stop_v0_1.sh
```

Rollback only this package:

```bash
bash deploy/formal_runtime_pkg_v0_1/scripts/rollback_v0_1.sh
```

Generate hashes:

```bash
bash deploy/formal_runtime_pkg_v0_1/scripts/hash_manifest_v0_1.sh
```

Docker:

```bash
docker compose -f deploy/formal_runtime_pkg_v0_1/docker-compose.yml up -d --build
```

systemd:

```bash
sudo cp deploy/formal_runtime_pkg_v0_1/systemd/taiji-formal-runtime-pkg-v0-1.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable taiji-formal-runtime-pkg-v0-1.service
sudo systemctl start taiji-formal-runtime-pkg-v0-1.service
```

## SHA256

Run:

```bash
bash deploy/formal_runtime_pkg_v0_1/scripts/hash_manifest_v0_1.sh
```

This session's shell execution is unavailable, so hashes must be generated locally by the script above.
