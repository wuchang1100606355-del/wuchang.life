# W7TP／8D ADI V2.3｜節點納管執行清單與未完成事項

觀測時間：2026-10-09（Asia/Taipei）；taiji01 現行 HEAD=`3c2e5884bc149ffbb02d81fdf288506918fae79e`。
本紀錄是現場查核／續接清單，非總場 D8 權威裁決、非設備部署完成回執。
技術：八合一單一動態狀態場；內部傳輸只用既有規則匝道器（deterministic rule gateway，確定性規則閘道器），不讓 LLM（大型語言模型）選傳輸、不主動 VPN（虛擬私人網路）。

## 目前 Desktop Commander（遠端桌面指揮官）實測

| 管理對象 | RDC 狀態 | 本輪實證 | 尚未完成 |
|---|---|---|---|
| taiji01 | Online（在線） | 已用 RDC 讀取總場與正典；規則橋接器來源候選已修改；原先單元測試 20/20 PASS | 正式 gateway（閘道）入口連結、接收者綁定與跨節點效果驗收 |
| MSI／微星 | Online（在線） | RDC MSI 為 WSL（Windows Linux 子系統）；Ollama 11434/11435 有回應；該 WSL clone 查不到所需三個規則傳輸來源檔 | 確認唯一 Windows/WSL 主體、共享規則版本、正式接收器與 LAN（區網）路徑 |
| penguin／企鵝 | Online（在線） | Linux 端 Ollama、Exact-V3 執行；可用 LAN 位址存取 Odoo；既定位置未找到 rule transport（規則傳輸）模組 | 核對現存真正 runtime（執行環境）的 rule base（規則基座）、兼容性、接收端呼叫 |
| taiji03／太極03 | **Online（已恢復在線）** | 本輪直接連入 WSL：hostname=taiji03、user=lenovo、LAN=192.168.50.148。`/home/lenovo/Taiji_Hub` 僅含歷史網路探測檔，非已驗證的規則程式庫 | 精確實體與接收端程式位置、規則版本、身份／權限與原胞接收能力。不可因在線自動發布 |
| taiji04／SUNMI Android | RDC 清單未列獨立設備 | Founder 確認曾用 Android Wireless Debugging（無線偵錯）。歷史 SUNMI 別名 `V3_MIX_EDLA_GL`、舊 LAN `192.168.50.176`；taiji01/MSI WSL/MSI Windows 的 adb devices/mdns 目前皆空；舊 IP 不可達 | 先讓實體裝置回到同 Wi-Fi（無線區網）並啟用 Wireless Debugging；用已配對宿主取得真實設備 ID、現在的動態埠；再驗證 RDC 是否支援該 Android 裝置作原生端點，否則用既有 RDC 宿主下的 ADB 納管，不造假獨立在線節點 |
| localhost／本機（舊名稱） | Offline（離線） | 歷史 Active node 的 `localhost` 曾描述為 iOS peer（iOS 對等端）；不能視作目前瀏覽器電腦的證明 | 比對唯一設備 ID 與主體，確定保留／重新安裝／正式退役方式；不得先撤銷 |
| wuchang-us-free-node | Offline（離線） | 已長期未連線；未知現在是否是必要的正式工作節點 | 先核對原角色與持續使用需求，若需要再在授權路徑恢復 agent（代理程式），不得為方便啟動 VPN |

## 必須保留的待辦（依序完成，每步寫入新證據）

- [x] 重讀 taiji01 正典指標、Git 與現有進度；本輪已核對。
- [x] 查 taiji03 狀態變更：從前次 Offline → 本次 Online，讀到 `192.168.50.148`。
- [ ] 針對各 RDC 內已上線節點逐台唯讀驗證：agent（代理程式）啟動方式、是否開機自啟、實體 ID／座標、重複別名與來源不混淆。
- [ ] 完成 taiji03 的規則基座定位：其 WSL `Taiji_Hub` 並非 taiji01 的程式庫鏡像；不可直接宣稱已安裝規則器官。
- [ ] 恢復 taiji04 原本已使用過的無線偵錯 ADB 接入；只處理已識別裝置，不盲掃整段 IP，不猜測 PIN／埠；驗證實體序號與 `V3_MIX_EDLA_GL` 對應。
- [ ] 核對 taiji04 在 Desktop Commander 的**平台支援範圍**：不能直接以 ADB 連線成功等同 RDC 原生裝置已新增；若不支援則註明為 ADB 受管子設備。
- [ ] 處理 `localhost`：先核對舊 iOS peer 的真實身分，避免用本機 Windows 誤佔既有身份。
- [ ] `wuchang-us-free-node`：先決定是否仍需要；如需恢復，先查公開網路／主權作用域的單獨授權與傳輸政策。
- [ ] 查各實際執行的 gateway（閘道）、服務與 node receiver（節點接收器）是不是已調用現有規則匝道器；原先 `tools/w7tp_bridge_dynamic_context_transport_v1.py` 源碼候選未驗證 live（正式載入）。
- [ ] 驗證所有接入節點的共享規則指紋、版本、接收就緒狀態與有效授權引用；**不可一律視為相同硬體／角色**。
- [ ] 在隔離測試環境比較完整傳輸與規則原胞傳輸，含真實端到端延遲、CPU（中央處理器）、wire bytes（線上位元組）、ADI（時空狀態索引）查詢／寫入、握手／驗證成本及等價效果。
- [ ] 第三階段原定三份文件：`comprehensive-codebase-guide.md`、`technical-recommendations.md`、`developer-onboarding-guide.md`，目前尚未產生。
- [ ] Odoo 另有 P0 候選：會員偏好／記憶路由與登入自然人的權限綁定，須於會員產品正式釋出前另做隔離驗證與最小修復。
- [ ] 送審本輪規則橋接器來源與新測試，經授權才 `git add/commit/push`；現有 29 個已追蹤未提交變更不能被一併混入或重置。
- [ ] 正式服務接通／D8 裁決／跨節點授權驗收完成後才能宣稱「全節點納管閉合」；目前未完成。

## 工作保護條件

不得更改 `wuchang.life` 網域、路由器、VPN、V2.3 正典指標、T-007；不得跨主體授權、讀取會員明文／密碼、改資料庫或重啟服務。RDC Online ≠ agent 可執行 ≠ 能力就緒 ≠ Active canonical（正式正典）。
