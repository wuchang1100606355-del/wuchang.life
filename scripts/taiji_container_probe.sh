#!/usr/bin/env bash
set -u

TS="$(date +%Y%m%d_%H%M%S)"
OUT="reports/container_probe_$TS.md"
JSON="reports/container_probe_$TS.json"

{
echo "# Taiji Container Probe"
echo
echo "timestamp: $TS"
echo "pwd: $(pwd)"
echo "user: $(whoami)"
echo "host: $(hostname)"
echo

echo "## Docker Version"
docker --version 2>/dev/null || echo "docker_not_found"
docker compose version 2>/dev/null || true
docker-compose --version 2>/dev/null || true
echo

echo "## Docker Service"
systemctl is-active docker 2>/dev/null || true
service docker status 2>/dev/null | head -n 20 || true
echo

echo "## Docker Info"
docker info 2>/dev/null || true
echo

echo "## Containers"
docker ps -a --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || true
echo

echo "## Images"
docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedSince}}' 2>/dev/null || true
echo

echo "## Networks"
docker network ls 2>/dev/null || true
echo

echo "## Volumes"
docker volume ls 2>/dev/null || true
echo

echo "## Compose Files"
find . -maxdepth 5 -type f \( -name 'docker-compose.yml' -o -name 'docker-compose.yaml' -o -name 'compose.yml' -o -name 'compose.yaml' -o -name 'Dockerfile' \) \
  | sort
echo

echo "## Container Inspect Summary"
for c in $(docker ps -aq 2>/dev/null); do
  echo
  echo "### $c"
  docker inspect "$c" --format \
'Name={{.Name}}
Image={{.Config.Image}}
Status={{.State.Status}}
Running={{.State.Running}}
StartedAt={{.State.StartedAt}}
RestartPolicy={{.HostConfig.RestartPolicy.Name}}
Networks={{range $k,$v := .NetworkSettings.Networks}}{{$k}}={{$v.IPAddress}} {{end}}
Mounts={{range .Mounts}}{{.Source}} -> {{.Destination}}; {{end}}
Ports={{json .NetworkSettings.Ports}}' 2>/dev/null || true
done
echo

echo "## Recent Logs: running containers last 80 lines each"
for c in $(docker ps -q 2>/dev/null); do
  name="$(docker inspect "$c" --format '{{.Name}}' 2>/dev/null | sed 's#^/##')"
  echo
  echo "### logs: $name / $c"
  docker logs --tail 80 "$c" 2>&1 || true
done
echo

echo "## Host Ports Related"
ss -lntup 2>/dev/null | grep -E ':8000|:9004|:9090|:50051|:8069|:5432|:6379|:11434|:3000|:8080' || true
echo

echo "## Sensitive Env Names Only"
for c in $(docker ps -aq 2>/dev/null); do
  name="$(docker inspect "$c" --format '{{.Name}}' 2>/dev/null | sed 's#^/##')"
  echo
  echo "### env names: $name"
  docker inspect "$c" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null \
    | sed 's/=.*$/=<redacted>/' \
    | grep -Ei 'key|secret|token|pass|pwd|credential|api|auth|odoo|db|postgres|redis|cloud|taiji|jules' \
    || true
done

} > "$OUT" 2>&1

cat > "$JSON" <<EOFJSON
{
  "timestamp": "$TS",
  "report": "$OUT",
  "mode": "filename_and_metadata_only",
  "warning": "secret values redacted; logs may still contain sensitive data and should be reviewed before sharing"
}
EOFJSON

echo "$OUT"
echo "$JSON"
