# 會員資訊庫 D 磁碟守門人政策

版本：2026-05-11  
適用主體：新北市三重區五常社區發展協會  
資訊負責人：江政隆，本會授權之總幹事  
數位代表號：admin@wuchang.life  
儲存定位：本機 D 磁碟 / 記憶卡  
生效時點：系統正式交付營運後；開發期間僅為治理設計  

## 開發期狀態

目前開發期間無正式會員個資庫。功能測試資料為本會幹部帳號測試用途，不等同正式會員資訊庫。

## 核心定義

會員資訊庫設於本機 D 磁碟 / 記憶卡。

此設計象徵並落實：

```text
資訊負責人為本會會員個資守門人。
會員資訊庫不屬於一般雲端同步資料。
會員資訊庫不屬於 AI 可任意記憶或任意讀取的資料。
會員資訊庫需經本人審查、公益度規、audit、SHA256 baseline 與存取理由。
```

資訊負責人對會員資訊庫及本系統受保護資訊負保管之責。若發生洩漏，資訊負責人責無旁貸；因此系統必須以更嚴格的分窗、audit、最小必要與本機守門原則設計。

會員資訊資料庫建立後即進入物理封存狀態。封存後僅得於下列三種情境開封：

1. 會員個人設備遺失或變更，為核對五維碼並註記。
2. 中華民國公務機關依法定權限之正式公文書命令。
3. 本人主張資料註銷或變更。

其他日常查詢、AI 記憶、雲端同步、開發測試、POS/Odoo 即時讀寫來源一律禁止。

## D 磁碟定位

D 磁碟 / 記憶卡為：

- 本機高權限資料區
- 會員資訊庫守門區
- 特殊用途資料封存區
- 需本人審查之資料存取區
- 不自動上雲區

建議路徑：

```text
D:/Taiji_Member_Vault/
```

WSL 對應路徑：

```text
/mnt/d/Taiji_Member_Vault/
```

## 可存放資料

| 資料類型 | 是否可存 | 條件 |
|---|---|---|
| 會員基本資料 | YES | 本會治理目的、權限分窗 |
| 會員聯絡資料 | YES | 最小必要、存取留痕 |
| 會員服務紀錄 | CONDITIONAL | 不得進 AI 任意記憶 |
| 會員大會授權相關文件 | YES | 文件版本與 SHA256 |
| 管委會或社區服務關聯資料 | CONDITIONAL | 依場景分窗 |
| 商家營業資料 | CONDITIONAL | 若涉及社區產業專案 |
| secret / token / private key | NO | 不與會員資訊庫混放 |

## 禁止事項

以下一律禁止：

- 將會員資訊庫同步到組織無敏雲端
- 將會員明文資料送外部 AI
- 將會員資訊庫作為自然語言直接查詢資料庫
- 將會員個資寫入 Runtime 長期記憶
- 將會員資料與商家營業資料無界線混合
- 將 D 磁碟設為全設備無限制共享
- 未經本人審查存取會員資訊庫
- 未留下 audit / SHA256 / 存取理由

## 存取流程

```text
存取需求
→ 說明目的
→ 公益度規檢查
→ 本人審查
→ 權限分窗
→ 產生 SHA256 baseline
→ 只讀或最小必要操作
→ audit record
→ rollback / 封存 reference
```

## AI 使用邊界

AI 可協助：

- 建立資料欄位 schema
- 建立匯入格式
- 建立去識別化規則
- 建立檢核表
- 建立 audit record
- 建立統計摘要流程

AI 不可：

- 自行讀取會員明文
- 自行輸出會員明文
- 將會員明文送雲端模型
- 建立可逆推出個人的 tensor/hash/vector label
- 直接修改 production Odoo 會員資料

## 建議資料夾

```text
D:/Taiji_Member_Vault/
  00_ACCESS_REVIEW/
  01_MEMBER_MASTER/
  02_MEMBER_CONTACT/
  03_SERVICE_RECORDS/
  04_MEETING_AUTHORIZATION/
  05_ODDO_IMPORT_REVIEW/
  06_REDACTION_WORKSPACE/
  90_ARCHIVE_SHA256/
```

## Audit Record

每次存取建議記錄：

```json
{
  "event": "member_vault_access_review",
  "vault": "D:/Taiji_Member_Vault",
  "reviewed_by": "江政隆，本會授權之總幹事",
  "purpose": "legal_governance_or_service_operation",
  "public_interest_metric": "aligned",
  "contains_member_plaintext": true,
  "cloud_upload_allowed": false,
  "external_ai_allowed": false,
  "sha256": "sha256:<hash>",
  "decision": "allow_with_audit"
}
```

## L3 Metric Hazard

以下一律標記為 `L3_metric_hazard = block`：

- 會員資訊庫上傳雲端
- 會員明文輸出到外部 AI
- 未審查讀取 D 磁碟會員庫
- 刪除會員庫 audit
- 將會員庫與無敏雲端 staging 混用
- 將會員庫資料轉為私人利益
- 以自然語言直接修改會員 production record

## 最終原則

```text
D 磁碟會員資訊庫是本會受保護資訊之守門區。
資訊負責人是個資守門人，不是資料濫用者。
Taiji Hub 的任務是保護、分窗、稽核、最小必要使用，而不是擴散會員資料。
```
