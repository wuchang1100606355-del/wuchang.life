# 第二階段已識別的程式模式與治理邊界

**節點／版本／時間：** taiji01，2026-10-09（Asia/Taipei）；HEAD `3c2e5884bc149ffbb02d81fdf288506918fae79e`，工作樹另有 28 個已追蹤未提交修改。
**範圍：** 只讀追查特定元件；模式是程式實作觀察，不是 Founder 技術重新定義，不表示整體設計與實際效果相同。

| 模式 | 實作座標 | 已知能力與不可越界的限制 |
|---|---|---|
| 正典指標與總場授權分離 | `runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json`、`ACTIVE_TOTAL_FIELD_AUTHORITY.json` | 當前指向 V2.3；Git／Hash／UI 不自動得權 |
| 單次、任務限定動態上下文 | `tools/total_field_dynamic_context_pull.py:229–452` | 用 task/provider/model 綁定並限制重播；broker 投影本體不等於模型已接收 |
| 原胞與規則分置 | `tools/w7tp_task_state_minimum_packet.py`、`tools/w7tp_task_state_local_rule.py` | 規則體在本地、封包以 ref 表示；必要 ADI / rule registry 依賴計入成本 |
| 候選式模型代理 | `tools/w7tp_nl_goal_runner.py`、`tools/w7tp_local_model_agent.py` | 隔離 shadow 修改候選；模型推論不能提升權威或當成部署 |
| 有界正式 GST consumer | `services/w7tp_gst_v23_runtime.py`、`ACTIVE_BINDING.json` | 精確綁定、D8 查核、有限交付；狀態 GET 不等於本次交付 |
| 舊 UI 事件紀錄 | `services/w7tp_ui_adapter.py`、`w7tp_evidence_ledger.py` | 編譯→lint→hash→ledger 會寫事件；事件不是正式 D8 裁決 |
| 業務模組與 UI 分離 | `Taiji_Odoo/addons/wuchang_cafe_menu_options/models/menu_manager.py`、`views/menu_option_views.xml` | `product.template` 真正寫入受責任人／公司綁定；視圖/模組 installed 非流程驗收 |
| 單自然人帳號、多職責 | `models/menu_change_request.py:424–736` | 同帳號審核和第二次明確確認，不預設店長／店員分開登入 |
| 會員偏好權限需綁同人 | `wuchang_cafe_ai_gateway/controllers/main.py:759–785` | 目前看到 user auth 和 sudo by supplied member_ref，未見所有權再綁定；為局部高風險候選 |
| 多條路由同名 | `wuchang_core/controllers/xiaoj_ordering_app_controller.py`、`wuchang_cafe_ai_gateway/controllers/main.py` | 匿名 GET 實測落在後者公開候選頁；不得由來源順序猜測全部身份環境 |
| 檔案與載入有區別 | `wuchang_core/controllers/__init__.py` | `menu_import.py`、`pos_mvp_api.py` 未在該 init 載入，故相關函式不能直接宣稱目前啟用 |
| 業務功能閘門 | `wuchang_member_registration/models/member_registration.py:2489–2540` | `is_landing_enabled` 缺少 gate 時預設關閉；某會員功能已啟用，需按目標範圍治理 |
| 現況來源分層 | Docker mounts、DB `ir_module_module`、`ir_model_data`、HTTP GET | 檔案存在→容器掛載→DB 安裝→路由回應→效果驗收為不同證據層，不能跳躍 |

## 導入 V2.3 的關鍵判斷

1. 八維不是上表的一串步驟；表列的每個受查對象，都同時存在意圖、狀態、座標、證據、執行政策、重構／傳輸、風險與權威耦合。
2. `D6` 名稱出現在舊 UI 並不能證明原胞傳輸；真正的 GST 取決於規則、封包、既有條件與驗證的連接。
3. `Hash` 一致只是資料完整性線索；`state_seal` 的無密鑰 fallback 若發生，不等於具自然人授權的簽章。
4. `installed` 表示 Odoo 資料庫模組狀態，`GET 200` 表示某請求可達，並非 POS 訂單、會員兌券或完整產品效果完成。
5. 未知或失配只限制相關業務與結論，不擴大為所有 V2.3 正典或系統失效。

## 現有可重用的測試來源（本輪均未執行）

- `tests/test_total_field_dynamic_context_pull.py`：TTL、重播阻斷、封包純度及暫態回收。
- `tests/test_w7tp_task_state_minimum_packet.py`：同一任務引用／checkpoint 隔離。
- `tests/test_w7tp_nl_goal_total_field_gate.py`：runner local model context 包封及任務約束。
- `tests/test_wuchang_cafe_menu_governance.py`：菜單候選、事物碼與治理驗證。
- `tests/test_ticket_purchase_truthfulness.py`：舊券未綁定時不虛構交易。
- `tests/test_msi_local_llm_route.py`：LAN/Tailscale/SSH 候選順位；與目前無 VPN 授權須再治理對齊。

## 第二階段文件索引

- `component-deep-dives/w7tp-legacy-ui-d8-boundary.md`
- `component-deep-dives/dynamic-context-adi-model-delivery.md`
- `component-deep-dives/odoo-menu-order-member-ticket.md`
- `technical-issues.md`
