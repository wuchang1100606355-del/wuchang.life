# W7TP 系統意圖場 L03 確定性核心 Shadow V1 候選

## 狀態與邊界

- 階段：`L03_DETERMINISTIC_CORE_SHADOW`
- 狀態：`CANDIDATE_SHADOW_ONLY`
- authority：`NONE`；正式決策權仍屬總場。
- active authority pointer：未建立、未修補、未修改。
- 外部 I/O、服務、模型、資料庫、記憶體效果、部署、重啟與遠端寫入：全部禁止。
- 本候選不建立第二個總場、會員主檔或平行 canonical registry。

控制器位於 `tools/total_field/w7tp_system_intent_field_deterministic_shadow.py`。它只接收 reference-only request、呼叫端提供的記憶體內 scoped state mapping，以及通過 Schema 的版本化規則 bundle。模組本身不讀檔、不讀環境、不接網路、不接資料庫、不取時鐘、不用隨機數，也沒有 model callable 或 model adapter 入口。

## 固定處理順序

1. 驗證 request 是封閉、reference-only 且所有敏感資料旗標為 `false`。
2. 驗證規則 bundle 的版本、controller identity 與全數 no-effect 權限旗標。
3. 以 `intent_code` 做精確查表；無規則立即回 `LOCAL_HOLD_INTENT_UNRESOLVED`。
4. 只有意圖已解析時才從呼叫端提供的 mapping 取得該 `scope_ref` 的 verified state。
5. Gate 1 驗證 canonical lock、scope binding、evidence、hard risk、state version 與 state hash CAS。
6. Gate 2 比對 target effect 與最小產品差分；無差分回 `BUILD_NOT_REQUIRED`。
7. 有確定性 reference delta 時，Gate 3 要求人類確認；未確認或拒絕即 HOLD。
8. 只有三閘門通過才產生 reference-only minimum delta 候選；仍不套用任何變更。
9. 輸出 canonical JSON SHA-256 decision trace；trace 不含原始輸入或私密狀態值。

## 路由語意

版本化 bundle 固定三種模板：

- `NO_STATE_CHANGE`：已知查詢路由，無最小差分即 `BUILD_NOT_REQUIRED`。
- `CANDIDATE_REFERENCE_REPLACE`：只產生 `REPLACE_REFERENCE` minimum delta，authority 為 `NONE`。
- `UNKNOWN_SLOT_HOLD`：L03 不呼叫模型，固定回 `LOCAL_HOLD_UNKNOWN_SLOT_REQUIRES_L04`。

即使規則是已知意圖，只要 request 宣告 unknown slot，L03 也只會 HOLD。模型只可能在獨立的 L04 候選工作包中處理縮減後的 unknown-delta packet；本包沒有模型介面。

## 三閘門與 fail-closed

| 閘門 | PASS 條件 | HOLD／終止 |
|---|---|---|
| Gate 1 canonical lock | state verified、scope bound、canonical locked、evidence complete、no hard risk、CAS 相符 | `HOLD_STATE_UNVERIFIED`、`HOLD_COORDINATE_UNBOUND`、`HOLD_CANONICAL_LOCK_FAILED`、`HOLD_EVIDENCE_INCOMPLETE`、`HOLD_HARD_RISK`、`HOLD_STATE_VERSION_RACE` |
| Gate 2 intent/product gap | target effect 與規則一致且存在最小差分 | effect 不符即 `HOLD_TARGET_EFFECT_MISMATCH`；無差分即 `BUILD_NOT_REQUIRED`；unknown slot 即本地 HOLD |
| Gate 3 human review | `CONFIRMED` | `HOLD_HUMAN_CONFIRMATION_REQUIRED` 或 `HOLD_HUMAN_REJECTED` |

Schema unknown field、版本不支援、禁止資料旗標、規則 bundle 不完整或權限升高都在 scoped state load 前 HOLD。未解析意圖同樣不載入 scoped state，也不呼叫模型。

## 重播、重複與競態

- 序列化：sorted-key compact ASCII JSON。
- 雜湊：SHA-256。
- 控制器不使用時間或隨機輸入，所以相同 request、state snapshot 與 rule bundle 產生完全相同的結果與 trace hash。
- 重複提交只回相同 no-effect trace，不產生新效果。
- state version 或 hash 不等於 request 的 expected CAS 時，固定回 `HOLD_STATE_VERSION_RACE`。

## 資料與治理界線

跨界只允許 intent code、role binding／8D reference、state reference、版本、hash、minimum delta、重構條件與驗證指示。禁止 raw user input、full context、known private state value、會員明文、付款秘密、credential 或 token。

會員身分權威仍屬協會治理來源；服務、POS、設備與模型只使用 role binding 或 8D identity packet reference。小J／W7TP 技術所有權、公益使用授權與 runtime authority 保持分離；本候選不推定任何權利移轉。

## 產物關係

- 規則與模板 bundle：`configs/total_field/w7tp_system_intent_field_deterministic_shadow_v1.candidate.json`
- bundle Schema：`schemas/field/w7tp_system_intent_field_deterministic_shadow_v1.schema.json`
- 控制器：`tools/total_field/w7tp_system_intent_field_deterministic_shadow.py`
- 測試：`tests/test_w7tp_system_intent_field_deterministic_shadow_v1.py`
- trace 與驗證報告：本 L03 工作包目錄。

## 回復程序

停止使用本地 Shadow controller，移除呼叫端對本候選檔案的測試引用即可。因為未建立 active pointer、未接服務且 effects 全為 `false`，不需要 runtime rollback、資料庫 rollback 或服務重啟。
