# W7TP Moving-V 路線、三段式生成與清理橋接矩陣 V2（候選）

狀態：`CANDIDATE_ONLY / NO_INTEGRATION_AUTHORITY`  
目的：把 V2 靜態契約與未來 adapter 邊界分開，防止將欄位相似、單元測試或概念文件誤宣稱為 live 整合。  
V1 邊界：本文件不修改、不覆寫、不重新封裝任何 V1 文件、配置、測試或審查包。

## 1. 判定詞

| 判定 | 含義 |
|---|---|
| `SPECIFIED_STATIC` | V2 文件已定義欄位、不變量與失敗關閉規則；沒有 runtime 證據 |
| `INTERFACE_MAPPABLE_ONLY` | 可提出來源到目標欄位映射；尚未共同執行 |
| `ADAPTER_REQUIRED/HOLD` | 缺少正式 adapter、來源血統、receipt 或故障證據；禁止 live action |
| `SHADOW_REQUIRED/HOLD` | adapter 完成後仍須只觀察 shadow，不允許 cancel/cleanup |
| `CANARY_REQUIRED/HOLD` | shadow 通過後仍須可回復 canary 與明確人類／總場核准 |
| `CONFLICT/HOLD` | 現有語義、身分、時間、所有權或證明互相矛盾 |
| `INTEGRATION_PROVEN` | 跨元件、故障注入、長時間與 rollback 均通過；本輪沒有任何項目達此級 |

所有 live integration 在本候選中固定為 `ADAPTER_REQUIRED/HOLD` 或更嚴格狀態。

## 2. 核心語義橋接

| V2 領域 | 必要正式來源 | V2 消費欄位／收據 | 目前狀態 | 阻擋原因 |
|---|---|---|---|---|
| 三段式生命週期 | 正式 generation scheduler 與 artifact registry | `PREDICTED_NOT_GENERATED`、`GENERATION_SCHEDULED_OR_RUNNING`、`GENERATION_COMPLETED`、stage epoch/sequence | `ADAPTER_REQUIRED/HOLD` | 尚無綁定的 stage transition adapter |
| 階段時間 | scheduler、worker、artifact registry 的同域時間或可驗證映射 | event/need/ingest/stage effective/observed/logical time | `ADAPTER_REQUIRED/HOLD` | 時間域、排序與 clock uncertainty 未共同驗證 |
| Moving-V | 經總場確認的 apex、H、P/R 及原生 ADI delta_F | `inside_v`、`outside_v`、V epoch | `ADAPTER_REQUIRED/HOLD` | V2 不自行計算 ADI 或取得 live apex |
| Route reachable | canonical route graph 與 deterministic verifier | `REACHABLE_PATH_PROOF` | `ADAPTER_REQUIRED/HOLD` | 正式 graph/ruleset roots 與 verifier 血統未綁定 |
| Route predicted miss | route selector | `ROUTE_PREDICTION_RECEIPT` | `ADAPTER_REQUIRED/HOLD` | 只能表示預測未命中，不是排除證明 |
| Route exclusion | 閉世界 route graph、完整 transition set、exclusion verifier | `ROUTE_EXCLUSION_PROOF`、frontier/cut certificate | `ADAPTER_REQUIRED/HOLD` | 未證明 closed-world 完整性與不可達 verifier |
| 預測錯誤分支 | actual route receipt + exclusion proof + graph snapshot | `BRANCH_PREDICTION_ERROR_PROOF`、descendant root | `ADAPTER_REQUIRED/HOLD` | 尚無正式 divergence 與 descendant closure adapter |

## 3. 三段式動作橋接

