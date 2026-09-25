from odoo import fields, models

from ..services.oauth_config import (
    build_callback_uri,
    callback_uri_state,
    login_health_state,
    public_base_url_from_callback,
    public_base_url_state,
)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    google_member_provider_state = fields.Char(
        string="Provider 狀態", compute="_compute_google_member_status"
    )
    google_member_provider_active_state = fields.Char(
        string="Provider 啟用狀態", compute="_compute_google_member_status"
    )
    google_member_client_id_state = fields.Char(
        string="Client ID", compute="_compute_google_member_status"
    )
    google_member_client_secret_state = fields.Char(
        string="Secret", compute="_compute_google_member_status"
    )
    google_member_callback_uri = fields.Char(
        string="Callback URI", compute="_compute_google_member_status"
    )
    google_member_callback_uri_state = fields.Char(
        string="Callback URI 狀態", compute="_compute_google_member_status"
    )
    google_member_public_base_url = fields.Char(
        string="Public base URL", compute="_compute_google_member_status"
    )
    google_member_public_base_url_state = fields.Char(
        string="Public base URL 狀態", compute="_compute_google_member_status"
    )
    google_member_login_health_state = fields.Char(
        string="登入健康狀態", compute="_compute_google_member_status"
    )

    def _compute_google_member_status(self):
        provider = self.env.ref("auth_oauth.provider_google", raise_if_not_found=False)
        params = self.env["ir.config_parameter"].sudo()
        explicit_redirect = params.get_param("wuchang_google_member_login.redirect_uri")
        configured_base = params.get_param("wuchang_google_member_login.base_url")
        web_base = params.get_param("web.base.url")
        callback_uri = build_callback_uri(
            explicit_redirect_uri=explicit_redirect,
            configured_base_url=configured_base,
            web_base_url=web_base,
        )
        public_base_url = (
            configured_base
            or public_base_url_from_callback(explicit_redirect)
            or web_base
            or ""
        )
        provider_exists = bool(provider)
        provider_active = bool(provider and provider.enabled)
        client_id_present = bool(provider and provider.client_id)
        client_secret_present = bool(
            params.get_param("wuchang_google_member_login.client_secret")
        )
        health_state = login_health_state(
            provider_exists,
            provider_active,
            client_id_present,
            client_secret_present,
            public_base_url,
            callback_uri,
        )
        for record in self:
            record.google_member_provider_state = "PRESENT" if provider_exists else "MISSING"
            record.google_member_provider_active_state = (
                "PRESENT" if provider_active else "INACTIVE"
            )
            record.google_member_client_id_state = (
                "PRESENT" if client_id_present else "MISSING"
            )
            record.google_member_client_secret_state = (
                "PRESENT" if client_secret_present else "MISSING"
            )
            record.google_member_callback_uri = callback_uri or "MISSING"
            record.google_member_callback_uri_state = callback_uri_state(callback_uri)
            record.google_member_public_base_url = public_base_url or "MISSING"
            record.google_member_public_base_url_state = public_base_url_state(public_base_url)
            record.google_member_login_health_state = health_state
