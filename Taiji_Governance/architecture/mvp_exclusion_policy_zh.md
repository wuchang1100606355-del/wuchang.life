# MVP 無用檔案排除規則

created_at: 2026-05-18T11:08:00+08:00
classification: non_secret_governance_policy
status: active_for_architecture_comparison

## 目的

本檔定義哪些檔案不進入 MVP 架構比對、拓樸圖、模組採用決策與正式同步流程。

排除不代表刪除。排除只表示：這些檔案不應作為架構成熟度、模組優先級、同名異版採用判斷的依據。

## 排除類型

| 類型 | 例子 | 原因 | 處理方式 |
| --- | --- | --- | --- |
| vendor_or_env | `.venv/`, `venv/`, `.venv_sa/`, `node_modules/`, `__pycache__/`, `.pytest_cache/` | 可重建、檔案多、污染掃描 | 不比對內容，只保留 requirements 或 lock file |
| cache_or_build | `.cache/`, `.npm/`, `open-webui/`, `build/`, `dist/`, `redis_data/` | 快取或第三方 build 產物 | 只記來源與重建方式 |
| secret_or_credential | `.env`, `*.key`, `*.pem`, service account JSON, private key, token | 高敏 | 不進 formal Hub，不進圖，不進一般同步 |
| database_or_volume | `*.db`, SQLite, PostgreSQL volume, Odoo data volume | 高敏或狀態型資料 | 只記 volume 名稱、用途、備份策略 |
| heavy_asset | `*.gguf`, model files, `*.tar.gz`, `*.tgz`, large release bundles, audio cache | 重但通常不代表架構 | 放 heavy asset layer，使用 manifest/hash |
| log_or_audit_dump | `*.log`, 大型 audit dump, route dump, process dump | 可能含敏感資訊且會放大完成度 | 只保留摘要、紅線後報告、hash |
| editor_or_os_noise | `.git/`, `.vscode/`, `.swp`, `Thumbs.db`, `Desktop.ini` | 工具狀態，不是系統模組 | 排除 |

## 四夾適用範圍

| 位置 | 排除重點 |
| --- | --- |
| `/home/taiji_admin/Taiji_Hub` | live runtime、logs、snapshots、secrets、open_webui_data、模型、release bundles |
| `C:\Users\o0930\Taiji_Hub` | keys、archive secrets、venv、data DB、Odoo volumes |
| `C:\wuchang_8_0_core` | venv、open-webui vendor tree、DB、logs、tarball、service account JSON |
| `/home/taiji_admin` | home-level secrets、Ollama models、system cache、large audit dumps、runtime volumes |

## Odoo 單一實例規則

Odoo 屬於 Business Core，不可在四夾中各自形成多份正式運行實例。

規則：

1. Odoo 18 只能有一份正式運行實例。
2. 正式 Odoo 必須位於共用容器組內，與唯一 PostgreSQL/Odoo data volume 綁定。
3. 其他資料夾只能保存非敏感的 compose template、addons source、部署說明、遷移計畫或冷備份索引。
4. `C:\Users\o0930\Taiji_Hub\Taiji_Odoo` 不作為獨立正式 runtime，只能作 formal mirror/template。
5. `/home/taiji_admin/Taiji_Hub/Taiji_Odoo` 若存在，必須被視為共用容器規格或 live evidence，不得直接複製成第二套 DB。
6. `C:\wuchang_8_0_core` 不承載正式 Odoo，只能提供 legacy integration reference。
7. PostgreSQL volume、Odoo data volume、sessions、filestore 預設高敏，不進 MVP 檔案比對。

判斷口訣：Odoo 可以有多份規格檔，但只能有一份正式資料實例。

## MVP 比對保留類型

以下類型可以進入 MVP 架構比對：

| 類型 | 例子 |
| --- | --- |
| architecture_doc | `Taiji_Governance/architecture/*.md`, topology docs |
| governance_policy | policy markdown, YAML governance rules |
| runtime_source | gateway, runtime entry, adapter source code |
| deployment_recipe | Dockerfile, docker-compose template, systemd template, start/stop scripts |
| schema | JSON schema, YAML schema, protocol schema |
| test_source | tests, validation scripts |
| manifest | non-secret manifest, hash list, module inventory |

## 同名異版處理

同名但內容不同的檔案不能直接覆蓋。必須先做特徵比對：

1. 比檔案角色：runtime、gateway、deployment、schema、governance。
2. 比修改時間與來源：Linux live、Windows formal、legacy core。
3. 比敏感度：含 secret/env/DB/log 者不得升級為 formal 檔案。
4. 比可重建性：可重建者只保留 manifest。
5. 做採用決策：adopt、merge、archive、ignore。

## 關機前保留

關機前只需要確保以下非敏感文件存在於四個續航位置：

- `mvp_persistence_anchor.md`
- `wuchang_taiji_operational_topology_v0_2.md`
- `mvp_exclusion_policy_zh.md`

## 安全邊界

本檔不列出任何密鑰內容、token、DB 密碼、Tailscale auth key、service account JSON 內容、會員資料、語音原始資料或 runtime volume 內容。
