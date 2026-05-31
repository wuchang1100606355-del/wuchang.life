# -*- coding: utf-8 -*-
"""
客顯設備音樂播放檢查控制器
提供 API 端點供設備端回報音樂播放狀態
"""
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class CustomerDisplayMusicController(http.Controller):

    @http.route('/api/customer_display/music/check', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def check_music_status(self, **kwargs):
        """
        設備端回報音樂播放狀態
        優先比對人為設定
        
        請求格式：
        {
            "device_id": 123,
            "track_name": "歌曲名稱",
            "artist": "藝術家",
            "source": "spotify",
            "is_playing": true,
            "volume": 50
        }
        """
        try:
            data = request.jsonrequest or {}
            device_id = data.get('device_id')
            
            if not device_id:
                return {
                    'status': 'error',
                    'message': '缺少 device_id',
                }
            
            track_info = {
                'track_name': data.get('track_name', ''),
                'artist': data.get('artist', ''),
                'source': data.get('source', 'unknown'),
                'is_playing': data.get('is_playing', False),
                'volume': data.get('volume', 0),
                'audio_quality': data.get('audio_quality', 'good'),
                'from_device': True,
            }
            
            # 執行檢查（優先比對人為設定）
            result = request.env['wuchang.customer.display.music.check'].sudo().check_device_music(
                device_id, track_info
            )
            
            return result
            
        except Exception as e:
            _logger.error(f"音樂檢查失敗: {e}")
            return {
                'status': 'error',
                'message': str(e),
            }

    @http.route('/api/customer_display/music/config', type='json', auth='user', methods=['GET'], csrf=False)
    def get_music_config(self, **kwargs):
        """
        獲取設備的音樂播放設定（人為設定優先）
        """
        try:
            device_id = request.params.get('device_id') or kwargs.get('device_id')
            
            if not device_id:
                return {
                    'status': 'error',
                    'message': '缺少 device_id',
                }
            
            config = request.env['wuchang.customer.display.music.config'].sudo().get_device_config(device_id)
            
            if not config.exists():
                return {
                    'status': 'no_config',
                    'message': '設備未設定音樂播放配置',
                }
            
            playlist_data = []
            effective_playlist = config.get_effective_playlist()
            for item in effective_playlist:
                playlist_data.append({
                    'id': item.id,
                    'name': item.name,
                    'artist': item.artist,
                    'genre': item.genre,
                    'source_url': item.source_url,
                    'source_id': item.source_id,
                })
            
            return {
                'status': 'success',
                'config': {
                    'config_type': config.config_type,
                    'is_active': config.is_active,
                    'priority': config.priority,
                    'playlist': playlist_data,
                    'manual_track_name': config.manual_track_name,
                    'manual_artist': config.manual_artist,
                    'manual_source_url': config.manual_source_url,
                    'enable_auto_detect': config.enable_auto_detect,
                    'auto_detect_interval': config.auto_detect_interval,
                },
                'message': '人為設定優先' if config.config_type in ['manual_playlist', 'manual_track'] else '自動檢測模式',
            }
            
        except Exception as e:
            _logger.error(f"獲取音樂設定失敗: {e}")
            return {
                'status': 'error',
                'message': str(e),
            }

    @http.route('/api/customer_display/music/compliance', type='json', auth='user', methods=['GET'], csrf=False)
    def get_compliance_report(self, **kwargs):
        """
        獲取符合度報告（人為設定優先）
        """
        try:
            device_id = request.params.get('device_id') or kwargs.get('device_id')
            days = int(request.params.get('days') or kwargs.get('days') or 7)
            
            report = request.env['wuchang.customer.display.music.check'].sudo().get_compliance_report(
                device_id=device_id, days=days
            )
            
            return {
                'status': 'success',
                'report': report,
            }
            
        except Exception as e:
            _logger.error(f"獲取符合度報告失敗: {e}")
            return {
                'status': 'error',
                'message': str(e),
            }
