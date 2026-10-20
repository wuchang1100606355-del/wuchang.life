"""Preview selected products and enqueue the existing reviewed change requests."""

import json
from html import escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.menu_batch_governance import build_batch_preview
from ..services.menu_change_governance import MenuChangeGovernanceError, stable_sha256
from .menu_manager import RESPONSIBLE_GROUP


_PREVIEW_TOKEN = object()


class WuchangCafeMenuBatchWizard(models.TransientModel):
    _name = "wuchang.cafe.menu.batch.wizard"
    _description = "咖啡館菜單批次預覽"

    product_ids = fields.Many2many("product.template", string="選取商品", required=True)
    operation = fields.Selection([
        ("set_price", "設定相同售價"), ("set_categories", "改分類"),
        ("pause", "暫停販售"), ("archive", "封存商品"),
        ("reactivate", "重新上架"),
    ], default="pause", required=True, string="批次動作")
    price = fields.Float(string="新售價")
    category_ids = fields.Many2many("pos.category", string="新分類")
    preview_json = fields.Text(string="逐項修改前後差異", readonly=True)
    preview_html = fields.Html(string="逐項修改前後差異", compute="_compute_preview_html", sanitize=True)
    preview_sha256 = fields.Char(readonly=True)
    changed_count = fields.Integer(string="有變更商品數", readonly=True)
    submitted = fields.Boolean(readonly=True)

    _INPUT_FIELDS = {"product_ids", "operation", "price", "category_ids"}

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if set(values) - self._INPUT_FIELDS:
                raise UserError(_("預覽證據只能由系統產生。"))
        safe_values = [{**values, "preview_json": False, "preview_sha256": False,
                        "changed_count": 0, "submitted": False} for values in vals_list]
        return super().create(safe_values)

    def write(self, values):
        if self.env.context.get("wuchang_batch_preview_write") is _PREVIEW_TOKEN:
            return super().write(values)
        if set(values) - self._INPUT_FIELDS:
            raise UserError(_("預覽證據不能由操作端修改。"))
        if any(wizard.submitted for wizard in self):
            raise UserError(_("已送審的預覽不能修改；請建立新預覽。"))
        return super().write({**values, "preview_json": False,
                              "preview_sha256": False, "changed_count": 0})

    def _build_preview(self):
        self.ensure_one()
        if not self.env.user.has_group(RESPONSIBLE_GROUP):
            raise UserError(_("請使用已有菜單維護授權的同一帳號。"))
        batch = self.env["product.template"]._wuchang_responsible_batch()
        products = self.product_ids.with_context(active_test=False).exists().sorted("id")
        if len(products) != len(self.product_ids):
            raise UserError(_("選取商品已不存在，請重新選取。"))
        for product in products:
            if product.company_id and product.company_id != batch.menu_company_id:
                raise UserError(_("批次操作不能跨營運公司。"))
            if not (product.available_in_pos or product.w5c_domain == "CAFE" or product.wuchang_option_group_id):
                raise UserError(_("請只選取咖啡館菜單商品。"))
        value = self.price if self.operation == "set_price" else self.category_ids.ids
        try:
            preview = build_batch_preview(
                [product.wuchang_menu_snapshot() for product in products], self.operation, value)
        except (MenuChangeGovernanceError, ValueError) as exc:
            raise UserError(_("無法建立預覽：%s") % exc) from exc
        preview["binding"] = {"company_id": batch.menu_company_id.id,
                              "batch_id": batch.id, "actor_user_id": self.env.user.id,
                              "product_ids": products.ids}
        preview.pop("sha256")
        preview["sha256"] = stable_sha256(preview)
        return products, batch, preview

    @api.depends("preview_json")
    def _compute_preview_html(self):
        labels = {"list_price": "售價", "pos_category_ids": "分類",
                  "active": "商品啟用", "available_in_pos": "收銀台販售"}
        def display(key, value):
            if key == "pos_category_ids":
                return "、".join(self.env["pos.category"].browse(value).mapped("name")) or "無分類"
            if isinstance(value, bool):
                return "是" if value else "否"
            return str(value)
        for wizard in self:
            if not wizard.preview_json:
                wizard.preview_html = False
                continue
            rows = []
            for row in json.loads(wizard.preview_json)["rows"]:
                for key, change in row["diff"].items():
                    cells = [row["before"]["name"], labels[key],
                             display(key, change["before"]), display(key, change["after"])]
                    rows.append("<tr>" + "".join("<td>" + escape(cell) + "</td>" for cell in cells) + "</tr>")
            wizard.preview_html = '<table class="table table-striped"><thead><tr><th>商品</th><th>修改項目</th><th>修改前</th><th>修改後</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>"

    def _reopen(self):
        return {"type": "ir.actions.act_window", "res_model": self._name,
                "res_id": self.id, "view_mode": "form", "target": "new"}

    def action_preview(self):
        self.ensure_one()
        if self.submitted:
            raise UserError(_("這份預覽已送審。"))
        _, _, preview = self._build_preview()
        self.with_context(wuchang_batch_preview_write=_PREVIEW_TOKEN).write({
            "preview_json": json.dumps(preview, ensure_ascii=False, indent=2),
            "preview_sha256": preview["sha256"], "changed_count": preview["changed_count"],
        })
        return self._reopen()

    def action_submit(self):
        self.ensure_one()
        self.env.cr.execute("SELECT id FROM wuchang_cafe_menu_batch_wizard WHERE id = %s FOR UPDATE", (self.id,))
        self.invalidate_recordset()
        if self.submitted or not self.preview_sha256:
            raise UserError(_("請先產生新預覽，不能重複送審。"))
        products = self.product_ids
        if products:
            self.env.cr.execute("SELECT id FROM product_template WHERE id IN %s ORDER BY id FOR UPDATE", (tuple(products.ids),))
            products.invalidate_recordset()
        products, batch, preview = self._build_preview()
        if preview["sha256"] != self.preview_sha256:
            raise UserError(_("商品或商家授權已改變，請重新預覽；尚未修改菜單。"))
        request_model = self.env["wuchang.cafe.menu.change.request"]
        requests = request_model.browse()
        for product, row in zip(products, preview["rows"]):
            if not row["diff"]:
                continue
            proposed = {key: change["after"] for key, change in row["diff"].items()}
            values = request_model._request_values_for_proposal(proposed)
            values.update({"origin": "merchant_manager", "change_type": "update",
                           "group_batch_id": batch.id, "product_template_id": product.id,
                           "support_reason": "批次預覽 sha256:%s" % self.preview_sha256})
            requests |= request_model.create(values)
        if not requests:
            raise UserError(_("選取商品沒有差異，無需修改。"))
        requests.action_submit_for_responsible_review()
        self.with_context(wuchang_batch_preview_write=_PREVIEW_TOKEN).write({"submitted": True})
        return {"type": "ir.actions.act_window", "name": "批次菜單審核",
                "res_model": request_model._name, "view_mode": "list,form",
                "domain": [("id", "in", requests.ids)], "target": "current"}


class ProductTemplateBatchMenu(models.Model):
    _inherit = "product.template"

    def action_wuchang_menu_batch_preview(self):
        return {"type": "ir.actions.act_window", "name": "批次修改預覽",
                "res_model": "wuchang.cafe.menu.batch.wizard", "view_mode": "form",
                "target": "new", "context": {"default_product_ids": [(6, 0, self.ids)]}}
