# W7TP / 小J 總場設計收斂：8D 身分封包成場架構

state: CANONICAL_DESIGN_NOTE
target: TOTAL_FIELD_DESIGN_CONSOLIDATION_8D_IDENTITY_PACKET_FIELD_ARCHITECTURE
execute_content: false
deploy: false
service_restart: false
secret_read: false
member_plaintext_read: false
db_write: false
financial_transfer: false
legal_effect: false

## 1. 核心定義

W7TP / 小J 的核心不是一般 AI agent、不是一般物業 App、不是一般 LINE Bot、不是一般 Odoo 權限表。

核心為：

> Odoo 登記人，8D 身分封包成場；LINE WORKS 作圖像入口，Open WebUI 作 LLM 作業面，Google 作外部查表面，taiji01 作生成式傳輸與高算力候選，本地總場負責 8D 解密、身分還原、權限驗證、Evidence、Redteam 與 Land，最後回到主權 AI 使用。

## 2. 8D 不是帳號，是身分封包

- 8D 不是帳號。
- 8D 是身分封包。
- 每個 8D 身分封包形成自己的場。
- OS / Unix 帳號只是 runtime carrier / operator account / host context。
- Odoo 註冊資料只是業務承載層。
- 8D 身分封包才決定此人在此場能看、讀、寫、用什麼功能。

正確語句：

> 身分封包成場。帳號只是承載此場的作業位置。

## 3. W7TP Root Skeleton Canonical

W7TP Root Skeleton 採用新版 canonical tree：

- Total Field Root
  - Intent Field
  - State Field
  - Coordinate Field
  - Evidence Field
  - Execution Field

- Canonical Transformation Chain
  - State → Coordinate → Hash → Packet

- Transmission Packet Layer
  - Packet Ref
  - Manifest Index
  - Delta
  - Hash
  - D8 Envelope
    - nonce
    - counter
    - TTL
    - HMAC / seal
    - replay guard

- 8D Governance Tensor
  - Identity
  - Intent
  - Authority
  - Space / Topology / Relation Context
  - Resource
  - Time
  - Risk
  - Governance

- Execution Lifecycle
  - Sandbox
  - Validate
  - Verifier
  - Evidence Ledger
  - Redteam Hold / Dead Letter
  - Land

- Version Boundary
  - Public Architecture: redacted / no dictionary
  - Patent Architecture: implementable but not full trade secret
  - Internal Runtime Architecture: access-controlled full governance map

## 4. Odoo 內每個註冊人都有 8D 身分封包

Odoo 註冊人不是只有 res.partner / res.users。

Odoo 註冊人應生成或綁定：

- packet_ref
- identity_ref
- field_context
- authority_scope
- relation_context
- resource_scope
- time_scope / TTL
- risk_level
- governance_state
- packet_hash / audit_hash
- evidence_ref

8D 身分封包決定：

- 他是誰
- 屬於哪個場
- 能用什麼設備
- 能用什麼功能
- 能看到什麼
- 能讀取什麼
- 能寫入什麼
- 能否向 taiji01 申請生成式傳輸
- 結果能否回到主權 AI 使用
- 是否進 Evidence Ledger / Redteam Hold / Land

## 5. 場域模型

目前場域包括：

### 5.1 admin 總資料場

- 承載帳號：taiji_admin
- 路徑：/home/taiji_admin/Taiji_Hub
- 角色：總場資料權威 / 資料保管 / 權限閘門 / clean source line

### 5.2 咖啡店場

- 承載帳號：taiji_01
- 路徑：/home/taiji_01/Taiji_Hub
- 場域：上品聊國咖啡館重新總店
- 角色：AI 商家服務員小J
- 定位：商業真實個資治理訓練場 / 團體會員總場 / 技術及資金供應商場

### 5.3 協會場

- 場域：新北市三重區五常社區發展協會
- 角色：AI 組織秘書小J
- 定位：組織管理 / 公益意圖調度 / 協會治理示範場

### 5.4 管委會場

- 場域：常勝江山A區管理委員會
- 角色：AI 管委會幹事小J
- 定位：物業腦 / 管委會工作輔佐 / 本地法律行政治理示範場

## 6. 不是單向 admin projection

不得把其他場壓成被動 view。  
資料交換是：

> 8D 場 ↔ 8D 場

admin 場是權威與保管場，但不是把其他場降成單純投影視窗。

## 7. 三組產品線

- 商家管理：AI 商家服務員小J / 上品聊國咖啡館重新總店
- 組織管理：AI 組織秘書小J / 新北市三重區五常社區發展協會
- 物業管理：AI 管委會幹事小J / 常勝江山A區管理委員會

## 8. 落地順序

