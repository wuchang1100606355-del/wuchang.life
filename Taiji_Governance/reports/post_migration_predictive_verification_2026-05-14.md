# 遷徙後預測驗證與排除紀錄 2026-05-14

## 結論

原生 Linux 工作區 `/home/taiji_admin/Taiji_Hub` 已可作為唯一正版工作區繼續開發。此次排除重點為「未來誤觸」與「遷徙後路徑漂移」，未變更 Tailscale ACL、未 SSH、未遠端部署。

## 已驗證

| 項目 | 結果 | 風險 |
|---|---:|---:|
| Canonical workspace | `/home/taiji_admin/Taiji_Hub` | L0 |
| Dashboard refresh | `dashboard_state.json` 可重建，總完成度 91% | L0 |
| Odoo local HTTP | `127.0.0.1:8069` reachable | L0 |
| Five Metric Engine | `/health` reachable，`policy_locked=true` | L0 |
| Formal Tensor Runtime | 已啟動於 `127.0.0.1:8126`，health OK | L0 |
| Runtime tests | `12 passed` | L0 |
| Tailscale nodes | 11 nodes online；taiji01 ping OK | L0 |
| Tailscale Serve/Funnel | No serve config | L0 |
| Legacy remote scripts | 預設 blocked，需顯式治理變數才可執行 | L1 |
| Public listeners | 多個 `0.0.0.0` listener 仍存在 | L2 |

## 已排除

1. `POST_MIGRATION_RUNTIME_CHECK.sh` 改為使用穩定 `TMPDIR=/tmp/taiji_pytest_tmp` 與 `python3 -m pytest -q -s`，避免 WSL/tmp capture tempfile 錯誤。
2. `deploy/systemd/*.service` 與 formal runtime package systemd template 已由 Windows 掛載路徑改為原生路徑。
3. `full_system.sh`、`run_nodes.sh`、`run_nodes_status.sh`、`Wuchang_Unified_Core/systemd_ignition.sh` 已 fail-closed，避免誤觸 SSH、遠端執行、殺進程或不受控啟動。
4. `Wuchang_Unified_Core/wuchang_core_control.sh` 的明確啟動路徑改為預設 `127.0.0.1` bind，可用 `TAIJI_BIND_HOST` 覆寫。
5. 新增 `POST_MIGRATION_PREDICTIVE_VERIFY.sh` 作為遷徙後重複驗證入口。

## 尚未自動排除

| 問題 | 原因 | 建議 |
|---|---|---|
| 現行系統服務仍有 `0.0.0.0` listeners | 需要 service unit/firewall 層級修改與 restart，屬於運行服務變更 | 先做 bind-down proposal，再由本人確認維護窗後執行 |
| Tailscale ACL 未切成 wuchang.life 組織 tailnet | 可能造成 lockout 或設備斷鏈 | 先產出 ACL proposal，不直接套用 |
| taiji01 未同步本次本地治理檔 | 遵守不 SSH、不遠端部署 | 待本人確認後，用 manifest/preflight/metric-governed sync |

## 驗證命令

```bash
cd /home/taiji_admin/Taiji_Hub
bash deploy/migration/wsl_native_migration_v0_1/POST_MIGRATION_PREDICTIVE_VERIFY.sh
```

## 風險分級

- L0: 原生工作區、核心 runtime、Odoo、Five Metric、dashboard 均可用。
- L1: 舊腳本已加保險，但仍保留原始能力，需治理變數才可解除。
- L2: 既有服務仍有 `0.0.0.0` 暴露，需下一輪針對 bind/firewall/systemd 做維護窗級修正。
- L3: 本輪未發現已啟用的 Tailscale Funnel、未執行 SSH、未遠端部署、未輸出 secret。
