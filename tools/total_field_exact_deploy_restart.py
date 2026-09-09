#!/usr/bin/env python3
"""Deploy the exact reviewed MSI WSL gateway bundle and reobserve it."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field_mandatory_application_gate import PASS_STATE, scan_operation

CONFIG_REL = Path("configs/total_field/git_push_review_gate_v1.json")
DEPLOY_SCOPE = "AUTHORIZE_EXACT_DEPLOY_RESTART"
PASS_DEPLOY = "PASS_EXACT_DEPLOY_RESTART_REOBSERVED"
HOLD_DEPLOY = "HOLD_EXACT_DEPLOY_RESTART"


class ExactDeployRejected(RuntimeError):
    pass


def _run(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ExactDeployRejected("DEPLOY_COMMAND_FAILED")
    return completed.stdout.strip()


def _git(root: Path, *args: str) -> str:
    return _run(["git", "-C", str(root), *args])


def _load(root: Path, deployment_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        config = json.loads((root / CONFIG_REL).read_text(encoding="utf-8"))
        passkey = config["passkey_verifier"]
        admitted = passkey["admitted_deployments"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ExactDeployRejected("DEPLOYMENT_REGISTRY_INVALID") from exc
    matches = [
        item
        for item in admitted
        if isinstance(item, dict) and item.get("deployment_id") == deployment_id
    ]
    if len(matches) != 1:
        raise ExactDeployRejected("DEPLOYMENT_NOT_ADMITTED")
    return passkey, matches[0]


def _authority(root: Path, passkey: Mapping[str, Any], *, consume: bool) -> dict[str, Any]:
    runtime = passkey.get("python_runtime")
    if not isinstance(runtime, str) or not Path(runtime).is_absolute():
        raise ExactDeployRejected("PASSKEY_RUNTIME_INVALID")
    command = [
        runtime,
        str(root / "tools/total_field_passkey_d8.py"),
        "--repo-root",
        str(root),
        "--gate-config",
        CONFIG_REL.as_posix(),
        "--required-scope",
        DEPLOY_SCOPE,
    ]
    if consume:
        command.append("--consume")
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ExactDeployRejected("PASSKEY_RESULT_INVALID") from exc
    if result.get("authority_verified") is not True:
        raise ExactDeployRejected(str(result.get("reason") or "DEPLOY_AUTHORITY_NOT_RESOLVED"))
    return result


def _health(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return False
    return response.status == 200 and payload.get("state") == "PASS_GATEWAY_PROCESS"


def _wait_health(port: int, timeout_seconds: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _health(port):
            return
        time.sleep(0.25)
    raise ExactDeployRejected("GATEWAY_HEALTH_REOBSERVATION_FAILED")


def _canary(root: Path, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise ExactDeployRejected("CANARY_PORT_IN_USE") from exc
    environment = dict(os.environ)
    environment["TAIJI_PROJECT_ROOT"] = str(root)
    process = subprocess.Popen(
        [
            "/usr/bin/python3",
            "-m",
            "uvicorn",
            "services.gateway.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=root,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_health(port)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _write_receipt(root: Path, authority_sha256: str, head: str, payload: Mapping[str, Any]) -> Path:
    path = root / "runtime/total_field/deploy_receipts" / authority_sha256 / f"{head}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    if path.exists():
        if path.is_symlink() or path.read_bytes() != encoded:
            raise ExactDeployRejected("DEPLOY_RECEIPT_COLLISION")
        return path
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def exact_deploy_restart(repo_root: str | Path, deployment_id: str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    created_links: list[Path] = []
    effects_started = False
    authority_consumed = False
    previous_gateway_enabled = ""
    previous_gateway_active = ""
    previous_timer_enabled = ""
    previous_timer_active = ""
    try:
        passkey, deployment = _load(root, deployment_id)
        if root.as_posix() != deployment["repository_root"]:
            raise ExactDeployRejected("REPOSITORY_ROOT_DRIFT")
        branch = _git(root, "branch", "--show-current")
        head = _git(root, "rev-parse", "HEAD")
        tree = _git(root, "rev-parse", "HEAD^{tree}")
        if _git(root, "status", "--porcelain", "--untracked-files=all"):
            raise ExactDeployRejected("DIRTY_WORKTREE_BLOCKED")
        resolved = _authority(root, passkey, consume=False)
        constraints = resolved.get("authority_scope_constraints") or {}
        if (
            constraints.get("deployment") != deployment
            or constraints.get("branch") != branch
            or constraints.get("target_tree") != tree
        ):
            raise ExactDeployRejected("DEPLOYMENT_AUTHORITY_COORDINATE_DRIFT")

        query = "部署並重啟總場已核定的 MSI WSL 閘道與每小時審查提交排程"
        target = scan_operation(
            repo_root=root,
            operation="PREFLIGHT",
            actor_class="SYSTEM",
            query=query,
        )
        if target.get("state") != PASS_STATE:
            raise ExactDeployRejected(str(target.get("reason") or "DEPLOY_TARGET_LOCK_FAILED"))
        for operation in ("DEPLOY", "RESTART"):
            review = scan_operation(
                repo_root=root,
                operation=operation,
                actor_class="SYSTEM",
                query=query,
                expected_branch=branch,
                expected_head=head,
                expected_tree=tree,
                expected_work_target_sha256=target["work_target_sha256"],
            )
            if review.get("state") != PASS_STATE or review.get("operation_authorized") is not True:
                raise ExactDeployRejected(str(review.get("reason") or f"{operation}_REVIEW_FAILED"))

        previous_gateway_enabled = subprocess.run(
            ["systemctl", "--user", "is-enabled", deployment["service"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        ).stdout.strip()
        previous_gateway_active = subprocess.run(
            ["systemctl", "--user", "is-active", deployment["service"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        ).stdout.strip()
        previous_timer_enabled = subprocess.run(
            ["systemctl", "--user", "is-enabled", deployment["timer"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        ).stdout.strip()
        previous_timer_active = subprocess.run(
            ["systemctl", "--user", "is-active", deployment["timer"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        ).stdout.strip()
        unit_root = Path.home() / ".config/systemd/user"
        effects_started = True
        for name in ("w7tp-hourly-reviewed-commit.service", deployment["timer"]):
            source = root / "systemd" / name
            target_link = unit_root / name
            if not source.is_file():
                raise ExactDeployRejected("DEPLOYMENT_UNIT_SOURCE_MISSING")
            if target_link.exists() or target_link.is_symlink():
                if not target_link.is_symlink() or target_link.resolve() != source.resolve():
                    raise ExactDeployRejected("DEPLOYMENT_UNIT_COLLISION")
        _canary(root, int(deployment["canary_port"]))
        consumed = _authority(root, passkey, consume=True)
        authority_consumed = True
        if consumed.get("authority_sha256") != resolved.get("authority_sha256"):
            raise ExactDeployRejected("DEPLOYMENT_AUTHORITY_CHANGED_BEFORE_EFFECT")

        unit_root.mkdir(parents=True, exist_ok=True)
        for name in ("w7tp-hourly-reviewed-commit.service", deployment["timer"]):
            source = root / "systemd" / name
            target_link = unit_root / name
            if not (target_link.exists() or target_link.is_symlink()):
                target_link.symlink_to(source)
                created_links.append(target_link)
        _run(["systemctl", "--user", "daemon-reload"])
        _run(["systemctl", "--user", "enable", deployment["service"]])
        _run(["systemctl", "--user", "enable", "--now", deployment["timer"]])
        _run(["systemctl", "--user", "restart", deployment["service"]])
        _wait_health(int(deployment["active_port"]))
        observed = {
            "gateway_active": _run(["systemctl", "--user", "is-active", deployment["service"]]),
            "gateway_enabled": _run(["systemctl", "--user", "is-enabled", deployment["service"]]),
            "timer_active": _run(["systemctl", "--user", "is-active", deployment["timer"]]),
            "timer_enabled": _run(["systemctl", "--user", "is-enabled", deployment["timer"]]),
            "health_state": "PASS_GATEWAY_PROCESS",
        }
        if any(value != "active" for key, value in observed.items() if key.endswith("_active")):
            raise ExactDeployRejected("DEPLOYED_SERVICE_NOT_ACTIVE")
        if any(value != "enabled" for key, value in observed.items() if key.endswith("_enabled")):
            raise ExactDeployRejected("DEPLOYED_SERVICE_NOT_ENABLED")
        if _git(root, "rev-parse", "HEAD") != head or _git(root, "status", "--porcelain", "--untracked-files=all"):
            raise ExactDeployRejected("POST_DEPLOY_REPOSITORY_DRIFT")
        outcome = {
            "state": PASS_DEPLOY,
            "deployment_id": deployment_id,
            "head": head,
            "tree": tree,
            "observed": observed,
            "authority_consumed": True,
        }
        receipt = _write_receipt(
            root,
            str(resolved["authority_sha256"]),
            head,
            outcome,
        )
        outcome["receipt_ref"] = receipt.relative_to(root).as_posix()
        return outcome
    except (ExactDeployRejected, OSError, KeyError, TypeError, ValueError) as exc:
        if effects_started:
            if previous_timer_active != "active":
                subprocess.run(["systemctl", "--user", "stop", deployment["timer"]], check=False)
            if previous_timer_enabled != "enabled":
                subprocess.run(["systemctl", "--user", "disable", deployment["timer"]], check=False)
            if previous_gateway_enabled != "enabled":
                subprocess.run(["systemctl", "--user", "disable", deployment["service"]], check=False)
            for link in created_links:
                if link.is_symlink():
                    link.unlink()
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
            if previous_gateway_active == "active":
                subprocess.run(["systemctl", "--user", "restart", deployment["service"]], check=False)
        return {"state": HOLD_DEPLOY, "reason": str(exc), "authority_consumed": authority_consumed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--deployment-id", required=True)
    args = parser.parse_args()
    result = exact_deploy_restart(args.repo_root, args.deployment_id)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("state") == PASS_DEPLOY else 1


if __name__ == "__main__":
    raise SystemExit(main())
