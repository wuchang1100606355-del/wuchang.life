#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/Taiji_Hub"
POLICY="$ROOT/commander/config/node_sync_policy.json"

python3 - <<'PY'
import json
import pathlib
import shlex

root = pathlib.Path.home() / "Taiji_Hub"
policy = json.loads((root / "commander/config/node_sync_policy.json").read_text(encoding="utf-8"))

print("# 五常節點同步與命令矩陣 DRY RUN")
print()
print("模式：只列命令，不跨機執行。")
print()

for node in policy.get("nodes", []):
    name = node.get("name", "UNKNOWN")
    ip = node.get("ip", "UNKNOWN")
    role = node.get("role", "")
    sync_items = node.get("sync", [])
    commands = node.get("commands", [])
    ssh_target = node.get("ssh_target")

    print(f"## {name} / {ip}")
    print(f"- role: {role}")

    print("- sync:")
    for item in sync_items:
        print(f"  - {item}")

    print("- commands:")
    for cmd in commands:
        print(f"  - {cmd}")

    if ssh_target:
        print("- dry-run rsync:")
        for item in sync_items:
            if item.startswith(("docs/", "services/", "commander/", "runtime/", "reviews/")):
                src = f"~/Taiji_Hub/{item}"
                dst = f"{ssh_target}:~/Taiji_Hub_mirror/{item}"
                print(
                    "  rsync -avn "
                    "--exclude .env "
                    "--exclude '*.key' "
                    "--exclude '*.pem' "
                    "--exclude '*.db' "
                    "--exclude 'postgres_data' "
                    "--exclude 'odoo_data' "
                    f"{src} {dst}"
                )

        print("- dry-run remote health:")
        remote_cmd = "hostname && date && tailscale status && ss -ltnp | grep -E ':9002|:8080|:11434' || true"
        print(f"  ssh {ssh_target} {shlex.quote(remote_cmd)}")

    print()
PY
