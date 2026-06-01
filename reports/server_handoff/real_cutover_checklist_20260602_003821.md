# 正式切換檢查表

timestamp: 2026-06-02T00:38:21+08:00
head: 90b8035

## 目前狀態
virtual_handoff: PASS
dual_diff: PASS
odoo_pg_inventory: PASS
rollback_plan: PASS
no_secret_scan: PASS_WITH_REVIEW

## 正式切換前必須確認
- [ ] taiji01 本地 snapshot 已建立
- [ ] Odoo/Postgres DB 名稱與 volume 已確認
- [ ] production copy set 已列出
- [ ] runtime/archive 已排除
- [ ] runtime/sandbox 已排除
- [ ] runtime/reports 已排除
- [ ] copy 與 restart 分離授權
- [ ] 人類核准 copy
- [ ] 人類核准 restart
- [ ] rollback restore test 已通過

## 禁止
- 未核准不得 SSH 操作正式變更
- 不得寫 DB
- 不得重啟服務
- 不得 broad copy
- 不得讀 secret
- 不得把 sandbox/archive 當 production

## 判定
real_cutover_ready: NO
next_gate: production_copy_set_manifest
