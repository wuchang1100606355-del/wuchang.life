from odoo import models, fields, api
import logging
import re

_logger = logging.getLogger(__name__)

class AiPerceptionSensor(models.AbstractModel):
    """
    AI Perception Sensor (感知監測器)
    Analyzes user messages for sentiment and keywords to trigger tiered support escalation.
    Tier 1: Local AI (Default)
    Tier 2: Sister Meimei (Little J Service Mode)
    Tier 3: Brother (Architect Escalation)
    Tier 4: Brother - Human Crisis (Violence, Psychology, Deep Emotion)
    """
    _name = 'wuchang.ai.perception.sensor'
    _description = 'AI Perception & Escalation Sensor'

    @api.model
    def analyze_message(self, message_body, author_name='User'):
        """
        Analyzes the message and returns a suggested action or state.
        """
        if not message_body:
            return {'action': 'none', 'reason': 'empty_message'}

        message_lower = message_body.lower()

        # --- Tier 4: Human Crisis Escalation (Strictly for Brother) ---
        # 心理問題 (Psychology), 暴力 (Violence), 感情 (Deep Emotion), 意外 (Accidents)
        crisis_keywords = [
            'suicide', 'kill', 'hurt', 'die', 'blood', 'abuse', 'police', 'danger',
            'depression', 'anxiety', 'breakup', 'divorce', 'affair', 'love', 'hate',
            '自殺', '殺', '死', '血', '暴力', '打人', '救命', '報警', '危險', '意外', '受傷',
            '憂鬱', '焦慮', '想不開', '痛苦', '心理醫生', '諮商',
            '分手', '外遇', '離婚', '愛上', '恨', '感情', '心情不好'
        ]
        if any(k in message_lower for k in crisis_keywords):
            return {
                'action': 'escalate_to_brother_crisis',
                'reason': 'human_crisis_detected',
                'context_hint': f"CRITICAL: User {author_name} is discussing sensitive human issues (Psychology/Violence/Emotion). AI MUST STOP. Human intervention required."
            }
        
        # --- Tier 3 Escalation Triggers (To Brother - Technical/Admin) ---
        brother_keywords = ['manager', 'boss', 'human', 'error', 'bug', 'stuck', 'fail', 'broken', '哥哥', '老闆', '經理', '真人', '壞掉', '卡住', '報錯']
        if any(k in message_lower for k in brother_keywords):
            return {
                'action': 'escalate_to_brother',
                'reason': 'technical_keyword_detected',
                'context_hint': f"User {author_name} is requesting high-level support or reporting a technical failure."
            }

        # --- Tier 2 Escalation Triggers (To Sister Meimei - Empathy) ---
        sister_keywords = ['help', 'confused', 'angry', 'upset', 'stupid', 'what', 'why', 'how', '不懂', '生氣', '討厭', '笨', '為什麼', '怎麼辦', '幫忙']
        if any(k in message_lower for k in sister_keywords):
             return {
                'action': 'activate_sister_mode',
                'reason': 'sentiment_or_confusion',
                'context_hint': f"User {author_name} seems confused or emotional. Sister Meimei needed for empathy and guidance."
            }
            
        # Default: Stay in Tier 1 (Local AI / Standard Response)
        return {'action': 'stay_local', 'reason': 'normal_interaction'}

    @api.model
    def generate_context_hint(self, message_body, history=None):
        """
        Generates a summary for the human architect (Brother).
        """
        return f"[System Hint]: User input: '{message_body}'. Please intervene."
