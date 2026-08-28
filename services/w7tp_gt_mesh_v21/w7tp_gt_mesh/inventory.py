"""Bounded node/container/service/listener/file metadata Domain Profile probes."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import socket
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from .core import (
    SNAPSHOT_SCHEMA,
    MeshHold,
    canonical_binding,
    safe_component,
    utc_now,
    utc_text,
)


def _run(command: Sequence[str], *, timeout_seconds: int = 8) -> tuple[str, str]:
    """Run one exact argv probe and expose no raw failure payload."""

    try:
        result = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
        )
    except FileNotFoundError:
        return "UNKNOWN", "EXECUTABLE_NOT_FOUND"
    except subprocess.TimeoutExpired:
        return "UNKNOWN", "PROBE_TIMEOUT"
    except OSError:
        return "UNKNOWN", "PROBE_UNAVAILABLE"
    if result.returncode != 0:
        return "UNKNOWN", f"PROBE_EXIT_{result.returncode}"
    return result.stdout, "OBSERVED"


def _service_metadata(names: Sequence[object]) -> tuple[list[dict[str, object]], dict[str, object]]:
    services: list[dict[str, object]] = []
    failures = 0
    system = platform.system()
    for raw_name in names:
        if isinstance(raw_name, str):
            name = safe_component(raw_name, code="HOLD_SERVICE_NAME_INVALID")
            scope = "system"
        elif isinstance(raw_name, Mapping):
            name = safe_component(raw_name.get("name"), code="HOLD_SERVICE_NAME_INVALID")
            scope = raw_name.get("scope", "system")
            if scope not in {"system", "user"}:
                raise MeshHold("HOLD_SERVICE_SCOPE_INVALID")
        else:
            raise MeshHold("HOLD_SERVICE_SPEC_INVALID")
        if system == "Windows":
            if scope == "user":
                failures += 1
                services.append({"service_id": name, "scope": scope, "observation_state": "UNKNOWN", "reason_code": "WINDOWS_USER_SERVICE_SCOPE_UNSUPPORTED"})
                continue
            output, state = _run(["sc.exe", "query", name])
            if state != "OBSERVED":
                failures += 1
                services.append({"service_id": name, "scope": scope, "observation_state": "UNKNOWN", "reason_code": state})
                continue
            values: dict[str, str] = {}
            for line in output.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    values[key.strip().lower()] = value.strip()
            services.append(
                {
                    "service_id": name,
                    "scope": scope,
                    "observation_state": "OBSERVED",
                    "load_state": "WINDOWS_SERVICE_MANAGER",
                    "active_state": values.get("state", "UNKNOWN"),
                    "sub_state": "UNKNOWN",
                    "main_pid": None,
                }
            )
        else:
            command = ["systemctl"]
            if scope == "user":
                command.append("--user")
            command.extend(
                [
                    "show",
                    name,
                    "--no-pager",
                    "--property=Id,LoadState,ActiveState,SubState,UnitFileState,MainPID",
                ]
            )
            output, state = _run(command)
            if state != "OBSERVED":
                failures += 1
                services.append({"service_id": name, "scope": scope, "observation_state": "UNKNOWN", "reason_code": state})
                continue
            values = {}
            for line in output.splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    values[key] = value
            pid_text = values.get("MainPID", "")
            services.append(
                {
                    "service_id": values.get("Id") or name,
                    "scope": scope,
                    "observation_state": "OBSERVED",
                    "load_state": values.get("LoadState", "UNKNOWN"),
                    "active_state": values.get("ActiveState", "UNKNOWN"),
                    "sub_state": values.get("SubState", "UNKNOWN"),
                    "unit_file_state": values.get("UnitFileState", "UNKNOWN"),
                    "main_pid": int(pid_text) if pid_text.isdigit() else None,
                }
            )
    return services, {
        "probe": "service_manager_metadata",
        "state": "OBSERVED" if failures == 0 else "PARTIAL_UNKNOWN",
        "requested": len(names),
        "unknown": failures,
    }


def _container_metadata(config: Mapping[str, object]) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, object],
]:
    if not config.get("enabled", True):
        return [], [], [], [], {"probe": "container_metadata", "state": "DISABLED", "requested": 0, "unknown": 0}
    engines = config.get("engines", ["docker", "podman"])
    if not isinstance(engines, list):
        raise MeshHold("HOLD_CONTAINER_ENGINES_INVALID")
    requested_names = config.get("names", [])
    if not isinstance(requested_names, list):
        raise MeshHold("HOLD_CONTAINER_NAMES_INVALID")
    wanted = {safe_component(name, code="HOLD_CONTAINER_NAME_INVALID") for name in requested_names}
    for raw_engine in engines:
        engine = safe_component(raw_engine, code="HOLD_CONTAINER_ENGINE_INVALID")
        if shutil.which(engine) is None:
            continue
        output, state = _run([engine, "ps", "--all", "--no-trunc", "--format", "{{json .}}"])
        if state != "OBSERVED":
            return [], [], [], [], {"probe": "container_metadata", "state": "UNKNOWN", "reason_code": state, "requested": len(wanted), "unknown": len(wanted)}
        records: list[dict[str, object]] = []
        import json

        for line in output.splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            name = str(item.get("Names") or item.get("Name") or "")
            if wanted and name not in wanted:
                continue
            container_id = str(item.get("ID") or item.get("Id") or "UNKNOWN")
            records.append(
                {
                    "container_id": container_id,
                    "name": name or "UNKNOWN",
                    "image_ref": str(item.get("Image") or "UNKNOWN"),
                    "state": str(item.get("State") or "UNKNOWN"),
                    "status": str(item.get("Status") or "UNKNOWN"),
                    "ports": str(item.get("Ports") or ""),
                    "engine": engine,
                    "observation_state": "OBSERVED_METADATA_ONLY",
                }
            )
        def json_rows(command: list[str], fields: Mapping[str, str]) -> tuple[list[dict[str, object]], str]:
            raw_rows, row_state = _run(command)
            if row_state != "OBSERVED":
                return [], row_state
            parsed_rows: list[dict[str, object]] = []
            for raw_line in raw_rows.splitlines():
                try:
                    raw_item = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                parsed_rows.append(
                    {
                        target: str(raw_item.get(source) or "UNKNOWN")
                        for target, source in fields.items()
                    }
                    | {"observation_state": "OBSERVED_METADATA_ONLY", "engine": engine}
                )
            return parsed_rows, "OBSERVED"

        images, image_state = json_rows(
            [engine, "images", "--no-trunc", "--format", "{{json .}}"],
            {"image_id": "ID", "repository": "Repository", "tag": "Tag", "digest": "Digest", "size": "Size"},
        )
        volumes, volume_state = json_rows(
            [engine, "volume", "ls", "--format", "{{json .}}"],
            {"volume_name": "Name", "driver": "Driver", "scope": "Scope"},
        )
        networks, network_state = json_rows(
            [engine, "network", "ls", "--no-trunc", "--format", "{{json .}}"],
            {"network_id": "ID", "network_name": "Name", "driver": "Driver", "scope": "Scope"},
        )
        return records, images, volumes, networks, {
            "probe": "container_metadata",
            "state": "OBSERVED",
            "engine": engine,
            "requested": len(wanted),
            "unknown": 0,
            "subobject_states": {"images": image_state, "volumes": volume_state, "networks": network_state},
        }
    return [], [], [], [], {"probe": "container_metadata", "state": "UNKNOWN", "reason_code": "NO_CONTAINER_ENGINE", "requested": len(wanted), "unknown": len(wanted)}


_LISTEN_ADDRESS = re.compile(r"^(?P<host>.+):(?P<port>[0-9]+)$")


def _listener_metadata(enabled: bool) -> tuple[list[dict[str, object]], dict[str, object]]:
    if not enabled:
        return [], {"probe": "listener_metadata", "state": "DISABLED"}
    if platform.system() == "Windows":
        output, state = _run(["netstat", "-ano"])
        if state != "OBSERVED":
            return [], {"probe": "listener_metadata", "state": "UNKNOWN", "reason_code": state}
        records = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 4 or parts[0].upper() not in {"TCP", "UDP"}:
                continue
            protocol = parts[0].upper()
            is_listen = protocol == "UDP" or "LISTEN" in line.upper()
            if not is_listen:
                continue
            local = parts[1]
            pid_text = parts[-1]
            match = _LISTEN_ADDRESS.match(local)
            records.append(
                {
                    "protocol": protocol,
                    "local_address": match.group("host") if match else local,
                    "local_port": int(match.group("port")) if match else None,
                    "pid": int(pid_text) if pid_text.isdigit() else None,
                    "process_name": None,
                    "observation_state": "OBSERVED_METADATA_ONLY",
                }
            )
        return records, {"probe": "listener_metadata", "state": "OBSERVED", "count": len(records)}
    output, state = _run(["ss", "-H", "-lntup"])
    if state != "OBSERVED":
        return [], {"probe": "listener_metadata", "state": "UNKNOWN", "reason_code": state}
    records = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        protocol = parts[0].upper()
        local = parts[4]
        match = _LISTEN_ADDRESS.match(local)
        process_text = " ".join(parts[6:]) if len(parts) > 6 else ""
        pid_match = re.search(r"pid=([0-9]+)", process_text)
        name_match = re.search(r'\(\("([^"]+)"', process_text)
        records.append(
            {
                "protocol": protocol,
                "local_address": match.group("host") if match else local,
                "local_port": int(match.group("port")) if match else None,
                "pid": int(pid_match.group(1)) if pid_match else None,
                "process_name": name_match.group(1) if name_match else None,
                "observation_state": "OBSERVED_METADATA_ONLY",
            }
        )
    return records, {"probe": "listener_metadata", "state": "OBSERVED", "count": len(records)}


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_record(path: Path, *, logical_root: Path, include_sha256: bool) -> dict[str, object]:
    metadata = path.lstat()
    if path.is_symlink():
        kind = "SYMLINK_METADATA_ONLY"
    elif stat.S_ISREG(metadata.st_mode):
        kind = "FILE"
    elif stat.S_ISDIR(metadata.st_mode):
        kind = "DIRECTORY"
    else:
        kind = "OTHER"
    try:
        relative = path.relative_to(logical_root).as_posix()
    except ValueError:
        relative = path.name
    record: dict[str, object] = {
        "logical_path": relative,
        "path_kind": kind,
        "size_bytes": metadata.st_size,
        "modified_time_ns": metadata.st_mtime_ns,
        "mode": stat.S_IMODE(metadata.st_mode),
        "content_sha256": None,
        "content_identity_state": "METADATA_ONLY",
    }
    if include_sha256 and kind == "FILE":
        record["content_sha256"] = _hash_file(path)
        record["content_identity_state"] = "HASHED_EXPLICIT_CURATED_PATH"
    return record


def _curated_files(items: Sequence[object]) -> tuple[list[dict[str, object]], dict[str, object]]:
    records: list[dict[str, object]] = []
    unknown = 0
    for raw in items:
        if not isinstance(raw, Mapping):
            raise MeshHold("HOLD_CURATED_FILE_SPEC_INVALID")
        raw_path = raw.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise MeshHold("HOLD_CURATED_FILE_PATH_INVALID")
        path = Path(raw_path).expanduser()
        if any(part == ".git" for part in path.parts):
            raise MeshHold("HOLD_CURATED_GIT_INTERNAL_PATH_FORBIDDEN")
        if not path.exists() and not path.is_symlink():
            records.append({"logical_path": raw_path, "observation_state": "UNKNOWN", "reason_code": "PATH_NOT_FOUND"})
            unknown += 1
            continue
        include_sha256 = raw.get("include_sha256", False) is True
        recursive = raw.get("recursive", False) is True
        max_entries = raw.get("max_entries", 1024)
        if isinstance(max_entries, bool) or not isinstance(max_entries, int) or not 1 <= max_entries <= 100_000:
            raise MeshHold("HOLD_CURATED_FILE_BUDGET_INVALID")
        logical_root = path if path.is_dir() else path.parent
        candidates = [path]
        if recursive and path.is_dir() and not path.is_symlink():
            candidates.extend(
                candidate
                for candidate in path.rglob("*")
                if ".git" not in candidate.parts
            )
        for candidate in candidates[:max_entries]:
            try:
                records.append(_file_record(candidate, logical_root=logical_root, include_sha256=include_sha256))
            except OSError:
                records.append({"logical_path": candidate.name, "observation_state": "UNKNOWN", "reason_code": "METADATA_READ_FAILED"})
                unknown += 1
        if len(candidates) > max_entries:
            unknown += len(candidates) - max_entries
    records.sort(key=lambda item: str(item.get("logical_path", "")))
    return records, {"probe": "curated_file_metadata", "state": "OBSERVED" if unknown == 0 else "PARTIAL_UNKNOWN", "count": len(records), "unknown": unknown}


def _remote_locator(remote_url: str) -> dict[str, object]:
    parsed = urlsplit(remote_url)
    if parsed.scheme:
        host = parsed.hostname or ""
        transport = parsed.scheme.lower()
        safe_locator = f"{transport}://{host}{parsed.path}"
    elif ":" in remote_url and "@" in remote_url.split(":", 1)[0]:
        transport = "ssh-scp-like"
        host_part, path = remote_url.split(":", 1)
        host = host_part.rsplit("@", 1)[-1]
        safe_locator = f"ssh://{host}/{path.lstrip('/')}"
    else:
        transport = "local-or-unknown"
        host = ""
        safe_locator = remote_url
    return {
        "transport": transport,
        "host": host,
        "remote_locator_sha256": hashlib.sha256(safe_locator.encode("utf-8")).hexdigest(),
    }


def _git_evidence(roots: Sequence[object]) -> tuple[list[dict[str, object]], dict[str, object]]:
    evidence: list[dict[str, object]] = []
    unknown = 0
    executable = shutil.which("git")
    if executable is None and roots:
        return [], {"probe": "git_d4_evidence", "state": "UNKNOWN", "reason_code": "GIT_EXECUTABLE_NOT_FOUND", "requested": len(roots), "unknown": len(roots)}
    for raw in roots:
        if isinstance(raw, str):
            root_text = raw
            include_untracked = True
        elif isinstance(raw, Mapping) and isinstance(raw.get("path"), str):
            root_text = str(raw["path"])
            include_untracked = raw.get("include_untracked", True) is True
        else:
            raise MeshHold("HOLD_GIT_EVIDENCE_ROOT_INVALID")
        root = str(Path(root_text).expanduser())
        top, top_state = _run([str(executable), "-C", root, "rev-parse", "--show-toplevel"])
        if top_state != "OBSERVED":
            unknown += 1
            evidence.append(
                {
                    "dimension": "D4_EVIDENCE",
                    "authority_state": "EVIDENCE_ONLY",
                    "live_effect_state": "NOT_ESTABLISHED_BY_GIT",
                    "root": root,
                    "observation_state": "UNKNOWN",
                    "reason_code": top_state,
                    "dirty_is_blocker": False,
                }
            )
            continue
        branch, branch_state = _run([str(executable), "-C", root, "symbolic-ref", "--quiet", "--short", "HEAD"])
        head, head_state = _run([str(executable), "-C", root, "rev-parse", "HEAD"])
        remote_names, remote_state = _run([str(executable), "-C", root, "remote"])
        status_command = [str(executable), "-C", root, "status", "--porcelain=v1"]
        status_command.append("--untracked-files=normal" if include_untracked else "--untracked-files=no")
        dirty_output, dirty_state = _run(status_command, timeout_seconds=20)
        remotes: list[dict[str, object]] = []
        if remote_state == "OBSERVED":
            for remote_name in sorted(filter(None, (line.strip() for line in remote_names.splitlines()))):
                if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", remote_name):
                    continue
                remote_url, url_state = _run([str(executable), "-C", root, "remote", "get-url", remote_name])
                if url_state == "OBSERVED":
                    remotes.append({"remote_name": remote_name, **_remote_locator(remote_url.strip())})
                else:
                    remotes.append({"remote_name": remote_name, "observation_state": "UNKNOWN", "reason_code": url_state})
        evidence.append(
            {
                "dimension": "D4_EVIDENCE",
                "authority_state": "EVIDENCE_ONLY",
                "live_effect_state": "NOT_ESTABLISHED_BY_GIT",
                "root": top.strip(),
                "branch": branch.strip() if branch_state == "OBSERVED" else "DETACHED_OR_UNKNOWN",
                "head": head.strip() if head_state == "OBSERVED" else "UNKNOWN",
                "remotes": remotes,
                "diff_count": len([line for line in dirty_output.splitlines() if line]) if dirty_state == "OBSERVED" else None,
                "include_untracked": include_untracked,
                "observation_state": "OBSERVED" if head_state == "OBSERVED" and dirty_state == "OBSERVED" else "PARTIAL_UNKNOWN",
                "dirty_is_blocker": False,
                "authority_effect": "NONE",
            }
        )
    return evidence, {"probe": "git_d4_evidence", "state": "OBSERVED" if unknown == 0 else "PARTIAL_UNKNOWN", "requested": len(roots), "unknown": unknown}


def _node_resources(config: Mapping[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    cpu_model = platform.processor().strip()
    if not cpu_model and Path("/proc/cpuinfo").is_file():
        try:
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
                if line.lower().startswith("model name") and ":" in line:
                    cpu_model = line.split(":", 1)[1].strip()
                    break
        except OSError:
            pass
    ram_total: int | None = None
    ram_available: int | None = None
    if Path("/proc/meminfo").is_file():
        try:
            values: dict[str, int] = {}
            for line in Path("/proc/meminfo").read_text(encoding="ascii", errors="replace").splitlines():
                parts = line.replace(":", "").split()
                if len(parts) >= 2 and parts[1].isdigit():
                    values[parts[0]] = int(parts[1]) * 1024
            ram_total = values.get("MemTotal")
            ram_available = values.get("MemAvailable")
        except OSError:
            pass
    disk_roots = config.get("disk_roots", [config.get("runtime_root")])
    if not isinstance(disk_roots, list):
        raise MeshHold("HOLD_DISK_ROOTS_INVALID")
    disks: list[dict[str, object]] = []
    for raw_root in disk_roots:
        if not isinstance(raw_root, str) or not raw_root:
            continue
        root = Path(raw_root).expanduser()
        try:
            usage = shutil.disk_usage(root if root.exists() else root.parent)
            disks.append(
                {
                    "root": str(root),
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "observation_state": "OBSERVED_METADATA_ONLY",
                }
            )
        except OSError:
            disks.append({"root": str(root), "observation_state": "UNKNOWN", "reason_code": "DISK_USAGE_UNAVAILABLE"})
    gpus: list[dict[str, object]] = []
    gpu_state = "UNKNOWN"
    if shutil.which("nvidia-smi"):
        output, gpu_probe = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
        if gpu_probe == "OBSERVED":
            for ordinal, line in enumerate(output.splitlines()):
                if "," not in line:
                    continue
                model, memory = (part.strip() for part in line.split(",", 1))
                gpus.append(
                    {
                        "gpu_ordinal": ordinal,
                        "model": model,
                        "memory_total_mib": int(memory) if memory.isdigit() else None,
                        "observation_state": "OBSERVED_METADATA_ONLY",
                    }
                )
            gpu_state = "OBSERVED" if gpus else "UNKNOWN"
    try:
        addresses = sorted(
            {
                item[4][0]
                for item in socket.getaddrinfo(socket.gethostname(), None)
                if isinstance(item[4], tuple) and item[4]
            }
        )
    except socket.gaierror:
        addresses = []
    tailscale_addresses: list[str] = []
    tailscale_state = "UNKNOWN"
    if shutil.which("tailscale"):
        output, tailscale_state = _run(["tailscale", "ip", "-4"])
        if tailscale_state == "OBSERVED":
            tailscale_addresses = sorted(line.strip() for line in output.splitlines() if line.strip())
    virtualization: list[str] = []
    if Path("/.dockerenv").exists():
        virtualization.append("CONTAINER_DOCKER_MARKER_OBSERVED")
    if Path("/proc/version").is_file():
        try:
            version = Path("/proc/version").read_text(encoding="utf-8", errors="replace").lower()
            if "microsoft" in version or "wsl" in version:
                virtualization.append("WSL_KERNEL_MARKER_OBSERVED")
        except OSError:
            pass
    if shutil.which("systemd-detect-virt"):
        output, virt_state = _run(["systemd-detect-virt"])
        if virt_state == "OBSERVED" and output.strip() and output.strip() != "none":
            virtualization.append(f"SYSTEMD_DETECT_VIRT:{output.strip()}")
    resources = {
        "cpu": {
            "logical_count": os.cpu_count(),
            "model": cpu_model or "UNKNOWN",
            "observation_state": "OBSERVED_METADATA_ONLY" if os.cpu_count() is not None else "UNKNOWN",
        },
        "ram": {
            "total_bytes": ram_total,
            "available_bytes": ram_available,
            "observation_state": "OBSERVED_METADATA_ONLY" if ram_total is not None else "UNKNOWN",
        },
        "disks": disks,
        "gpus": gpus,
        "gpu_observation_state": gpu_state,
        "network": {
            "ip_addresses": addresses,
            "tailscale_addresses": tailscale_addresses,
            "tailscale_observation_state": tailscale_state,
        },
        "virtualization_evidence": virtualization,
        "virtualization_observation_state": "OBSERVED_METADATA_ONLY" if virtualization else "UNKNOWN",
    }
    return resources, {"probe": "node_resource_metadata", "state": "OBSERVED_WITH_EXPLICIT_UNKNOWNS"}


def _tailscale_peer_topology(config: Mapping[str, object]) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Read a bounded, safe-field-only peer view from the local carrier."""

    limit = config.get("tailscale_peer_limit", 256)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 4096:
        raise MeshHold("HOLD_TAILSCALE_PEER_LIMIT_INVALID")
    if shutil.which("tailscale") is None:
        return [], {
            "probe": "tailscale_peer_topology",
            "state": "UNKNOWN",
            "reason_code": "TAILSCALE_EXECUTABLE_NOT_FOUND",
            "count": 0,
        }
    output, state = _run(["tailscale", "status", "--json"], timeout_seconds=10)
    if state != "OBSERVED":
        return [], {"probe": "tailscale_peer_topology", "state": "UNKNOWN", "reason_code": state, "count": 0}
    if len(output.encode("utf-8")) > 4 * 1024 * 1024:
        return [], {
            "probe": "tailscale_peer_topology",
            "state": "UNKNOWN",
            "reason_code": "TAILSCALE_STATUS_OUTPUT_TOO_LARGE",
            "count": 0,
        }
    try:
        document = json.loads(output)
    except json.JSONDecodeError:
        return [], {
            "probe": "tailscale_peer_topology",
            "state": "UNKNOWN",
            "reason_code": "TAILSCALE_STATUS_JSON_INVALID",
            "count": 0,
        }
    peers = document.get("Peer") if isinstance(document, Mapping) else None
    if peers is None:
        peers = {}
    if not isinstance(peers, Mapping):
        return [], {
            "probe": "tailscale_peer_topology",
            "state": "UNKNOWN",
            "reason_code": "TAILSCALE_PEER_MAP_INVALID",
            "count": 0,
        }
    records: list[dict[str, object]] = []
    for ordinal, raw_peer in enumerate(peers.values()):
        if ordinal >= limit:
            break
        if not isinstance(raw_peer, Mapping):
            continue
        raw_addresses = raw_peer.get("TailscaleIPs")
        addresses = (
            sorted(str(value) for value in raw_addresses[:16] if isinstance(value, str) and value)
            if isinstance(raw_addresses, list)
            else []
        )

        def text_or_unknown(key: str) -> str:
            value = raw_peer.get(key)
            return value if isinstance(value, str) and value else "UNKNOWN"

        def bool_or_unknown(key: str) -> bool | str:
            value = raw_peer.get(key)
            return value if isinstance(value, bool) else "UNKNOWN"

        values = {
            "node_id": text_or_unknown("ID"),
            "node_name": text_or_unknown("HostName"),
            "dns_name": text_or_unknown("DNSName"),
            "operating_system": text_or_unknown("OS"),
            "addresses": addresses,
            "online": bool_or_unknown("Online"),
            "active": bool_or_unknown("Active"),
            "key_expiry": text_or_unknown("KeyExpiry"),
        }
        values["observation_state"] = (
            "OBSERVED"
            if addresses and all(value != "UNKNOWN" for key, value in values.items() if key != "addresses")
            else "OBSERVED_WITH_EXPLICIT_UNKNOWNS"
        )
        records.append(values)
    records.sort(key=lambda item: (str(item["node_id"]), str(item["dns_name"]), str(item["node_name"])))
    truncated = len(peers) > limit
    return records, {
        "probe": "tailscale_peer_topology",
        "state": "OBSERVED_TRUNCATED" if truncated else "OBSERVED",
        "count": len(records),
        "configured_limit": limit,
        "truncated": truncated,
    }


