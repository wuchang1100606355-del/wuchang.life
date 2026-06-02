# Member Registration Design Batch 001

timestamp: 20260602_120122
head: c589c8f

created:
- W7TP_MEMBER_REGISTRATION_ARCHITECTURE_V1.yaml
- W7TP_MEMBER_REGISTRATION_FLOW_V1.yaml
- W7TP_MEMBER_REGISTRATION_PRIVACY_GATE_V1.yaml
- W7TP_MEMBER_REGISTRATION_ODOO_MODEL_SPEC_V1.yaml
- W7TP_MEMBER_REGISTRATION_API_PACKET_V1.yaml

core_result:
- 註冊流程以 provisional -> human review -> verified member 為主線。
- LINE/Google 僅作登入綁定，不等於正式會員。
- 日常系統不輸出原始個資。
- 商家只能發起會員核准聯絡，不得取得會員名單。
- Odoo 模型需分 registration、identity code、external auth、consent ledger、recovery case。
- 後續可進入 sandbox prototype，不直接 DB write。

next:
- MEMBER_REGISTRATION_SANDBOX_MODEL_PROTO
- MEMBER_REGISTRATION_ODOO_ACCESS_RULE_PROTO
- MEMBER_REGISTRATION_UI_FLOW_PROTO
