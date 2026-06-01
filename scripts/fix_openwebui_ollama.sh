#!/bin/bash
set -e

echo "☯️ 修復 Open WebUI ↔ Ollama ↔ 蝦敖工具"

docker network create taiji-ai 2>/dev/null || true

OLLAMA_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' wuchang_gpu_brain | awk '{print $1}')

if [ -z "$OLLAMA_IP" ]; then
  echo "❌ 找不到 wuchang_gpu_brain IP"
  exit 1
fi

echo "🧠 Ollama 容器 IP: $OLLAMA_IP"

docker rm -f open-webui 2>/dev/null || true

docker run -d \
  --name open-webui \
  --network taiji-ai \
  --add-host=ollama:$OLLAMA_IP \
  -p 3000:8080 \
  -e OLLAMA_BASE_URL=http://ollama:11434 \
  -v open-webui:/app/backend/data \
  --restart unless-stopped \
  ghcr.io/open-webui/open-webui:main

docker network connect --alias taiji_claw --alias xiaao_voice taiji-ai taiji_claw 2>/dev/null || true

sleep 10

echo "===== Open WebUI ====="
curl -I http://localhost:3000 2>/dev/null | head || true

echo
echo "===== Open WebUI → Ollama ====="
docker exec open-webui python3 - <<'PY'
import urllib.request
print(urllib.request.urlopen("http://ollama:11434/api/tags", timeout=8).read().decode()[:800])
PY

echo
echo "===== Open WebUI → 蝦敖工具 ====="
docker exec open-webui python3 - <<'PY'
import urllib.request
for url in ["http://taiji_claw:9004/healthz", "http://taiji_claw:9004/"]:
    try:
        print(url)
        print(urllib.request.urlopen(url, timeout=5).read().decode()[:300])
    except Exception as e:
        print(url, "reachable/error:", e)
PY

echo
echo "✅ 修復完成"
echo "Open WebUI: http://localhost:3000"
echo "Ollama URL: http://ollama:11434"
echo "蝦敖工具 URL: http://taiji_claw:9004"
