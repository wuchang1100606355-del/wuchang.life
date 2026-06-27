# XiaoJ QuickClick Grade Menu Auth Stickiness LAND Packet

RUN_ID=D8_MANDATORY_TASK_20260624_083658_XIAOJ_QUICKCLICK_GRADE_MENU_AND_AUTH_LAND_PACKET_PREP
STATE=LAND_PACKET_READY_FOR_HUMAN_REVIEW
ROOT=/home/taiji_admin/Taiji_Hub
NEXT_GATE=XIAOJ_AV_ORDERING_AUTH_AND_STICKINESS_LAND_P1

## Product Target

Build XiaoJ as the cafe operation layer that can drive the browser, understand the real shop menu, help staff order by voice/image/table, and keep customers returning through LINE/Google registration, role-aware permissions, and sticky service memory.

This is not a generic POS clone. The Odoo/POS transaction core remains the formal authority. XiaoJ is the multi-intent local brain and browser operator that turns shop context into verified candidate actions.

## Human Requirements Captured

| Requirement | LAND meaning |
| --- | --- |
| `這些功能都造` | Build all QuickClick-grade menu management functions, not only a demo list |
| `僅可用我店內原有菜單` | Real cafe menu source is mandatory; no GPT invented items |
| `店長是越南人` | Manager UI must be Vietnamese-friendly with icons, tables, and confirmation states |
| `退單改價現場忙，使用下拉是選單確定` | Busy operations use dropdowns plus final confirmation |
| `店內現金櫃台POS與後台都得有即時訊息` | Cashier and back office need live operational notices |
| `廠商收費用可由店雲從店內現金預支` | Cash advance is evidence/custody workflow, not payment capture |
| `所有介面都是小J控制瀏覽器` | XiaoJ browser-control layer must be the operator surface |
| `用圖片及表格來表示文字輔助AI可轉英文越文` | Product UI should prioritize images, tables, and bilingual/trilingual assist labels |
| `LINE註冊登入及GOOGLE註冊沒問題` | LINE and Google member routes must become non-404 before launch claim |
| `總場範圍不只本機還必須所有節點及容器` | Total Field must observe all nodes/containers but cannot mutate runtime without approval |

## Current Evidence

| Evidence | Result |
| --- | --- |
| Total Field status | PASS, D8 memory 4741 |
| QuickClick menu management scope | Captured and sealed |
| Node/container gate | Container gate PASS |
| Auth route gate | HOLD; LINE/Google/member registration routes still 404 |
| Real menu source | HOLD; human QuickClick screenshot conflicts with local CSV/Odoo source |
| Odoo/POS write in this run | Not allowed and not performed |

## Build Scope For P1

P1 must create the smallest real product spine that makes the requested end state more true:

1. LINE/Google/member registration route gate
2. Real menu source lock and conflict resolution
3. Product-grade menu management screen
4. Vietnamese manager/cashier operation layer
5. XiaoJ browser-control command envelope
6. Live cashier/back-office message channel
7. Candidate-only AI action preview
8. Role/permission matrix tied to store, manager, staff, and cashier refs

## Required QuickClick-Grade Functions

| Function | Required behavior | Gate |
| --- | --- | --- |
| Product list | Show product code, name, category, add-on menu, inventory, update time, and actions | Real source only |
| Category selector | Filter by real cafe category | Source lock |
| Menu selector | Select active store menu such as `聊國咖啡館重新店-QC` | Store/menu collision check |
| Category settings | Create/edit/sort/assign categories | Preview diff |
| Add product | Add only from human-approved real source | Human confirmation |
| Edit product | Edit metadata/category/photo/add-on/availability | Dry-run then approve |
| Copy product | Copy real product as draft candidate | Candidate only |
| Delete/archive | Prefer archive/disable; destructive delete requires explicit approval | Human confirmation |
| Recommended products | Hidden/order-count/custom recommendation controls | No accounting/order side effect |
| Attributes | Size, temperature, sweetness, beans, meal type, and shop-specific attributes | Real options only |
| Add-on menu | Choices, price deltas, required/optional rules | Real add-ons only |
| Batch update | Select all/none and apply category/menu/availability | Dry-run diff |
| Import | Import QuickClick/Odoo verified source | Stale-source conflict check |
| Export/audit | Export current menu index, source hash, and rollback evidence | Required |
| Role permission | Owner, manager, cashier, staff | No privilege guessing |
| Live notice | POS/cashier/back-office messages | Evidence-backed only |
| Cash advance evidence | Record vendor cash advance request/approval/ref | No payment capture |
| Multilingual UI | Chinese truth source plus Vietnamese/English assist labels | Translation cannot invent facts |
| Photo reference | Real product/store photos only | Generated image not menu authority |

