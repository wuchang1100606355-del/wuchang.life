# 系統生效檔案紅隊審查與優化建議

日期：2026-05-12  
範圍：`Taiji_Governance/system_info`、`Taiji_Governance/policies`、`Taiji_Governance/integrations`、`schemas`、`site/taiji_system_dashboard`  
模式：本地只讀掃描 + 文件/schema/manifest 一致性審查  
限制：未讀取 secret、未呼叫 Google API、未修改 Odoo production、未進入容器、未讀會員明文

## 結論

目前生效檔案的治理方向是安全的：會員五維碼不保存個資、會員 AI 端需白名單、Odoo/Google provisioning 仍停在 manifest-only、雲端只接收無敏總量與 reference，本會本地治理可見資料不等於雲端可見。

紅隊主要風險不是已發生外洩，而是未來落地時可能因「便利性」造成越窗：

- 會員 AI 端把五維碼當成萬用通行證。
- Google Workspace provisioning 從 manifest-only 漂移成直接 Admin SDK 寫入。
- 社區總量、人流、時間桶、人口統計在小樣本下可反推個人或單店。
- 總幹事/商家/物業/自然人會員分窗在 Odoo 權限實作時混用。

## 已確認安全點

| 項目 | 狀態 |
| --- | --- |
| JSON / manifest 語法 | 通過 |
| 生效檔案 secret 明文掃描 | 未發現新增 secret pattern |
| 會員五維碼 | 定義為非個資代表碼，不可逆查自然人 |
| 會員 AI 端 | 限定白名單功能，需 Gateway / Five Metric Gate |
| Odoo / Google provisioning | manifest-only，未 live API |
| Google 雲端 | 僅允許 metric/hash/event/anonymized/audit ref |
| 會計資料 | 單店只記營業總額，社區層才看總量市場訊號 |
| 職務/會員分離 | 總幹事不等於一般會員，商家不等於物業/管委會 |

## 紅隊發現

### F1. 五維碼白名單缺少獨立 validator 實作

等級：L2_drift  
目前白名單規則已在政策、schema、manifest 中，但尚未看到獨立 runtime validator，例如：

- `validate_member_five_code_request(packet)`
- `allowed_whitelist_functions`
- `forbidden_member_ai_actions`
- `five_metric_gate_required`

風險：未來 UI 或會員 AI 端可能直接根據五維碼功能名稱執行，沒有經過同一個 validator。

建議：新增 local-only policy stub，不呼叫 Google/Odoo live：

`services/gateway/policies/member_five_code_policy.py`

### F2. 小樣本反推風險尚未格式化為硬性門檻

等級：L2_drift  
政策已寫「不可反推個人/單店」，但尚未定義最小樣本門檻。

風險：例如某時段只有一間店或少數交易，社區總量資料仍可能反推出單店或個人。

建議新增門檻欄位：

- `min_store_count`
- `min_transaction_count`
- `min_distinct_member_count`
- `suppress_if_reidentification_risk=true`

### F3. Google Workspace provisioning 仍需拆分論壇/信箱/群組權限窗

等級：L2_drift  
目前 manifest 已禁止會員 AI 端直接 Admin SDK，但信箱、論壇會員、群組 membership 仍在同一 provisioning manifest。

風險：未來把論壇會員 token 與信箱帳號建立混在一起，會提升 scope。

建議拆三類 manifest：

- `forum_registration_token_request`
- `odoo_mailbox_request`
- `google_group_membership_request`

每類各自 scope、審核、rollback。

### F4. Odoo role 與 Google role 尚未建立一對一映射表

等級：L2_drift  
已有 Odoo 主公司、團體會員、分公司、總幹事等分窗，但尚未看到 Odoo group 到 Google OU/group 的正式對照表。

風險：Google group 權限可能超過 Odoo 場景權限。

建議新增：

`Taiji_Governance/integrations/odoo_google_role_mapping_2026-05-12.md`

### F5. 看板為公開內部視圖，需標示不可作權限來源

等級：L1_near  
看板已不讀 secret，也只載入 `dashboard_state.json`。但看板內容可能被誤認為 live 權限狀態。

建議在看板加註：

「本頁為治理可視化，不是權限授權來源；實際權限以 manifest + Gateway + Five Metric Gate + audit 為準。」

## 優化建議清單

| 優先 | 建議 | 類型 | 風險下降 |
| --- | --- | --- | --- |
| P0 | 新增會員五維碼白名單 validator | code / local policy | L2 -> L1 |
| P0 | 新增小樣本抑制規則 | schema / policy | L2 -> L1 |
| P1 | 拆分 Google provisioning manifest | governance manifest | L2 -> L1 |
| P1 | 建立 Odoo role ↔ Google OU/group 對照表 | integration spec | L2 -> L1 |
| P1 | 看板加註非授權來源 | dashboard | L1 hardening |
| P2 | 將紅隊規則納入測試 | tests | regression guard |

## 建議下一步

1. 新增 `services/gateway/policies/member_five_code_policy.py`。
2. 新增 `schemas/member_five_code_request.schema.json`。
3. 新增 `tests/test_member_five_code_policy.py`。
4. 更新看板非授權來源提示。
5. 建立 Odoo ↔ Google role mapping 文件。

## 禁止行為

- 不得用五維碼直接建立 Google 帳號。
- 不得從會員 AI 端直接呼叫 Google Admin SDK 或 Gmail API。
- 不得用五維碼反查會員明文。
- 不得在小樣本下公開總量資料。
- 不得將總幹事、商家、物業、自然人會員權限混用。
- 不得把看板完成度當成 production 權限依據。

