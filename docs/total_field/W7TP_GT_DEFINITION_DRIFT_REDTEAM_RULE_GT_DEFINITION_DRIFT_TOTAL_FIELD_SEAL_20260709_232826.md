# W7TP 生成式傳輸定義漂移紅隊規則

STATE=GT_DEFINITION_DRIFT_TOTAL_FIELD_SEAL
RUN_ID=GT_DEFINITION_DRIFT_TOTAL_FIELD_SEAL_20260709_232826
SOURCE_RECALL_RUN_ID=GT_CASE_RECALL_20260709_184502
SOURCE_REDTEAM_RUN_ID=GT_FAILURE_REDTEAM_CONTROL_20260709_184814
SAFETY=NO_SECRET_NO_DB_WRITE_NO_DEPLOY_NO_RESTART_NO_ROUTER_WRITE_NO_RESCAN

## 正確技術定義

生成式傳輸不是檔案搬運、不是雲端密文同步、不是備份、不是下載解密、不是完整上下文轉存、不是 raw data copy。

生成式傳輸是：

```text
狀態場封包 + 引用 + 查表條件 + 重構規則 + 驗證資料
→ 接收端生成可驗證等價狀態
→ VERIFY
→ SEAL
```

核心流程：

```text
SOURCE → PACKET → RECONSTRUCT → VERIFY → SEAL
```

## REDTEAM 規則

```text
RULE_ID=REDTEAM_GT_DEFINITION_DRIFT
LEVEL=HOLD
TRIGGER=凡將生成式傳輸錯定義為檔案搬運、完整同步、雲端備份、下載解密、raw data copy、完整上下文轉存，或偏離 SOURCE→PACKET→RECONSTRUCT→VERIFY→SEAL 流程者。
ACTION=立即 HOLD，不得落地；需回到狀態場封包、引用、查表條件、重構規則與驗證資料後，才可重新進入候選。
```

## 來源證據

```text
SUCCESS_CASES=370
HOLD_CASES=205
FAIL_CASES=48
ALL_GT_HITS=782
CONTROLLED_FAIL_CASES=48
CONTROL_COVERAGE=100%
```

## 推定漂移鏈

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

## 總場鎖定句

```text
生成式傳輸之技術本質，是以狀態場封包、引用、查表條件、重構規則與驗證資料，使接收端生成可驗證等價狀態；凡將其錯定義為資料搬運、同步、備份、下載解密或完整上下文轉存者，均屬定義漂移，列入紅隊 HOLD。
```

NEXT=所有後續生成式傳輸候選，先通過 GT_DEFINITION_DRIFT 檢查，再進入 RECONSTRUCT_VERIFY_SEAL。
