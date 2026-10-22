# Taiji_Hub 架構與呼叫關係分析（第一階段）

**證據座標：** taiji01；2026-10-09 14:02–14:07（台北）；Git HEAD `3c2e5884bc149ffbb02d81fdf288506918fae79e`；程式來源及有限 GET 健康探測。此文件不是 D8 正式批准，也未證明所有執行中的程序與工作樹位元組一致。

## 1. 定義與運行角色區分

- Founder 正典：W7TP／8D ADI V2.3 八合一單一動態狀態場；D1 意圖、D2 狀態、D3 座標、D4 證據、D5 執行／政策、D6 生成式狀態傳輸、D7 風險／隔離、D8 封套／權威。此處僅描述同一事物的耦合狀態，不視為八階段程序。
- 正典註冊：`runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json` → `manifests/total_field/w7tp_8d_adi_v2_3_canonical/CONTRACT.json`；前者 `ACTIVE_CANONICAL`，後者禁止 self-promotion（自行升格）。
- Current Field：`runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_CANONICAL.json` 宣告全節點 V2.3，`ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json` 為含路由器版本。
- 總場權威檔：`runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json`，載明允許效果集合；登錄存在、雜湊一致不等於所有業務動作已獲授權。
- Odoo 是營運業務器官，不能因模組宣告或一般 ERP 慣例反向取得 W7TP 總場正典制定權；小J產品隔離候選也不等於現行上線。

## 2. 實際原始碼呼叫圖（不是八維的順序流程）

```text
外部或區網請求
  -> services/gateway/main.py : FastAPI Gateway（原始碼入口，8081）
     |-> /api/taiji/{plan,execute,voice}
     |     -> services/gateway/natural_language_control.py
     |        -> core/msi_local_llm_route.py （選擇 MSI 本地模型路由）
     |        -> core/resource_arbitration.py （資源仲裁與靜態狀態原胞）
     |        -> tools/w7tp_nl_goal_runner.py （只在執行請求啟動後）
     |           -> tools/w7tp_task_state_minimum_packet.py
     |           -> tools/total_field_dynamic_context_pull.py
     |           -> tools/w7tp_local_model_agent.py （本地模型候選生成）
     |-> /api/w7tp/gst/v23/{status,deliver}
     |     -> services/w7tp_ui_adapter.py
     |        -> services/w7tp_gst_v23_runtime.py
     |           -> runtime/total_field/gst_v23_runtime_consumer/ACTIVE_BINDING.json
     |           -> products/eight_dimensional_generative_memory/...consumer_candidate.py
     |-> /api/w7tp/intent/compile 等其他 UI 路由
     |-> topology / openai_compat / NVR / natural_language_control 路由

獨立接口：services/w7tp_native_adi/service.py : 9110
  -> services/w7tp_native_adi/core.py::SpacetimeADI
  -> /v1/adi/{insert,search,packet,reconstruct}

業務子系統：Taiji_Odoo/docker-compose.yml
  -> Odoo 18 宣告，LAN 192.168.50.249:8069
  -> PostgreSQL 15 宣告，Taiji_Odoo/addons 16 個頂層模組目錄
```

## 3. 可確定的呼叫邊與副作用界限

| 來源 → 目標 | 直接程式證據 | 可證明範圍／限制 |
|---|---|---|
| `main.py::execute` → `governed_execute` | `services/gateway/main.py:315–317` | POST 執行路由已註冊；非唯讀查詢 |
| `natural_language_control.execute` → run state、`systemd-run` | `services/gateway/natural_language_control.py:498–596` | `dry_run=False` 會建立 run 資料與暫態 runner；本次**未呼叫** |
| `natural_language_control.build_plan` → `build_static_state_cell_envelope` | 同檔約 159–191 行 | 已有來源呼叫；不能僅憑此宣稱模型收到完整 Dynamic Context |
| `w7tp_nl_goal_runner` → Dynamic Context Pull Broker | `tools/w7tp_nl_goal_runner.py:852–918,1054–1074` | 會先建立任務最小原胞、register/pull，再附加至模型提示；本次未新跑任務 |
| `w7tp_ui_adapter.gst_v23_deliver` → `deliver_packet` | `services/w7tp_ui_adapter.py:12–33` | V2.3 路由存在；POST 會寫交付目錄，故未觸發 |
| `deliver_packet` → 既有 consumer + D8 檢查 | `services/w7tp_gst_v23_runtime.py:236–418` | 契約檢查、隔離交付機制存在；未驗收本次封包效果等價 |
| native ADI service → `SpacetimeADI` | `services/w7tp_native_adi/service.py:15–156` | 明示索引、封包及重構 API；本次只 GET `/health` |
| 菜單選項模組 → AI Gateway／會員模組 | `Taiji_Odoo/addons/wuchang_cafe_menu_options/__manifest__.py` | Odoo 模組依賴宣告，不表示真實資料庫已成功升級 |

