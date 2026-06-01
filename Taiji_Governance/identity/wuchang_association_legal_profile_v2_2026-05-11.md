# 新北市三重區五常社區發展協會法定與數位身分 v2

版本：2026-05-11  
資料性質：組織治理基準資料  
用途：Taiji Hub / Odoo / POS / Google Workspace / 組織共用雲端 / 社區產業發展專案之身份對齊  

## 法定組織資料

| 欄位 | 內容 |
|---|---|
| 組織名稱 | 新北市三重區五常社區發展協會 |
| 立案字號 | 新北市社區補字第1100606355號 |
| 所轄地區 | 新北市三重區五常里、仁忠里、五順里 |
| 中央主管機關 | 衛生福利部 |
| 地方主管機關 | 新北市政府社會局、新北市政府文化局 |
| 所屬網域 | wuchang.life |
| 資訊負責人 | 江政隆，本會授權之總幹事 |
| 數位世界代表號 | admin@wuchang.life |

## 數位世界代表號定位

`admin@wuchang.life` 為本會在數位世界之組織代表號。

此帳號定位為：

- 組織治理窗口
- Google Workspace / wuchang.life 組織管理窗口
- 組織共用雲端空間治理代表
- Taiji Hub / Odoo / POS / 社區產業發展專案之數位行政代表
- 權限分窗、audit、文件封存與組織資料保護之管理入口

此帳號不是：

- 個人私用資料所有者
- 任意繞過 Gateway 的最高權限通道
- 可任意公開會員、商家、管委會敏感資料的帳號
- 可刪除 audit / rollback / SHA256 baseline 的免責帳號

## 資訊負責人定位

江政隆為本會授權之總幹事，於本系統中擔任資訊負責人。

資訊負責人可負責：

- 專案維運授權
- 組織共用雲端 staging 審查
- C 磁碟場景資料分窗規劃
- D 磁碟高權限資料存取審查
- Odoo / POS / 業務服務系統資料保護治理
- audit / rollback / SHA256 baseline 管理

資訊負責人仍受以下邊界約束：

- 會員大會授權脈絡
- 本會公益目的
- Five Metric Gate
- Taiji Gateway
- Audit Runtime
- Human Decision Boundary
- 不得將公益資產轉為私人利益

## 網域治理

`wuchang.life` 為本會所屬數位網域。

建議映射：

| 用途 | 建議位址 |
|---|---|
| 組織主網域 | wuchang.life |
| 治理文件 | gov.wuchang.life |
| 社區服務 | community.wuchang.life |
| Gateway | gateway.wuchang.life |
| Audit | audit.wuchang.life |
| POS / 點餐 | pos.wuchang.life / order.wuchang.life |

所有外部入口需經：

```text
Gateway / Tunnel / Reverse Proxy
→ Five Metric Gate
→ Audit
→ Rollback
→ Human Decision when required
```

## 儲存邊界對齊

| 位置 | 定位 |
|---|---|
| 組織共用雲端 | 無敏、唯讀、全設備可用 |
| Linux 子系統 | 開發、測試、runtime |
| C 磁碟 | 經常讀寫、個別需求、場景資料 |
| D 磁碟 / 記憶卡 | 高權限、特殊用途，需公益度規、本人審查、記錄在案 |

## L3 Metric Hazard

以下行為一律封鎖：

- 使用 `admin@wuchang.life` 繞過 Gateway / Five Metric / Audit
- 將 `admin@wuchang.life` 視為個人私產帳號
- 將本會受保護資訊直接上傳到無敏雲端
- 將會員明文、商家營業機密、管委會敏感資訊送外部 AI
- 刪除會員大會授權脈絡
- 刪除 audit / rollback / SHA256 baseline
- 使用自然語言直接改 production Odoo/POS

## 最終原則

```text
admin@wuchang.life 是本會數位世界代表號。
江政隆是本會授權之總幹事與資訊負責人。
wuchang.life 是本會所屬網域。
所有數位權限必須回到本會、會員大會授權、公益度規與 Taiji Gateway 治理。
```

