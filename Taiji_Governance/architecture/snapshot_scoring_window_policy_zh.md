# 快照得分窗權限閱讀規則

created_at: 2026-05-18T11:12:00+08:00
classification: non_secret_governance_policy
status: active_for_5min_snapshot_scoring

## 定義

快照得分窗不是備份，也不是同步複製。

快照得分窗是每隔固定時間，依照權限邊界讀取允許範圍內的 metadata、治理骨架與架構訊號，計算目前 MVP 架構狀態分數。

## 權限閱讀層級

| 層級 | 可讀內容 | 不可讀內容 | 用途 |
| --- | --- | --- | --- |
| L0 public marker | 檔名、大小、修改時間、hash、非敏感 marker | 內容不明檔案 | 存在性與新鮮度評分 |
| L1 governance readable | 架構文件、排除規則、拓樸圖、續航錨點、schema | secrets、DB、logs、volume | MVP 完整度評分 |
| L2 controlled runtime metadata | systemd 名稱、compose template、非敏感 service 名稱、節點角色 | token、env、實際資料內容 | runtime coverage 評分 |
| L3 restricted data | Odoo DB、PostgreSQL volume、filestore、sessions、private env、keys | 不讀 | 只檢查邊界與是否被排除 |

## 誰看到什麼

| 角色 | 可看到 | 不能看到 | 說明 |
| --- | --- | --- | --- |
| Operator / 操作者 | 拓樸圖、MVP 分數、缺檔清單、風險摘要、下一步建議 | secrets、DB、會員資料、token、原始 logs | 人類決策入口，只看足夠決策的摘要 |
| Codex / 架構代理 | L1 governance 檔案內容、L2 metadata、hash、同名異版候選 | L3 restricted data 內容 | 可做架構比對與文件更新，不讀高敏資料 |
| Snapshot Scoring Window | 檔名、大小、mtime、hash、允許的治理骨架內容 | 檔案本體中高敏內容、volume、session、filestore | 只計分，不搬資料 |
| Windows Control Plane | formal mirror、架構文件、治理政策、schema、非敏感 manifest | live DB、runtime secrets、Odoo volume | 用於整理與閱讀，不承載正式資料 |
| Linux Canonical Root | runtime metadata、服務名稱、治理檔、可執行腳本、健康狀態 | 明文 secrets、DB 內容、會員資料 | 主 runtime 可看運行狀態，但不把敏感內容寫回 formal |
| Business Core / Odoo | 自己的 DB、filestore、sessions、addons、Odoo config reference | 不向 formal mirror 暴露資料本體 | 正式資料只留在共用容器組內 |
| AI Runtime | 任務摘要、允許的 prompt/context skeleton、模型 manifest、heavy asset manifest | 私密 token、DB 明文、會員資料、未紅線 logs | 只拿最小必要上下文 |
| Cloud Scheduler | 節點角色、健康分數、任務政策、allow/block/human decision 結果 | SSH key、Tailscale auth key、service account JSON、DB password | 控制平面只拿 reference，不持有秘密 |
| VPN Node / Tailscale Fabric | 節點名稱、可達性、角色 tag、健康摘要 | 應用層資料、DB、token | 負責連線，不負責資料閱讀 |
| Governance Record Plane | 稽核摘要、政策版本、事件 hash、決策紀錄 | 原始秘密、原始會員資料、完整 DB dump | 留證據鏈，不留敏感本體 |

## 可見性口訣

1. 人看決策摘要。
2. Codex 看治理骨架與 metadata。
3. 快照窗看分數來源，不看資料本體。
4. Odoo 看自己的資料，但資料只在唯一共用容器內。
5. Cloud Scheduler 看節點與政策，不拿 key。
6. Governance 只記錄事件與 hash，不收集秘密。

## 得分項目

| 項目 | 權重 | 說明 |
| --- | ---: | --- |
| anchor_presence | 20 | 四夾是否有 `mvp_persistence_anchor.md` |
| topology_presence | 20 | 四夾是否有 `wuchang_taiji_operational_topology_v0_2.md` |
| exclusion_policy_presence | 15 | 四夾是否有 `mvp_exclusion_policy_zh.md` |
| freshness | 15 | 主要治理檔是否在合理時間窗內更新 |
| role_coverage | 15 | Windows Control、Linux Root、Business Core、AI Runtime、Edge、Governance 是否都有檔案訊號 |
| drift_candidates | -10 | 同名異版未決策越多扣分 |
| restricted_boundary_violation | -30 | L3 內容若進入 formal mirror 或快照窗，重大扣分 |

## 讀取規則

1. 預設只讀 metadata。
2. 只有 L1 governance readable 檔案可以讀內容。
3. L2 只能讀名稱、路徑、大小、修改時間與 hash。
4. L3 不讀內容，不複製，只檢查是否被排除。
5. Odoo 正式資料實例只能一份；快照窗只驗證單一實例規則，不讀 DB。
6. 快照窗輸出 score、risk、missing、drift、safe_next_actions。

## 四夾用途

| 位置 | 快照窗用途 |
| --- | --- |
| `/home/taiji_admin/Taiji_Hub` | Linux-native 主線狀態與治理檔新鮮度 |
| `C:\Users\o0930\Taiji_Hub` | formal mirror 完整度與排除政策一致性 |
| `C:\wuchang_8_0_core` | legacy engine 是否仍可追溯 |
| `/home/taiji_admin` | live evidence root 邊界與節點證據，不讀敏感內容 |

## 輸出格式

每個 5 分鐘窗應輸出：

- window_id
- score
- risk_level
- present anchors
- missing anchors
- drift candidates
- restricted boundary notes
- safe next actions

## 安全邊界

本規則不允許快照窗讀取或複製密鑰、token、`.env`、DB、Odoo/PostgreSQL volume、filestore、sessions、logs、模型權重或 heavy assets。
