# Data Scope Matrix

| Data scope | Owner boundary | May mix with |
| --- | --- | --- |
| private_store_data | private commercial operator | private accounting only |
| community_association_data | public-interest governance body | public-interest governance |
| community_industry_data | community industry operator | governed fund-pool records |
| pos_customer_data | POS service node | minimal Odoo/POS scope |
| odoo_operational_data | Odoo runtime | governed role scope |
| audit_data | audit runtime | governance review |
| ai_runtime_metadata | Taiji runtime | redacted tensor state |

Blocked: private store data mixed with association data without accounting review and human decision.