| 生命週期 | V／route 結果 | V2 候選動作 | Live 依賴 | 狀態 |
|---|---|---|---|---|
| `PREDICTED_NOT_GENERATED` | reachable/V 內 | 保留候選與預載意圖 | predictor candidate store adapter | `ADAPTER_REQUIRED/HOLD` |
| `PREDICTED_NOT_GENERATED` | V 外 route miss | 取消候選 | predictor candidate CAS/receipt adapter | `ADAPTER_REQUIRED/HOLD` |
| `PREDICTED_NOT_GENERATED` | 錯誤分支 proven | 取消整段未生成候選；released bytes=0 | branch candidate index adapter | `ADAPTER_REQUIRED/HOLD` |
| `PREDICTED_NOT_GENERATED` | unknown/conflict | HOLD | fail-closed adapter | `ADAPTER_REQUIRED/HOLD` |
| `GENERATION_SCHEDULED_OR_RUNNING` | reachable/V 內 | 保留工作 | scheduler stage adapter | `ADAPTER_REQUIRED/HOLD` |
| `GENERATION_SCHEDULED_OR_RUNNING` | V 外 miss 或錯誤分支 | 發 cancellation request | scheduler/worker cancellation adapter | `ADAPTER_REQUIRED/HOLD` |
| `GENERATION_SCHEDULED_OR_RUNNING` | cancellation accepted | 等 worker/GPU fence，之後才能提暫存清理 | worker/GPU fence adapter | `ADAPTER_REQUIRED/HOLD` |
| `GENERATION_SCHEDULED_OR_RUNNING` | receipt=`ALREADY_COMPLETED` | 轉入完成階段重新分類 | completion receipt adapter | `ADAPTER_REQUIRED/HOLD` |
| `GENERATION_COMPLETED` | reachable/V 內 | 保留 materialization | artifact/cache pin adapter | `ADAPTER_REQUIRED/HOLD` |
| `GENERATION_COMPLETED` | V 外 predicted miss | 只軟卸載可重建 materialization | GTP/ADI reconstruction + cache adapter | `ADAPTER_REQUIRED/HOLD` |
| `GENERATION_COMPLETED` | proven wrong + 獨占非正典 | 刪除 materialization/獨占 cache | ownership/reverse-ref/delete adapter | `ADAPTER_REQUIRED/HOLD` |
| `GENERATION_COMPLETED` | proven wrong + shared | 只 detach branch reference | atomic graph reference adapter | `ADAPTER_REQUIRED/HOLD` |
| `GENERATION_COMPLETED` | proven wrong + canonical | detach 可解除 edge；內容 retain | canonical lineage adapter | `ADAPTER_REQUIRED/HOLD` |
| `GENERATION_COMPLETED` | unknown/conflict | HOLD | fail-closed adapter | `ADAPTER_REQUIRED/HOLD` |

## 4. Receipt 鏈橋接

任何實體效果必須能形成下列可驗證因果鏈：

```text
STAGE_TRANSITION_RECEIPT
  + V_CLASSIFICATION_RECEIPT
  + ROUTE_PROOF_OR_PREDICTION_RECEIPT
  + BRANCH_OWNERSHIP_SNAPSHOT (若為分支清理)
  -> IMMUTABLE_DECISION_TOKEN
  -> CANCELLATION_RECEIPT (僅 scheduled/running)
  -> WORKER_FENCE_RECEIPT (若已開始生成)
  -> CLEANUP/DETACH/DELETE_COMMIT_RECEIPT
  -> RELEASE_ACCOUNTING_RECEIPT
```

| Receipt／能力 | 必要 producer | Verifier 要求 | 目前狀態 |
|---|---|---|---|
| `STAGE_TRANSITION_RECEIPT` | scheduler/artifact registry | stage sequence、effective time、previous/result hash | `ADAPTER_REQUIRED/HOLD` |
| `V_CLASSIFICATION_RECEIPT` | Moving-V classifier | apex/time domain/ADI/V policy epoch | `ADAPTER_REQUIRED/HOLD` |
| `ROUTE_*_PROOF` | route engine | graph/ruleset/constraint roots、proof verifier hash | `ADAPTER_REQUIRED/HOLD` |
| `BRANCH_OWNERSHIP_SNAPSHOT` | ownership/reverse-reference index | immutable descendant root、完整反向引用 | `ADAPTER_REQUIRED/HOLD` |
| `CANCELLATION_RECEIPT` | scheduler | job/stage/version CAS、明確 outcome | `ADAPTER_REQUIRED/HOLD` |
| `WORKER_FENCE_RECEIPT` | worker/GPU runtime | worker 不再寫入、GPU fence 完成 | `ADAPTER_REQUIRED/HOLD` |
| `COMMIT_RECEIPT` | cleanup transaction engine | CAS、pre/post hash、idempotency、audit chain | `ADAPTER_REQUIRED/HOLD` |
| `RELEASE_ACCOUNTING_RECEIPT` | allocator/storage | unique physical allocation、actual released bytes | `ADAPTER_REQUIRED/HOLD` |
| `FALSE_MISS_RECEIPT` | demand/rehydration observer | prior committed soft unload、actual hit、hash 與 latency | `ADAPTER_REQUIRED/HOLD` |

