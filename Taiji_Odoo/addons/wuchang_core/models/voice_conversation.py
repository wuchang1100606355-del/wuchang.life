# -*- coding: utf-8 -*-
"""
小J 語音對話優化模型
提供對話上下文管理、情感分析、個性化回應等功能
"""
from odoo import models, fields, api
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class VoiceConversation(models.Model):
    _name = 'wuchang.voice.conversation'
    _description = '小J 語音對話記錄'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='使用者', index=True)
    session_id = fields.Char(string='會話 ID', index=True, help='同一會話的對話記錄')
    user_message = fields.Text(string='使用者訊息', required=True)
    assistant_message = fields.Text(string='小J 回應')
    emotion = fields.Selection([
        ('happy', '開心'),
        ('sad', '難過'),
        ('angry', '生氣'),
        ('anxious', '焦慮'),
        ('neutral', '中性'),
        ('excited', '興奮'),
        ('calm', '平靜'),
    ], string='情感狀態', default='neutral')
    sentiment_score = fields.Float(string='情感分數', help='-1 (負面) 到 1 (正面)')
    response_time = fields.Float(string='回應時間 (秒)')
    user_satisfaction = fields.Selection([
        ('very_satisfied', '非常滿意'),
        ('satisfied', '滿意'),
        ('neutral', '普通'),
        ('dissatisfied', '不滿意'),
        ('very_dissatisfied', '非常不滿意'),
    ], string='使用者滿意度')
    context_summary = fields.Text(string='上下文摘要', help='本次對話的上下文摘要')
    tags = fields.Char(string='標籤', help='逗號分隔的標籤')
    device_type = fields.Selection([
        ('desktop', '桌面'),
        ('mobile', '行動裝置'),
        ('tablet', '平板'),
    ], string='裝置類型')
    page = fields.Char(string='頁面', default='voice')
    
    # 統計欄位
    is_helpful = fields.Boolean(string='有幫助')
    is_relevant = fields.Boolean(string='相關')
    follow_up_count = fields.Integer(string='後續對話次數', default=0, help='同一會話中的後續對話數量')
    
    create_date = fields.Datetime(string='建立時間', readonly=True)
    
    @api.model
    def create_conversation(self, user_message, user_id=None, session_id=None, **kwargs):
        """建立新的對話記錄"""
        if not user_id:
            user_id = self.env.user.id
        if not session_id:
            session_id = f"session_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 分析情感
        emotion_data = self._analyze_emotion(user_message)
        
        # 獲取上下文摘要
        context_summary = self._get_context_summary(session_id, user_id)
        
        conv = self.create({
            'user_id': user_id,
            'session_id': session_id,
            'user_message': user_message,
            'emotion': emotion_data.get('emotion', 'neutral'),
            'sentiment_score': emotion_data.get('score', 0.0),
            'context_summary': context_summary,
            'device_type': kwargs.get('device_type', 'desktop'),
            'page': kwargs.get('page', 'voice'),
        })
        
        return conv
    
    def update_response(self, assistant_message, response_time=None):
        """更新小J的回應"""
        self.write({
            'assistant_message': assistant_message,
            'response_time': response_time or 0.0,
        })
    
    def _analyze_emotion(self, text):
        """簡單的情感分析（可擴展為更複雜的模型）"""
        text_lower = text.lower()
        
        # 關鍵字匹配
        happy_keywords = ['開心', '高興', '快樂', '謝謝', '感謝', '好', '棒', '讚']
        sad_keywords = ['難過', '傷心', '不開心', '糟糕', '不好', '討厭']
        angry_keywords = ['生氣', '憤怒', '討厭', '煩', '氣', '爛']
        anxious_keywords = ['擔心', '焦慮', '害怕', '緊張', '不安']
        excited_keywords = ['興奮', '激動', '太棒了', '太好了', '厲害']
        
        score = 0.0
        emotion = 'neutral'
        
        if any(kw in text_lower for kw in happy_keywords):
            score = 0.7
            emotion = 'happy'
        elif any(kw in text_lower for kw in excited_keywords):
            score = 0.9
            emotion = 'excited'
        elif any(kw in text_lower for kw in sad_keywords):
            score = -0.5
            emotion = 'sad'
        elif any(kw in text_lower for kw in angry_keywords):
            score = -0.7
            emotion = 'angry'
        elif any(kw in text_lower for kw in anxious_keywords):
            score = -0.3
            emotion = 'anxious'
        else:
            score = 0.0
            emotion = 'neutral'
        
        return {'emotion': emotion, 'score': score}
    
    def _get_context_summary(self, session_id, user_id, limit=5):
        """獲取對話上下文摘要"""
        recent_convs = self.search([
            ('session_id', '=', session_id),
            ('user_id', '=', user_id),
        ], limit=limit, order='create_date desc')
        
        if not recent_convs:
            return ''
        
        summary_parts = []
        for conv in reversed(recent_convs):  # 從舊到新
            if conv.user_message and conv.assistant_message:
                summary_parts.append(f"使用者：{conv.user_message[:50]}...")
                summary_parts.append(f"小J：{conv.assistant_message[:50]}...")
        
        return "\n".join(summary_parts)
    
    @api.model
    def get_conversation_history(self, session_id=None, user_id=None, limit=10):
        """獲取對話歷史"""
        domain = []
        if session_id:
            domain.append(('session_id', '=', session_id))
        if user_id:
            domain.append(('user_id', '=', user_id))
        else:
            domain.append(('user_id', '=', self.env.user.id))
        
        convs = self.search(domain, limit=limit, order='create_date desc')
        return convs
    
    @api.model
    def get_user_preferences(self, user_id=None):
        """獲取使用者偏好（基於歷史對話）"""
        if not user_id:
            user_id = self.env.user.id
        
        recent_convs = self.search([
            ('user_id', '=', user_id),
        ], limit=50, order='create_date desc')
        
        preferences = {
            'preferred_tone': 'warm',  # warm, formal, casual, friendly
            'preferred_length': 'medium',  # short, medium, long
            'topics': [],
            'emotion_pattern': 'neutral',
        }
        
        if recent_convs:
            # 分析情感模式
            emotions = [c.emotion for c in recent_convs if c.emotion]
            if emotions:
                from collections import Counter
                emotion_counts = Counter(emotions)
                preferences['emotion_pattern'] = emotion_counts.most_common(1)[0][0] if emotion_counts else 'neutral'
            
            # 分析主題（簡單版本，可擴展）
            all_messages = ' '.join([c.user_message for c in recent_convs if c.user_message])
            # 這裡可以加入更複雜的主題分析
        
        return preferences


