【五常智慧雲｜本會章程效力、社區發展制度補強與公開資訊業務權限條款】

一、章程效力

新北市三重區五常社區發展協會之組織章程，經會員或會員代表大會通過，並報請主管機關社會局同意備查後，具本會組織運作、會員權利義務、任務範圍、經費來源、理監事職權、會議程序、會計制度與內部治理之章程效力。

本會章程明定：

1. 本會為依人民團體法設立，非以營利為目的之社會團體。
2. 本會宗旨為促進社區發展、增進居民福利、保障社會弱勢。
3. 本會組織區域為五常、仁忠、五順三里轄區。
4. 本會任務包含建立歷史、地理、環境、人文資料、人口資料、社區資源資料、社區問題個案資料及其他與社區發展有關資料。
5. 本會得與轄區有關之機關、機構、學校、團體及村里辦公處加強協調聯繫，以爭取支援社區發展工作並維護成果。
6. 本會會員制度包含個人會員、團體會員與贊助會員。
7. 本會經費來源包含入會費、經常會費、社區生產收益、政府機關補助、捐助收入、福利服務活動收入、基金及孳息、其他收入。

二、社區發展制度補強

本會章程任務承接社區發展工作綱要之制度精神，並受現行社區發展工作要點及主管機關社區發展政策補強。

因社區發展工作綱要已於 114 年 7 月 1 日廢止，並同步由主管機關函頒社區發展工作要點，故本系統之正式表述應為：

「本會章程內容承接社區發展工作綱要之制度精神，並受現行社區發展工作要點及主管機關社區發展政策補強。」

不得僅稱「依社區發展工作綱要」而忽略其已廢止之現行法規狀態。

三、五常智慧雲之制度定位

基於本會章程效力、社區發展制度精神與現行社區發展工作要點補強，五常智慧雲可定位為：

1. 本會社區資料建立之數位化工具。
2. 本會社區資源資料整理工具。
3. 本會公益業務推廣工具。
4. 本會團體會員與個人會員治理原型。
5. 本會物業管理論壇與商業管理論壇之公開實體索引工具。
6. 本會 Odoo 公益平台架構原型與金流原型。
7. 本會 3D 空間照準、公共設施、社區人文水文地理資料治理原型。
8. 本會科技平權、低碳 AI、社區資訊人才培育與居民創新獎勵之公益數位平台原型。

四、公開資訊蒐集與公益推廣權限

本會得於章程目的、轄區範圍、特定公益目的、必要範圍、公開來源、人工審核與稽核紀錄條件下，蒐集、整理及利用轄區內公開資訊，包括：

1. 商家公開資訊。
2. 管委會公開資訊。
3. 公共設施公開資訊。
4. 物業管理公開資訊。
5. 社區產業公開資訊。
6. 團體會員或潛在團體會員公開資訊。
7. 公開負責人姓名、公開職稱與公開聯絡窗口。
8. 政府公開資料。
9. Google Maps / Google 商家檔案公開資料。
10. 官方網站、公開粉專、公開公告、公開活動資訊。

用途限於：

1. 公益業務推廣。
2. 團體會員邀請。
3. 商業管理論壇邀請。
4. 物業管理論壇邀請。
5. 公共服務通知。
6. 社會福利合作。
7. 社區資訊人才培育。
8. 科技平權服務通知。
9. 低碳 AI 公益實證邀請。
10. 社區產業協作。
11. 管委會與商家公開實體索引。
12. Odoo 平台架構原型。
13. 3D 空間照準公開點位標註。
14. Google 商家檔案公開資料對齊。
15. 人工審核與來源查證。

五、禁止用途

章程效力、社區發展制度補強與本會業務權限，不得被解釋為：

1. 可無限制蒐集個人資料。
2. 可處理非公開資料。
3. 可繞過個資法與當事人權利。
4. 可將會員明文資料提供商家或團體會員。
5. 可建立住戶監控或個人側寫。
6. 可將公開負責人資訊轉為商業名單販售。
7. 可將公開資訊直接作外部 AI 訓練。
8. 可將 Odoo 分公司視為法律公司。
9. 可將開發期原型誤稱正式營運平台。

六、Odoo 對應

Odoo 可建立：

model: wuchang.public.entity

fields:
- entity_token
- entity_type
- entity_name
- public_representative_name
- public_representative_title
- public_contact
- public_address_or_area
- source_url
- source_type
- source_public_status
- jurisdiction_match
- collection_purpose
- legal_or_bylaw_authority
- community_development_basis
- manual_review_status
- opt_out_status
- odoo_branch
- spatial_anchor
- request_id
- sha256_hash

分流：

商家公開資訊
→ Odoo 商業部分公司

管委會與物業公開資訊
→ Odoo 物管部分公司

公益服務與社會福利公開資訊
→ Odoo 社區數位發展基金分公司

系統、API、3D、碳帳本資料
→ Odoo 社區資訊管理暨開發部門

七、最終公式

Association_Bylaw_Authority = true

Community_Development_Basis =
Bylaw_Effect
⊕ Community_Development_Work_Outline_Legacy_Spirit
⊕ Current_Community_Development_Work_Points
⊕ Competent_Authority_Policy

Public_Source_Collection_By_Association(entity)=true

iff:

Association_Bylaw_Authority=true
AND Specific_Purpose_Defined=true
AND Jurisdiction_Relevant=true
AND Source_Is_Public_or_Generally_Available=true
AND Public_Interest_or_Association_Business_Relevance=true
AND Necessary_Scope=true
AND Manual_Review_Required=true
AND Odoo_Branch_Defined=true
AND Audit_Record=true
AND No_Private_Profile=true
AND No_Harm_To_Data_Subject_Rights=true

Final Principle:

本會章程經主管機關社會局同意備查後具章程效力；其任務內容承接社區發展工作綱要之制度精神，並受現行社區發展工作要點補強。此基礎足以支撐五常智慧雲作為社區資料建立、公益公開資訊蒐集、團體會員拓展、Odoo 公益金流原型、3D 空間照準、物業管理論壇、商業管理論壇與科技平權之數位治理原型。

但此權限是公益治理與權益保護之合法基礎，不是個資後門，也不是無限制商業利用或 AI 訓練授權。
