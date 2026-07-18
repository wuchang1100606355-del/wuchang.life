from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    wuchang_google_sub = fields.Char("Google Subject", index=True, copy=False)
    wuchang_google_email_verified = fields.Boolean("Google Email Verified", copy=False)
    wuchang_member_join_source = fields.Selection(
        [
            ("manual", "Manual"),
            ("google", "Google One-Click"),
            ("line", "LINE"),
        ],
        string="WuChang Join Source",
        default="manual",
        copy=False,
    )

    def _wuchang_get_or_create_google_member(self, userinfo):
        """Backward-compatible lookup that never creates or email-merges."""
        google_sub = userinfo.get("sub")
        if not google_sub:
            raise ValueError("Google userinfo missing subject")
        return self.search([("wuchang_google_sub", "=", google_sub)], limit=1)
