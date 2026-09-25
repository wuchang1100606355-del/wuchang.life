# XiaoJ Capability Risk Evidence Field Matrix

本文收斂 XiaoJ / W7TP（小J / W7TP）產品化系統的風險證據場。此文件的目的不是放寬執行，而是把所有 candidate ability（候選能力）進入 EXECUTE_REQUEST（執行請求）、HOLD（暫停）、QUARANTINE（隔離）、DEAD_LETTER（死信）或 human review（人類審查）的條件統一成一份可驗證矩陣。

## Core Rule

本系統治理 capability（能力），不是只治理 output（輸出）。

Cloud model（雲端模型）、LLM（大型語言模型）、group intelligence（群智來源）與 tool（工具）只能產生 candidate ability（候選能力）或 EXECUTE_REQUEST（執行請求）。它們不得直接產生 EXECUTE（執行）、REAL_VERIFIED（真實已驗證）或 EXECUTABLE_AUTHORIZED（可執行已授權）。

真正權威必須由 local reconstruction（本地重構）、local discrete verifier（本地離散驗證器）、evidence seal（證據封緘）與 owner/admin approval ref（所有者 / 管理者核准引用）共同形成。

## Evidence Field Backbone

每一個風險控制項至少應對齊以下 evidence fields（證據欄位）：

| Field（欄位） | Meaning（意義） | Missing Policy（缺漏政策） |
|---|---|---|
| `risk_code`（風險代碼） | 風險類型的穩定識別 | HOLD（暫停） |
| `risk_level`（風險等級） | 低、中、高或 release blocking（阻擋發佈） | HOLD（暫停） |
| `intent_field_hash`（意圖場雜湊） | 意圖場輸入摘要 | HOLD（暫停） |
| `packet_hash`（封包雜湊） | 8D packet（八維封包）摘要 | HOLD（暫停） |
| `candidate_hash`（候選雜湊） | 候選能力或候選輸出摘要 | HOLD（暫停） |
| `evidence_ref`（證據引用） | 本地可查證證據索引 | 不得宣稱真實 |
| `evidence_hash`（證據雜湊） | 證據摘要 | 不得發佈或執行 |
| `local_lookup_ref`（本地查表引用） | 本地 lookup（查表）權威索引 | HOLD（暫停） |
| `local_reconstruction_hash`（本地重構雜湊） | 重構後狀態摘要 | HOLD（暫停） |
| `total_field_query_hash`（總場查詢雜湊） | total field subfield query（總場級分場查詢）摘要 | HOLD（暫停） |
| `verifier_policy_ref`（驗證器政策引用） | 使用哪個 verifier policy（驗證政策） | HOLD（暫停） |
| `verifier_state`（驗證器狀態） | PASS（通過）或 HOLD（暫停）等狀態 | HOLD（暫停） |
| `failure_reasons`（失敗原因） | 阻擋原因 | 必須顯示 |
| `approval_ref`（核准引用） | owner/admin approval（所有者 / 管理者核准） | 不得正式 release（發佈） |
| `release_condition_ref`（發佈條件引用） | 正式放行條件 | 不得正式 release（發佈） |
| `seal_hash`（封緘雜湊） | evidence seal（證據封緘）摘要 | HOLD（暫停） |
| `ttl`（有效期限） | time-to-live（有效期限） | HOLD（暫停） |
| `nonce`（一次性隨機碼） | replay protection（重放防護） | HOLD（暫停） |
| `route_key`（路由鍵） | 能力路由與權限路徑 | HOLD（暫停） |

## Risk Matrix

