# Taiji_Hub Agent Rules

These rules are repository gates for Codex and other agents working in W7TP / XiaoJ / GTS / IGC. They bind project work in this repo before local preference, UI convenience, or generic agent patterns.

## Direct Shortest Path Rule

This repo's agent work must follow the direct shortest path.

Do not convert W7TP, XiaoJ, Five-in-One, 8D Packet, Member-Owned Sidebar XiaoJ, No-Plaintext Context, BYOK, or Cloud Blind Compute into an ordinary UI, ordinary agent, ordinary extension, ordinary SaaS workflow, generic chatbot, or browser automation project.

The work must preserve W7TP / XiaoJ as a generative transmission system: state is encoded, coordinated, hashed, packetized, transferred, verified, reconstructed, evidenced, and only then acted upon.

## Generative Transfer Priority Gate

If a task involves any of the following:

- XiaoJ member system
- 8D packet
- Member-Owned Sidebar XiaoJ
- browser-driving AI
- Cloud Blind Compute
- No-Plaintext Context
- BYOK / key_ref / api_ref
- merchant / committee API_ref
- Five-in-One deployment

and `W3_GENERATIVE_TRANSFER_DEPLOY` does not yet exist or is not yet indexed, the next step must be:

`W3_GENERATIVE_TRANSFER_DEPLOY`

Do not jump to these before Generative Transfer Deploy is complete and indexed by the Master Deploy Index:

- Browser Action Bus
- UI Scaffold
- Context Broker
- Key/API Broker
- Avatar Spec
- Connector Spec

## Main Chain Rule

All next-step ordering must check the main chain first:

State
-> Coordinate
-> Hash
-> Packet
-> Generative Transfer
-> Verify
-> Reconstruct
-> Evidence
-> Action

If a proposed next step is not on this main chain, output:

`STATE=HOLD_MAIN_CHAIN_DEVIATION`

## Redteam Rule

Redteam is not a blocker.

Redteam work exists to:

- find risk;
- set boundaries;
- produce safe one-paste paths;
- advance the main trunk.

Redteam must not use generic compliance review to indefinitely postpone core generative transfer.

Safety must identify the safe shortest path; it must not be used as a reason to slow or block the main trunk.

## No Detour Rule

Do not skip Generative Transfer because a UI seems more intuitive, an Action Bus seems safer, or a Broker seems more engineered.

If the 8D Schema SDK is complete and Generative Transfer is not complete, the fixed next step is Generative Transfer Deploy.

## Required Next Step Chain

Every next step must preserve this sequence:

State -> Coordinate -> Hash -> Packet -> Generative Transfer -> Verify -> Reconstruct -> Evidence -> Action

## Output Rule

Codex final responses for this repo must be minimal:

- STATE
- RUN_ID
- HEAD_BEFORE
- HEAD_AFTER
- files changed
- verifier result
- git status
- HOLD reason if any

## Founder Canonical V2.3 Hard Gate

- `CURRENT_FOUNDER_CANONICAL_BASELINE=2.3`.
- W7TP V2.1 is historical/quarantined evidence only. It must not be installed, invoked, started, exposed, packetized, transmitted, or accepted as the current canonical runtime.
- Before any W7TP install, deploy, start, send, receive, reconstruct, or projection action, bind the action to verified V2.3 canonical, pointer, lineage, receipt, and D8 authority evidence. If any binding is absent or a live component reports V2.1, stop with `HOLD_CANONICAL_VERSION_MISMATCH`.
- Sender/receiver mutual agreement, service health, `PASS_RECEIVED`, or exact-byte reconstruction cannot override this version gate.
- Accountability reference: `runtime/total_field/gt_definition_drift/GTP_ACCOUNTABILITY_VERSION_DRIFT_20260912T200131Z/ACCOUNTABILITY_INCIDENT.json`.

## 已完成工作沿用硬閘（Completed Work Reuse Hard Gate）

進行任何搜尋、掃描、盤點、發現、重播、重構或提出替代 `NEXT` 之前，
必須先從目前任務、同日任務／對話紀錄、既有執行編號及成果／證據座標，
建立以下內部欄位：

- `PRIOR_RESULT_STATUS`
- `PRIOR_RUN_ID`
- `PRIOR_RESULT_REF`
- `PRIOR_SCOPE_ID`
- `REQUESTED_SCOPE_ID`
- `SCOPE_RELATION`
- `DELTA_TRIGGER`
- `REPEAT_AUTHORIZATION`
- `OUTPUT_POLICY`
- `DATA_KIND`
- `CONTENT_OUTPUT_AUTHORIZATION`

開始取得資料前，必須把這些欄位交給
`scripts/verify/verify_completed_work_reuse_gate.sh` 判定。判定為沿用或暫停時，
禁止再次取得資料；只有「新階段通過」或「已授權重做」才能執行。

若相同意圖與作用域已有完成或有限範圍完成的成果，必須直接沿用，且只能從
其尚未解決的邊界繼續；禁止重跑已完成的資料取得階段。使用者明確表示工作
已做過時，本規則是不可略過的硬閘。

`SCOPE_RELATION` 必須明確區分：

- `EXACT`：先前成果與目前要求的作用域完全相同；
- `PRIOR_SUBSET`：先前成果只是目前要求的一部分；
- `DISJOINT`：兩者沒有重疊；
- `UNKNOWN`：無法證明兩者關係。

若為 `PRIOR_SUBSET`，必須保留並沿用已完成部分，只能繼續未覆蓋範圍，輸出：