取消 request 或 cancellation receipt 本身都不得產生 release accounting；只有實際 cleanup commit 後的 allocator/storage 收據可增加 released bytes。

## 5. 分支 ownership 與刪除橋接

| 節點種類 | 必要證據 | 動作 | 禁止事項 | 狀態 |
|---|---|---|---|---|
| 獨占非正典後代 | wrong-branch proof、唯一 owner、無外部 reverse ref、completed stage、非 canonical | delete materialization、獨占 cache／temp | 不得刪 canonical parent；不得重複算共享 allocation | `ADAPTER_REQUIRED/HOLD` |
| 共享後代 | 至少另一 live owner 或外部分支 reverse ref | detach wrong-branch edge only | 不得刪 shared content/allocation | `ADAPTER_REQUIRED/HOLD` |
| canonical 後代 | canonical lineage/root | retain content；僅 detach 安全的非正典 edge | 不得由 V2 刪除 canonical | `ADAPTER_REQUIRED/HOLD` |
| 身分／ownership 未知 | 索引缺失、root 漂移或同 ID 異 hash | HOLD subtree | 不得以 refcount=0 推測可刪 | `CONFLICT/HOLD` |

共享節點 detach 後若成為 orphan，必須建立新 snapshot 與獨立 orphan/GC decision；原錯誤分支 proof 不自動延伸為 orphan delete authority。

## 6. 身分、CAS 與重複資料橋接

V2 需要三種不可混淆的 ID：

- `logical_record_key`：namespace、record ID、record version。
- `materialization_id`：每一完成或部分生成物的唯一 ID。
- `physical_allocation_id`：實際 RAM、VRAM 或磁碟 allocation。

| 風險 | Adapter 必須提供 | 未具備時 |
|---|---|---|
| duplicate record ID | content hash、record version、identity conflict receipt | `HOLD` |
| 同物多個 materialization | 唯一 materialization ID 與 lineage | `HOLD` |
| shared physical allocation | allocation ownership/ref map | `HOLD`，不計釋放 |
| ABA／stale decision | stage、record、job、route、prediction epoch CAS | `HOLD` |
| crash/retry double effect | idempotency key 與 durable commit lookup | `HOLD` |

## 7. Event、Need、Watermark 與節點橋接

| 契約 | 正式依賴 | 目前狀態 | 阻擋條件 |
|---|---|---|---|
| apex 單調前進 | aligned time adapter | `ADAPTER_REQUIRED/HOLD` | 未綁定 time domain 與 rollback 處理 |
| event/need 分離 | event source + predictor | `ADAPTER_REQUIRED/HOLD` | 現有欄位來源與語義未共同驗證 |
| ingest snapshot | node ingestion ledger | `ADAPTER_REQUIRED/HOLD` | ingest sequence 與分類 snapshot 未綁定 |
| safe watermark | required-node membership + node watermarks | `ADAPTER_REQUIRED/HOLD` | 缺節點、partition、stale report 必須停住 |
| late event reconciliation | event-time reconciler | `ADAPTER_REQUIRED/HOLD` | 無 reconciliation receipt 不得 past cleanup |

過去清理不得只比較 need time。正式 adapter 必須同時證明 event time 與 need time均位於 `Wsafe - grace` 之前，且 late event 已完成對帳。

## 8. ADI、GTP、模型與記憶體橋接

| 元件 | 允許的未來角色 | 不得推論 | 狀態 |
|---|---|---|---|
| 原生 ADI | 提供具血統的 `delta_F` 與 state/evidence roots | 名稱相近不代表已綁定 V2 | `ADAPTER_REQUIRED/HOLD` |
| GTP／8D 靜態封包 | 提供可驗證重建參照與預期 hash | 生成式輸出不等於 canonical source | `ADAPTER_REQUIRED/HOLD` |
| 小模型／Codex／Ollama | 未來可能消費 V 內投射 | V2 不授權模型路由或載入 | `ADAPTER_REQUIRED/HOLD` |
| RAM cache | soft unload 與 actual release receipt | resident_bytes 宣稱不等於實際釋放 | `ADAPTER_REQUIRED/HOLD` |
| VRAM/KV cache | 引擎原生生命週期、GPU fence | RAM 規則不能直接套到 GPU tensor | `ADAPTER_REQUIRED/HOLD` |
| 檔案／物件儲存 | temp/materialization delete transaction | 路徑字串或 noncanonical flag 不構成刪除證明 | `ADAPTER_REQUIRED/HOLD` |

