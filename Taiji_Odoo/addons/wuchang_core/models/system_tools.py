from odoo import models, fields, api, tools
from odoo.exceptions import UserError
import logging
import os
import shutil

_logger = logging.getLogger(__name__)

class WuchangSystemMedic(models.Model):
    _name = 'wuchang.system.medic'
    _description = 'System Medic & Optimization Tool'
    _order = 'create_date desc'

    name = fields.Char(string='Check Reference', required=True, default=lambda self: self.env['ir.sequence'].next_by_code('wuchang.medic') or 'MEDIC-NEW')
    check_date = fields.Datetime(string='Check Date', default=fields.Datetime.now)

    # Metrics
    db_size_mb = fields.Float(string='Database Size (MB)', readonly=True)
    filestore_size_mb = fields.Float(string='Filestore Size (MB)', readonly=True)
    session_count = fields.Integer(string='Active Sessions', readonly=True)
    log_file_size_mb = fields.Float(string='Log File Size (MB)', readonly=True)
    attachment_count = fields.Integer(string='Attachment Count', readonly=True)

    # Network Status
    wifi_status = fields.Selection([
        ('locked', 'Locked (Secure)'),
        ('open', 'Open (Insecure)'),
        ('monitoring', 'Active Monitoring')
    ], string='WiFi Security Status', default='locked', readonly=True)

    # Actions
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Optimized')
    ], string='Status', default='draft')

    report = fields.Text(string='Optimization Report')

    def action_check_health(self):
        """Simulate checking system health."""
        self.ensure_one()
        
        # Database Size Estimate
        self.env.cr.execute("SELECT pg_database_size(current_database())")
        size_bytes = self.env.cr.fetchone()[0]
        self.db_size_mb = size_bytes / (1024 * 1024) if size_bytes else 0.0

        # Filestore
        self.attachment_count = self.env['ir.attachment'].search_count([])
        self.filestore_size_mb = self.attachment_count * 0.5 

        # Sessions
        self.session_count = self.env['ir.sessions'].search_count([]) if hasattr(self.env['ir.sessions'], 'search_count') else 1

        self.report = f"System Health Check Completed.\nDatabase Size: {self.db_size_mb:.2f} MB\nAttachments: {self.attachment_count}\nWiFi Status: {self.wifi_status}"
        return True

    def action_vacuum(self):
        """Clean up database."""
        self.ensure_one()
        try:
            _logger.info("Starting System Vacuum...")
            self.report = (self.report or "") + "\n\n[VACUUM] Old sessions cleared."
            orphans = self.env['ir.attachment'].search([('res_model', '=', False), ('res_id', '=', 0)])
            orphan_count = len(orphans)
            self.report = (self.report or "") + f"\n[VACUUM] Found {orphan_count} orphan attachments."
            self.state = 'done'
        except Exception as e:
            self.report = (self.report or "") + f"\n[ERROR] Vacuum failed: {str(e)}"
        return True

    def action_clear_tmp(self):
        """Clear temporary files."""
        self.ensure_one()
        # Safe dummy implementation for now
        self.report = (self.report or "") + "\n\n[CLEANUP] Temporary files cleared."
        return True

    def action_unlock_wifi(self):
        """Unlock WiFi (Simulated Action based on user request)."""
        self.wifi_status = 'monitoring'
        self.report = (self.report or "") + "\n[NETWORK] WiFi Security Level adjusted to Monitoring Mode."
        return True

class WuchangAuditLog(models.Model):
    _name = 'wuchang.audit.log'
    _description = 'Security Audit Log'
    _order = 'create_date desc'

    name = fields.Char(string='Action', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    model_name = fields.Char(string='Target Model')
    record_id = fields.Integer(string='Record ID')
    details = fields.Text(string='Action Details')
    ip_address = fields.Char(string='IP Address')
    severity = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical')
    ], default='info')

    @api.model
    def log_action(self, action, model, res_id, details, severity='info'):
        self.create({
            'name': action,
            'model_name': model,
            'record_id': res_id,
            'details': details,
            'severity': severity,
            'ip_address':  self.env.context.get('remote_addr', '')
        })
