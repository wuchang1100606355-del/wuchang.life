# Taiji Hub WSL Native Migration v0.1

目的：將 Taiji Hub 從 Windows 掛載路徑搬到 Linux 子系統原生檔案系統。

建議來源：

```text
/mnt/c/Users/o0930/Taiji_Hub
```

建議目標：

```text
/home/taiji_admin/Taiji_Hub
```

## 為什麼要搬

Linux 原生 ext4 路徑比 `/mnt/c` 更適合：

- Python runtime
- shell scripts
- executable permission
- Docker build context
- systemd user/service
- SHA256 baseline
- audit JSONL 連續寫入
- Odoo / POS / Gateway 長期開發

## 安全規則

此遷移包：

- 預設只做 dry-run
- 不覆寫既有目標檔案
- 不刪除來源檔案
- 不啟動 production service
- 不執行 docker compose up
- 不執行 systemctl start
- 不輸出 secret 內容
- 預設排除常見 secret 檔案與 runtime state

## 操作順序

1. 先做 dry-run：

```bash
cd /mnt/c/Users/o0930/Taiji_Hub
bash deploy/migration/wsl_native_migration_v0_1/MIGRATE_DRY_RUN.sh
```

2. 確認計畫：

```bash
cat deploy/migration/wsl_native_migration_v0_1/migration_plan.json
```

3. 實際複製：

```bash
APPLY=1 bash deploy/migration/wsl_native_migration_v0_1/MIGRATE_APPLY.sh
```

4. 到 Linux 原生目標：

```bash
cd /home/taiji_admin/Taiji_Hub
```

5. 產生 hash baseline：

```bash
bash deploy/migration/wsl_native_migration_v0_1/POST_MIGRATION_VERIFY.sh
```

6. 測試 Runtime：

```bash
bash deploy/packages/taiji_formal_tensor_runtime_v0_1_0/PREFLIGHT.sh
bash deploy/packages/taiji_formal_tensor_runtime_v0_1_0/START_LOCAL_V011.sh
bash deploy/packages/taiji_formal_tensor_runtime_v0_1_0/STATUS_LOCAL_V011.sh
```

## 回滾

若尚未切換服務，只要刪除目標副本即可。

```bash
bash deploy/migration/wsl_native_migration_v0_1/ROLLBACK_MIGRATION_COPY.sh
```

此 rollback 只移除本遷移包建立的目標資料夾，不會刪除 `/mnt/c/Users/o0930/Taiji_Hub`。

