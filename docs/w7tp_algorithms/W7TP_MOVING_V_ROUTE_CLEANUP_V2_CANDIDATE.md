# W7TP Moving-V 路線與三段式生成清理 V2（候選）

狀態：`CANDIDATE_ONLY / STATIC_SPEC_ONLY`  
權限：`NO_RUNTIME_AUTHORITY / NO_LIVE_DELETE / NO_DEPLOYMENT`  
與 V1 的關係：本文件是新候選，不修改、不覆寫、也不宣稱取代任何 V1 來源。

## 1. 創辦人校正後的核心語義

時間先決定檔案或生成物所處的生命週期階段；Moving-V 與 route 證據只決定該階段應 `retain`、`cancel`、`soft unload`、`detach` 或 `cleanup`，不得把「未來」一概視為可刪除。

唯一三個正式階段為：

1. `PREDICTED_NOT_GENERATED`：只有預測候選、路線節點或生成意圖，尚未建立生成工作及 materialization。
2. `GENERATION_SCHEDULED_OR_RUNNING`：已排入生成排程或正在生成；可能已有 worker、GPU/KV 狀態、暫存檔或部分輸出。
3. `GENERATION_COMPLETED`：生成工作已產生完成收據及可識別 materialization。

對已證明預測錯誤的延伸分支：

- 未生成：取消候選，不虛構「刪除檔案」或「釋放 bytes」。
- 已排程／生成中：送出 cancellation request，等待具約束力的 cancellation receipt；只有確認 worker fence 完成後才能清理獨占暫存，且實際清理收據前不得計入已釋放量。
- 已完成：刪除該錯誤分支獨占的非正典節點、materialization 與快取；共享節點只解除該分支引用；canonical 節點只解除可解除的非正典關聯並永久保留內容。

## 2. 時間、V 與生命週期是不同維度

每筆記錄分別具有：

- `event_time`：來源事件發生時間。
- `need_time`：預測系統需要該候選或生成物的時間；Moving-V 的前後位置以此判斷。
- `ingest_time` 與 `ingest_seq`：本節點觀察到事件的時間及順序。
- `stage_effective_time`：該生命週期階段正式生效的時間。
- `stage_observed_time`：本節點收到階段收據的時間。
- `logical_time`、`time_domain_id`：跨節點排序及避免不同時間域互相比較。

Moving-V 尖端 `T_e` 是同一 `time_domain_id` 下、經對齊且單調前進的現在。定義：

```text
delta_t(r) = need_time(r) - T_e
inside_v(r) = 0 < delta_t <= H AND delta_F(r) <= P_e(delta_t)
outside_v(r) = 0 < delta_t <= H AND P_e(delta_t) < delta_F(r) <= R_e(delta_t)
```

`inside_v` 是預載保護範圍；`outside_v` 最多表示路線預測未命中，不能單獨證明路線不可能，也不能單獨授權永久刪除。

## 3. 三段式狀態機與階段收據

允許的主要轉移：

```text
PREDICTED_NOT_GENERATED
  -> GENERATION_SCHEDULED_OR_RUNNING
  -> GENERATION_COMPLETED
```

取消是帶收據的旁支結果，不允許直接把階段欄位倒寫：

```text
PREDICTED_NOT_GENERATED -> PREDICTION_CANDIDATE_CANCELLED

GENERATION_SCHEDULED_OR_RUNNING
  -> CANCELLATION_REQUESTED
  -> CANCELLED_BEFORE_START | CANCELLED_DURING_RUN | ALREADY_COMPLETED

ALREADY_COMPLETED -> 重新讀取完成收據 -> GENERATION_COMPLETED 規則
```

每個 `STAGE_TRANSITION_RECEIPT` 必須包含：

```text
transition_receipt_id
logical_record_key
materialization_id_or_null
generation_job_id_or_null
from_stage
to_stage
stage_epoch
stage_sequence
event_time
need_time
ingest_time
ingest_sequence
stage_effective_time
stage_observed_time
logical_time
time_domain_id
apex_time
safe_watermark
prediction_epoch
route_epoch
record_version
expected_previous_state_hash
resulting_state_hash
issuer_id
receipt_hash
```

不變要求：`stage_sequence` 嚴格遞增；`stage_effective_time` 不倒退；同一 idempotency key 最多產生一個有效結果；缺少合法前一階段收據時一律 `STAGE_UNKNOWN_HOLD`。

## 4. 路線證明四態

