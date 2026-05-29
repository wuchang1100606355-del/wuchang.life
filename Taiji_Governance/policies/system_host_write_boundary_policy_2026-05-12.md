# 系統主機寫入邊界政策

版本：2026-05-12

## 生效規則

系統主機 `taiji01` 除本機 SSH 連線、本機現場操作、度規寫入外，不可具有寫入權限。

## 允許

- 負責人於本機現場 console 操作。
- 負責人於本機 SSH 連線中明確執行經審查的本機腳本。
- 度規寫入：具備 manifest、Five Metric Gate decision、audit record、rollback plan 的受控寫入。
- 只讀盤點、健康檢查、節點資訊收集。
- dry-run 與 manifest 產生。

## 禁止

- Codex/Jules/Gateway 透過未經度規 Gate 的 SSH 自動寫入系統主機。
- 非互動式遠端批次寫入。
- 遠端自動覆蓋、搬移、刪除、restart、docker compose up/down。
- 使用遠端寫入繞過 Five Metric Gate、Taiji Gateway、audit、rollback。

## 寫入窗

```yaml
write_window:
  default: blocked
  allowed_when:
    - local_ssh_connection
    - local_console_operation
    - metric_governed_write
  requires:
    - manifest
    - five_metric_gate_decision
    - dry_run
    - audit
    - rollback
    - no_secret_output
```

## 風險

```text
remote_automated_write_without_metric_gate = L3_metric_hazard
local_ssh_or_console_apply_with_manifest = L1_near
metric_governed_write_with_audit_rollback = L1_near
readonly_inventory = L0_exact_match
```