def collect_snapshot(config: Mapping[str, object], *, logical_time: int) -> dict[str, object]:
    """Collect a bounded, metadata-only node state snapshot."""

    node_id = safe_component(config.get("node_id"), code="HOLD_NODE_ID_INVALID")
    logical_root_id = safe_component(config.get("logical_root_id"), code="HOLD_LOGICAL_ROOT_ID_INVALID")
    services_raw = config.get("services", [])
    curated_raw = config.get("curated_files", [])
    git_roots = config.get("git_evidence_roots", [])
    container_config = config.get("containers", {})
    listeners_config = config.get("listeners", {})
    if not isinstance(services_raw, list) or not isinstance(curated_raw, list) or not isinstance(git_roots, list):
        raise MeshHold("HOLD_INVENTORY_CONFIG_INVALID")
    if not isinstance(container_config, Mapping) or not isinstance(listeners_config, Mapping):
        raise MeshHold("HOLD_INVENTORY_CONFIG_INVALID")
    now = utc_now()
    services, service_probe = _service_metadata(services_raw)
    containers, container_images, container_volumes, container_networks, container_probe = _container_metadata(container_config)
    listeners, listener_probe = _listener_metadata(listeners_config.get("enabled", True) is True)
    curated_files, file_probe = _curated_files(curated_raw)
    git_evidence, git_probe = _git_evidence(git_roots)
    resources, resource_probe = _node_resources(config)
    discovered_nodes, tailscale_peer_probe = _tailscale_peer_topology(config)
    return {
        "schema_id": SNAPSHOT_SCHEMA,
        "canonical_id": "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1",
        "version": "2.1",
        "canonical_binding": canonical_binding(),
        "domain_profile": "NODE_CONTAINER_SERVICE_LISTENER_CURATED_FILE_METADATA",
        "source_node_ref": f"node:{node_id}",
        "logical_root_id": logical_root_id,
        "logical_time": logical_time,
        "observed_at": utc_text(now),
        "node": {
            "node_id": node_id,
            "hostname": socket.gethostname(),
            "platform_system": platform.system(),
            "platform_release": platform.release(),
            "machine": platform.machine(),
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "process_id": os.getpid(),
            "executable_name": Path(sys.executable).name,
            "observation_state": "OBSERVED_METADATA_ONLY",
        },
        "services": services,
        "containers": containers,
        "container_images": container_images,
        "container_volumes": container_volumes,
        "container_networks": container_networks,
        "listeners": listeners,
        "curated_files": curated_files,
        "git_evidence": git_evidence,
        "resources": resources,
        "discovered_nodes": discovered_nodes,
        "probe_evidence": [service_probe, container_probe, listener_probe, file_probe, git_probe, resource_probe, tailscale_peer_probe],
        "authority_state": "EVIDENCE_ONLY",
        "live_effect_state": "NOT_ESTABLISHED_BY_METADATA",
        "runtime_integrity_boundary": "NO_SECRET_OR_PRIVATE_LOOKUP_CONTENT_READ_BY_DEFAULT",
    }
