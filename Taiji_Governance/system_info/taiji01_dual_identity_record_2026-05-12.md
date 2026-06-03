# taiji01 系統主機雙身分紀錄

版本：2026-05-12

## 結論

`taiji01` 具有雙身分，必須分窗治理，不得混用權限。

## 身分一：系統主機 / Runtime Host

```yaml
identity_id: TDI-HOST-taiji01-runtime-host
host_name: taiji01
account_hint: taiji_01@taiji01
role:
  - Taiji Hub system host
  - Linux runtime host
  - local compute and service carrier
authority_window:
  - local_ssh_connection
  - local_console_operation
  - metric_governed_write
write_boundary:
  default: blocked
  allowed_only_when:
    - local SSH connection by responsible human/operator
    - local physical console operation
    - metric-governed write with manifest, gate decision, audit, rollback
risk:
  ungoverned_remote_write: L3_metric_hazard
```

## 身分二：VPN / Topology Gateway Node

```yaml
identity_id: TDI-NODE-vpn-server-01
host_name: taiji01
tailscale_ip: 100.71.224.18
role:
  - Tailscale node
  - subnet/router node
  - topology adjacency carrier
authority_window:
  - readonly_status
  - route_preflight
  - allowlist_verification
boundary:
  service_object: true
  arbitrary_remote_mutation: false
risk:
  topology_bypass: L3_metric_hazard
```

## 分窗規則

| Window | Allowed | Blocked |
|---|---|---|
| Runtime Host | 本機 SSH、本機現場、度規寫入 | 非度規遠端自動寫入 |
| VPN Gateway | 狀態、路由、節點信任盤點 | 未授權路由修改、VPN 邊界繞過 |
| Audit | SHA256、manifest、rollback、diagnostics | audit 刪除、歷史覆蓋 |

## 既有關聯文件

- `Taiji_Governance/identity/identity_architecture.md`
- `Taiji_Governance/identity/multi_governance_identity.md`
- `Taiji_Governance/identity/digital_identity.yml`
- `Taiji_Governance/runtime/identity/topology_trust_graph.md`
- `Taiji_Governance/runtime/non_linguistic/topology_runtime.md`
- `Taiji_Governance/deployments/cafe_main_redeploy_status.md`
- `Taiji_Governance/policies/system_host_write_boundary_policy_2026-05-12.md`

## 五維碼

```yaml
intent: system_host_dual_identity_governance
resource: host_runtime_and_vpn_topology_node
time: active_development_pre_production
authority: split_window_local_ssh_console_metric_write
topology: taiji01_runtime_host_and_tailscale_subnet_router
```
