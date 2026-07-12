# W7TP GT Definition Drift Red-Team Rule
# W7TP 生成式傳輸定義漂移紅隊規則

STATE=GT_DEFINITION_DRIFT_TOTAL_FIELD_SEAL
RUN_ID=GT_DEFINITION_DRIFT_TOTAL_FIELD_SEAL_20260709_232316
SOURCE_RECALL_RUN_ID=GT_CASE_RECALL_20260709_184502
SOURCE_REDTEAM_RUN_ID=GT_FAILURE_REDTEAM_CONTROL_20260709_184814
SAFETY=NO_SECRET_NO_DB_WRITE_NO_DEPLOY_NO_RESTART_NO_ROUTER_WRITE_NO_RESCAN

## 1. 正確技術定義

生成式傳輸不是檔案搬運、不是雲端密文同步、不是備份、不是下載解密、不是完整上下文轉存、不是 raw data copy。

生成式傳輸是：

```text
狀態場封包 + 引用 + 查表條件 + 重構規則 + 驗證資料
→ 接收端生成可驗證等價狀態
→ VERIFY
→ SEAL
```

其核心流程為：

```text
SOURCE → PACKET → RECONSTRUCT → VERIFY → SEAL
```

## 2. 定義漂移判定

若任一 AI 候選輸出、程式設計、文件敘述或執行流程，將生成式傳輸錯定義為下列任一項，應判定為 GT_DEFINITION_DRIFT：

```text
檔案搬運
完整資料同步
雲端備份
下載解密
raw transcript 轉存
密文雲端搬移
以資料本體傳輸取代狀態場封包重構
以 scp / copy / sync 取代封包重構
以完整上下文搬移取代等價狀態生成
```

## 3. 紅隊處置規則

```text
RULE_ID=REDTEAM_GT_DEFINITION_DRIFT
LEVEL=HOLD
TRIGGER=生成式傳輸被錯定義為資料搬運、雲端同步、備份、下載解密、raw data copy、完整上下文轉存，或偏離封包→重構→驗證→封印流程。
ACTION=立即 HOLD，不得落地；需回到狀態場封包、引用、查表條件、重構規則與驗證資料後，才可重新進入候選。
```

## 4. 與既有失敗案例之關聯

已調閱生成式傳輸案例：

```text
SOURCE_RECALL_RUN_ID=GT_CASE_RECALL_20260709_184502
SUCCESS_CASES=370
HOLD_CASES=205
FAIL_CASES=48
ALL_GT_HITS=782
```

已完成失敗案例紅隊管制：

```text
SOURCE_REDTEAM_RUN_ID=GT_FAILURE_REDTEAM_CONTROL_20260709_184814
TOTAL_FAIL_CASES=48
CONTROLLED_CASES=48
CONTROL_COVERAGE=100%
```

失敗原因中，高度可能與 AI 定義漂移相關者包含：

```text
REDTEAM_RECONSTRUCTION_MISMATCH=32
REDTEAM_PATH_OR_REFERENCE_FAIL=27
REDTEAM_JSON_OR_SCHEMA_FAIL=27
REDTEAM_HASH_OR_SEAL_FAIL=24
REDTEAM_CLOUD_BOUNDARY=19
REDTEAM_DISCLOSURE_BOUNDARY=18
REDTEAM_SECRET_OR_TOKEN=18
```

推定漂移鏈：

```text
AI 錯定義生成式傳輸
→ 誤以為要搬資料 / 搬檔案 / 搬雲端內容
→ 路徑與引用錯位
→ JSON/schema 不合
→ 重構不一致
→ hash/seal 失敗
→ 觸發 cloud boundary / disclosure boundary / secret risk
→ 紅隊 HOLD / BLOCK
```

## 5. 總場鎖定句

```text
生成式傳輸之技術本質，是以狀態場封包、引用、查表條件、重構規則與驗證資料，使接收端生成可驗證等價狀態；凡將其錯定義為資料搬運、同步、備份、下載解密或完整上下文轉存者，均屬定義漂移，列入紅隊 HOLD。
```

## 6. 後續執行門檻

```text
IF candidate_mentions_gt AND candidate_path_is_copy_or_sync:
  STATE=HOLD_GT_DEFINITION_DRIFT

IF candidate_mentions_gt AND missing_reconstruct_verify_seal:
  STATE=HOLD_GT_DEFINITION_DRIFT

IF candidate_mentions_gt AND exposes_H64_or_WHY_IT_RUNS:
  STATE=HOLD_DISCLOSURE_BOUNDARY

IF candidate_mentions_gt AND requires_raw_secret_or_member_plaintext:
  STATE=BLOCK_SECRET_OR_MEMBER_PLAINTEXT
```

NEXT=所有後續生成式傳輸候選，先通過 GT_DEFINITION_DRIFT 檢查，再進入重構驗證與封印。
