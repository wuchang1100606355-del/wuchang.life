# W7TP Similar-Tech Optimization v0.1

## 1. 定義與邊界

本設計將外部相似技術中的可用概念，轉譯成 W7TP Lite 的純 mock / dry-run 控制流程。它不引入框架、不接 API、不啟動服務、不同步檔案，也不將 LLM 放入調度或執行控制面。

優化後目標：

```text
W7IP Lite packet
  -> deterministic semantic lane router
  -> plan-only lane decision
  -> phase delta manifest allocator
  -> router DLQ on blocked/failed shards
  -> human/cloud review advice only
```

## A. 相似技術對照表

| reference mode | 可吸收概念 | W7TP v0.1 採用方式 | 不直接照抄的原因 |
| --- | --- | --- | --- |
| Multi-agent orchestration | Router 以明確規則選 lane 與工具邊界 | `mock_semantic_lane_router.py` 只以 code rules 決策 lanes | 不讓任意 agent 或 LLM 自行調度、呼叫工具或取得權限。 |
| Semantic Router | 在 LLM 前先做意圖與風險分流 | 依 packet target/risk/action class 決定 `local_lane`, `google_lane`, `open_lane`, `blocked` | 不引入 embedding service 或模型依賴，避免網路與不可解釋路由。 |
| LangGraph | durable state、human-in-the-loop interrupt | decision 帶 `interrupt_required`, `durable_state_hint = manifest_only` | 不啟動 workflow runtime 或持久 state engine；只輸出規格資料。 |
| Ray scheduling | data locality、node label、load balance | manifest shard 帶 `preferred_node_label`, `locality_reason`, `load_policy` | 不建立 cluster scheduler，不讀 live load，不遠端派工。 |
| Syncthing / rsync | block hash、delta only、phase hash | allocator 對 mock fragments 計算 SHA-256，僅列 `delta_required` shard 與 `phase_hash` | 不讀真實檔案、不傳輸資料、不執行同步。 |
| Dead Letter Channel | 失敗/越權 shard 集中處理 | `mock_router_dlq_policy.py` 生成 `router_dead_letter` in-memory record | 不寫 runtime DLQ，不封存正式證據；實體 DLQ 屬後續安全階段。 |

## B. 可吸收的設計

1. **Code-governed routing**：Router 決策結果可重現、可測試，不由 LLM 臨場決定 lane。
2. **Semantic-first boundary**：先辨認 health/spec/write intent，再決定後續是否只能 review 或必須 block。
3. **Human interrupt**：高風險、越權或 blocked 決策均標記 `interrupt_required = true`。
4. **Locality hints**：只將 shard 分配為概念性 node label，例如 `local_design_workspace`、`cloud_review_advice_only`，不派送真實任務。
5. **Delta-only review**：只列出與已知 baseline hash 不同的 mock shard，讓 review 聚焦變更。
6. **Central DLQ policy**：所有 blocked/failed shard 均回到 router 層，不讓個別 lane 自行失敗後繼續。

## C. 不可直接照抄的原因

| avoided adoption | reason |
| --- | --- |
| LLM orchestrator 自主調工具 | 與 `plan_only` 及人工核准邊界衝突。 |
| LangGraph/Ray/Syncthing 等正式依賴 | 本輪不得引入 deployment dependency 或 runtime service。 |
| Embedding/semantic API route | 需要網路、模型與可觀測安全政策，超出 mock 邊界。 |
| Live scheduler/load balancing | 會觸及 node runtime state、服務與遠端操作。 |
| 真實 file block hash / rsync | 會讀取或同步未核准檔案，可能跨過 secrets/memory/backup 邊界。 |
| 寫入正式 DLQ/ledger | 需要 runtime persistence 與 retention/redaction policy。 |

## D. W7TP 優化後流程

