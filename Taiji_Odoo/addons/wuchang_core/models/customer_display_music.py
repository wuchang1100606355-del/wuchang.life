# -*- coding: utf-8 -*-
"""
客顯設備音樂播放檢查機制
確認播放台灣地區咖啡館常用音樂
優先級：人為設定 > 自動檢測
"""
from odoo import models, fields, api
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class CustomerDisplayMusicPlaylist(models.Model):
    _name = 'wuchang.customer.display.music.playlist'
    _description = '客顯設備音樂播放清單（台灣咖啡館適用）'
    _order = 'sequence, name'

    name = fields.Char(string='音樂名稱', required=True)
    artist = fields.Char(string='藝術家/歌手')
    genre = fields.Selection([
        ('jazz', '爵士樂'),
        ('bossa_nova', 'Bossa Nova'),
        ('acoustic', '輕音樂/原聲'),
        ('taiwanese_indie', '台灣獨立音樂'),
        ('chinese_pop', '華語流行'),
        ('instrumental', '純音樂'),
        ('lounge', 'Lounge 音樂'),
        ('ambient', '環境音樂'),
        ('classical', '古典音樂'),
        ('other', '其他'),
    ], string='音樂類型', default='jazz')
    
    # 音樂來源
    source_type = fields.Selection([
        ('spotify', 'Spotify'),
        ('youtube', 'YouTube'),
        ('local', '本地檔案'),
        ('streaming', '串流服務'),
        ('other', '其他'),
    ], string='來源類型', default='spotify')
    
    source_url = fields.Char(string='來源 URL', help='Spotify、YouTube 或其他音樂來源的 URL')
    source_id = fields.Char(string='來源 ID', help='Spotify Track ID、YouTube Video ID 等')
    
    # 播放設定
    sequence = fields.Integer(string='排序', default=10)
    is_active = fields.Boolean(string='啟用', default=True)
    duration_seconds = fields.Integer(string='播放時長 (秒)', help='音樂的播放時長')
    
    # 台灣咖啡館適用性
    is_taiwan_cafe_appropriate = fields.Boolean(string='適合台灣咖啡館', default=True)
    appropriateness_score = fields.Integer(string='適用性評分', default=5, help='1-10 分，10 分最適合')
    
    # 使用統計
    play_count = fields.Integer(string='播放次數', default=0, readonly=True)
    last_played_date = fields.Datetime(string='最後播放時間', readonly=True)
    
    note = fields.Text(string='備註')
    
    @api.model
    def get_taiwan_cafe_playlist(self, limit=20):
        """獲取適合台灣咖啡館的音樂清單"""
        return self.search([
            ('is_active', '=', True),
            ('is_taiwan_cafe_appropriate', '=', True),
        ], order='appropriateness_score desc, sequence asc', limit=limit)


class CustomerDisplayMusicConfig(models.Model):
    _name = 'wuchang.customer.display.music.config'
    _description = '客顯設備音樂播放設定（人為設定優先）'
    _order = 'device_id, priority desc'

    device_id = fields.Many2one('wuchang.infrastructure.device', string='客顯設備', required=True, domain=[('device_type', '=', 'chrome_os')])
    
    # 設定類型
    config_type = fields.Selection([
        ('manual_playlist', '手動指定播放清單'),
        ('manual_track', '手動指定單曲'),
        ('auto_detect', '自動檢測（僅監控）'),
        ('disabled', '停用音樂檢查'),
    ], string='設定類型', default='manual_playlist', required=True, help='人為設定優先於自動檢測')
    
    # 手動設定（優先）
    manual_playlist_ids = fields.Many2many(
        'wuchang.customer.display.music.playlist',
        'customer_display_music_config_playlist_rel',
        'config_id', 'playlist_id',
        string='指定播放清單',
        help='人為指定的播放清單，優先於自動檢測',
        domain=[('is_active', '=', True), ('is_taiwan_cafe_appropriate', '=', True)]
    )
    
    manual_track_name = fields.Char(string='指定曲目名稱', help='人為指定的單一曲目')
    manual_artist = fields.Char(string='指定藝術家', help='人為指定的藝術家')
    manual_source_url = fields.Char(string='指定來源 URL', help='Spotify、YouTube 等音樂來源 URL')
    
    # 自動檢測設定（僅在未手動設定時使用）
    enable_auto_detect = fields.Boolean(string='啟用自動檢測', default=False, help='僅在未手動設定時啟用')
    auto_detect_interval = fields.Integer(string='自動檢測間隔 (分鐘)', default=5, help='每 N 分鐘自動檢測一次')
    
    # 優先級（數字越大優先級越高）
    priority = fields.Integer(string='優先級', default=10, help='數字越大優先級越高，人為設定通常為 10')
    
    # 狀態
    is_active = fields.Boolean(string='啟用', default=True)
    
    # 設定者資訊
    set_by_user_id = fields.Many2one('res.users', string='設定者', readonly=True, default=lambda self: self.env.user)
    set_date = fields.Datetime(string='設定時間', readonly=True, default=fields.Datetime.now)
    
    note = fields.Text(string='備註', help='設定說明或備註')
    
    @api.model
    def get_device_config(self, device_id):
        """獲取設備的音樂播放設定（優先返回人為設定）"""
        configs = self.search([
            ('device_id', '=', device_id),
            ('is_active', '=', True),
        ], order='priority desc, config_type desc', limit=1)
        
        if configs:
            return configs[0]
        
        # 如果沒有設定，返回預設設定（自動檢測）
        return self.env['wuchang.customer.display.music.config']
    
    def get_effective_playlist(self):
        """獲取有效的播放清單（人為設定優先）"""
        self.ensure_one()
        
        if self.config_type == 'manual_playlist' and self.manual_playlist_ids:
            # 人為指定的播放清單
            return self.manual_playlist_ids.sorted('sequence')
        elif self.config_type == 'manual_track' and self.manual_track_name:
            # 人為指定的單曲
            return self.env['wuchang.customer.display.music.playlist'].search([
                ('name', 'ilike', self.manual_track_name),
                ('is_active', '=', True),
            ], limit=1)
        elif self.config_type == 'auto_detect' and self.enable_auto_detect:
            # 自動檢測模式：返回推薦清單供參考
            return self.env['wuchang.customer.display.music.playlist'].get_taiwan_cafe_playlist()
        
        return self.env['wuchang.customer.display.music.playlist']
    
    def action_apply_config(self):
        """套用設定到設備"""
        self.ensure_one()
        # 這裡可以透過 API 或命令隊列將設定發送到設備
        self.message_post(body=f"音樂播放設定已套用：{self.config_type}")
        return True


