# W7TP OpenWebUI Desensitized Cloud Proxy DB MVP

STATE=SANDBOX_ONLY

Endpoint:
- GET /healthz
- GET /v1/models
- POST /v1/chat/completions

Model:
- w7tp-cloud-desensitized

Adapter:
- SAFE_LOCAL_STUB

Safety:
- no member plaintext
- no secret read/send
- no Odoo/POS/production DB write
- no payment
- no service restart
- no deploy
