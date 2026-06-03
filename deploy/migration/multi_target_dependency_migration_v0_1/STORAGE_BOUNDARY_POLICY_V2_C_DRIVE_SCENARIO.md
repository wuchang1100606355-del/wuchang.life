# Taiji Hub Storage Boundary Policy v2

版本：2026-05-11  
修正重點：C 磁碟定義為經常讀寫、個別需求之系統資料夾  

## 三層儲存邊界

| 邊界 | 定位 | 典型資料 | 權限規則 |
|---|---|---|---|
| Linux 子系統 | 開發、測試、runtime 工作區 | code、schema、test、runtime artifact | 開發者本機治理 |
| C 磁碟 | 經常讀寫、個別需求系統資料夾 | 團體會員、商家營業資料、管委會會議資訊 | 依場景分窗，不自動上雲 |
| 組織共用雲端 | 無敏、唯讀、全設備可用 | 白皮書、架構圖、無敏 schema、無敏 deploy manifest | 組織唯讀，禁止 secret/個資/營業機密 |
| D 磁碟 / 記憶卡 | 高權限、特殊用途、熱資訊封存 | 高敏 snapshot、特殊用途資料、需審查資料 | 公益度規 + 本人審查 + audit + SHA256 |

## C 磁碟用途

C 磁碟不是雲端公開區，也不是 D 磁碟審查封存區。

C 磁碟可作為日常經常讀寫資料區，處理個別場景需求：

- 團體會員資料
- 商家營業資料
- 管委會會議資訊
- 社區服務案件資料
- Odoo 匯入暫存資料
- POS 營業紀錄
- 會議紀錄與附件
- 待去敏後上雲的候選資料

建議 Windows 路徑：

```text
C:/Users/o0930/Taiji_Data/
```

WSL 對應路徑：

```text
/mnt/c/Users/o0930/Taiji_Data/
```

## C 磁碟建議資料夾

```text
Taiji_Data/
  group_members/
  merchant_operations/
  condo_committee_meetings/
  community_service_cases/
  odoo_import_staging/
  pos_business_records/
  meeting_minutes_private/
  export_review/
  redacted_cloud_candidates/
```

## C 磁碟上雲流程

C 磁碟資料不得直接同步雲端。

正確流程：

```text
C scenario data
→ redact / summarize
→ export_review
→ redacted_cloud_candidates
→ owner review
→ org readonly cloud staging
```

## 資料類型判斷

| 資料類型 | C 磁碟 | 雲端 | D 磁碟 |
|---|---|---|---|
| 無敏架構文件 | YES | YES readonly | YES |
| 團體會員資料 | YES | NO | CONDITIONAL |
| 商家營業資料 | YES | NO，除非去敏摘要 | CONDITIONAL |
| 管委會會議資訊 | YES | NO，除非去敏公開版 | CONDITIONAL |
| 明文個資 | CONDITIONAL | NO | CONDITIONAL with review |
| 營業機密 | YES with local boundary | NO | CONDITIONAL with review |
| Secret / key / token | NO general folder | NO | CONDITIONAL secure store only |
| Odoo/Postgres live volume | NO direct sync | NO | separate DB backup flow only |

## L3 Block

以下一律封鎖：

- C 磁碟明文個資直接進組織雲端
- 商家營業機密直接進組織雲端
- 管委會會議資訊未去敏直接進組織雲端
- C 磁碟資料由自然語言直接寫入 production Odoo
- D 磁碟高權限資料未經本人審查被讀取、同步或上雲
- 將 C 磁碟或 D 磁碟設成全設備無限制共享

## 最終原則

```text
雲端：無敏唯讀，全設備可用。
C 磁碟：經常讀寫，個別需求與場景資料。
D 磁碟：高權限特殊用途，需公益度規、本人審查、audit、SHA256。
Linux：開發與 runtime 工作區。
```

