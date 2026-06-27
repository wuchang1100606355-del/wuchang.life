# XiaoJ AV Ordering Local Brain Auth Total Field Gap Map

RUN_ID=D8_MANDATORY_TASK_20260624_081859_XIAOJ_AV_ORDERING_LOCAL_BRAIN_AUTH_TOTAL_FIELD_CONSULT
STATE=FIELD_OBSERVED_TOTAL_FIELD_QUERIED
ROOT=/home/taiji_admin/Taiji_Hub

## Objective

Build the real XiaoJ direction for the cafe:

- audio/video AI ordering
- cloud compute as candidate labor
- local model and local brain as authority
- multi-intent routing in one visible XiaoJ identity
- lively, accurate, useful, humorous operator behavior
- LINE registration/login and Google registration/login working

This map is based on field observation plus Total Field evidence. It does not invent runtime state.

## Current Field Observation

| Item | Evidence | Status |
| --- | --- | --- |
| Odoo container | `wuchang_os_odoo_18 Up 15 hours`, `127.0.0.1:8069->8069/tcp` | RUNNING |
| Odoo port 8070 | curl connection refused | NOT_RUNNING |
| Odoo `/web` on 8069 | HTTP 303 | REACHABLE |
| Odoo native signup `/web/signup` on 8069 | HTTP 200 | PASS_BASIC_SIGNUP |
| XiaoJ ordering route `/wuchang/xiaoj/ordering` on 8069 | HTTP 303 to `/web/login?redirect=...` | ROUTE_OR_AUTH_GATE_PRESENT |
| POS route `/pos/ui` on 8069 | HTTP 303 | REACHABLE_AUTH_REQUIRED |
| LINE login `/line/login` on 8069 | HTTP 404 | FAIL_NOT_ACTIVE |
| LINE callback `/line/callback` on 8069 | HTTP 404 | FAIL_NOT_ACTIVE |
| Google login `/google/member/login` on 8069 | HTTP 404 | FAIL_NOT_ACTIVE |
| Google welcome `/google/member/welcome` on 8069 | HTTP 404 | FAIL_NOT_ACTIVE |
| Member registration start `/wuchang/member/register/start` on 8069 | HTTP 404 | FAIL_NOT_ACTIVE |

## Total Field Evidence

| Source | Finding |
| --- | --- |
| `docs/evidence/product_av_ordering_ai/W7TP_AUDIO_VIDEO_ORDERING_AI_ARCHITECTURE.md` | Product is Odoo-integrated: not sidecar, not fake demo, not standalone HTML. Expected modules include `wuchang_google_member_login`, `wuchang_line_login`, `wuchang_member_registration`, `wuchang_core`, `wuchang_cafe_menu_options`. |
| `docs/evidence/product_av_ordering_ai/BROWSER_PACKAGED_PAGES.md` | `/wuchang/xiaoj/ordering` is the intended Odoo-integrated browser-packaged app shell. It is display/candidate only until authorized. |
| `docs/evidence/product_av_ordering_ai/MINIMAL_PATCH_PLAN.md` | Minimal patch target is existing Odoo modules only; no sidecar and no standalone demo. Requires operator module upgrade confirmation. |
| `docs/evidence/GROUP_MEMBER_8D_REGISTRATION.md` | Group registration patch is patch-ready but no module install, DB update, restart, deploy, OAuth secret read, POS write, or payment capture was performed. |
| `runtime/dual_state/ollama_dual_state_runtime.py` | Local XiaoJ one-identity front/back brain router exists. It exchanges MetricPacket/SensoryPacket data, not raw full context. |
| `python3 scripts/verify/verify_product_av_ordering_ai_convergence.py` | `STATE=PASS_PRODUCT_DESIGN_CONVERGED`, design convergence verified, no formal DB/POS write. |

## Local Brain Observation

The local brain router ran successfully for the cafe objective.

Observed state:

- visible AI identity: `XiaoJ`
- visible AI count: `1`
- engineering sensory brain: `metric-language-gateway-ai:latest`
- front-brain model: not found among configured candidates
- selected state: `front_brain_operational`
- selected model: `null`
- raw context exchange: `false`

