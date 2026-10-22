# taiji03／taiji04 規則匝道器接入可行性｜2026-10-09 現場唯讀判定

**技術基準：** Founder 8D ADI V2.3 八合一單一動態狀態場。內部原胞傳輸的傳輸模式由既有確定性規則匝道器判定，不用模型智能分析，不主動 VPN；僅使用已取得身份、規則能力與對應授權的精確節點。
**本次狀態：** `DESIGN_ELIGIBLE_WITH_HOLDS`，非已接通／正式新增正典節點。範圍僅讀取 taiji01、MSI、penguin 來源及有限 LAN/ADB（Android 偵錯橋接）可達性，不掃描網段、不讀取 ADB 私鑰或裝置資料。

## 身分與來源（不同證據層）

- `runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json` 是現行 V2.3 帶路由器狀態場，其節點列包含 Android `V3_MIX_EDLA_GL`，**沒有以 `taiji04` 字面 ID 作獨立節點**，也沒有 `taiji03`。不可因歷史別名自動增加 Active node。
- 歷史 `runtime/total_field/device_registry/vpn_audio_nodes/ACTIVE_TAIJI04_SUNMI_POS_GOOGLE_VOICE_NODE.json` 將 `taiji04` 別名對應 `V3_MIX_EDLA_GL`，標示 `SUNMI_ANDROID_POS`、`ACTIVE_REGISTERED`（這是 2026-08 的**設備登錄**，非當前 Wi-Fi 可達或接收端已具備規則基座的證據）。
- `docs/total_field/W7TP_WIFI_SUNMI_HOMEPAD_INVENTORY_REPORT.md` 記錄 04／SUNMI 的歷史 LAN IP `192.168.50.176` 與未完成的 ADB 裝置實證。`configs/total_field/w7tp_all_node_audio_topology_v1.json` 對 04 曾標示 `HOLD_D3_DEVICE_IDENTITY_MISMATCH`／`runtime_enabled=false`。不能以較舊聲音角色 HOLD 推導 V2.3 整體技術失效。
- `docs/total_field/TAIJI03_FOUNDER_FIXED_STORE_STATION.md` 定義 03 為 Founder 專用固定店內管理站，不是一般會員公共終端；可以作規則匝道器的候選接收端，但不可憑描述取得資料庫或正典修改權。
- `docs/total_field/W7TP_SMALL_AGENT_NODE_AUTHORITY_DEPLOYMENT_REPLAY_REPORT.md` 過去明確把 `taiji03` 與 SUNMI POS 排除於當時八個正式節點的部署名單。此歷史紀錄不否定後續再申請角色有界接入，但**不能由候選直接視為授權部署**。

## 2026-10-09 實機證據

- Remote Desktop Commander（遠端桌面連線指揮官）對 taiji01、MSI、penguin 均顯示 Online；`taiji03` 顯示 Offline（最近約 38 小時前在線）；RDC 清單沒有獨立 `taiji04`。RDC 不等於 ADB 連線管理器。
- taiji01 Linux 與 MSI WSL 均有 `/usr/bin/adb`。兩端 `adb devices -l` 返回空列表；`adb mdns services` 未發現當前無線偵錯服務。執行唯讀查詢時 ADB 客戶端曾自動啟動**本機** adb daemon，沒有對 Android 配對或寫入。
- MSI Windows 主機透過 Windows PowerShell `Get-Command adb` 確認安裝 WinGet Google Platform Tools（Google Android 平台工具）；Windows 原生 `adb devices -l` 和 `adb mdns services` 亦為空。
- 僅檢視 ADB 配對檔**中繼資料**：taiji01 `~/.android/adbkey` 與 MSI WSL `~/.android/adbkey`、`adb_known_hosts.pb` 存在（MSI 的 known-hosts 檔修改於 2026-10-07）；未讀取私鑰／內容。存在配對檔不能證明曾配對的目標一定是 04，也不能證明目前連線有效。
- taiji01 對歷史 `192.168.50.176` 發送**單一**目標 ICMP ping 無回應，`ip neigh` 顯示 `INCOMPLETE`；只證明該位址本次未可達，不證明 Android 永久離線或 IP 不曾變更。
- taiji01 `ssh -G taiji03` 只解析為主機名稱 `taiji03`，未提供經實證的 LAN IP；未透過 VPN／SSH 對 03 做連線。

## 角色接入判定（不是分裂技術原理）

| 節點 | D3 設定／既有角色 | 可納入的候選能力 | 目前必須 HOLD 的事項 |
|---|---|---|---|
| taiji03 | Windows/WSL、Founder 店內固定管理站 | 既有自然人授權範圍內的規則匝道器管理／候選接收端，依節點實際能力執行確定性工作 | 現時離線、沒有已驗 LAN 傳輸與接收端規則指紋；不能自動獲得總場或管理員權威 |
| taiji04 | Owner 歷史 SUNMI／Android 13／POS 語音硬體 `V3_MIX_EDLA_GL` 別名；曾使用 ADB 無線偵錯是 Founder 本次直接補充 | 接受與自身設備能力相符的原胞控制、店員 POS／語音 I/O 候選，通道優先為**已有配對的同區網 ADB**，後續可使用更適合正式產品的既有 app／服務傳輸 | ADB 當前未連線、mDNS 未找到服務、歷史 LAN IP 不可達、精確設備身分／接收規則與 D8 作用域尚未實際綁定；不可把 ADB 除錯通道等同常駐正式商用通道 |

## 具體下一個無副作用核對點

1. 04 設備恢復同區網、無線偵錯開啟後，**先用既有已配對的 Windows/MSI 或 taiji01 ADB 宿主**查 `adb devices -l`、`adb mdns services`，取得當下精確裝置身分與動態埠；不得硬套 `192.168.50.176` 或 5555。若仍需配對，須由實體裝置當下操作確認，不能猜測配對碼。
2. 以可讀的 Android model（設備型號）、serial（序號／雜湊引用）、當前區網 IP、實際連線模式驗證 `V3_MIX_EDLA_GL` 是否真的對應現用 04／SUNMI POS；只將允許的識別引用納入規則匝道器，保留角色與權限差異。
3. 03 恢復上線且能取得區網精確座標後，先唯讀核對其既有角色、服務、已安裝規則基座與版本，再讓既有 `w7tp_endpoint_rule_handshake_v1.py` 判斷是否能力相容，非由模型猜測。
4. 對 03／04 的加入，需區分 node discovery（節點觀測）、capability admitted（能力可接受）、rule transport working（原胞真實交付）、Total Field authority（總場授權）四層；任何實測未通過不可寫成正式閉合。

**不可採用的替代：** 不為找設備自行啟動 VPN、網段盲掃、路由器設定、任意登錄新的 8D 核心或將 ADB 無線偵錯當作跨會員權威通道。

**本次改動：** 僅在 `analysis/` 寫入本診斷文件；沒有變更正典、服務程式、Android 設備、資料庫或 Git 索引。
