# -*- coding: utf-8 -*-
from odoo import fields, models


class PM3MemoryIndex(models.Model):
    _name = 'pm3.memory.index'
    _description = 'PM3 Realtime Memory Index'
    _order = 'last_seen_at desc, id desc'
    _rec_name = 'name'

    name = fields.Char(required=True, index=True)
    node_code = fields.Char(required=True, default='MSI', index=True)

    vault_path = fields.Char(required=True, index=True)
    vault_rel_path = fields.Char(required=True, index=True)
    vault_section = fields.Char(index=True)

    five_d_code = fields.Char(string='Five-Dimensional Code', index=True)
    five_d_source = fields.Selection([
        ('explicit', 'Explicit'),
        ('projection', 'Projection'),
        ('missing', 'Missing'),
    ], default='projection', index=True)

    payload_kind = fields.Selection([
        ('file_index', 'File Index'),
        ('runtime', 'Runtime'),
        ('governance', 'Governance'),
        ('metric', 'Metric'),
        ('deadbox', 'Deadbox'),
        ('evidence', 'Evidence'),
        ('template', 'Template'),
        ('plaintext_state', 'Plaintext State'),
        ('vector_state', 'Vector State'),
        ('fixed_vector_state', 'Fixed Vector State'),
        ('behavior_vector', 'Behavior Vector'),
        ('dashboard_state', 'Dashboard State'),
        ('other', 'Other'),
    ], default='file_index', index=True)

    payload_summary = fields.Text()

    plaintext_enabled = fields.Boolean(default=True, index=True)
    plaintext_body = fields.Text(string='Plaintext Body')
    plaintext_excerpt = fields.Text(string='Plaintext Excerpt')
    plaintext_size = fields.Integer(string='Plaintext Size')

    vector_enabled = fields.Boolean(default=True, index=True)
    vector_algorithm = fields.Char(default='pm3_hash_vector_v1')
    vector_dim = fields.Integer(default=64)
    vector_state_json = fields.Text(string='Vector State JSON')
    vector_hash = fields.Char(index=True)
    vector_updated_at = fields.Datetime(index=True)

    change_detected = fields.Boolean(default=False, index=True)
    change_state = fields.Selection([
        ('new', 'New'),
        ('changed', 'Changed'),
        ('unchanged', 'Unchanged'),
        ('sensitive_blocked', 'Sensitive Blocked'),
    ], default='unchanged', index=True)

    sensitive_scan_status = fields.Selection([
        ('unknown', 'Unknown'),
        ('clear', 'Clear'),
        ('redacted', 'Redacted'),
        ('suspect', 'Suspect'),
        ('blocked', 'Blocked'),
    ], default='unknown', index=True)

    sensitive_flags = fields.Text()

    fixed_vector_window = fields.Boolean(default=False, index=True)
    fixed_vector_state_json = fields.Text(string='Fixed Vector State JSON')
    fixed_vector_hash = fields.Char(index=True)
    fixed_vector_locked_at = fields.Datetime(index=True)
    fixed_last_content_sha256 = fields.Char(index=True)
    fixed_vector_reason = fields.Text()

    behavior_vector_db = fields.Boolean(default=False, index=True)
    behavior_event_type = fields.Selection([
        ('runtime', 'Runtime'),
        ('sync', 'Sync'),
        ('odoo', 'Odoo'),
        ('member', 'Member'),
        ('security', 'Security'),
        ('policy', 'Policy'),
        ('governance', 'Governance'),
        ('vector', 'Vector'),
        ('memory', 'Memory'),
        ('file_change', 'File Change'),
        ('unknown', 'Unknown'),
    ], default='unknown', index=True)
    behavior_subject_code = fields.Char(index=True)
    behavior_action_code = fields.Char(index=True)
    behavior_metric_key = fields.Char(index=True)
    behavior_vector_score = fields.Float(index=True)
    behavior_state_json = fields.Text(string='Behavior State JSON')
    behavior_recorded_at = fields.Datetime(index=True)

    desensitized_dashboard = fields.Boolean(default=False, index=True)
    dashboard_title = fields.Char(index=True)
    dashboard_category = fields.Selection([
        ('runtime', 'Runtime'),
        ('sync', 'Sync'),
        ('governance', 'Governance'),
        ('security', 'Security'),
        ('member', 'Member'),
        ('memory', 'Memory'),
        ('vector', 'Vector'),
        ('system', 'System'),
        ('other', 'Other'),
    ], default='other', index=True)
    dashboard_safe_text = fields.Text(string='Desensitized Dashboard Text')
    dashboard_status = fields.Selection([
        ('ok', 'OK'),
        ('changed', 'Changed'),
        ('watch', 'Watch'),
        ('blocked', 'Blocked'),
    ], default='ok', index=True)
    dashboard_updated_at = fields.Datetime(index=True)

    taiji_route_source = fields.Char(index=True)
    taiji_signature_status = fields.Selection([
        ('unknown', 'Unknown'),
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
    ], default='unknown', index=True)
    source_node = fields.Char(index=True)
    request_id = fields.Char(index=True)
    jwt_subject = fields.Char(index=True)
    jwt_scope = fields.Char(index=True)
    route_trace_hash = fields.Char(index=True)

    content_sha256 = fields.Char(required=True, index=True)
    file_ext = fields.Char(index=True)
    file_size = fields.Integer()

    source_mtime = fields.Datetime(index=True)
    last_seen_at = fields.Datetime(index=True)

    sync_state = fields.Selection([
        ('active', 'Active'),
        ('missing_local', 'Missing Local'),
        ('sealed', 'Sealed'),
    ], default='active', index=True)

    access_level = fields.Selection([
        ('plaintext', 'Plaintext'),
        ('internal', 'Internal'),
        ('index_only', 'Index Only'),
        ('sealed', 'Sealed'),
    ], default='plaintext', index=True)

    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'pm3_memory_index_node_path_unique',
            'unique(node_code, vault_rel_path)',
            'Memory index path must be unique per node.'
        ),
    ]
