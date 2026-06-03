# 原生區唯一正版工作區宣告

- 唯一正版工作區：`/home/taiji_admin/Taiji_Hub`
- 節點：`VPN-MSI-WSL-DEVELOPMENT`
- Windows 掛載區：`/mnt/c/Users/o0930/Taiji_Hub`
- Windows 掛載區用途：封存、衝突審查、人工來源比對。
- 禁止：在 Windows 掛載區直接作為後續開發根、同步資料庫 volume、同步 secrets、反向覆蓋原生區。

## 合併規則

1. 新檔可由 Windows 掛載區補入原生區。
2. 同名不同內容檔案一律進入 `Taiji_Governance/backups/workspace_merge_review_*`。
3. `keys/`、`.env`、service account、token、private key、Odoo data volume、PostgreSQL volume 不進行自動合併。
4. 後續 Codex / 小J 工程操作一律以原生區為 cwd。