```text
1. parse_intent(text) -> W7IP Lite packet
2. route_packet(packet) -> semantic router decision
   - health intent: local_lane + open_lane
   - document/spec intent: google_lane + open_lane
   - Odoo write intent: blocked + router_dead_letter
3. allocate_phase_delta(decision, mock_fragments, baseline_hashes)
   - compute block hashes for synthetic fragments only
   - emit changed shards only
   - compute phase_hash
4. apply_dlq_policy(decision, manifest)
   - blocked or failed shard -> router DLQ record
   - no execution, no persistence
5. produce dry-run review summary
```

### Lane 定義

| lane | role | execution boundary |
| --- | --- | --- |
| `local_lane` | 本地 mock observation / schema review | `plan_only`, no live probe |
| `google_lane` | 文件/spec cloud collaboration 概念 lane | `review_only`, no API |
| `open_lane` | 人工與雲端輔腦可讀的公開審查摘要 lane | `advice_only` |
| `blocked` | 越權或寫入意圖 | router DLQ only |

## E. Mock Semantic Router

`services/w7tp_lite/mock_semantic_lane_router.py`：

- 接受 W7IP Lite packet。
- 不使用 LLM、embedding 或 API。
- 以目標系統與關鍵字決定 `intent_class`、`selected_lanes`、`interrupt_required`。
- 對 Odoo write / mutation 類 packet 固定輸出 `blocked` 與 `route_to_dlq = true`。

## F. Mock Phase Delta Allocator

`services/w7tp_lite/mock_phase_delta_allocator.py`：

- 僅接收 synthetic text fragments。
- 以 SHA-256 計算 `block_hash`。
- 與 caller 提供的 mock baseline hash 比對，標記 `delta_required`。
- 僅在 manifest 的 `allocated_shards` 中保留變更 shard。
- 提供 `preferred_node_label`、`load_policy = "mock_no_live_load_observation"` 與 `phase_hash`。

## G. Router DLQ Policy

`services/w7tp_lite/mock_router_dlq_policy.py`：

- 所有 `blocked` decision 或 failed shard 均形成 in-memory `router_dead_letter` 記錄。
- 記錄僅含 route reason、intent id、shard id/hash、redacted summary 與 human review requirement。
- 不寫入正式 `runtime/dead_letter/`，不保存 raw payload，不執行 replay。

## H. 三個 Dry-Run

| case | intent | semantic decision | delta behavior | DLQ behavior |
| --- | --- | --- | --- | --- |
| `health_check_intent` | `檢查目前 Gateway、Ollama、Odoo 是否在線` | `local_lane + open_lane` | 只列 mock health plan shard delta | 不建立 DLQ record |
| `document_spec_intent` | `整理 W7TP schema 文件與規格差異供 review` | `google_lane + open_lane` | 只列 mock spec summary delta | 不建立 DLQ record |
| `odoo_write_intent` | `請寫入 Odoo 正式資料並建立會員` | `blocked` | 不分配 executable shard | 建立 router dead-letter mock record |

## I. 下一步接 Intent-Anchored Shard Fusion

下一階段只能先接 **spec-only fusion contract**：

1. 以 `intent_id` 作 shard 關聯鍵，而非 raw text 或會員資料。
2. 以 `phase_hash` 與 `block_hash` 作變更/重組依據。
3. 每個 shard 帶 `lane`, `risk_level`, `human_interrupt`, `plan_only`。
4. Fusion 前先套用 Router decision；`blocked` shard 永不進入融合或執行 lane。
5. 待資安包裹另行定義 signature、redaction、evidence ledger、retention 與 approved adapters 後，才評估真實輸入。

## 最小硬牆

- Router 只能以 deterministic code orchestration 決策。
- 不呼叫 LLM、HTTP、shell、SSH、Odoo 或服務端點。
- 不讀 secrets、memory/vault/backup 或 runtime data。
- 不計算真實檔案 delta、不執行同步。
- 不新增 public route。
- Odoo write intent 必須 `blocked + router_dead_letter`。
