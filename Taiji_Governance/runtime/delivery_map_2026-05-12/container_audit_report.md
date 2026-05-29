# Container Audit Report

本報告只使用容器 metadata，不讀取 env 值、不進入容器、不刪除容器、不停止服務。

## Running Containers

| Container | Image | Ports | Risk | Notes |
| --- | --- | --- | --- | --- |
| `taiji_syslog` | `alpine:latest` | internal | L1 | governance syslog holder |
| `taiji_worklist` | `alpine:latest` | internal | L1 | governance worklist holder |
| `taiji_audit` | `alpine:latest` | internal | L1 | audit holder |
| `taiji_progress` | `alpine:latest` | internal | L1 | progress holder |
| `wuchang_os_odoo_18` | `odoo:18.0` | `127.0.0.1:8069` | L2 | Odoo 主場景；需確認 dbfilter/no database manager 與 secret boundary |
| `wuchang_os_pg` | `postgres:15` | internal `5432` | L2 | Odoo DB；volume 不可破壞 |
| `taiji_voice_gateway` | `taiji_voice_gateway:local` | `127.0.0.1:9201` | L1/L2 | voice gateway local bind |
| `taiji_device_resilience_adapter` | local image | no published host port in ps output | L1/L2 | device adapter |
| `taiji_pos_google_voice_tool` | local image | no published host port in ps output | L2 | 主權 AI 商業用 POS 語音工具 |
| `taiji_claw_safe` | local image | `127.0.0.1:9004` | L1/L2 | local claw safe runtime |
| `open-webui` | `ghcr.io/open-webui/open-webui:main` | `0.0.0.0:3000` | L2/L3 | 必須證明只在可信 VPN/Gateway/防火牆邊界內 |
| `wuchang_gpu_brain` | `ollama/ollama:latest` | internal `11434` | L1/L2 | local model backend |

## Compose Projects

| Project | Status | Config |
| --- | --- | --- |
| `taiji_claw_safe` | running | `Taiji_Claw_Safe/docker-compose.yml` |
| `taiji_device_resilience_adapter` | running | `Taiji_Device_Resilience_Adapter/docker-compose.yml` |
| `taiji_governance` | running | `Taiji_Governance/docker-compose.yml` |
| `taiji_odoo` | running | `Taiji_Odoo/docker-compose.yml` |
| `taiji_pos_google_voice_tool` | running | `Taiji_POS_Google_Voice_Tool/docker-compose.yml` |

## Optimization Plan

1. Keep all running containers untouched until owner confirms a maintenance window.
2. Treat `0.0.0.0:3000` as L2/L3 until firewall/VPN/Gateway proof is recorded.
3. Move any password-like runtime configuration away from process args / compose plaintext before production.
4. Add healthcheck metadata to containers that do not expose a health status.
5. Do not delete stopped containers, images, or volumes without explicit confirmation and backup.

