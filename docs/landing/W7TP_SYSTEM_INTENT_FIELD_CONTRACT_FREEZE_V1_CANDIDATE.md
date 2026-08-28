# W7TP 系統意圖場契約定版 V1 候選

狀態：`CANDIDATE_CONTRACT_FREEZE_NO_EFFECT`

工作包：`L02_CONTRACT_AND_FIELD_FREEZE`

目前決定：`CONTRACTS_FROZEN_CANDIDATE_STATIC_REVIEW_REQUIRED`

本文件只說明 D1 Intent Root、真實 minimum delta、D8 envelope、receipt chain 與版本遷移規則的候選定版。它不建立第二個總場、第二個會員主檔或平行 canonical registry，也不部署、不重啟、不寫資料庫、不呼叫模型、不改記憶體或 active pointer。

## 1. 正典與權限邊界

- 系統維持一個受治理意圖場。
- 會員身分權威仍屬協會治理的會員身分來源。
- 服務、POS、設備、Odoo 與模型只使用 role binding 或 8D identity packet reference，不取得會員主檔權威。
- 不複製完整會員明文。
- 小J／W7TP 技術所有權、公益使用授權與 runtime authority 分離；沒有正式移轉或授權文件不得推定移轉。
- 模型、adapter、裝置、測試與 route proof 均沒有正式效果權限。

目前 `runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json` 不存在，authority profile 為 inactive。本包因此固定：

```text
formal_landing_allowed=false
applies_change=false
memory_effect=false
database_write=false
deployment=false
restart=false
remote_write=false
```

## 2. Intent Root

`schemas/field/w7tp_system_intent_root_v1.schema.json` 封閉 D1 intent root：

- `result` 只保存結果引用、結果代碼與 SHA-256。
- `subject` 只接受 anonymous role ref、role binding ref 或 8D identity packet ref。
- `scene` 只保存場景、節點與服務引用。
- `known_state_refs`、`constraints`、`acceptance` 與 `target_product_effect` 均為受治理引用或封閉候選描述。
- 原始輸入、會員明文、秘密內容與正式效果權限固定為 false。
- D1 未解析時固定 `HOLD_BEFORE_STATE_LOAD_OR_MODEL_CALL`，必須在載入私密狀態或呼叫模型前停止。

## 3. Minimum Delta

`schemas/field/w7tp_system_intent_minimum_delta_v1.schema.json` 只允許 refs、差分操作、hash 與 unknown slot 定義：

- `minimum_delta_state=NONE` 時 affected coordinates、changed state 與 unknown slots 必須全空，結果為 `BUILD_NOT_REQUIRED`。
- `minimum_delta_state=DELTA_REQUIRED` 時至少有一個 affected coordinate，且 changed state 或 unknown slots 至少一項非空。
- changed state 只傳 previous/candidate refs 與 candidate SHA-256，不傳完整狀態值。
- 模型封包只包含 intent/current state refs、stable refs、affected coordinates、unknown slots、效果引用、重構／驗證條件與輸出 Schema。
- raw input、full context、known private state、member plaintext、payment secret 與 credential/token 均禁止。
- 模型輸出 authority 固定 `CANDIDATE_ONLY`，minimum delta authority 固定 `NONE`。

## 4. D8 Envelope

`schemas/field/w7tp_system_intent_d8_envelope_v1.schema.json` 固定依序封裝 D1–D7 refs：

```text
D1 -> D2 -> D3 -> D4 -> D5 -> D6 -> D7
```

每一維只有 `dimension`、`state_ref` 與 `state_sha256`。封包另包含 intent root、current state root、minimum delta、重構條件、驗證指示、receipt chain、nonce、期限與 verifier refs。完整上下文、會員明文、秘密與所有效果旗標固定拒絕。

## 5. Receipt Chain

`schemas/field/w7tp_system_intent_receipt_chain_v1.schema.json` 有三種封閉狀態：

1. `HOLD`：只有 decision receipt，transition/effect/rollback 必須為 null。
2. `BUILD_NOT_REQUIRED`：只有無建構需求 decision receipt，不得夾帶 effect。
3. `CANDIDATE_READY_FOR_TOTAL_FIELD`：decision、transition、no-effect effect 與 rollback receipt 全部必須存在。

本版本 effect receipt 固定：

```text
effect_type=NONE
effect_result=NOT_APPLIED_CANDIDATE_ONLY
applies_change=false
formal_authority=false
```

重播與競態固定採 single-use nonce、idempotency key、原 receipt 返回或 HOLD、terminal receipt 與 CAS precedence；不得用 last-writer-wins 產生新 effect。

## 6. 版本遷移

`configs/total_field/w7tp_system_intent_field_version_migration_rules_v1.candidate.json` 只允許追加式 successor：

- exact version 只驗證，不轉換。
- semantic predecessor 必須有明確欄位 mapping、保留來源並重新驗證。
- unknown field、unsupported version、lossy mapping、authority increase、forbidden material 或 hash mismatch 一律 HOLD。
- receipt chain 只能 append successor refs，不覆寫歷史。
- 不自動遷移、不自動 promotion。
- rollback 是保留前一 Schema 並丟棄候選 migration。

## 7. 產物

- Contract freeze manifest：`configs/total_field/w7tp_system_intent_field_contract_freeze_v1.candidate.json`
- Manifest Schema：`schemas/field/w7tp_system_intent_field_contract_freeze_v1.schema.json`
- Intent Root Schema：`schemas/field/w7tp_system_intent_root_v1.schema.json`
- Minimum Delta Schema：`schemas/field/w7tp_system_intent_minimum_delta_v1.schema.json`
- D8 Envelope Schema：`schemas/field/w7tp_system_intent_d8_envelope_v1.schema.json`
- Receipt Chain Schema：`schemas/field/w7tp_system_intent_receipt_chain_v1.schema.json`
- Migration Rules：`configs/total_field/w7tp_system_intent_field_version_migration_rules_v1.candidate.json`
- Migration Rules Schema：`schemas/field/w7tp_system_intent_field_version_migration_rules_v1.schema.json`
- Tests：`tests/test_w7tp_system_intent_field_contract_freeze_v1.py`

## 8. 後續邊界

L02 通過只代表 closed schemas、unknown-field rejection、負向測試與靜態總場審查閉合。它不證明 runtime、ADI producer、GTP reconstruction、模型品質、效能、effect receipt 執行或正式 authority 已完成。

下一步只能產生 L03 entry 候選決定；若使用者沒有另行指定 L03 工作包，必須停止。
