# 第二階段技術疑點、證據分級與最小下一步

**觀測：** taiji01，2026-10-09（Asia/Taipei）；HEAD `3c2e5884bc149ffbb02d81fdf288506918fae79e`；工作樹另有 28 個已追蹤未提交修改。此為只讀稽核結論，非變更提案批准、非漏洞利用證明、非總場裁決。

## 結論摘要

- 主線 V2.3 正典／產品根 pointer 雜湊未變；當前正式 GST consumer 的只讀狀態回報 D8 已對該 consumer 閉合。
- **最高優先局部候選：** Odoo 已開啟的會員記憶開關路由在已讀來源中未見目標會員與登入自然人之間的授權映射驗證；此處應先作隔離驗證，不影響無關功能。
- **次高優先候選：** Dynamic Context 的已重構 `state_projection` 未在本地模型交付包中出現；原胞發行伴隨 ADI insert，而不能當成零副作用唯讀 Pull。
- 其他獨立候選：舊 UI `TRANSACTION_COMMITTED`／事件帳與 D8 權威混淆、Odoo 點餐路由同名及不同 auth、LAN-first 路由仍保留 VPN fallback。

## 問題矩陣（P 是審查優先度，不是系統失敗率）

| ID／優先度 | 支持／直接觀測 | 反證／未知 | 最小候選下一步 |
|---|---|---|---|
| **C-01 / P0：跨會員偏好與記憶權限邊界** | `wuchang_cafe_ai_gateway/controllers/main.py:352–364,743–785`：`member-memory-toggle` 接受 member_ref 並以 sudo 查詢／寫入；`member-preference-candidate` 使用 `find_by_member_ref` 取得偏好；`wuchang_member_registration/models/member_registration.py:2098–2270` 的 `write` 和查詢未見 caller 所有權檢查，`build_pos_candidate_context` 還會寫 `last_candidate_at`；DB 兩項功能閘門均 enabled | 全域中介層、外部代理與會話 guard 的實際作用仍未知；未送請求、不證明越權成功，也不宣稱資料已洩漏 | 在隔離測試用兩個授權測試身份檢查 A 不能讀改 B 的偏好；沿既有會員身分包驗證 request.env.user，再做精準最小修復 |
| **C-02 / P1：D6 重構資訊未完整送達本地模型候選** | `tools/w7tp_task_state_minimum_packet.py:695–839` 組成投影；`tools/w7tp_nl_goal_runner.py:852–918,1053–1074` 僅回傳並注入 `state_cell_transmission`，未含 `state_projection` | broker 成功暫態重構已由原始碼明確表達；部分 agent 另可讀 shadow source，但不能假設讀到 runtime 狀態；無本次模型等價驗收 | 同任務、同觀測範圍，驗證模型可見內容與答案接收條件；調整時維持 D8 與個資隔離，不自造記憶核心 |
| **C-03 / P1：同名點餐路由之身份／體驗差異** | `/wuchang/xiaoj/ordering` 同時出現在 `wuchang_core` (`auth=user` + packet gate) 與 `wuchang_cafe_ai_gateway` (`auth=public`)；匿名 GET 200 title `小J影音點餐`，吻合公開候選頁 | 此結果未代表已登入員工會話，也不證明業務寫入安全失效 | 在隔離測試明確記錄匿名／店員／會員身份的 route owner 與功能限制；用途分開前不重命名既有 URL |
| **C-04 / P1：No-VPN 意圖與路由候選政策對齊** | `core/msi_local_llm_route.py:25–65,124–163` 有 LAN 優先後的 Tailscale、SSH 備援；測試來源同樣驗證可選用；User 最新意圖禁用 VPN | 本次未主動啟用／探測 VPN，且該檔目前有未提交修改；不證明目前實際走 VPN | 查既有治理 policy 對路由候選是否有限制；若未限制，提交「僅 LAN 或獲明確授權傳輸」最小策略候選 |
| **C-05 / P2：legacy UI 結果與 D8 正式權威可混淆** | `services/w7tp_d6_linter.py` 預設 `TRANSACTION_COMMITTED`；`services/w7tp_evidence_ledger.py` 直接 append；無正式 D8 審核，鍵名不同於 V2.3 | 舊 UI 沒有直接引用 V2.3 deliver；正式 GST consumer 綁定狀態另外獨立健康 | 將 UI 事件標明候選／舊投影，測試下游不可把 ledger/event_hash 視為正式 D8 |
| **C-06 / P2：本地 Context Pull 總成本與副作用帳缺口** | `issue_task_state_minimum_packet()` 先執行 native ADI `/v1/adi/insert`；本地規則與 `/v1/adi/packet` 可重複查詢／重構 | 無本次同任務總封包 bytes、CPU、索引 insert、前置成本量測，不能證明傳輸無效率 | 以既有記錄器量測同任務 end-to-end 前置成本，不改權威，不從 target bytes=0 推導完整成本=0 |
| **C-07 / P2：Odoo 業務鏈驗收尚缺** | 模組 DB installed、視圖 XML ID 存在、匿名菜單／點餐展示頁可達；`/api/pos/v1/order` 為候選且在 core init 未 import；舊券買賣來源回 HOLD | `GET 200`、模組存在或 controller 程式碼不能證明 QuickClick 等價，也不能推出所有會員券失效 | 針對授權員工場景建立菜單、規格、收銀、會員、券、票據、異常處理的逐項相同任務驗收表 |
| **C-08 / P2：Odoo DB 憑證程序參數曝露面** | 只讀查核 Odoo 程序時看到 DB 密碼以 process argv（程序命令列參數）呈現；本文件未寫任何秘密值 | 未量測無權使用者是否能讀取該 argv，不能稱已被第三方取得 | 依原有密鑰治理評估啟動時改採安全傳遞方式，先保持正常服務，不自行重啟 |
| **C-09 / P3：孤立來源不可誤判 live API** | `wuchang_core/controllers/menu_import.py` 宣告無認證匯入路由，但該檔未被 `controllers/__init__.py` import；`pos_mvp_api.py` 同樣未 import | 未遍歷所有可能動態匯入機制，不能給全域不存在斷言 | 只做 import／實際 Odoo 路由表確認，不應擅自部署、不以此檔直接宣稱存在對外未授權可寫 API |
| **C-10 / P1：候選偏好查詢有資料庫副作用** | `wuchang_member_registration/models/member_registration.py` 的 `build_pos_candidate_context()` 更新 `last_candidate_at`；`wuchang_cafe_ai_gateway/controllers/main.py:743–758` 從 POST `member-preference-candidate` 進入此函式 | 本次未確認資料庫目前是否有實際呼叫該路由，亦未測量其效果；受功能閘門與登入要求約束 | 在隔離測試將「只讀偏好投影」和「有審計的最後使用時間更新」分開驗收，保留既有合法操作 |

