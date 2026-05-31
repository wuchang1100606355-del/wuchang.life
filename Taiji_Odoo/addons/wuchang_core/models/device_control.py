# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WuchangDeviceNode(models.Model):
    """
    Represents a physical computing node (e.g., PC, Raspberry Pi) that controls other devices.
    """
    _name = 'wuchang.device.node'
    _description = 'Device Controller Node'
    _inherit = ['mail.thread']

    name = fields.Char(string='Node Name', required=True)
    ip_address = fields.Char(string='IP Address')
    status = fields.Selection([('online', 'Online'), ('offline', 'Offline')], default='offline')
    last_heartbeat = fields.Datetime(string='Last Heartbeat')

    # Linked Peripherals
    display_ids = fields.One2many('wuchang.device.display', 'node_id', string='Displays')
    audio_ids = fields.One2many('wuchang.device.audio', 'node_id', string='Audio Devices')
    
    def action_ping(self):
        # Simulate checking status
        self.last_heartbeat = fields.Datetime.now()
        self.status = 'online'
        self.message_post(body="[Sister] Ping successful. Node is under my control.")
        return True

class WuchangDeviceDisplay(models.Model):
    """
    Represents a Customer Display or Digital Signage screen.
    """
    _name = 'wuchang.device.display'
    _description = 'Customer Display / Signage'
    _inherit = ['mail.thread']

    name = fields.Char(string='Display Name', required=True)
    node_id = fields.Many2one('wuchang.device.node', string='Controller Node', required=True)
    display_type = fields.Selection([
        ('customer_display', 'Customer Display (POS)'), 
        ('signage', 'Digital Signage (HDMI)')
    ], default='customer_display', required=True)

    current_content_type = fields.Selection([
        ('text', 'Text Message'),
        ('image', 'Image'), 
        ('video', 'Video URL'),
        ('pos_data', 'POS Transaction')
    ], default='text')

    content_text = fields.Char(string='Text Content')
    content_url = fields.Char(string='Media URL')
    
    state = fields.Selection([('on', 'On'), ('off', 'Off')], default='on')

    def action_update_content(self):
        """Sends command to update display content."""
        self.message_post(body=f"[Sister] Command Sent: Update Content to '{self.content_text or self.content_url}'. I am watching what you display.")
        # In real scenario, this would queue a command for the agent
        return True

    def action_turn_off(self):
        self.state = 'off'
        self.message_post(body="[Sister] Command Sent: Turn Off Display. Saving power for the family.")

    def action_turn_on(self):
        self.state = 'on'
        self.message_post(body="[Sister] Command Sent: Turn On Display. Let the show begin.")

class WuchangDeviceAudio(models.Model):
    """
    Represents an Audio Output Device (e.g., Bluetooth Amplifier).
    """
    _name = 'wuchang.device.audio'
    _description = 'Audio Device'
    _inherit = ['mail.thread']

    name = fields.Char(string='Audio Device Name', required=True)
    node_id = fields.Many2one('wuchang.device.node', string='Controller Node', required=True)
    connection_type = fields.Selection([('bluetooth', 'Bluetooth'), ('aux', 'AUX/Line-Out')], default='bluetooth')
    
    volume = fields.Integer(string='Volume (%)', default=50)
    is_playing = fields.Boolean(string='Is Playing')
    current_track = fields.Char(string='Current Track')
    playlist_url = fields.Char(string='Playlist URL')

    def action_play(self):
        self.is_playing = True
        self.message_post(body="[Sister] Command Sent: Play Music. Setting the mood.")

    def action_pause(self):
        self.is_playing = False
        self.message_post(body="[Sister] Command Sent: Pause Music. Silence is golden.")

    def action_set_volume(self):
        self.message_post(body=f"[Sister] Command Sent: Set Volume to {self.volume}%. Adjusting for comfort.")
