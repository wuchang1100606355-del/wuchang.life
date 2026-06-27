# Total Field Node Container Manifest And Risk Matrix

RUN_ID=D8_MANDATORY_TASK_20260624_082807_TOTAL_FIELD_NODE_CONTAINER_MANIFEST_AND_XIAOJ_ROUTE_GATE
STATE=NODE_CONTAINER_MANIFEST_AND_RISK_MATRIX_READY
ROOT=/home/taiji_admin/Taiji_Hub

## Purpose

This document turns the expanded Total Field scope into a concrete non-secret manifest and risk matrix for XiaoJ AV ordering, LINE/Google registration, local brain, cloud candidate compute, Odoo/POS, devices, router, and containers.

It is an observation and routing artifact only. It does not grant runtime authority.

## Current Verified Base

| Evidence | Result |
| --- | --- |
| D8 mandatory workflow | PASS |
| Total Field console | PASS |
| D8 memory | 4741 records |
| Active all-node canonical | `ALL_NODES`, `ALL_8_DIMENSIONS`, no direct OS authority assumption |
| All-node/container scope seal | `TOTAL_FIELD_SCOPE_EXPANDED_TO_ALL_NODES_AND_CONTAINERS` |
| Odoo native signup | `/web/signup` previously verified HTTP 200 on `127.0.0.1:8069` |
| LINE/Google auth | runtime routes previously observed as HTTP 404; not launch-ready |
| XiaoJ ordering route | `/wuchang/xiaoj/ordering` previously observed as HTTP 303 to login |

## Observed Docker Containers

| Node Ref | Container | Image | Observed Status | Port Exposure | Total Field Role | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| `node.container.d8_db` | `taiji_d8_db` | `pgvector/pgvector:pg16` | Up, healthy | `0.0.0.0:15432->5432/tcp` | D8 governance memory | L2, because DB port is externally bound |
| `node.container.odoo` | `wuchang_os_odoo_18` | `odoo:18.0` | Up | `127.0.0.1:8069->8069/tcp` | Odoo/POS embodiment | L2 for read; L3 for write/upgrade/restart |
| `node.container.odoo_pg` | `wuchang_os_pg` | `postgres:15` | Up | internal `5432/tcp` | Odoo database | L3 by default; no production DB write |
| `node.container.quarantine_pg` | `quarantine_wuchang_os_pg_20260508_200520` | `postgres:15` | Up | internal `5432/tcp` | quarantine evidence container | BLOCK if used as normal context |

## Observed Host Ports

| Port | Bind | Observed Process Hint | Classification | Required Next Step |
| --- | --- | --- | --- | --- |
| 8069 | `127.0.0.1` | Odoo container proxy | Odoo local runtime | Keep local unless domain/reverse-proxy task is approved |
| 15432 | `0.0.0.0` and IPv6 | D8 DB container | D8 DB exposed | Classify firewall/VPN boundary before public claim |
| 11434 | `*` | likely Ollama/local model | local model node | Bind into XiaoJ local brain manifest |
| 9002 | `0.0.0.0` | Python gateway | AI gateway candidate node | Verify LAN/VPN allowlist before use |
| 9199 | `0.0.0.0` | Python HTTP server | runtime static/demo node | classify owner and expected purpose |
| 9200 | `0.0.0.0` | Python HTTP server | runtime static/demo node | classify owner and expected purpose |
| 8000 | `0.0.0.0` | Python HTTP server | unknown app node | classify before use |
| 8105 | `0.0.0.0` | unknown | unknown node | classify before use |
| 8088 | `0.0.0.0` | unknown | unknown node | classify before use |
| 18069 | `0.0.0.0` | Python HTTP server | possible Odoo/proxy mirror | classify before use |
| 8080 | `*` | unknown | unknown node | classify before use |
| 22 | `0.0.0.0` and IPv6 | SSH | host access | L3 for mutation; read-only status only |
| 2377, 7946 | `*` | Docker swarm-related | container orchestration boundary | L3 for mutation |
| 445, 139 | `0.0.0.0` and IPv6 | SMB | file sharing boundary | classify data exposure |
| 53 | `0.0.0.0` and IPv6 | DNS | network service | router/DNS boundary classification |
| 3389 | `*` | remote desktop | remote access boundary | L3 for remote operation |
| 5201 | `*` | iperf-like test port | performance/test node | close/classify after test purpose known |

## Product Route Nodes

| Product Node | Current Evidence | Desired Role | Risk Gate |
| --- | --- | --- | --- |
| XiaoJ front brain | local router exists, front model not detected | lively operator/personality layer | L1 until model route mutation |
| XiaoJ engineering sensory brain | `metric-language-gateway-ai:latest` detected previously | routing, packet, hazard, sensory bundle | L1 for local inference status |
| Odoo native signup | `/web/signup` HTTP 200 | fallback registration | L1 read; L3 config/write |
| LINE auth | `/line/login` and `/line/callback` previously 404 | member/channel login | L3 until addon route activation authorized |
| Google auth | `/google/member/login` and welcome previously 404 | member/channel login | L3 until addon route activation authorized |
| XiaoJ ordering UI | `/wuchang/xiaoj/ordering` redirects to login | staff/customer AV ordering shell | L2 read; L3 module upgrade/restart |
| Real menu source | QuickClick screenshot contradicts local CSV in prior seal | menu truth source | HOLD until source locked |
| Loyalty/retention | designed but not implemented | customer stickiness | L2 design; L3 if writing coupons/member data |

## Risk Matrix For Next XiaoJ LAND

| Work Item | Node/Container | Allowed First Action | Forbidden Without Release | Pass Evidence |
| --- | --- | --- | --- | --- |
| Auth route fix | Odoo addon nodes | read code, patch in allowed paths after LAND | module upgrade/restart, OAuth secret read | `/line/login`, `/google/member/login` non-404 or controlled HOLD |
| XiaoJ UI shell | Odoo route/static assets | patch UI shell after LAND | POS write, payment, member plaintext | authenticated page renders product shell |
| Local brain | Ollama/local model | route manifest, local model availability check | external API, embedding | front and sensory models selected or HOLD |
| Cloud candidate brain | cloud node | config refs only | token read/API call | candidate adapter manifest only |
| Real menu | QuickClick/Odoo sources | source manifest/hash | invent menu, write POS | source lock report |
| Staff confirmation | Odoo/POS UI | candidate-only dry-run | POS order/payment | dry-run verifier output |
| Loyalty loop | Odoo/LINE/Google | opaque ref schema | member plaintext, auto coupons | retention metric schema |
| Container route awareness | all containers | manifest/risk check | restart/inspect env/compose mutation | guard blocks mutation attempts |

## Required Guard Additions

Before runtime landing, add or verify guard checks for:

- container mutation attempts
- exposed port without classification
- LINE/Google route claim while 404
- OAuth config/secret read attempt
- member plaintext read attempt
- menu source missing
- direct POS order creation
- payment capture
- Odoo module upgrade/restart without explicit release
- cloud API or embedding use without release

## Next LAND Packet Name

```text
XIAOJ_AV_ORDERING_AUTH_AND_STICKINESS_LAND_P1
```

Recommended release scope:

- allow specific Odoo addon paths only after human confirmation
- keep OAuth secrets unread and unprinted
- allow code patch but hold before module upgrade/restart unless explicitly released
- verify non-404 auth routes or controlled HOLD pages
- keep all product behavior candidate-only until staff confirmation gate

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
