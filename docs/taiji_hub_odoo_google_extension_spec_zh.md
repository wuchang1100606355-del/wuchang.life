# Taiji Hub Odoo 主場景與 Google 無敏權限管理延伸開發規格

版本：0.1  
日期：2026-05-11  
狀態：設計先行，沙盒驗證中  
分類：非敏感系統規格

## 目的

本規格定義 Taiji Hub 後續延伸開發的主系統分工：

- Odoo 作為社區、POS、設備、工單、服務流程與場景資料的主系統。
- Google Workspace 作為無敏帳戶、群組、OU、權限政策與稽核 metadata 的管理系統。
- 小J/AI 作為受限工程代理與使用者介面協作，不持有 secret、不直接掌控 production。
- Taiji Gateway / Five Metric Gate 作為所有跨系統行為的匝道與判斷層。

此分工是一份規格，不是單方控制架構。任何一方不得獨大：Odoo 不直接掌控 Google 權限，Google 不保存 Odoo 個資場景明文，AI 不直接繞過 Gateway 執行，開發者最高授權也必須被度規法則約束。

## 系統分工

| 子系統 | 主要職責 | 不得承擔 | 控制方式 |
| --- | --- | --- | --- |
| Odoo | 社區場景、POS、設備、工單、服務流程、非敏/受控業務資料 | Google 超管、服務帳戶 key、個人 Gmail 內容 | Odoo role、dbfilter、Gateway-approved client |
| Google Workspace | 無敏帳戶、群組、OU、裝置/瀏覽器政策、audit metadata | Odoo 會員明文、POS 交易明文、社區私密資料 | 最小 scope、readonly 優先、Gateway manifest |
| 小J / AI | 文件、patch、掃描、建議方案、沙盒驗證、受限瀏覽器 UI | secret 持有者、超管自動提交者、付款/部署執行者 | 認知窗降權、分窗、redacted audit |
| Taiji Gateway | 跨系統請求匝道、policy check、scope manifest | 任意放行 | Five Metric / Audit / Human Decision |
| Five Metric Gate | L0/L1/L2/L3 判斷、阻擋危害 | 替代人類決策 | policy_locked、risk table、rollback |
| 會計師精準分窗 | 基金池、補償、收入、稅務、付款審核 | AI 自行作正式會計結論 | 憑證、用途、核准、audit |

## 資料邏輯對齊

Odoo 與 Google 的對齊以無敏映射為原則：

| Odoo 場景資料 | Google 對應 | 可同步 | 不可同步 |
| --- | --- | --- | --- |
| 設備代碼 | 裝置群組/OU tag | 設備 id、角色、狀態摘要 | 管理密碼、私密網路憑證 |
| POS 角色 | 群組或 kiosk policy | role name、permission label | 交易明文、會員個資 |
| 工單/事件 | audit metadata / group routing | ticket id、severity、owner role | 住戶姓名、電話、地址全文 |
| Odoo 系統信箱 | Gmail send-only policy | 非敏通知、工單代碼 | 個人郵件本文、會員明文 |
| 權限變更 | Admin audit readonly | who/when/action metadata | secret、session token |

## 雲地自動帳戶橋接與日誌

雲端 Google Workspace 與本地 Odoo/Taiji 可以透過自動帳戶橋接，但橋接帳戶不得持有或輸出 secret，也不得成為單方控制者。

橋接規則：

- 本地 Odoo service role 只產生無敏 role/event/device code。
- Taiji Gateway bridge controller 檢查 request manifest、scope、風險與 rollback。
- Google service account proxy 只接收無敏 group/OU/policy metadata，預設不啟用 live API。
- Audit logger 只記 request id、five_dim_code、source、target、scope hash、result 與 rollback id。
- 每筆橋接都必須有日誌；無日誌即不可視為有效同步。

橋接日誌不得保存：

- service account JSON。
- OAuth token。
- Gmail 本文。
- Odoo 會員明文。
- 付款敏感資料。
- session cookie。

## 五維碼零樹狀張量 I/O

Odoo/Google 對齊建議使用五維碼零樹狀張量 I/O 作為非敏橋接格式：

