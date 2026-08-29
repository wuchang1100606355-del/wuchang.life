from odoo import _, fields, models
from odoo.exceptions import UserError


STATE_LABELS = {
    "draft": "人工分配草稿",
    "captain": "隊長初核",
    "sg": "總幹事批示",
    "chairman": "理事長批示",
    "committee": "常務理事會追認",
}


class VolunteerPoint(models.Model):
    _name = "wuchang.volunteer.point"
    _description = "志工點數派發簽核"

    volunteer_id = fields.Many2one(
        "res.partner",
        string="志工姓名",
        required=True,
    )
    points = fields.Integer(string="點數", required=True)
    state = fields.Selection(
        list(STATE_LABELS.items()),
        string="簽核狀態",
        default="draft",
    )

    def _advance_state(self, expected_state, next_state):
        self.ensure_one()
        if self.state != expected_state:
            raise UserError(
                _("簽核階段順序錯誤：目前為「%s」。")
                % STATE_LABELS.get(self.state, self.state)
            )
        self.state = next_state
        return True

    def action_approve_captain(self):
        return self._advance_state("draft", "captain")

    def action_approve_sg(self):
        return self._advance_state("captain", "sg")

    def action_approve_chairman(self):
        return self._advance_state("sg", "chairman")

    def action_approve_committee(self):
        return self._advance_state("chairman", "committee")
