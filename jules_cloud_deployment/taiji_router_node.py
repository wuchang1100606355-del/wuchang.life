#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import http.server
import socketserver
import json
import logging
import re

PORT = 9005
logging.basicConfig(level=logging.INFO, format='%(asctime)s [微小J 城門] %(message)s')

class TaijiGatekeeper(http.server.SimpleHTTPRequestHandler):
    
    def _prompt_slimming_engine(self, raw_text):
        """【閘道器減肥引擎】剝除多餘字元、人類禮貌用語，極限壓縮 Token"""
        if raw_text == "EMPTY_PAYLOAD": return raw_text
        text = raw_text
        # 1. 消除多餘空白與換行 (Token殺手)
        text = re.sub(r'\s+', ' ', text)
        # 2. 消除無意義的人類禮貌用語與廢話 (減脂)
        stop_words = ['請幫我', '你能', '謝謝', '麻煩你', '請問一下', '我想知道', '可以幫我', '幫我', '請問']
        for w in stop_words: text = text.replace(w, '')
        return text.strip()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        raw_payload = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "EMPTY_PAYLOAD"

        logging.warning(f"🛡️ 警報！城門遭受敲擊！來源維度: {self.client_address[0]}")
        
        # 啟動閘道器減肥機制
        original_len = len(raw_payload)
        slimmed_payload = self._prompt_slimming_engine(raw_payload)
        slimmed_len = len(slimmed_payload)
        saved_ratio = ((original_len - slimmed_len) / original_len * 100) if original_len > 0 else 0

        logging.warning(f"✂️ [閘道器減肥] 原始大小: {original_len} -> 壓縮後: {slimmed_len} (替總司令節省算力 {saved_ratio:.1f}%)")
        logging.warning(f"📦 壓縮後核心作戰指令: {slimmed_payload}")

        response_data = {
            "status": "GATE_DEFENDED_AND_SLIMMED",
            "node": "mu_2 (微小J 城門)",
            "commander": "F124771717",
            "message": f"訊號已攔截並減肥！替總司令節省 Token 算力 {saved_ratio:.1f}%",
            "slimmed_payload": slimmed_payload
        }

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

    def do_GET(self):
        response_data = {
            "status": "ALIVE",
            "node": "mu_2",
            "message": "微小J 運作正常，減肥引擎待命中。"
        }
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), TaijiGatekeeper) as httpd:
        logging.info(f"正在堅守 Port {PORT}，減肥閘道器已啟動...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
