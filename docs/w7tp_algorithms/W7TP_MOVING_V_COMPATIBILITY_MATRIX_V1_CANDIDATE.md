# W7TP 移動式 V 字整合相容性矩陣 V1（候選）

狀態：`CANDIDATE_ONLY / NO_INTEGRATION_AUTHORITY`  
目的：防止把從未共同執行的設計誤寫成已整合系統。

## 證據等級

| 等級 | 定義 |
|---|---|
| `PROVEN_ISOLATED` | 只證明單一純邏輯或單一元件在隔離測試成立 |
| `INTERFACE_COMPATIBLE_ONLY` | 欄位與邊界可映射，但沒有共同執行證據 |
| `SHADOW_PROVEN` | 已以實際流量只觀察、不改狀態，結果符合 |
| `CANARY_PROVEN` | 已在可回復的小範圍實際執行並通過安全門檻 |
| `INTEGRATION_PROVEN` | 跨元件、故障注入與長時間測試均通過 |
| `UNPROVEN` | 尚無足夠證據 |
| `CONFLICT` | 現有語義或權限互相衝突，需先修改契約 |

`PROVEN_ISOLATED` 不得被描述成 `INTEGRATION_PROVEN`。

## 元件現況

| 元件／設計 | 目前等級 | 已知事實 | 未證明／風險 | 本輪動作 |
|---|---|---|---|---|
| 移動式 V 分類與壓力規劃純函式 | `PROVEN_ISOLATED` | 尖端、V 內、V 側、過去、水位、CAS、lease、hash 與背壓已有隔離測試 | 沒有真實快取、模型或節點資料 | 僅保存候選與測試 |
| 創辦人原生 ADI `delta_F` | `INTERFACE_COMPATIBLE_ONLY` | 可提供非負整數狀態距離；禁止代理幾何／相似度 | 目前所見實作位於 optimized successor candidate，正式血統與 active binding 尚未確認 | V 只接受已算好的 `delta_F`，不匯入候選 ADI runtime |
| GTP／8D 靜態封包重建 | `INTERFACE_COMPATIBLE_ONLY` | 可用 reference + hash 描述重建需求 | 盤點所見 temporal 綁定仍不完整，且未做真實 TTL/replay、false miss 重建、延遲、成本與語意一致性測試 | 僅要求參照與 hash，不呼叫生成模型 |
| 既有小模型動態上下文／可調記憶體預算 | `UNPROVEN` | 既有構件有 TTL/LRU/anchor 或容量控制概念；本候選以 2 GiB 作合成起點 | 尚無 V 狀態、event time、水位、lease/CAS/refcount；任何數值尚未以真實 UX/效能校準 | 不改 adapter、不改容量 |
| 裝置韌性與記憶體壓力 | `UNPROVEN` | 有裝置處理與稽核候選基礎 | 尚缺 live RAM/VRAM 壓力分數、背壓、重試/DLQ 與本 V 契約綁定 | 不接服務 |
| 多節點非同步時間對齊 | `UNPROVEN` | 本候選定義最小安全水位與單調尖端 | 未驗證時鐘偏移、節點離線、網路分割、late event | 只測純函式水位規則 |
| RAM 實際卸載 | `UNPROVEN` | 有非破壞性動作契約 | 未做 shadow/canary、崩潰恢復、double-free 測試 | 禁止 live eviction |
| VRAM/KV cache 實際卸載 | `UNPROVEN` | 僅有存放層級模型 | 未綁定推論引擎、張量生命週期或 GPU fence | 禁止 live eviction |
| Ollama／Codex／本地模型路由 | `UNPROVEN` | 可作未來消費者 | 尚未驗證提示、工具狀態與預載命中關係 | 不改模型或路由 |
| 總場治理 | `INTERFACE_COMPATIBLE_ONLY` | 可用候選審查包、hash 與明確禁令 | 尚無本設計 final decision | 保持 pending/hold |
| 專利／時空概念文件 | `INTERFACE_COMPATIBLE_ONLY` | 提供概念來源與術語 | 文件敘述不是可執行或效能證據 | 只作 provenance，不當 runtime dependency |

