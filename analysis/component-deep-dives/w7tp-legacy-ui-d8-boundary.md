# 第二階段元件追查 A｜舊式控制面板與 V2.3 D8 權威邊界

**節點／觀測：** taiji01，2026-10-09（台北）；Git `3c2e5884bc149ffbb02d81fdf288506918fae79e`；本次僅讀取原始碼與 GET 狀態，沒有呼叫 POST 或執行測試。
**狀態：** `SOURCE_TRACE_CONFIRMED / LEGACY_SEMANTIC_BOUNDARY_REVIEW_REQUIRED`，不是全域正典不一致裁決。

## 正典定義與當前對象

- Founder V2.3：D1 意圖、D2 狀態、D3 座標、D4 證據、D5 執行／政策、D6 生成式狀態傳輸、D7 風險／隔離、D8 封套／權威，八合一單一動態狀態場。
- 已核對正式來源 `runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json`、`manifests/total_field/w7tp_8d_adi_v2_3_canonical/CONTRACT.json`；不允許因舊介面鍵名自動取得正典權威。
- 本次查核的對象是「舊 Web 控制面板的一次編譯、檢查與稽核」；8D 是此對象的耦合觀測，不是八個執行步驟。

## 實際路由及消費者

1. `web/w7tp_8d_control_panel.html:435–483`：`compileIntent()` 呼叫 POST `/api/w7tp/intent/compile`，儲存 `lastPacket`；後續 `lintIntent()`、`sealState()`、`commitEvidence()` 與 `fullFlow()` 沿同一物件傳遞。
2. `services/w7tp_ui_adapter.py:69–98`：`compile_packet()` 回傳 `D1_Taiji_Root`、`D6_Governance_Linter`、`D8_State_FSM` 等舊式名稱；`source=local_adapter`；不是 V2.3 D1/D6/D8 的同名語義。
3. `services/w7tp_ui_adapter.py:99–132`：Lint（靜態規則檢查）、封存雜湊、evidence commit（證據紀錄）各自呼叫其 helper；此鏈未呼叫 `services/w7tp_gst_v23_runtime.py::deliver_packet()`。
4. `services/w7tp_d6_linter.py:48–86`：文字規則檢查後預設 `allowed=true` 並回覆 `TRANSACTION_COMMITTED`，其名稱容易被錯讀為業務交易已正式完成。
5. `services/w7tp_state_hash.py:19–72`：有 `W7TP_HMAC_KEY` 才使用 HMAC（具密鑰訊息鑑別碼），否則退為 `UNKEYED_DEV_HASH`（無密鑰開發雜湊）。原始碼提供模式欄位；本次未查詢正式金鑰環境，不能宣稱當前使用無密鑰模式。
6. `services/w7tp_evidence_ledger.py:30–78`：無論 `decision.allowed` 是否為 true，均寫入 `runtime/ledger/w7tp_ui_events.jsonl`；拒絕狀態另寫 dead-letter（異常信箱）。此為本地事件帳，不含總場 D8 正式授權查核。
7. `web/w7tp_8d_control_panel.html:347–408`：若前端 hostname 恰為 `wuchang.life` 或 `www.wuchang.life`，會回傳本地 static demo（靜態示範）而不發出寫入 POST；但由其他 hostname 進入時，前端程式會直接呼叫後端。此程式分支不等於已驗證所有網域代理。

## 與正式 V2.3 GST 的分隔

- `services/w7tp_ui_adapter.py:14–34` 的 `/api/w7tp/gst/v23/status` 與 `/deliver` 是另一條獨立路由，交付會進入 `services/w7tp_gst_v23_runtime.py` 的來源驗證、D8 約束及隔離消費端。
- 本次 `GET http://127.0.0.1:8081/api/w7tp/gst/v23/status` HTTP 200，回傳 `ACTIVE_GST_V23_USER_DELIVERY`、`total_field_decision=PASS` 與 `CLOSED_FOR_EXACT_GST_V23_RUNTIME_CONSUMER_BINDING`。這是**特定 consumer 綁定**的當前回報，不證明任意 UI 編譯封包可升格或本次完成交付效果。
- 查找源碼中 `D1_Taiji_Root`／`D6_Governance_Linter`／`D8_State_FSM` 的命中位置為 `services/w7tp_ui_adapter.py`；Web 端使用 `/intent/compile`；此次界定的是這條 legacy UI 子鏈，非總場所有消費者。

## D1–D8 同對象差異與反證

- D1：目的是讓控制面板編譯並檢查意圖，非替 Founder 改定義。
- D2／D3：程式存在且路由已登錄於 8081；來源作用域是 `services/w7tp_ui_adapter.py` 和 Web 控制面板，不能延伸為產品正式交易。
- D4：有對應原始碼、路由登錄與單次 GET；沒有新 POST 效果驗收。
- D5：`commitEvidence()` 確實觸發本地 append-only 事件寫入；本次未呼叫。
- D6：舊稱 `D6_Governance_Linter` 是命名投影而非 V2.3 GST；不能用鍵名等同生成式狀態傳輸。
- D7：模式退為無密鑰摘要屬可能的封存可信度分級缺口；金鑰設定未知，不能宣稱已發生弱保護。
- D8：本地 `state_seal`、`commit_evidence` 並無獨立正式 D8 決策，且未見直接進入正典寫入路由；因此 `TRANSACTION_COMMITTED` 應解讀為舊 UI 規則回傳，而不是權威裁決。

## 支持／反證／未知／判定

- **支持：** 舊鍵名、Web 真實呼叫、事件落檔程式皆存在；無 D8 呼叫可直接見於這段程式。
- **反證：** 正式 GST `/status` 在獨立路由已回報特定 consumer 的 D8 綁定有效，不能由舊 UI 語義推導全部 V2.3 失敗。
- **未知：** 該 UI 其他反向代理的實際暴露範圍、外部系統是否會把 UI `event_hash` 當成 D8、真實封存是否採 HMAC 模式。
- **判定：** `LOCAL_LEGACY_UI_SEMANTIC_AMBIGUITY`；應以既有 UI adapter 作受限相容隔離，保留查核，避免另造核心。

## 最小候選措施（未實作）

- 明確標註舊 UI 封包及 ledger 為 `LEGACY_UI_EVENT_CANDIDATE_ONLY`，不將 `TRANSACTION_COMMITTED` 類字串解讀為已交易。
- 額外定義 adapter 到 V2.3 的消費端接受／拒絕契約；不得僅改鍵名便當作語義等價。
- 針對 eventbook 增加「非正式 D8」防誤升格測試及審核關聯性測試；正式修復需另行取證及授權。
