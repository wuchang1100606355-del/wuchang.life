import json
import time
import threading
import subprocess
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

class 局態張量場運算引擎:
    """
    五常太極大陣 - 社區節點防護閘道引擎 (雙擎融合版)
    結合「背景常駐深度探針雷達」與「前景 HTTP 意圖防護閘道」。
    """
    def __init__(self, 範疇):
        self.地場 = 範疇
        self.PORT_ODOO = 8069
        self.PORT_OLLAMA = 11434
        self.雷達跳動 = True
        
        # 這是雷達即時更新的「度規狀態快取」
        # 閘道器攔截意圖時直接讀取，達成毫秒級控場裁決
        self.健康度 = {
            "vpn_連線": False,
            "vpn_ip": "",
            "odoo_安全": False,
            "ollama_穩定": False
        }

    def 檢測網格陣眼(self):
        """實體探測 Tailscale VPN 狀態"""
        try:
            result = subprocess.run(['tailscale', 'ip', '-4'], capture_output=True, text=True, timeout=2)
            ip = result.stdout.strip()
            if result.returncode == 0 and ip:
                return True, ip
            return False, ""
        except Exception:
            return False, ""

    def 探測_API(self, url, payload=None):
        """支援 GET 與 POST 的 HTTP 深度防假死探針"""
        try:
            if payload:
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
            else:
                req = urllib.request.Request(url, method='GET')
            
            with urllib.request.urlopen(req, timeout=2.0) as response:
                return response.status == 200
        except Exception:
            return False

    def 常駐雷達探針(self):
        """[執行緒 1] 背景執行的無限迴圈，每 5 秒更新系統狀態"""
        print(" 📡 [雷達] 常駐深度探針已啟動 (每 5 秒掃描網格與 API 假死狀態)...")
        while self.雷達跳動:
            # 1. 測網格
            vpn, ip = self.檢測網格陣眼()
            self.健康度["vpn_連線"] = vpn
            self.健康度["vpn_ip"] = ip
            
            # 2. 測 Odoo 地場 (安全爻)
            self.健康度["odoo_安全"] = self.探測_API(f"http://127.0.0.1:{self.PORT_ODOO}/")
            
            # 3. 測 Ollama 算力 (穩定爻) - 確保 API 有回應，防假死
            self.健康度["ollama_穩定"] = self.探測_API(f"http://127.0.0.1:{self.PORT_OLLAMA}/")
            
            time.sleep(5) # 常駐心跳

    def 兩儀分流驗證(self, 意圖):
        # 1. 優先檢測大陣經絡 (直接讀取雷達快取)
        if not self.健康度["vpn_連線"]:
            print("【艮卦 ☶】網格斷線！大陣淪為孤島，阻斷社區請求。")
            return {"狀態": "☶_隔離", "動作": "vpn_offline", "封包": 意圖, "訊息": "Tailscale 網格失聯"}

        # 強制執行確定性輸出（閹割 AI 幻覺）
        意圖["調校"] = 0.0
        
        # 2. 結合雷達掃描結果與封包意圖，推算三爻
        上爻 = 1 if self.健康度["odoo_安全"] else 0
        中爻 = 1 if self.健康度["ollama_穩定"] else 0
        初爻 = 1 if 意圖.get("路權", False) else 0
        
        三爻卦象 = (上爻, 中爻, 初爻)
        return self.八卦形態場控陣(三爻卦象, 意圖)

    def 八卦形態場控陣(self, 卦象, 封包):
        # 1. 乾卦 ☰ (1, 1, 1)：健康全開狀態
        if 卦象 == (1, 1, 1):
            print("【乾卦 ☰】網格通暢，API 清明。放行社區請求，准許寫入 Odoo。")
            return {"狀態": "☰_放行", "動作": "allow_write", "封包": 封包}

        # 2. 兌卦 ☱ (1, 1, 0)：安全唯讀狀態
        elif 卦象 == (1, 1, 0):
            print("【兌卦 ☱】安全唯讀。僅供社區查詢，不予變更帳本。")
            return {"狀態": "☱_唯讀", "動作": "read_only", "封包": 封包}

        # 3. 離卦 ☲ (1, 0, 1)：幻覺潛伏狀態
        elif 卦象 == (1, 0, 1):
            print("【離卦 ☲】警報！AI 算力 API 假死，強制社區管理員人工確認。")
            封包["審查"] = True
            return {"狀態": "☲_介入", "動作": "human_review", "封包": 封包}

        # 4. 震卦 ☳ (0, 0, 1)：破界失穩狀態
        elif 卦象 == (0, 0, 1) or 卦象[0] == 0:
            print("【震卦 ☳ / 坤卦 ☷】警報！核心地場 API 異常！全場鎖死，阻斷請求。")
            return {"狀態": "☷_鎖死", "動作": "block_all", "封包": 封包}

        else:
            print(f"【過渡卦象 {卦象}】沙盒隔離，暫不處理請求。")
            return {"狀態": "☴☵☶_隔離", "動作": "sandbox", "封包": 封包}


# 初始化太極引擎
太極引擎 = 局態張量場運算引擎(範疇="台灣五常社區")

class TaijiGatewayHandler(BaseHTTPRequestHandler):
    """[執行緒 2] 處理社區節點與 AI 傳來的 HTTP POST 請求"""
    
    def do_POST(self):
        # 確保只接收 /api/intent (意圖過濾) 的路徑
        if self.path == '/api/intent':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                # 解析社區節點傳來的 JSON
                意圖封包 = json.loads(post_data.decode('utf-8'))
                print(f"\n[社區節點請求] 收到來自 {self.client_address[0]} 的意圖封包: {意圖封包.get('內文', '未提供')}")
                
                # 送入太極陣法進行度規驗證
                裁決結果 = 太極引擎.兩儀分流驗證(意圖封包)
                
                # 回傳 JSON 給前端或 Odoo
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(裁決結果, ensure_ascii=False).encode('utf-8'))
                
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                print(f"[錯誤] 社區請求封包解析失敗: {e}")
        else:
            self.send_response(404)
            self.end_headers()

    # 隱藏伺服器預設的 log，保持太極畫面乾淨
    def log_message(self, format, *args):
        pass

def 啟動實體閘道器(port=8081):
    # --- 關鍵：啟動背景常駐雷達 (Threading) ---
    雷達執行緒 = threading.Thread(target=太極引擎.常駐雷達探針, daemon=True)
    雷達執行緒.start()

    # --- 啟動前景防護閘道 ---
    伺服器位址 = ('0.0.0.0', port)
    httpd = HTTPServer(伺服器位址, TaijiGatewayHandler)
    
    print("==================================================")
    print(f" ☯️ 台灣五常社區 - 太極雙擎防護閘道 (Port: {port})")
    print("==================================================")
    print("[系統] HTTP 閘道器已啟動，正在監聽社區網格與 AI 傳來的意圖封包...")
    print("[傳承] 為東方科學尋定位。")
    print("--------------------------------------------------")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[系統] 收到中斷信號，閘道器與雷達安全關閉。")
        太極引擎.雷達跳動 = False
        httpd.server_close()

if __name__ == '__main__':
    啟動實體閘道器()