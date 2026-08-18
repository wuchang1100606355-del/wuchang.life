#!/usr/bin/env python3
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from urllib.parse import (
    parse_qs,
    urlparse,
)
from pathlib import Path
from datetime import (
    datetime,
    timedelta,
    timezone,
)
import argparse
import hashlib
import json
import secrets
import threading

parser = argparse.ArgumentParser()
parser.add_argument("--bind", required=True)
parser.add_argument("--port", required=True, type=int)
parser.add_argument("--node-ref", required=True)
parser.add_argument("--node-ip", required=True)
parser.add_argument("--control-file", required=True)
parser.add_argument("--receipt-dir", required=True)
args = parser.parse_args()

NODE_REF = args.node_ref
NODE_IP = args.node_ip
CONTROL_FILE = Path(args.control_file)
RECEIPT_DIR = Path(args.receipt_dir)
HTML = '<!doctype html>\n<html lang="zh-Hant">\n<head>\n<meta charset="utf-8">\n<meta name="viewport"\n content="width=device-width,initial-scale=1">\n<title>小J商米語音節點</title>\n</head>\n<body>\n<button id="start"\n style="width:100%;min-height:120px;font-size:28px">\n啟動小J商米語音節點\n</button>\n\n<div id="status"\n style="font-size:24px;margin-top:24px">\n尚未啟動\n</div>\n\n<script>\nconst nodeRef = "TAIJI04_SUNMI_POS_GOOGLE_VOICE_NODE";\nconst statusBox = document.getElementById("status");\nlet running = false;\n\nasync function receipt(id, state, errorMessage="") {\n  await fetch("/receipt", {\n    method: "POST",\n    headers: {"Content-Type": "application/json"},\n    body: JSON.stringify({\n      request_id: id,\n      node_ref: nodeRef,\n      execution_state: state,\n      error_message: errorMessage,\n      executed_at: new Date().toISOString()\n    })\n  });\n}\n\nasync function loop() {\n  while (running) {\n    try {\n      const response = await fetch(\n        "/next?node_ref="\n          + encodeURIComponent(nodeRef),\n        {cache: "no-store"}\n      );\n\n      if (response.status === 204) {\n        await new Promise(resolve =>\n          setTimeout(resolve, 700)\n        );\n        continue;\n      }\n\n      if (!response.ok) {\n        statusBox.textContent =\n          "通道錯誤：" + response.status;\n\n        await new Promise(resolve =>\n          setTimeout(resolve, 1500)\n        );\n        continue;\n      }\n\n      const item = await response.json();\n\n      statusBox.textContent =\n        "播放：" + item.text;\n\n      const utterance =\n        new SpeechSynthesisUtterance(item.text);\n\n      utterance.lang = "zh-TW";\n      utterance.rate = 0.92;\n      utterance.volume = 1.0;\n\n      const voices =\n        speechSynthesis.getVoices();\n\n      const voice =\n        voices.find(v =>\n          v.lang.toLowerCase().startsWith("zh-tw")\n        )\n        ||\n        voices.find(v =>\n          v.lang.toLowerCase().startsWith("zh")\n        );\n\n      if (voice) {\n        utterance.voice = voice;\n      }\n\n      await new Promise(resolve => {\n        utterance.onend = async () => {\n          await receipt(\n            item.request_id,\n            "FINISHED"\n          );\n          resolve();\n        };\n\n        utterance.onerror = async event => {\n          await receipt(\n            item.request_id,\n            "FAILED",\n            String(\n              event.error || "speech_error"\n            )\n          );\n          resolve();\n        };\n\n        speechSynthesis.cancel();\n        speechSynthesis.speak(utterance);\n      });\n\n      statusBox.textContent =\n        "等待下一個總場核准要求";\n\n    } catch (error) {\n      statusBox.textContent =\n        "等待VPN通道：" + error;\n\n      await new Promise(resolve =>\n        setTimeout(resolve, 1500)\n      );\n    }\n  }\n}\n\ndocument.getElementById("start").onclick =\nasync () => {\n  if (running) return;\n\n  const activated = await fetch(\n    "/activate",\n    {\n      method: "POST",\n      headers: {\n        "Content-Type": "application/json"\n      },\n      body: JSON.stringify({\n        node_ref: nodeRef\n      })\n    }\n  );\n\n  if (!activated.ok) {\n    statusBox.textContent =\n      "啟動失敗：" + activated.status;\n    return;\n  }\n\n  running = true;\n\n  document.getElementById(\n    "start"\n  ).disabled = true;\n\n  statusBox.textContent =\n    "VPN語音節點已啟動";\n\n  speechSynthesis.getVoices();\n  loop();\n};\n</script>\n</body>\n</html>'

queue = []
used_nonces = set()
lock = threading.Lock()

