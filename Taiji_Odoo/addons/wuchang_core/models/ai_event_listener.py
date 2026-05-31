from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class AiEventListener(models.Model):
    """
    Global Event Listener hooking into mail.message to forward system events to the AI Perception Sensor.
    """
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, values_list):
        messages = super(AiEventListener, self).create(values_list)

        try:
            # Get the sensor model
            Sensor = self.env['wuchang.ai.perception.sensor']
            # Get Task Model (check if exists)
            Task = self.env['wuchang.task'] if hasattr(self.env, 'wuchang.task') else None

            for msg in messages:
                # Skip system messages or messages from the AI itself (if identifiable)
                if msg.message_type == 'notification' or msg.author_id.name == 'OdooBot' or 'AI' in msg.author_id.name:
                    continue

                # Analyze the message
                analysis = Sensor.analyze_message(msg.body, msg.author_id.name)

                if analysis['action'] == 'escalate_to_brother_crisis':
                    _logger.warning(f"[Sister Watchdog] CRISIS DETECTED: {analysis['reason']}")
                    self._create_emergency_task(msg, analysis['context_hint'])
                    # Append warning to message
                    msg.write({'body': msg.body + f"<br/><br/><strong style='color:red;'>[Sister]: ⚠️ I sense a crisis. I have notified Brother immediately. Please hold on.</strong>"})

                elif analysis['action'] == 'escalate_to_brother':
                    _logger.info(f"[Sister Watchdog] Escalating to Brother. Reason: {analysis['reason']}")
                    self._create_support_task(msg, analysis['context_hint'])
                    msg.write({'body': msg.body + f"<br/><br/><span class='text-danger'>[Sister]: This is technical. I'm calling Brother to handle it.</span>"})

                elif analysis['action'] == 'activate_sister_mode':
                    _logger.info(f"[Sister Watchdog] Activating Sister Mode. Reason: {analysis['reason']}")
                    # Logic to trigger Sister's response can be added here

        except Exception as e:
            # Don't block message creation on sensor failure
            _logger.warning(f"AI Perception Sensor Error: {e}")

        return messages

    def _create_emergency_task(self, msg, hint):
        """Creates a high priority task for the human architect."""
        try:
            admin = self.env.ref('base.user_admin')
            self.env['wuchang.task'].sudo().create({
                'name': f"🚨 EMERGENCY: Crisis Detected from {msg.author_id.name}",
                'description': f"User: {msg.author_id.name}\nMessage: {msg.body}\nContext: {hint}",
                'priority': '3', # High
                'user_ids': [(4, admin.id)],
                'category': 'resident_need'
            })
            # Send Email
            self.env['mail.mail'].sudo().create({
                'subject': f"🚨 CRISIS ALERT: {msg.author_id.name}",
                'body_html': f"<p>Crisis detected.</p><p><b>User:</b> {msg.author_id.name}</p><p><b>Content:</b> {msg.body}</p>",
                'email_to': 'o970106@gmail.com',
                'email_from': 'sister@wuchang.life',
            }).send()
        except Exception as e:
            _logger.error(f"Failed to create emergency task: {e}")

    def _create_support_task(self, msg, hint):
         """Creates a normal support task."""
         try:
            admin = self.env.ref('base.user_admin')
            self.env['wuchang.task'].sudo().create({
                'name': f"Support Request: {msg.author_id.name}",
                'description': f"User: {msg.author_id.name}\nMessage: {msg.body}\nContext: {hint}",
                'priority': '2', # Medium
                'user_ids': [(4, admin.id)],
                'category': 'resident_need'
            })
         except Exception as e:
            _logger.error(f"Failed to create support task: {e}")
