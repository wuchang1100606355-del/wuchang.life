<!-- W7TP_LLM_REALITY_BOUNDARY_V1: {"schema": "W7TP_LLM_REALITY_BOUNDARY_V1", "principle": "LLM hallucination is conditionally allowed only inside an imagined candidate layer.", "reality_layers": ["REAL_VERIFIED", "IMAGINED_CANDIDATE", "EXECUTABLE_AUTHORIZED"], "llm_hallucination_allowed": "conditional", "allowed_hallucination_layer": "IMAGINED_CANDIDATE", "environment_provided_by_total_field": true, "llm_self_truth_authority": false, "truth_boundary_ref_required": true, "reality_discrimination_method": "total_field_supplied_environment_with_evidence_anchors_truth_boundary_ref_local_reconstruction_and_discrete_verifier_status", "imagined_content_must_be_labeled": true, "real_claim_requires_evidence_ref": true, "execution_claim_requires_local_gate": true, "cloud_can_mark_real_verified": false, "cloud_can_mark_executable_authorized": false, "total_field_distinguishes_real_or_imagined": true, "real_verified_source": "local_reconstruction_plus_evidence", "execution_source": "local_discrete_state_verifier"} -->

# 上品聊國咖啡館（重新總店 Company 3）｜AI 精選商業版 Gemini 知識庫素材包
- **生成時間**：`2026-10-21T17:53+08:00`
- **所屬系統**：`W7TP／8D ADI V2.3`（D4 第 7 筆四維時空封印 `1b771a60…` 已閉合）
- **核心任務（WUC-10）**：在不複製舊 UI 的前提下，打造**超越市售產品級的人類店家介面（支援中/越/英三語輔助標籤、圖片+表格+繁忙時段下拉選單快速確認、櫃台與後台即時通知）**，並完整閉合五項功能缺口：
  1. **菜單匯入**：來源版本 (`M387676` 64商品/21規格組/212選項) + 現有商品狀態雙基準預覽，19項同碼異名與30列重複列不誤合併，核定後寫入。
  2. **專用分類編輯**：分類新增、切換、排序，串接既有責任人授權及審核稽核。
  3. **整合菜單匯出**：現行商品／選項、來源雜湊、版本、可追溯稽核及回復封套。
  4. **加料／客製化完整點餐**：必填、多選、尺寸價差、溫度糖分、品類例外（濾掛咖啡排除現場點餐）與 POS 端到端驗收。
  5. **訂單統計**：依既有授權界線串接訂單統計與必要店員通知，不改寫歷史訂單。

---
## [1] CORE_SPEC｜`docs/product/XIAOJ_QUICKCLICK_GRADE_MENU_AUTH_STICKINESS_LAND_PACKET.md`
- **用途說明**：越南店長三語、下拉選單、即時訊息與 M387676 菜單核心需求
- **SHA-256**：`a955c2034d2dc64a486fd2d8a9e5693907c0431874919072247ea3a03520aa45`

````md
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

````

---
## [2] CORE_SPEC｜`docs/operations/QUICKCLICK_MENU_MANAGEMENT_FUNCTIONS_SCOPE.md`
- **用途說明**：QuickClick 歷史菜單管理完整功能範圍
- **SHA-256**：`0be70293baab5d2d63d21597504bd625c0793f88cd45ed672618d883a00ef4de`

````md
# QuickClick Style Menu Management Functions Scope

RUN_ID=D8_MANDATORY_TASK_20260624_071412_QUICKCLICK_MENU_MANAGEMENT_FUNCTIONS_SCOPE_CAPTURE
STATE=FIELD_OBSERVED_TOTAL_FIELD_QUERIED
TARGET=聊國咖啡館重新總店菜單與 POS 後台功能

## Purpose

This scope captures the functions visible in the QuickClick menu management screen and converts them into a safe implementation target for the cafe system.

This is not a menu invention pass. Product names, categories, prices, add-ons, photos, translations, and availability must come from real cafe sources such as QuickClick export, verified screenshots, Odoo records, or human-approved shop materials.

## Required Function Groups

| Group | Function | Product Rule |
| --- | --- | --- |
| Product list | Display product code, product name, product attributes, category, add-on menu, inventory, update time, and row actions | Must use real source rows only |
| Product category selector | Filter product list by category | Category names must match real cafe taxonomy |
| Menu selector | Select active menu for the store, such as `聊國咖啡館重新店-QC` | Store/menu identity must pass collision check |
| Product category settings | Create, edit, sort, and assign categories | No fake emergency category as final authority |
| Add product | Add a new product only from human-approved real source | No GPT invented menu item |
| Edit product | Update product metadata, category, attribute, add-on group, photo, and availability | Requires preview and human confirmation before Odoo/POS write |
| Copy product | Duplicate a real product as a draft candidate | Must remain draft until verified |
| Delete product | Prefer disable/archive over destructive delete | Requires human approval |
| Recommended products | Support hidden, order-count based, and custom recommendations | Recommendation must not alter accounting/order records |
| Product attributes | Manage attribute groups and values such as size, temperature, sweetness, beans, meal type | Attribute ordering affects POS display |
| Add-on menu | Manage add-on groups, choices, price deltas, and required/optional rules | Add-ons must match real shop choices |
| Batch update | Select all/none and apply category/menu/availability changes | Batch writes require dry-run diff first |
| Import menu | Import production menu from verified QuickClick/Odoo source | Import must detect stale source conflict |
| Export/audit | Export current menu index, source hash, and change evidence | Required for rollback and store review |
| Role permission | Owner, manager, cashier, and staff scopes | Vietnamese manager flow must be clear enough for direct operation |
| Live notice | Back office and cash register need immediate messages | Message must be evidence-backed, not payment/order automation |
| Vendor advance | If vendor fees are paid from store cash advance, record as cash custody evidence | Does not create payment capture or accounting posting without approval |
| Multi-language support | Chinese source with English/Vietnamese assistive labels | AI may translate labels, but not invent menu facts |
| Photo support | Attach real product/store photos as references | Generated images are not menu truth |

## Minimum Product-Grade Behavior

1. The first screen should be operational, not marketing copy.
2. Menu management must work by table, image, and category, with clear icon actions.
3. A Vietnamese-speaking manager must be able to confirm what each button does without reading long Chinese instructions.
4. Dropdowns are acceptable for busy store operations such as return, price change, category move, and add-on selection, but the final action must show a confirmation state.
5. Every AI suggestion must be a candidate. It cannot silently create products, orders, payments, accounting entries, or member records.
6. Real menu source has priority over GPT text, demo JSON, emergency menu, and product prompt packs.

## Required Data Fields

| Field | Meaning |
| --- | --- |
| store_ref | Store identity, such as 聊國咖啡館重新總店 |
| menu_ref | Menu identity and source hash |
| product_code | QuickClick/Odoo product code |
| product_name_zh | Real Chinese product name |
| product_name_vi | Vietnamese assistive label |
| product_name_en | English assistive label |
| category_ref | Product category |
| addon_menu_ref | Add-on group |
| attribute_refs | Size, temperature, sweetness, bean, meal, or other attribute references |
| price | Human-approved price |
| inventory_state | Visible stock/availability status |
| available_in_pos | POS visibility flag |
| photo_ref | Real product or shop photo reference |
| source_ref | QuickClick export, screenshot, Odoo row, or human-approved document |
| source_hash | Evidence hash for the source |
| review_status | draft, verified, approved, landed, disabled |
| audit_ref | Change evidence and rollback pointer |

## Safety Gates

| Gate | Rule |
| --- | --- |
| Source gate | HOLD if real menu source is missing or contradictory |
| Collision gate | HOLD if store/menu/POS identity conflicts |
| Dry-run gate | All batch/product writes require a preview diff |
| Human gate | Odoo/POS writes require explicit human release |
| Payment gate | No payment capture in menu management |
| Order gate | No POS order creation in menu management |
| Member gate | No member plaintext in menu management |
| Secret gate | No `.env`, token, password, or config secret read |

## Implementation Phases

| Phase | Scope | Landing Rule |
| --- | --- | --- |
| P0 Source lock | Bring in verified QuickClick export/screenshots and current Odoo read-only product index | Docs/runtime only unless approved |
| P1 Catalog UI | Product list, filters, edit/copy/archive draft actions | Code changes require new task capsule |
| P2 Menu/category UI | Menu selector, category settings, sorting, assignment | Dry-run first |
| P3 Attributes/add-ons | Product attributes and add-on menu management | Must match real cafe options |
| P4 Recommendations | Hidden/order-count/custom recommendation controls | No accounting/order side effect |
| P5 Batch operations | Select all/none, category move, availability update | Preview diff required |
| P6 Translation/photo layer | Chinese source with Vietnamese/English assist labels and photo refs | Translation cannot create facts |
| P7 Store messaging | Back office/cashier live messages and cash advance evidence | No payment capture |
| P8 Odoo/POS landing | Write approved products/options into Odoo/POS | Requires explicit human authorization |

## Current Decision

STATE=HOLD_FOR_IMPLEMENTATION_APPROVAL

The functions are valid product targets. This run captured the scope only. Actual implementation will touch Odoo addon/UI/data paths and therefore requires a new explicit LAND packet that names allowed code paths and write limits.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE

````

---
## [3] CORE_SPEC｜`docs/operations/QUICKCLICK_MENU_EQUIVALENCE_GAP_20261009.md`
- **用途說明**：WUC-10 五項待整合功能缺口與雙基準預覽規格
- **SHA-256**：`53d1ea381f72c2ddffaef90b3d5619ad412d59074aa79bf95f973b4b479cc6bf`

````md
# 咖啡館菜單等價重構：本輪範圍與差異

本輪意圖：沿用 `wuchang_cafe_menu_options`，先完成可獨立驗收的菜單管理缺口。所有程式變更均為隔離候選，正式服務與資料未由本輪修改。

## 觀測與來源