def send_json(handler, status, payload):
    body = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    handler.send_response(status)

    handler.send_header(
        "Content-Type",
        "application/json; charset=utf-8",
    )

    handler.send_header(
        "Content-Length",
        str(len(body)),
    )

    handler.end_headers()
    handler.wfile.write(body)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return

    def node_allowed(self):
        return self.client_address[0] == NODE_IP

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/healthz":
            send_json(
                self,
                200,
                {
                    "status": "ok",
                    "node_ref": NODE_REF,
                },
            )
            return

        if parsed.path == f"/node/{NODE_REF}":
            if not self.node_allowed():
                send_json(
                    self,
                    403,
                    {
                        "state":
                        "BLOCK_SOURCE_DEVICE_MISMATCH"
                    },
                )
                return

            body = HTML.encode("utf-8")

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8",
            )

            self.send_header(
                "Content-Length",
                str(len(body)),
            )

            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/next":
            if not self.node_allowed():
                send_json(
                    self,
                    403,
                    {
                        "state":
                        "BLOCK_SOURCE_DEVICE_MISMATCH"
                    },
                )
                return

            requested_node = (
                parse_qs(parsed.query)
                .get("node_ref", [""])[0]
            )

            if requested_node != NODE_REF:
                send_json(
                    self,
                    403,
                    {
                        "state":
                        "BLOCK_NODE_REF_MISMATCH"
                    },
                )
                return

            item = None

            with lock:
                while queue:
                    candidate = queue.pop(0)

                    expires_at = (
                        datetime.fromisoformat(
                            candidate["expires_at"]
                        )
                    )

                    if (
                        expires_at
                        > datetime.now(timezone.utc)
                    ):
                        item = candidate
                        break

            if item is None:
                self.send_response(204)
                self.end_headers()
            else:
                send_json(
                    self,
                    200,
                    item,
                )

            return

        send_json(
            self,
            404,
            {"state": "NOT_FOUND"},
        )

    def do_POST(self):
        parsed = urlparse(self.path)

        length = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
        )

        try:
            payload = json.loads(
                self.rfile.read(length).decode(
                    "utf-8"
                )
            )
        except Exception:
            send_json(
                self,
                400,
                {"state": "INVALID_JSON"},
            )
            return

        if parsed.path == "/activate":
            if not self.node_allowed():
                send_json(
                    self,
                    403,
                    {
                        "state":
                        "BLOCK_ACTIVATION_SOURCE"
                    },
                )
                return

            if payload.get("node_ref") != NODE_REF:
                send_json(
                    self,
                    403,
                    {
                        "state":
                        "BLOCK_NODE_REF_MISMATCH"
                    },
                )
                return

            control = json.loads(
                CONTROL_FILE.read_text(
                    encoding="utf-8"
                )
            )

            now = datetime.now(timezone.utc)

            request_id = (
                "TAIJI04_VOICE_TEST_"
                + now.strftime(
                    "%Y%m%dT%H%M%SZ"
                )
            )

            nonce = secrets.token_hex(16)

            text = (
                "小J總場控制測試。"
                "商米語音節點已接入VPN音訊通道。"
            )

            with lock:
                used_nonces.add(nonce)

                queue.append({
                    "request_id":
                        request_id,
                    "node_ref":
                        NODE_REF,
                    "text":
                        text,
                    "text_sha256":
                        hashlib.sha256(
                            text.encode("utf-8")
                        ).hexdigest(),
                    "control_packet_sha256":
                        control.get(
                            "packet_sha256"
                        ),
                    "nonce":
                        nonce,
                    "issued_at":
                        now.isoformat(),
                    "expires_at":
                        (
                            now
                            + timedelta(seconds=30)
                        ).isoformat(),
                    "decision":
                        "ALLOW",
                })

            send_json(
                self,
                200,
                {
                    "state": "ACTIVATED",
                    "request_id": request_id,
                },
            )
            return

        if parsed.path == "/receipt":
            if not self.node_allowed():
                send_json(
                    self,
                    403,
                    {
                        "state":
                        "BLOCK_RECEIPT_SOURCE"
                    },
                )
                return

            receipt = {
                "receipt_type":
                    "W7TP_VPN_AUDIO_PLAYBACK_RECEIPT_V1",
                "request_id":
                    payload.get("request_id"),
                "node_ref":
                    NODE_REF,
                "execution_state":
                    payload.get(
                        "execution_state"
                    ),
                "error_message":
                    payload.get(
                        "error_message",
                        "",
                    ),
                "executed_at":
                    payload.get("executed_at"),
                "received_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
                "raw_audio_saved":
                    False,
            }

            unsigned = (
                json.dumps(
                    receipt,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")

            receipt["receipt_sha256"] = (
                hashlib.sha256(
                    unsigned
                ).hexdigest()
            )

            path = (
                RECEIPT_DIR
                / (
                    str(receipt["request_id"])
                    + "_RECEIPT.json"
                )
            )

            if not path.exists():
                path.write_text(
                    json.dumps(
                        receipt,
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

                path.chmod(0o600)

            send_json(
                self,
                200,
                {
                    "state":
                        "RECEIPT_ACCEPTED",
                    "receipt_sha256":
                        receipt[
                            "receipt_sha256"
                        ],
                },
            )
            return

        send_json(
            self,
            404,
            {"state": "NOT_FOUND"},
        )

ThreadingHTTPServer(
    (args.bind, args.port),
    Handler,
).serve_forever()