### 4.1 `FUTURE_REACHABLE_PROVEN`

具有可由正式 verifier 重播的 `REACHABLE_PATH_PROOF`。若同時位於 V 內，狀態為 `FUTURE_REACHABLE_V_PROTECTED`，必須保留／預載。

### 4.2 `FUTURE_ROUTE_PREDICTED_MISS`

具有 `ROUTE_PREDICTION_RECEIPT`，但沒有不可達證明；通常位於 V 外。它只代表未被目前路線選中，可取消尚未生成的候選或軟卸載可重建的已完成 materialization，不得宣稱永遠不會命中。

### 4.3 `FUTURE_ROUTE_EXCLUDED_PROVEN`

具有可驗證 `ROUTE_EXCLUSION_PROOF`。排除證明必須基於閉世界路線圖、固定 route epoch／roots、完整允許轉移集合及能證明目標在有效時間窗內不可達的 frontier/cut certificate。搜尋逾時、top-k 遺漏、低相似度或 V 外都不是排除證明。

### 4.4 `FUTURE_ROUTE_UNKNOWN_HOLD`

證明缺失、過期、視窗未涵蓋 need time、route roots 不同、時間域不明、verifier 不可用或證據互相矛盾。未知未來一律 HOLD。

若相同 route epoch/root 下 `REACHABLE_PATH_PROOF` 與 `ROUTE_EXCLUSION_PROOF` 同時成立，或 V 內受保護節點同時被宣稱排除，狀態為 `PROOF_CONFLICT_HOLD`，不得取消、卸載或刪除。

## 5. 路線證明契約

所有 route proof 至少包含：

```text
proof_id
proof_type
proof_version
prediction_epoch
route_epoch
route_graph_root
route_ruleset_root
start_state_root
target_state_or_predicate_hash
constraint_root
valid_from
valid_until
need_time_covered
closed_world_declared
witness_path_or_cut_certificate_root
verifier_id
verifier_binary_hash
proof_payload_hash
proof_hash
```

`ROUTE_EXCLUSION_PROOF` 另外必須包含 `complete_transition_set_root`、`visited_frontier_root`、`unreachable_target_predicate_hash` 與 `search_bound`。任何 route graph、ruleset、constraint、membership 或 epoch 改變，舊排除證明立即失效。

## 6. 階段 × 路線決策矩陣

| 生命週期 | V／route 狀態 | 唯一允許結果 |
|---|---|---|
| `PREDICTED_NOT_GENERATED` | reachable 且 V 內 | `RETAIN_PREDICTION_AND_PRELOAD_INTENT` |
| `PREDICTED_NOT_GENERATED` | V 外預測未命中 | `CANCEL_PREDICTION_CANDIDATE` |
| `PREDICTED_NOT_GENERATED` | 已證明錯誤分支 | `CANCEL_BRANCH_CANDIDATES`；釋放量固定為 0 |
| `PREDICTED_NOT_GENERATED` | unknown/conflict | `KEEP_HOLD` |
| `GENERATION_SCHEDULED_OR_RUNNING` | reachable 且 V 內 | `RETAIN_GENERATION_JOB` |
| `GENERATION_SCHEDULED_OR_RUNNING` | V 外預測未命中或已證明錯誤 | `REQUEST_CANCELLATION`；等待 receipt |
| `GENERATION_SCHEDULED_OR_RUNNING` | unknown/conflict | `KEEP_HOLD_NO_CANCEL` |
| `GENERATION_COMPLETED` | reachable 且 V 內 | `RETAIN_COMPLETED_MATERIALIZATION` |
| `GENERATION_COMPLETED` | V 外預測未命中 | 僅 `SOFT_UNLOAD_RECONSTRUCTIBLE` |
| `GENERATION_COMPLETED` | 已證明錯誤、獨占非正典後代 | `DELETE_EXCLUSIVE_NONCANONICAL_MATERIALIZATION` |
| `GENERATION_COMPLETED` | 已證明錯誤、共享後代 | `DETACH_BRANCH_REFERENCE_ONLY_AND_RETAIN` |
| `GENERATION_COMPLETED` | 已證明錯誤、canonical 後代 | `DETACH_NONCANONICAL_EDGE_IF_SAFE_AND_RETAIN_CANONICAL` |
| `GENERATION_COMPLETED` | unknown/conflict | `KEEP_HOLD` |

## 7. 錯誤分支整段清理

