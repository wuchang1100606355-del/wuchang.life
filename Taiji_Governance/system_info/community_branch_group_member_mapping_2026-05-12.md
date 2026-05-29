# 社區分公司與團體會員治理映射

日期：2026-05-12  
狀態：ACTIVE_GOVERNANCE_MAPPING_ONLY  
注意：本文件不建立會員名冊、不含會員明文、不直接修改 Odoo production。

## 映射原則

本會以新北市三重區五常社區發展協會作為 Odoo 主公司與公益治理主體。

團體會員與分公司皆須開立獨立會計帳冊，並只能透過不可逆「總類科目」與「總數字」映射彙入本會總量治理資料，不得混帳。

總幹事屬本會治理與執行職務，不等同一般會員權益窗口。商家團體會員與物業/管委會團體會員也不得混同；兩者服務資料、權限、帳冊與 audit 分窗必須分離。

可讀營業摘要屬商業機密，不得作為一般總資料庫內容、雲端唯讀內容或 AI 可自由讀取內容。單店層級只做營業總額紀錄。

社區總量市場層可做品類總量與總金額統計。例如仁義商圈早餐業市場集中型態中，單店只記「今日營業總額」，而全社區可統計「漢堡總銷量」與「漢堡總金額」。此統計不得反推任何單店品項明細或營業結構。

人口統計層只可保存不可識別分布。本會不需要知道誰買了漢堡，但可知道群體比例，例如 50-60 歲占消費額度 8%、男性 65%、女性 35%。此類分布不得與單店、付款、時間、會員或裝置資料交叉到可識別個人。

時間桶市場熱度層只可保存不可識別時段總量。本會可以知道幾點或哪個時段大家生意最好，例如早餐尖峰時段或全社區某時段營業額最高；但不會知道誰在該時段買了些什麼。

公共服務需求訊號層可由本會本地治理掌握，例如幾點出現上班車潮、居民是否需要學童安全社區專車、哪個時段需要接送或交通安全服務。此類訊號屬社區治理用途，本會可見；但雲端不可見明細，只能接收無敏總量指標、hash、事件代號、匿名狀態或 audit reference。

會員入會時之必要明文資料採物理保管與人類審查流程。會員取得之五維碼只代表會員權益、資格分窗、服務窗口與治理狀態，不作個資紀錄；個資明文原則上保存在會員設備、會員持有文件或本會物理封存流程，不進入雲端與 AI runtime。

會員 AI 端可依本會組織政策調用白名單五維碼功能，例如本人狀態查詢、社區服務申請、論壇註冊 token、Odoo 信箱申請 manifest 與 audit receipt 查詢。白名單外功能不得調用；Google Admin SDK、Gmail API、Odoo production write、付款、secret/token 存取均不得由會員 AI 端直接執行。

## 組織與會員映射

| 名稱 | 類型 | 會員/組織角色 | 帳冊規則 | 主要職能 |
| --- | --- | --- | --- | --- |
| 聊國咖啡館重新店 / 上品食品行 | 社區團體贊助會員 / 開發商協力廠商 / 技術轉移者 | group_supporting_member、developer_vendor、technology_transferor | 獨立帳冊；單店只記營業總額 | 協助主權 AI 商業用 POS 系統、技術支援、協助管理自然人贊助會員 |
| 聊國咖啡館仁義店 | 分公司 / 社區產業基金本體店 | branch_company / community_industry_fund_body | 獨立帳冊；該店會計帳即為五常社區數位發展基金本體；單店只記營業總額 | 可複製重新店菜單；社區產業場景、POS 服務、基金池營運 |
| 物業管理雲 | 分公司 | branch_company_for_group_members | 獨立帳冊；只映射總類科目與總數字 | 專收團體會員，承接管委會、物業設備、AI 管委會服務 |
| 商業協力雲 | 分公司 | branch_company_for_group_members | 獨立帳冊；只映射總類科目與總數字 | 專收團體會員，承接商家、協力廠商、社區產業服務 |

## 自然人贊助會員協助管理

聊國咖啡館重新總店可協助及管理其他自然人贊助會員之服務流程，但不得因此取得自然人會員明文資料之無限制存取權。

允許：

- 服務流程協助。
- 非敏狀態查詢。
- 人類確認後的服務紀錄。
- 經 Gateway / Audit 的最小必要資料處理。

禁止：

- 將自然人會員完整個資交由商家或分公司自由使用。
- 將自然人贊助會員資料混入團體會員帳冊。
- 將分公司帳冊明細混入本會公益總帳明細。
- 將單店營業摘要、品項明細、交易細節或商業機密映射為可讀資料。
- 將可讀營業摘要放入組織唯讀雲端。
- 以社區品類總量資料反推單店銷售結構。
- 以人口統計分布反推個別購買者或個別會員行為。
- 以時間桶市場熱度反推個別購買者、個別會員行為或單店交易細目。
- 將學童安全社區專車、上班車潮或居民服務需求中的個人路徑、兒童資訊、家庭資訊送往雲端。
- 將本會本地治理可見資料錯誤標示為雲端可見資料。
- 將會員五維碼設計成可逆個資索引，或以五維碼反查會員設備中的明文個資。
- 會員 AI 端以五維碼繞過本會組織政策白名單、Gateway、Five Metric Gate 或 audit。
- AI 自動決定會員權益、會費、付款、核銷或正式會計結果。
- 將聊國咖啡館仁義店之社區產業基金本體帳冊轉為私人資本利得或私人分配。

## 聊國咖啡館仁義店社區產業基金定位

聊國咖啡館仁義店可複製聊國咖啡館重新店菜單，用於本會設計之社區產業運作。

其制度定位如下：

- 屬於本會社區產業設計下之分公司/社區產業節點。
- 無資本利得分配目的。
- 該店本身之會計帳即為「五常社區數位發展基金」本體帳冊。
- 菜單、POS 流程、設備與營運模型可承接重新店技術轉移。
- 營運結果只可依公益、社區產業永續、系統維運與本會治理決議使用。
- 不得因複製重新店菜單而混同重新店商業帳冊、上品食品行帳冊或本會公益總帳明細。

## Odoo Representation

```yaml
odoo_representation:
  main_company:
    name: 新北市三重區五常社區發展協會
    role: association_main_company
    accounting: public_interest_main_ledger

  group_supporting_member:
    name: 聊國咖啡館重新店 / 上品食品行
    roles:
      - group_supporting_member
      - developer_vendor
      - cooperation_contractor
      - technology_transferor
    accounting: independent_ledger_gross_revenue_total_only
    assists:
      - natural_person_supporting_member_service_management

  branch_companies:
    - name: 聊國咖啡館仁義店
      role:
        - branch_company
        - community_industry_fund_body
      menu_source: 聊國咖啡館重新店
      menu_replication_allowed: true
      capital_gain_distribution: forbidden
      accounting: wuchang_community_digital_development_fund_body_ledger
    - name: 物業管理雲
      role: branch_company_for_group_members
      accepts_member_class:
        - group_member
      accounting: independent_ledger_category_total_number_only
    - name: 商業協力雲
      role: branch_company_for_group_members
      accepts_member_class:
        - group_member
      accounting: independent_ledger_category_total_number_only
```

## Five-Metric Code

```yaml
intent: community_branch_group_member_mapping
resource: organization_role_metadata_no_member_plaintext
time: development_period_governance_mapping
authority: association_bylaw_and_owner_confirmed_mapping
topology: odoo_main_company_branch_group_member_separation
```
