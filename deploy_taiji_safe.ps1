# Taiji 一鍵安全整理與啟動腳本
$ErrorActionPreference = "Continue"

Write-Host "☯️ Taiji Hub 一鍵部署開始..."
Write-Error "This legacy script is disabled by governance. Use audited manifest/preflight scripts instead."
exit 1

# 1. 建立安全目錄
mkdir core, edge, security, scripts, services\gateway, archive 2>$null

# 2. 保護敏感資料
mkdir archive\secrets_backup 2>$null
if (Test-Path keys) {
  Copy-Item keys archive\secrets_backup\keys_backup -Recurse -Force
  Write-Host "🔐 keys 已備份到 archive/secrets_backup"
}

# 3. 建立 .gitignore
@"
keys/
.env
*.db
*.db-shm
*.db-wal
__pycache__/
*.pyc
*.log
*.out
taiji_env/
jules_env/
Taiji_Odoo/odoo_data/
Taiji_Odoo/postgres_data/
archive/
"@ | Out-File .gitignore -Encoding utf8

# 4. 建立 Gateway 最小入口
@"
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
"@ | Out-File services\gateway\app.py -Encoding utf8

# 5. 建立 requirements
@"
fastapi
uvicorn
httpx
"@ | Out-File requirements.txt -Encoding utf8

# 6. 安裝依賴
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 7. 啟動 Gateway
Write-Host "🚪 啟動 Taiji Gateway：http://127.0.0.1:8080"
python -m uvicorn services.gateway.app:app --host 127.0.0.1 --port 8080