`BRANCH_PREDICTION_ERROR_PROOF` 必須綁定：

```text
branch_id
branch_root_node_id
prediction_epoch
route_epoch
route_graph_root
actual_route_receipt_hash
divergence_transition_id
route_exclusion_proof_hash
descendant_set_root
proof_valid_time_window
proof_hash
```

產生清理計畫時，以同一 graph snapshot 建立完整 descendant manifest。每個節點必須具有：

```text
node_id
logical_record_key
materialization_id
physical_allocation_id
canonical_flag
owner_branch_ids
reverse_reference_ids
content_hash
record_version
stage_transition_receipt_hash
planned_action
```

節點判定：

```text
exclusive_noncanonical =
  canonical_flag = false
  AND owner_branch_ids = {wrong_branch_id}
  AND no_reverse_reference_outside_wrong_branch

shared = owner_branch_ids contains another live branch
         OR reverse_reference exists outside wrong branch
```

- `exclusive_noncanonical`：完成 CAS、引用、lease、pin、retention 與 proof 閘門後，刪除節點、materialization、獨占快取及獨占暫存。
- `shared`：只刪除 wrong branch 的 edge/reference；不得刪除共享內容，也不得把共享 allocation bytes 計為釋放。
- `canonical`：內容永久 `RETAIN`；只可解除可證明非正典且不影響其他路線的 edge。
- 分支內某節點身分不明、反向索引不完整或 descendant root 改變：整個不確定子樹 `HOLD`。

共享節點因 detach 後變為零引用，也不得沿用原分支 proof 直接刪除；必須另走具新 snapshot 與新收據的 orphan/GC 審查。

## 8. 排程中取消與暫存清理

`CANCELLATION_REQUEST` 至少綁定 generation job、worker、stage epoch、job version、route proof、預期 stage 及請求時間。有效 `CANCELLATION_RECEIPT` 的 outcome 只能是：

- `CANCELLED_BEFORE_START`
- `CANCELLED_DURING_RUN_WORKER_FENCED`
- `ALREADY_COMPLETED`
- `REJECTED_STALE_STAGE_OR_VERSION`
- `FAILED_HOLD`

只有前兩個 outcome 且 worker/GPU fence 已確認，才可建立 `TEMP_CLEANUP_DECISION`。`ALREADY_COMPLETED` 必須轉入完成階段規則；其他結果保持 HOLD。

取消收據不是釋放收據。暫存清理完成後另產生 `CLEANUP_COMMIT_RECEIPT`，其中 `actual_released_bytes` 由 allocator/storage 回報；在此之前 `released_bytes=0`。

## 9. 身分、重複與實際釋放量

```text
logical_record_key = namespace + record_id + record_version
materialization_id = 每一實體生成物的唯一 ID
physical_allocation_id = RAM/VRAM/磁碟實際 allocation ID
```

- 相同 logical key 與相同 content hash 可合併為同一邏輯記錄。
- 相同 logical key/version 但 content hash 不同：`IDENTITY_CONFLICT_HOLD`。
- 清理清單中的 materialization ID 必須唯一。
- 釋放量按唯一 physical allocation 計算；共享 allocation 只 detach，不得重複加總。
- `planned_release_bytes` 是估計；只有 commit receipt 的 `actual_released_bytes` 可進入已釋放計量。
- V2 純函式參考提交器只接受單一 materialization 獨占的 physical allocation；多 materialization 共用 allocation 即使全數可清，也必須等待另行審查的原子 group-commit adapter，不得拆成多個單筆 reclaim token。

## 10. Commit 與 false-miss 收據

所有 cancel、detach、soft unload、temp cleanup 或 delete 都先建立 immutable decision token，再於提交點重查：stage/route/prediction epoch、record/job version、proof roots、lease、引用、pin、canonical、retention、descendant root 與 allocation identity。

`COMMIT_RECEIPT` 必須包含 action、decision hash、CAS 結果、pre/post state hash、stage transition receipt hash、route proof hash、實際釋放量、commit sequence、idempotency key、前一 audit hash 與本收據 hash。同一 idempotency key 重跑只能取得原結果。

重放既有收據前仍須重算收據完整性 hash，並核對 decision/token、內容、epoch、提交時間、action、failure state 與 release upper bound；不能只比 idempotency key。V2 純函式只會產生 `SIMULATED_COMMIT`／`SIMULATED_FALSE_MISS`，這些結果不得計入真實 UX、allocator 或 runtime 成效；任何 `COMMITTED` live receipt 仍需另行審查的 authority/ledger adapter。