class VoiceConversationStats(models.Model):
    _name = 'wuchang.voice.conversation.stats'
    _description = '語音對話統計'
    _order = 'date desc'

    date = fields.Date(string='日期', required=True, index=True)
    user_id = fields.Many2one('res.users', string='使用者', index=True)
    
    total_conversations = fields.Integer(string='總對話數', default=0)
    avg_response_time = fields.Float(string='平均回應時間 (秒)', default=0.0)
    avg_satisfaction = fields.Float(string='平均滿意度', default=0.0)
    total_duration = fields.Float(string='總對話時長 (分鐘)', default=0.0)
    
    emotion_distribution = fields.Text(string='情感分布', help='JSON 格式的情感分布')
    
    @api.model
    def update_daily_stats(self, date=None):
        """更新每日統計"""
        if not date:
            date = fields.Date.today()
        
        # 獲取當日所有對話
        conversations = self.env['wuchang.voice.conversation'].search([
            ('create_date', '>=', f'{date} 00:00:00'),
            ('create_date', '<', f'{date} 23:59:59'),
        ])
        
        # 按使用者分組統計
        user_stats = {}
        for conv in conversations:
            user_id = conv.user_id.id
            if user_id not in user_stats:
                user_stats[user_id] = {
                    'total': 0,
                    'response_times': [],
                    'satisfactions': [],
                    'emotions': [],
                }
            
            user_stats[user_id]['total'] += 1
            if conv.response_time:
                user_stats[user_id]['response_times'].append(conv.response_time)
            if conv.user_satisfaction:
                satisfaction_map = {
                    'very_satisfied': 5,
                    'satisfied': 4,
                    'neutral': 3,
                    'dissatisfied': 2,
                    'very_dissatisfied': 1,
                }
                user_stats[user_id]['satisfactions'].append(satisfaction_map.get(conv.user_satisfaction, 3))
            if conv.emotion:
                user_stats[user_id]['emotions'].append(conv.emotion)
        
        # 更新或創建統計記錄
        for user_id, stats in user_stats.items():
            existing = self.search([
                ('date', '=', date),
                ('user_id', '=', user_id),
            ], limit=1)
            
            avg_response_time = sum(stats['response_times']) / len(stats['response_times']) if stats['response_times'] else 0.0
            avg_satisfaction = sum(stats['satisfactions']) / len(stats['satisfactions']) if stats['satisfactions'] else 0.0
            
            emotion_dist = {}
            if stats['emotions']:
                from collections import Counter
                emotion_counts = Counter(stats['emotions'])
                total = len(stats['emotions'])
                emotion_dist = {k: v / total for k, v in emotion_counts.items()}
            
            vals = {
                'date': date,
                'user_id': user_id,
                'total_conversations': stats['total'],
                'avg_response_time': avg_response_time,
                'avg_satisfaction': avg_satisfaction,
                'emotion_distribution': json.dumps(emotion_dist, ensure_ascii=False),
            }
            
            if existing:
                existing.write(vals)
            else:
                self.create(vals)
        
        return True
