from odoo import models, fields


class WuchangGroupCustomer(models.Model):
    _name = "wuchang.group.customer"
    _description = "團體客戶：商家、管委會、協會、企業"
    _rec_name = "name"

    name = fields.Char("團體客戶名稱", required=True)
    customer_type = fields.Selection([
        ("hoa", "管委會/社區"),
        ("merchant", "商家"),
        ("association", "協會/在地雲端商"),
        ("enterprise", "企業"),
        ("foundation", "基金會"),
        ("other", "其他"),
    ], string="客戶類型", default="hoa", required=True)
    contact_id = fields.Many2one("res.partner", string="聯絡主體")
    service_area = fields.Char("服務場域/社區/商圈")
    notes = fields.Text("備註")

    member_ids = fields.One2many("wuchang.member.identity", "group_customer_id", string="會員")
    field_device_ids = fields.One2many("wuchang.field.verification.device", "group_customer_id", string="第2件：場域權限驗證設備")
    governance_node_ids = fields.One2many("wuchang.trusted.governance.node", "group_customer_id", string="第3件：受託營運/治理設備")
    local_cloud_ids = fields.One2many("wuchang.local.cloud.appliance", "group_customer_id", string="第4件：在地雲端商設備")


class WuchangMemberIdentity(models.Model):
    _name = "wuchang.member.identity"
    _description = "第1件：會員權限來源身分"
    _rec_name = "display_name"

    display_name = fields.Char("無敏稱謂/會員顯示名", required=True)
    partner_id = fields.Many2one("res.partner", string="對應聯絡人")
    group_customer_id = fields.Many2one("wuchang.group.customer", string="所屬團體客戶")
    member_role = fields.Selection([
        ("resident", "住戶"),
        ("owner", "區分所有權人/業主"),
        ("consumer", "消費會員"),
        ("merchant_staff", "商家人員"),
        ("committee", "管委會委員"),
        ("property_staff", "物業人員"),
        ("operator", "協會/在地雲端商維運人員"),
    ], string="會員角色", required=True, default="resident")
    status = fields.Selection([
        ("active", "有效"),
        ("suspended", "停權"),
        ("pending", "待審核"),
    ], string="狀態", default="active")
    five_code_public_ref = fields.Char("5維碼公開參照/雜湊")
    happiness_coin_balance = fields.Float("幸福幣餘額", default=0.0)
    sovereign_device_ids = fields.One2many("wuchang.member.sovereign.device", "member_id", string="會員權限來源設備")
    notes = fields.Text("備註")


class WuchangMemberSovereignDevice(models.Model):
    _name = "wuchang.member.sovereign.device"
    _description = "第1件：會員權限來源設備"
    _rec_name = "name"

    name = fields.Char("設備名稱", required=True)
    member_id = fields.Many2one("wuchang.member.identity", string="會員", required=True)
    device_type = fields.Selection([
        ("mobile", "手機/會員App"),
        ("nfc", "NFC卡/門禁卡"),
        ("wearable", "穿戴裝置"),
        ("emergency", "緊急求救設備"),
        ("wallet", "數位憑證皮夾"),
        ("other", "其他"),
    ], string="設備類型", default="mobile", required=True)
    device_uid_hash = fields.Char("設備識別雜湊")
    can_issue_permission = fields.Boolean("可產生授權", default=True)
    can_hold_wallet = fields.Boolean("可持有幸福幣/憑證", default=True)
    last_seen = fields.Datetime("最後連線")
    notes = fields.Text("備註")


class WuchangFieldVerificationDevice(models.Model):
    _name = "wuchang.field.verification.device"
    _description = "第2件：場域權限驗證設備"
    _rec_name = "name"

    name = fields.Char("設備名稱", required=True)
    group_customer_id = fields.Many2one("wuchang.group.customer", string="團體客戶", required=True)
    domain_type = fields.Selection([
        ("merchant", "商家場域"),
        ("hoa", "管委會/社區場域"),
        ("mixed", "混合場域"),
    ], string="場域類型", default="hoa", required=True)
    device_class = fields.Selection([
        ("pos", "POS/收銀核銷"),
        ("door", "門禁"),
        ("qr", "動態QR節點"),
        ("beacon", "Beacon/NFC定位"),
        ("iot", "公設IoT"),
        ("parking", "停車設備"),
        ("elevator", "電梯/梯控"),
        ("fire", "消防/防災"),
        ("emergency", "緊急求救"),
        ("other", "其他"),
    ], string="設備分類", required=True, default="qr")
    location_code = fields.Char("方位碼/位置代碼")
    status = fields.Selection([
        ("online", "在線"),
        ("offline", "離線"),
        ("maintenance", "維護中"),
        ("retired", "停用"),
    ], string="狀態", default="online")
    governance_node_id = fields.Many2one("wuchang.trusted.governance.node", string="對應第3件治理設備")
    local_cloud_id = fields.Many2one("wuchang.local.cloud.appliance", string="對應第4件在地雲端設備")
    notes = fields.Text("備註")


class WuchangTrustedGovernanceNode(models.Model):
    _name = "wuchang.trusted.governance.node"
    _description = "第3件：受託營運/治理設備"
    _rec_name = "name"

    name = fields.Char("治理/營運節點名稱", required=True)
    group_customer_id = fields.Many2one("wuchang.group.customer", string="團體客戶", required=True)
    node_type = fields.Selection([
        ("merchant_ops", "商家受託營運設備"),
        ("hoa_gov", "管委會受託治理設備"),
        ("property_mgmt", "物業管理節點"),
        ("association_ops", "協會維運節點"),
    ], string="節點類型", required=True, default="hoa_gov")
    operator_partner_id = fields.Many2one("res.partner", string="受託操作主體")
    local_cloud_id = fields.Many2one("wuchang.local.cloud.appliance", string="上接第4件在地雲端設備")
    field_device_ids = fields.One2many("wuchang.field.verification.device", "governance_node_id", string="下接場域設備")
    trust_boundary = fields.Text("權限邊界/受託範圍")
    notes = fields.Text("備註")


class WuchangLocalCloudAppliance(models.Model):
    _name = "wuchang.local.cloud.appliance"
    _description = "第4件：團體客戶端在地雲端商設備"
    _rec_name = "name"

    name = fields.Char("在地雲端設備名稱", required=True)
    group_customer_id = fields.Many2one("wuchang.group.customer", string="部署團體客戶", required=True)
    local_cloud_provider_id = fields.Many2one("res.partner", string="在地雲端商/協會")
    deployment_site = fields.Char("部署位置")
    appliance_serial_hash = fields.Char("設備序號雜湊")
    odoo_endpoint = fields.Char("Odoo/ERP端點")
    ai_node_name = fields.Char("AI小腦/本地模型節點")
    service_scope = fields.Text("服務範圍")
    status = fields.Selection([
        ("planned", "規劃中"),
        ("active", "啟用"),
        ("maintenance", "維護中"),
        ("suspended", "暫停"),
        ("retired", "停用"),
    ], string="狀態", default="planned")
    last_audit_at = fields.Datetime("最後稽核時間")
    governance_node_ids = fields.One2many("wuchang.trusted.governance.node", "local_cloud_id", string="第3件節點")
    field_device_ids = fields.One2many("wuchang.field.verification.device", "local_cloud_id", string="第2件設備")
    notes = fields.Text("備註")


class WuchangPermissionProof(models.Model):
    _name = "wuchang.permission.proof"
    _description = "5維碼/權限證明事件"
    _rec_name = "one_time_code_hash"

    member_id = fields.Many2one("wuchang.member.identity", string="會員")
    source_device_id = fields.Many2one("wuchang.member.sovereign.device", string="第1件來源設備")
    group_customer_id = fields.Many2one("wuchang.group.customer", string="團體客戶")
    target_type = fields.Selection([
        ("merchant", "商家"),
        ("hoa", "管委會/社區"),
        ("emergency", "緊急安全場"),
    ], string="目標場域", default="hoa")
    proof_type = fields.Selection([
        ("five_code", "5維碼"),
        ("status_code", "狀態碼"),
        ("orientation_code", "方位碼"),
        ("voucher_route", "票券路由碼"),
        ("happiness_coin", "幸福幣憑證"),
        ("emergency", "緊急授權"),
    ], string="證明類型", default="five_code")
    one_time_code_hash = fields.Char("一次性授權碼雜湊", required=True)
    request_state = fields.Selection([
        ("issued", "已產生"),
        ("verified", "已驗證"),
        ("rejected", "已拒絕"),
        ("expired", "已逾期"),
    ], string="狀態", default="issued")
    expires_at = fields.Datetime("到期時間")
    verified_by_field_device_id = fields.Many2one("wuchang.field.verification.device", string="驗證設備")
    governance_node_id = fields.Many2one("wuchang.trusted.governance.node", string="受託治理設備")
    local_cloud_id = fields.Many2one("wuchang.local.cloud.appliance", string="在地雲端設備")
    amount = fields.Float("金額/幸福幣數量")
    notes = fields.Text("備註")


class WuchangHappinessLedger(models.Model):
    _name = "wuchang.happiness.ledger"
    _description = "幸福幣/管理費折抵帳"
    _rec_name = "memo"

    member_id = fields.Many2one("wuchang.member.identity", string="會員")
    group_customer_id = fields.Many2one("wuchang.group.customer", string="團體客戶")
    ledger_type = fields.Selection([
        ("earn", "取得"),
        ("spend", "使用"),
        ("fee_offset", "管理費折抵"),
        ("voucher", "商家票券核銷"),
        ("reversal", "沖正"),
    ], string="帳務類型", required=True, default="earn")
    amount = fields.Float("數量", required=True)
    related_proof_id = fields.Many2one("wuchang.permission.proof", string="關聯權限證明")
    state = fields.Selection([
        ("draft", "草稿"),
        ("posted", "已入帳"),
        ("reversed", "已沖正"),
    ], string="狀態", default="draft")
    memo = fields.Char("摘要")
    notes = fields.Text("備註")