只有具有 `SOFT_UNLOAD_RECONSTRUCTIBLE + COMMITTED` 收據、後來在相同 prediction/route epoch 實際命中並完成 hash 驗證，才可產生 `FALSE_MISS_RECEIPT`。`KEEP_HOLD`、取消未完成、CAS 失敗或未提交不得記為 false miss。

若同一 route epoch/root 下，已由 exclusion proof 清理的分支後來實際命中，這是 `ROUTE_PROOF_SAFETY_VIOLATION`，必須停止該 verifier/epoch；若 route epoch 已改變，則記為 `ROUTE_CHANGE_REGENERATION`，不冒充原 proof 正確。

## 11. Event/Need/Watermark 安全條件

```text
past_cut = Wsafe - past_grace

PAST_ELIGIBLE implies:
  need_time < T_e - current_guard
  AND need_time <= past_cut
  AND event_time <= past_cut
  AND ingest_seq <= classification_snapshot_ingest_seq
  AND late_event_reconciled = true
```

`Wsafe` 必須是指定 membership epoch 中全部 required node watermark 的最小值。缺少節點、回報過期、partition、time domain 不同或 membership root 不符時，水位不得前進。不得再以 need time 單獨推導過去可清理。

## 12. 固定形式不變量

```text
I01 time/stage classification precedes every V/route action.
I02 future alone never authorizes delete.
I03 reachable AND inside_V implies retain/protect in all three stages.
I04 future unknown or proof conflict implies HOLD.
I05 predicted miss without exclusion proof permits at most cancel-not-generated,
    cancel-running-with-receipt, or soft-unload-completed.
I06 scheduled/running cleanup requires a successful cancellation receipt and worker fence.
I07 cancellation receipt alone contributes zero released bytes.
I08 completed wrong-branch delete requires valid branch error/exclusion proof.
I09 only exclusive noncanonical descendants may be physically deleted.
I10 shared descendants are detach-only; canonical content is always retained.
I11 every descendant action binds one immutable graph/descendant root.
I12 stage sequence and stage effective time never move backward.
I13 past eligibility requires both event_time and need_time behind safe watermark/grace.
I14 required-node membership completeness is mandatory for watermark advance.
I15 one idempotency key commits at most one physical effect.
I16 bytes are counted once per physical allocation and only from commit receipts.
I17 false-miss receipt requires a prior committed soft unload.
I18 route/root/epoch change invalidates prior exclusion proof.
I19 any identity, ownership, reverse-reference or stage ambiguity fails closed.
I20 no candidate document self-grants runtime or Total Field authority.
```

## 13. 最低靜態與故障測試

1. 三階段各自對 reachable/V 內、V 外 miss、excluded、unknown 的完整笛卡兒測試。
2. scheduled job 取消時同時完成，receipt 回 `ALREADY_COMPLETED`，不得清暫存並須改走 completed 規則。
3. cancellation request 成功前不得計算釋放量；cleanup commit 後只計 allocator 實際值。
4. 錯誤分支包含獨占、共享、canonical 三種後代，驗證 delete/detach/retain 不混用。
5. 重複 record ID、materialization ID 與共享 allocation 不得 double count/double free。
6. event time 尚未過 Wsafe、need time 已過去時仍必須 HOLD。
7. 缺失 required node、partition、clock rollback 與 late event 必須停止水位。
8. reachable/excluded proof 衝突、proof 過期、graph root 改變必須 HOLD。
9. KEEP_HOLD 或未提交 soft unload 不得產生 false-miss receipt。
10. crash 發生於 cancel、fence、temp cleanup、detach、delete 每一階段時，重啟須依 receipt 冪等恢復。

## 14. 整合與權限邊界

本文件只定義可驗證契約。下列全部為 `ADAPTER_REQUIRED / HOLD`：正式 route graph/verifier、ADI delta_F、生成排程器、worker/GPU cancellation fence、RAM/VRAM allocator、反向引用與 ownership index、canonical lineage、GTP 重建、跨節點 watermark、commit/audit ledger、預算調整器及人類使用體驗量測。

在各 adapter、shadow、可回復 canary、故障注入及總場決策完成前：不得接入 live generation、不得取消真實工作、不得清除 RAM/VRAM／檔案、不得改模型或路由、不得宣稱已證明效能或使用體驗提升。
