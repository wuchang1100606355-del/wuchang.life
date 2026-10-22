# 小J合一 AI — 七種場景前綴與管理總頁面

## 一、使用者定義

同模型、同核心、同一自然人身分原胞封包；七種小J是**不同的場景前綴**，不是七個模型、七套登入或七個獨立身分根。

七個頁面分別為：工作秘書小J、商圈服務小J、開發者小J、住宅服務小J、協會服務小J、生活秘書小J、我的社區小J。

每個場景均有獨立的**介紹與管理總頁面**，顯示其意圖、候選技能、可讀資料候選、可修改動作候選、邊際限制、授權來源及稽核說明。前綴選擇只是場景意圖，不自行增加能力或權限。

## 二、既有技術來源與不可混淆之處

- 既有自然人身分前綴：tools/total_field/w7tp_intent_field_suite/identity_prefix.py。其不可變前綴只由現行總場身分簽發者建立，LLM（大型語言模型）不得重寫。
- 既有身分投影驗證：tools/total_field/w7tp_intent_field_suite/identity_projection.py。
- 既有人類需求路由：tools/total_field/xiaoj_human_need_router.py。
- 既有會員入口：tools/total_field/xiaoj_member_product_entry_adapter.py。
- 現行 UI 來源：products/wuchang_xiaoj_community。其 2026-07 產品根／V2.1 相容欄位屬**歷史殼層證據**，不可直接當作 V2.3 正式權威。
- 觀測到 Open WebUI（開放式網頁操作介面）有 xiaoj-founder 模型別名，但沒有證據足以宣稱分散式推論模型在全部節點已統一綁定。
- MSI 的 Open WebUI 實機 oauth.providers（外部登入供應者）為空、一般密碼登入開啟。
- Odoo 的 Google／LINE 入口尚因既有功能控制閘而 HOLD，不得以同信箱直接合併帳號。
- 目前 taiji01 中 wuchang.life/openwebui/ 仍為 HTTP 502，不能宣稱已公開接通。

**在同一身分封包內的正式設計**：不可變自然人身分前綴及七個受治理場景前綴共同依當前八合一動態狀態場生效。現有 immutable prefix schema 不能任意擴充為七個身分根；本候選僅設計服務場景引用及其授權投影，不修改現行正典。

## 三、隔離候選成果

- product_preview/index.html：在既有產品候選首頁**第一屏**加入七個服務入口，保留舊頁面及原有 JS（JavaScript，網頁互動程式）。
- product_preview/scene-pages/：七個管理與說明總頁面；共用 CSS（樣式表），內容以同一 SCENE_PREFIX_VIEW_CANDIDATE.json 來源生成，不重複七份模型。
- SCENE_PREFIX_VIEW_CANDIDATE.json：七種場景候選內容，所有實際讀／寫授權初始為未核對。
- scene_scope_candidate.py：不呼叫真實工具的動作級邊界計算候選；不綁定正式可信 D8 驗證器時停止；即使模擬取得 PASS 也**只回候選可行**，不執行讀寫。
- OPEN_WEBUI_PROMPT_SUGGESTIONS_CANDIDATE.json：對應 Open WebUI 原生七個首頁對話提示卡，**未寫入 MSI Open WebUI 正式設定**。
- ODOO_MEMBER_ENTRY_LINKS_CANDIDATE.json：既有 Odoo 自然人登入後服務入口對接契約草案，**未新增 Odoo 路由或選單**。
- EXISTING_PRODUCT_HOME_PATCH_CANDIDATE.diff：僅針對既有產品首頁的可審查差異。
- evidence/：Chromium（瀏覽器）桌面與手機畫面證據。

## 四、狀態場與授權執行契約

1. 人類選一個小J場景，僅作為意圖線索。
2. 經既有 Odoo 身分來源及 Native ADI（原生時空狀態索引資料庫）取得**本次**可驗證的一人一封包引用、簽發者、來源、期限、撤銷及相關任務證據。
3. 從同一當前狀態場核對選定場景可用技能／資料讀取／資料修改範圍／時效、次數、成本、資料量、交易與風險界線。不同場景不互相自動傳遞授權。
4. 來源不存在、過期、失配，或必要依賴失效時只阻止相關服務動作；其他已確認且獨立獲授權的服務繼續。
5. 模型只能提出候選意圖與下一步，不能修改身分不可變前綴或越過總場 D8（封套／權威）與 Odoo 原生業務規則。
6. 正式讀／寫由伺服端重新核對 D8 動作級權威、同意、來源系統及額度。前端按鈕、JSON（資料格式）或模型輸出不是憑證。
7. 所有應驗收動作保留原始收據、受影響對象、版本、依賴、效果與更正脈絡，不得以 HTTP 200 取代效果驗收。

## 五、實機邊界

本次只在 taiji01 總場候選目錄建立隔離副本，不改動原始產品、Odoo、Open WebUI、DNS、VPN（虛擬私人網路）、路由器、Docker（容器）、資料庫或 Git（版本管理）分支。

**不得把本候選直接部署**。尚須接通真實的登入／身分封包驗證、技能登錄、動作級 D8 授權與限額讀取；並先完成首頁與管理設定的登入後、權限拒絕及真實操作驗收。

## 六、預覽與驗收

已執行共 35 項純候選測試，涵蓋一人一封包、七場景、不可跨場景取得權限、讀寫及次數／額度／成本／風險限制、身分撤銷與期限失效、HTML（網頁標記）連結及原產品 JS 未被修改。隔離 Chromium 畫面：桌面 1365×960、手機 390×900。

下一步：以既有 XJ-021 與 T-019 正式索引及總場權威，讓 Odoo 自然人身分、Open WebUI 同一個小J模型別名、會員能力器官及七場景授權投影真正共用一份動態狀態場，先完成唯讀與拒絕效果驗證，再進行正式發布。
