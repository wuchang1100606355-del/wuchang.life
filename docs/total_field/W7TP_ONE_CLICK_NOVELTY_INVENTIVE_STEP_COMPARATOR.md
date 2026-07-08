# W7TP ONE-CLICK NOVELTY AND INVENTIVE STEP COMPARATOR
# 一鍵新穎性與進步性比較器

STATE: POLICY_SPEC_CREATED
MODE: IP_REVIEW_PRODUCT_FEATURE
FINAL_AUTHORITY: ΩGI_TOTAL_FIELD
AI_STATUS: CANDIDATE_ONLY

## 1. 功能定位

本功能提供使用者一鍵觸發之新穎性、進步性與相同技術查定流程。

使用者點擊後，系統應將核心發明拆解為 machine-checkable claim features，並針對全球專利、論文、標準、開源專案、產品文件與技術白皮書進行候選檢索與特徵比對。

本功能僅產生智財初判報告，不取代專利專責機關、專利師、法院或人類最終判斷。

## 2. 核心比較對象

核心發明項目：

主權治理主體認知治理模型執行系統。

核心技術特徵至少包含：

- 主權治理主體
- 多個 7D 意圖場
- 無 LLM AI 治理進程
- 無 GPU / 無浮點可運行
- 非公開規則表 / 營業秘密 ref
- verifier chain
- hash / prev_hash / HMAC / trajectory verifier
- candidate_only 雲端不可回推
- ALLOW / HOLD / REVIEW / DEADBOX / HUMAN_CONFIRM
- ΩGI / human final authority

## 3. 一鍵流程

USER_CLICK
→ claim packet extraction
→ claim feature decomposition
→ prior-art query generation
→ global search candidate collection
→ feature-by-feature comparison
→ closest prior art ranking
→ novelty decision
→ inventive step decision
→ identical technology check
→ claim rewrite suggestion
→ R&D history evidence appendix
→ final report seal

## 4. 輸入

系統可接收：

- claim packet
- 發明名稱
- 技術特徵清單
- 研發歷程 evidence refs
- git commit / tag refs
- runtime report refs
- verifier / seal refs
- red-team report refs
- user confirmation refs

不得接收：

- H64-TD codebook
- H64-TD mapping
- H64-TD table
- H64-TD rules
- 會員明文
- secrets / token / key
- raw audio
- 可回推個資或敏感照護內容

## 5. 新穎性判斷

若單一先前技術文件揭露核心請求項之全部必要特徵，則標示：

NOVELTY_HOLD

若未找到單一先前技術揭露全部必要特徵，但找到部分高度接近技術，則標示：

NOVELTY_CONDITIONAL_PASS

若檢索結果不足或證據不明，則標示：

NOVELTY_REVIEW_REQUIRED

## 6. 進步性判斷

系統應比較最接近先前技術與本發明之差異，並判斷該差異是否產生技術效果。

主要技術效果包含：

- 無 LLM 作為最終裁決來源
- 多個 7D 意圖場之跨場仲裁
- 無 GPU / 無浮點治理進程
- candidate_only 不可回推雲端候選
- verifier chain 可審計與可回滾
- 主權治理主體保留最終裁決權

若差異僅為普通政策引擎、人類審查或 AI agent workflow，應標示：

INVENTIVE_STEP_HOLD

若差異可形成具體技術效果，應標示：

INVENTIVE_STEP_CONDITIONAL_PASS

若需要更多先案或實驗證據，應標示：

INVENTIVE_STEP_REVIEW_REQUIRED

## 7. 相同技術查定

系統應輸出：

- IDENTICAL_TECH_FOUND
- NO_IDENTICAL_TECH_FOUND
- CLOSE_PRIOR_ART_FOUND
- FEATURE_OVERLAP_SCORE
- DISTINGUISHING_FEATURES
- CLAIM_REWRITE_REQUIRED

不得因未找到相同技術即宣稱必然可專利。

## 8. 研發歷程附件

完整研發歷程可作為 evidence appendix，包含：

- git commit / tag
- runtime report
- memory seal
- red-team report
- background prejudge report
- verifier PoC
- Odoo / sidecar evidence
- Google Drive design evidence
- sha256 / HMAC / report hash
- 對話摘要與版本演化紀錄

研發歷程可用於佐證：

- 發明來源
- 研發連續性
- 可實施性
- 技術效果
- 非事後拼貼
- 非單純概念宣告

研發歷程不得被誤用為新穎性或進步性之唯一證明。

## 9. 報告輸出

一鍵比較器應輸出：

- NOVELTY_DECISION
- INVENTIVE_STEP_DECISION
- IDENTICAL_TECH_FOUND
- CLOSE_PRIOR_ART_FOUND
- TOP_PRIOR_ART
- FEATURE_BY_FEATURE_COMPARISON
- DISTINGUISHING_FEATURES
- CLAIM_REWRITE_SUGGESTIONS
- R_AND_D_HISTORY_APPENDIX
- REPORT_HASH
- FINAL_DECISION

## 10. Forbidden

- 不得宣稱一鍵比較等於專利核准。
- 不得宣稱未找到先案即必然新穎。
- 不得宣稱紅隊通過即必然具進步性。
- 不得將研發歷程視為可取代全球先案查定。
- 不得揭露 H64-TD codebook / mapping / table / rules。
- 不得將雲端檢索封包包含可回推個資、會員明文、金流、照護情境或原始瀏覽器狀態。
- 不得讓 AI 成為最終智財裁決者。

## 11. 發射狀態

ONE_CLICK_NOVELTY_INVENTIVE_STEP_COMPARATOR: TRUE
GLOBAL_PRIOR_ART_SEARCH_REQUIRED: TRUE
FEATURE_BY_FEATURE_COMPARISON_REQUIRED: TRUE
R_AND_D_HISTORY_APPENDIX_ALLOWED: TRUE
R_AND_D_HISTORY_IS_NOT_SOLE_NOVELTY_PROOF: TRUE
AI_CANDIDATE_ONLY: TRUE
H64_TD_REF_ONLY: TRUE
OMEGA_GI_FINAL_AUTHORITY: TRUE

FINAL_DECISION: ONE_CLICK_NOVELTY_INVENTIVE_STEP_COMPARATOR_READY
