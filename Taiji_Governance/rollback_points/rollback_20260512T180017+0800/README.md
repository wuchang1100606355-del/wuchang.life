# Taiji Hub 回滾點 20260512T180017+0800

狀態：已建立去敏開發快照。  
用途：回滾治理文件、Odoo addons、schemas、services、runtime adapters、site dashboard、geospatial seed 與 runtime package。  
不包含：keys、.secrets、.env、Odoo DB volume、Open WebUI data、venv、runtime ledger 原文。

## 檔案

- Snapshot: `Taiji_Governance/snapshots/snapshot_20260512T180017+0800/taiji_hub_safe_snapshot_20260512T180017+0800.tar.gz`
- File list: `Taiji_Governance/snapshots/snapshot_20260512T180017+0800/snapshot_filelist.txt`
- SHA256: `Taiji_Governance/snapshots/snapshot_20260512T180017+0800/SHA256SUMS`
- Rollback script: `Taiji_Governance/rollback_points/rollback_20260512T180017+0800/ROLLBACK.sh`

## 回滾指令

```bash
cd /home/taiji_admin/Taiji_Hub
CONFIRM_ROLLBACK=YES bash Taiji_Governance/rollback_points/rollback_20260512T180017+0800/ROLLBACK.sh
```

## 安全邊界

此快照不是正式資料庫備份，不含會員明文與金鑰。正式 DB 回滾需另走 Odoo/PostgreSQL 備份與會計/個資治理流程。
