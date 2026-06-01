# 文件時間版本與封存政策

版本：2026-05-11  
狀態：開發期治理規則  
適用範圍：Taiji Hub、Odoo 場景設計、POS/業務服務系統、Google 無敏帳戶治理、Runtime 文件與部署 artifact  

## 核心規則

本系統在開發期不得保存任何「會員個別進度」。

允許保存的是：

- 整份文件的時間版本
- 整份文件的封存狀態
- 整份文件的 SHA256 baseline
- 整份文件的 audit record
- 整份文件的 rollback reference

不允許保存的是：

- 會員個人進度
- 會員個別任務狀態
- 會員個別服務歷程
- 會員可識別行為時間線
- 以姓名、電話、Email、帳號、裝置或其他識別資訊建立的個人進度追蹤

## 設計目的

此政策用於避免開發期文件、Runtime、Odoo 草稿、POS 草稿、Google Workspace 設定草稿或治理筆記，在尚未進入正式資料保護流程前，形成可識別的會員狀態資料庫。

系統只追蹤「文件版本」與「治理狀態」，不追蹤「個人會員進度」。

## 允許的版本格式

建議使用：

```text
<document_name>__YYYY-MM-DD__vNN.md
<document_name>__YYYY-MM-DDTHH-MM-SS+08-00__snapshot.md
<document_name>__YYYY-MM-DD__archived.md
```

範例：

```text
taiji_runtime_whitepaper__2026-05-11__v01.md
odoo_identity_model__2026-05-11__snapshot.md
pos_service_intent_policy__2026-05-11__archived.md
```

## 封存規則

文件封存時應記錄：

- 文件名稱
- 文件版本
- 封存時間
- 封存原因
- SHA256 baseline
- 是否含敏感資料：必須為 `false` 或標示已去識別化
- rollback reference

不得記錄：

- 會員姓名
- 會員身分證字號
- 會員電話
- 會員 Email
- 會員住址
- 會員個別辦理進度
- 會員個別繳費或服務狀態

## Audit 格式

建議 audit event：

```json
{
  "event": "document_version_archived",
  "document_id": "doc_<hash>",
  "document_name": "example.md",
  "version": "2026-05-11_v01",
  "archived_at": "2026-05-11T00:00:00+08:00",
  "sha256": "sha256:<hash>",
  "contains_member_progress": false,
  "contains_personal_data": false,
  "rollback_reference": "archive/<document_name>/<version>"
}
```

## L3 封鎖項目

以下一律視為 `L3_metric_hazard`：

- 將會員個別進度寫入開發期文件
- 將會員個人資料作為 Runtime 記憶
- 將會員明文送往外部 AI 或雲端 API
- 以會員識別資訊建立向量標籤、tensor label、hash label，且可逆推出個人
- 將會員資料與 POS/Odoo/Google 測試資料混用
- 將公益治理文件轉成會員追蹤資料庫

## 正確做法

開發期只保留：

```text
文件版本 -> SHA256 -> audit -> rollback -> archive
```

不得保留：

```text
會員 -> 個人進度 -> 狀態追蹤 -> 歷程累積
```

## 最終原則

Taiji Hub 開發期治理只追蹤文件與系統狀態，不追蹤會員個人進度。

會員資料若未來進入正式服務流程，必須另行建立：

- 個資法合規邊界
- Odoo 權限分窗
- 人類授權流程
- 最小必要資料原則
- audit / retention / deletion policy

