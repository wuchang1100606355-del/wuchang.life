# W7TP 系統意圖場建構落地流程 V1 候選計畫

狀態：`CANDIDATE_PLAN_ONLY`

目前決定：`PLAN_COMPLETE_EXECUTION_NOT_STARTED`

本計畫把既有小J本機 Intent Field、意圖場建構候選、True-8D 最小差分三閘門、公開測試鏈及 ADI/GTP/Moving-V Shadow 設計收斂為一條可逐階段驗收的落地路徑。本輪只建立流程與閘門，不部署、不重啟、不寫資料庫、不進行正式會員或金流效果。

## 1. 最終要落地的不是第二個資料庫

系統意圖場是「受治理的動態狀態與效果協調層」，不是新的會員主檔、Odoo 副本或第二個總場。它只做五件事：

1. 解析使用者真正要達成的結果、場景、限制與驗收條件。
2. 依引用載入最小、已驗證、作用範圍內的狀態。
3. 先走決定性查表、規則、模板與狀態轉移。
4. 只有未知欄位需要補齊時，才請本機模型產生候選差分。
5. 重構、驗證並交人審與總場裁決；模型、設備與 adapter 均不取得正式效果權限。

會員身分權威仍在協會治理的會員身分來源；服務系統只使用 role binding 或 8D identity packet reference，不複製完整會員明文。小J／W7TP 技術權利、公益授權與系統 runtime authority 分開處理，未有正式移轉或授權文件時不得互相推定。

## 2. 系統分層

```text
控制面：政策、權限、範圍、版本升格與撤銷
意圖面：D1 intent root、接受條件、產品效果
狀態面：最小 verified scoped state 與 session
執行面：決定性路由優先，模型只補 unknown delta
重構面：ADI/GTP refs、expected hash、重構與驗證收據
記憶面：Moving-V Shadow 觀察與預算候選
證據面：decision/transition/effect/rollback receipt chain
體驗面：任務效果、使用摩擦、延遲、失敗與復原
```

控制面不存業務明文；狀態面不自行取得身分權威；執行面不自行升格；證據面不替代人類語意審查。

## 3. 單筆意圖的建構順序

```text
D1 intent resolution
  -> load verified scoped state
  -> Gate 1 canonical lock
  -> Gate 2 intent/product gap
  -> Gate 3 human UI/product review
  -> generate unknown delta only
  -> reconstruct candidate state
  -> verify candidate
  -> total-field review
```

關鍵停損：

- D1 無法解析：在載入狀態與呼叫模型前 `HOLD`。
- 沒有真實 minimum delta：`BUILD_NOT_REQUIRED`。
- 已知狀態與規則可決定：不呼叫模型。
- 模型輸出欄位、雜湊或 verifier 不通過：`HOLD`，不交付 effect。
- 沒有總場 decision receipt：不 commit。

## 4. 資料最小化契約

原始輸入只可存在於入口的短暫處理邊界，不得進 Intent Cache，也不得原樣送入 unknown-delta 模型封包。模型只看到：intent root ref、current state root ref、stable refs、affected coordinates、unknown slots、目標產品效果、重構條件、驗證條件與輸出 Schema。

禁止放入模型或跨節點封包的內容包括完整上下文、已知私密狀態值、會員明文、付款秘密、憑證與 token。跨節點只傳 refs、delta、hash、authority、重構條件、驗證指示與 receipts。

## 5. 九階段落地流程

| 階段 | 目的 | 主要產物 | 通過後才可進入 |
|---|---|---|---|
| L00 範圍與權限鎖定 | 確認唯一意圖場、技術權利、角色與正式效果邊界 | 簽署範圍、角色矩陣、禁止效果清單 | L01 |
| L01 唯讀基線 | 盤點 runtime、政策、Schema、健康、證據與缺口 | baseline、能力圖、gap register、SHA 清單 | L02 |
| L02 契約與場定版 | 定版 D1–D8、intent root、delta、envelope 與 receipts | closed schemas、版本遷移規則、負向測試 | L03 |
| L03 決定性核心 Shadow | 完成意圖解析、scoped state、三閘門與規則路由 | shadow controller、規則包、decision trace | L04 |
| L04 模型未知差分 Shadow | 本機模型只補 unknown slots，輸出仍為候選 | delta adapter、validator、品質與資料邊界報告 | L05 |
| L05 ADI/GTP/Moving-V Shadow | 綁 ADI receipt、GTP 重構與記憶體觀察 | 重構收據、hash verdict、false-miss/效能報告 | L06 |
| L06 人審本機試點 | 紙上或本機公開測試，無正式 DB write | 任務、摩擦、延遲、復原與 incident 報告 | L07 |
| L07 限定可撤銷 Canary | 只開一條狹窄、可回復、具收據的效果路徑 | authorization、effect、rollback receipts | L08 |
| L08 正式升格與運維 | 簽署版本、active pointer、SLO、事故與升級回退 | release bundle、runbook、dashboard | 持續營運 |

目前可直接進行的不是部署，而是人審本計畫後，把 L00 與 L01 組成一個「無 effect 工作包」。L02 之後的任何動作都必須拿前一階段的證據作為 entry gate。

## 6. 每階段共通驗收規則

每個階段都必須同時具備：

- 明確輸入、輸出、版本與 SHA-256。
- entry gate、exit gate、HOLD 原因與 rollback。
- 正向、負向、重播、重複提交、競態與失敗測試。
- 不把測試通過當成 runtime authority。
- 不改 active pointer；直到限定授權與 rollback receipt 都已存在。
- 不以整體平均掩蓋資料安全、個資、權限或 canonical 違規。

## 7. 量測與升格判定

目標優先序固定為：

1. 資料、身分與 canonical 安全。
2. 任務效果與正確性。
3. 人類可感知延遲與操作摩擦。
4. 重構、失敗復原與 rollback 可靠度。
5. 意圖解析、HOLD/clarification、預載與 false miss。
6. 系統穩定度。
7. 記憶體、運算與傳輸節省。

未經基線與人審校準前，不先發明 p95、命中率或記憶體門檻。下列永遠是零容忍：未授權效果、會員明文或秘密洩漏、canonical source 刪除、模型／設備擴權、無 receipt 的 effect。

## 8. 回退模型

- L00–L02：拒絕候選或保留前版 Schema，不碰 active runtime。
- L03–L05：停止 Shadow controller/adapter，回到決定性 HOLD；不需資料回復。
- L06：關閉試點入口，保留去識別化候選證據。
- L07：撤銷 canary receipt、停用入口、恢復前一簽署版本並驗證 state root。
- L08：切回前一 signed active pointer，執行 post-rollback verification。

任何 rollback 都不能刪除必要的 decision、effect、incident 與 rollback 證據。

## 9. 第一個落地工作包

下一案應只做 `L00 + L01`：

1. 人類確認目標場景、首個允許 intent、第一個禁止 effect、操作角色與可接受體驗。
2. 唯讀刷新 8080/8081/9002/9107/9004/11434、Intent Cache、總場 authority、現有 Schema/adapter/測試與 evidence hashes。
3. 產出 source-of-truth map、component/gap matrix、第一版 threat model 與 L02 entry decision。
4. 結果只有 `PASS_TO_CONTRACT_FREEZE` 或 `HOLD_WITH_GAPS`，不部署。

機器可讀版本位於 `configs/total_field/w7tp_system_intent_field_landing_plan_v1.candidate.json`，由對應 JSON Schema 與一致性測試鎖定。
