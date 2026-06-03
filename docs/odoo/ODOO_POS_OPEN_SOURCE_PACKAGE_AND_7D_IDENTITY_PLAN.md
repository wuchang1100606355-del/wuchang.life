# Odoo POS 開源套件挑選與相對身分 7 維碼落地規畫

## 目標

以 Odoo POS 容器與 POS 沙盒資料庫作為第一實踐場，建立：

1. POS 事件治理。
2. 商家、會員、志工、店員、管委會、協會角色的相對身分 7 維碼。
3. D8 信任封套對接。
4. 開源/OCA/市場套件候選清單。
5. 不碰正式個資、不直接寫正式庫、不讓雲端成為治理主體。

## 開源套件導入原則

第一階段只採「候選清單」，不直接下載安裝外部套件。

候選來源：
- Odoo 官方核心模組。
- OCA / 社群開源模組。
- 已存在本地 Taiji_Odoo/addons 的自製模組。
- reviews / runtime/build 中已存在的候選模組。

導入條件：
- 支援 Odoo 18 或可明確移植。
- license 可接受。
- manifest 清楚。
- 不含外部追蹤、廣告、未知 API key 需求。
- 可在 posdev_* sandbox 測試。
- 不直接接觸 clean18 正本。
- 不接觸 raw_member_pii。
- 不自動寫正式帳本。

## 第一波建議候選

本地優先：
- wuchang_core
- wuchang_cafe_menu_options
- wuchang_fund_allocation
- wuchang_wish_tree_coin
- wuchang_property_local_cloud
- wuchang_property_manpower_surface
- taiji_member_login
- wuchang_line_login
- wuchang_google_member_login

Odoo 官方核心優先：
- point_of_sale
- pos_hr
- pos_online_payment
- pos_sms

外部開源候選：
- 先列入候選，不自動安裝。
- 需人工檢查 license、branch、manifest、security、dependency。
- 通過後才 clone 到 reviews/odoo18_open_source_candidates。

## 相對身分 7 維碼

相對身分不是永久真實身分。  
它是「在特定任務、場域、節點、同意、風險、公益/商業脈絡下」產生的短期治理身份碼。

7D 欄位：

D1 actor_scope：
使用者在此任務中的角色範圍。

D2 relationship_context：
使用者與協會、商家、POS、志工、管委會、會員設備的相對關係。

D3 consent_and_session：
同意狀態、session token、是否可撤回。

D4 privacy_boundary：
raw PII 是否禁止、是否只用 pseudonymous id、是否允許 redacted cloud shard。

D5 service_intent：
點餐、公益額度、惜食、外送、會員服務、活動、補助、管委會服務等意圖。

D6 execution_authority：
可否執行、可否寫 Odoo、可否進 POS、可否進雲端、是否需人審。

D7 evidence_and_metrics：
audit hash、linter、focused status、commit hash、服務紀錄、雙腦 metrics。

D8 trust_envelope：
節點簽章、payload hash、nonce、timestamp、counter、git head、node state hash。

## POS 沙盒優化方向

1. 建立 posdev_* DB。
2. 在 posdev_* 更新 wuchang_core / POS 相關模組。
3. mock POS event 轉 7D identity packet。
4. D8 signer/verifier 驗證。
5. Odoo 留存 redacted audit event。
6. 產生節點同步 receipt。
