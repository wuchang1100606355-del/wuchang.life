# No-Secret 命中項分類報告

timestamp: 2026-06-02T00:38:21+08:00
head: 90b8035

## 結論
no_secret_scan: PASS_WITH_REVIEW
production_secret_leak: NOT_CONFIRMED
archive_secret_trace: FOUND
sandbox_secret_trace: FOUND
critical_blocker: NO_FOR_VIRTUAL_HANDOFF
real_cutover_gate: HUMAN_REVIEW_REQUIRED

## 分類
### 誤報
- tools/security/no_secret_linter_simple.py
原因：掃描規則本身含 OPENAI_API_KEY / GOOGLE_CLIENT_SECRET / LINE_CHANNEL_SECRET / PRIVATE KEY 等字串。

### 歷史/封存痕跡
- runtime/archive/*
- runtime/archive/restricted_backup_archive_20260601/*
- runtime/reports/*
原因：屬歷史報告、備份、掃描結果或封存同步內容，需保留為 restricted review，不直接進 production copy set。

### Sandbox 痕跡
- runtime/sandbox/odoo_sync_validation/*
原因：屬 sandbox/validation 區，不可直接納入正式 runtime promotion。

## 決策
- 虛擬交接：PASS
- 正式切換：仍需 human review
- production copy set：必須排除 runtime/archive、runtime/sandbox、runtime/reports 與 secret-like report
