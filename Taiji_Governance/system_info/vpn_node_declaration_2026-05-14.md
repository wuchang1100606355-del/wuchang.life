# VPN 節點宣告與唯一正版工作區

- 產生時間：2026-05-14T03:26:28+08:00
- 唯一正版工作區：`/home/taiji_admin/Taiji_Hub`
- Windows 掛載工作區：`/mnt/c/Users/o0930/Taiji_Hub`，定位為來源封存與人工審查，不再作為主工作區。
- 本宣告僅為本機治理宣告，不修改 Tailscale ACL、不遠端部署。
- 全域寫入規則：只有原生區本機寫入、taiji01 本機 SSH/現場操作、或度規治理寫入可進入寫入窗；其他 VPN 節點不得直接寫入 production。

## 節點表

| 節點 | IP | OS | 角色 | 信任位置 | 寫入邊界 | 狀態 |
|---|---:|---|---|---|---|---|
| MSI WSL / taiji_admin (`VPN-MSI-WSL-DEVELOPMENT`) | `100.107.187.77` | linux | development_node, orchestration_node, canonical_workspace_host, local_runtime_node | trusted_local | local_write_allowed_with_audit | online |
| taiji01 / VPN 節點伺服器01 (`VPN-TAIJI01-SERVER-01`) | `100.71.224.18` | linux | governance_node, edge_runtime_node, memory_node, subnet_router, metric_governed_write_target | trusted_vpn_after_preflight | local_ssh_or_local_console_or_metric_governed_write_only | online |
| MSI Windows 11 Pro (`VPN-MSI-WIN11-OPERATOR-CONSOLE`) | `100.105.82.28` | windows | operator_console, browser_ui, ollama_ui_host, local_human_interface | trusted_local_ui_gateway_controlled | no_direct_system_write_without_gateway | online |
| drallion (`VPN-DRALLION`) | `100.84.254.20` | android | mobile_operator_device, human_confirmation_interface | trusted_user_device_limited | confirmation_only_no_direct_runtime_write | online |
| iphone-11 (`VPN-IPHONE_11`) | `100.94.212.10` | iOS | mobile_operator_device, human_confirmation_interface | trusted_user_device_limited | confirmation_only_no_direct_runtime_write | online |
| penguin Linux auxiliary node (`VPN-PENGUIN-LINUX-AUX`) | `100.111.139.7` | linux | auxiliary_linux_node, low_risk_compute_candidate | trusted_vpn_low_risk_after_preflight | no_production_write | online |
| v3-mix-edla-gl (`VPN-V3_MIX_EDLA_GL`) | `100.98.69.115` | android | mobile_operator_device, human_confirmation_interface | trusted_user_device_limited | confirmation_only_no_direct_runtime_write | online |
| wuchang-us-free-node (`VPN-WUCHANG_US_FREE_NODE`) | `100.94.236.81` | linux | ephemeral_cloud_compute_node, low_sensitive_batch_candidate | external_cloud_low_trust_even_if_vpn | no_secrets_no_pii_no_production_write | online |
| wuchang-us-free-node-1 (`VPN-WUCHANG_US_FREE_NODE_1`) | `100.116.123.20` | linux | ephemeral_cloud_compute_node, low_sensitive_batch_candidate | external_cloud_low_trust_even_if_vpn | no_secrets_no_pii_no_production_write | online |
| wuchang-us-free-node-2 (`VPN-WUCHANG_US_FREE_NODE_2`) | `100.94.209.106` | linux | ephemeral_cloud_compute_node, low_sensitive_batch_candidate | external_cloud_low_trust_even_if_vpn | no_secrets_no_pii_no_production_write | online |
| wuchang-us-free-node-4 (`VPN-WUCHANG_US_FREE_NODE_4`) | `100.99.148.2` | linux | ephemeral_cloud_compute_node, low_sensitive_batch_candidate | external_cloud_low_trust_even_if_vpn | no_secrets_no_pii_no_production_write | online |

## 認知校準

- MSI WSL 是開發與正式原生工作區，不再以 `/mnt/c` 為開發根。
- MSI Windows 是人類操作台、瀏覽器 UI、Ollama/OpenWebUI 視窗，不因本機身分取得直接 production 寫入權。
- taiji01 是 VPN 節點伺服器01、治理/邊緣/記憶節點與 192.168.50.0/24 子網路路由候選，寫入需符合本機 SSH、現場操作或度規寫入。
- wuchang-us-free-node 類節點可作低敏/無敏算力候選，不得存放 secret、會員明文、商業機密或 Odoo production 資料。
- 行動裝置節點可作人類確認與狀態查看，不可作無人決策寫入點。

## 風險與後續

- L1：節點宣告與原生區鎖定已完成。
- L2：目前 Tailscale 控制平面仍是個人 tailnet；wuchang.life 是治理/domain 邊界。未來若切換組織 tailnet，需另立遷移計畫與 ACL。
- L3 阻擋：任何節點嘗試繞過 Gateway/Five Metric Gate/audit/rollback/human decision 直接寫 production。
