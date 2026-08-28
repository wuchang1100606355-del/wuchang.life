# 來源、權威與安全邊界

## 來源類別

- `USER_EXPLICIT`：使用者本次明確表達；只有此類別可供 `allowed_effects` 引用。
- `AI_COMPLETION_HYPOTHESIS`：數位新創總監、產品負責人或其他 AI 的補全、推論與設計候選。
- `FIELD_EVIDENCE`：worktree-local 普通檔 ref、stage receipt 與 detached 實算 SHA-256；自報字串不是證據。
- `EXTERNAL_PRIMARY_SOURCE`：外部第一手公開模式的參照、版本、授權與完整性資訊。
- `MODEL_PRIOR_CANDIDATE`：模型先驗、類比或推論候選；不得成為權威。
- `AUTHORITY_DECISION_REQUIRED`：表示仍需獨立總場權威決定，不是已有授權。

六種來源類別必須完整且全檔一致。每個來源至少帶 `class` 與 `ref`。只保存參照、版本與雜湊，不保存秘密值、會員明文或外部全文。

## 不可提升的權威

- AI 補全不得聲稱權威，也不得進入允許效果。
- 封包、身分、角色、登入成功、測試閉合、Git 提交、遠端送達、跨節點完整性與部署存在都不等於授權。
- 8D 身分封包只供識別、關聯及驗證；角色綁定與每項效果仍由總場權威決定。
- 缺少、失效或衝突的權威指標必須保持 `ACTIVATION_NOT_AUTHORIZED`。
- 協會會員主權資料不得因服務登入而轉移成服務資料庫的正式會員登記。
- `HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD` 只表示正典八面動態選用，不是第九維，也不授權。
- caller signature 與 authority 只能記為 `claimed_signature_state` 與 `claimed_authority_state`；`AUTHENTICITY_UNVERIFIED` 固定保留。
- 本版沒有封包外固定可信信任根、受信 runner 或原子 nonce ledger。完整性不等於真實性，真實性不等於權威。
- producer、runner、caller 自報的 executed、`FIELD_EVIDENCE` 或 verifier_result 不採信。

## 8D 降階限制

3D-7D 只可用於無效果預分析 `CANDIDATE`。下列任一類強制完整 8D，資源節省不得降階：

1. 身分、角色、權威或治理。
2. 秘密、隱私、會員資料或營業秘密。
3. 跨節點正式 runtime、DB、部署或路由。
4. 外部不可逆效果或不確定前沿。

## 安全輸入

只接受已去識別化的建構規格。不得把下列來源交給工具：秘密檔、會員名冊、原始權杖、瀏覽器資料、失敗佇列原始內容、資料庫資料列、私有查表、真實權重資料、相位映射、真正 `WHY_IT_RUNS` 技術內容或內部推理。

工具遇到原始密碼、金鑰、權杖、私鑰、會員姓名／電話／信箱／地址／身分證號欄位與明文值，立即 `HOLD`，只回報欄位座標，不回報值。只對真實內容 `HOLD`；名稱、規則、文件敘述、`placeholder`、`${ENV}`、`env_ref`、`key_ref`、雜湊、欄位名稱及 weight 參數名不因字樣本身被判為秘密。

## 內外樣式供應

`FIELD_EVIDENCE` 至少要求 worktree-local 普通檔 ref、stage receipt 與 detached 實算 SHA-256。`EXTERNAL_PRIMARY_SOURCE` 另要求授權狀態與來源權威狀態；缺一即隔離該模式。禁止：

- 以名稱相似連結來源。
- 把未固定版本的網頁當成不可變依賴。
- 把外部範例的權限、資料流或品牌宣告原樣搬入。
- 把來源雜湊一致誤報為作者、授權、簽章或正式權威通過。
- 在十二段未全嘗試前用模型先驗或外部來源補缺。
- 用補缺內容改寫 `USER_EXPLICIT`、正典、權威或效果。

## 操作邊界

預設僅建構候選檔。修改正式程式、提交、推送、部署、重啟、資料庫寫入、路由寫入及啟用都需要各自明確授權。某群組被隔離時，繼續處理與它無相依關係的安全群組。

所有推演、模擬、候選組合與修改影響評估只可在隔離虛擬空間完成；主線只讀。分析結果、相似度、檔名接近、表面結構接近、runner 輸出或 producer 輸出都不得授權接線、合併、覆蓋、部署、啟用或其他效果。

`ANALYSIS` 與 `ADDRESSING` 必須共同輸出主線關係與接續距離：`candidate_relation` 只能是 `CONTINUE`、`FUSE`、`REPLACE`、`PARALLEL_SHADOW`、`ISOLATE`、`HOLD`。`continuation_distance` 必須逐軸列 `semantic`、`structure_contract`、`dependency`、`tests`、`runtime_wiring`、`data_migration`、`governance_authority`、`security`、`cross_node`、`recovery` 的 `state` 與 `evidence_refs`；`state` 只能是 `ALIGNED`、`DELTA`、`UNKNOWN`，任一軸 `UNKNOWN` 即 `HOLD`。

關係硬閘固定：`CONTINUE` 必驗輸入輸出契約、依賴、版本；`FUSE` 必驗重疊供給、優先序、雙執行風險、權威衝突；`REPLACE` 必驗所有消費者覆蓋、行為等價、資料遷移、退場與回復；`PARALLEL_SHADOW` 僅可隔離且無效果；`ISOLATE` 用於無關或風險邊界；`HOLD` 用於未知軸或必要閘未閉合。相似度不得升格任何關係，未閉合只能 `PARALLEL_SHADOW`、`ISOLATE` 或 `HOLD`。

供需依存必須密合列出 `old_demand_set` → `new_supply_mapping`、`uncovered_demands`、`extra_side_effects`、`unknown_dynamic_consumers`、`dependency_cycles`、`authority_conflicts`、`recovery_route`。任一必要缺口非空不得 `REPLACE` 或覆蓋，只能 `PARALLEL_SHADOW` 或 `HOLD`。安全順序固定 `expand` → `migrate` → `deprecate`，且每步必須有回復。

任何結構與雜湊閉合輸出最高仍只能是 `STRUCTURE_AND_HASH_CHECK_PASS`，且必須同時保留 `RUNTIME_EVIDENCE_UNVERIFIED`、`USER_JOURNEY_EVIDENCE_UNVERIFIED`、`CROSS_NODE_REPLAY_UNVERIFIED`、`AUTHENTICITY_UNVERIFIED`、`ACTIVATION_NOT_AUTHORIZED`。這些主線關係規則不得改動 transfer invariant，也不得產生授權效果。
