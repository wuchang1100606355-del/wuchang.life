# Taiji Natural Intent POS Gateway

版本：0.1  
日期：2026-05-11  
狀態：本地設計與測試骨架  
分類：非敏感 POS 與業務服務意圖控制規格

## 產品定位

中文名稱：自然語言意圖控制系統  
英文名稱：Natural Language Intent Control System  
產品模組名稱：Taiji Natural Intent POS Gateway  
替代中文名稱：太極自然語意點餐閘道器

本系統不是泛用瀏覽器控制 AI。瀏覽器若被使用，只是最小權限的動作介面，不是核心系統，也不得成為管理員繞權工具。

核心方向是：以自然語言作為 POS 系統及業務服務系統的輸入介面，將人類語音或文字轉成結構化、可審計、可回滾的 POS/服務意圖。原始自然語言不得直接修改 production POS、Odoo、Google 或任何服務。

## 正確管線

```text
自然語言
  -> 意圖解析
  -> 度規張量判斷
  -> 規向量投影
  -> POS/Service 草稿
  -> 人類確認
  -> 受控執行
  -> audit / rollback
```

自然語言不是最高權限。自然語言只是意圖入口。

## 五維度規張量

每一個使用者請求都必須映射為五維度規張量：

```text
M5 = <N, D, A, W, R>
```

| 維度 | 名稱 | 說明 |
| --- | --- | --- |
| N | node_identity | 涉及的設備、帳號、服務、容器、POS 終端、客顯機、Odoo runtime、voice gateway 或本地 AI 節點 |
| D | data_sensitivity | public_menu_data、non_sensitive_metadata、order_draft、transaction_reference、customer_personal_data、payment_sensitive_data、secret_or_token |
| A | action_intent | menu_query、pos_order_create、pos_order_modify、pos_order_cancel_item、pos_order_confirm、payment_prepare、payment_execute、service_request、display_update、staff_assist、manager_override |
| W | permission_window | design、development、testing、governance、finance_accounting、deployment_preparation、runtime |
| R | reversibility_public_value | 可逆性、rollback 可能性、audit 需求與公益/服務價值 |

## 規向量

```text
Vr = <allow, audit, warn, block, require_human_confirmation, rollback_required>
```

系統必須計算：

```text
IntentResult = Gate(M5) -> Vr
```

任何自然語言命令都不得繞過 `Gate(M5)`。

## POS 與業務服務意圖類別

| 意圖 | 預設風險 | 預設行為 |
| --- | --- | --- |
| menu_query | L0 | allow，read-only |
| staff_assist | L0/L1 | 無 mutation 時 allow；涉及任務建立時 audit |
| pos_order_create | L1 | 建立草稿，audit，人類確認後才可提交 |
| pos_order_modify | L1 | 修改草稿，audit，人類確認後才可提交 |
| service_request | L1 | 建立服務請求草稿，audit |
| display_update | L1 | 僅限非敏狀態顯示，audit |
| pos_order_confirm | L2 | warn，人類確認，audit，rollback note |
| pos_order_cancel_item | L2 | 已確認訂單取消項目需人類確認與 rollback note |
| payment_prepare | L2 | 僅準備付款流程，不執行付款 |
| payment_execute | L3 | block |
| manager_override | L3 | block |

## 人類確認規則

- L0 read-only 查詢可不需人類確認。
- L1 可建立草稿或服務請求，但不得直接送出 production mutation。
- L2 必須有明確人類確認、audit record 與 rollback note。
- L3 預設阻擋，除非未來另有獨立、已審核、已啟用的人類治理 runtime。

## Audit 與 Rollback

每個 intent action manifest 至少要保存：

- `request_id`
- `raw_text_hash` 或非敏 redacted summary
- `node_identity`
- `data_sensitivity`
- `action_intent`
- `permission_window`
- `risk_level`
- `requires_human_confirmation`
- `allowed_action`
- `audit_required`
- `rollback_required`
- `target_system`
- `created_at`

原始顧客語音或文字不得預設保存。若需要保存，必須先被分類為非敏感，並經 Gateway/Five Metric/human decision 放行。

## L3 Metric Hazard

以下情況一律視為 `L3_metric_hazard`：

- 原始自然語言直接修改 production POS、Odoo、Google 或其他服務。
- AI 未經人類確認執行付款、退款、折扣、刪除或主管覆核。
- AI 讀取或輸出 secret、token、private key、service account JSON、OAuth credential 或 session cookie。
- 顧客個資以可逆方式嵌入五維碼、稀疏張量標籤、metadata 或 hash label。
- Odoo 顧客明文被送往 Google、OpenAI、Jules 或任何外部 AI 服務。
- Open WebUI 或類似 AI UI 未受信任網路限制而公開暴露。
- AI 使用 admin browser session 提交高權限設定。
- Gateway、Five Metric、audit、rollback 或 human decision 被繞過。

## MVP v0.1

MVP v0.1 只實作：

- voice/text input placeholder。
- 自然語言到結構化 intent。
- POS 訂單草稿產生。
- 員工/顧客確認顯示。
- audit event 產生。

MVP v0.1 不實作：

- payment execution。
- refund。
- discount override。
- manager override。
- member personal data processing。
- Google Workspace live API。
- external AI plaintext context transfer。
- direct production database writes。

## 分工原則

- 度規張量負責判斷場景。
- 規向量負責投影行動。
- Gateway 負責收斂能力。
- Five Metric Gate 負責 allow、audit、warn、block。
- Human decision 負責確認高風險行為。
- Audit/Rollback 負責留下可追溯治理證據。

目標是讓 POS 點餐與業務服務互動更快、更安全、可審計、可自然使用，同時保留人類確認與社區公益治理邊界。
