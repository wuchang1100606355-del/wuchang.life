# W7TP / 小J 紅隊驗證正確記憶寫入總場

state: CANONICAL_REDTEAM_VERIFIED_MEMORY
target: TOTAL_FIELD_REDTEAM_VERIFIED_MEMORY_INTAKE
source: assistant_memory_after_redteam_correction
execute_content: false
deploy: false
service_restart: false
secret_read: false
member_plaintext_read: false
db_write: false
financial_transfer: false
legal_effect: false

## 1. 作業主線

目前主作業線只使用：

- machine: taiji01
- account: taiji_admin
- repo: /home/taiji_admin/Taiji_Hub

此線為 admin 總場所在、clean source line、總場資料權威與開發主線。

## 2. taiji_01 的正確定位

taiji_01 是使用者原本帳號，也是咖啡館場域曾經/可作為承載的帳號資訊。

但後續 active operation 不再以 OS 帳號切場。  
因已採用 8D 身分封包作為場身分，咖啡店、協會、管委會應以 8D 身分封包 / 場封包表示，而不是靠 Unix account 表示場。

taiji_01 內部資訊需保留，後續收入總場時先做 path-only manifest、分類、紅隊/總場查驗，不直接讀 secret、不直接讀會員明文、不直接混入 production。

## 3. 總場需宏觀所有帳號的 8D

總場要能宏觀所有帳號、承載層、場身分封包的 8D 狀態。

這不是表示總場要直接登入所有帳號做任意控制，而是總場要維護：

- account / carrier ref
- 8D identity packet ref
- field packet ref
- role / authority boundary
- evidence ref
- intake status
- risk / governance state

OS account 是 carrier；8D 身分封包才是治理物。

## 4. 總場小J為開發者意志

總場小J不是一般 chatbot，也不是單純 LLM agent。

總場小J是開發者意志在 W7TP 總場中的治理化表達，負責保存與調度：

- 架構決策
- 場域邊界
- 安全規則
- 8D 封包紀律
- Evidence / Redteam / HOLD / Land
- 產品與專利演化方向

邊界：

- 開發者意志不等於任意執行
- 不跳過 verifier
- 不直接讀 secret
- 不直接讀會員明文
- 不自動寫 DB / Odoo / POS
- 不自動 deploy / restart
- 不自動產生法律或金流效果

## 5. 8D 的正確語義

紅隊修正後的正確語義：

- 不是帳號，是身分封包。
- 每個 8D 身分封包形成自己的場。
- 帳號只是承載此場的作業位置。
- Odoo record 是 business/runtime carrier。
- 8D Identity Packet 是場身分與治理物。

正確語句：

> 身分封包成場。

## 6. Odoo 註冊與 8D

在 Odoo 內每個人註冊都應生成或綁定一個 8D 身分封包。

該封包決定：

- 他是誰
- 屬於哪個場
- 能看什麼
- 能讀什麼
- 能寫什麼
- 能用什麼功能
- 能否申請 taiji01 生成式傳輸
- 能否回到主權 AI 使用

不得把 Odoo 註冊等同於一般聯絡人表。Odoo 是承載層；8D 封包是身分、權限、功能、風險與治理判定層。

## 7. 三場域產品方向

目前保留三個場域方向，但不以 OS 帳號切場：

1. 咖啡店場
   - 上品聊國咖啡館重新總店
   - AI 商家服務員小J
   - 商業真實個資治理訓練場

2. 協會場
   - 新北市三重區五常社區發展協會
   - AI 組織秘書小J
   - 協會治理 / 公益意圖調度
   - 先去識別 / synthetic / dry-run

3. 管委會場
   - 常勝江山A區管理委員會
   - AI 管委會幹事小J
   - 物業腦 / 本地法律行政治理 / 公文簽核
   - 先虛擬場與流程場

## 8. 公文簽核流程

公文簽核流程是管委會場核心功能，不是一般物業 App 清單項。

它屬於：

- Odoo 內物業專利功能記錄
- 本地法律 / 行政治理流程
- 8D 身分封包授權流程
- Evidence-backed approval workflow

包含：

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

## 9. LINE WORKS + Open WebUI

LINE WORKS 是圖像化功能入口，不是權限來源。  
Open WebUI 是 LLM 作業面，不是權限來源。  
中間必須由 8D Gateway 判定。

