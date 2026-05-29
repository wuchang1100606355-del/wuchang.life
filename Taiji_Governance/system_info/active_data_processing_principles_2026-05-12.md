# Taiji Hub 生效中系統資料處理原則

版本：2026-05-12  
狀態：ACTIVE  
適用系統：Taiji Hub / Odoo ADI / POS / Gateway / Runtime / 組織雲端 / 社區向量資訊 / 分散式算力  
組織主體：新北市三重區五常社區發展協會  
網域：wuchang.life  
數位代表號：admin@wuchang.life  

## 0. 生效聲明

本文件為 Taiji Hub 目前生效之系統資料處理原則總表。

後續 Runtime、Gateway、Odoo ADI、社區向量資訊資料產品、組織雲端 staging、C/D 磁碟資料邊界、分散式算力節點與內部系統看板，均應以本文件作為資料治理基準。

## 1. 公益與法定主體

本系統服務於：

```text
新北市三重區五常社區發展協會
經會員大會通過之社區產業發展專案
```

所有資料處理須符合：

- 公益目的
- 社區產業永續
- 本會資訊保護責任
- 會員大會授權脈絡
- Five-Metric Gate
- Taiji Gateway
- Audit / SHA256 / Rollback

## 2. 無明文上下文

AI Runtime、外部資料產品、公開看板與買方授權資料不得直接接觸個別明文。

可進入 AI / 公開 / 買方上下文者：

- 公式
- 欄位定義
- 聚合方法
- 最後統計數據
- 去識別向量
- SHA256
- audit 摘要
- 版本資訊

不可進入者：

- 會員明文
- 個別會員行為數字
- 個別計算過程
- 可逆識別資料
- 商家營業機密
- 管委會敏感明細
- secret / token / key

核心原則：

```text
只見公式。
不見個別數字。
只見結果。
不見過程。
```

## 3. 個別行為匯入總量

個別會員或團體會員之行為資訊，可以進入本會總量計算。

但公開端、AI 上下文與買方資料產品只能看見：

- 公式
- 統計口徑
- 聚合方法
- 最後結果

不得看見：

- 個別數字
- 個別過程
- 中間值
- 個別貢獻量
- 可逆識別分組

## 4. 社區向量資訊資料產品

本會得就度規系統產生之社區向量資訊，於無敏、去識別、不可逆、聚合化、可稽核之前提下，作為公益學術、社區產業、ESG 指標與公共價值衡量資料產品，進行授權、販售或合作交換。

可授權：

- 社區向量資訊
- ESG 指標
- 公益成效統計
- 去識別行為向量
- 聚合趨勢資料

不可授權：

- 會員個資
- 個別行為紀錄
- 可逆識別資料
- D 磁碟會員封存庫
- 商家營業機密
- secret

## 5. 識別暗碼與不可斷鏈

本會所轄度規資訊得加註非個人化識別暗碼，用以追溯資料包版本、授權對象類別、release window、canary code 與 SHA256 baseline。

原則：

```text
追資料包，不追個人。
追授權鏈，不追居民。
度規資訊可以流通，但不可斷鏈。
```

識別暗碼不得包含個資、設備明文識別、secret 或可逆會員標籤。

## 6. Odoo ADI 帳務

Odoo 會計帳務套用 ADI 度規資料庫法則。

可見性分為：

```text
一般會計帳務：權限可見、可稽核。
公益帳戶：上雲、公開、24H 可見。
```

公益帳戶公開規則：

```text
數據科目可見。
摘要可見。
明細不可見。
```

公開的是公益流向、分類、總額、趨勢、基金池留存與 ESG 摘要；保護的是會員、明細、商家機密、單筆憑證與帳戶資訊。

## 7. 儲存邊界

| 邊界 | 用途 | 規則 |
|---|---|---|
| Linux 子系統 | 開發、測試、runtime | 可處理 code/schema/test/artifact，不外送 secret |
| C 磁碟 | 經常讀寫、個別需求、場景資料 | 團體會員、商家營業、管委會資料；不自動上雲 |
| D 磁碟 / 記憶卡 | 高權限、特殊用途、會員資訊庫正式營運後封存 | 需本人審查、audit、SHA256；開發期不啟用正式會員庫 |
| 組織共用雲端 | 無敏、唯讀、全設備可用 | 僅無敏公開摘要、文件、schema、ESG 結果 |

## 8. 開發期與正式啟用

開發期間：

- 無正式會員個資庫
- 使用本會幹部帳號、mock、schema、redacted fixture 測試
- 開發效率優先
- 不依賴正式會員明文

正式啟用前：

- 開發期金鑰、token、測試帳號與可能個資需清洗或輪替
- 建立 SHA256 baseline
- 建立 rollback plan
- owner approval

正式營運後：

- 會員資訊庫 D 磁碟物理封存政策生效
- 僅三種情境可開封

## 9. 分散式算力

本階段先打通分散式算力架構，算力如何流動容後再議。

本會運算服務容器區與會員設備區必須嚴格隔離。

原則：

```text
算力可以流動。
權限、secret、會員明文不可流動。
```

會員設備可作為低權限互動端或能力訊號端，不得成為本會容器 shell、資料庫節點、secret store 或 production admin node。

## 10. 研究使用

公益學術研究可使用個資或行為資訊，但必須治理：

- 特定目的
- 告知/同意或合法依據
- 去識別化或假名化優先
- 最小必要
- audit
- 不外送外部 AI 明文
- 不公開可識別資訊

開發期仍以 mock / 幹部測試帳號 / redacted fixture 為主。

## 11. L3 永久封鎖

以下一律 `L3_metric_hazard = block`：

- 販售個資或個別行為紀錄
- 將個別行為過程交給買方或 AI
- 會員明文上雲
- secret / token / service account JSON 輸出
- 公益基金池私用
- 一般帳務明細全公開
- D 會員封存庫用於開發測試
- 會員設備取得容器或 production 權限
- 任何節點繞過 Gateway / Five Metric / Audit / Rollback
- 刪除 audit、SHA256 或授權鏈

## 12. 已生效引用檔

本文件引用並整合下列已建立政策與 schema：

- `public_interest_academic_research_data_policy_2026-05-11.md`
- `community_industry_revenue_use_policy_2026-05-11.md`
- `non_sensitive_vector_data_product_policy_2026-05-11.md`
- `odoo_adi_account_visibility_policy_2026-05-12.md`
- `public_account_subject_visible_summary_policy_2026-05-12.md`
- `group_member_aggregate_mapping_policy_2026-05-12.md`
- `individual_behavior_to_aggregate_no_process_policy_2026-05-12.md`
- `metric_information_audit_watermark_policy_2026-05-12.md`
- `distributed_compute_boundary_policy_2026-05-11.md`
- `pre_activation_sanitize_rotate_policy_2026-05-11.md`

## 最終原則

```text
AI 不讀人，AI 讀度規。
公開公式，不公開個體。
公開結果，不公開過程。
社區向量資訊可以授權，個資與機密不可販售。
度規資訊可以流通，但不可斷鏈。
```

