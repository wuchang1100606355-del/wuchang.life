# -*- coding: utf-8 -*-
import hashlib
import hmac
import os

from odoo import api, fields, models
from odoo.exceptions import AccessDenied, UserError


class ResUsersGoogleProxy(models.Model):
    _inherit = 'res.users'

    google_proxy_enabled = fields.Boolean(
        string='Google Proxy Enabled',
        default=False,
    )
    google_proxy_role = fields.Selection([
        ('member', 'Member Proxy'),
        ('staff', 'Staff Proxy'),
        ('admin_delegate', 'Admin Delegate Proxy'),
    ], string='Google Proxy Role', default='member')
    google_proxy_scope = fields.Char(string='Google Proxy Scope')
    google_proxy_last_auth = fields.Datetime(string='Google Proxy Last Auth')
    identity_hash = fields.Char(
        string='Identity Hash (Versioned)',
        index=True,
        copy=False,
    )
    identity_hash_version = fields.Selection([
        ('hmac-sha256-v1', 'HMAC-SHA256 v1'),
    ], string='Identity Hash Version', default='hmac-sha256-v1')
    identity_namespace = fields.Char(string='Identity Namespace', index=True, copy=False)
    identity_source_type = fields.Selection([
        ('line', 'LINE'),
        ('google', 'Google'),
        ('email', 'Email'),
        ('other', 'Other'),
    ], string='Identity Source Type', index=True)
    identity_alias = fields.Char(string='Identity Alias')
    five_dim_code = fields.Char(string='Five-Dimensional Identity Code', index=True)
    line_user_hash = fields.Char(string='LINE User Hash (Legacy)', index=True, copy=False)
    xiaoj_superadmin_channel = fields.Selection([
        ('none', 'None'),
        ('active_single_seat', 'Active Single Seat'),
        ('transferred_out', 'Transferred Out'),
    ], string='XiaoJ Super Admin Channel', default='none')
    xiaoj_superadmin_registered_at = fields.Datetime(string='XiaoJ Super Admin Registered At')
    xiaoj_superadmin_transfer_note = fields.Char(string='XiaoJ Super Admin Transfer Note')

    @staticmethod
    def _get_identity_hmac_secret():
        secret = os.environ.get('PM3_IDENTITY_HMAC_SECRET')
        if not secret:
            raise AccessDenied('PM3_IDENTITY_HMAC_SECRET is required for external identity binding.')
        return secret

    @classmethod
    def _make_identity_hash(cls, namespace, source_type, raw_external_id):
        secret = cls._get_identity_hmac_secret()
        message = f"{namespace}:{source_type}:{raw_external_id}"
        return hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()

    @classmethod
    def _make_five_dim_code(cls, identity_hash):
        timestamp_component = f"{int(fields.Datetime.now().timestamp()):010d}"[-5:]
        checksum_input = f"{identity_hash[:8]}{timestamp_component}w"
        checksum = hashlib.md5(checksum_input.encode('utf-8')).hexdigest()[:4]
        return f"{identity_hash[:8]}-{timestamp_component}-w-{checksum}"

    @api.model
    def get_or_create_by_external_identity(self, namespace, source_type, raw_external_id, profile=None):
        if not namespace or not source_type or not raw_external_id:
            raise UserError('namespace, source_type, raw_external_id are required')

        identity_hash = self._make_identity_hash(namespace, source_type, raw_external_id)
        user = self.search([('identity_hash', '=', identity_hash)], limit=1)
        if user:
            return user

        profile = profile or {}
        identity_alias = profile.get('displayName') or profile.get('name') or f"{source_type}_{identity_hash[:8]}"
        login_base = identity_alias.replace(' ', '_').lower()[:20]
        login = f"{login_base}_{identity_hash[:6]}"
        domain = self.env['ir.config_parameter'].sudo().get_param('mail.catchall.domain', 'wuchang.life')
        email = profile.get('email') or f"{login}@{domain}"

        portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
        user_vals = {
            'name': identity_alias,
            'login': email if source_type == 'google' and email else login,
            'email': email,
            'identity_hash': identity_hash,
            'identity_hash_version': 'hmac-sha256-v1',
            'identity_namespace': namespace,
            'identity_source_type': source_type,
            'identity_alias': identity_alias,
            'five_dim_code': self._make_five_dim_code(identity_hash),
            'tz': 'Asia/Taipei',
        }
        if portal_group:
            user_vals['groups_id'] = [(6, 0, [portal_group.id])]
        if source_type == 'line':
            user_vals['line_user_hash'] = identity_hash
        return self.create(user_vals)

    @api.model
    def get_or_create_by_line_id(self, line_profile):
        raw_line_id = line_profile.get('userId')
        if not raw_line_id:
            raise UserError('LINE profile missing userId')
        return self.get_or_create_by_external_identity(
            namespace='wuchang.odoo',
            source_type='line',
            raw_external_id=raw_line_id,
            profile=line_profile,
        )

    @api.model
    def get_or_create_by_google_id(self, google_profile):
        raw_google_id = google_profile.get('sub')
        if not raw_google_id:
            raise UserError('Google profile missing sub')

        google_profile['displayName'] = google_profile.get('name', '')
        email = (google_profile.get('email') or '').strip().lower()
        namespace = 'wuchang.odoo'
        source_type = 'google'
        identity_hash = self._make_identity_hash(namespace, source_type, raw_google_id)

        user = self.search([('identity_hash', '=', identity_hash)], limit=1)
        if user:
            return user

        merge_target = False
        if email:
            merge_target = self.search(['|', ('email', '=', email), ('login', '=', email)], limit=1)
        if merge_target:
            values = {
                'identity_hash': identity_hash,
                'identity_hash_version': 'hmac-sha256-v1',
                'identity_namespace': namespace,
                'identity_source_type': source_type,
                'identity_alias': google_profile.get('displayName') or merge_target.name,
            }
            if not merge_target.five_dim_code:
                values['five_dim_code'] = self._make_five_dim_code(identity_hash)
            merge_target.sudo().write(values)
            return merge_target

        return self.get_or_create_by_external_identity(
            namespace=namespace,
            source_type=source_type,
            raw_external_id=raw_google_id,
            profile=google_profile,
        )

    def _active_xiaoj_superadmin_domain(self):
        return [('xiaoj_superadmin_channel', '=', 'active_single_seat')]

    @api.model
    def activate_single_seat_superadmin(self, user, transfer=False, note=''):
        """Activate the guarded super-admin channel with one active seat only."""
        if not user:
            raise UserError('target user is required')

        active = self.sudo().search(self._active_xiaoj_superadmin_domain())
        active_other = active.filtered(lambda item: item.id != user.id)
        if active_other and not transfer:
            raise AccessDenied('XiaoJ super-admin channel already has one active seat; transfer is required.')

        if active_other and transfer:
            active_other.sudo().write({
                'xiaoj_superadmin_channel': 'transferred_out',
                'xiaoj_superadmin_transfer_note': note or f'transferred to {user.login}',
            })
            group_system = self.env.ref('base.group_system', raise_if_not_found=False)
            if group_system:
                for old_user in active_other:
                    if group_system in old_user.groups_id:
                        old_user.sudo().write({'groups_id': [(3, group_system.id)]})

        group_system = self.env.ref('base.group_system', raise_if_not_found=False)
        if group_system and group_system not in user.groups_id:
            user.sudo().write({'groups_id': [(4, group_system.id)]})

        user.sudo().write({
            'xiaoj_superadmin_channel': 'active_single_seat',
            'xiaoj_superadmin_registered_at': fields.Datetime.now(),
            'xiaoj_superadmin_transfer_note': note or 'single-seat super-admin channel activated',
            'google_proxy_enabled': True,
            'google_proxy_role': 'admin_delegate',
        })
        return user

    def evaluate_google_proxy_permission(self, action, risk_level='low'):
        self.ensure_one()
        action = (action or '').strip().lower()
        risk = (risk_level or 'low').strip().lower()

        if not self.google_proxy_enabled:
            return False, 'PROXY_DISABLED', 'google proxy is disabled for this account'

        blocked_actions = {
            'admin.reset_org_policy',
            'admin.export_raw_pii',
            'admin.share_private_key',
            'admin.grant_super_admin',
        }
        if action in blocked_actions:
            return False, 'COMPLIANCE_FAILED', 'blocked high-risk administrative action'

        role = self.google_proxy_role or 'member'
        role_allow = {
            'member': {'drive.read', 'calendar.read', 'gmail.read'},
            'staff': {'drive.read', 'drive.write', 'calendar.read', 'calendar.write', 'gmail.read'},
            'admin_delegate': {
                'drive.read', 'drive.write', 'calendar.read', 'calendar.write',
                'gmail.read', 'gmail.send', 'admin.audit.read'
            },
        }
        if action and action not in role_allow.get(role, set()):
            return False, 'STATE_TRANSITION_REJECTED', f'action not allowed for proxy role: {role}'

        if risk == 'high' and role != 'admin_delegate':
            return False, 'HUMAN_REVIEW_REQUIRED', 'high risk requires admin delegate or manual review'

        return True, 'VERIFIED_OK', 'google proxy permission granted'