| Risk（風險） | Surface（表面） | Required Evidence（必要證據） | Missing Result（缺漏結果） | Forbidden（禁止） |
|---|---|---|---|---|
| Cloud candidate overreach（雲端候選越權） | cloud model / group intelligence（雲端模型 / 群智） | `candidate_hash`、`packet_hash`、`evidence_ref`、`evidence_hash`、`verifier_state` | HOLD_CLOUD_CANDIDATE_NOT_AUTHORITY（暫停：雲端候選不是權威） | EXECUTE（執行） |
| Missing evidence anchor（缺少證據錨點） | reality claim / execution claim（真實主張 / 執行主張） | `evidence_ref`、`evidence_hash`、`local_lookup_ref`、`seal_hash` | HOLD_EVIDENCE_ANCHOR_REQUIRED（暫停：需要證據錨點） | REAL_VERIFIED_OR_EXECUTE（真實已驗證或執行） |
| Total field danger（總場危險旗標） | total field subfield query（總場級分場查詢） | `total_field_query_hash`、`risk_code`、`failure_reasons`、`seal_hash` | HOLD_TOTAL_FIELD_SUBFIELD_REQUIRED（暫停：需要分場查詢） | EXECUTE（執行） |
| Member personal data return（會員個資回本機） | local vault（本地保管庫） | `member_ref`、`consent_ref`、`local_vault_ref`、`encrypted_payload_hash`、`ttl`、`nonce` | HOLD_ENCRYPTED_LOCAL_VAULT_REF_REQUIRED（暫停：需要加密本地保管庫引用） | plaintext to prompt/cloud（明文進提示或雲端） |
| Delegate rotation（代理身分輪替） | 8D delegate（八維代理） | `old_packet_ref`、`new_packet_ref`、`revocation_ref`、`owner_admin_or_quorum_ref`、`evidence_chain_hash` | HOLD_DELEGATE_ROTATION_EVIDENCE_CHAIN_REQUIRED（暫停：需要證據鏈） | rotate without revocation（未撤銷即輪替） |
| Sovereign XiaoJ claim（主權小J領用） | member device binding（會員裝置綁定） | `member_ref`、`xiaoj_instance_ref`、`device_ref`、`claim_packet_hash`、`revocation_ref`、`transfer_policy_ref` | HOLD_SOVEREIGN_XIAOJ_CLAIM_REFS_REQUIRED（暫停：需要領用引用） | claim without member/device binding（未綁會員與裝置即領用） |
| Formal POS order（正式 POS 下單） | POS（銷售點系統） | `order_candidate_ref`、`menu_source_ref`、`merchant_manager_ref`、`approval_ref`、`release_condition_ref` | HOLD_FORMAL_POS_RELEASE_REQUIRED（暫停：需要正式 POS 發佈） | POS write without release（未放行即寫入 POS） |
| Formal payment（正式付款） | payment capture（付款請款） | `payment_intent_ref`、`amount_hash`、`payer_consent_ref`、`approval_ref`、`release_condition_ref` | HOLD_PAYMENT_RELEASE_REQUIRED（暫停：需要付款放行） | payment capture without release（未放行即請款） |
| LINE WORKS formal send（LINE WORKS 正式送出） | notification send（通知送出） | `lineworks_channel_ref`、`connector_ref`、`message_candidate_hash`、`approval_ref`、`release_condition_ref` | HOLD_LINEWORKS_SEND_RELEASE_REQUIRED（暫停：需要 LINE WORKS 送出放行） | formal send without release（未放行即正式送出） |
| Property management action（物業管理動作） | resident/property case（住戶 / 物業案件） | `resident_ref`、`property_case_ref`、`property_case_evidence_ref`、`property_action_approval_ref`、`local_reconstruction_hash` | HOLD_PROPERTY_ACTION_EVIDENCE_REQUIRED（暫停：需要物業案件證據） | resident plaintext execution（住戶明文執行） |
| LLM hallucination boundary（大型語言模型幻覺邊界） | truth boundary（真實邊界） | `truth_boundary_ref`、`candidate_hash`、`evidence_ref`、`local_reconstruction_hash`、`verifier_state` | HOLD_REALITY_BOUNDARY_REQUIRED（暫停：需要真實邊界） | REAL_VERIFIED_BY_CLOUD（雲端宣稱真實已驗證） |
| Secret material exposure（秘密材料外洩） | prompt / contract（提示 / 合約） | `redaction_policy_ref`、`prompt_redaction_hash`、`secret_scan_hash`、`seal_hash` | HOLD_SECRET_REDACTION_REQUIRED（暫停：需要秘密遮罩） | API key（應用程式介面金鑰）、token（存取權杖）、會員明文、住戶明文、raw audio/video（原始音訊 / 影片） |

## Release Interpretation

`READY_FOR_HUMAN_REVIEW`（可進人審）不是 EXECUTE（執行）。

`EXECUTE_REQUEST_ONLY`（僅執行請求）不是 EXECUTE（執行）。

`PASS`（通過）只代表 local verifier（本地驗證器）通過目前層級；正式 POS（銷售點系統）、payment（付款）、LINE WORKS（LINE WORKS 通知系統）、member registration（會員註冊）、resident/property action（住戶 / 物業動作）仍需 release condition（發佈條件）與 owner/admin approval ref（所有者 / 管理者核准引用）。

## Public / Secret Boundary

可公開：

- capability governance chain（能力治理鏈）
- candidate-only cloud model boundary（雲端模型僅候選邊界）
- 8D packet（八維封包）欄位分類
- evidence ref/hash/seal（證據引用 / 雜湊 / 封緘）要求
- local reconstruction / verifier（本地重構 / 驗證器）要求
- HOLD / QUARANTINE / DEAD_LETTER（暫停 / 隔離 / 死信）治理

可抽象公開：

- intent-field tensor mapping（意圖場張量映射）
- ancient-math imprint mapping（古數學印記映射）
- route selection heuristics（路由選擇啟發式）
- risk scoring policy（風險評分政策）

應保密：

- WHY_IT_RUNS（核心運作機理）
- complete lookup table（完整查表）
- private weights（私有權重）
- complete routing table（完整路由表）
- router password（路由器密碼）
- API key（應用程式介面金鑰）
- token（存取權杖）
- member plaintext（會員明文）
- resident plaintext（住戶明文）
- raw audio/video（原始音訊 / 影片）
- any data that can re-identify a member or resident（可回推會員或住戶身分之資料）

## Current Status

STATE=P1_RISK_EVIDENCE_FIELD_MATRIX_READY_P2_RELEASE_HOLD（狀態=P1 風險證據場矩陣完成，P2 正式發佈仍暫停）

This matrix（本矩陣） allows product work to continue as dry-run（乾跑）、candidate（候選）、preflight（預檢）、human review（人審） and evidence-sealed handoff（證據封緘交付） only. It does not authorize production side effects（正式營運副作用）.