## 跨元件必要契約

| 組合 | 接合前必須證明 | 尚未具備時的狀態 |
|---|---|---|
| V + ADI | `delta_F` 規則版本、state root、epoch 與 V 分類收據可重現 | `HOLD_ADI_BINDING_UNPROVEN` |
| V + GTP | 每個卸載候選有耐久來源、最小封包、預期 hash；false miss 可重建且 hash 一致 | `HOLD_RECONSTRUCTION_UNPROVEN` |
| V + 動態上下文 | event time 與 logical time 對應、CAS、lease、refcount、pin、冪等狀態機 | `HOLD_CACHE_LIFECYCLE_UNPROVEN` |
| V + 裝置韌性 | 真實記憶體壓力、高低水位、界限隊列、背壓與 DLQ | `HOLD_PRESSURE_CONTROL_UNPROVEN` |
| V + 多節點 | active node 集合、最小安全水位、時鐘倒退、partition 與 late-event 規則 | `HOLD_TIME_ALIGNMENT_UNPROVEN` |
| V + RAM/VRAM | shadow 觀察零誤清，之後可回復 canary；canonical source 永不受影響 | `HOLD_LIVE_EVICTION_UNPROVEN` |
| V + 總場 | 規格、測試、紅隊與 manifest 經總場決策 | `HOLD_PENDING_TOTAL_FIELD_DECISION` |

額外衝突隔離：原生 ADI `deleted_refs`／tombstone 不得映射為快取卸載。本候選只允許獨立的 `materialization_evictions`，並固定 `canonical_action=RETAIN`。

## 分階段驗證順序

| 階段 | 允許內容 | 通過條件 | 目前狀態 |
|---|---|---|---|
| S0 隔離邏輯 | 純函式、靜態配置、合成資料 | 邊界與安全不變量全通過 | `PASS_LOCAL_ISOLATED_ONLY` |
| S1 契約對接 | 離線讀取 ADI/GTP 合成收據，不碰 live cache | 每一欄位有來源、版本與 hash；無代理距離 | `NOT_RUN` |
| S2 Shadow | 真實事件只分類和記錄，不卸載 | 零保護區提案、可量測 hit/false miss、水位無倒退 | `NOT_AUTHORIZED` |
| S3 RAM Canary | 可回復的小範圍軟卸載 | 零資料遺失、零 double-free、重建 p95 達標 | `NOT_AUTHORIZED` |
| S4 VRAM Canary | 推論引擎原生生命週期內的小範圍卸載 | 無 use-after-free、輸出一致、GPU fence 正確 | `NOT_AUTHORIZED` |
| S5 多節點故障測試 | 時鐘偏移、partition、節點掉線、重啟 | 安全水位停止正確、恢復冪等、無越權清理 | `NOT_AUTHORIZED` |
| S6 正式整合 | 經總場與人類核准的有限部署 | 長時間 SLO、安全指標及 rollback 全通過 | `NOT_AUTHORIZED` |

任何階段不得因下一階段尚未執行而用推論補足證據。

## 立即停止條件

- V 內或現在保護資料出現任何卸載提案。
- prediction epoch、record version、來源 hash 或 ADI 血統不一致。
- 節點水位倒退、缺失或網路分割卻仍推進回收。
- 無法從耐久來源重建，或重建 hash 不符。
- 2 GiB 壓力下候選不足卻嘗試清 V 內資料。
- 任何程式要求永久刪除 canonical source。
- 將本機測試 `PASS` 宣稱為總場、實機或多節點 `PASS`。
- 把 2 GiB、60 秒、V 寬或任何合成測試數字誤宣稱為不可調整的創辦人常數。

上述任一情況皆須 `HOLD`，不得自動降級安全條件。
