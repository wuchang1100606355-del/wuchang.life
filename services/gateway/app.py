from fastapi import FastAPI

app = FastAPI(title="Taiji Gateway")

@app.get("/healthz")
def healthz():
    return {"ok": True, "service": "Taiji Gateway"}

@app.get("/")
def root():
    return {
        "system": "Taiji_Hub",
        "mode": "local-first",
        "security": "zero-trust-gateway",
        "status": "running"
    }
