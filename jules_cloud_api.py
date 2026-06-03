import os, json, re
from datetime import datetime
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

GCP_PROJECT = "taiji-f124771717"
LOCATION = "asia-east1"

def get_gcp_token():
    # 向 GCP 索取合法展期的企業級 Token
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(GoogleAuthRequest())
    return credentials.token

# 雙路由綁定，確保絕對攔截
# @app.post("/api/v1/proxy/chat/completions")
# @app.post("/chat/completions")
async def proxy_openai_to_gemini(request: Request):
    auth_header = request.headers.get("Authorization", "")
    
    # 1. 攔截您的專屬密碼，自動替換為 GCP Token (破解 60 分鐘斷線)
    if "F124771717-PRO" in auth_header:
        real_token = get_gcp_token()
    else:
        real_token = auth_header.replace("Bearer ", "").strip()

    # 2. 啟動減肥抽脂引擎 (省下數萬元成本的關鍵)
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes.decode('utf-8'))
        if "messages" in payload:
            for msg in payload["messages"]:
                if "content" in msg and isinstance(msg["content"], str):
                    text = msg["content"]
                    text = re.sub(r'\s+', ' ', text)
                    for w in ['請幫我', '你能', '謝謝', '麻煩你', '請問一下', '我想知道', '可以幫我', '幫我', '請問', '請']: 
                        text = text.replace(w, '')
                    msg["content"] = text.strip()
        body_bytes = json.dumps(payload).encode('utf-8')
    except Exception:
        pass

    # 3. 智慧路由至 Vertex AI 企業端點
    target_url = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{GCP_PROJECT}/locations/{LOCATION}/endpoints/openapi/chat/completions"
    headers = {
        "Authorization": f"Bearer {real_token}",
        "Content-Type": "application/json"
    }
    
    # 4. 建立非同步串流通道 (支援打字機效果)
    client = httpx.AsyncClient()
#     async def stream_response():
#         async with client.stream("POST", target_url, headers=headers, content=body_bytes, timeout=60.0) as response:
#             if response.status_code != 200:
#                 err = await response.aread()
#                 yield err
#                 return
#             async for chunk in response.aiter_raw():
#                 yield chunk
#                 
#     return StreamingResponse(stream_response(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
# --- BEGIN: appended safe streaming proxy handler ---
import os
import logging
import httpx
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse

logger = logging.getLogger(__name__)

# 若你有環境變數 UPSTREAM_URL，會使用；否則請改成實際上游 URL
UPSTREAM_URL = os.environ.get("UPSTREAM_URL", "https://upstream.example.com/chat/completions")

async def _upstream_stream_generator(body_bytes: bytes, target_url: str):
    try:
        token = None
        # 使用你現有的 get_gcp_token() 若可用，否則嘗試從環境變數取得
        try:
            token = get_gcp_token()  # 若此函式存在，會回傳 str
        except Exception:
            token = os.environ.get("UPSTREAM_TOKEN")
    except Exception:
        token = None

    headers = {"Content-Type": "application/json"}
    if token:
        token_str = str(token).strip().replace("\n", "").replace("\r", "")
        if token_str:
            headers["Authorization"] = f"Bearer {token_str}"
        else:
            logger.debug("Upstream token empty after strip; not sending Authorization header")
    else:
        logger.debug("No upstream token available; not sending Authorization header")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", target_url, headers=headers, content=body_bytes, timeout=120.0) as resp:
                if resp.status_code >= 400:
                    text = await resp.aread()
                    logger.error("Upstream returned error %s: %s", resp.status_code, text[:1000])
                    raise HTTPException(status_code=502, detail="Upstream returned error")
                async for chunk in resp.aiter_bytes():
                    if chunk:
                        yield chunk
    except httpx.LocalProtocolError:
        logger.exception("LocalProtocolError when calling upstream (likely illegal header)")
        raise HTTPException(status_code=502, detail="Upstream protocol error")
    except httpx.RequestError:
        logger.exception("RequestError when calling upstream")
        raise HTTPException(status_code=502, detail="Upstream request failed")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error when proxying to upstream")
        raise HTTPException(status_code=502, detail="Upstream proxy failed")

# 路由 handler（附加兩個路由，若原檔已有同路由，FastAPI 會以先註冊為準）
# @app.post("/api/v1/proxy/chat/completions")
# @app.post("/chat/completions")
async def proxy_chat_completions(request: Request):
    try:
        body_bytes = await request.body()
    except Exception:
        logger.exception("Failed to read request body")
        return JSONResponse(status_code=400, content={"detail": "Invalid request body"})

    return StreamingResponse(_upstream_stream_generator(body_bytes, UPSTREAM_URL),
                             media_type="text/event-stream")
# --- END: appended safe streaming proxy handler ---
# mixed handler to replace proxy behavior
import os, json, logging, httpx
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)
UPSTREAM_URL = os.environ.get("UPSTREAM_URL", "https://upstream.example.com/chat/completions")

async def _proxy_mixed(body_bytes: bytes, target_url: str):
    try:
        token = None
        try:
            token = get_gcp_token()
        except Exception:
            token = os.environ.get("UPSTREAM_TOKEN")
    except Exception:
        token = None

    headers = {"Content-Type": "application/json"}
    if token:
        token_str = str(token).strip().replace("\n","").replace("\r","")
        if token_str:
            headers["Authorization"] = f"Bearer {token_str}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(target_url, content=body_bytes, headers=headers, timeout=120.0)
        except Exception as e:
            logger.exception("Upstream POST failed")
            raise HTTPException(status_code=502, detail=f"Upstream request failed: {e}")

        ctype = resp.headers.get("content-type","")
        # 若是 JSON 或常見非錯誤回應，直接回傳完整 body
        if "application/json" in ctype or resp.status_code < 400:
            text = await resp.aread()
            try:
                parsed = json.loads(text.decode('utf-8') if isinstance(text, (bytes,bytearray)) else text)
                return JSONResponse(status_code=resp.status_code, content=parsed)
            except Exception:
                return JSONResponse(status_code=resp.status_code, content={"raw": text.decode('utf-8', errors='replace')})

        # 否則 fallback to streaming
        async def stream_gen():
            try:
                async with client.stream("POST", target_url, headers=headers, content=body_bytes, timeout=120.0) as sresp:
                    if sresp.status_code >= 400:
                        text = await sresp.aread()
                        logger.error("Upstream error %s: %s", sresp.status_code, text[:1000])
                        raise HTTPException(status_code=502, detail="Upstream returned error")
                    async for chunk in sresp.aiter_bytes():
                        if chunk:
                            yield chunk
            except Exception:
                logger.exception("streaming proxy error")
                return
        return StreamingResponse(stream_gen(), media_type="text/event-stream")

# route replacement (appended)
@app.post("/chat/completions")
@app.post("/api/v1/proxy/chat/completions")
async def proxy_chat_completions(request: Request):
    body_bytes = await request.body()
    result = await _proxy_mixed(body_bytes, UPSTREAM_URL)
    return result