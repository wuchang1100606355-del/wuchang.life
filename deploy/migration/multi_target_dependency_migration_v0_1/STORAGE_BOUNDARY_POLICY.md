# Taiji Hub Storage Boundary Policy

版本：2026-05-11  
狀態：三層儲存邊界規則  

## 核心定義

Taiji Hub 的檔案依用途分為三個儲存邊界：

| 邊界 | 用途 | 權限 | 資料敏感度 |
|---|---|---|---|
| Linux 子系統原生空間 | 開發、測試、runtime | 開發者本機 | 中低到中高，依檔案分類 |
| 組織共用雲端空間 | 無敏、唯讀、全設備可用 | 組織唯讀或受控編輯 | 低敏 / 無敏 |
| D 磁碟 / 記憶卡 | 熱資訊、高權限、特殊用途 | 需本人審查、公益度規、記錄在案 | 中高敏 / 特殊用途 |

## 雲端邊界

雲端只存放：

- 無敏文件
- 唯讀文件
- 全設備可用的治理摘要
- 白皮書
- 架構圖
- schema
- deploy artifact manifest
- runtime adapter 原始碼
- 測試檔
- 不含 secret 的 audit summary

雲端不得存放：

- secret
- service account JSON
- OAuth token
- private key
- password
- browser cookie
- Odoo/PostgreSQL live volume
- 會員個別進度
- 會員明文
- D 磁碟熱資訊
- 高權限特殊用途檔案

雲端預設權限：

```text
read-only
organization shared space
all-device accessible
no personal-owner dependency
no anyone-with-link public exposure
```

## D 磁碟 / 記憶卡邊界

D 磁碟不是一般雲端同步區。

D 磁碟可保存：

- 熱資訊
- 高權限特殊用途檔案
- 本地封存資料
- 裝置搬移用資料
- 需離線保存的治理證據
- 特殊用途 runtime snapshot

D 磁碟存取必須符合：

- 公益度規規範
- 本人審查
- audit record
- SHA256 baseline
- 存取理由
- 存取時間
- 存取者身份
- rollback / 封存紀錄

D 磁碟不得被當成：

- 自動公開同步目錄
- 任何設備無限制讀取區
- 個人臨時亂放 secret 區
- 未審查資料交換區

## Linux 子系統原生空間

Linux 子系統是主要開發與 runtime 工作區。

可保存：

- runtime code
- schemas
- tests
- local deployment package
- governance documents
- 本地 audit
- 本地 runtime state

但仍不得輸出或上傳：

- secret 明文
- 會員個別進度
- service account JSON 內容
- private key

## 存取分級

| 資料類型 | Linux | 雲端 | D 磁碟 |
|---|---|---|---|
| 無敏白皮書 | YES | YES readonly | YES |
| 架構圖 / 完成度看板 | YES | YES readonly | YES |
| schema / tests | YES | YES readonly | YES |
| runtime source | YES | YES readonly if no secret | YES |
| deploy manifest | YES | YES readonly | YES |
| runtime audit summary | YES | YES if hash-only | YES |
| full runtime log | YES local | NO | CONDITIONAL |
| local DB | CONDITIONAL | NO | CONDITIONAL |
| Odoo/Postgres volume | CONDITIONAL separate flow | NO | CONDITIONAL separate flow |
| keys / credentials | CONDITIONAL local secure store | NO | CONDITIONAL owner-reviewed |
| member progress | NO in development | NO | NO unless future formal service governance exists |

## L3 Block

以下一律封鎖：

- 將 D 磁碟高權限資料同步到雲端
- 將 secret 放入組織共用雲端
- 將會員個別進度放入雲端
- 未經本人審查存取 D 磁碟特殊用途資料
- D 磁碟資料無 audit / SHA256 / 存取理由
- 將 D 磁碟設成全設備無限制共享

