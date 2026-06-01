# MSI ↔ taiji01 雙邊虛擬交接差異分析

timestamp: 2026-06-02T00:28:34+08:00
repo: /home/taiji_admin/Taiji_Hub
branch: main
head: df74c95

## 雙邊來源
- MSI 驗收報告: reports/server_handoff/dual_virtual_handoff_acceptance_20260602_002256.md
- taiji01 回報包: evidence/server_handoff/taiji01_virtual_handoff/taiji01_virtual_handoff_20260601_162600/taiji01_virtual_handoff_report_20260601_162600.md

## 差異結論
- MSI 為主 Git repo / canonical evidence host。
- taiji01 目前不是 Git repo，因此不在 01 端提交。
- taiji01 可回報 runtime/container/user boundary 狀態。
- taiji01 runtime 目前只允許 shadow handoff / readonly evidence。
- 正式切換仍需人工核准。

## 一致項
- virtual_handoff: PASS
- runtime_promotion: NO_GO
- db_write: NO_GO
- service_restart: NO_GO
- secret_read: NO_GO

## 主要差異
| 項目 | MSI | taiji01 | 判定 |
|---|---|---|---|
| Git repo | yes | no / not_git_repository | MSI 作為 canonical repo |
| Evidence storage | tracked in Git | outbox tar.gz | 需回傳 MSI 入庫 |
| Runtime containers | not this report focus | Odoo/Postgres readonly snapshot | taiji01 為 runtime target |
| Commit authority | yes | no | commit only on MSI |
| Runtime mutation | no | no | 仍禁用 |

## 下一步
1. 建立 Odoo/Postgres readonly inventory。
2. 建立 taiji01 rollback snapshot plan。
3. 建立 no-secret linter report。
4. 建立 real cutover checklist。
5. 人審後才可進入 copy/restart 分離核准。

## Git status