## 4. 來源宣告與執行狀態分開觀測

| 座標／時間 2026-10-09 約 14:05 | 即時結果 | 不可外推的結論 |
|---|---|---|
| `127.0.0.1:8081/health` | HTTP 200，回報 `taiji-gateway 1.1.0-redteam` | 不等於所有下游 runner 已健康 |
| `127.0.0.1:8082/healthz` | HTTP 200，`ADI_KNOWN_NOVEL_V3` | 不等於 D8 核准每個請求 |
| `127.0.0.1:9110/health` | HTTP 200，`W7TP_NATIVE_ADI_AGENT` | 不等於曾執行實際重構驗收 |
| `192.168.50.249:8069/web/login` | HTTP 200 | 不等於會員／點餐／收銀流程已驗收 |
| `127.0.0.1:8099` | 本次無法連線 | 僅此位址未知，不代表系統全域失效 |
| PID 1557 / 9110 | user.slice 的 `w7tp-native-adi.service` cgroup；system-level 同名單元 inactive | 不得把不同層 systemd unit 混為同一個服務 |
| `127.0.0.1:8081/openapi.json` | 28 條路徑；自然語言與 GST POST、狀態 GET 均登錄 | API 登錄不等於有權執行或效果驗收 |

## 5. 狹義候選疑點（未裁決）

1. **V2.3 語義相容性候選：** `services/w7tp_ui_adapter.py::compile_packet` 仍產出 `D1_Taiji_Root`、`D6_Governance_Linter`、`D8_State_FSM` 等舊式鍵名，與現行 V2.3 的 D1/D6/D8 語義名稱不同。該路由在執行閘道的 OpenAPI 中可見。缺少：其消費端映射、是否只是 legacy UI 投影，以及是否有證據誤當正式 V2.3 封包；**不得據此判定全場失效**。
2. **模型啟用證據不足：** Runner 程式有真正的 Dynamic Context 拉取函式，但此次沒有新觸發模型執行、模型答案驗證或 8D 效果等價測試；檔案存在不能替代運行證據。
3. **版本／工作樹界限：** 工作樹已有 28 個已追蹤修改，其中包含本地模型路由及 Odoo 模組；本次程式閱讀可能含未提交候選，不能當成 HEAD 或容器現行位元組。
4. **產品隔離：** `products/wuchang_xiaoj_community/README.md` 明示不連正式 Odoo API，也不部署；不可把產品候選宣稱已正式上線。
5. **完整傳輸成本尚未量測：** 尚未對同任務、同前置規則、封包、索引讀取、重構及驗證總成本與效果做比較；不得用封包大小宣稱全面優越。

## 6. 下一階段精準分析目標（非自動修改指令）

- P1：沿 `compile_packet` 實際消費者，界定 legacy 投影與 V2.3 正典傳輸的隔離／失配；只需有限路徑查核。
- P1：查核 Dynamic Context `register/pull` 的實際測試與最新獨立驗收，指定同任務、觀測範圍及驗收條件。
- P1：比對 Odoo 菜單、點餐、會員、票券模組的 controller→model→view 與 Compose→容器→資料庫的實際載入關係（不讀 secrets、不查會員明文）。
- P2：確認 9110 使用者層服務所有權與 Gateway 依賴，避免以 system 層單元狀態誤判。
- 先重用 `docs/total_field/W7TP_RUNTIME_QUERY_INDEX.md` 與 `tools/w7tp_runtime_query_indexer.py`；查詢索引不授予執行或正典權威。

**完成類型：** `PHASE1_ARCHITECTURE_READ_ONLY_DOCUMENTED`；非 `TOTAL_FIELD_PASS`、非正式修改、非部署。
