# W7TP Indexer Manual Transfer Checklist

Status: `plan-only`

This document describes human-review steps only. It provides no remote access,
transfer, deployment, or container execution command.

## 移動前確認

- [ ] 記錄人工審核者、審核時間、目標節點與變更理由。
- [ ] 確認目標仍為經人審的 `pure_linux_server`，且只處理 one-shot job 準備。
- [ ] 計算並記錄每個允許 artifact 的 SHA256。
- [ ] 確認 path mapping template 中所有實際路徑已另經人工審核。
- [ ] 確認本次動作不包含正式資料庫、路由器設定或居民原始資料。

## 允許搬移的 Artifacts

- `wuchang_indexer_oneshot.compose.template.yml`
- `wuchang_indexer_oneshot_job.template.json`
- `indexer_server_path_mapping.template.json`
- `indexer_oneshot_job_linter.py`
- `indexer_oneshot_compose_linter.py`

## 禁止搬移

- secrets 或任何認證材料
- `.env`
- `keys`
- `.ssh`
- `private_key`
- local inventory
- `postgres_data`
- raw member data

## 搬移後驗證邊界

- [ ] 只允許 dry-run validation，不允許啟動容器。
- [ ] 確認 compose template 維持 `restart: "no"` 與 `network_mode: "none"`。
- [ ] 確認兩個 linter 的結果與 artifact hash 一併記錄。
- [ ] 若驗證不符、artifact hash 不符或遇到禁止資料，立即中止並回到人工審查。

## 必填人工紀錄

| Field | Required Record |
| --- | --- |
| Reviewer | 人工審核者識別 |
| Reviewed at | 審核時間 |
| Artifact hashes | 各 artifact 的 SHA256 |
| Target node | 已審核目標節點 |
| Validation result | dry-run 結果摘要 |
| Decision | 通過、退回或中止 |
