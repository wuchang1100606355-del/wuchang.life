# W7TP 小J／ADI／GTP／Moving-V 調適融合 V3 候選設計

狀態：`DESIGN_INTEGRATED_CANDIDATE`

運行上限：`SHADOW_LIVE_OBSERVATION_NO_EFFECT`

目前決定：`HOLD_SHADOW_ONLY`

本文件把小J原先「ADI 生成式程式傳輸記憶體應用」的意圖，接到既有 Moving-V V1 安全分類、V2 生命週期證明與已運行的唯讀 Shadow 觀察器。這是追加式整合，不修改 V1／V2 的原始位元與既有審查包，也不把元件存在誤寫成端到端相容已證明。

## 1. 融合後的單一路徑

```text
小J本機入口與 Intent Field
  -> 治理過的 Intent Cache 中繼資料
  -> Native ADI delta_F / state-root receipt（待正式綁定）
  -> Moving-V：V內／V側／已確認過去分類
  -> V2 三階段生成生命週期與 route proof
  -> GTP 可重建參照與預期 hash（adapter 待證明）
  -> Ollama 模型駐留與主機記憶體唯讀觀察
  -> Shadow 調適預算候選
  -> 總場 review / scoped canary / commit receipt
```

目前真正接通的是「小J本機狀態、治理快取政策、Ollama 駐留狀態與主機記憶體 → Shadow 候選判斷」。ADI `delta_F` producer receipt、GTP 重建 adapter、RAM/VRAM allocator、跨節點水位及 live commit 仍是 `HOLD`。

## 2. 各構件的責任邊界

| 構件 | 在融合設計中的責任 | 當前狀態 |
|---|---|---|
| 小J入口／Intent Field | 提供本機治理、intent、memory、topology 與 hardwall readiness | 已唯讀觀察 |
| Intent Cache | 只保存治理後流程模板，不納入 raw／會員／付款／秘密明文 | ACTIVE 政策中繼資料已觀察 |
| Native ADI | 只供應 founder-native `delta_F` 與 hash-bound state root；Moving-V 不自行計算替代距離 | 候選原始碼存在，runtime receipt 未綁定 |
| Moving-V V1 | 保護 V 內與現在；V 側只做可重建軟卸載候選；過去清理需全部閘門 | 靜態驗證完成 |
| Moving-V V2 | 綁定 route proof、watermark、CAS、lease、引用與三階段生成狀態 | 靜態／隔離驗證完成 |
| GTP | 提供最小重建參照、來源雜湊、重建收據與 expected-hash verdict | adapter required／HOLD |
| Ollama | 只供應當前模型駐留中繼資料；本迴圈不送 prompt、不載入模型 | 已唯讀觀察 |
| Shadow 調適器 | 合併安全與容量訊號，輸出可解釋預算候選及 HOLD 理由 | 已運行，無 effect |
| 總場權限閘門 | 在任何 canary 或 live effect 前要求限定範圍、可撤銷授權與 commit/rollback receipt | inactive／HOLD |

## 3. 空間與時間語義保持不變

- `V 內`：現在與未來預載保護區，禁止卸載或清理。
- `V 側`：只是本輪預測未命中，不代表永遠不會命中；最多提出 RAM／VRAM 可重建軟卸載。
- `尖端後方`：只有被水位確認的過去資料，仍須通過引用、lease、ownership、retention、CAS、canonicality 與 hash 檢查。
- canonical source 永遠保留。生成式輸出、GTP 重建結果與快取 materialization 都不會因此取得 canonical authority。
- 缺收據、來源衝突、時間未對齊、重建 hash 不符或狀態未知，一律 `HOLD`。

## 4. 生成式傳輸的三階段融合

1. `PREDICTED_NOT_GENERATED`：只可提出取消候選，不能刪除資料。
2. `GENERATION_SCHEDULED_OR_RUNNING`：只可提出取消 job，且必須等待終止收據；完成競態由 completion receipt 勝出並重分類。
3. `GENERATION_COMPLETED`：只可對 exclusive、noncanonical、無引用、無 lease、可重建且 hash-bound 的 materialization 提出軟卸載或隔離候選。

