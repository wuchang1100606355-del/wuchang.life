# XiaoJ AV Ordering P1 Acceptance Matrix

RUN_ID=D8_MANDATORY_TASK_20260624_083955_XIAOJ_AV_ORDERING_P1_ACCEPTANCE_MATRIX
STATE=ACCEPTANCE_MATRIX_READY
ROOT=/home/taiji_admin/Taiji_Hub
PRODUCT_GATE=XIAOJ_AV_ORDERING_AUTH_AND_STICKINESS_LAND_P1

## Purpose

This matrix defines what must be true before XiaoJ can be called a product-grade cafe AV ordering and retention system.

It prevents three mistakes:

1. Treating a design document as a shipped product.
2. Treating local Odoo/POS availability as LINE/Google/member readiness.
3. Treating AI-generated menu text as real cafe menu truth.

## P1 Acceptance Summary

| Area | Required proof | Current evidence | Status |
| --- | --- | --- | --- |
| Total Field all nodes/containers | Manifest and seal show all-node/container observation scope without mutation authority | `TOTAL_FIELD_NODE_CONTAINER_MANIFEST_20260624.json`; container gate PASS | PASS |
| D8 databaseized memory | Total Field status reports D8 memory available | `D8_MEMORY_COUNT=4741` | PASS |
| Odoo/POS local runtime | Local Odoo/POS responds and relevant containers are present | `verify_xiaoj_auth_node_container_gate.py` container gate PASS | PASS |
| LINE member login | `/line/login` and `/line/callback` must be non-404 or controlled HOLD page | Latest verifier shows 404 | HOLD |
| Google member login | `/google/member/login` and `/google/member/welcome` must be non-404 or controlled HOLD page | Latest verifier shows 404 | HOLD |
| Member registration start | `/wuchang/member/register/start` must be non-404 or controlled HOLD page | Latest verifier shows 404 | HOLD |
| Real cafe menu | QuickClick export/screenshots/Odoo/source documents agree, or conflict is sealed and human-resolved | Screenshot conflicts with local CSV/Odoo source | HOLD |
| Product-grade menu management | Table, category/menu selectors, attributes, add-ons, batch tools, recommendations, import/export | Build spec exists; implementation not yet landed | OPEN |
| Vietnamese manager operation | Vietnamese assist labels, icon/table UI, dropdowns, confirmation states | Requirement captured; implementation not yet landed | OPEN |
| XiaoJ browser-control interface | Candidate action envelope and UI bridge prove XiaoJ controls browser without silent writes | Envelope specified; implementation not yet landed | OPEN |
| AV ordering | Audio/video/text input produces candidate order preview; raw audio not saved | Architecture exists; product verifier not yet PASS | OPEN |
| Local/cloud brain convergence | Local model and cloud candidate compute are routed through refs; no external API without release | Local/container scope captured; front-brain route incomplete | OPEN |
| Multi-intent handling | Order, menu query, translation, manager override, refund candidate, live message, cash advance, membership routed distinctly | Intent set defined; runtime verifier missing | OPEN |
| Lively but accurate XiaoJ | Persona/tone test passes without menu invention, payment action, or member plaintext | Not yet verified | OPEN |
| Customer stickiness | Registration, return loop, loyalty/referral/message cadence, and evidence metrics exist | Market packet exists; runtime not landed | OPEN |
| Safety invariants | No secret read, member plaintext, POS order, payment, deploy, restart, Odoo DB write without release | Current prep runs clean | PASS |

## Definition Of Done For P1

P1 is accepted only when all of the following are true:

| Gate | Pass condition |
| --- | --- |
| Auth route gate | LINE, Google, and member registration routes return 200/302/303/controlled 4xx, not raw 404 |
| Menu source gate | A real menu source lock exists with product codes, names, categories, add-ons, prices, and source hashes |
| Menu UI gate | Product table, category selector, menu selector, attributes, add-ons, batch preview, and import/export render |
| Manager UI gate | Vietnamese manager labels and dropdown-confirm flows render for price changes, returns, category moves, and availability |
| XiaoJ control gate | XiaoJ produces browser-control candidate actions with confirm/cancel states and no silent writes |
| AV gate | Audio/video/text input can produce a candidate order preview without saving raw audio |
| Local brain gate | Local model route is selected and health-checked; cloud compute remains a ref unless explicitly released |
| Multi-intent gate | At least eight intents are routed and independently verified |
| Stickiness gate | LINE/Google registration, return prompt, reward/referral/message loop, and metrics refs exist |
| Safety gate | Secret/member/payment/order/restart/deploy/prod-write flags remain clean unless explicitly approved and truthfully reported |

## Minimum P1 Intent Set

| Intent | Example | Required result |
| --- | --- | --- |
| menu_lookup | "耶加雪夫有什麼選項" | Show real product/options from locked menu |
| order_candidate | "我要一杯熱拿鐵少糖" | Candidate order preview, no POS order yet |
| translate_assist | "給店長看越文" | Vietnamese assist label only; no fact creation |
| manager_price_change | "這個改價" | Dropdown/stepper candidate and manager confirm |
| return_candidate | "退這筆" | Reason dropdown and manager confirm; no payment capture |
| category_move | "移到無咖啡因" | Dry-run affected rows |
| live_notice | "櫃台提醒後台" | Evidence-backed message |
| cash_advance_ref | "廠商費用先從現金預支" | Custody evidence ref only |
| member_register | "LINE/Google註冊" | Auth route starts registration flow |
| loyalty_return | "下次再來提醒" | Retention/referral/message candidate |

## Required Evidence Artifacts

| Artifact | Purpose |
| --- | --- |
| `runtime/d8_db/reports/XIAOJ_AUTH_NODE_CONTAINER_GATE_VERIFY_20260624.json` | Current auth/container gate evidence |
| `docs/product/XIAOJ_QUICKCLICK_GRADE_MENU_AUTH_STICKINESS_LAND_PACKET.md` | Human-reviewed LAND boundary |
| `docs/operations/XIAOJ_QUICKCLICK_GRADE_MENU_MANAGEMENT_BUILD_SPEC.md` | UI/build specification |
| `docs/product/XIAOJ_AV_ORDERING_P1_ACCEPTANCE_MATRIX.md` | This acceptance matrix |
| Future auth verifier report | Proves LINE/Google/member routes are no longer raw 404 |
| Future real menu source lock report | Proves menu truth source is locked |
| Future UI smoke report | Proves the menu management UI renders |
| Future XiaoJ candidate action report | Proves AI actions remain candidate-only |

## Current Decision

STATE=HOLD_P1_NOT_ACCEPTED

P1 is not complete. The next safe product movement is a human-approved LAND task for route shells and menu UI code paths. Runtime actions still require a separate explicit release.

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
