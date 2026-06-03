import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from XiaoJ_Local_Driver import XiaoJ_LocalDriver

driver = XiaoJ_LocalDriver()

class RequestHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req_json = json.loads(post_data.decode('utf-8'))
            packet = driver.smart_desensitize(req_json.get('text', ''), req_json.get('user_profile', {}))
            
            is_care_intent = packet.detected_intent == "community_care"
            is_risk = "轉帳" in packet.original_text or "匯款" in packet.original_text
            audit_status = "APPROVED" if is_care_intent and not is_risk else ("REJECTED" if is_risk else "UNCLEAR")
            reason = "符合醫療照護意圖" if audit_status == "APPROVED" else ("觸發攔截" if audit_status == "REJECTED" else "未定義")
            
            res = {
                "original_text": packet.original_text,
                "masked_text": packet.masked_text,
                "audit_status": audit_status,
                "audit_reason": reason,
                "token_map": packet.token_map
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

if __name__ == '__main__':
    server_address = ('0.0.0.0', 8000)
    httpd = HTTPServer(server_address, RequestHandler)
    print("啟動 API 閘道器於 Port 8000...")
    httpd.serve_forever()