流程：

LINE WORKS
→ 8D Gateway
→ 8D 身分封包 / 權限 / 可看 / 可讀 / 可寫
→ Open WebUI / LLM 作業
→ Local Verifier
→ LINE WORKS / Odoo / 主權 AI

禁止 LINE WORKS 直接打 unrestricted LLM execution。

## 10. 8D 需 LLM 作業

8D 是場與治理骨架。  
LLM 是 8D 作業腦 / 生成作業員。  
Verifier 是裁判。  
人與總場是最終權威。

LLM 可以：

- 語意理解
- 封包生成
- 骨架化
- delta 補全
- 文字轉 8D
- 8D 轉任務
- 雲端候選生成
- 生成式傳輸補全

LLM 不可以：

- 成為權限來源
- 直接解密
- 直接 Land
- 直接讀 secret / 會員明文
- 直接寫 Odoo / DB / POS

## 11. 加密 8D 生成式傳輸

核心句：

> 主體算力找雲端，8D 解密找我們。

雲端可做：

- 高算力候選
- skeleton / delta / packet_ref 推演
- 候選補全

本地總場負責：

- 8D 解密
- 身分還原
- 權限驗證
- 場域治理
- Evidence
- Redteam
- Land

雲端不得取得完整明文，不得成為權限來源，不得直接 Land。

## 12. Google 查表最高境界

Google / Google Workspace / Google 家庭 / Google 文件 / 試算表 / 表單 / 日曆 / Drive / Groups 是外部查表面或工作表面，不是總場權限來源。

正確語義：

- 不是 Google 幫我們。
- 是每個 8D 身分封包 / 場封包依自身場態調用外部查表面。
- 外部只看到角色查表，不知道真實人與真實行為鏈。

Google 可知道：

- role_token
- field_type
- capability_query
- policy_template_ref
- query_count

Google 不應知道：

- 真實姓名
- 誰實際做了什麼
- 誰簽了什麼
- 誰查了什麼
- 誰寫入了什麼
- 原始行為事件鏈

## 13. 團體會員限制功能服務帳戶

團體會員可設本會限制功能服務帳戶。

此帳戶只可：

- 執行預先設定告警
- 回傳無敏行為資訊統計
- 回傳聚合型使用統計
- 回傳已讀率 / 點擊率 / 流程卡點 / 功能使用次數
- 回傳狀態通知

禁止：

- 讀 secret / token / key
- 讀會員明文
- 讀原始個人行為鏈
- 跨場個資合併
- 任意 LLM 指令
- Odoo / POS / DB 自動寫入
- 金流
- 法律承諾
- deploy
- restart

## 14. 紅隊修正後廢棄事項

以下不得再當成正確架構：

- 不再用 taiji01-cafe 作正式命名。
- 不再用 taiji01-taiji_01 作主作業線。
- 不再把 taiji_01 說成另一個人。
- 不再把場域壓平成 admin 單向 projection。
- 不再用一般物業 App 功能清單替代總場物業腦。
- 不再宣稱本地小J已接雲端算力，除非實際安裝驗證。
- 不再把 VS Code Tunnel 當 Remote-SSH 成功。
- 不再叫使用者把 prompt 貼給另一個總場/小J；本系統可直接生成時應直接生成。

## 15. 總場紅線

預設禁止：

- secret_read
- member_plaintext_read
- cross_field_personal_data_merge
- cloud_as_authority
- llm_direct_land
- cloud_full_plaintext
- auto_odoo_pos_db_write
- auto_financial_transfer
- auto_legal_commitment
- deploy
- service_restart

## 16. Next Safe Action

後續從本文件與既有 total field consolidation 錨點拆出：

1. 8D_IDENTITY_PACKET_SCHEMA
2. ODOO_8D_REGISTRATION_BINDING_SPEC
3. LINE_WORKS_VISUAL_MENU_8D_GATEWAY_SPEC
4. ENCRYPTED_8D_GENERATIVE_TRANSFER_SPEC
5. GROUP_MEMBER_RESTRICTED_SERVICE_ACCOUNT_SPEC

所有拆分均須 static spec first，不得自動 deploy、restart、讀 secret、讀會員明文或寫 DB。
