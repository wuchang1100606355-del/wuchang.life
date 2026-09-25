# W7TP 拉取式封包原生二級輕雲正式架構

## 正式邊界

本架構將會員身分匝道器、轉譯匝道器容器、生成式傳輸與 taiji01 二級輕雲整合成同一條確定性路徑。核心原則是「資料不離場，能力封包進場」。

生成式傳輸是協定原生的 8D 狀態場封包：攜帶引用、查表索引、重構條件、等價狀態生成規則、傳輸協定及驗證方法，由 taiji01 本地或總場驗證。它不是檔案搬運、完整檔案複製、雲端同步、備份或下載後解密。只重構封包所需部分，並以封包要求的 L1、L2 或 L3 驗證層級判定。

固定政策：

- `NO_MEMBER_DATA_UPLOAD=TRUE`
- `NO_IDENTITY_PLAINTEXT_UPLOAD=TRUE`
- `NO_LOCAL_CONTEXT_UPLOAD=TRUE`
- `NO_DATABASE_REPLICA_UPLOAD=TRUE`
- `CLOUD_MODE=PULL_PACKET_ONLY`
- `RECONSTRUCTION_LOCATION=TAIJI01_LOCAL`
- `VERIFICATION_LOCATION=TAIJI01_OR_TOTAL_FIELD`

## 正式資料流

```text
會員／裝置
  → 身分匝道器
  → 轉譯匝道器容器
  → taiji01 二級輕雲
  → 按需拉取能力封包
  → 本地重構
  → L1–L8 多層稽核
  → 本地或總場驗證
  → Odoo／POS／物業／協會／家庭服務場
```

標準封包生命週期為 `SOURCE → PACKET → RECONSTRUCT → VERIFY → SEAL`。若任何必要證據缺失或相互衝突，立即回傳 `STATE=HOLD`，不得封印。

## 身分匝道器

身分匝道器只處理 `identity_ref`、`role_refs`、`authority_scope`、`consent_state`、`revocation_state`、`device_binding_ref`、`scenario_ref` 與身分封套驗證。姓名、電話、地址及其他可識別會員的明文欄位不屬於任何正式封包 Schema；匝道器也會遞迴拒絕這類欄位。

身分解析不授予新權限，只比較入口封套與已驗證的權限引用。不同意、已撤銷、裝置不一致或場景不一致均為 `HOLD`。

## 轉譯匝道器容器

場景路由表提供 `ASSOCIATION`、`PROPERTY`、`CAFE_POS`、`HOUSEHOLD`、`GENERIC` 五個容器。完整封包以引用、規則表及服務契約在本地正規化、映射和路由，不要求 LLM。

LLM 只能是 `OPTIONAL_LANGUAGE_TRANSLATOR` 或 `OPTIONAL_CANDIDATE_PROVIDER`。候選輸出仍為 L3 candidate，未經本地狀態機驗證不得執行或封印；LLM 不得取代身分匝道器、路由器、驗證器或正式執行核心。

## taiji01 二級輕雲

taiji01 同時是身分匝道節點、轉譯容器宿主、封包原生路由器、能力封包拉取器、本地狀態重構器、多層稽核器及驗證／封印閘門。它不把本地問題上送給外部能力池回答。

缺少能力時只執行：

```text
LOCAL_INTENT
  → CAPABILITY_REF_RESOLVE
  → PULL_CAPABILITY_PACKET
  → LOCAL_RECONSTRUCT
  → LOCAL_COMPARE
  → LOCAL_VERIFY
  → HOLD_OR_SEAL
```

外部只會收到 `capability_id`、`capability_ref`、`packet_type`、`schema_version`、`domain_code`、`language_code`、`compatibility_profile`、`request_nonce`、`return_protocol`。能力類型限於 `LANGUAGE_CAPABILITY_PACKET`、`CODE_COMPONENT_PACKET`、`RESEARCH_CANDIDATE_PACKET`、`PROFESSIONAL_RULE_PACKET`。能力註冊表只保存能力引用、Schema、版本、來源引用與相容資訊。

Owner／小J與總場是兩條隔離管道。`OWNER_XIAOJ` 只有在 Owner 明確指定後才可拉取候選能力封包，`AUTO_CLOUD_CALL=FORBIDDEN`；`TOTAL_FIELD` 可依治理規則獨立拉取候選，但不得啟動小J。兩條管道不得混用 authority、run、身分、啟動權、裁決權或服務帳戶憑證。

## 8D 封包契約

- D1 INTENT：服務結果引用，不包含可上送的完整會員意圖。
- D2 STATE：身分、角色、同意與工作流程的本地引用。
- D3 COORDINATE：taiji01、容器、目的服務場、模組與任務位置。
- D4 EVIDENCE：證據引用及雜湊。
- D5 EXECUTION：最短本地動作與服務契約引用。
- D6 GENERATIVE TRANSMISSION：封包協定、查表引用、重構條件與驗證方法。
- D7 RISK：真實硬風險與權限邊界。
- D8 ENVELOPE：身分引用、權限範圍、TTL、nonce、sha256、protocol、verifier。

七份 JSON Schema 共同限制入口、權限、轉譯、最小能力拉取、能力回包、本地重構及最終驗證。`additionalProperties=false` 用於阻止未定義資訊越界。

## L1–L8 確定性稽核

1. L1：Schema 與版本完整。
2. L2：身分引用、同意、撤銷及權限相符。
3. L3：場景容器與目的服務場符合路由表。
4. L4：能力拉取只含九個最小揭露欄位。
5. L5：引用、證據與能力雜湊完整。
6. L6：重構模式、條件、效果契約及比較結果一致。
7. L7：拉取式政策成立，沒有本地資訊上送。
8. L8：封套、雜湊、TTL、nonce、協定與封印條件完整。

L1 full reconstruction 只在封包協定定義完整結果時要求 hash／bit-level 結果一致；L2 equivalent reconstruction 驗證任務、狀態、控制與效果等價，不要求 byte identity；L3 candidate reconstruction 只是候選，必須經本地狀態機判定。

## 既有前端接入契約

Gemini 產生版 `App.tsx` 的角色固定為 `FRONTEND_CONTRACT_ONLY`；其中 mockData、展示狀態、`setTimeout` 與隨機值不進入正式後端。五個容器的 `packet_type` 與 `capability_ref` 由正式路由表固定映射。

不建立第二套 Dashboard。`produce_verification_packet()` 提供既有前端可直接接入的穩定欄位：`state`、`run_id`、`packet_id`、`selected_container`、`packet_type`、`capability_ref`、`current_stage`、`verification_result`、`evidence_refs`、`sha256`、`seal_status`、`confidence`，並固定回傳：

- `cloud_mode=PULL_PACKET_ONLY`
- `member_upload=DENY`
- `reconstruct=TAIJI01_LOCAL`
- `verify=LOCAL_OR_TOTAL_FIELD`

正式 `sha256` 由 canonical JSON 封包內容確定性計算；`run_id` 使用正式執行上下文傳入值，`packet_id` 沿用來源封包識別。若沒有可驗證的確定性評分依據，`confidence` 回傳 `null`，不得生成隨機分數。

正式服務整合仍須由既有 taiji01 本地服務程序接入；本次架構落地不執行部署、重新啟動、資料庫寫入或正式發布。