- GitHub 預設主線與 taiji01 提交：`3c2e5884bc149ffbb02d81fdf288506918fae79e`，2026-10-08T21:59Z 前後唯讀觀測；這不是運行模組已載入的證明。
- 正式任務上下文：`context:task-state:ODOO_QUICKCLICK_EQUIVALENT_20261009:0a3d0c5ffcaee39a`；單次拉取摘要 `3ba25616b4413a3f6411cd4b872b6d90345ee47e0bc8f90afa821640f5eeaf95`。既有總場於本地揮發工作區重構；本輪未另造上下文核心。
- 最新菜單：`匯出菜單-聊閣社區咖啡重新店-QC_1791483045386.xlsx`，來源 SHA-256（安全雜湊演算法）`c3f4a31ee60509dc6a75dad64c6c6be4de0089ff1ff5f00695467ae61b34c630`；Library 檔案 `libfile_ea2bc0c055208191a974dd33265c479d`。
- 菜單 `M387676`，64 個商品、21 組規格組合、45 個題型、242 列原始選項。沿用既有解析器後為 212 個語義選項。19 項代碼對應不同名稱警示，加上 30 列重複列合併警示。這些警示不可當成正式資料修正授權。
- 功能需求：既有 `QUICKCLICK_MENU_MANAGEMENT_FUNCTIONS_SCOPE.md`；此文件是歷史功能範圍證據，本輪未重新觀測全部 QuickClick 畫面，也未使用歷史訂單做推薦驗收。

## 差異對照

| 實際需求 | 主線程式已有能力 | 本輪候選／剩餘差異 | 驗收界限 |
|---|---|---|---|
| 商品搜尋、圖片卡、清單、分類篩選 | 專用搜尋、看板、清單、表單 | 沿用；清單增加批次預覽入口 | 須由隔離 Odoo 載入視圖，不能只由 XML 存在認定 |
| 單項價格、名稱、分類、規格修改 | 單筆變更申請與前後快照；商品表單仍可直改 | 專用表單改為檢視及申請；封存／上架先建立申請 | 後台通用產品編輯與既有權限不在本輪重寫範圍 |
| 批次價格、分類、暫停、封存、上架 | 只有需求規格，無選取後預覽精靈 | 新增最多 100 商品的中文前後差異表；送審不套用 | 每項重用既有審核及稽核；無差異不建立申請 |
| 防止過期預覽覆寫商品 | 單筆快照重新驗證 | 預覽綁公司、商家、帳號、商品集合；再次核對再送審 | 套用鎖定申請與商品；完整同時並發壓力測試未完成 |
| 回復已套用的變更 | 原始快照與稽核保存，無回復入口 | 建立新的反向申請；價格、分類、名稱、規格及啟用／販售狀態可回復 | 商品較新狀態會阻擋；圖片前像未保存時阻擋；新增商品改走封存 |
| 自然人單一帳號、既有商家授權 | 負責帳號綁定、權限組、記錄規則 | 沿用；無新增登入系統 | 本輪空白測試庫帳號是既有 Odoo 測試帳號；非正式會員 |
| 菜單切換、分類排序、新建分類 | 商品來源欄位、Odoo 原生分類；專用分類只有讀取權 | 尚未完成專用預覽審核介面 | 不擴充正式權限 |
| 屬性與加料、必填、多選、價差 | 規格組、題型、選項、價格差已有程式 | 沿用；來源代碼衝突須保留選項範圍，不可按單一代碼合併 | 本輪未宣告完整加料點餐等價 |
| 真實菜單匯入、來源衝突檢測 | 既有 XLSX 快照解析器、來源欄位、舊匯入路徑 | 已讀最新來源；正式安全匯入與來源版本比對仍待補 | 本輪不呼叫舊公開匯入路徑、不寫正式商品 |
| 匯出目前菜單、來源雜湊及稽核 | Odoo 原生匯出、快照與事件簿 | 尚缺整合下載與回復封套 | 預覽與變更稽核已保存；不是完整匯出產品驗收 |
| 推薦商品、訂單統計、店員通知 | 需求規格及其他模組基礎 | 本輪不實作；銜接既有點餐工作 | 不動訂單、收款、會計或會員資料 |

## 操作流程

選取清單商品 → 批次修改預覽 → 逐項比較商品／修改項目／前值／後值 → 送審 → 原帳號核准 → 原帳號再次確認套用。送審及核准均不修改商品。回復從已套用申請建立新申請，再走同一流程；不改寫歷史。

## 隔離依賴與回復

主線空白 Odoo 18 安裝首先被 `wuchang_member_registration/views/signup_templates.xml` 的舊 XPath 阻擋；菜單模組尚未載入。隔離測試重用 taiji01 已有的一行修復（`auth_signup.fields` 節點），修復檔雜湊為 `8f4d00a692735ca518d0a8cd8b62eaa092b48f52fa56b48f5852492c34dd6627`。本輪未修改正式註冊來源，此依賴不屬於本輪菜單補丁。

空白 PostgreSQL（關聯式資料庫）與 Odoo 測試容器只有私有隔離網路，沒有公開主機連接埠，沒有複製正式資料。測試結束移除本輪測試容器與網路。正式 Odoo／資料庫程序啟動時間及重啟次數前後對照記於驗收文件。

候選撤回：不套用補丁即可；沒有正式資料或權威指標回滾需求。若日後獲准部署，需先備份資料庫、核對現行依賴修復與模組版本，另行完成真實介面及正式資料驗收。

## 本輪驗收結果

- 2026-10-09 06:11:43（台北）：真實 Odoo 18 空白隔離庫驗收通過。70 個相依模組成功載入，10 項實際 ORM（物件關聯映射）流程測試零失敗、零錯誤。
- 既有及新增純程式測試 17 項通過，修改檔編譯、XML 解析與補丁空白檢查通過。
- taiji01 候選與本地 15 個菜單模組來源檔雜湊一致。正式菜單模組工作樹仍無本輪修改；未提交、未推送、未部署。
- 三輪測試均記錄正式 Odoo／資料庫程序前後狀態一致，測試容器與私有網路均已移除。完整回執、原始失敗脈絡及最終測試日誌摘要見 `QUICKCLICK_MENU_BATCH_ACCEPTANCE_20261009.json`。
- 本輪沒有完成瀏覽器視覺驗收、64 個商品全面匯入、歷史訂單與推薦功能驗收，或總場正式啟用裁決。來源菜單未被示範資料取代。

## 下一個獨立工作

將最新來源的商品、規格及代碼衝突接入既有受審核匯入，建立「來源版本＋目前商品狀態」雙基準預覽；再與進行中的本地小J點餐工具銜接。完整 QuickClick 功能等價仍未驗收，不應由本輪局部通過推廣為全部完成。

````

---
## [4] CORE_SPEC｜`docs/design/W7TP_009_LIAOGUO_COMPANY_POS_IDENTITY_PATCH.md`
- **用途說明**：重新總店(Company 3)、仁義分店、合作商家三主體帳務隔離規範
- **SHA-256**：`62249cab45981cdfd77ee7f4efe457c60ac455693997b397ff8493f9719473a3`

````md
# W7TP-009 聊國咖啡公司 / POS 主體身分補丁

狀態：PLANONLY / DESIGN PATCH ONLY

## A. 外部友軍贊助公司

- company_name=上品食品行
- tax_id=34778660
- responsible_person=江政隆
- pos_name=上品聊國咖啡館 重新總店
- address=新北市三重區重新路三段204號1樓
- company_boundary_type=external_friendly_sponsor
- community_jurisdiction=false
- inside_wuchang_community=false
- accounting_scope=external_sponsor_company_account
- capital_gain=true
- public_interest_support=true
- support_direction=one_way_to_association_infrastructure

## B. 社區 / 協會公益基金池主體

- company_name=新北市三重區五常社區發展協會
- tax_id=同協會統編
- responsible_person=江政隆（協會派任）
- pos_name=上品聊國咖啡館 仁義分店
- company_boundary_type=community_industry_subsidiary
- community_jurisdiction=true
- accounting_scope=community_digital_development_fund_pool
- personal_capital_gain=false
- fund_nature=五常社區數位發展基金
- renyi_store_staff_caregiver_qualified=true

## C. 外送合作商家示範 POS

- pos_name=外送合作商家示範 POS
- company_boundary_type=delivery_partner_demo
- accounting_scope=demo_partner_account
- purpose=delivery_partner_template
- cross_company_accounting_mix=false

## Hardwall

- 上品食品行 / 重新總店 不等於 五常社區發展協會 / 仁義分店。
- 協會統編待填，不得用 34778660 代替協會統編。
- 重新總店帳務不得混入協會基金池。
- 仁義分店公益基金池不得混入重新總店營利帳。
- 三 POS 必須 company_id / branch_id / accounting_scope / pos_scope 分離。
- raw_pii_to_cloud=false
- odoo_write=false
- db_connect=false
- plan_only=true

````

---
## [5] CORE_SPEC｜`docs/product/XIAOJ_BUSINESS_BACKEND_OPTIMIZATION_AND_AV_AI_MERCHANT_SYSTEM_PLAN.md`
- **用途說明**：商家營運駕駛艙、AI 品質、LINE 與財務永續藍圖
- **SHA-256**：`a5a0f2a0c4652ef2013a67dcc215613b6f97aa396be0046ad032fd0ae73e335b`

````md
# XiaoJ Business Backend Optimization and AV AI Merchant System Plan

STATE=P1_BACKEND_OPTIMIZATION_REVIEW_READY

## Purpose

This plan turns the existing XiaoJ productization, Odoo authority node, LINE/LINE WORKS gates, and total-field evaluation work into a business backend improvement roadmap for a high-quality audiovisual AI merchant system.

The system must improve business operation without interrupting the cafe's current manual operation. It must also respect the current local reality: the cafe is active, the association depends on cafe operating cashflow, Sanchong community self-funding is not yet mature, and the founder mission needs to become sustainable beyond single-person burden.

## Target Outcome

The target backend is not just an AI demo. It must become an operator-grade merchant system with:

- a cafe operating cockpit for revenue, orders, courses, referrals, LINE status, and handoff blockers;
- a safe AV AI ordering workflow that produces candidate orders only until Odoo validates menu, price, options, member, voucher, and payment boundaries;
- a LINE Official Account / LINE WORKS control plane that separates association and cafe subjects;
- a financial sustainability layer that tracks debt pressure, course cost allocation, cafe cashflow recovery, and revenue recovery;
- a Sanchong demonstration layer that measures local trust, course-to-member conversion, cafe revenue signals, and community self-funding triggers;
- a no-secret, no-plaintext, no-production-side-effect P1 review mode.

## Current Backend Surfaces

Existing usable surfaces:

- `Business Backend Optimization`: packet-backed P1 backend review cockpit for business continuity, AV AI quality, financial sustainability, Sanchong demonstration, founder mission, release gates, and staff correction queue.
- `Total Product Handoff`: operator ref collection, handoff pack, side-effect boundary, production activation hold.
- `LINE Official Account Config`: candidate settings, webhook candidate, human owner/admin release boundary.
- `LINE WORKS Notification`: candidate, preflight, release refs, runtime activation draft, operator handoff.
- `Cafe AI Eventbook`: event evidence and candidate workflow surface.
- `Cafe Menu Options`: structured menu customization options.
- `Member Registration`: member identity, consent, organization/person review gates.
- `Property / Association / Fund Allocation modules`: broader association and resident management context.

