---
name: w7tp-8d-adi-change-to-closure
description: 將 W7TP／8D ADI V2.3 變更從總場事實上下文、因果依賴、隔離驗證、D8 正式送審、必要人審、精確執行、效果重驗直到工作帳本封口統一成固定流程。適用「變更送審推送」、「完成未結工作」、「工作閉環」，禁止把 GitHub PR 等同 D8 送審。
---

# W7TP／8D ADI V2.3 — 變更到工作閉環

**定位：** 現有工作治理能力的協調技能，不是第二套總場或 D8 裁決者。8D ADI 是八合一耦合**單一動態狀態場**，不是八步流程。D1 意圖、D2 狀態、D3 時空座標、D4 事實證據、D5 執行政策、D6 生成式狀態傳輸（GST）、D7 風險隔離、D8 封套權威應同時約束同一工作。Git diff 不是 D6，PR、Git commit、模型回答、測試通過與一般收據都不是 D8 權威。

## 固定任務生命週期

1. **BOUND（目標綁定）：** 取得創辦人最新目標、預期成果及禁止效果；沿 taiji01 的 `ACTIVE_W7TP_CANONICAL_POINTER.json`、`ACTIVE_PRODUCT_SYSTEM_ROOT_POINTER.json` 核對現行 V2.3；針對**唯一 TASK_ID**，透過 `tools/w7tp_bridge_dynamic_context_transport_v1.py` 與 `tools/total_field_dynamic_context_pull.py` 取得當次 Dynamic Context（動態上下文）。讀取 `state/WORK_LEDGER.json`、`state/ACTION_LEDGER.json` 和 `state/CURRENT_CONVERSATION_CHECKPOINT.json`，檢查雜湊及時序；舊檢查點不得覆蓋較新事實。查核失敗 `HOLD_CONTEXT`。
2. **LOCALIZED（ADI 定位與因果依賴）：** 本地小J先理解「想要什麼、成果應長什麼樣子」並提出候選；總場依既有事實、D3 座標、證據、依賴與風險定位缺項。每個變更綁定 `TASK_ID + SOURCE_SHA + TARGET_COORDINATE + DEPENDENCIES + ACCEPTANCE`；只追蹤受影響範圍，不以大模型廣泛猜測代替 ADI 索引。跨任務衝突則 `HOLD`。
3. **ISOLATED（隔離來源）：** `git status / diff / fetch` 唯讀盤點，更新遠端參照；從最新遠端基座建立獨立 review worktree（審查工作樹），只複製精確來源與必須的測試；比對來源 SHA-256。排除巢狀 worktree、壓縮候選、私密資料、運行狀態符號連結及無關任務。**禁止 `git add .`、reset 或清除原工作樹**。
4. **VERIFIED（工程與反證）：** 在隔離工作樹執行必要語法／安全／單元／系統測試，以及紅隊反證、回復與失敗路徑。使用既有 `tools/w7tp_commit_envelope_gate.py`、`tools/d8_codex_preflight_gate.py` 和 `tools/total_field/w7tp_worktree_index_review_successor_entrypoint.py` 適用的契約；任何 `HOLD` 必如實保留，不得改壞 V2.3 定義換取測試通過。D4 測試證據不等於 D8。
5. **REVIEW_REQUESTED（總場正式送審）：** 實際向既有 **taiji01 D8 主管理入口**送入綁定 `TASK_ID / exact Git HEAD / staged hashes / 目標 / 前像 / 依賴 / 風險 / TTL / 效果類別 / D4` 的審查請求，並取得該入口**已受理的 request_id 與收據**。根據請求類型重用 `tools/total_field/w7tp_d8_reviewer_entrypoint.py` 或 `w7tp_static_review_entrypoint.py` 等既有能力；不得推定特定審查器授權其契約以外的效果。**GitHub PR、Draft、審查請求檔、Git push 不代表 D8 已受理**。
6. **DECIDED（D8 正式裁決）：** 查核回傳的正式 `D8_DECISION_RECEIPT`，確定範圍、SHA、身分、一次性、TTL、效果類別與必要自然人核可完全相符。無收據、裁決 `HOLD / BLOCK`、任一依賴不完整時，後續正式效果不得執行。破壞、財務、權限擴張、正式部署、身分根簽發、撤銷／復原、正典升格應維持自然人核可。
7. **EXECUTED（作用執行）：** 僅在授權範圍內交由現有工具完成；必有 preimage（前像）、冪等鍵、rollback（回復）、時效及執行證據。使用者明確要求 Git 推送時，可以建立**隔離候選 PR**並非強制推送，但只有 `GIT_DRAFT_ONLY`，不能宣稱正式送審、核准或部署；正式變更必依適用 D8 效果許可。禁止自動合併主線、重啟 Odoo 或執行交易。
8. **REOBSERVED（作用重驗）：** 重讀遠端 SHA、PR 真實狀態、服務狀態及必要端對端效果；以最新有效 D4 對照 D1 完成條件。檔案存在、測試 PASS、PR `open`、commit 存在、服務在線，均不能單獨宣稱工作完成。
9. **CLOSED（帳本閉環）：** 使用既有 `core/execution_continuity.py`、`core/work_ledger.py`、`core/intent_continuity.py`，更新逐項 Action Ledger（動作帳本）與實際效果；**所有原本完成條件及依賴都驗證成立**後才將 Work Ledger（工作帳本）標 DONE 並封口，更新當前檢查點。否則保持 `HOLD`／`BLOCKED` 和唯一 `NEXT_ACTION`。DONE 封口不得偷偷重開。

