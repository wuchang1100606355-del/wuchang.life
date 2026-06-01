# Taiji Runtime Deployment Artifact Generation Report

Date: 2026-05-11
Mode: deployment-artifact-generation-only
Execution boundary: files generated only; no live start, no SSH, no SCP, no service restart, no docker compose execution

## Generated Artifact Scope

The deployment artifact layer was generated under `deploy/`:

- Docker runtime assets
- systemd unit files
- local runtime scripts
- runtime environment examples
- executable Python runtime entrypoint
- pytest coverage for the runtime entrypoint

## Runtime Services

The generated Docker compose model includes:

- taiji_gateway
- tensor_validator
- replay_runtime
- deadbox_runtime
- audit_runtime
- continuity_cache
- voice_runtime
- browser_runtime

## Runtime Endpoints

The entrypoint provides:

- `GET /health`
- `POST /tensor/validate`
- `POST /tensor/route`

## Binding Rule

Default binding remains:

```text
127.0.0.1
```

Unrestricted `0.0.0.0` bind is refused by `runtime_entry.py`.

External access must be provided only through:

- Taiji Gateway
- trusted tunnel
- governed reverse proxy

## Secret Boundary

No API key, OAuth token, service account JSON, private key, password, or cookie is embedded.

Environment files contain only examples and secret-boundary declarations.

## Execution Status

No live runtime start was executed in this generation pass.

The Codex exec launcher in this session is still unavailable, so no local command result is claimed here.

## Required Local Verification

Run locally when the execution launcher is available:

```bash
python3 -m json.tool schemas/formal_tensor_packet.schema.json
python3 -m py_compile services/gateway/policies/formal_tensor_validator.py
python3 -m py_compile deploy/runtime/runtime_entry.py
PYTHONPATH=. pytest -q tests/test_formal_tensor_validator.py tests/test_runtime_entry.py
bash deploy/scripts/preflight_check.sh
```

## Safe Start Commands

Local script mode:

```bash
bash deploy/scripts/bootstrap_runtime.sh
bash deploy/scripts/start_runtime.sh
bash deploy/scripts/runtime_status.sh
```

Docker mode:

```bash
docker compose -f deploy/docker/docker-compose.runtime.yml --env-file deploy/docker/.env.runtime.example up -d --build
```

systemd mode:

```bash
sudo cp deploy/systemd/taiji-runtime.service /etc/systemd/system/
sudo cp deploy/systemd/taiji-gateway.service /etc/systemd/system/
sudo cp deploy/systemd/taiji-audit.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable taiji-runtime.service taiji-gateway.service taiji-audit.service
sudo systemctl start taiji-runtime.service taiji-gateway.service taiji-audit.service
```

## Rollback Commands

Local script mode:

```bash
bash deploy/scripts/stop_runtime.sh
```

Docker mode:

```bash
docker compose -f deploy/docker/docker-compose.runtime.yml down
```

systemd mode:

```bash
sudo systemctl stop taiji-runtime.service taiji-gateway.service taiji-audit.service
sudo systemctl disable taiji-runtime.service taiji-gateway.service taiji-audit.service
```

## Risk Rating

| Area | Rating | Reason |
|---|---|---|
| Artifact generation | L1_near | Local files only; reviewable and rollbackable. |
| Runtime exposure | L1_near | Default localhost bind; external access requires governed ingress. |
| Live deployment | L0_exact_match | Not executed in this pass. |
| Secret exposure | L0_exact_match | No secret material embedded or printed. |
| Verification | L2_drift | Local exec unavailable in this session; user-side pytest result is separately acknowledged. |

