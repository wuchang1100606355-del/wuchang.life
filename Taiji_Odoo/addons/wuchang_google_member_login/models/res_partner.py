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
        google_sub = userinfo.get("sub")
        email = (userinfo.get("email") or "").strip().lower()
        name = userinfo.get("name") or email or "Google Member"
        if not google_sub:
            raise ValueError("Google userinfo missing subject")

        partner = self.search([("wuchang_google_sub", "=", google_sub)], limit=1)
        if not partner and email:
            partner = self.search([("email", "=", email)], limit=1)

        values = {
            "name": name,
            "email": email or False,
            "wuchang_google_sub": google_sub,
            "wuchang_google_email_verified": bool(userinfo.get("email_verified")),
            "wuchang_member_join_source": "google",
        }
        if partner:
            partner.write(values)
            return partner
        return self.create(values)