這三階段避免把「預測路線改變」、「排程已取消」及「實際資料已安全釋放」混成同一事件。

## 5. 調適迴圈

```text
OBSERVE -> NORMALIZE -> CLASSIFY -> RECOMMEND
        -> REVIEW_GATE -> CANARY_GATE -> COMMIT_RECEIPT
```

目前 phase ceiling 是 `RECOMMEND`：

- `OBSERVE` 只讀本機 loopback 與政策中繼資料。
- `NORMALIZE` 對缺值、不安全狀態、時間衝突 fail closed。
- `CLASSIFY` 只產生空間／時間／生命週期標籤，不產生刪除權限。
- `RECOMMEND` 只產生門檻、V 寬、時間窗或記憶體預算候選，固定 `applies_change=false`。
- 後三階段必須由另案證據、總場授權、可回復 canary 與 hash-bound commit/rollback receipt 才能進入。

數值最佳化次序固定為：資料安全、任務效果、人類可感知延遲、重建可靠度、命中／false miss、系統穩定度，最後才是記憶體與傳輸節省。2 GiB 仍只是可調候選起點。

## 6. 已觀察到的融合狀態

最新有界 Shadow 報告記錄五個樣本：所有必要端點可讀、Intent Field hardwalls 與治理快取政策符合要求，但觀察期間 Ollama active model count 為 0，因此結果正確停在：

```text
reason=HOLD_NO_ACTIVE_MODEL_WORKLOAD
state=HOLD_SHADOW_ADAPTATION
applies_change=false
memory_limit_changed=false
ram_vram_unloaded=false
service_restarted=false
```

這證明本機唯讀訊號可以被同一調適層合併並 fail closed；它不證明有負載時的任務效果、TTFT、命中率、重建可靠度或實際釋放能力。

## 7. 權限與資料硬牆

融合設計固定禁止：

- 非 loopback 網路與遠端寫入。
- prompt 正文、會員明文、付款資料、憑證、token、模型權重及秘密內容讀取。
- 自動送出模型生成請求或載入模型。
- 取消 job、變更 memory limit、RAM/VRAM unload、刪檔、canonical delete、重啟或部署。
- 以測試通過、route proof 或建議值替代總場 execution authority。

目前 active total-field authority profile 為 `false`，所以即使後續樣本達到效能門檻，也只能輸出候選。

## 8. 進入 canary 前的封閉條件

以下全部通過前不進入 live effect：

1. 正式 ADI `delta_F` producer receipt 與 state-root lineage 綁定。
2. GTP reconstruction adapter、expected hash、重建成功率與 p50/p95 latency 證明。
3. preload hit、false miss、絕對 TTFT、任務效果、安全違規零容忍與足量負載樣本。
4. RAM allocator 實際 release receipt；VRAM 另具 GPU fence 與完成競態處理。
5. 重啟、網路分割、late event、重播、重複提交、取消／完成競態與 rollback 測試。
6. 由總場簽發限定節點、限制動作、限制時間、可撤銷的 canary authorization。
7. 每個 effect 都留下輸入雜湊、前後狀態、執行結果及 rollback receipt。

## 9. 設計產物

- 機器可讀契約：`configs/total_field/w7tp_xiaoj_adi_moving_v_adaptive_integration_v3.candidate.json`
- JSON Schema：`schemas/field/w7tp_xiaoj_adi_moving_v_adaptive_integration_v3.schema.json`
- Shadow 實作：`tools/total_field/xiaoj_adi_moving_v_shadow_adapter.py`
- Shadow 設計：`docs/w7tp_algorithms/W7TP_XIAOJ_ADI_MOVING_V_SHADOW_ADAPTATION_V1.md`
- 設計一致性測試：`tests/test_w7tp_xiaoj_adi_moving_v_adaptive_integration_v3.py`

因此「融入設計」的精確狀態是：設計拓撲與 Shadow 訊號路徑已融合；ADI/GTP/live allocator/總場 effect path 尚未整合證明，故保持 `HOLD_SHADOW_ONLY`。