以上九個標籤是**操作狀態的生命週期**，不是 D1→D8 的維度順序。允許不同工作原胞並行，但不得共用模糊任務引用、未核定權威或失效驗證。

## 不變條件

- `REVIEW_REQUESTED` 必有正式總場受理 ID；`GIT_DRAFT_ONLY` 絕對不等於 `REVIEW_REQUESTED`。
- `DECIDED` 必有該作用範圍的正式 D8 收據；`EXECUTED` 必有允許的作用種類與效果收據。
- `CLOSED` 必滿足最初 D1 的完成條件；不能只因 Git 推送或審查候選建立就結案。
- 工作／動作帳本是 D2/D4 延續證據，不授權重跑；Process（程序）中斷不等於可以重新執行。已結案的任務重新開啟要有明確權威與前次封套。
- GitHub reviewer（程式碼審查者）與創辦人／總場權威並非同義；不能模擬簽章或自行補建授權收據。
- 不必要外部防禦不能擴張為核心內部瓶頸；仍保留 D8 權威、憑證及明文治理。

## 固定輸出與驗證器

每次回報：`TASK_ID / D1_DESIRED_RESULT / CURRENT_STAGE / D3_TARGET / D4_EVIDENCE_REFS / GIT_HEAD / D8_REQUEST_ID / D8_DECISION_RECEIPT / HUMAN_APPROVAL / ACTION_RECEIPT / OBSERVED_EFFECT / BLOCKERS / NEXT_ACTION`。

`python3 capabilities/w7tp-8d-adi-change-to-closure/scripts/validate_flow.py --input <state.json>` 驗證最小狀態／收據欄位，但**不簽署 D8、不送出審查、不執行效果**。用 `--selftest` 跑正反例。範例：`references/example.json`。

對已建立 PR #26：`git_state = GIT_DRAFT_ONLY`，`d8_review_state = NOT_SUBMITTED`，`effect_state = NO_EFFECT`；來源及專項封套 `HOLD`，必須沿現有 D8 送審通道補齊，不因本技能存在即當成完成。

## 器官參照

`capabilities/w7tp-deterministic-effect-gate/SKILL.md`、`capabilities/w7tp-execution-evidence-lifecycle/SKILL.md`、`capabilities/w7tp-bounded-delegation-chain/SKILL.md`、`core/work_ledger.py`、`core/execution_continuity.py`、`core/intent_continuity.py`、`tools/w7tp_bridge_dynamic_context_transport_v1.py`、`tools/total_field/w7tp_d8_reviewer_entrypoint.py`、`tools/total_field/w7tp_static_review_entrypoint.py`、`tools/total_field/w7tp_worktree_index_review_successor_entrypoint.py`、`tools/w7tp_commit_envelope_gate.py`。
