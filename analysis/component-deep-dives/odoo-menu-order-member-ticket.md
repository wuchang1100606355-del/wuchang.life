# 第二階段元件追查 C｜Odoo 菜單／點餐／會員／票券的來源、載入與權限

**觀測座標：** taiji01，2026-10-09（台北）；Git HEAD `3c2e5884bc149ffbb02d81fdf288506918fae79e`；使用只讀 Docker 觀測、PostgreSQL SELECT、對區網本機 Odoo HTTP GET，不發送資料修改／訂單／票券請求。
**服務定位：** `wuchang_os_odoo_18`（Odoo 18）與 `wuchang_os_pg`（PostgreSQL 15）顯示 Up；容器從 `2026-10-08T03:40:41.883378996Z` 啟動；Odoo `192.168.50.249:8069`。

## 已安裝與承載：確定事實，不等於全部功能已驗收

- `docker inspect` 只讀掛載回報 Odoo `/mnt/extra-addons` 來自 `/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons`；對比三個模組 manifest 在容器內及工作樹 SHA-256 一致。
- 對 `ir_module_module` 的只讀 SELECT：`point_of_sale`、`web`、`wuchang_core`、`wuchang_cafe_ai_gateway`、`wuchang_cafe_menu_options`、`wuchang_member_registration`、`wuchang_google_member_login`、`wuchang_line_login` 均為 `installed`。
- 只讀 `ir_model_data` 有 `wuchang_cafe_menu_options.action_wuchang_cafe_menu_products`、`menu_wuchang_cafe_menu_products`、`view_wuchang_cafe_menu_product_form`、`view_wuchang_cafe_menu_product_kanban` 的正式 XML IDs（程式與資料庫介面識別碼）。
- `ir_model_fields` 確有 `product.template.w5c_code`、`w5c_time_state`、`wuchang_option_group_id`、`available_in_pos`。
- 這些證明「容器掛載與模組／欄位／視圖登錄」；不等於未提交的來源修改已經 Odoo registry（模型登錄）重載，亦不等於業務流程通過驗收。

## 已定位之 menu（菜單）功能及責任

- `wuchang_cafe_menu_options/__manifest__.py` 指向三個 models 以及 `views/menu_option_views.xml`；`models/__init__.py` 確實 import `menu_manager`、`menu_options`、`menu_change_request`。
- `views/menu_option_views.xml:1–135` 的搜尋、卡片、清單與表單提供商品圖、名稱、售價、分類、選項群、上架狀態、封存／再上架；DB 已對應視圖 ID，但本次不代替店員現場操作驗收。
- `models/menu_manager.py:186–480` 擴充 `product.template`：負責人可在同一帳號與其業務批次綁定下新增／修改正式菜單商品，限制欄位且保留 W5C 穩定事物碼；遠端支援不能直接寫正式菜單。
- `models/menu_change_request.py:424–736` 遠端修正採候選→負責人明確審核→同一帳號再次確認套用，套用時驗證當前菜單狀態並寫事件紀錄；這是候選到可執行效果的治理路徑，不表示已測過每條操作。
- `menu_manager.py:526–674` 的「送交總場候選」需要事先配置合法內網 `:9107/api/intent-field` 及 Odoo POS caller ref，才會進行正式候選發送；本次未讀取配置值，也未呼叫 POST，該功能**當前可達性未知**。

## 點餐實際路由與重複宣告

- `wuchang_core/controllers/xiaoj_ordering_app_controller.py:8–35` 宣告 `/wuchang/xiaoj/ordering`，`auth='user'` 並先經 `validate_xiaoj_8d_packet_gate()`。
- `wuchang_cafe_ai_gateway/controllers/main.py:398–401` **同一路徑**另宣告 `auth='public'`，回傳候選展示頁。
- 區網匿名 GET `/wuchang/xiaoj/ordering` HTTP 200，`<title>小J影音點餐</title>`，且沒有 core 的 `.webmanifest` 參照；與 AI Gateway 的公開候選頁吻合。**直接觀測僅證明匿名請求落在公開候選頁**，不是擁有登入的員工也永遠如此，更不是正式 POS 下單已啟用。
- 匿名 GET `/wuchang/xiaoj/order` → title `小J下單`；GET `/wuchang/xiaoj/payment` → title `小J付款`；都是內容可達，不等於後端寫訂單或收款。
- `wuchang_cafe_ai_gateway/controllers/main.py:418–451` 的 `/api/order`、`/api/payment` 呼叫 candidate builder（候選生成器），不是正式 Odoo `pos.order` 交易；`wuchang_core/controllers/pos_mvp_api.py` 的 `/api/pos/v1/order` 明示 `DRY_RUN_CANDIDATE_ONLY`（僅模擬候選）。
- `wuchang_core/controllers/__init__.py` 有 import `order_site`、`xiaoj_ordering_app_controller`、`ticket_controller`，**沒有** import `pos_mvp_api` 或 `menu_import`。因此 `menu_import.py` 即使在來源宣告 `/api/menu/import`，不可據檔案存在便宣稱已載入或目前可受呼叫；不觸發此 POST。
- `wuchang_core/controllers/order_site.py:18–93` 的 `/order` 已可匿名 GET，對 `/api/order/create` 有 `landing.pos_order` feature gate（功能閘門），通過後才可能 `sudo().create` 真實 `wuchang.order`；當前只讀資料庫未查到 `landing.pos_order` 特定閘門紀錄，且 `is_landing_enabled()` 的預設為 false。這限定的是該 gate 的已知狀態，未模擬真正購物。

