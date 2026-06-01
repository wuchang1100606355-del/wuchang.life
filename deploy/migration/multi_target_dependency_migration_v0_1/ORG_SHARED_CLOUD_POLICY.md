# Organization Shared Cloud Policy

版本：2026-05-11  
適用：wuchang.life 組織共用空間  
狀態：無敏唯讀 staging / manifest only，不直接上傳  

## 核心修正

雲端目標不是個人雲端硬碟，而是組織共用空間。

雲端所存放的資料定位為：

```text
無敏
唯讀
全設備可用
組織共用
```

因此雲端同步必須符合：

- 組織網域：`wuchang.life`
- 空間類型：organization shared space / shared drive / shared workspace
- 擁有權：組織治理，不屬於私人帳號
- 權限：最小權限、群組或角色授權，不用個人散發連結
- 日誌：需保留 staging manifest、SHA256、audit record
- 個資：不得含會員個別進度或會員明文
- secret：不得含 key、token、service account JSON、OAuth secret、private key、password
- 權限：預設唯讀，不作為熱資訊或高權限資料存放區

## 不可做

```text
不得直接上傳到個人 Google Drive 根目錄
不得使用私人帳號作為唯一擁有者
不得建立 anyone-with-link 公開分享
不得同步 keys/、.env、token、credentials、service account JSON
不得同步 Odoo/PostgreSQL live volume
不得同步會員個別進度
不得同步可逆推出個人的 tensor/hash/vector label
不得同步 D 磁碟熱資訊或特殊用途資料
```

## 可進入組織共用 staging 的類型

| 類型 | 可否進入 | 條件 |
|---|---|---|
| 白皮書 / 架構文件 | YES | 不含個資與 secret |
| governance policy | YES | 不含個資與 secret |
| schemas | YES | 不含 secret example |
| tests | YES | 不含真實資料 |
| deploy artifact | CONDITIONAL | 僅無敏 script / manifest |
| runtime adapters | YES | 不含 key/token |
| audit summary | CONDITIONAL | packet hash / document hash only |
| DB / Odoo volume | NO | 另走資料庫備份治理 |
| keys / credentials | NO | 永久禁止 |

## 組織共用空間建議資料夾

```text
wuchang.life Shared Space/
  Taiji_Hub/
    00_README_GOVERNANCE/
    01_Whitepaper/
    02_Runtime_Schemas/
    03_Deployment_Artifacts/
    04_Audit_Summaries/
    05_Architecture_Dashboards/
    90_Archive/
```

## 上雲前人工檢查

必須先在本地 staging 檢查：

```bash
find /home/taiji_admin/Taiji_Hub_Org_Shared_Staging -type f | sort
```

再做 secret scan：

```bash
rg -n --pcre2 '-----BEGIN|private_key\s*[:=]|client_secret\s*[:=]|oauth_token\s*[:=]|api_key\s*[:=]|password\s*[:=]|ya29\.|AIza' /home/taiji_admin/Taiji_Hub_Org_Shared_Staging
```

若有命中，必須停止，不得上雲。

## 風險分級

| 行為 | 等級 | 處置 |
|---|---|---|
| 本地建立 org shared staging | L1_near | allow_with_audit |
| 組織共用空間手動上傳無敏文件 | L1_near | allow_with_audit |
| 使用 Google API 自動上傳 | L2_drift | 需 Gateway / Audit / Scope |
| 上傳 secret / service account JSON | L3_metric_hazard | block |
| 上傳會員個別進度 | L3_metric_hazard | block |
| 個人帳號成為唯一擁有者 | L3_metric_hazard | block |
