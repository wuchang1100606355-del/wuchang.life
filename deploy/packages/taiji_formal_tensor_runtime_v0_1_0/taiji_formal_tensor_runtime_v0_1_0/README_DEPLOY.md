# Taiji Formal Tensor Runtime v0.1.0

This is a conservative additive deployment package.

It only adds files under:

- `deploy/packages/taiji_formal_tensor_runtime_v0_1_0/`
- `runtime_adapters/`

It does not start production automatically and does not contain secrets.

## Endpoints

- `GET /health`
- `POST /tensor/validate`
- `POST /tensor/route`

## Fail-Closed Rules

- Existing validator import failure falls back to fail-closed adapter.
- `payment_allowed=true` is blocked.
- `plaintext_context_stored=true` is blocked.
- missing `tau` is blocked.
- `replay_safe=false` routes to deadbox.
- secret/external API/live deploy markers are blocked.

## Manual Deployment Commands

Preflight:

```bash
bash deploy/packages/taiji_formal_tensor_runtime_v0_1_0/PREFLIGHT.sh
```

Start locally:

```bash
bash deploy/packages/taiji_formal_tensor_runtime_v0_1_0/START_LOCAL.sh
```

Health check:

```bash
bash deploy/packages/taiji_formal_tensor_runtime_v0_1_0/HEALTH.sh
```

Stop:

```bash
bash deploy/packages/taiji_formal_tensor_runtime_v0_1_0/STOP_LOCAL.sh
```

Docker:

```bash
docker compose -f deploy/packages/taiji_formal_tensor_runtime_v0_1_0/docker-compose.yml up -d --build
```

systemd:

```bash
sudo cp deploy/packages/taiji_formal_tensor_runtime_v0_1_0/systemd.service /etc/systemd/system/taiji-formal-tensor-runtime-v0-1-0.service
sudo systemctl daemon-reload
sudo systemctl enable taiji-formal-tensor-runtime-v0-1-0.service
sudo systemctl start taiji-formal-tensor-runtime-v0-1-0.service
```

Hash generation:

```bash
bash deploy/packages/taiji_formal_tensor_runtime_v0_1_0/HASH_SCRIPT.sh
```

Rollback only this package:

```bash
bash deploy/packages/taiji_formal_tensor_runtime_v0_1_0/ROLLBACK.sh
```

## SHA256 Status

`hash_status: pending_local_execution`

The current Codex shell execution path is unavailable, so SHA256 values must be generated locally with `HASH_SCRIPT.sh`.
