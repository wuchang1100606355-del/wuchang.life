# Taiji Hub Google Workspace 組織政策閘道設計

版本：0.1  
日期：2026-05-11  
狀態：設計中，未啟用 live API  
分類：非敏感組織政策設計文件

## 目的

本文件定義 Taiji Hub 如何在未來接入 Google Workspace 組織政策、Admin SDK、Reports API、Gmail/Odoo 信箱與服務帳戶代理能力。現階段只允許設計與本地檢查，不直接呼叫 Google API、不讀取 service account JSON、不輸出 token、不把明文上下文送往雲端。

此處的「超管」與「服務帳戶」只作為授權語意，不代表 AI 可直接取得或使用最高權限。最高權限必須經度規拓樸匝道器降權到最小必要 scope，再通過 Gateway / Policy / Five Metric / Audit / Human Decision。

## 外部參考

本設計依據 Google 官方 Workspace 文件的原則整理：

- Admin SDK Directory API scope：最小化 scope，依資料類型選取必要權限。
- Admin SDK Reports API scope：以 audit/usage readonly 為主。
- Gmail API scope：避免不必要的信件本文讀取與 restricted scope。
- Domain-wide delegation best practices：避免不必要 DWD、限制 OAuth scopes、避免 service account key、降低橫向移動與 insider risk。

## Google Workspace 權限分窗

| 分窗 | 可做 | 禁止 |
| --- | --- | --- |
| 設計窗 | scope 設計、OU/群組模型、policy proposal | 呼叫 API |
| 只讀盤點窗 | 檢查本地是否存在 credential 檔名、不得讀內容 | 讀取 key/token 明文 |
| Gateway 預檢窗 | 產生 request manifest、scope diff、風險表 | 實際 impersonation |
| Reports Audit 窗 | 未來可讀取 admin audit metadata | Gmail/Drive 明文內容 |
| Odoo 信箱窗 | 僅無個資 Odoo 系統信箱的通知/寄件草案 | 個人信箱、會員信件本文 |
| Live Admin 窗 | 目前未啟用 | Admin SDK 實際變更 |

## Odoo 無個資信箱邊界

Odoo 信箱必須設計為無個資或最小資料信箱：

- 只承載系統通知、非敏感狀態、交易代碼或工單代號。
- 不保存會員明文、身分證件、付款敏感資訊、Google 私人資料或 ChatGPT 原文。
- 若收到個資或會員明文，需標記 `L3_metric_hazard`，隔離該資料，不送入 AI 或雲端。
- AI 可產生寄件草案，但不得直接代表人類或組織送出敏感內容。

## Odoo 主場景與 Google 權限管理分工

Taiji Hub 的延伸開發以 Odoo 為場景主系統。Google Workspace 不取代 Odoo，也不承載 Odoo 場景明文；它只作為無敏帳戶、群組、OU、裝置/瀏覽器政策與稽核 metadata 的權限管理層。

分工原則：

- Odoo 保存社區/POS/設備/工單/服務流程的主資料與場景狀態。
- Google Workspace 保存無敏帳戶、群組、OU、政策 label 與 audit metadata。
- Odoo 到 Google 只同步無敏 identity、role、permission label、ticket id 或 device id。
- Google 到 Odoo 只回傳 policy allow/deny、group membership label 或 audit metadata。
- 任何會員明文、交易明文、付款敏感資訊或個人信箱內容都不得進入 Google 權限管理層。

這是一份分工規格，目的在避免單方獨大：Odoo 不直接控制 Google 超管，Google 不持有 Odoo 個資，AI 不持有 secret，Gateway/Five Metric 不替代人類決策。

## 建議最小 scope 候選

實際 scope 必須在啟用前重新確認，並由 Gateway/Five Metric 產生 allow 決策。

| 用途 | 候選 scope | 原則 |
| --- | --- | --- |
| 使用者/群組/OU 設計盤點 | Directory readonly 類 scope | 優先 readonly |
| 裝置盤點 | ChromeOS/mobile device readonly 類 scope | 僅盤點，非 wipe/lock |
| Audit / usage | `admin.reports.audit.readonly`、`admin.reports.usage.readonly` | 只讀稽核 |
| Odoo 系統寄件 | Gmail send 類 scope | 僅無個資 Odoo 信箱，不讀個人信件 |
| 安全事件 | Reports / Alert 類 readonly | 不讀內容本體 |

## Domain-wide Delegation 原則

Domain-wide delegation 是高風險能力，預設不啟用。若未來必須啟用：

- 使用 dedicated Google Cloud project。
- 避免 service account key；優先使用短期憑證或受控簽章流程。
- 僅授權必要 scopes。
- 不允許任意 user impersonation；須指定可代理對象與用途。
- 每次 request 必須有 manifest、scope diff、human decision、audit 與 rollback。
- 不得讓 AI 持有 service account JSON 或 private key。

## Jules / Google Session 處理

Jules session 或 Google 雲端工作階段可被視為珍貴設計來源，但目前不作 live API 讀取。任何雲端內容要進入 Taiji Hub：

1. 先建立非敏感 design manifest。
2. 經 Gateway/Policy/Five Metric 判斷可否引入。
3. 只引入必要摘要或 redacted context。
4. 不引入 token、session cookie、OAuth credential 或私人資料。

## 啟用前 Gate

啟用任何 Google Workspace 功能前，必須完成：

- `L0/L1` risk only；任何 secret exposure 或 cloud plaintext 為 `L3`。
- Gateway route ready。
- Five Metric policy locked。
- audit writable。
- scope manifest ready。
- service account credential remains outside repo。
- Odoo 信箱已驗證無個資用途。
- human decision receipt。

## 明確禁止

- 直接呼叫 Google Admin/Gmail/Drive/Gemini API。
- 讀取或輸出 service account JSON。
- 讀取個人 Gmail 信件本文。
- 將 Odoo 會員明文送到 Google/OpenAI/Jules。
- 讓 AI 使用超管帳號瀏覽器 session 自動修改組織設定。
- 使用 domain-wide delegation 作為日常自動化捷徑。