- 商家線先真實落地：作為商業真實個資治理訓練場。
- 協會線延後真實個資：先用去識別化 / 假資料 / synthetic case。
- 物業線先虛擬：先做流程、角色、公文、簽核、報修、公告、管理費、管委會作業模擬。

## 9. LINE WORKS + Open WebUI + 8D Gateway

- LINE WORKS：圖像化功能入口，不是權限來源。
- Open WebUI：LLM 作業介面，不是權限來源。
- 8D Gateway：身分 / 權限 / 可視 / 可讀 / 可寫 / 風險判定層。

流程：

LINE WORKS → 8D Gateway → 8D 身分封包 → Open WebUI / LLM 作業 → Local Verifier → LINE WORKS / Odoo / 主權 AI

## 10. 8D 需 LLM 作業

- 8D 是場與治理骨架。
- LLM 是 8D 的作業腦 / 生成作業員。
- Verifier 是裁判。
- 人與總場是最終權威。

LLM 可作業，但不可成為權限來源、不可直接解密、不可直接 Land。

## 11. 加密 8D 生成式傳輸與主權解密

核心原則：

> 主體算力找雲端，8D 解密找我們。

雲端可做：

- 高算力候選補全
- skeleton / delta / packet_ref 推演
- 候選生成

本地總場負責：

- 8D 解密
- 身分還原
- 權限驗證
- 場域治理
- Evidence Ledger
- Validate / Land

## 12. 封包分型

- 8D_IDENTITY_PACKET
- 8D_DATA_PROJECTION_PACKET
- 8D_CAPABILITY_CALL_PACKET
- 8D_UI_ACTION_DELTA_PACKET
- 8D_GENERATIVE_TRANSFER_REQUEST
- 8D_CANDIDATE_COMPLETION_PACKET
- 8D_BEHAVIOR_EVENT_PACKET
- 8D_LOCAL_VERDICT_PACKET

## 13. Google 多程式與查表最高境界

Google 家庭、Google Workspace、Google 文件、試算表、表單、日曆、雲端硬碟、Google 群組等是外部查表面 / 工作表面，不是總場權限來源。

正確語義：

> 每個 8D 身分封包 / 場封包，依自身場、身分、意圖、權限、風險，調用外部查表面，取得候選能力表。

查表最高境界：

> 真實人事物在本地，外部只看到角色查表。

Google 可知道 role_token / field_type / capability_query / policy_template_ref / query_count。  
Google 不應知道真實姓名、真實個人行為、誰實際簽了什麼、誰實際查了什麼、誰實際寫入什麼。

## 14. 管委會小J

Google 多程式統合的自製管委會工作輔佐 AI 小J：

- Google 多程式：工作表面
- Odoo：業務流程、物業專利功能記錄、公文簽核、流程承載
- 8D 身分封包：身分、權限、可視、讀取、寫入、簽核範圍
- 小J：管委會工作輔佐 AI / 物業腦作業員
- W7TP 總場：治理、驗證、Evidence、Redteam、Land

## 15. 公文簽核流程

公文簽核流程屬於 Odoo 內物業專利記錄與本地法律行政治理流程。

包括：

- 公文產生
- 公文編號
- 收文 / 發文
- 承辦
- 會辦
- 簽核
- 用印 / 核准
- 發送
- 歸檔
- Evidence Ledger
- Redteam / 補正 / 退回

Odoo 內應記錄 document_ref、case_ref、8d_identity_packet_ref、authority_scope、approval_chain、document_state、signature_state、evidence_hash、audit_log、redteam_hold_reason、final_land_state。

## 16. 團體會員限制功能服務帳戶

團體會員可設「本會限制功能服務帳戶」。

只可：

- 執行預先設定的告警
- 回傳無敏行為資訊統計
- 回傳聚合型使用統計
- 回傳已讀率、點擊率、流程卡點、功能使用次數
- 回傳狀態通知

禁止：

- secret / token / key
- 會員明文
- 原始個人行為鏈
- 跨場個資合併
- 任意 LLM 指令
- Odoo / POS / DB 自動寫入
- 金流
- 法律承諾
- deploy
- restart

## 17. 總場紅線

預設禁止：

- 讀 secret
- 讀會員明文
- 跨場讀個資
- 讓 Google / LINE WORKS / Open WebUI 成為權限來源
- 讓 LLM 直接 Land
- 讓雲端拿完整明文
- 自動寫 Odoo / POS / DB
- 自動金流
- 自動法律承諾
- deploy
- restart

## 18. Next Safe Action

NEXT_SAFE_ACTION=產出 8D schema 草案、Odoo binding 草案、LINE WORKS visual function menu 草案，但不得自動 deploy、restart、讀 secret、讀會員明文或寫 DB。
