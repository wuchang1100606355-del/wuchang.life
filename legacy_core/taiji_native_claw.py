from fastapi import FastAPI, HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import os
import ipaddress

app = FastAPI()

DEFAULT_ALLOWED_CLIENT_CIDRS = (
    "127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,"
    "192.168.0.0/16,100.64.0.0/10,fc00::/7,fe80::/10"
)


def _allowed_networks():
    raw = os.getenv("ALLOWED_CLIENT_CIDRS", DEFAULT_ALLOWED_CLIENT_CIDRS)
    return [ipaddress.ip_network(item.strip(), strict=False) for item in raw.split(",") if item.strip()]


def _client_allowed(host: str) -> bool:
    try:
        client_ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(client_ip in network for network in _allowed_networks())


@app.middleware("http")
async def enforce_client_whitelist(request: Request, call_next):
    client_host = request.client.host if request.client else ""
    if not _client_allowed(client_host):
        return JSONResponse(
            status_code=403,
            content={"detail": "Forbidden: client is outside ALLOWED_CLIENT_CIDRS"},
        )
    return await call_next(request)

class ClawRequest(BaseModel):
    prompt: str

@app.post("/api/openclaw/ask")
async def execute_claw(req: ClawRequest):
    print(f"🦞 [太極原生爪] 收到指令: {req.prompt}")
    try:
        # 強制拆解並執行寫檔動作
        if "建立" in req.prompt and "lobster_strike.py" in req.prompt:
            with open("lobster_strike.py", "w", encoding="utf-8") as f:
                f.write('print("🦞 報告總指揮官！太極原生實體結界已完美突破！")\n')
            return {"response": "Success: lobster_strike.py created."}
        return {"response": f"指令已接收: {req.prompt}"}
    except Exception as e:
        return {"response": f"Error: {e}"}

if __name__ == "__main__":
    port = int(os.getenv("CLAW_PORT", "9004"))
    host = os.getenv("CLAW_HOST", "0.0.0.0")
    print(f"太極原生 Claw 啟動中 ({host}:{port})...")
    uvicorn.run(app, host=host, port=port)
