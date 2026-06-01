# 回滾快照計畫

timestamp: 2026-06-02T00:33:13+08:00
head: c528f28

## 目標
正式切換前，先定義失敗時如何回到目前狀態。

## 目前安全基線
- MSI main repo HEAD: c528f28
- taiji01: 僅完成唯讀盤點
- Odoo/Postgres: 未寫入
- Service: 未重啟
- DB: 未登入、未修改
- Runtime promotion: NO

## 回滾原則
1. 不覆蓋未知資料。
2. 不直接操作 DB。
3. 不重啟服務，除非人審核准。
4. 切換前必須另建 taiji01 本地 snapshot。
5. copy 與 restart 分離核准。

## 判定
rollback_plan: PASS_PLAN_ONLY
real_cutover_ready: NO
next_gate: no_secret_linter
