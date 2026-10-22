# 第二階段元件追查 B｜Dynamic Context、ADI 原胞、模型接收與成本

**觀測：** taiji01，2026-10-09（台北）；Git HEAD `3c2e5884bc149ffbb02d81fdf288506918fae79e`，其中 `core/msi_local_llm_route.py`、`core/resource_arbitration.py`、`services/gateway/natural_language_control.py` 為未提交工作樹版本。分類 `SOURCE_IMPLEMENTATION_REVIEW`，未重跑模型、未觸發 insert 或任務執行。

## 同一任務動態狀態場的現存耦合

- 意圖／政策：`services/gateway/natural_language_control.py:16–40,159–195` 對自然語言意圖做資源路由與靜態狀態原胞封套；`execute` 非 `dry_run` 將創建 run 資料、FIFO（先入先出管線）及暫態 systemd runner（服務執行器），本次**未呼叫**。
- 狀態／座標／依賴：`tools/w7tp_task_state_minimum_packet.py:164–245` 從 `state/WORK_LEDGER.json` 與 `state/ACTION_LEDGER.json` 選取特定 task/action refs，限制最近已確認行動與 ADI 參考。
- 原生 ADI：`tools/w7tp_task_state_local_rule.py:81–116` 用 POST `/v1/adi/packet` 查回命中的 ADI record；`tools/w7tp_task_state_minimum_packet.py:604–625` 的最小原胞發行先執行 `insert_task_state_adi_record()`，最終經 POST `/v1/adi/insert` 建立新的任務狀態座標。
- 原胞／本地規則：`tools/w7tp_task_state_minimum_packet.py:467–598` 讀取本地 rule registry（規則登錄表），建立任務原胞；`tools/w7tp_task_state_local_rule.py:201–289` 以本地任務狀態／行動／checkpoint／ADI 索引材料建立確定性重構規則。
- 單次拉取：`tools/total_field_dynamic_context_pull.py:229–452` 的 `TotalFieldDynamicContextPullBroker` 會驗證 task/provider/model、TTL（有效期限）、禁止重播與狀態包純度；先消耗座標，再 `volatile_reconstruction`（暫態重構），使用後刪除 workset（作業材料）。
- 模型投影：`tools/w7tp_task_state_minimum_packet.py:695–839` 可建立含 task 狀態、完成準則、下一動作、同任務 checkpoint、actions、ADI record refs 的 `model_visible_context.state_projection`。

## 重點差異：重構成功不保證模型獲得投影本體

- `tools/w7tp_nl_goal_runner.py:852–918` 的 `pull_task_dynamic_context_for_model()` 拿到 `result["model_visible_context"]`，卻只擷取其中 `context_ref`；回傳給模型路由的是 `state_cell_transmission`，未包括完整 `state_projection`（例如 `task.title/state/next_action` 及 action 確認結果）。
- `tools/w7tp_nl_goal_runner.py:1053–1074` 只把 `state_cell_transmission` JSON 加入本地模型 prompt（提示輸入）；`665–714` 的無工具 `run_local_transform()` 同樣只串入該 transmission，不另取投影。
- 對會修改程式的 `run_local_agent()`（同檔約 `717–743`），模型另可讀隔離 shadow 原始碼，但 `build_prompt()`（`613–641`）明示 shadow 排除 runtime/evidence 歷史，故不可假設它能從影子樹取得先前未隨封包交付的當前 task 狀態。
- `tests/test_w7tp_nl_goal_total_field_gate.py:~145–197` 的模擬測試明示檢查 `result` 中**沒有** `model_visible_context`；這證明既有測試重視不洩露完整上下文，但並未驗證接收模型能解出足夠、等價的任務語義。
- **局部判定：** `MODEL_VISIBLE_STATE_PROJECTION_NOT_DELIVERED_CANDIDATE`。不能說原胞引擎沒有重構能力，也不能說模型已獲得該完整結果。需以「同任務問句、本地模型實際收到的位元組、回答可驗證性」另行驗收。

