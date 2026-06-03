# W7TP-009 聊國咖啡公司 / POS 主體身分補丁

狀態：PLANONLY / DESIGN PATCH ONLY

## A. 外部友軍贊助公司

- company_name=上品食品行
- tax_id=34778660
- responsible_person=江政隆
- pos_name=上品聊國咖啡館 重新總店
- address=新北市三重區重新路三段204號1樓
- company_boundary_type=external_friendly_sponsor
- community_jurisdiction=false
- inside_wuchang_community=false
- accounting_scope=external_sponsor_company_account
- capital_gain=true
- public_interest_support=true
- support_direction=one_way_to_association_infrastructure

## B. 社區 / 協會公益基金池主體

- company_name=新北市三重區五常社區發展協會
- tax_id=同協會統編
- responsible_person=江政隆（協會派任）
- pos_name=上品聊國咖啡館 仁義分店
- company_boundary_type=community_industry_subsidiary
- community_jurisdiction=true
- accounting_scope=community_digital_development_fund_pool
- personal_capital_gain=false
- fund_nature=五常社區數位發展基金
- renyi_store_staff_caregiver_qualified=true

## C. 外送合作商家示範 POS

- pos_name=外送合作商家示範 POS
- company_boundary_type=delivery_partner_demo
- accounting_scope=demo_partner_account
- purpose=delivery_partner_template
- cross_company_accounting_mix=false

## Hardwall

- 上品食品行 / 重新總店 不等於 五常社區發展協會 / 仁義分店。
- 協會統編待填，不得用 34778660 代替協會統編。
- 重新總店帳務不得混入協會基金池。
- 仁義分店公益基金池不得混入重新總店營利帳。
- 三 POS 必須 company_id / branch_id / accounting_scope / pos_scope 分離。
- raw_pii_to_cloud=false
- odoo_write=false
- db_connect=false
- plan_only=true
