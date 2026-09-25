# XiaoJ AV Ordering Developer Guide

STATE=DEVELOPER_GUIDE_READY_RUNTIME_HOLD

This guide is for developers and Total Field operators who continue XiaoJ AV
ordering, LINE/Google registration, local-brain operation, and cafe POS
integration.

The current product is source-ready for local rehearsal and field practicum.
It is not yet released for live Odoo/POS writes, live payment capture, or
production deployment.

## 1. Main Chain

All work must preserve:

```text
State → Coordinate → Hash → Packet → Generative Transfer → Verify → Reconstruct → Evidence → Action
```

Do not start by patching, restarting, deploying, or writing DB. First observe
the field, ask Total Field, then use the smallest safe path.

## 2. Current Verified Surface

| Surface | Evidence | State |
| --- | --- | --- |
| D8 Total Field DB | `tools/d8_total_field_console.sh status` | PASS |
| P1 console prototype | `scripts/verify/verify_xiaoj_p1_console_prototype.py` | PASS, runtime false |
| Local intent engine | `scripts/verify/verify_xiaoj_p1_intent_engine.py` | PASS |
| Staff voice grammar | `docs/operations/XIAOJ_STAFF_VOICE_POS_GRAMMAR_RULE.md` | PASS |
| Local voice rehearsal | `scripts/verify/verify_xiaoj_p1_local_rehearsal.py` | PASS |
| Field practicum dual-track | `scripts/verify/verify_xiaoj_field_practicum_dual_track.py` | PASS |

Known runtime holds:

| Gate | Meaning |
| --- | --- |
| `HOLD_AUTH_ROUTE_GATE` | LINE / Google / member runtime routes are not released |
| `HOLD_REAL_MENU_SOURCE_LOCK` | Real menu source and price authority are not locked |
| `HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED` | Live POS order creation not approved |
| `HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED` | Live payment capture not approved |

## 3. Component Map

| Component | Path | Role |
| --- | --- | --- |
| P1 console | `runtime/total_field/xiaoj_p1_console/index.html` | Static operator UI prototype |
| P1 console JS | `runtime/total_field/xiaoj_p1_console/app.js` | Candidate-only browser-side rehearsal |
| Local rehearsal CLI | `tools/xiaoj_p1_local_rehearsal.py` | Voice → order/payment/receipt candidate chain |
| Intent engine | `Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/p1_intent_engine.py` | Pure local service module |
| Source route shell | `Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py` | Odoo route source shell, not runtime released |
| Menu source lock | `runtime/total_field/xiaoj_p1_console/menu_source_lock.json` | Holds current menu-source authority state |
| Dual-track rule | `docs/operations/XIAOJ_FIELD_PRACTICUM_DUAL_TRACK_RULE.md` | Field practicum boundary |

## 4. Mandatory Preflight

Before edits, runtime actions, DB writes, report sealing, or handoff packages:

```bash
tools/d8_codex_mandatory_workflow.sh start \
  --task-name <TASK_NAME> \
  --mode review \
  --scope-json '<json>' \
  --allowed-paths-json '<json>' \
  --forbidden-paths-json '<json>' \
  --expected-output '<expected output>'
```

Decision policy:

| Decision | Meaning |
| --- | --- |
| PASS | May proceed in bounded scope |
| INFO | May proceed and record |
| WARN | Sandbox only unless human releases |
| HOLD | Stop and wait |
| BLOCK | Stop immediately |

## 5. Safe Development Loop

1. Observe field state:

```bash
pwd
git rev-parse HEAD
git status --short
tools/d8_total_field_console.sh status
tools/d8_total_field_console.sh alerts --limit 20
tools/d8_total_field_console.sh evals --limit 20
```

2. Run relevant verifiers:

```bash
python3 scripts/verify/verify_xiaoj_p1_intent_engine.py
python3 scripts/verify/verify_xiaoj_p1_console_prototype.py
python3 scripts/verify/verify_xiaoj_p1_local_rehearsal.py
python3 scripts/verify/verify_xiaoj_field_practicum_dual_track.py
```

3. Make only bounded source/docs changes.

4. Re-run verifiers.

5. Produce report and seal under:

```text
runtime/d8_db/reports/
runtime/total_field/status/
```

## 6. Local Voice Rehearsal Contract

Input:

```text
大冰少糖拿鐵
```

Required parse:

| Slot | Value |
| --- | --- |
| size | large |
| temperature | ice |
| sweetness | less_sugar |
| item | 拿鐵 |

Required chain:

```text
voice_payload → menu_source_resolution → order_candidate → payment_candidate → receipt_candidate
```

Required holds when source/runtime not released:

```text
HOLD_REAL_MENU_SOURCE_LOCK
HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED
HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED
HOLD_RUNTIME_POS_RECEIPT_REQUIRED
```

## 7. LINE / Google Registration Boundary

The goal requires LINE and Google registration/login to work, but the current
runtime verifier still reports route HOLD. Developers must not claim completion
until route evidence shows non-raw-404 behavior.

Runtime release requires:

- Odoo module release approval.
- Route verifier pass.
- No secret output.
- No member plaintext read.
- Controlled error pages for unavailable OAuth tokens.

Do not read `.env`, OAuth secrets, database passwords, or provider tokens in
ordinary development flow.

## 8. Menu Source Boundary

Real product data must come from locked source, not GPT text.

Release requirements:

- Live QuickClick export.
- Source hash per product row.
- Human review of conflicts.
- Explicit Odoo/POS menu write approval.
- Separate transaction release approval.

Until then, local rehearsal must keep:

```text
price_authority=false
live_orderable=false
```

## 9. Odoo/POS Runtime Boundary

Default:

```text
ODOO_DB_WRITE=FALSE
ODOO_MODULE_UPGRADE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
```

The following require explicit human authorization:

- Odoo restart.
- Odoo module upgrade.
- Odoo DB write.
- POS order creation.
- Payment capture.
- Production deploy.

If any occur, final report must truthfully set the flags to TRUE.

## 10. Developer Do / Do Not

Do:

- Keep redteam evidence non-executable.
- Use verifier-first work.
- Keep Track A and Track B separate.
- Preserve Vietnamese manager labels.
- Preserve `尺寸 → 溫度 → 甜度 → 品項`.
- Write reports and seals.

Do not:

- Read `.env*`.
- Read quarantine originals.
- Read member plaintext.
- Invent menu items.
- Create 三明治 or 蛋餅 unless real source says so.
- Pretend rehearsal is live order.
- Trigger external APIs without release.
- Generate embeddings without release.
- Restart services without release.

## 11. Suggested Next LAND Packet

When human releases runtime-source work, use a packet that only targets:

```text
XIAOJ_AV_ORDERING_AUTH_AND_STICKINESS_LAND_P1
```

It should allow exactly the needed route/UI source edits and still HOLD before:

- Odoo module upgrade.
- Odoo restart.
- Odoo DB write.
- POS order creation.
- Payment capture.
- Secret/OAuth token read.
- Member plaintext read.

## 12. Safety Flags

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
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
EXECUTABLE_REDTEAM_ARTIFACTS=FALSE
POLLUTION_GUARD=TRUE
REVERSE_INDEX_ISOLATION=TRUE
DO_NOT_TOUCH_AGENTS_MD=TRUE