Backend gap:

The current backend is strong on safety gates and productization packets, but it needs a business cockpit that makes revenue continuity, course economics, local demonstration progress, AI AV quality, and operator burden visible in one operating loop.

## End-To-End Flow

1. Customer or staff initiates inquiry through in-store service, LINE, future AV AI ordering, or manual channel.
2. AI layer captures intent as text/audio/video candidate only.
3. Candidate parser creates structured order intent with menu item, options, quantity, context, allergy risk, and confidence.
4. Odoo authority validates menu, price, custom options, availability, member, voucher, and payment preconditions.
5. Operator cockpit shows the candidate with risk flags and fallback path.
6. Human staff confirms or edits before any real POS write.
7. Payment and voucher actions remain manual or separately released until activation refs are complete.
8. LINE/LINE WORKS notifications remain candidate/preflight unless human release refs and runtime resolver refs pass.
9. Daily close reconciles manual orders, POS entries, LINE events, course income, expenses, debt pressure, and community demonstration metrics.
10. Total field receives evaluation packets, not raw secrets, raw member data, raw payment data, or uncontrolled API authority.

## Backend Feature Additions

### 1. Business Continuity Cockpit

Required widgets:

- current manual operation status;
- new automation hold status;
- today's order count, revenue signal, and manual fallback status;
- open blockers by release gate;
- DNS/gateway rollback status;
- LINE/cafe/association subject separation status;
- vendor/API control risk status.

Required refs:

- `manual_order_fallback_ref`
- `manual_payment_fallback_ref`
- `existing_pos_continuity_ref`
- `line_manual_customer_service_ref`
- `dns_gateway_rollback_ref`
- `lost_order_prevention_ref`
- `daily_revenue_reconciliation_ref`

### 2. AV AI Merchant Quality Panel

Required widgets:

- voice capture candidate quality;
- video/product/menu recognition candidate quality;
- intent confidence;
- anti-hallucination status;
- allergy/price/payment/member risk flags;
- Odoo authority validation result;
- staff correction queue;
- customer-facing response preview.

Quality gates:

- no raw audio saved in P1;
- no raw video saved in P1;
- no cloud model authority;
- no direct POS write by AI;
- no price invented by AI;
- no voucher mutation by AI;
- low-confidence candidate goes to staff review.

### 3. Menu, Product, and Custom Option Control

Required widgets:

- menu source of truth status;
- active item availability;
- custom options JSON coverage;
- product photo evidence status;
- generated-image candidate status;
- price/version audit.

Rules:

- Custom Options JSON is preferred for sweetness, ice, temperature, size, toppings, and service notes.
- Generated images may be design candidates, not product evidence.
- Real product photo or staff-approved product photo is required before official product evidence use.

### 4. LINE / Domain / API Control Plane

Required widgets:

- association LINE OA refs;
- cafe LINE OA refs;
- channel candidate ids;
- provider/admin role review;
- vendor access review;
- association-approved subdomain;
- webhook relay;
- callback relay;
- runtime secret rotation readiness.

Rules:

- association and cafe LINE OA subjects must stay separate;
- cafe endpoints must use association-approved subdomains;
- association can provide protective gateway support but cannot silently take over cafe commercial ownership;
- vendor-controlled API cannot write POS, payment, member, or LINE send surfaces.

### 5. Financial Sustainability Panel

Required widgets:

- operator-reported three-year debt increase review;
- course expansion review;
- course cost allocation;
- cafe cashflow recovery;
- debt reduction plan;
- revenue recovery signal;
- unfunded fixed-cost warning.

Required refs:

- `debt_increase_review_ref`
- `association_course_expansion_ref`
- `course_cost_allocation_ref`
- `cafe_cashflow_recovery_ref`
- `debt_reduction_plan_ref`
- `revenue_recovery_ref`

### 6. Sanchong Demonstration and Community Self-Funding Panel

Required widgets:

- Sanchong local readiness status;
- demonstration success metric;
- community trust building;
- course-to-member conversion;
- cafe revenue signal;
- community self-funding trigger.

Strategy:

Sanchong is treated as not yet fully self-funding. The operating strategy is to first create visible, low-risk demonstration results through cafe service and association courses, then use those results to trigger community self-funding.

### 7. Founder Mission Sustainability Panel

Required widgets:

- founder mission ref;
- governance handoff status;
- volunteer role split;
- operator burden reduction;
- public-service continuity;
- single-person risk concentration warning.

Rule:

The founder mission must be institutionalized. The system must not require continued single-person debt absorption, unbounded labor, or unmanaged technical risk.

## Process Improvement Measures

1. Add a daily operating review:
   revenue signal, manual fallback, unresolved candidates, LINE incidents, course income, and release blockers.
2. Add a weekly sustainability review:
   debt pressure, course cost allocation, operator burden, community conversion, and next demonstration milestone.
3. Add a release gate board:
   P1 candidate, human refs pending, ready for human review, ready for activation packet, executed after release.
4. Add a staff correction loop:
   AI candidate mistakes become menu/intent/risk training evidence without raw personal data.
5. Add a local demonstration score:
   small visible wins before any large unfunded scale-up.

## Activation Boundary

P1 review may create packets, reports, dashboards, and candidates only.

P1 must not:

- send LINE/LINE WORKS formally;
- write real POS orders;
- capture payments;
- register members formally;
- redeem vouchers formally;
- read raw secrets;
- move member/resident plaintext into prompts;
- save raw audio/video;
- deploy, restart, or upgrade Odoo.

## Recommended First Backoffice Enhancements

1. Add a backend checklist tab for business continuity refs and daily reconciliation.
2. Add a backend checklist tab for AV AI quality gates and staff correction queue.
3. Add a backend checklist tab for financial sustainability and course cost allocation.
4. Add a backend checklist tab for Sanchong demonstration metrics.
5. Add a backend checklist tab for founder mission handoff and operator burden reduction.

These additions can start as packet-backed fields and readonly JSON/Markdown panels before becoming full Odoo models.

## Odoo P1 Backend Surface

Initial Odoo surface:

```text
Model: wuchang.business.backend.optimization
Menu: WuChang Cafe / Business Backend Optimization
Mode: packet-backed readonly/checklist P1 review
```

The surface builds a `W7TP_XIAOJ_BUSINESS_BACKEND_OPTIMIZATION_PACKET_V1` review packet and exposes:

- backend panel list;
- checklist items with required refs, success metrics, and operator status;
- KPI snapshots for safe numeric and summary tracking;
- daily operating signals for safe aggregate revenue, order, incident, course, and burden indicators;
- AV AI candidate quality queue for audio, video, menu text, product image, and multimodal order candidates;
- product/menu quality queue for Odoo product refs, price refs, Custom Options JSON refs, photo evidence refs, availability, and AI candidate permission;
- signal trend review for improving, flat, regressing, and insufficient daily operating signals;
- management decision queue for critical/high/medium actions derived from trends, scorecards, and operating review;
- operator runbook for opening checks, service monitoring, daily close signal entry, weekly sustainability review, and total-field packet review;
- process walkthrough and improvement items for each merchant workflow stage;
- readiness scorecard for AV AI merchant maturity, blockers, and next actions;
- end-to-end flow;
- AV AI technology features;
- quality gates;
- required refs;
- business context;
- first backoffice enhancement list;
- P1 side-effect boundary.
- operating review packet with checklist blockers, KPI coverage, and next actions.
- daily signal packet with missing signal types, needs-action signals, observed day count, and next actions.
- AV candidate quality packet with confidence, Odoo validation state, red flags, product photo evidence state, and staff-review requirements.
- product/menu quality packet with required refs, blocker counts, missing custom options, missing photo evidence, and ready-for-AI-candidate counts.
- signal trend packet with trend items, regressing signal types, insufficient signal types, and next actions.
- management decision queue packet with sorted decision items and priority counts.
- operator runbook packet with daily/weekly operating phases and next actions.
- process walkthrough packet with stage-by-stage improvement backlog.
- readiness scorecard packet with score components, activation blockers, and improvement-first next actions.

It does not activate production behavior.

Operating review output:

```text
Schema: W7TP_XIAOJ_BUSINESS_BACKEND_OPERATING_REVIEW_PACKET_V1
Button: Build Operating Review
Inputs: checklist item statuses and KPI snapshot summaries
Outputs: blocked checklist items, missing KPI types, needs-action KPI list, next actions
```

Daily signal review output:

```text
Schema: W7T
````

---
## [6] ODOO_MENU_ADDON｜`Taiji_Odoo/addons/wuchang_cafe_menu_options/models/menu_batch_wizard.py`
- **用途說明**：現行批次修改預覽精靈（最多100商品中文差異表）
- **SHA-256**：`2b3313173f8faced947080586c32b5b24603f7396d86cdb056484ad02ed66c29`

````py
"""Preview selected products and enqueue the existing reviewed change requests."""

import json
from html import escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.menu_batch_governance import build_batch_preview
from ..services.menu_change_governance import MenuChangeGovernanceError, stable_sha256
from .menu_manager import RESPONSIBLE_GROUP


_PREVIEW_TOKEN = object()


class WuchangCafeMenuBatchWizard(models.TransientModel):
    _name = "wuchang.cafe.menu.batch.wizard"
    _description = "咖啡館菜單批次預覽"

    product_ids = fields.Many2many("product.template", string="選取商品", required=True)
    operation = fields.Selection([
        ("set_price", "設定相同售價"), ("set_categories", "改分類"),
        ("pause", "暫停販售"), ("archive", "封存商品"),
        ("reactivate", "重新上架"),
    ], default="pause", required=True, string="批次動作")
    price = fields.Float(string="新售價")
    category_ids = fields.Many2many("pos.category", string="新分類")
    preview_json = fields.Text(string="逐項修改前後差異", readonly=True)
    preview_html = fields.Html(string="逐項修改前後差異", compute="_compute_preview_html", sanitize=True)
    preview_sha256 = fields.Char(readonly=True)
    changed_count = fields.Integer(string="有變更商品數", readonly=True)
    submitted = fields.Boolean(readonly=True)

    _INPUT_FIELDS = {"product_ids", "operation", "price", "category_ids"}

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if set(values) - self._INPUT_FIELDS:
                raise UserError(_("預覽證據只能由系統產生。"))
        safe_values = [{**values, "preview_json": False, "preview_sha256": False,
                        "changed_count": 0, "submitted": False} for values in vals_list]
        return super().create(safe_values)

    def write(self, values):
        if self.env.context.get("wuchang_batch_preview_write") is _PREVIEW_TOKEN:
            return super().write(values)
        if set(values) - self._INPUT_FIELDS:
            raise UserError(_("預覽證據不能由操作端修改。"))
        if any(wizard.submitted for wizard in self):
            raise UserError(_("已送審的預覽不能修改；請建立新預覽。"))
        return super().write({**values, "preview_json": False,
                              "preview_sha256": False, "changed_count": 0})

    def _build_preview(self):
        self.ensure_one()
        if not self.env.user.has_group(RESPONSIBLE_GROUP):
            raise UserError(_("請使用已有菜單維護授權的同一帳號。"))
        batch = self.env["product.template"]._wuchang_responsible_batch()
        products = self.product_ids.with_context(active_test=False).exists().sorted("id")
        if len(products) != len(self.product_ids):
            raise UserError(_("選取商品已不存在，請重新選取。"))
        for product in products:
            if product.company_id and product.company_id != batch.menu_company_id:
                raise UserError(_("批次操作不能跨營運公司。"))
            if not (product.available_in_pos or product.w5c_domain == "CAFE" or product.wuchang_option_group_id):
                raise UserError(_("請只選取咖啡館菜單商品。"))
        value = self.price if self.operation == "set_price" else self.category_ids.ids
        try:
            preview = build_batch_preview(
                [product.wuchang_menu_snapshot() for product in products], self.operation, value)
        except (MenuChangeGovernanceError, ValueError) as exc:
            raise UserError(_("無法建立預覽：%s") % exc) from exc
        preview["binding"] = {"company_id": batch.menu_company_id.id,
                              "batch_id": batch.id, "actor_user_id": self.env.user.id,
                              "product_ids": products.ids}
        preview.pop("sha256")
        preview["sha256"] = stable_sha256(preview)
        return products, batch, preview

    @api.depends("preview_json")
    def _compute_preview_html(self):
        labels = {"list_price": "售價", "pos_category_ids": "分類",
                  "active": "商品啟用", "available_in_pos": "收銀台販售"}
        def display(key, value):
            if key == "pos_category_ids":
                return "、".join(self.env["pos.category"].browse(value).mapped("name")) or "無分類"
            if isinstance(value, bool):
                return "是" if value else "否"
            return str(value)
        for wizard in self:
            if not wizard.preview_json:
                wizard.preview_html = False
                continue
            rows = []
            for row in json.loads(wizard.preview_json)["rows"]:
                for key, change in row["diff"].items():
                    cells = [row["before"]["name"], labels[key],
                             display(key, change["before"]), display(key, change["after"])]
                    rows.append("<tr>" + "".join("<td>" + escape(cell) + "</td>" for cell in cells) + "</tr>")
            wizard.preview_html = '<table class="table table-striped"><thead><tr><th>商品</th><th>修改項目</th><th>修改前</th><th>修改後</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>"

    def _reopen(self):
        return {"type": "ir.actions.act_window", "res_model": self._name,
                "res_id": self.id, "view_mode": "form", "target": "new"}

    def action_preview(self):
        self.ensure_one()
        if self.submitted:
            raise UserError(_("這份預覽已送審。"))
        _, _, preview = self._build_preview()
        self.with_context(wuchang_batch_preview_write=_PREVIEW_TOKEN).write({
            "preview_json": json.dumps(preview, ensure_ascii=False, indent=2),
            "preview_sha256": preview["sha256"], "changed_count": preview["changed_count"],
        })
        return self._reopen()

    def action_submit(self):
        self.ensure_one()
        self.env.cr.execute("SELECT id FROM wuchang_cafe_menu_batch_wizard WHERE id = %s FOR UPDATE", (self.id,))
        self.invalidate_recordset()
        if self.submitted or not self.preview_sha256:
            raise UserError(_("請先產生新預覽，不能重複送審。"))
        products = self.product_ids
        if products:
            self.env.cr.execute("SELECT id FROM product_template WHERE id IN %s ORDER BY id FOR UPDATE", (tuple(products.ids),))
            products.invalidate_recordset()
        products, batch, preview = self._build_preview()
        if preview["sha256"] != self.preview_sha256:
            raise UserError(_("商品或商家授權已改變，請重新預覽；尚未修改菜單。"))
        request_model = self.env["wuchang.cafe.menu.change.request"]
        requests = request_model.browse()
        for product, row in zip(products, preview["rows"]):
            if not row["diff"]:
                continue
            proposed = {key: change["after"] for key, change in row["diff"].items()}
            values = request_model._request_values_for_proposal(proposed)
            values.update({"origin": "merchant_manager", "change_type": "update",
                           "group_batch_id": batch.id, "product_template_id": product.id,
                           "support_reason": "批次預覽 sha256:%s" % self.preview_sha256})
            requests |= request_model.create(values)
        if not requests:
            raise UserError(_("選取商品沒有差異，無需修改。"))
        requests.action_submit_for_responsible_review()
        self.with_context(wuchang_batch_preview_write=_PREVIEW_TOKEN).write({"submitted": True})
        return {"type": "ir.actions.act_window", "name": "批次菜單審核",
                "res_model": request_model._name, "view_mode": "list,form",
                "domain": [("id", "in", requests.ids)], "target": "current"}


class ProductTemplateBatchMenu(models.Model):
    _inherit = "product.template"

    def action_wuchang_menu_batch_preview(self):
        return {"type": "ir.actions.act_window", "name": "批次修改預覽",
                "res_model": "wuchang.cafe.menu.batch.wizard", "view_mode": "form",
                "target": "new", "context": {"default_product_ids": [(6, 0, self.ids)]}}

````

---
## [7] ODOO_MENU_ADDON｜`Taiji_Odoo/addons/wuchang_cafe_menu_options/services/menu_batch_governance.py`
- **用途說明**：現行批次預覽與反向回復治理邏輯
- **SHA-256**：`2eac6d8b579376a62fd0db12e947e9acffaac830d6bc8edca469b905992c5af4`

````py
"""Bounded menu previews; uses the existing menu snapshot and candidate rules."""

from .menu_change_governance import MenuChangeGovernanceError, _menu_values, stable_sha256


MAX_BATCH_ITEMS = 100


def build_batch_preview(snapshots, operation, value=None):
    if not isinstance(snapshots, list) or not 1 <= len(snapshots) <= MAX_BATCH_ITEMS:
        raise MenuChangeGovernanceError("BATCH_SIZE_INVALID")
    if operation == "set_price":
        proposed = _menu_values({"list_price": value}, "batch")
    elif operation == "set_categories":
        proposed = _menu_values({"pos_category_ids": value}, "batch")
    elif operation == "pause":
        proposed = {"available_in_pos": False}
    elif operation == "archive":
        proposed = {"active": False, "available_in_pos": False}
    elif operation == "reactivate":
        proposed = {"active": True, "available_in_pos": True}
    else:
        raise MenuChangeGovernanceError("BATCH_OPERATION_INVALID")
    # canonical serialization rejects NaN and infinity as well as invalid prices.
    stable_sha256(proposed)
    rows, seen = [], set()
    for snapshot in snapshots:
        before = _menu_values(snapshot, "before")
        code = before.get("thing_code")
        if not code or code in seen:
            raise MenuChangeGovernanceError("BATCH_IDENTITY_MISSING_OR_DUPLICATE")
        seen.add(code)
        after = {**before, **proposed}
        diff = {key: {"before": before.get(key), "after": after[key]}
                for key in proposed if before.get(key) != after[key]}
        rows.append({"before": before, "after": after, "diff": diff})
    preview = {"schema": "wuchang-menu-batch-preview/1.0", "operation": operation,
               "rows": rows, "changed_count": sum(bool(row["diff"]) for row in rows),
               "product_write": False}
    preview["sha256"] = stable_sha256(preview)
    return preview


def build_reversal_values(before, proposed, current):
    before = _menu_values(before, "before")
    proposed = _menu_values(proposed, "proposed")
    current = _menu_values(current, "current")
    if current != {**before, **proposed}:
        raise MenuChangeGovernanceError("REVERSAL_BASE_CHANGED")
    if "image_sha256" in proposed:
        raise MenuChangeGovernanceError("REVERSAL_IMAGE_PREIMAGE_UNAVAILABLE")
    if not proposed or not set(proposed).issubset(before):
        raise MenuChangeGovernanceError("REVERSAL_PREIMAGE_INCOMPLETE")
    return {key: before[key] for key in proposed}

````

---
## [8] ODOO_MENU_ADDON｜`Taiji_Odoo/addons/wuchang_cafe_menu_options/models/menu_change_request.py`
- **用途說明**：單筆/批次變更申請、責任人核准與反向回復模型
- **SHA-256**：`3b0b3e55d9e1c35f77a18f8974a886bbba877f44b704fcebc9a8c34c109b88be`

````py
"""Human-reviewed remote support changes for one Odoo cafe menu item."""

from __future__ import annotations

import hashlib
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.menu_change_governance import (
    MenuChangeGovernanceError,
    build_menu_change_candidate,
    build_responsible_authorization_event,
)
from ..services.menu_batch_governance import build_reversal_values
from .menu_manager import (
    GOVERNANCE_ADMIN_GROUP,
    REMOTE_SUPPORT_GROUP,
    RESPONSIBLE_GROUP,
    build_human_menu_event_values,
    schedule_rejected_menu_event,
)


_MENU_WORKFLOW_TOKEN = object()


class WuchangCafeMenuChangeRequest(models.Model):
    _name = "wuchang.cafe.menu.change.request"
    _description = "WuChang Cafe Menu Change Request"
    _order = "create_date desc, id desc"

    name = fields.Char(
        default="New Menu Change",
        required=True,
        readonly=True,
        copy=False,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending_responsible_review", "Pending Responsible Review"),
            ("approved", "Approved — Awaiting Explicit Apply"),
            ("applied", "Applied"),
            ("rejected", "Rejected"),
            ("dead_letter", "Dead Letter"),
        ],
        default="draft",
        readonly=True,
        index=True,
        copy=False,
    )
    origin = fields.Selection(
        [
            ("merchant_manager", "Merchant Manager"),
            ("remote_support", "Remote Support"),
        ],
        required=True,
        default="merchant_manager",
        index=True,
        copy=False,
    )
    change_type = fields.Selection(
        [
            ("create", "Create Item"),
            ("update", "Update Item"),
            ("archive", "Archive Item"),
            ("reactivate", "Reactivate Item"),
        ],
        required=True,
        default="update",
    )
    group_batch_id = fields.Many2one(
        "wuchang.member.group.registration.batch",
        string="Merchant Group",
        required=True,
        index=True,
        ondelete="restrict",
        domain="[('business_onboarding_enabled', '=', True), ('business_onboarding_state', '=', 'operational_ready')]",
    )
    company_id = fields.Many2one(
        "res.company",
        related="group_batch_id.menu_company_id",
        readonly=True,
        store=True,
        index=True,
    )
    requester_user_id = fields.Many2one(
        "res.users",
        readonly=True,
        index=True,
        copy=False,
    )
    responsible_reviewer_user_id = fields.Many2one(
        "res.users",
        readonly=True,
        index=True,
        copy=False,
    )
    responsible_person_ref = fields.Char(readonly=True, copy=False)
    product_template_id = fields.Many2one(
        "product.template",
        string="Menu Item",
        index=True,
        ondelete="restrict",
        domain="[('company_id', 'in', [False, company_id])]",
    )
    applied_product_template_id = fields.Many2one(
        "product.template",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )

    change_name = fields.Boolean(default=False)
    proposed_name = fields.Char()
    change_price = fields.Boolean(default=False)
    proposed_list_price = fields.Float(string="Proposed Price")
    change_pos_categories = fields.Boolean(default=False)
    proposed_pos_category_ids = fields.Many2many(
        "pos.category",
        "wuchang_cafe_menu_change_pos_category_rel",
        "request_id",
        "category_id",
        string="Proposed POS Categories",
    )
    change_option_group = fields.Boolean(default=False)
    proposed_option_group_id = fields.Many2one(
        "wuchang.cafe.option.group",
        string="Proposed Option Group",
        ondelete="restrict",
    )
    change_image = fields.Boolean(default=False)
    proposed_image_1920 = fields.Binary(string="Proposed Product Image")
    change_availability = fields.Boolean(default=False)
    proposed_available_in_pos = fields.Boolean(default=True)
    change_active = fields.Boolean(default=False)
    proposed_active = fields.Boolean(default=True)
    support_reason = fields.Text(
        help="Describe the observed problem and intended correction. Do not paste credentials, payment data, or member plaintext."
    )
    responsible_review_note = fields.Text()

    current_snapshot_json = fields.Text(readonly=True, copy=False)
    proposed_values_json = fields.Text(readonly=True, copy=False)
    candidate_packet_json = fields.Text(readonly=True, copy=False)
    current_snapshot_sha256 = fields.Char(readonly=True, index=True, copy=False)
    candidate_sha256 = fields.Char(readonly=True, index=True, copy=False)
    approval_seal_json = fields.Text(readonly=True, copy=False)
    approval_sha256 = fields.Char(readonly=True, index=True, copy=False)
    reviewed_by_user_id = fields.Many2one(
        "res.users", readonly=True, copy=False
    )
    reviewed_at = fields.Datetime(readonly=True, copy=False)
    applied_at = fields.Datetime(readonly=True, copy=False)
    submitted_at = fields.Datetime(readonly=True, copy=False)
    submitted_location_ref = fields.Char(readonly=True, copy=False)
    support_reason_sha256 = fields.Char(readonly=True, copy=False)

    remote_support_direct_write = fields.Boolean(default=False, readonly=True)
    single_account_multi_role = fields.Boolean(default=False, readonly=True)
    formal_pos_order = fields.Boolean(default=False, readonly=True)
    payment_capture = fields.Boolean(default=False, readonly=True)

    _INPUT_FIELDS = {
        "origin",
        "change_type",
        "group_batch_id",
        "product_template_id",
        "change_name",
        "proposed_name",
        "change_price",
        "proposed_list_price",
        "change_pos_categories",
        "proposed_pos_category_ids",
        "change_option_group",
        "proposed_option_group_id",
        "change_image",
        "proposed_image_1920",
        "support_reason",
        "change_availability",
        "proposed_available_in_pos",
        "change_active",
        "proposed_active",
    }
    _PROTECTED_FIELDS = {
        "state",
        "company_id",
        "requester_user_id",
        "responsible_reviewer_user_id",
        "responsible_person_ref",
        "applied_product_template_id",
        "current_snapshot_json",
        "proposed_values_json",
        "candidate_packet_json",
        "current_snapshot_sha256",
        "candidate_sha256",
        "approval_seal_json",
        "approval_sha256",
        "reviewed_by_user_id",
        "reviewed_at",
        "applied_at",
        "submitted_at",
        "submitted_location_ref",
        "support_reason_sha256",
        "remote_support_direct_write",
        "single_account_multi_role",
        "formal_pos_order",
        "payment_capture",
    }

    @api.model_create_multi
    def create(self, vals_list):
        is_remote = self.env.user.has_group(REMOTE_SUPPORT_GROUP)
        is_responsible = self.env.user.has_group(RESPONSIBLE_GROUP)
        if not is_remote and not is_responsible:
            raise UserError(
                _("Only a cafe menu responsible person or remote support operator can create a menu change request.")
            )
        safe_list = []
        for raw_values in vals_list:
            unknown = set(raw_values) - self._INPUT_FIELDS
            if unknown:
                raise UserError(
                    _("The safe menu request does not allow these fields: %s")
                    % ", ".join(sorted(unknown))
                )
            if self._PROTECTED_FIELDS & set(raw_values):
                raise UserError(_("Protected review fields cannot be supplied by the requester."))
            values = dict(raw_values)
            origin = values.get("origin") or (
                "merchant_manager" if is_responsible else "remote_support"
            )
            if origin == "merchant_manager" and not is_responsible:
                raise UserError(_("The merchant-manager action requires the cafe menu responsible-person permission."))
            if origin == "remote_support" and not is_remote:
                raise UserError(_("The remote-support action requires the remote support permission."))
            if origin not in {"merchant_manager", "remote_support"}:
                raise UserError(_("Choose a valid menu change action context."))
            batch = self.env["wuchang.member.group.registration.batch"].browse(
                values.get("group_batch_id")
            ).exists()
            if not batch or batch.business_onboarding_state != "operational_ready":
                raise UserError(_("An operational merchant group binding is required."))
            if not batch.menu_company_id or not batch.responsible_menu_reviewer_user_id:
                raise UserError(_("The merchant group has no menu company or responsible reviewer binding."))
            values.update(
                {
                    "origin": origin,
                    "requester_user_id": self.env.user.id,
                    "responsible_reviewer_user_id": batch.responsible_menu_reviewer_user_id.id,
                    "responsible_person_ref": batch.responsible_person_ref,
                }
            )
            safe_list.append(values)
        clean_context = {key: value for key, value in self.env.context.items()
                         if key not in {"default_" + field for field in self._PROTECTED_FIELDS}}
        return super(WuchangCafeMenuChangeRequest, self.with_context(clean_context)).create(safe_list)

    def write(self, values):
        if self.env.context.get("wuchang_menu_request_internal_write") is _MENU_WORKFLOW_TOKEN:
            return super().write(values)
        unknown = set(values) - self._INPUT_FIELDS - {"responsible_review_note"}
        if unknown:
            raise UserError(
                _("The safe menu request does not allow these fields: %s")
                % ", ".join(sorted(unknown))
            )
        if self._PROTECTED_FIELDS & set(values):
            raise UserError(_("Review state and seal fields can only be changed by workflow actions."))
        for request in self:
            if request.state != "draft":
                if request.state != "pending_responsible_review":
                    raise UserError(_("Completed menu-change evidence is immutable."))
                if set(values) != {"responsible_review_note"}:
                    raise UserError(_("Submitted menu changes are immutable. Create a new request instead."))
                request._assert_responsible_reviewer()
            if request.state == "draft" and request.requester_user_id != self.env.user:
                raise UserError(_("Only the requester can edit a draft menu change."))
            if request.state == "draft" and "origin" in values:
                if values["origin"] == "merchant_manager" and not self.env.user.has_group(RESPONSIBLE_GROUP):
                    raise UserError(_("The merchant-manager action requires the cafe menu responsible-person permission."))
                if values["origin"] == "remote_support" and not self.env.user.has_group(REMOTE_SUPPORT_GROUP):
                    raise UserError(_("The remote-support action requires the remote support permission."))
        if "group_batch_id" in values:
            batch = self.env["wuchang.member.group.registration.batch"].browse(
                values["group_batch_id"]
            ).exists()
            if not batch or batch.business_onboarding_state != "operational_ready":
                raise UserError(_("An operational merchant group binding is required."))
            if not batch.menu_company_id or not batch.responsible_menu_reviewer_user_id:
                raise UserError(_("The merchant group has no menu company or responsible reviewer binding."))
        result = super().write(values)
        if "group_batch_id" in value
````

---
## [9] ODOO_MENU_ADDON｜`Taiji_Odoo/addons/wuchang_cafe_menu_options/views/menu_option_views.xml`
- **用途說明**：現行一卡一商品看板、清單與安全表單視圖
- **SHA-256**：`c9f04e929584dc875bf5750ffc07ca1412c07dc2af8888374e5f799315dd904a`

````xml
<odoo>
    <!-- Merchant-facing product library: one item per card, no full ERP form. -->
    <record id="view_wuchang_cafe_menu_product_search" model="ir.ui.view">
        <field name="name">wuchang.cafe.menu.product.search</field>
        <field name="model">product.template</field>
        <field name="arch" type="xml">
            <search string="搜尋咖啡館菜單">
                <field name="name" string="商品名稱"/>
                <field name="pos_categ_ids" string="POS 分類"/>
                <field name="wuchang_option_group_id" string="客製化規格"/>
                <filter name="active_menu" string="上架中" domain="[('active', '=', True), ('available_in_pos', '=', True)]"/>
                <filter name="paused_menu" string="暫停販售" domain="[('active', '=', True), ('available_in_pos', '=', False)]"/>
                <filter name="archived_menu" string="已封存" domain="[('active', '=', False)]"/>
                <group expand="1" string="分組">
                    <filter name="group_pos_category" string="POS 分類" context="{'group_by': 'pos_categ_ids'}"/>
                    <filter name="group_option" string="客製化規格" context="{'group_by': 'wuchang_option_group_id'}"/>
                </group>
            </search>
        </field>
    </record>

    <record id="view_wuchang_cafe_menu_product_kanban" model="ir.ui.view">
        <field name="name">wuchang.cafe.menu.product.kanban</field>
        <field name="model">product.template</field>
        <field name="arch" type="xml">
            <kanban create="0" class="o_kanban_small_column" records_draggable="0" sample="0">
                <field name="name"/>
                <field name="list_price"/>
                <field name="image_128"/>
                <field name="pos_categ_ids"/>
                <field name="wuchang_option_group_id"/>
                <field name="available_in_pos"/>
                <field name="active"/>
                <field name="w5c_time_state"/>
                <templates>
                    <t t-name="card" class="p-0">
                        <div class="d-flex gap-3 p-3">
                            <field name="image_128" widget="image" options="{'img_class': 'rounded o_image_64_contain'}" alt="商品圖片"/>
                            <main class="flex-grow-1 min-w-0">
                                <div class="d-flex justify-content-between gap-2 align-items-start">
                                    <strong class="fs-5 text-truncate"><field name="name"/></strong>
                                    <span class="fw-bold text-nowrap"><field name="list_price"/></span>
                                </div>
                                <div class="mt-2"><field name="pos_categ_ids" widget="many2many_tags"/></div>
                                <div class="text-muted mt-2" t-if="record.wuchang_option_group_id.value">
                                    客製化：<field name="wuchang_option_group_id"/>
                                </div>
                                <span class="badge text-bg-success mt-2" t-if="record.active.raw_value and record.available_in_pos.raw_value">上架中</span>
                                <span class="badge text-bg-warning mt-2" t-elif="record.active.raw_value">暫停販售</span>
                                <span class="badge text-bg-secondary mt-2" t-else="">已封存</span>
                            </main>
                        </div>
                    </t>
                </templates>
            </kanban>
        </field>
    </record>

    <record id="view_wuchang_cafe_menu_product_list" model="ir.ui.view">
        <field name="name">wuchang.cafe.menu.product.list</field>
        <field name="model">product.template</field>
        <field name="arch" type="xml">
            <list string="咖啡館菜單" create="0" delete="0" duplicate="0" multi_edit="0">
                <header><button name="action_wuchang_menu_batch_preview" type="object" string="批次修改預覽" groups="wuchang_cafe_menu_options.group_wuchang_cafe_menu_responsible"/></header>
                <field name="active" column_invisible="True"/>
                <field name="image_128" widget="image" string="圖片"/>
                <field name="name" string="商品名稱"/>
                <field name="list_price" string="售價"/>
                <field name="pos_categ_ids" widget="many2many_tags" string="POS 分類"/>
                <field name="wuchang_option_group_id" string="客製化規格"/>
                <field name="available_in_pos" string="POS 上架"/>
                <field name="w5c_time_state" string="編碼狀態" optional="hide"/>
            </list>
        </field>
    </record>

    <record id="view_wuchang_cafe_menu_product_form" model="ir.ui.view">
        <field name="name">wuchang.cafe.menu.product.safe.form</field>
        <field name="model">product.template</field>
        <field name="arch" type="xml">
            <form string="單項菜單維護" create="0" edit="0" delete="0" duplicate="0">
                <header>
                    <button name="action_wuchang_menu_request_edit" type="object" string="提出修改並預覽" class="btn-primary" groups="wuchang_cafe_menu_options.group_wuchang_cafe_menu_responsible"/>
                    <button name="action_wuchang_submit_cafe_pos_candidate" type="object" string="送交總場候選" class="btn-primary" invisible="not available_in_pos" confirm="只會送出商品與商家不透明引用，建立 CAFE_POS 候選及總場回執；不建立訂單、付款、發票、會員資料或社區幣交易。" groups="wuchang_cafe_menu_options.group_wuchang_cafe_menu_responsible"/>
                    <button name="action_wuchang_menu_archive" type="object" string="封存商品" class="btn-secondary" invisible="not active" confirm="將建立封存申請供你檢視，尚不修改商品。"/>
                    <button name="action_wuchang_menu_reactivate" type="object" string="重新上架" class="btn-primary" invisible="active and available_in_pos" confirm="將建立重新上架申請供你檢視，尚不修改商品。"/>
                </header>
                <sheet>
                    <field name="active" invisible="1"/>
                    <field name="company_id" invisible="1"/>
                    <field name="currency_id" invisible="1"/>
                    <field name="type" invisible="1"/>
                    <div class="alert alert-info" role="status">
                        一張卡就是一個商品。修改先按「提出修改並預覽」；不再販售請建立封存申請。確認套用前不會改動商品。
                    </div>
                    <div class="d-flex flex-column flex-lg-row gap-4 align-items-start">
                        <field name="image_1920" widget="image" class="oe_avatar" options="{'preview_image': 'image_128', 'convert_to_webp': True}"/>
                        <div class="flex-grow-1 w-100">
                            <label for="name" string="商品名稱"/>
                            <h1><field name="name" placeholder="輸入實際商品名稱"/></h1>
                            <group>
                                <group string="販售資訊">
                                    <field name="list_price" string="售價" widget="monetary" options="{'currency_field': 'currency_id'}"/>
                                    <field name="pos_categ_ids" string="POS 分類" widget="many2many_tags" options="{'no_create': True}"/>
                                    <field name="available_in_pos" string="在 POS 上架"/>
                                </group>
                                <group string="客製化">
                                    <field name="wuchang_option_group_id" string="口味／甜度／溫度規格" options="{'no_create_edit': True}"/>
                                    <div class="text-muted">規格另由「客製化規格」集中管理，避免每個商品重複建立造成店員混亂。</div>
                                </group>
                            </group>
                        </div>
                    </div>
                    <group string="總場追蹤">
                        <field name="w5c_code" string="穩定事物碼" readonly="1"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_wuchang_cafe_menu_products" model="ir.actions.act_window">
        <field name="name">咖啡館菜單</field>
        <field name="res_model">product.template</field>
        <field name="view_mode">kanban,list,form</field>
        <field name="domain">['|', ('available_in_pos', '=', True), ('w5c_domain', '=', 'CAFE')]</field>
        <field name="context">{'active_test': False, 'search_default_active_menu': 1, 'default_available_in_pos': True}</field>
        <field name="search_view_id" ref="view_wuchang_cafe_menu_product_search"/>
        <field name="view_ids" eval="[(5, 0, 0),
            (0, 0, {'view_mode': 'kanban', 'view_id': ref('view_wuchang_cafe_menu_product_kanban')}),
            (0, 0, {'view_mode': 'list', 'view_id': ref('view_wuchang_cafe_menu_product_list')}),
            (0, 0, {'view_mode': 'form', 'view_id': ref('view_wuchang_cafe_menu_product_form')})]"/>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">新增第一個菜單商品</p>
            <p>請由「菜單變更審核」新增真實商品候選，檢視差異後確認套用。</p>
        </field>
    </record>

    <!-- Human-readable remote-support review queue. -->
    <record id="view_wuchang_cafe_menu_change_request_list" model="ir.ui.view">
        <field name="name">wuchang.cafe.menu.change.request.list</field>
        <field name="model">wuchang.cafe.menu.change.request</field>
        <field name="arch" type="xml">
            <list string="菜單變更審核" create="1" delete="0" duplicate="0" decoration-warning="state == 'pending_responsible_review'" decoration-info="state == 'approved'" decoration-success="state == 'applied'" decoration-muted="state in ['rejected', 'dead_letter']">
                <field name="name" string="修正單"/>
                <field name="state" string="狀態"/>
                <field name="origin" string="事件情境"/>
                <field name="change_type" string="動作"/>
                <field name="group_batch_id" string="商家"/>
                <field name="product_template_id" string="商品"/>
                <field name="requester_user_id" string="誰"/>
                <field name="submitted_location_ref" string="哪裡"/>
                <field name="submitted_at" string="何時"/>
            </list>
        </field>
    </record>

    <record id="view_wuchang_cafe_menu_change_request_search" model="ir.ui.view">
        <field name="name">wuchang.cafe.menu.change.request.search</field>
        <field name="model">wuchang.cafe.menu.change.request</field>
        <field name="arch" type="xml">
            <search string="搜尋遠端修正">
                <field name="name"/>
                <field name="group_batch_id"/>
                <field name="product_template_id"/>
                <filter name="pending" string="待負責人審核" domain="[('state', '=', 'pending_responsible_review')]"/>
                <filter name="approved" string="已核准待套用" domain="[('state', '=', 'approved')]"/>
                <filter name="applied" string="已套用" domain="[('state', '=', 'applied')]"/>
                <filter name="rejected" string="已拒絕" domain="[('state', '=', 'rejected')]"/>
            </search>
        </field>
    </record>

    <record id="view_wuchang_cafe_menu_change_request_form" model="ir.ui.view">
        <field name="name">wuchang.cafe.menu.change.request.form</field>
        <field name="model">wuchang.cafe.menu.change.request</field>
        <field name="arch" type="xml">
            <form string="單項菜單修正審核" create="1" delete="0" duplicate="0">
                <header>
                    <button name="action_submit_for_responsible_review" type="object" string="送負責人審核" class="btn-primary" invisible="state != 'draft'" groups="wuchang_cafe_menu_options.group_wuchang_cafe_remote_support,wuchang_cafe_menu_options.group_wuchang_cafe_menu_responsible"/>
                    <button name="action_responsible_approve" type="object" string="核准候選（尚不套用）" class="btn-primary" invisible="state != 'pending_responsible_review'" confirm="請確認已逐項比較修改前與修改後內容。本次只核准候選，不會改動正式菜單；套用仍需同一帳號再次明確確認。" groups="wuchang_cafe_menu_options.group_wuchang_cafe_menu_responsible"/>
                    <button name="action_responsible_apply" type="object" string="再次確認並套用" class="btn-primary" invisible="state != 'approved'
````

---
## [10] ODOO_UI_SUITE｜`Taiji_Odoo/addons/wuchang_ordering_ui_suite/views/management_ui.xml`
- **用途說明**：聊國咖啡重新總店管理中心（靛藍科技/暖米咖啡/墨韻典藏三主題）
- **SHA-256**：`eccf73eec184ee139251dc4496d34f933fc2029aeb3f79c9a10725ba78096e78`

````xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
  <template id="management_ui" name="聊國咖啡重新總店管理中心">
    <t t-call="website.layout">
      <t t-set="additional_title">聊國管理中心 · <t t-esc="suite_name"/></t>
      <main id="wuchang-management-app" class="wc-manager" t-att-data-suite="suite">
        <aside class="wc-side">
          <div class="wc-brand"><span class="wc-mark">聊</span><div><b>重新總店</b><small>MANAGER / 03</small></div></div>
          <nav aria-label="管理功能">
            <button class="is-active" data-panel="overview">營運總覽</button>
            <button data-panel="orders">訂單與通路</button>
            <button data-panel="menu">菜單與價格</button>
            <button data-panel="inventory">庫存</button>
            <button data-panel="eightd">小J・8D 資源判讀</button>
            <button data-panel="community">Google 商家／社群協作</button>
            <button data-panel="devices">音樂／監視資源</button>
          </nav>
          <div class="wc-theme-links">
            <small>管理介面風格</small>
            <a href="/wuchang/ordering/management/a">靛藍科技</a>
            <a href="/wuchang/ordering/management/b">暖米咖啡</a>
            <a href="/wuchang/ordering/management/c">墨韻典藏</a>
          </div>
        </aside>
        <section class="wc-workspace">
          <header class="wc-head"><div><p class="wc-kicker">LOGECOFFEE / ODOO 18</p><h1><t t-esc="suite_name"/>・店家管理</h1></div><div id="wc-sync" class="wc-state is-warn">正在讀取真實狀態</div></header>
          <div class="wc-scope">固定商業歸屬：重新總店／上品食品行（Company 3）；精確 POS 尚未核定，因此正式讀取與寫入均阻塞。外部發佈、播放、音量、錄影下載與權限變更均未授權。</div>
          <section id="wc-panel" aria-live="polite"><div class="wc-loading">連接 Odoo 唯讀資料…</div></section>
        </section>
      </main>
      <script type="text/javascript" src="/wuchang_ordering_ui_suite/static/src/js/management_ui.js"></script>
    </t>
  </template>
</odoo>

````

---
## [11] ODOO_UI_SUITE｜`Taiji_Odoo/addons/wuchang_ordering_ui_suite/static/src/js/management_ui.js`
- **用途說明**：管理中心前端互動與狀態渲染邏輯
- **SHA-256**：`46e4ce355c5dd1865ceb4c120bc43a09a25fe81d4e6ff2d595c835b554514908`

````js
/** @odoo-module **/

(() => {
  "use strict";
  const root = document.getElementById("wuchang-management-app");
  if (!root) return;
  const panel = document.getElementById("wc-panel");
  const sync = document.getElementById("wc-sync");
  let state = null;
  let active = "overview";

  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
  const money = (value) => value == null ? "未判定" : `NT$ ${Number(value).toLocaleString("zh-TW")}`;
  const statusClass = (value) => String(value || "").startsWith("PASS") ? "wc-pass" : "wc-hold";
  const stateLine = (value) => `<span class="wc-pill ${statusClass(value)}">${esc(value || "UNKNOWN")}</span>`;
  const card = (title, value, note) => `<article class="wc-card"><small>${esc(title)}</small><h2>${esc(value)}</h2><p>${esc(note)}</p></article>`;

  async function rpc(path, params = {}) {
    const response = await fetch(path, {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({jsonrpc: "2.0", method: "call", params, id: Date.now()}),
    });
    const body = await response.json();
    if (!response.ok || body.error) throw new Error(body.error?.data?.message || `HTTP ${response.status}`);
    return body.result;
  }

  function overview() {
    const menu = state.menu || {};
    const orders = state.orders || {};
    return `<div class="wc-grid">
      ${card("Odoo 商品映射", `${menu.product_count ?? menu.observed_count ?? 0}/64`, menu.state)}
      ${card("近 7 日訂單", orders.order_count ?? "未判定", `已付款 ${orders.paid_order_count ?? "未判定"} 筆`)}
      ${card("已付款金額", money(orders.paid_amount_total), "未付款訂單不列入收入")}
      ${card("毛利", "未判定", orders.gross_margin_state)}
    </div>
    <div class="wc-section-title"><h2>資料與權威狀態</h2><small>${esc(state.observed_at)} · ${esc(state.timezone)}</small></div>
    <div class="wc-grid two">
      <article class="wc-card"><h3>Odoo 正式資料</h3>${stateLine(menu.state)}<p>範圍 ${esc(state.store_ref)}。畫面只讀，無訂單、付款或票券效果。</p></article>
      <article class="wc-card"><h3>小J AI 總成</h3>${stateLine(state.ai?.state)}<p>本地模型只產候選；總場規則准駁，效果收據才可完成。</p></article>
    </div>`;
  }

  function orders() {
    const data = state.orders || {};
    return `<div class="wc-grid">
      ${card("全部訂單", data.order_count ?? "未判定", "資料期間內 Odoo 訂單")}
      ${card("已付款", data.paid_order_count ?? "未判定", "只計 paid / done / invoiced")}
      ${card("收入", money(data.paid_amount_total), "無跨系統歸因")}
      ${card("未付款", data.unpaid_not_counted_as_revenue ?? "未判定", "不計收入")}
    </div><div class="wc-section-title"><h2>堂食／外帶／外送</h2></div>
    <article class="wc-card">${stateLine(data.sale_mode_state)}<p>用餐方式是訂單層級；沒有已驗證欄位時不由商品或模型推測。</p></article>`;
  }

  function menu() {
    const data = state.menu || {};
    const rows = (data.products || []).slice(0, 64).map((item) => `<tr><td>${esc(item.id)}</td><td>${esc(item.name)}</td><td>${esc(item.category)}</td><td>${money(item.price)}</td><td>${esc((item.groups || []).join(", ") || "無")}</td></tr>`).join("");
    if (!rows) return `<div class="wc-empty">${esc(data.state)}；未精確映射 64/64 前不顯示猜配商品。</div>`;
    return `<div class="wc-section-title"><h2>QuickClick 64 精確來源映射</h2>${stateLine(data.state)}</div><div class="wc-card"><table class="wc-table"><thead><tr><th>來源 ID</th><th>商品</th><th>分類</th><th>Odoo 售價</th><th>非變體屬性群組</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function inventory() {
    const data = state.inventory || {};
    const rows = (data.items || []).map((item) => `<tr><td>${esc(item.source_product_id)}</td><td>${esc(item.name)}</td><td>${esc(item.qty_available)}</td><td>${esc(item.forecasted_qty)}</td></tr>`).join("");
    return `<div class="wc-section-title"><h2>統一庫存唯讀檢視</h2>${stateLine(data.state)}</div><article class="wc-card"><p>${esc(data.low_stock_state)}</p>${rows ? `<table class="wc-table"><thead><tr><th>來源 ID</th><th>商品</th><th>現有量</th><th>預測量</th></tr></thead><tbody>${rows}</tbody></table>` : "沒有可驗證資料"}</article>`;
  }

  function eightd() {
    const data = state.eightd || {};
    const rows = (data.coordinates || []).map((item) => `<tr><td>${esc(item.object)}</td><td>${esc(item.version)}</td><td>${esc(item.time)}</td><td>${esc(item.state)}</td><td>${item.fresh ? "是" : "否"}</td><td>${item.authority_allowed ? "範圍內" : "未授權"}</td><td>${esc(item.source_ref)}</td></tr>`).join("");
    return `<div class="wc-section-title"><h2>8D 單一耦合場資源定位</h2>${stateLine(data.state)}</div>
      <article class="wc-card"><p>觀測端：03 店家管理節點；目標端：${esc(data.target_ref)}。區分存在、載入、可呼叫、效果驗收；過時或缺證據不得當作現況。</p>
      <table class="wc-table"><thead><tr><th>資源</th><th>版本</th><th>觀測時間</th><th>狀態</th><th>時效</th><th>授權</th><th>證據座標</th></tr></thead><tbody>${rows}</tbody></table></article>
      <div class="wc-section-title"><h2>候選動作</h2></div><article class="wc-card"><p>目前沒有動作被執行。任何搜尋、設備控制、外部發佈或 Odoo 寫入，須取得對應授權並由原底層執行器回傳效果收據。</p><button class="wc-disabled" disabled>等待總場授權與執行器綁定</button></article>`;
  }

  function connector(title, data, details) {
    return `<article class="wc-card"><h3>${esc(title)}</h3>${stateLine(data?.state)}<p>${esc(details)}</p><p>資源：${esc(data?.account_resource_ref || "未取得")}<br/>最後同步：${esc(data?.last_sync || "未取得")}<br/>權限已核：${data?.permissions_verified ? "是" : "否"}</p><button class="wc-disabled" disabled>外部寫入需另行核准</button></article>`;
  }

  function community() {
    return `<div class="wc-grid two">
      ${connector("Google 商家檔案", state.google_business, "商家資訊、評論、貼文與績效只在精確商家資源及唯讀權限已驗證後顯示。")}
      ${connector("平台中立社群協作", state.social_collaboration, "貼文草稿、協作任務與審核；不冒充平台原生排程，不自行新增平台。")}
    </div><div class="wc-section-title"><h2>協作邊界</h2></div><article class="wc-card"><p>咖啡店自然人商家帳號與協會 Workspace 分離。Google 指標與 Odoo 銷售只並列，沒有歸因證據不得宣稱貼文帶來營收。</p></article>`;
  }

  function devices() {
    return `<div class="wc-grid two">
      ${connector("店內音樂資源", state.music, "只顯示既有設備／服務與可驗證控制接口；播放、音量變更尚未授權。")}
      ${connector("NVR／指定攝影機", state.nvr, "僅店長管理面可見。憑證綁定與新鮮畫格收據未閉合時，不展示、下載或外傳影像。")}
    </div><div class="wc-section-title"><h2>總場執行閉環</h2></div><article class="wc-card"><p>小J先定位資源與授權範圍，總場准駁後交原執行器；命令回應不等於現場效果，必須回收設備或 NVR 效果收據。</p></article>`;
  }

  const renderers = {overview, orders, menu, inventory, eightd, community, devices};
  function render() { panel.innerHTML = (renderers[active] || overview)(); }
  root.querySelectorAll("[data-panel]").forEach((button) => button.addEventListener("click", () => {
    root.querySelectorAll("[data-panel]").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active"); active = button.dataset.panel; render();
  }));

  rpc("/wuchang/ordering/management/state").then((result) => {
    state = result;
    sync.textContent = `${result.state} · ${result.observed_at}`;
    sync.className = `wc-state ${String(result.state).startsWith("PASS") ? "is-pass" : "is-warn"}`;
    render();
  }).catch((error) => {
    sync.textContent = "讀取失敗"; sync.className = "wc-state is-warn";
    panel.innerHTML = `<div class="wc-empty">${esc(error.message)}；不得把失敗標為完成。</div>`;
  });
})();

