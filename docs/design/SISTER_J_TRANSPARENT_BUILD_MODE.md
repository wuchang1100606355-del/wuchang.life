# Sister J Transparent Build Mode

## 1. 定義

Sister J Transparent Build Mode（小J透明構造模式）是一個設計期的觀測封包流程。它的目的不是控制 runtime，而是讓本地小J將已核准可揭露的架構、狀態、錯誤、候選程式與決策缺口，整理成可供雲端輔腦與人工快速閱讀的 `Transparent Observation Pack`。

本模式遵循：

```text
local approved observation input
  -> mock collector
  -> mock redactor
  -> mock cloud review packet
  -> human-readable next action proposal
```

本 MVP 不做即時掃描、不啟動服務、不讀取敏感檔、不操作 Odoo、不執行同步，也不把雲端建議直接轉成執行。

## 2. 透明的意義

透明不是無限制公開，而是將可安全揭露且有判斷價值的內容明確分層：

| principle | transparent content |
| --- | --- |
| 架構透明 | system role、canonical boundary、元件責任與已知 candidate paths。 |
| 狀態透明 | 設計/原型/稽核階段，以及已提供的 mock status summary。 |
| 錯誤透明 | 已知缺口、阻擋原因、尚未驗證事項。 |
| 程式碼透明 | 候選檔路徑、角色與 review 狀態，不含秘密或 runtime records。 |
| 設計決策透明 | 為何採 plan-only、為何延後正式安全封裝、下一個最小決策。 |

## 3. 必須留在本地的資訊

以下資料只可以出現在 `blocked_sensitive_paths` 的規則說明中，不得由觀測包輸出其內容：

| blocked material | rule |
| --- | --- |
| `.env`, `.env.*` | 不讀、不輸出、不傳遞。 |
| `logs/` | 不讀 runtime trace 或可能含識別資訊的輸出。 |
| `memory/`, `memory_zone/`, `wuchang_memory_vault/`, `_ollama_memory/` | 不讀 memory/vault 原文。 |
| `backup_*` | 不讀、不展開、不納入摘要。 |
| private keys, token files, credential files | 不讀內容，不輸出值或片段。 |
| OAuth secret、password、會員個資 | 任何字串若疑似出現，redactor 必須遮蔽。 |

## 4. Observation Pack 最小結構

| field | role |
| --- | --- |
| `system_role` | 被觀測系統的責任定位。 |
| `current_stage` | `design`, `prototype`, `audit` 之一。 |
| `directory_map_summary` | 僅描述核准可揭露的路徑角色與狀態。 |
| `services_status_summary` | `mock_not_probed`, `planned`, `unknown` 等摘要；不得假裝 live observation。 |
| `ports_summary` | 候選連接埠用途，不執行 listen/curl 驗證。 |
| `docker_summary` | 是否在本階段排除容器查核。 |
| `gateway_summary` | gateway 角色、已知缺口與 plan-only 判斷。 |
| `odoo_boundary_summary` | Odoo 僅為邊界說明，不讀或寫正式資料。 |
| `ollama_models_summary` | 模型狀態只可標成未探測或 mock。 |
| `topology_summary` | canonical root、edge / governance plane 與 packet contract 摘要。 |
| `known_errors` | 可供雲端輔腦排序的已知問題。 |
| `candidate_files` | 只列可 review 的檔案與角色。 |
| `blocked_sensitive_paths` | 固定安全硬牆清單。 |
| `open_questions` | 需要人工決定的缺口。 |
| `next_recommended_actions` | 可審查、不可自動執行的下一步。 |

## 5. Mock Pipeline

### Collector

`mock_observation_collector.py` 僅接受內建的三種合成場景，輸出標記為
`sister_j.transparent_observation_draft.v0.1` 的中間草稿；只有經過 redactor
並由 cloud packet assembler 加入 review 邊界後，才會標記為
`sister_j.transparent_observation_pack.v0.1`：

| scenario | intent |
| --- | --- |
| `design_baseline` | 表達 W7TP Lite 仍在設計階段，所有 runtime 狀態都未探測。 |
| `prototype_gap` | 表達 mock prototype 已建立，但 gateway/webhook contract 尚缺。 |
| `audit_blocked` | 表達遇到敏感參照或 live-action 需求時，必須阻擋並回到人工審查。 |

Collector 不讀目錄、不查 port、不查 Docker、不查 Odoo 或 Ollama，只產生合成資料。

### Redactor

`mock_redactor.py` 只處理記憶體中的 mock dictionary，遮蔽：

- 疑似 token / password / private key / OAuth secret / credential 值。
- Bearer 形式的字串。
- Email 與電話形式的合成個資。
- `raw_profile`、`member_profile`、`vault_content` 等禁止鍵值。

`blocked_sensitive_paths` 是政策名稱清單，必須保留名稱，不能被 redactor 刪掉。

### Cloud Review Packet

`mock_cloud_review_packet.py` 將 redacted observation pack 附上：

- `review_priority`
- `review_focus`
- `decision_requests`
- `cloud_action_boundary = "advice_only_no_execution"`
- `redaction_summary`

雲端輔腦只能建議排序、缺口與下一步，不得取得秘密，也不得直接操作系統。

## 6. 三個 Dry-Run 範例

| scenario | current_stage | exposed decision value | expected cloud review |
| --- | --- | --- | --- |
| `design_baseline` | `design` | canonical role、W7TP Lite 設計產物、所有 live status 未探測 | 建議先完成 schema/review gate，不要求連線。 |
| `prototype_gap` | `prototype` | mock parser/plan generator 已存在；webhook/gateway 安全契約未完成 | 建議聚焦 plan-only contract 與 negative tests。 |
| `audit_blocked` | `audit` | 合成錯誤含疑似 secret/個資參照，須遮蔽與阻擋 | 僅提供 redacted issue、要求人工判斷，禁止移動資料。 |

## 7. 雲端輔腦快速判斷格式

雲端接收 packet 時應能在一次閱讀中回答：

1. 這是什麼系統，現在處於哪個階段？
2. 哪些狀態是已知，哪些只是未探測或 mock？
3. 哪些候選檔案可 review，哪些路徑不可觸碰？
4. 目前最大的阻擋缺口是什麼？
5. 下一步是否只是設計/審查，還是需要人工另外授權？

因此每一包都必須明列 `known_errors`、`blocked_sensitive_paths`、`open_questions` 與 `next_recommended_actions`，而非只傳一段自然語言描述。

## 8. 不可移除的硬牆

1. Collector 在此階段只能使用靜態 mock input，不能探測 filesystem、port、Docker 或 service。
2. Redactor 必須在 cloud packet 產生前執行。
3. Pack 必須帶有完整 `blocked_sensitive_paths`。
4. Status 必須標註證據來源，例如 `mock_not_probed`；不得宣稱 live healthy。
5. Cloud packet 必須固定為 advice-only，不得產生可自動執行指令。
6. 不啟動服務、不操作 Odoo、不讀 secrets/logs/memory/vault/backup，不做 Runtime -> Hub sync。

## 9. 最短落地路徑

1. Review 本文件與 JSON Schema 欄位是否足以支持人工判斷。
2. 離線執行三組 mock scenario，確認 redaction 與 advice-only output。
3. 若內容格式可接受，再設計「經人工批准的非敏感輸入清單」，仍不接 live probes。
4. 最後才決定是否建立正式資安包裹、可稽核 ledger 與受控 observation adapters。
