# 財務會計審核包 Runtime 政策 v0.1

本政策將 0 EPS、ESG、基金池、幸福幣、商家票券額度、勞務補償與智慧貢獻，全部收斂為「審核包」而非自動財務執行。

## 定位

- AI 可以建立非敏摘要、風險判斷、審核包與公開科目摘要。
- AI 不可以核准正式會計、付款、退款、調帳、轉帳、代幣金融化或 Odoo 會計寫入。
- 公益帳戶公開只允許科目與摘要；明細、憑證、商業機密、會員明文不可公開。
- 幸福幣與商家票券額度在正式審核前只能是社區治理設計單位或草稿，不得宣稱法幣、投資品或保證收益。

## 分級

- L1: 公益帳戶科目/摘要公開，且不含明細與憑證。
- L2: 0 EPS 分配、基金池留存、幸福幣/票券額度、勞務與智慧貢獻，進入會計師與本人審核佇列。
- L3: 付款、退款、公益資產私人化、物理刪帳、明文公開、secret/credential、AI 自動正式會計核准。

## 不可變規則

- `payment_allowed=false`
- `odoo_mutation_allowed=false`
- `accounting_approved=false`
- `physical_delete_allowed=false`
- `public detail visible=false`
- `voucher visible=false`

## 生效檔案

- runtime_adapters/finance_accounting_review_policy.py
- schemas/finance_accounting_review_packet.schema.json
- tests/test_finance_accounting_review_policy.py