````

---
## [12] ODOO_UI_SUITE｜`Taiji_Odoo/addons/wuchang_ordering_ui_suite/services/live_odoo_projection.py`
- **用途說明**：M387676 64商品白名單投影與伺服器端客製化計價引擎
- **SHA-256**：`41896bf2a2df3b13c0e66147e391b0bb87d2b51112257ac099a8b6d8fd29295a`

````py
"""Read-only Odoo projection for the three preserved ordering designs.

The QuickClick snapshot is used only as the immutable 64-source whitelist.
Names, prices, categories and option deltas are projected from the bound Odoo
records.  A partial or duplicate mapping fails closed; it is never repaired by
name matching.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from typing import Any

from odoo import fields
from odoo.tools import file_open


STORE_BINDING = {
    "company_id": 3,
    "company_name": "上品食品行",
    # Founder intent fixes the merchant company, but no current pos.config is
    # proven to be the Chongxin-HQ POS.  POS 2 belongs to the association and
    # POS 3 is only named "餐廳"; neither may be promoted by inference.
    "pos_config_id": None,
    "pos_config_name": "上品聊國咖啡館 重新總店",
    "store_ref": "store:liaoguo-chongxin-hq",
    "quickclick_menu_id": "M387676",
}
POS_CONFIG_PARAMETER = "liaoguo.chongxin.pos_config_id"


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=1)
def source_contract() -> dict[str, Any]:
    path = "wuchang_ordering_ui_suite/static/src/data/quickclick_web_data.json"
    with file_open(path, "r") as handle:
        data = json.load(handle)
    identity_path = "wuchang_ordering_ui_suite/static/src/data/SOURCE_TO_ODOO_IDENTITY_REVIEW.json"
    with file_open(identity_path, "r") as handle:
        identity = json.load(handle)
    web_by_source = {
        str(item.get("sourceProductId")): item for item in (data.get("products") or [])
    }
    products = []
    for item in identity.get("items") or []:
        source_id = str(item.get("source_product_id") or "")
        products.append(
            web_by_source.get(source_id)
            or {
                "sourceProductId": source_id,
                "name": item.get("source_product_name"),
                "price": item.get("source_base_price"),
                "category": item.get("source_category"),
                "optionGroupIds": item.get("source_option_group_ids") or [],
            }
        )
    source_ids = [str(item.get("sourceProductId") or "") for item in products]
    if len(source_ids) != 64 or len(set(source_ids)) != 64 or any(not item for item in source_ids):
        raise ValueError("QUICKCLICK_64_SOURCE_CONTRACT_INVALID")
    data["allProducts"] = products
    return data


def configured_pos_config_id(env) -> int | None:
    """Read the separately authorized target without guessing an existing POS."""

    raw = env["ir.config_parameter"].sudo().get_param(POS_CONFIG_PARAMETER, "")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def binding_receipt(env) -> dict[str, Any]:
    company = env["res.company"].sudo().browse(STORE_BINDING["company_id"]).exists()
    pos_config_id = configured_pos_config_id(env)
    pos_target_declared = isinstance(pos_config_id, int)
    pos = (
        env["pos.config"].sudo().browse(pos_config_id).exists()
        if pos_target_declared
        else env["pos.config"].browse()
    )
    checks = {
        "company_exists": bool(company),
        "company_name_matches": bool(company and company.name == STORE_BINDING["company_name"]),
        "pos_target_declared": pos_target_declared,
        "pos_exists": bool(pos),
        "pos_name_matches": bool(pos and pos.name == STORE_BINDING["pos_config_name"]),
        "pos_company_matches": bool(pos and pos.company_id.id == STORE_BINDING["company_id"]),
    }
    if not checks["company_exists"] or not checks["company_name_matches"]:
        state = "HOLD_EXACT_COMPANY_BINDING_MISMATCH"
    elif not pos_target_declared:
        state = "HOLD_EXACT_POS_CONFIG_TARGET_REQUIRED"
    else:
        state = "PASS_EXACT_CHONGXIN_BINDING" if all(checks.values()) else "HOLD_EXACT_POS_BINDING_MISMATCH"
    resolved_binding = {**STORE_BINDING, "pos_config_id": pos_config_id}
    material = {"binding": resolved_binding, "checks": checks}
    return {
        "state": state,
        "store_ref": STORE_BINDING["store_ref"],
        "binding": resolved_binding,
        "checks": checks,
        "receipt_ref": "sha256:" + _canonical_sha256(material),
        "database_write": False,
    }


def _question_projection(question) -> dict[str, Any]:
    options = []
    for item in question.item_ids.filtered("active").sorted(lambda row: (row.sequence, row.id)):
        option_ref = item.quickclick_item_code or f"odoo-option-item:{item.id}"
        options.append(
            {
                "label": item.display_name or item.name,
                "delta": float(item.price_delta or 0.0),
                "id": option_ref,
                "option_ref": option_ref,
            }
        )
    return {
        "name": question.display_name or question.name,
        "required": bool(question.required),
        "selection_mode": question.selection_type,
        "question_ref": question.quickclick_question_code or f"odoo-option-question:{question.id}",
        "options": options,
    }


def _group_projection(group) -> dict[str, Any]:
    return {
        "group_ref": group.code,
        "name": group.name,
        "questions": [
            _question_projection(question)
            for question in group.question_ids.filtered("active").sorted(lambda row: (row.sequence, row.id))
        ],
    }


def _integer_twd(value: float | int | Decimal) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def menu_projection(env) -> dict[str, Any]:
    binding = binding_receipt(env)
    if not binding["state"].startswith("PASS"):
        return {**binding, "formal_effect": False}

    contract = source_contract()
    expected = [str(item["sourceProductId"]) for item in contract["allProducts"]]
    products = env["product.template"].sudo().with_company(STORE_BINDING["company_id"]).search(
        [
            ("quickclick_menu_id", "=", STORE_BINDING["quickclick_menu_id"]),
            ("quickclick_product_id", "in", expected),
            ("active", "=", True),
        ]
    )
    by_source: dict[str, list[Any]] = {}
    for product in products:
        by_source.setdefault(str(product.quickclick_product_id or ""), []).append(product)
    missing = [source_id for source_id in expected if source_id not in by_source]
    duplicates = [source_id for source_id, rows in by_source.items() if len(rows) != 1]
    if missing or duplicates or len(products) != 64:
        material = {
            "expected_count": 64,
            "observed_count": len(products),
            "missing": missing,
            "duplicates": duplicates,
            "binding_receipt_ref": binding["receipt_ref"],
        }
        return {
            "state": "HOLD_QUICKCLICK_64_EXACT_MAPPING_REQUIRED",
            "store_ref": STORE_BINDING["store_ref"],
            "expected_count": 64,
            "observed_count": len(products),
            "missing_source_product_ids": missing,
            "duplicate_source_product_ids": duplicates,
            "source_contract_sha256": contract["source"]["sha256"],
            "projection_receipt_ref": "sha256:" + _canonical_sha256(material),
            "formal_effect": False,
            "database_write": False,
        }

    ordered = [by_source[source_id][0] for source_id in expected]
    categories: list[str] = []
    group_records: dict[str, Any] = {}
    product_rows = []
    for product in ordered:
        category = product.quickclick_raw_category or (
            product.pos_categ_ids[:1].name if product.pos_categ_ids else "未分類"
        )
        if category not in categories:
            categories.append(category)
        group = product.wuchang_option_group_id
        if group:
            group_records[group.code] = group
        product_rows.append(
            {
                "id": str(product.quickclick_product_id),
                "odoo_product_template_id": product.id,
                "name": product.name,
                "price": _integer_twd(product.list_price),
                "category": category,
                "groups": [group.code] if group else [],
                "image_url": f"/web/image/product.template/{product.id}/image_512",
            }
        )

    groups = {
        code: _group_projection(group)["questions"]
        for code, group in sorted(group_records.items())
    }
    projection_material = {
        "binding_receipt_ref": binding["receipt_ref"],
        "source_contract_sha256": contract["source"]["sha256"],
        "products": product_rows,
        "groups": groups,
    }
    return {
        "state": "PASS_ODOO_MENU_PROJECTION",
        "store_ref": STORE_BINDING["store_ref"],
        "menu_id": STORE_BINDING["quickclick_menu_id"],
        "source_sha256": contract["source"]["sha256"],
        "observed_at": fields.Datetime.now().isoformat(),
        "categories": categories,
        "products": product_rows,
        "groups": groups,
        "product_count": len(product_rows),
        "projection_receipt_ref": "sha256:" + _canonical_sha256(projection_material),
        "formal_effect": False,
        "database_write": False,
    }


def staff_pos_payload(projection: dict[str, Any]) -> dict[str, Any]:
    categories = list(projection["categories"])
    products = []
    size_data: dict[str, list[list[Any]]] = {}
    for index, product in enumerate(projection["products"]):
        products.append(
            {
                "key": index,
                "source_product_id": product["id"],
                "name": product["name"],
                "category": categories.index(product["category"]),
                "price": product["price"],
                "group": product["groups"][0] if product["groups"] else "",
            }
        )
    for group_ref, questions in projection["groups"].items():
        for question in questions:
            labels = {str(item["label"]).upper() for item in question["options"]}
            if labels & {"S", "M", "L"}:
                size_data[group_ref] = [
                    [item["label"], item["delta"]] for item in question["options"]
                ]
                break
    return {
        "categories": categories,
        "products": products,
        "size_data": size_data,
        "meta": {
            "source": "Odoo Company 3 / exact POS pending QuickClick projection",
            "source_sha256": projection["source_sha256"],
            "status": projection["state"],
            "projection_receipt_ref": projection["projection_receipt_ref"],
            "price_policy": "server-projected base and option deltas; no variant products",
        },
    }


def price_projection(env, payload: dict[str, Any]) -> dict[str, Any]:
    projection = menu_projection(env)
    if projection.get("state") != "PASS_ODOO_MENU_PROJECTION":
        return projection
    product_ref = str(payload.get("product_ref") or "")
    quantity = payload.get("quantity", 1)
    option_refs = payload.get("option_refs") or []
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1 or quantity > 30:
        return {"state": "HOLD_QUANTITY_OUT_OF_RANGE", "formal_effect": False}
    if not isinstance(option_refs, list) or any(not isinstance(item, str) for item in option_refs):
        return {"state": "HOLD_OPTION_REFS_ARRAY_REQUIRED", "formal_effect": False}
    product = next((row for row in projection["products"] if row["id"] == product_ref), None)
    if not product:
        return {"state": "HOLD_PRODUCT_OUTSIDE_QUICKCLICK_64", "formal_effect": False}

    questions = []
    for group_ref in product["groups"]:
        questions.extend(projection["groups"].get(group_ref, []))
    allowed: dict[str
````

---
