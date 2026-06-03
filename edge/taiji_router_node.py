#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 五常太極大陣 - 微小J 城門 (Micro J Router Node)
# 最高指揮官: 哥哥 江政隆 (F124771717)
# 節點位置: Asuswrt-Merlin (Tailscale IP: 100.121.79.82)
# 任務: 駐守 Port 9005，接收大陣的實體探測與網路喚醒 (WOL) 指令

import http.server
import socketserver
import json
import logging

# 微小J 專屬防禦埠號
PORT = 9005

# 設定軍事級日誌格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s [微小J 城門] %(message)s')

class TaijiGatekeeper(http.server.SimpleHTTPRequestHandler):
    
    def do_POST(self):
        """處理來自 Sister J 或 Jules 的實體打擊指令"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"EMPTY_PAYLOAD"

        logging.warning(f"🛡️ 警報！城門遭受敲擊！來源維度: {self.client_address[0]}")
        logging.warning(f"📦 解析作戰指令: {post_data.decode('utf-8')}")

        # 這裡未來可以加入真正的 Asuswrt 網路喚醒 (WOL) 腳本執行邏輯
        # os.system("ether-wake -i br0 XX:XX:XX:XX:XX:XX")

        response_data = {
            "status": "GATE_DEFENDED",
            "node": "mu_2 (微小J 城門)",
            "commander": "F124771717",
            "message": "實體探測訊號已接收！城門防禦陣型穩固，網格未被攻破！"
        }

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        # 加上 CORS 讓雷達如果想直接觀測也可以穿透
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

    def do_GET(self):
        """處理日常的巡邏心跳偵測"""
        logging.info(f"📡 收到心跳偵測，來源: {self.client_address[0]}")
        
        response_data = {
            "status": "ALIVE",
            "node": "mu_2",
            "message": "微小J 運作正常，隨時可接受物理打擊指令。"
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

if __name__ == "__main__":
    print("\n" + "="*50)
    print("   [ ⛩️ 微小J 城門守衛系統載入中 ⛩️ ]   ")
    print("="*50)
    logging.info(f"正在堅守 Port {PORT}，等待總司令 (F124771717) 的指令...")
    
    # 啟動輕量級 TCP 伺服器，永不休止
    with socketserver.TCPServer(("", PORT), TaijiGatekeeper) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n城門守衛休眠。")
