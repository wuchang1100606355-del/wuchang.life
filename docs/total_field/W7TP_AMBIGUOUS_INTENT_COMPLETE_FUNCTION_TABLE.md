# W7TP AMBIGUOUS INTENT COMPLETE FUNCTION TABLE
# 歧義意圖候選發現完整功能表

STATE: FUNCTION_TABLE_DRAFT
MODE: READONLY_INVENTORY
FINAL_AUTHORITY: ΩGI_TOTAL_FIELD

## 1. 核心功能

| ID | Function | 中文名稱 | Status | Description |
|---|---|---|---|---|
| F01 | ORIGINAL_INTENT_PRESERVED | 原始意圖保全 | SPEC_CONFIRMED | 保留使用者原始輸入，不得以 AI 誤解覆蓋 |
| F02 | AMBIGUITY_CANDIDATE | 歧義候選生成 | SPEC_CONFIRMED | 對錯字、歧義、省略語產生候選解讀 |
| F03 | BEAUTIFUL_MISREAD_CANDIDATE | 美麗誤會候選 | SPEC_CONFIRMED | AI 誤解但產生有價值功能時，標記為候選 |
| F04 | USER_CONFIRMATION_REQUIRED | 使用者確認 Gate | SPEC_CONFIRMED | 候選升級前必須取得使用者確認 |
| F05 | AI_CANDIDATE_ONLY | AI 僅候選 | SPEC_CONFIRMED | AI 不得成為最終裁決者 |
| F06 | OMEGA_GI_FINAL_AUTHORITY | ΩGI 最終裁決 | SPEC_CONFIRMED | 最終裁決回總場 / 主權治理主體 |
| F07 | H64_TD_REF_ONLY | H64-TD 僅引用 | SPEC_CONFIRMED | 僅使用 trade_secret_ref，不揭露 codebook / mapping / rules |

## 2. 已存在之誤讀風險場景

| ID | Scenario | Risk | Existing Evidence |
|---|---|---|---|
| R01 | Production Release HOLD | PASS 被誤讀為 deploy authority | landing_gap_inventory |
| R02 | Wish Tree Donate Naming | donate 被誤讀為現金或私人移轉 | wuchang_total_factory_retrieval |
| R03 | Wish Coin / Grant Naming | coin / grant 被誤讀為 stored value | wuchang_total_factory_retrieval |
| R04 | Global Agent Domain Executor | executor authorization 被誤讀為 broad deploy authority | intent_reconstruct_jump |
| R05 | Member Portability | portability 被誤讀為 cross-site tracking | W7TP_PORTABLE_XIAOJ_MEMBER_AGENT_SPEC_V1 |
| R06 | Guest Wi-Fi Presence | Wi-Fi presence 被誤讀為 identity proof | W7TP_PORTABLE_XIAOJ_MEMBER_AGENT_SPEC_V1 |
| R07 | Revenue Sharing | revenue sharing 被誤讀為 data monetization | W7TP_GROUP_MEMBER_REVENUE_SHARING_RULE_V1 |

## 3. Runtime Gap

目前功能狀態：

L1_DOC_SPEC: TRUE
RUNTIME_REFERENCES: TRUE
TOOLS_IMPLEMENTATION_CONFIRMED: FALSE
CONTROLLERS_IMPLEMENTATION_CONFIRMED: FALSE
SCHEMA_IMPLEMENTATION_CONFIRMED: FALSE

本功能目前為總場治理規格與風險辨識表。
若要成為完整 runtime 功能，仍需補足：

- original intent storage schema
- ambiguity candidate schema
- beautiful misread candidate schema
- user confirmation gate
- deadbox / quarantine record
- seal / hash evidence chain
- runtime tool or controller wiring

## 4. Required Runtime Components

| Component | Required |
|---|---|
| Original Input Keeper | TRUE |
| Ambiguity Candidate Generator | TRUE |
| Beautiful Misread Candidate Generator | TRUE |
| Misread Risk Classifier | TRUE |
| User Confirmation Gate | TRUE |
| Deadbox / Quarantine | TRUE |
| Evidence Seal | TRUE |
| Runtime Wiring | TRUE |

## 5. Boundary

FORBIDDEN:

- 不得把 AI 誤解直接當成使用者原始意圖。
- 不得自動覆蓋原始輸入。
- 不得未確認即寫入主發明。
- 不得未確認即 commit/tag。
- 不得將候選功能宣稱為 production。
- 不得揭露 H64-TD codebook / mapping / table / rules。

FINAL_DECISION: COMPLETE_FUNCTION_TABLE_READY
