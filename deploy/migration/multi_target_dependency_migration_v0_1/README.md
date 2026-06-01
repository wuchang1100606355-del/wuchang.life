# Taiji Hub Multi-Target Dependency Migration v0.1

目的：依照檔案用途與風險，將 Taiji Hub 依賴檔案分別遷移到：

1. Linux 子系統原生工作區
2. D 磁區 / 記憶卡封存區
3. 雲端待同步 staging 區

## 最高規則

- 不直接上傳雲端。
- 不輸出 secret 內容。
- 不複製 service account JSON、private key、OAuth token、password 到 cloud staging。
- 不直接搬移 live Odoo/PostgreSQL volume。
- 不覆寫既有目標檔案。
- 不刪除來源檔案。
- 預設 dry-run。
- 實際 copy 必須 `APPLY=1`。

## 目標用途

| 目標 | 預設路徑 | 用途 |
|---|---|---|
| Linux native workspace | `/home/taiji_admin/Taiji_Hub` | 實際開發、測試、runtime |
| D archive | `/mnt/d/Taiji_Hub_Archive` | 記憶卡/外接碟封存、冷備份 |
| Cloud staging | `/home/taiji_admin/Taiji_Hub_Cloud_Staging` | 去敏後手動雲端同步前審核區 |

## 檔案分類

| 分類 | Linux | D archive | Cloud staging |
|---|---|---|---|
| runtime artifact | yes | yes | yes |
| docs / governance | yes | yes | yes |
| schemas / tests | yes | yes | yes |
| deployment scripts | yes | yes | yes |
| models metadata | yes | yes | no by default |
| data DB | no by default | optional local only | no |
| Odoo/Postgres volume | no | no by default | no |
| keys / credentials | no | no | no |
| runtime logs | no by default | optional | no |

## 使用方式

1. 建立遷移計畫：

```bash
cd /home/taiji_admin/Taiji_Hub
bash deploy/migration/multi_target_dependency_migration_v0_1/BUILD_MIGRATION_PLAN.sh
```

2. dry-run：

```bash
bash deploy/migration/multi_target_dependency_migration_v0_1/DRY_RUN.sh
```

3. 實際執行：

```bash
APPLY=1 bash deploy/migration/multi_target_dependency_migration_v0_1/APPLY_MIGRATION.sh
```

4. 驗證：

```bash
bash deploy/migration/multi_target_dependency_migration_v0_1/VERIFY_MIGRATION.sh
```

## 雲端同步原則

本遷移包只建立 cloud staging，不直接呼叫 Google Drive、Google API、Gemini、OpenAI 或任何外部雲端 API。

雲端同步前必須人工確認 staging 內容：

```bash
find /home/taiji_admin/Taiji_Hub_Cloud_Staging -type f | sort
```

如需上雲，必須另走 Gateway / Audit / Policy / Human Decision。

