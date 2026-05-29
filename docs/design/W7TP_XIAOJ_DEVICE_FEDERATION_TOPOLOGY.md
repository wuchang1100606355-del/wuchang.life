# W7TP / 小J 系統總成設備拓樸

狀態：PLANONLY / ARCHITECTURE DESIGN ONLY

## 1. 系統總成

小J / W7TP 系統不是單一伺服器，而是由以下三類設備共同構成的分散式意圖治理網：

1. 會員使用者設備
2. 團體會員三件式設備
3. 協會意圖架構設備

## 2. 會員使用者設備

- 個人手機
- LINE / Web / 小J入口
- 個人 AI 代理人
- 七維身份碼
- 一次性驗證
- 個人服務進度查詢

定位：會員自身主權設備，用於維護會員合法利益、權益、隱私、同意權、服務權與自主權。

## 3. 團體會員三件式設備

- POS
- 店內伺服器 / 店內服務電腦
- 客顯服務電腦 / 會員服務顯示端

定位：團體會員服務節點，承接會員端 AI 意圖，提供 POS、點餐、客顯、店內服務與商家 AI。

適用：
- 商家團體會員
- 非轄區贊助團體會員
- 外送合作商家
- 仁義店社區產業子公司

## 4. 協會意圖架構設備

- W7TP Gateway
- Open WebUI 本地小J工作台
- Odoo 邦聯節點
- Admin-blind privacy / 三鑰保管
- DLQ / audit / redaction / sharding
- 協會治理與意圖路由設備

定位：協會治理中樞，負責意圖路由、脫敏、分片、審核、稽核、PLANONLY 與三鑰制度。

## 5. 共同治理規則

- 所有設備進入小J域後，依七維身份碼、角色、授權、同意、隱私邊界與 W7TP Gateway 治理規則運作。
- 會員設備不等於 Odoo 後台權限。
- 團體會員設備不等於 raw PII 解密權。
- 協會架構設備不等於單一 admin 可任意讀取個資。
- 跨設備服務必須經 redaction、sharding、audit 與 PLANONLY。

## 6. Hardwall

- member_device_is_not_odoo_admin=true
- group_member_device_is_not_raw_pii_access=true
- association_device_is_not_single_admin_decrypt=true
- raw_pii_to_cloud=false
- cross_company_accounting_mix=false
- role_based_permission_required=true
- consent_required=true
- audit_required=true
- plan_only=true
