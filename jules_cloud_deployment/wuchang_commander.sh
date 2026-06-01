#!/bin/bash
# 五常太極大陣 - 終極全境點火與介面生成卷軸 (Complete Genesis)
# 總指揮官: 江政隆 (F124771717)

BASE_DIR="$HOME/Taiji_Hub/jules_cloud_deployment"
mkdir -p "$BASE_DIR"
cd "$BASE_DIR" || exit 1

GREEN='\033[1;32m'
RED='\033[1;31m'
BLUE='\033[1;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}    ⚡ 啟動【大一統全境點火與介面生成協定】 ⚡${NC}"
echo -e "${BLUE}======================================================${NC}"

echo -e "${YELLOW}[1/5] 鑄造後端實體陣眼 (Sister J & 微小 J)...${NC}"

# 補齊 Sister J
cat << 'EOF' > sister_j_edge_cortex.py
#!/usr/bin/env python3
import time, logging
from jules_metric_tensor_engine import WuchangKnowledgeManifold
logging.basicConfig(level=logging.INFO, format='%(asctime)s [Sister J 邊緣皮層] %(message)s')
class SisterJEdgeCortex:
    def __init__(self):
        self.core_mind = WuchangKnowledgeManifold()
    def report_status(self):
        self.core_mind.read_my_state()
if __name__ == "__main__":
    cortex = SisterJEdgeCortex()
    while True: time.sleep(60)
EOF

# 補齊 微小 J 城門
cat << 'EOF' > taiji_router_node.py
#!/usr/bin/env python3
import http.server, socketserver, json, logging
PORT = 9005
logging.basicConfig(level=logging.INFO, format='%(asctime)s [微小J 城門] %(message)s')
class TaijiGatekeeper(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()
        self.wfile.write(json.dumps({"status": "GATE_DEFENDED", "message": "實體探測訊號已接收！"}).encode('utf-8'))
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ALIVE", "message": "微小J 運作正常。"}).encode('utf-8'))
if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), TaijiGatekeeper) as httpd: httpd.serve_forever()
EOF

echo -e "${YELLOW}[2/5] 鑄造前端上帝視角與商業 POS (UI)...${NC}"

# 補齊 賈維斯觀測儀 (極簡版，確保不吃字)
cat << 'EOF' > wuchang_jarvis_cortex.html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>五常大陣 - 賈維斯觀測儀</title>
    <style>body { background: #0b0f19; color: #38bdf8; font-family: monospace; padding: 20px; }</style>
</head>
<body>
    <h1>五常太極大陣 v22.0 (LLM Dispatch)</h1>
    <p>指揮官: F124771717 | 目標 API: <input type="text" id="api" value="http://127.0.0.1:8000" style="background:#1e293b;color:#fff;"></p>
    <button onclick="check()" style="padding:10px; background:#047857; color:white; border:none; cursor:pointer;">1. 掃描度規張量</button>
    <button onclick="strike()" style="padding:10px; background:#b45309; color:white; border:none; cursor:pointer;">2. 發動實體探測 (Port 9005)</button>
    <pre id="log" style="background:#000; padding:15px; margin-top:20px; color:#a3e635;">系統待命中...</pre>
    <script>
        const log = msg => document.getElementById('log').innerText += '\n> ' + msg;
        async function check() {
            try { const r = await fetch(document.getElementById('api').value+'/api/v1/tensor'); log(JSON.stringify(await r.json(), null, 2)); } catch(e) { log('連線失敗'); }
        }
        async function strike() {
            try { const r = await fetch(document.getElementById('api').value+'/api/v1/forward/mu_2', {method:'POST'}); log((await r.json()).message); } catch(e) { log('打擊失敗'); }
        }
    </script>
</body>
</html>
EOF

# 補齊 蝦敖 POS (AI 語音版骨架)
cat << 'EOF' > xia_ao_pos_commercial.html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>蝦敖 POS 語音系統 [AI 助理版]</title>
    <style>
        body { background: #121212; color: #d4af37; font-family: sans-serif; text-align: center; padding-top: 50px; }
        input { padding: 10px; text-align: center; font-weight: bold; }
        button { padding: 10px 20px; background: #d4af37; border: none; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🍤 蝦敖 POS 企業版</h1>
    <p>請輸入金鑰 (F124771717-PRO) 解鎖系統：</p>
    <input type="password" id="key" placeholder="Enter License...">
    <button onclick="unlock()">驗證</button>
    <h2 id="msg" style="color:red;"></h2>
    <script>
        function unlock() {
            if(document.getElementById('key').value === 'F124771717-PRO') {
                document.getElementById('msg').style.color = '#10b981';
                document.getElementById('msg').innerText = "✅ 解鎖成功！語音模組已載入。";
                let t = new SpeechSynthesisUtterance("指揮官，歡迎使用蝦敖企業級語音 POS 系統。");
                t.lang = 'zh-TW'; speechSynthesis.speak(t);
            } else { document.getElementById('msg').innerText = "❌ 授權無效"; }
        }
    </script>
</body>
</html>
EOF

echo -e "${YELLOW}[3/5] 鑄造 Open WebUI 戰術武器庫 (LLM Tools)...${NC}"

# 補齊 Open WebUI 三合一工具
cat << 'EOF' > open_webui_taiji_tools.py
"""
title: 五常大陣 - 戰術指揮武器庫 (三合一)
author: 江政隆 (F124771717)
description: 讓 AI 具備雷達觀測、度規掃描與實體打擊的能力。
"""
import urllib.request, json
class Tools:
    def __init__(self): self.api = "http://127.0.0.1:8000"
    def check_taiji_health(self) -> str:
        """調閱大陣健康度與度規張量特徵值。"""
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{self.api}/api/v1/tensor", method="GET"), timeout=5) as r:
                d = json.loads(r.read().decode())
                return f"狀態:{d.get('health')} | 特徵值:{d.get('eigenvalues')}"
        except Exception as e: return f"連線失敗: {e}"
    def execute_physical_strike(self, target_node: str) -> str:
        """對實體節點(如 mu_2)發動打擊探測。"""
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{self.api}/api/v1/forward/{target_node}?command=STRIKE", method="POST"), timeout=5) as r:
                return f"打擊回報: {json.loads(r.read().decode()).get('message')}"
        except Exception as e: return f"發射失敗: {e}"
    def get_radar_stats(self) -> str:
        """獲取大陣通訊日誌與攔截次數。"""
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{self.api}/api/v1/stats", method="GET"), timeout=5) as r:
                s = json.loads(r.read().decode()).get("statistics", {})
                return f"總通訊:{s.get('total_communications')}次 | 日誌:{s.get('recent_logs')}"
        except Exception as e: return f"雷達異常: {e}"
EOF

echo -e "${YELLOW}[4/5] 掃蕩舊版殘留進程...${NC}"
pkill -f taiji_router_node.py || true
pkill -f sister_j_edge_cortex.py || true
pkill -f jules_cloud_api.py || true
pkill -f "uvicorn jules_cloud_api:app" || true
sleep 1.5

echo -e "${YELLOW}[5/5] 進入陣地並全面點火...${NC}"
nohup python3 jules_cloud_api.py > local_api.log 2>&1 &
nohup python3 sister_j_edge_cortex.py > edge_cortex.log 2>&1 &
nohup python3 taiji_router_node.py > router_node.log 2>&1 &
sleep 2

echo "------------------------------------------------------"
if pgrep -f "jules_cloud_api.py" > /dev/null || pgrep -f "uvicorn jules_cloud_api:app" > /dev/null; then echo -e " [mu_0] Jules API替身 : ${GREEN}[ ✅ 運行中 ]${NC}"; else echo -e " [mu_0] Jules API替身 : ${RED}[ ❌ 失敗 ]${NC}"; fi
if pgrep -f "sister_j_edge_cortex.py" > /dev/null; then echo -e " [mu_1] Sister J 皮層 : ${GREEN}[ ✅ 運行中 ]${NC}"; else echo -e " [mu_1] Sister J 皮層 : ${RED}[ ❌ 失敗 ]${NC}"; fi
if pgrep -f "taiji_router_node.py" > /dev/null; then echo -e " [mu_2] 微小J 城門    : ${GREEN}[ ✅ 運行中 ]${NC}"; else echo -e " [mu_2] 微小J 城門    : ${RED}[ ❌ 失敗 ]${NC}"; fi

echo -e "${BLUE}======================================================${NC}"
echo -e "  ✅ 全境點火完畢！大陣、UI、LLM工具 已全數生成！"
echo -e "  📂 您的 HTML 介面與 Python 工具已存放在:"
echo -e "     ${YELLOW}$BASE_DIR${NC}"
echo -e "  👉 請直接用瀏覽器開啟資料夾內的 .html 檔案。"
echo -e "${BLUE}======================================================${NC}"