class CustomerDisplayMusicCheck(models.Model):
    _name = 'wuchang.customer.display.music.check'
    _description = '客顯設備音樂播放檢查記錄'
    _order = 'check_date desc'

    device_id = fields.Many2one('wuchang.infrastructure.device', string='客顯設備', required=True, domain=[('device_type', '=', 'chrome_os')])
    check_date = fields.Datetime(string='檢查時間', default=fields.Datetime.now, required=True)
    
    # 檢查來源
    check_source = fields.Selection([
        ('manual', '手動檢查'),
        ('auto_detect', '自動檢測'),
        ('device_report', '設備主動回報'),
    ], string='檢查來源', default='manual')
    
    # 檢查結果
    is_playing = fields.Boolean(string='正在播放', default=False)
    current_track_name = fields.Char(string='當前曲目')
    current_artist = fields.Char(string='當前藝術家')
    current_source = fields.Selection([
        ('spotify', 'Spotify'),
        ('youtube', 'YouTube'),
        ('local', '本地檔案'),
        ('streaming', '串流服務'),
        ('unknown', '未知'),
    ], string='音樂來源', default='unknown')
    
    # 匹配結果（與人為設定比對）
    config_id = fields.Many2one('wuchang.customer.display.music.config', string='相關設定')
    matched_playlist_id = fields.Many2one('wuchang.customer.display.music.playlist', string='匹配的播放清單項目')
    is_taiwan_cafe_appropriate = fields.Boolean(string='適合台灣咖啡館', default=False)
    match_confidence = fields.Float(string='匹配信心度', help='0-1，1 表示完全匹配')
    
    # 是否符合人為設定
    matches_manual_config = fields.Boolean(string='符合人為設定', default=False, help='是否與人為設定的播放清單匹配')
    manual_config_status = fields.Selection([
        ('matched', '符合設定'),
        ('not_matched', '不符合設定'),
        ('no_config', '無手動設定'),
    ], string='人為設定狀態', default='no_config')
    
    # 檢查狀態
    check_status = fields.Selection([
        ('success', '檢查成功'),
        ('failed', '檢查失敗'),
        ('no_audio', '無音訊輸出'),
        ('unknown_source', '未知來源'),
        ('manual_override', '人為設定優先'),
    ], string='檢查狀態', default='success')
    
    check_message = fields.Text(string='檢查訊息', help='檢查結果的詳細訊息')
    
    # 音訊資訊
    volume_level = fields.Integer(string='音量等級', help='0-100')
    audio_quality = fields.Selection([
        ('excellent', '優秀'),
        ('good', '良好'),
        ('fair', '普通'),
        ('poor', '不佳'),
    ], string='音質')
    
    @api.model
    def check_device_music(self, device_id, track_info=None):
        """
        檢查指定設備的音樂播放狀態
        優先比對人為設定
        
        Args:
            device_id: 設備 ID
            track_info: 可選的音樂資訊字典（由設備端提供）
        
        Returns:
            dict: 檢查結果
        """
        device = self.env['wuchang.infrastructure.device'].browse(device_id)
        if not device.exists() or device.device_type != 'chrome_os':
            return {
                'status': 'error',
                'message': '設備不存在或不是 Chrome OS 設備',
            }
        
        # 獲取設備的人為設定（優先）
        config = self.env['wuchang.customer.display.music.config'].get_device_config(device_id)
        
        # 如果沒有人為設定，且未啟用自動檢測，則不檢查
        if not config.exists() or config.config_type == 'disabled':
            return {
                'status': 'skipped',
                'message': '設備未設定音樂播放檢查',
            }
        
        # 如果 track_info 為空，嘗試從設備端獲取
        if not track_info:
            track_info = {
                'is_playing': False,
                'track_name': '',
                'artist': '',
                'source': 'unknown',
            }
        
        # 比對人為設定
        matches_manual = False
        manual_status = 'no_config'
        matched_playlist = None
        match_confidence = 0.0
        
        if config.config_type in ['manual_playlist', 'manual_track']:
            # 有人為設定，優先比對
            if config.config_type == 'manual_playlist' and config.manual_playlist_ids:
                # 比對播放清單
                for playlist_item in config.manual_playlist_ids:
                    if track_info.get('track_name') and playlist_item.name.lower() in track_info.get('track_name', '').lower():
                        matches_manual = True
                        matched_playlist = playlist_item
                        match_confidence = 0.9
                        break
                    elif track_info.get('artist') and playlist_item.artist and playlist_item.artist.lower() in track_info.get('artist', '').lower():
                        matches_manual = True
                        matched_playlist = playlist_item
                        match_confidence = 0.7
                        break
                
                manual_status = 'matched' if matches_manual else 'not_matched'
            
            elif config.config_type == 'manual_track' and config.manual_track_name:
                # 比對單曲
                if track_info.get('track_name') and config.manual_track_name.lower() in track_info.get('track_name', '').lower():
                    matches_manual = True
                    manual_status = 'matched'
                    match_confidence = 0.9
                else:
                    manual_status = 'not_matched'
        
        # 判斷是否適合台灣咖啡館
        is_appropriate = False
        if matched_playlist:
            is_appropriate = matched_playlist.is_taiwan_cafe_appropriate
        elif matches_manual:
            is_appropriate = True  # 人為設定的音樂視為適合
        
        # 建立檢查記錄
        check_record = self.create({
            'device_id': device_id,
            'check_date': fields.Datetime.now(),
            'check_source': 'manual' if not track_info.get('from_device') else 'device_report',
            'is_playing': track_info.get('is_playing', False),
            'current_track_name': track_info.get('track_name', ''),
            'current_artist': track_info.get('artist', ''),
            'current_source': track_info.get('source', 'unknown'),
            'config_id': config.id if config.exists() else False,
            'matched_playlist_id': matched_playlist.id if matched_playlist else False,
            'is_taiwan_cafe_appropriate': is_appropriate,
            'match_confidence': match_confidence,
            'matches_manual_config': matches_manual,
            'manual_config_status': manual_status,
            'check_status': 'manual_override' if matches_manual else ('success' if track_info.get('is_playing') else 'no_audio'),
            'volume_level': track_info.get('volume', 0),
            'audio_quality': track_info.get('audio_quality', 'good'),
            'check_message': f"人為設定優先：{'符合' if matches_manual else '不符合' if manual_status == 'not_matched' else '無設定'}",
        })
        
        # 如果匹配到播放清單，更新播放統計
        if matched_playlist:
            matched_playlist.action_play()
        
        return {
            'status': 'success',
            'check_id': check_record.id,
            'matches_manual_config': matches_manual,
            'is_appropriate': is_appropriate,
            'match_confidence': match_confidence,
            'message': check_record.check_message,
        }
    
    @api.model
    def get_latest_check(self, device_id):
        """獲取設備的最新檢查記錄"""
        return self.search([
            ('device_id', '=', device_id),
        ], order='check_date desc', limit=1)
    
    @api.model
    def get_compliance_report(self, device_id=None, days=7):
        """獲取符合度報告（人為設定優先）"""
        domain = [
            ('check_date', '>=', fields.Datetime.now() - timedelta(days=days)),
        ]
        if device_id:
            domain.append(('device_id', '=', device_id))
        
        checks = self.search(domain)
        
        total_checks = len(checks)
        manual_matched = len(checks.filtered(lambda c: c.matches_manual_config))
        manual_not_matched = len(checks.filtered(lambda c: c.manual_config_status == 'not_matched'))
        no_manual_config = len(checks.filtered(lambda c: c.manual_config_status == 'no_config'))
        
        return {
            'total_checks': total_checks,
            'manual_config_matched': manual_matched,
            'manual_config_not_matched': manual_not_matched,
            'no_manual_config': no_manual_config,
            'compliance_rate': (manual_matched / total_checks * 100) if total_checks > 0 else 0,
            'message': f"人為設定符合率：{manual_matched}/{total_checks} ({manual_matched / total_checks * 100 if total_checks > 0 else 0:.1f}%)",
        }
