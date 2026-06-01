# 資訊負責人保管責任聲明

版本：2026-05-11  
適用主體：新北市三重區五常社區發展協會  
資訊負責人：江政隆，本會授權之總幹事  
數位代表號：admin@wuchang.life  

## 核心聲明

資訊負責人對本系統全部受保護資訊負保管之責。

若因保管不當、權限失控、錯誤外流、未審查上雲、未留痕存取或其他治理失守導致資訊洩漏，資訊負責人責無旁貸。

此聲明之目的不是擴張個人任意權限，而是建立更嚴格的守門責任與系統防護要求。

## 受保護資訊範圍

受保護資訊包含但不限於：

- 會員資訊
- 明文個資
- 商家營業資料
- 管委會敏感會議資訊
- POS / Odoo 業務資料
- 社區服務案件資料
- D 磁碟會員資訊庫
- C 磁碟場景資料
- audit / rollback / SHA256 baseline
- 系統拓樸與高權限節點資訊
- secret / token / private key / service account JSON 等憑證資訊

## 系統設計義務

因資訊負責人承擔保管責任，Taiji Hub 必須協助落實：

- 最小必要使用
- 權限分窗
- 本機優先
- 雲端無敏唯讀
- D 磁碟高權限審查
- C 磁碟場景資料分類
- 不輸出 secret
- 不將會員明文送外部 AI
- 不將營業機密送雲端
- 不由自然語言直接修改 production
- 所有高敏存取須 audit
- 所有封存須 SHA256 baseline
- 所有可逆動作須 rollback reference

## 不可轉嫁原則

資訊保管責任不得因下列原因被模糊：

- AI 自動化
- 自然語言指令
- 雲端同步便利性
- 代理帳號
- admin 權限
- 開發測試需求
- 多設備存取
- Google Workspace 或 Odoo 權限設定

任何自動化系統都必須服務於資訊保護，而不是成為洩漏藉口。

## 高風險動作

以下動作必須先經本人審查、公益度規、audit 與必要時 human confirmation：

- 讀取 D 磁碟會員資訊庫
- 匯出會員資料
- 匯入 Odoo 會員或商家資料
- 同步資料到組織共用雲端
- 接入外部 AI
- 產生資料摘要供外部使用
- 修改 POS/Odoo production
- 存取 secret 或憑證
- 刪除或修改 audit / rollback / baseline

## L3 Metric Hazard

以下一律封鎖：

- 未審查外流受保護資訊
- 將會員明文送外部 AI
- 將 D 磁碟會員庫同步到雲端
- 將商家營業機密放入無敏雲端
- 用 admin 權限繞過 Gateway / Five Metric / Audit
- 以自然語言直接讀寫 production Odoo/POS
- 刪除洩漏相關 audit 或 baseline
- 以任何自動化理由規避資訊負責人保管責任

## Runtime Enforcement

任何處理受保護資訊的 runtime packet 必須包含：

```json
{
  "custodian": "江政隆，本會授權之總幹事",
  "custodian_accountability": true,
  "data_scope": "protected_association_information",
  "minimum_necessary": true,
  "audit_required": true,
  "cloud_plaintext_allowed": false,
  "external_ai_plaintext_allowed": false,
  "rollback_required": true
}
```

## 最終原則

```text
資訊負責人負責保管，不代表可以任意使用。
AI 可以協助守門，不可以替代守門。
系統可以自動化流程，不可以自動化責任逃避。
所有受保護資訊必須可分類、可審查、可追溯、可回滾。
```