- D1 node_identity。
- D2 data_sensitivity。
- D3 action_intent。
- D4 permission_window。
- D5 reversibility_public_value。

零值分支代表「沒有權限、沒有資料、沒有證據或沒有用途」，不得由 AI 自動補值。若缺少必要分支，應進入 L2 warn 或 L3 block，而不是猜測。

完整評估見 `docs/taiji_hub_five_dim_zero_tree_tensor_io_assessment_zh.md`。

## 延伸開發流程

1. Odoo 先定義場景：POS、設備、工單、社區服務或看板。
2. 抽出無敏 identity / role / permission label。
3. Google Workspace 只接收無敏帳戶/群組/OU/policy metadata。
4. 產生 Gateway request manifest。
5. Five Metric Gate 判斷 L0/L1/L2/L3。
6. 沙盒驗證資料映射與權限最小化。
7. 紅隊觀點檢查單方獨大、越權、雲端明文與公益資產私有化。
8. 修正後才以 patch、manifest、或最小權限瀏覽器 UI 落地。

## 建議方案格式

任何推給開發者的告警、設計提案或修補建議，必須包含：

```yaml
recommendation:
  title: "建議方案名稱"
  summary: "為何建議這樣做"
  affected_modules:
    - odoo
    - google_workspace
    - taiji_gateway
  impact_assessment:
    benefit: "預期效益"
    cost: "工程成本或維運成本"
    risk: "仍存在的風險"
    data_boundary: "是否碰到敏感資料"
    permission_change: "是否變更權限"
    rollback: "如何回滾"
  safe_next_action: "下一步安全動作"
```

## 方案影響評估基準

| 評估面 | 問題 |
| --- | --- |
| 公益 | 是否提升社區公益與眾利？ |
| 基金池 | 是否傷害基金池可存活？ |
| 權限 | 是否符合最小權限？ |
| 資料 | 是否避免個資、會員明文與雲端明文？ |
| Odoo | 是否維持 Odoo 主場景資料完整性？ |
| Google | 是否只使用無敏帳戶/權限 metadata？ |
| AI | 是否只是協作與 UI，不成為單方控制者？ |
| 財務 | 是否切入會計師精準分窗？ |
| 回滾 | 是否可回復到前一版本？ |
| 稽核 | 是否有 audit、SHA256 baseline 與 human decision？ |

## 單方獨大防線

- Odoo 不可直接寫 Google Admin policy。
- Google 不可持有 Odoo 會員明文。
- AI 不可持有 service account JSON、OAuth token 或超管 session。
- 開發者最高授權不可繞過度規不變式。
- 會計/財務不可由 AI 單獨定案。
- Gateway 不可在無 Five Metric 與 audit 下放行。
- 任何一方要求獨占控制，標記 `L3_metric_hazard`。
- 度規總成不可廢；五維碼、Google、Odoo、AI 或自動帳戶都不得取代度規總成。

## 第一階段可實作項

| 項目 | 交付 | 風險 |
| --- | --- | --- |
| POS inventory | POS 檔案清單、資料邊界 | L1 |
| Odoo role map | Odoo role 到無敏 Google group label | L1 |
| Odoo no-PII mailbox | send-only 草案與禁止欄位 | L2 |
| Workspace request manifest | scope、用途、資料邊界、rollback | L2 |
| Predictive alert recommendation | 每則告警含建議方案與影響評估 | L1 |
| Browser UI action manifest | 最小權限瀏覽器動作清單 | L2 |

## Odoo 接 Google for Nonprofits 信箱

延伸規格見 `docs/taiji_hub_odoo_google_nonprofit_mail_bridge_zh.md`，manifest 見 `Taiji_Governance/integrations/odoo_google_nonprofit_mail_bridge_manifest.json`。

本階段採用：

- Odoo 作主場景與通知來源。
- Google Workspace for Nonprofits 作免費非營利網域信箱與無敏權限管理。
- `smtp-relay.gmail.com` 作候選 SMTP relay。
- Odoo 信件僅可包含無個資 code、工單代號、設備代碼、audit 摘要與需登入查看的連結。
- 任何 live 設定需先由人類管理員與 Gateway/Five Metric 審核。