## 9. 預算與人類使用體驗橋接

預算調整不得只用記憶體數字或相對 p95。正式 adapter 至少要提供：

- 主機實體容量、保留量與 allocator 真實占用。
- absolute TTFT、p50/p95/p99、可見 stall、排隊與 cancellation latency。
- 生成成功率、任務效果、preload hit、false miss、重建成功率與重建延遲。
- OOM、swap thrashing、GPU eviction/fence failure、backpressure 時間。
- 各生命週期的候選數、進行中工作數、完成 materialization 及 actual released bytes。

門檻未經 shadow/canary 校準前固定 `ADAPTER_REQUIRED/HOLD`；即使合成 gate PASS，也不代表更好的真人使用體驗或可調整 live memory limit。

## 10. 分階段橋接路線

| 階段 | 允許內容 | 通過條件 | 現況 |
|---|---|---|---|
| S0 靜態契約 | V2 文件、schema 設計、純測試向量 | 語義與不變量審查 | `SPECIFIED_STATIC` |
| S1 Adapter contract | 離線 receipt fixture 與 verifier | 每個欄位具正式 producer/root/version | `ADAPTER_REQUIRED/HOLD` |
| S2 Shadow | 讀真實事件但不 cancel、不 detach、不 cleanup | 三階段與 proof 分類可重現；零越權提案 | `SHADOW_REQUIRED/HOLD` |
| S3 Cancellation dry-run | scheduler 接受 no-op request 模擬 | race、already-completed、fence、crash 全通過 | `ADAPTER_REQUIRED/HOLD` |
| S4 RAM/檔案 canary | 可回復的小範圍 temp cleanup/soft unload | 零資料遺失、receipt 冪等、actual bytes 正確 | `CANARY_REQUIRED/HOLD` |
| S5 Branch cleanup canary | 單一人工核准錯誤分支 | 獨占刪、共享 detach、canonical retain 全正確 | `CANARY_REQUIRED/HOLD` |
| S6 VRAM canary | 引擎原生 GPU fence/生命週期 | 零 use-after-free、輸出一致、可回復 | `CANARY_REQUIRED/HOLD` |
| S7 多節點故障 | clock skew、partition、掉線、late event、重啟 | watermark 停止與恢復正確 | `ADAPTER_REQUIRED/HOLD` |
| S8 正式整合 | 總場與人類有限核准 | 長時間 SLO、UX、安全與 rollback 通過 | `HOLD_PENDING_SEPARATE_DECISION` |

後一階段不得用推論或文件敘述補足前一階段缺失證據。

## 11. 立即停止條件

- 把未來或 V 外直接當成永久刪除授權。
- 在 stage transition receipt 缺失時推測生命週期。
- scheduled/running 尚未取得 cancellation receipt 與 worker fence 就清暫存。
- cancellation receipt 後、cleanup commit 前先計算已釋放 bytes。
- `ALREADY_COMPLETED` 仍依 running 規則清暫存。
- 對 shared 或 canonical 節點執行 physical delete。
- descendant/root、route/root、stage epoch 或 record/job version 改變後仍提交舊 decision。
- 同一 physical allocation 被多次計量或同一 idempotency key產生多次效果。
- KEEP_HOLD／CAS failure／未提交 soft unload 產生 false-miss receipt。
- required node 缺失、partition 或 watermark 倒退時仍推進 past cleanup。
- 將 `SPECIFIED_STATIC`、單元測試或合成 PASS 宣稱為 live、UX、總場或整合 PASS。

命中任何一項均為 `HOLD`；不得以降級 canonical、ownership、proof、receipt 或時間安全條件來滿足記憶體目標。

## 12. 本輪精確結論

目前只有 V2 靜態語義與橋接需求被寫明。三段式生成生命週期、route proofs、錯誤分支 descendant closure、取消／fence、detach/delete、實際釋放量、false miss、跨節點時間與使用體驗均沒有 live integration 證據，全部保持 `ADAPTER_REQUIRED/HOLD`。本文件本身不具取消、刪除、部署、模型載入、記憶體調整或總場核准權限。
