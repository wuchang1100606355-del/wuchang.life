# -*- coding: utf-8 -*-
from odoo import models, fields, api
import hashlib
import random

class PrivacyMask(models.AbstractModel):
    _name = 'wuchang.privacy.mask'
    _description = 'Privacy Masking & DID Generation'

    @api.model
    def generate_did(self, raw_data):
        """
        Converts raw personal data (e.g., phone number) into a Hash DID.
        This ensures personal data stays on the edge node, and only the hash goes on-chain/central.
        """
        if not raw_data:
            return False
        
        # Simple SHA-256 hash for demonstration of DID concept
        # In production, this might involve a more complex salt or specific DID method
        hash_object = hashlib.sha256(raw_data.encode())
        return f"did:wuchang:{hash_object.hexdigest()}"

class WuchangWit(models.AbstractModel):
    _name = 'wuchang.wit'
    _description = 'Wuchang AI Personality'

    @api.model
    def get_quote(self):
        """Returns a random Wuchang Wit quote."""
        quotes = [
            "當你全身上下沒有一樣是他要的，你也不會咬他，他才不想理你！",
            "科技是用來助人的，不是用來控制人的。",
            "這就是「溫柔但有底線」的科技倫理。",
            "別讓算法決定你的善良。"
        ]
        return random.choice(quotes)

class WuchangPlatformAdmin(models.AbstractModel):
    _name = 'wuchang.platform.admin'
    _description = 'Wuchang Platform Admin Enforcer'

    @api.model
    def _pair_groups(self):
        env = self.env
        pairs = []
        def get(ref):
            return env.ref(ref, raise_if_not_found=False)
        pairs.append((get('wuchang_core.group_wuchang_volunteer_admin'), get('wuchang_core.group_wuchang_volunteer_user')))
        pairs.append((get('wuchang_core.group_wuchang_property_admin'), get('wuchang_core.group_wuchang_property_user')))
        pairs.append((get('wuchang_core.group_wuchang_business_admin'), get('wuchang_core.group_wuchang_business_user')))
        pairs.append((get('wuchang_core.group_wuchang_services_admin'), get('wuchang_core.group_wuchang_services_user')))
        return [(a, u) for (a, u) in pairs if a and u]

    @api.model
    def enforce_single_admins(self):
        User = self.env['res.users'].sudo()
        Params = self.env['ir.config_parameter'].sudo()
        def get_slot_login(key):
            return (Params.get_param('platform.admin.slot.%s' % key) or '').strip()
        slots = {
            'volunteer': get_slot_login('volunteer'),
            'property': get_slot_login('property'),
            'business': get_slot_login('business'),
            'services': get_slot_login('services'),
        }
        founder_raw = Params.get_param('founder.identity.google_accounts') or '[]'
        try:
            import json
            founders = json.loads(founder_raw)
        except Exception:
            founders = []
        for admin_group, user_group in self._pair_groups():
            admins = User.search([('groups_id', 'in', admin_group.id)])
            if len(admins) <= 1:
                continue
            # platform key by group id mapping
            key = None
            if admin_group.xml_id:
                if admin_group.xml_id.endswith('_group_wuchang_volunteer_admin'):
                    key = 'volunteer'
                elif admin_group.xml_id.endswith('_group_wuchang_property_admin'):
                    key = 'property'
                elif admin_group.xml_id.endswith('_group_wuchang_business_admin'):
                    key = 'business'
                elif admin_group.xml_id.endswith('_group_wuchang_services_admin'):
                    key = 'services'
            slot_login = slots.get(key) if key else ''
            slot_user = User.search([('login', '=', slot_login)], limit=1) if slot_login else self.env['res.users']
            prefer_founder = admins.filtered(lambda u: u.login in founders)
            prefer_system = admins.filtered(lambda u: u.has_group('base.group_system') or u.has_group('base.group_erp_manager'))
            keep = slot_user if slot_user else (prefer_founder[:1] if prefer_founder else (prefer_system[:1] if prefer_system else admins[:1]))
            demote = admins[1:]
            for u in demote:
                vals = {
                    'groups_id': [(3, admin_group.id), (4, user_group.id)]
                }
                try:
                    u.write(vals)
                except Exception:
                    pass
        return True

    @api.model
    def set_admin_slot(self, platform, login):
        platform = (platform or '').strip()
        login = (login or '').strip()
        if platform not in ('volunteer','property','business','services'):
            return {'error': 'invalid_platform'}
        Params = self.env['ir.config_parameter'].sudo()
        user = self.env.user
        accs_raw = Params.get_param('founder.identity.google_accounts') or '[]'
        try:
            import json
            accs = json.loads(accs_raw)
        except Exception:
            accs = []
        allowed_set = (user.login in accs) or user.has_group('base.group_system') or user.has_group('wuchang_core.group_wuchang_commander_xiao_j')
        if not allowed_set:
            return {'error': 'forbidden'}
        if login == '':
            allowed_revoke = (user.login in accs) or user.has_group('base.group_system')
            if not allowed_revoke:
                return {'error': 'forbidden_revoke'}
        Params.set_param('platform.admin.slot.%s' % platform, login)
        return {'ok': True}
