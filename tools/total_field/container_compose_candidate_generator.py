"""Generate a candidate-only compose document from Total Field container map.

This generator is source-only and dry-run only:
- no docker compose up
- no docker compose down
- no restart
- no deploy
- no DB write
- no volume creation
- no live URL creation
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping


FORBIDDEN_RUNTIME_ACTIONS = {
    "docker compose up",
    "docker compose down",
    "docker compose restart",
    "docker system prune",
    "docker volume rm",
    "database migration",
    "router write",
    "live url create",
    "payment capture",
}


def load_candidate_map(path: str | Path) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("mode") != "candidate_only_no_deploy":
        raise ValueError("candidate map must be candidate_only_no_deploy")
    return data


def _assert_policy_safe(data: Mapping[str, Any]) -> None:
    policy = dict(data.get("policy") or {})
    required_false = [
        "delete",
        "restore",
        "deploy",
        "restart",
        "db_write",
        "router_write",
        "web_touch",
        "runtime_bulk_output",
        "production_activation",
    ]
    bad = [key for key in required_false if policy.get(key) is not False]
    if bad:
        raise ValueError("unsafe policy: " + ",".join(bad))


def _assert_services_safe(data: Mapping[str, Any]) -> None:
    compose = dict(data.get("compose_candidate") or {})
    services = dict(compose.get("services") or {})
    bad = []

    for name, service in services.items():
        item = dict(service or {})
        if item.get("create_now") is not False:
            bad.append(f"{name}:create_now")
        if item.get("restart_now") is not False:
            bad.append(f"{name}:restart_now")
        if item.get("authority_inside_container") is not False:
            bad.append(f"{name}:authority_inside_container")

    if bad:
        raise ValueError("unsafe service: " + ",".join(bad))


def verify_candidate_map(data: Mapping[str, Any]) -> Dict[str, Any]:
    _assert_policy_safe(data)
    _assert_services_safe(data)

    forbidden = set(data.get("forbidden_runtime_actions") or [])
    missing_forbidden = sorted(FORBIDDEN_RUNTIME_ACTIONS - forbidden)
    if missing_forbidden:
        raise ValueError("missing forbidden runtime actions: " + ",".join(missing_forbidden))

    compose = dict(data.get("compose_candidate") or {})
    services = dict(compose.get("services") or {})
    volumes = dict(compose.get("volumes") or {})
    networks = dict(compose.get("networks") or {})

    return {
        "decision": "PASS_CANDIDATE_MAP_SAFE_FOR_DRY_GENERATION",
        "service_count": len(services),
        "volume_count": len(volumes),
        "network_count": len(networks),
        "deployable_now": compose.get("deployable_now") is True,
    }


def generate_compose_candidate(data: Mapping[str, Any]) -> Dict[str, Any]:
    verification = verify_candidate_map(data)
    compose = dict(data.get("compose_candidate") or {})

    services = {}
    for name, service in dict(compose.get("services") or {}).items():
        item = dict(service or {})
        services[name] = {
            "image": item.get("image_or_build", "candidate_only"),
            "container_name": item.get("candidate_service_name", name),
            "profiles": ["candidate-only-no-deploy"],
            "labels": {
                "w7tp.authority_inside_container": "false",
                "w7tp.create_now": "false",
                "w7tp.restart_now": "false",
                "w7tp.total_field_required": "true",
            },
            "x-w7tp-role": item.get("container_role", "candidate_service"),
            "x-w7tp-authority-inside-container": False,
            "x-w7tp-create-now": False,
            "x-w7tp-restart-now": False,
            "x-w7tp-volumes-required": item.get("volumes_required", []),
            "depends_on": item.get("depends_on", []),
        }

    volumes = {}
    for name, volume in dict(compose.get("volumes") or {}).items():
        item = dict(volume or {})
        volumes[name] = {
            "external": True,
            "x-w7tp-persistent": bool(item.get("persistent")),
            "x-w7tp-create-now": False,
            "x-w7tp-externalized-authority": bool(item.get("externalized_authority", False)),
        }

    networks = {}
    for name, network in dict(compose.get("networks") or {}).items():
        item = dict(network or {})
        networks[name] = {
            "external": True,
            "x-w7tp-type": item.get("type", "private_network_candidate"),
            "x-w7tp-create-now": False,
        }

    return {
        "state": "CONTAINER_COMPOSE_GENERATED_CANDIDATE_ONLY_NO_DEPLOY",
        "version": "3.9",
        "name": compose.get("project_name", "w7tp_total_field_candidate"),
        "x-w7tp-policy": {
            "candidate_only": True,
            "deploy": False,
            "restart": False,
            "db_write": False,
            "router_write": False,
            "production_activation": False,
        },
        "x-w7tp-verification": verification,
        "services": services,
        "volumes": volumes,
        "networks": networks,
    }


def to_yaml_like(value: Any, indent: int = 0) -> str:
    space = " " * indent

    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{space}{key}:")
                lines.append(to_yaml_like(item, indent + 2))
            else:
                lines.append(f"{space}{key}: {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(lines)

    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{space}-")
                lines.append(to_yaml_like(item, indent + 2))
            else:
                lines.append(f"{space}- {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(lines)

    return f"{space}{json.dumps(value, ensure_ascii=False)}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--map",
        default="configs/total_field/container_compose_candidate_map.json",
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="json",
    )
    args = parser.parse_args()

    data = load_candidate_map(args.map)
    candidate = generate_compose_candidate(data)

    if args.format == "yaml":
        print(to_yaml_like(candidate))
    else:
        print(json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
