# W7TP 小J／ADI／Moving-V Shadow 調適融合 V1

狀態：`SHADOW_ONLY / OBSERVE_RECOMMEND_NO_EFFECT`  
目的：把小J Intent Field、既有治理快取政策、Ollama 實際載入狀態、主機記憶體與 Moving-V 預算安全閘門接成可重複觀察的旁路控制迴圈。

## 1. 本輪融合範圍

```text
taiji-gateway :8081/:9002 ─┐
XiaoJ Intent Field :9107  ├─> shadow sampler
Taiji Claw capability :9004 ┤
Ollama process state :11434 ┤
/proc/meminfo              ┤
active intent cache policy ┘
                              -> Moving-V budget gate
                              -> candidate recommendation
                              -> immutable runtime report
```

融合器讀取的資料均為本機 loopback 或本機政策中繼資料。它不讀取提示正文、會員明文、憑證、token、模型權重或秘密檔案，也不對模型送出生成請求。

## 2. 不可解除的 Shadow 硬牆

候選配置與程式同時固定下列欄位為 `false`：

- `applies_change`
- `memory_limit_change_allowed`
- `job_cancellation_allowed`
- `ram_vram_unload_allowed`
- `file_delete_allowed`
- `canonical_source_delete_allowed`
- `service_restart_allowed`
- `remote_write_allowed`

任何非 loopback URL、狀態不是 `SHADOW_ONLY`、模式不是 `OBSERVE_RECOMMEND_NO_EFFECT`，或任一實體效果欄位被改成 `true`，配置會在取樣前直接拒絕。

## 3. 調適判定

每一輪先確認：

1. gateway、Intent Field、Ollama 及 Claw capability 端點可讀。
2. Intent Field 的 intent、memory、topology、policy gate 均已載入。
3. hardwalls 啟用，cloud／PII／secrets 均禁止。
4. 既有 intent-flow cache policy 為 ACTIVE，且禁止 raw plaintext、付款、秘密及會員明文。
5. 主機可用記憶體與 Ollama 實際載入模型數可取得。

判定規則：

- 必要端點或政策不安全：`HOLD`。
- 主機可用量低於保留量：只提出向下調整候選，不套用。
- 沒有載入中的模型：維持目前候選上限，不用閒置狀態推論效能。
- 有模型負載但缺少命中率、false miss、重建、延遲與安全樣本：只提出向上候選並 `HOLD`。
- 完整效能證據通過既有 Moving-V 預算閘門：輸出 `PASS_BUDGET_ADJUSTMENT_CANDIDATE_ONLY`，仍保持 `applies_change=false`。

2 GiB 繼續只是目前候選上限；最小值、最大值、步幅與保留量均可在候選配置中調整，但任何 live 套用仍須另案總場決定及可回復 canary。

## 4. 執行方式

預設執行五次、每次間隔 0.25 秒，並在 `runtime/reports` 產生唯一 JSON 報告：

```bash
python3 tools/total_field/xiaoj_adi_moving_v_shadow_adapter.py
```

只在終端顯示結果、不寫報告：

```bash
python3 tools/total_field/xiaoj_adi_moving_v_shadow_adapter.py --no-write
```

較長的觀察仍保持有界，例如 60 次、每五秒一次：

```bash
python3 tools/total_field/xiaoj_adi_moving_v_shadow_adapter.py \
  --samples 60 --interval-seconds 5
```

## 5. 進入 canary 前仍需的證據

- 綁定正式 ADI `delta_F` producer receipt。
- 取得 preload hit、false miss、重建 hash／延遲與絕對 TTFT 分位數。
- 建立 RAM allocator 的實際釋放收據；VRAM 另需 GPU fence。
- 通過重啟、網路分割、late event、重複提交及 rollback 測試。
- 取得可限定範圍、可撤銷的總場 runtime decision receipt。

在此之前，Shadow 調適的正確產物是「可解釋候選」與「HOLD 原因」，不是實體記憶體變更。