## 會員與票券：來源實作與效果分開

- `wuchang_member_registration/controllers/main.py:426–447` 提供公開起始會員註冊與狀態查詢；起始註冊會 `sudo().create` 暫態會員登錄，受 `_registration_enabled()` 控制。這是來源可追到的寫入能力，**本次沒有建立任何會員**。
- `wuchang_core/controllers/ticket_controller.py:11–32` 的舊票券路由明示 `HOLD_TICKET_SALES_NOT_BOUND`／`HOLD_TICKET_PURCHASE_NOT_BOUND`，不假造商品、扣款及發券；`tests/test_ticket_purchase_truthfulness.py` 有相關靜態／模擬測試，**本次未執行**。
- `wuchang_cafe_ai_gateway/controllers/main.py:787–811` 的主權會員兌券另有候選與 `dry_run` 路由，分別受社區 feature gate 約束。不可從舊票券 HOLD 推導所有會員券功能不可用，也不可把 dry-run 當正式兌券。
- `wuchang_cafe_ai_gateway/models/member_ticket_payment_gate.py:253–326` 有參考值界線與 `ALLOW_DRYRUN`、`HOLD`、`REJECT` 判斷，建構門檻封包而不是收款憑證。

## 權限高優先度候選：會員記憶開關

- `wuchang_cafe_ai_gateway/controllers/main.py:759–785` 的 `POST /wuchang/xiaoj/api/member-memory-toggle` 雖為 `auth='user'`，但取用前端傳入 `member_ref`／`member_id` 查找目標；`_member_identity_from_ref` (`352–364`) 使用 `sudo().search`；後續 `preference.sudo().create/write`。
- 從這段來源**未見**目標 `member_ref` 與當前 `request.env.user` 或已驗證會員身分包之間的所有權／授權映射檢查，也未看到獨立 D8 授權憑證；此為 `CANDIDATE_CROSS_MEMBER_MEMORY_TOGGLE_SCOPE`，不是已證實越權成功。
- `wuchang_member_registration/models/member_registration.py:2098–2229` 的 `WuchangMemberPreferenceVault` 真正實作 `create`、`write`、`find_by_member_ref`；`write` 直接執行 `super().write(vals)`，再刷新偏好雜湊，該模型函式內亦未見自然人與目標會員授權綁定檢查。這使前述路由的所有權驗證候選具有實際 model-level（模型層）依據，但尚未證明利用成功。
- `wuchang_cafe_ai_gateway/controllers/main.py:743–758` 另一條已登入會員偏好候選路由，同樣以請求提供的 `member_ref` 呼叫 `WuchangMemberPreferenceVault.find_by_member_ref()`；後者於 `member_registration.py:2217–2229` 使用 `sudo().search` 而未見登入者綁定。`build_pos_candidate_context()`（約 2230–2270 行）也會寫入 `last_candidate_at` 時間欄位，並依偏好設定輸出推薦欄位。因此名稱為 candidate 的查詢**仍可能讀取目標偏好並觸發資料庫寫入**。未以真實會員請求驗證。
- 只讀資料庫查得 `sovereign_member_ai_memory`、`sovereign_member_preference`、`sovereign_member_voucher`、`sovereign_member_voucher_redeem` 的 `enabled=true, gate_state=enabled`。此現況提升局部權限候選的優先程度，但不能因此直接認定使用者可以跨會員修改。
- 現有測試目錄搜尋 `member-memory-toggle` 及該 lookup 未找到直接針對這一授權綁定的測試。這是**本次有限範圍未命中**，不能宣稱整個專案沒有任何防護。

## 工作樹／載入落差與次要備查

- 本次 Git 有 28 個已追蹤未提交修改，包含會員註冊、AI Gateway controller、ticket_controller、Compose。由於 Docker 是長期程序，掛載位元組一致及模組已登錄**仍不單獨證明 Python registry 已載入每一條目前磁碟修改**。
- 此次檢視 Odoo 啟動程序時看見資料庫存取憑證以命令列參數形式存在；本文件**不紀錄或回傳任何密碼值**。是否需改善啟動時憑證傳遞屬獨立機敏作業風險，非本輪自動修改範圍。
- 已知 `GET` 只能證明頁面請求行為與 HTTP 回應，不證明同一路徑 JSON-RPC（JSON 遠端程序呼叫）的 POST、付款、正式 POS 或領券效果。

## 驗收與下一步候選

1. P0：針對已啟用 `member-memory-toggle` 的帳號與會員目標，補齊「同一自然人會話→會員身分包→可改權限」驗證測試；未授權的其他會員引用必須拒絕。保留原本合法會員功能。
2. P1：釐清 `/wuchang/xiaoj/ordering` 兩路由的用途，避免公開候選頁與需 8D 身分閘門的操作端共用路徑。先查實際消費端，再決定最小隔離，不直接改 URL 或權威。
3. P1：對菜單建立、雙次確認、上架、登入與點餐連動作真正業務等價驗收；不要因模組 installed 就宣稱 QuickClick 全功能等價重構完成。
4. P2：對券發售與實際 POS order 明確區分候選、受治理 DB 寫入與正式交易收據，沿現有 `landing.pos_order`、會員券閘門驗證，不重新起造核心。

**本次沒有：** 資料庫寫入、會員／交易資料讀取、權限修改、模組更新、Docker 重啟、網域變更或正式 D8 裁決。
