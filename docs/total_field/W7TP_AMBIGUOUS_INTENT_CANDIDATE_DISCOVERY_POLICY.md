# W7TP AMBIGUOUS INTENT CANDIDATE DISCOVERY POLICY
# 歧義意圖候選發現機制

STATE: POLICY_BOUNDARY_SEALED
MODE: INTENT_GOVERNANCE
FINAL_AUTHORITY: ΩGI_TOTAL_FIELD

## 1. 核心定義

當使用者輸入含有錯別字、語意歧義、口語省略、多重可能解讀或上下文不完整時，系統不得直接覆蓋原始意圖。

系統應保留原始輸入，並產生一個或多個候選解讀，標示為 AMBIGUITY_CANDIDATE。

## 2. 候選分支

歧義候選可包含：

- 原始意圖候選
- 修正錯字候選
- 系統誤解但具價值之功能候選
- 專利技術候選
- 產品化候選
- 紅隊風險候選

## 3. 美麗誤會機制

若 AI 因錯字或歧義產生非原始意圖但具高價值之功能，該功能不得自動視為使用者原意，但可標記為：

BEAUTIFUL_MISREAD_CANDIDATE: TRUE

此候選可進入總場審查、紅隊分析、產品矩陣或專利候選池。

## 4. 升級條件

候選分支升級為正式功能，至少需滿足：

- 使用者明確確認
- 總場 ALLOW
- 紅隊未 HOLD
- 不含 secret / 個資 / H64-TD codebook
- 不造成 production mutation
- 不覆蓋原始意圖紀錄

## 5. 禁止

- 不得把 AI 誤解直接當成使用者原始意圖。
- 不得自動覆蓋原文。
- 不得未確認即寫入主發明。
- 不得未確認即 commit/tag。
- 不得將候選功能宣稱為 production。
- 不得讓雲端 AI 取得最終裁決權。

## 6. 發射狀態

AMBIGUOUS_INTENT_CANDIDATE_DISCOVERY: TRUE
ORIGINAL_INTENT_PRESERVED: TRUE
BEAUTIFUL_MISREAD_CANDIDATE_ALLOWED: TRUE
USER_CONFIRMATION_REQUIRED: TRUE
AI_CANDIDATE_ONLY: TRUE
OMEGA_GI_FINAL_AUTHORITY: TRUE
H64_TD_REF_ONLY: TRUE
