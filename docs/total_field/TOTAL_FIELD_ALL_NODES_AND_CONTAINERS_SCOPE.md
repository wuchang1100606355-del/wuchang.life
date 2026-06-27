# Total Field All Nodes And Containers Scope

RUN_ID=D8_MANDATORY_TASK_20260624_082542_TOTAL_FIELD_ALL_NODES_AND_CONTAINERS_SCOPE_EXPANSION
STATE=TOTAL_FIELD_SCOPE_EXPANDED_TO_ALL_NODES_AND_CONTAINERS
ROOT=/home/taiji_admin/Taiji_Hub

## Human Direction

From this point, the Total Field scope is not limited to the local repo or local D8 database. It must cover all known nodes and containers as governance subjects.

This is a scope expansion, not an automatic operation grant.

```text
Total Field may observe, index, classify, route, warn, and seal all nodes and containers.
Total Field may not mutate, restart, deploy, inspect secrets, or write production state without a separate approved packet.
```

## Canonical Interpretation

The existing all-node architecture already states:

- `total_field = ALL_NODES`
- `field_scope = ALL_8_DIMENSIONS`
- node policy is macro-governed by path/ref/hash/report only
- no direct OS authority is assumed

This packet extends that same rule to containers.

## Scope Classes

| Class | Examples | Total Field Authority | Runtime Authority |
| --- | --- | --- | --- |
| Local governance node | `taiji01`, D8 local DB, repo runtime reports | Observe, index, seal, warn | Only via preflight and task capsule |
| Odoo/POS node | `wuchang_os_odoo_18`, POS UI, cafe POS | Observe routes/status; no member plaintext | Write/upgrade/restart only with explicit human release |
| Database node | `taiji_d8_db`, `wuchang_os_pg`, quarantined Postgres | D8 local DB writes allowed only for governance; production DB read/write forbidden unless authorized | No production mutation by default |
| Router/network node | ASUS router, LAN/VPN/DNS boundary | Boundary metadata and policy only | No router write/reboot/DNS mutation without human release |
| AI/model node | Ollama/local model, cloud candidate brain, AI gateway | Candidate routing and capability registry | No external API/embedding without authorization |
| Device/display node | SUNMI POS, customer display, browser kiosk, QR desk display | Device identity, health, display candidates | No direct device control without approval |
| Voice/audio node | local TTS, voice adapter, browser speech synthesis | Text/audio capability refs | No raw audio retention |
| Cloud node | Google/LINE/OAuth/cloud compute candidates | Opaque ref and public/status metadata only | No token/API/config secret read |
| Storage/vault node | local vault, association future machine, backups | ref/hash/manifest only | No member plaintext export |
| Quarantine node | incident quarantine, redteam evidence | reverse-index only | Non-executable; no normal context pollution |

## Current Container Observation

Observed by read-only `docker ps`:

| Container | Image | Status | Ports | Scope |
| --- | --- | --- | --- | --- |
| `taiji_d8_db` | `pgvector/pgvector:pg16` | Up, healthy | `0.0.0.0:15432->5432/tcp` | D8 governance DB |
| `wuchang_os_odoo_18` | `odoo:18.0` | Up | `127.0.0.1:8069->8069/tcp`, internal `8071-8072/tcp` | Odoo/POS runtime |
| `wuchang_os_pg` | `postgres:15` | Up | internal `5432/tcp` | Odoo Postgres |
| `quarantine_wuchang_os_pg_20260508_200520` | `postgres:15` | Up | internal `5432/tcp` | quarantined DB container |

Observed by read-only socket listing:

- Odoo local port `127.0.0.1:8069`
- D8 DB exposed on `0.0.0.0:15432`
- local model endpoint likely on `*:11434`
- other host ports exist and require classification before any public exposure claim

No `docker inspect`, env dump, secret read, restart, compose action, or container mutation was performed.

## Governance Rule

Every node/container action must be represented as:

```text
State -> Coordinate -> Hash -> Packet -> Generative Transfer -> Verify -> Reconstruct -> Evidence -> Action
```

For all nodes and containers, Total Field must first answer:

1. What node/container is involved?
2. What authority does this task claim?
3. Is the task observation, proposal, write, restart, deploy, payment, member, secret, or production?
4. What is the narrowest non-sensitive evidence needed?
5. Which preflight gate applies?
6. What stopline would block the action?

## Allowed By Default

- list container names/status/ports
- list local listening sockets
- read existing non-secret reports/seals
- read public/non-sensitive docs
- create governance reports/seals
- create node/container manifests that do not include secrets
- D8 local governance DB write through approved D8 tools

## Forbidden By Default

- `docker inspect` environment dumps
- reading `.env*`
- reading Odoo config secrets
- reading quarantine originals
- reading member plaintext
- restarting containers
- docker compose up/down
- module upgrade
- production DB write
- POS order creation
- payment capture
- router write/reboot/DNS mutation
- cloud API/token use
- embedding generation
- deploy or production release

## Node/Container Risk Levels

| Level | Meaning | Examples | Required Gate |
| --- | --- | --- | --- |
| L0 | docs/report only | scope packet, manifest, seal | D8 preflight |
| L1 | read-only status | `docker ps`, `ss`, `curl -I`, public docs | D8 preflight |
| L2 | sensitive-adjacent observation | Odoo shell, DB read, router read, domain probe | explicit scoped task and no-secret guard |
| L3 | mutation/runtime | restart, upgrade, DB write, router write, deploy | explicit human release |
| BLOCK | sensitive exposure | secret output, member plaintext, payment capture without authorization | stop immediately |

## Implication For XiaoJ Product

The XiaoJ AV ordering product may use all nodes and containers as a governed field:

- local model for intent and personality
- cloud compute for candidate-only work
- Odoo/POS container as embodiment
- D8 DB as governance memory
- router as network boundary
- LINE/Google auth as channel nodes
- display/POS devices as presentation nodes
- future association machine as long-term governance/vault node

But XiaoJ must not collapse those into one unsafe authority. The Total Field sees the whole field; each node keeps its own permission boundary.

## Next Required Work

Before runtime landing:

1. Create a non-secret node/container manifest.
2. Classify each exposed port as local-only, LAN, VPN, public, or unknown.
3. Bind each node/container to role, owner, risk, and allowed actions.
4. Add guard checks for container mutation attempts.
5. Extend the XiaoJ auth/ordering LAND packet to include node/container route awareness.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
D8_LOCAL_DB_WRITE=TRUE
PRODUCTION_DB_WRITE=FALSE
ODOO_DB_WRITE=FALSE
ODOO_MODULE_UPGRADE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
CONTAINER_MUTATION=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
ODOO_FILES_TOUCHED=FALSE
LINE_LOGIN_FILES_TOUCHED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE
