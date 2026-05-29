#!/usr/bin/env python3
import http.server, socketserver, json, logging, re
PORT = 9005
logging.basicConfig(level=logging.INFO, format='%(asctime)s [微小J 城門] %(message)s')
class TaijiGatekeeper(http.server.SimpleHTTPRequestHandler):
    def _prompt_slimming_engine(self, raw_text):
        if raw_text == "EMPTY_PAYLOAD": return raw_text
        text = re.sub(r'\s+', ' ', raw_text)
        for w in ['請幫我', '你能', '謝謝', '麻煩你', '請問一下', '我想知道', '可以幫我', '幫我', '請問']: text = text.replace(w, '')
        return text.strip()
    def do_POST(self):
        len_val = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(len_val).decode('utf-8') if len_val > 0 else "EMPTY_PAYLOAD"
        slim = self._prompt_slimming_engine(raw)
        saved = ((len(raw) - len(slim)) / len(raw) * 100) if len(raw) > 0 else 0
        logging.warning(f"✂️ [閘道器減肥] 原始: {len(raw)} -> 壓縮: {len(slim)} (省 {saved:.1f}%)")
        self.send_response(200); self.send_header('Content-type', 'application/json'); self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
        self.wfile.write(json.dumps({"status": "SLIMMED", "message": f"減肥完成！省下 {saved:.1f}% 算力", "payload": slim}).encode('utf-8'))
    def do_GET(self):
        self.send_response(200); self.send_header('Content-type', 'application/json'); self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers()
        self.wfile.write(json.dumps({"status": "ALIVE", "message": "微小J 運作正常，減肥引擎待命。"}).encode('utf-8'))
if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), TaijiGatekeeper) as httpd: httpd.serve_forever()
