#!/bin/bash

echo "===== Docker PS ====="
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}'
echo

echo "===== wuchang_gpu_brain inspect ====="
docker inspect wuchang_gpu_brain \
  --format 'Name={{.Name}}
Running={{.State.Running}}
NetworkMode={{.HostConfig.NetworkMode}}
IPAddress={{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}
Ports={{json .HostConfig.PortBindings}}' 2>/dev/null || true
echo

echo "===== 11434 使用狀態 ====="
sudo ss -ltnp | grep 11434 || true
echo

echo "===== Ollama 容器內模型 ====="
docker exec wuchang_gpu_brain ollama list 2>/dev/null || true
echo

echo "===== Open WebUI 環境變數 ====="
docker exec open-webui printenv | grep -i OLLAMA || true
echo

echo "===== taiji-ai 網路成員 ====="
docker network inspect taiji-ai --format '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null || true
echo