## 工程裁決的必要條件

1. **證據**：保留節點、檔案版本、觀測時點、實際程式呼叫鏈；靜態分析不直接升格執行結果。
2. **反證**：對 C-01 查有無外部會員授權 guard、對 C-02 查任何額外投影傳遞、對 C-03 比對登入態路由，未解之前只稱候選。
3. **隔離**：只限制相關 member-memory 或 UI/route 的待修覆蓋面，不停掉正常菜單、現行 GST 或整個 Odoo。
4. **驗收**：每項候選定義相同任務、可見輸入、效果及否定案例。安全測試應在隔離資料與授權身份上進行，不使用真實會員資料探測。
5. **權威**：模型建議、unit test（單元測試）通過、DB installed、HTTP 200、Git HEAD、文件寫入都不是 Total Field D8 PASS。

## 第二階段驗收紀錄

- `READ_ONLY_SOURCE_AND_LIVE_METADATA = COMPLETE`；具體證據分載三份 `component-deep-dives/*.md`。
- `TESTS_EXECUTED = 0`，僅讀既有測試來源；無漏洞利用／身份操弄試驗。
- `D8_CANONICAL_CHANGE = NONE`；`PRODUCTION_MUTATION = NONE`；`GIT_COMMIT_PUSH = NONE`。
- 後續第三階段只提供可實作的最小修復／產品驗收建議，不假裝本輪已完成任何修復。

## 補充 C-11｜Founder 的內部傳輸效能優先技術準則（2026-10-09）

- **來源：** Founder 明確指示「內部傳輸應摒除一切不必要的外部防禦以效率優先」，並更正「8DADI是我的技術原理」。此為技術定位與設計方向，不是效能實測或正典檔案變更。
- **P1 候選：** `products/eight_dimensional_generative_memory/w7tp_endpoint_rule_handshake_v1.py:148–256` 逐規則重新雜湊／觀測；`tools/w7tp_origin_context_transport_v1.py:129–301` 建立多種候選封包，於接收端再做握手重觀測。直接程式證據成立，重複成本是否顯著仍未知。
- **既有反證：** `tests/test_w7tp_origin_context_transport_v1.py` 已設計大型重複訊息選原胞、小訊息可選完整傳輸；`w7tp_endpoint_rule_handshake_v1.py::select_transport` 已比較序列化線上位元組數。不可說現行程式完全沒有擇優。
- **缺口：** 尚未將握手／規則雜湊／原胞產生／ADI 查表／重構／驗證／重試成本，按同任務條件一起計量；且原胞 adapter 是否為所有 live 節點正式路徑未驗證。
- **最小下一步：** 沿既有端點規則握手和原胞傳輸 adapter 優化；候選方向為已驗能力有效期內重用、刪除無必要外部中轉與重複驗證，以及相同任務完整成本選擇器。D7／D8 是 8D ADI 技術原理中的耦合維度，不應增造外部防禦鏈；跨主體授權與真實失配仍按必要條件處理。
- **詳細工程證據：** `analysis/component-deep-dives/internal-transport-8dadi-efficiency-principle.md`。`IMPLEMENTED=false`、`DEPLOYED=false`、`BENCHMARKED=false`。

## 2026-10-09 C-11 最小落地更新

- 已在既有 `tools/w7tp_bridge_dynamic_context_transport_v1.py` 移除 `build_plan()` 智能／資源計畫依賴；採確定性工作紀錄／檢查點 task 綁定，傳輸選擇仍委託既有規則握手器。
- 不猜測 unknown task，不允許一條意圖內有多個明確 task 時擅自選擇。測試 8 + 4 + 8 = 20／20 通過；為局部程式與模擬測試結果。
- **仍未閉合：** C-11 的快取／重複雜湊成本優化、實際工作請求端至接收端的 live 呼叫關係及同任務端到端效能測量。既有非橋接路由仍可使用模型；本次沒有全域替換或部署。
- 詳細變更位置：`analysis/component-deep-dives/internal-transport-8dadi-efficiency-principle.md`。`CODING=YES`、`DEPLOY=NO`、`D8_REVIEW=NOT_RUN`。