## 副作用及必要前置成本

- `issue_task_state_minimum_packet()` 會先向 Native ADI 插入 task-state record，**不是純唯讀 Pull**；實際執行一次任務可能包含新資料寫入，即便後續上下文拉取或模型候選失敗。
- `select_task_state_support_refs()` 會存取兩個 ledger、向 ADI 查詢引用資格；產包程序重取資料／規則並在 `/dev/shm`（共享記憶體）形成驗收 manifest；broker 再做暫態重構、驗證、清理。
- 可見原胞 `target_bytes_transmitted=0` 與 `rule_body_transmitted=False` 只表示未傳目標原始位元組與規則本體，不表示規則、索引、查詢、封包欄位、回執或上游準備零成本。
- 若同一意圖需要本地模型與 Gemini 候選，`tools/w7tp_nl_goal_runner.py:770–837,1049–1145` 可形成不同 task-state packet 發行／Pull 路徑；本次未計算實際呼叫次數或總成本。
- `GET http://127.0.0.1:9110/metrics` HTTP 200 回報 `record_count=2511`（觀測當次）；屬整體服務總數，不是這一任務的讀寫次數或成功率。

## 本地模型路由：當前宣告與使用者的區網邊界

- `core/msi_local_llm_route.py:25–165` 優先候選為 MSI LAN `192.168.50.82:11434`，其後仍登錄 Windows Tailscale（虛擬私人網路覆疊路由）及 SSH reverse tunnel（反向安全通道）備援。
- `tests/test_msi_local_llm_route.py:16–111` 已有單元測試描述前述路由次序；**本次未執行**。此程式檔及測試在查核時有未提交修改，需以其當前 worktree 版本觀測。
- Founder 明確指定不主動使用 VPN／區網優先；故仍具備自動選擇 Tailscale 的程式邏輯屬 `NO_VPN_POLICY_ALIGNMENT_REVIEW` 候選，而不是本次實際啟用 VPN 的證據。

## 反證與非全域限制

- `tests/test_total_field_dynamic_context_pull.py` 的來源包括有效 TTL、單次使用、重播阻擋、非差分純度與暫態清理；`tests/test_w7tp_task_state_minimum_packet.py` 有同任務 checkpoint 投影及排除他任務資訊的測試。這是**測試設計**，非本次運行 PASS。
- `services/w7tp_gst_v23_runtime.py` 的正式 GST `deliver_packet()` 是另一條經 D8 驗證的交付路徑；`GET /api/w7tp/gst/v23/status` 回報該**精確消費端綁定**有效，不證明本地模型的 task-state body 已接收或特定任務答案有效。
- 不得因模型收到 refs 而宣稱其完成重構；也不得因 body 未隨 prompt 傳送便否定本地 `volatile_reconstruction()` 的實際存在。

## 下一步驗收條件（建議，不執行）

1. 在既有 runner 的隔離測試中新增「同任務重構投影是否可供目標本地模型真正使用」驗證，不必傳送所有私人狀態；可使用有明確授權、消隱且不可提升權威的任務投影。
2. 分別記錄 `packet_total_bytes`、`registry_prior_cost`、`adi_query_bytes/count`、`adi_insert_count`、`reconstruction_cpu_ms`、`verification_ms`、`model_visible_payload_bytes`、`model_answer_acceptance`，比較相同任務／同成本口徑。
3. 保留 T-007 V2.3 正典和既有能力，不建立第二個狀態場、第二個小J或平行索引權威。
4. 僅在相應授權後考慮對「不得使用 VPN」的實際路由 selector 提供政策閘門；本次不改設定、不觸發備援路由探測。

**本次：** `TEST_EXECUTION=NOT_RUN`；`ADI_INSERT=NOT_RUN`；`MODEL_CALL=NOT_RUN`；`TOTAL_FIELD_DECISION=NOT_RUN`。