## UI Standard

The first screen must be the operation console, not a marketing landing page.

Use:

- tables for products, attributes, add-ons, prices, and status
- product/store photos where real photos exist
- icons for edit/copy/archive/message/confirm
- dropdowns for return, price change, category move, add-on group, and availability
- confirmation panel before any write candidate becomes real
- Chinese source labels with Vietnamese and English assist labels
- no long instruction paragraphs inside the working interface

## Role Model

| Role | Allowed default | Requires manager/human confirmation |
| --- | --- | --- |
| Store owner | approve menu source, approve deployment scope, approve cash custody policy | production release |
| Vietnamese manager | confirm price change, refund/return candidate, category moves, closing checks | Odoo/POS write landing |
| Cashier/staff | take orders, cash collection, handoff notes, live messages | price override, refund, member plaintext |
| XiaoJ | observe screen, propose actions, translate, prepare dry-run, explain risks | final action without human confirmation |
| Total Field | observe/index/classify/warn/seal all nodes/containers | runtime mutation |

## Data Model Targets

| Field | Meaning |
| --- | --- |
| store_ref | Shop identity / D8 code / packet ref |
| manager_ref | Manager authority ref, not plaintext identity |
| staff_ref | Staff shift and rule ref |
| menu_ref | Menu identity and source hash |
| product_code | Real QuickClick/Odoo product code |
| product_name_zh | Source-of-truth Chinese product name |
| product_name_vi | Vietnamese assist label |
| product_name_en | English assist label |
| category_ref | Real category |
| addon_menu_ref | Add-on group |
| attribute_refs | Size, temperature, sweetness, beans, meal, other options |
| price | Human-approved price |
| availability | POS visibility/stock state |
| photo_ref | Real photo evidence ref |
| source_ref | QuickClick export, screenshot, Odoo row, or approved shop document |
| source_hash | Evidence hash |
| review_status | draft, verified, approved, landed, disabled |
| xiaoj_candidate_action | Proposed browser/POS action before approval |
| audit_ref | Change evidence and rollback pointer |

## Hard HOLD Conditions

| Condition | State |
| --- | --- |
| LINE/Google/member route still 404 when launch is claimed | HOLD_AUTH_ROUTE_GATE |
| Real menu source conflicts or is missing | HOLD_REAL_MENU_SOURCE_LOCK |
| Odoo addon path not explicitly authorized | HOLD_ODOO_PATH_SCOPE |
| Odoo restart/module upgrade needed but not approved | HOLD_RUNTIME_APPROVAL |
| Secret/OAuth token required | HOLD_SECRET_REQUIRED |
| Member plaintext needed | HOLD_MEMBER_PLAINTEXT_REQUIRED |
| POS order/payment action requested during menu management | BLOCK_SCOPE_VIOLATION |

## Proposed Human Release Text

Use the following release only when ready to authorize code edits, not service restart:

```text
允許進入 XIAOJ_AV_ORDERING_AUTH_AND_STICKINESS_LAND_P1。
本輪只允許修改指定 Odoo addon / UI / verifier 路徑。
允許修 LINE/Google/member registration route 404、真實菜單管理 UI、越南店長操作層、dry-run preview。
不允許讀 .env / OAuth secret / member plaintext。
不允許重啟 Odoo、不允許 module upgrade、不允許寫 Odoo DB、不允許下單、不允許付款、不允許 deploy，除非下一段人審再明確批准。
```

## Safety Flags For This Prep Run

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
