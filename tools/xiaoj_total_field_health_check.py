#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("/home/taiji_admin/Taiji_Hub")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))



SOURCE_MANIFEST = (
    PROJECT_ROOT
    / "manifests/ollama_xiaoj_total_field_v0_1/source_manifest.sha256"
)
AUTHORITY_PROFILE = (
    PROJECT_ROOT / "configs/total_field/active_total_field_authority_runtime_v1.json"
)
REQUIRED_SERVICES = ("taiji-gateway.service",)
PORT_EXPECTATIONS = {8080: True, 8081: True, 9002: True, 9011: True, 8787: False, 9108: False}
OLLAMA_GENERATE_URL = "http://127.0.0.1:11434/api/generate"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_source_manifest() -> dict[str, Any]:
    mismatches: list[str] = []
    checked = 0
    for line in SOURCE_MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(maxsplit=1)
        target = (PROJECT_ROOT / relative.strip()).resolve()
        if PROJECT_ROOT not in target.parents:
            mismatches.append("PATH_ESCAPE")
            continue
        checked += 1
        if not target.is_file():
            mismatches.append(relative.strip())
        elif _sha256(target) != expected:
            mismatches.append(relative.strip())
    return {
        "state": "PASS" if not mismatches else "DRIFT",
        "checked": checked,
        "mismatch_count": len(mismatches),
        "mismatch_refs": mismatches[:8],
    }


def _service_active(service: str) -> bool:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "--quiet", service],
        check=False,
        timeout=10,
    )
    return result.returncode == 0


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def build_health_observation() -> dict[str, Any]:
    alignment = {
        "aligned": _port_open(8080) and _port_open(9002),
        "source": "LIVE_CURRENT_CONTAINER_ROUTE",
        "openwebui_port": 8080,
        "upstream_port": 9002,
        "legacy_database_used": False,
    }
    manifest = verify_source_manifest()
    services = {name: _service_active(name) for name in REQUIRED_SERVICES}
    ports = {
        str(port): {
            "expected_open": expected,
            "observed_open": _port_open(port),
        }
        for port, expected in PORT_EXPECTATIONS.items()
    }
    authority = json.loads(AUTHORITY_PROFILE.read_text(encoding="utf-8"))
    healthy = (
        alignment.get("aligned") is True
        and manifest["state"] == "PASS"
        and all(services.values())
        and all(
            item["expected_open"] == item["observed_open"]
            for item in ports.values()
        )
    )
    return {
        "schema_id": "W7TP_XIAOJ_SCHEDULED_HEALTH_OBSERVATION_V2_3",
        "state": "HEALTHY" if healthy else "DRIFT",
        "decision_engine": "8D_ADI",
        "model_role": "PASSIVE_HEALTH_ENGINEERING_ORGAN",
        "alignment": alignment,
        "source_manifest": manifest,
        "services": services,
        "ports": ports,
        "d8_authority": {
            "state": authority.get("state", "UNKNOWN"),
            "active": authority.get("active") is True,
        },
        "external_effect": False,
        "reobservation": True,
    }


def invoke_model_on_drift(observation: dict[str, Any]) -> dict[str, Any]:
    packet = {
        "schema_id": "W7TP_MINIMUM_REDACTED_HEALTH_DRIFT_PACKET_V2_3",
        "state": observation["state"],
        "alignment": observation["alignment"],
        "source_manifest": observation["source_manifest"],
        "services": observation["services"],
        "ports": observation["ports"],
        "instruction": "以紅隊找出失敗座標，再以紫隊收斂唯一最短唯讀診斷；不得宣稱修復或執行。",
    }
    request = urllib.request.Request(
        OLLAMA_GENERATE_URL,
        data=json.dumps(
            {
                "model": "xiaoj:latest",
                "prompt": json.dumps(packet, ensure_ascii=False, separators=(",", ":")),
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 256},
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
        text = str(result.get("response") or "")
        return {
            "invoked": True,
            "state": "MODEL_ANALYSIS_RETURNED",
            "response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "response_preview": text[:500],
            "external_effect": False,
        }
    except (OSError, TimeoutError, ValueError, urllib.error.URLError) as exc:
        return {
            "invoked": True,
            "state": "MODEL_ANALYSIS_UNAVAILABLE",
            "error_type": type(exc).__name__,
            "external_effect": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-model", action="store_true")
    args = parser.parse_args()
    observation = build_health_observation()
    observation["model_analysis"] = (
        {"invoked": False, "reason": "NO_DRIFT"}
        if observation["state"] == "HEALTHY"
        else (
            {"invoked": False, "reason": "DISABLED_FOR_THIS_RUN"}
            if args.no_model
            else invoke_model_on_drift(observation)
        )
    )
    print(json.dumps(observation, ensure_ascii=False, sort_keys=True))
    return 0 if observation["state"] == "HEALTHY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
