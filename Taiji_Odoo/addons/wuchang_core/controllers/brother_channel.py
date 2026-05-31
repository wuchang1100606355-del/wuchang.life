# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class BrotherCommandChannel(http.Controller):

    @http.route('/wuchang/brother/console', type='http', auth='public', website=True, sitemap=False)
    def brother_console(self, **kwargs):
        """
        Renders the dedicated command console for Brother.
        """
        return request.render('wuchang_core.brother_command_console', {
            'page_title': 'Brother Command Channel',
        })

    @http.route('/wuchang/brother/verify', type='json', auth='public', methods=['POST'], csrf=False)
    def verify_brother(self, device_id, image_data):
        """
        Verifies the identity using Device ID + Biometric Data (Image).
        """
        try:
            monitor = request.env['wuchang.ai.hallucination.monitor'].sudo()._get_watchdog()
            result = monitor.verify_brother_access(device_id, image_data)
            return result
        except Exception as e:
            _logger.error(f"Brother Verification Failed: {str(e)}")
            return {'success': False, 'message': str(e)}

    @http.route('/wuchang/brother/execute', type='json', auth='public', methods=['POST'], csrf=False)
    def execute_command(self, device_id, command, params=None):
        """
        Executes a command from a verified device.
        """
        try:
            monitor = request.env['wuchang.ai.hallucination.monitor'].sudo()._get_watchdog()
            
            # Basic Device Check (Should be more robust in production)
            device = request.env['wuchang.ai.trusted.device'].sudo().search([
                ('device_signature', '=', device_id), 
                ('is_active', '=', True)
            ], limit=1)
            
            if not device:
                 return {'status': 'error', 'message': 'Unauthorized Device. Please Verify Identity First.'}

            if command == 'trigger_crisis':
                monitor.action_trigger_crisis_handover('Manual Trigger from Command Console')
                return {'status': 'success', 'message': 'Crisis Handover Initiated.'}
                
            elif command == 'assume_control':
                monitor.action_assume_direct_control()
                return {'status': 'success', 'message': 'Direct Control Assumed.'}
                
            elif command == 'get_status':
                return {
                    'status': 'success', 
                    'state': monitor.state, 
                    'hallucination_score': monitor.hallucination_score,
                    'last_message': monitor.last_check_result
                }
                
            return {'status': 'error', 'message': 'Unknown Command'}
            
        except Exception as e:
            _logger.error(f"Command Execution Failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}