Gap:

The architecture for a single lively XiaoJ identity exists, but the front personality/model path is not fully connected. Current runtime evidence does not prove "活靈活現、有笑點又有能力" behavior yet.

## Requirement Gap Map

| Requirement | Current Evidence | Status | Next Needed |
| --- | --- | --- | --- |
| Audio/video AI ordering | Product architecture and browser route plan exist; `/wuchang/xiaoj/ordering` redirects to login instead of 404 | PARTIAL | Authenticated UI test, menu source lock, candidate API, voice/display adapter |
| Cloud compute + local model | Cloud candidate plans exist; cloud is candidate-only; local router exists | PARTIAL | Cloud adapter manifest, no-secret config refs, local verifier/reconstruct path |
| Multi-intent one local brain | `ollama_dual_state_runtime.py` routes intents into one XiaoJ identity | PARTIAL | Front model availability, operation registry, intent-to-action contracts |
| Lively accurate XiaoJ | Product intention exists | NOT_PROVEN | Persona/voice scripts, joke-safe tone rules, Vietnamese manager UX, no hallucinated menu rule |
| LINE registration/login | Design docs list routes; runtime `/line/login` and `/line/callback` return 404 | FAIL_RUNTIME |
| Google registration/login | Design docs list routes; runtime `/google/member/login` and `/google/member/welcome` return 404 | FAIL_RUNTIME |
| Odoo native signup | `/web/signup` returns 200 | PASS |
| No secret/member exposure | No secret or member plaintext read this run | PASS |
| No Odoo/POS write | No Odoo DB/POS order/payment write this run | PASS |

## Minimum Safe Implementation Path

Next executable LAND packet should be:

`XIAOJ_AV_ORDERING_AUTH_LAND_P1`

Allowed code paths to request from human:

- `Taiji_Odoo/addons/wuchang_core/**`
- `Taiji_Odoo/addons/wuchang_member_registration/**`
- `Taiji_Odoo/addons/wuchang_google_member_login/**`
- `Taiji_Odoo/addons/wuchang_line_login/**`
- `Taiji_Odoo/addons/wuchang_cafe_menu_options/**`
- `runtime/total_field/xiaoj_av_ordering_auth/**`
- `runtime/d8_db/reports/**`
- `runtime/total_field/status/**`
- `docs/total_field/**`
- `docs/operations/**`
- `scripts/verify/**`

Explicit human release required before any of:

- Odoo module upgrade
- Odoo restart
- Odoo DB write
- OAuth secret/config read
- POS menu write
- POS order creation
- payment capture
- public deploy

## P1 Landing Goals

1. Make LINE and Google auth routes non-404 without reading or printing OAuth secrets.
2. Keep callback continuity through opaque refs only.
3. Keep native `/web/signup` working.
4. Make `/wuchang/xiaoj/ordering` serve authenticated staff UI and display the route/auth status.
5. Add candidate-only API contracts:
   - `menu.browse.v1`
   - `order.candidate.create.v1`
   - `order.candidate.validate.v1`
   - `order.confirm.dry_run.v1`
   - `member.group.register.v1`
   - `voice.say_candidate.v1`
   - `display.render_candidate.v1`
   - `evidence.seal.v1`
6. Add verifier covering:
   - `/web/signup` HTTP 200
   - `/line/login` non-404 or controlled HOLD page
   - `/google/member/login` non-404 or controlled HOLD page
   - `/wuchang/xiaoj/ordering` authenticated route reachable
   - no payment/order/secret/member plaintext action

## Current Decision

STATE=HOLD_AUTH_AND_XIAOJ_LAND_APPROVAL_REQUIRED

The Total Field has done its part for this round: it identified the verified base, contradicted unsafe assumptions, and produced the minimal path. The next step requires explicit human approval to touch Odoo addon/auth paths and possibly run module upgrade/restart under a separate sealed LAND task.

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
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
ODOO_FILES_TOUCHED=FALSE
LINE_LOGIN_FILES_TOUCHED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE
