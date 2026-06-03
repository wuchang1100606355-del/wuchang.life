from odoo import models, fields


class WuchangKnowledgeSource(models.Model):
    _name = "wuchang.knowledge.source"
    _description = "五常知識庫同步來源"
    _rec_name = "name"

    name = fields.Char("來源名稱", required=True)
    root_path = fields.Char("容器內來源路徑", required=True)
    host_path_note = fields.Char("主機來源路徑")
    source_type = fields.Selection([
        ("local_runtime", "本機Runtime"),
        ("odoo", "Odoo"),
        ("drive", "雲端硬碟"),
        ("manual", "手動"),
    ], string="來源類型", default="local_runtime", required=True)
    sync_state = fields.Selection([
        ("draft", "草稿"),
        ("active", "啟用"),
        ("paused", "暫停"),
        ("error", "錯誤"),
    ], string="同步狀態", default="active")
    last_sync_at = fields.Datetime("最後同步時間")
    item_count = fields.Integer("檔案數")
    safety_policy = fields.Text("安全政策", default="唯讀同步；跳過 .env、key、pem、token、password、credentials、private、secret、資料庫、二進位與大型檔；同步內容僅保存遮罩後摘要。")
    notes = fields.Text("備註")


class WuchangKnowledgeItem(models.Model):
    _name = "wuchang.knowledge.item"
    _description = "五常知識庫同步項目"
    _rec_name = "name"

    source_id = fields.Many2one("wuchang.knowledge.source", string="來源", required=True, ondelete="cascade")
    name = fields.Char("檔名", required=True)
    relative_path = fields.Char("相對路徑", index=True)
    absolute_path = fields.Char("容器內路徑")
    file_ext = fields.Char("副檔名")
    size_bytes = fields.Integer("大小 bytes")
    modified_at = fields.Datetime("修改時間")
    sha256 = fields.Char("SHA256")
    sync_status = fields.Selection([
        ("indexed", "已索引"),
        ("skipped", "已跳過"),
        ("error", "錯誤"),
    ], string="同步狀態", default="indexed")
    skipped_reason = fields.Char("跳過原因")
    content_excerpt = fields.Text("安全摘要")
    privacy_level = fields.Selection([
        ("public", "公開/低敏"),
        ("internal", "內部"),
        ("sensitive_masked", "敏感已遮罩"),
        ("skipped_secret", "機密已跳過"),
    ], string="隱私等級", default="internal")
    notes = fields.Text("備註")
