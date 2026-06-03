# W7TP Container Server Offload Plan-Only

Scope: Wuchang Smart Cloud / XiaoJ / W7TP / VPN Device Cooperative Runtime

Status: plan-only  
Mode: no SSH / no container move / no restart / no data copy / no secret transfer

## Purpose

This document defines which containers should remain on the MSI local control node and which workloads should be offloaded to a pure Linux server or VPN worker node.

## Core Principle

Local MSI remains the control console, final authority, secret boundary, and attended boost node.

Pure Linux server nodes handle low-risk background workloads, scheduled one-shot jobs, report generation, indexing, validation, and long scans.

## Container Classes

### local_control

Remain on MSI:

- local authority tools
- secret-bound tools
- local inventory
- manual approval gates
- router / Merlin checklist
- final git commit authority
- short GPU boost tests

### server_preferred

Move to pure Linux server or VPN worker:

- one-shot indexer
- readonly probe
- service health check
- runtime report/proof aggregation
- task card generation
- dashboard generation
- schema validation
- long grep / scan

### always_on_server

Can run as daemon if stable:

- Odoo staging
- Postgres staging
- gateway staging
- report API
- worker queue receiver

### never_remote

Never move to server worker:

- private keys
- tokens
- password files
- router credentials
- local redacted inventory
- raw member PII
- formal production database write authority
- final git commit
- router write actions

## Current Critical Finding

`wuchang_os_indexer` was observed as:

- Cmd: `python -u watcher.py`
- ExitCode: `0`
- RestartPolicy: `unless-stopped`
- RestartCount: high
- Result: restart loop

Conclusion:

`wuchang_os_indexer` should be treated as a one-shot or scheduled job, not an always-on daemon, unless `watcher.py` is rewritten to be a true watcher.

Recommended policy:

```yaml
restart: "no"
mode: one_shot
target_host: pure_linux_server
Offload Rules

Worker containers must:

use minimal readonly mounts
receive signed or allowlisted job manifests
produce summary result and sha256 proof
avoid secrets and raw PII
avoid direct git commit
avoid router and SSH operations
avoid production DB writes
Forbidden Worker Mounts
/
/home/*/.ssh
.env
keys/
configs/merlin/router_inventory_redacted.local.json
Taiji_Odoo/postgres_data
raw member data directories
Result Contract

Each offloaded task should return:

summary JSON
markdown report
sha256 proof
resource usage
error summary if failed