`STATE=CONTINUE_UNCOVERED_SCOPE_ONLY`

不得把「有限範圍完成」寫成「全系統完成」，也不得為了補齊全系統而重掃已完成
的節點、帳號、來源或時間範圍。

合法的 `DELTA_TRIGGER` 僅限：

- 使用者明確要求重做；
- 較新的 Founder／Total Field 權威決定使原結果失效；
- 直接觀察到來源在原結果時間之後發生變更；
- 原驗證器對完全相同的要求範圍失敗或未完成。

記憶尚未建立索引、切換任務／對話、上下文壓縮、代理交接，或代理自己忘記
既有路徑，都不構成變更理由。必須找回並沿用原成果。若不重做就無法找回其
座標，必須停止並輸出：

`STATE=HOLD_PRIOR_RESULT_COORDINATE_REQUIRED`

既有成果可沿用時，輸出：

`STATE=REUSE_PRIOR_COMPLETED_WORK`

限定範圍沒有命中，不等於全域不存在，也不構成擴大或改用其他來源重新搜尋的
授權。即時座標驗證可以偵測飄移，但不得暗中重跑已完成的內容搜尋。除非
`DELTA_TRIGGER` 與 `REPEAT_AUTHORIZATION` 都明確且有效，`NEXT` 不得再次指定
已完成階段。

違反本閘一律分類為：

`ERROR_DUPLICATE_COMPLETED_WORK`

並立即關閉動作閘，不得以搜尋結果有價值、記憶未更新或需要再次確認為理由
繼續執行。

## 技能優先執行硬閘

接受任何命令後，第一件事必須是理解命令意圖，並以當前可用技能的名稱、說明與
適用邊界判斷：是否存在能完整或部分完成命令的技能。此判斷必須發生在搜尋、
掃描、規劃、直接工具呼叫或修改之前。

內部必須先建立：

- `SKILL_MATCH_STATUS`
- `MATCHED_SKILLS`
- `SELECTED_SKILLS`
- `SKILL_CAN_COMPLETE`
- `SKILL_READ_COMPLETE`
- `SKILL_EXECUTION_REQUIRED`

只要存在適用技能：

1. 必須選用全部與命令直接相關的技能；
2. 必須完整讀取每個被選技能的 `SKILL.md`；
3. 必須依技能定義執行其可完成的部分；
4. 不得以直接工具、一般模型能力、較熟悉的舊流程或自行設計流程繞過技能；
5. 技能只能完成部分時，先使用技能完成該部分，再對精確缺口採用最小補充能力；
6. 使用者明確指定技能時，該技能缺失或不可讀必須停止並回報，不得假裝使用。

開始任務動作前，必須通過：

`scripts/verify/verify_skill_first_gate.sh`

若有適用技能但未選用、未完整讀取或未依技能執行，一律輸出：

`STATE=HOLD_APPLICABLE_SKILL_NOT_USED`

工具仍是技能後台的執行能力。使用技能不等於禁止工具；禁止顯示原始工具輸出
也不等於禁止使用工具。

## 人工智慧對話資料輸出硬閘

「閱讀、索引、連結、盤點所有人工智慧對話」預設且強制採用：

`OUTPUT_POLICY=METADATA_ONLY`

且必須使用：

`REQUIRED_SKILL=account-ai-conversation-governance`

除非使用者在目前命令明確要求輸出對話正文，否則工具輸出、進度回報、證據檔與
最終回答都不得顯示對話正文。只可輸出來源座標、人工智慧身分、節點、數量、
時間範圍、雜湊、去重狀態、覆蓋缺口與治理關係。

當 `DATA_KIND=AI_CONVERSATION` 時，若 `OUTPUT_POLICY` 不是 `METADATA_ONLY`，
必須同時存在 `CONTENT_OUTPUT_AUTHORIZATION=true`；否則立即輸出
`STATE=HOLD_CONTENT_OUTPUT_NOT_AUTHORIZED`，不得讀出或顯示正文。

本帳號已明確要求的全域作用域是「全系統、本帳號所轄全部人工智慧」，不得縮減
成目前節點、本機 Codex、taiji01、MSI 或任何單一供應商後宣告完成。無法接觸的
來源必須列為精確覆蓋缺口，不得以局部成功代替。

「本帳號所轄」同時包含個人空間，以及本帳號加入、擁有或管理的組織／團隊／
企業工作空間。帳號相同不等於空間相同；個人來源不得替代組織空間來源。若組織
空間存在但身分或座標未解析，必須輸出
`HOLD_ACCOUNT_ORGANIZATION_SPACES_UNRESOLVED`，不得宣告全系統完成。

本類任務必須同時使用該技能的三項後台能力：

- `config/account_ai_sources.json`：全系統本帳號人工智慧來源清單；
- `scripts/inventory_metadata.py`：只產生中繼資料收據的後台解析器；
- `scripts/verify_coverage.py`：拒絕以局部覆蓋宣告全系統完成的覆蓋驗證器。

組織空間尚未解析時，固定輸出 `HOLD_ACCOUNT_ORGANIZATION_SPACES_UNRESOLVED`；
組織空間已解析但來源清單仍為 `OPEN` 時，輸出
`HOLD_FULL_SYSTEM_SOURCE_REGISTRY_OPEN`。只有
來源清單已有權威封閉證據、全部已登記來源完成且無覆蓋缺口，才能輸出
`COMPLETE_ALL_SYSTEM_ACCOUNT_AI`。能力自我測試只能使用合成對話，不得重讀既有
taiji01、MSI 或其他已完成來源。
