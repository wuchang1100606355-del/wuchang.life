#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thirty focused runtime-entrypoint checks with no formal node connection."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CLI_SOURCE = ROOT / "tools/w7tp_small_agent_cli.py"
RELEASE = ROOT / "manifests/w7tp_small_agent_release_v0_1_1_d27230aba7a4"
SECURITY_RELEASE = ROOT / "manifests/w7tp_small_agent_release_v0_1_3_d27230aba7a4"
OLD_RELEASE = ROOT / "manifests/w7tp_small_agent_release_v0_1_d27230aba7a4"
ENTRYPOINT = RELEASE / "bin/w7tp-small-agent"
EXPECTED_VERSION = "v0.1.1-d27230aba7a4"
EXPECTED_POLICY_SHA256 = (
    "d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960"
)
EXPECTED_OLD_TREE_SHA256 = (
    "2f5a47fbee773d70c94dc4f90f64c040866639f29b43eedf5c2cd57c9c2a1312"
)

from tools.build_w7tp_small_agent_release import (
    build_security_runtime_patch_release,
    verify_security_runtime_patch_release,
)
from tools.deploy_w7tp_small_agent_all_nodes import (
    CommandResult,
    NodeRecord,
    deploy_nodes,
    install_linux_release,
)


def _minimal_environment(home: Path, pythonpath: str | None = None) -> dict[str, str]:
    """Return a credential-free environment for one local CLI child."""

    environment = {
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if pythonpath is not None:
        environment["PYTHONPATH"] = pythonpath
    return environment


def _run_cli(
    *arguments: str,
    cwd: Path | str = ROOT,
    pythonpath: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the packaged CLI locally with no inherited environment values."""

    with tempfile.TemporaryDirectory() as directory:
        return subprocess.run(
            [str(ENTRYPOINT), *arguments],
            cwd=str(cwd),
            env=_minimal_environment(Path(directory), pythonpath),
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )


def _state_evidence(
    result: subprocess.CompletedProcess[str], expected_state: str
) -> dict[str, Any]:
    """Parse one successful two-line CLI state contract."""

    if result.returncode != 0:
        raise AssertionError(
            f"command failed rc={result.returncode}: {result.stdout[:300]}"
        )
    lines = result.stdout.strip().splitlines()
    if len(lines) != 2 or lines[0] != f"STATE={expected_state}":
        raise AssertionError(f"unexpected state output: {result.stdout[:300]}")
    evidence = json.loads(lines[1])
    if not isinstance(evidence, dict):
        raise AssertionError("state evidence is not an object")
    return evidence


def _version_fields(result: subprocess.CompletedProcess[str]) -> dict[str, str]:
    """Parse the closed five-line version output."""

    fields: dict[str, str] = {}
    for line in result.stdout.strip().splitlines():
        key, separator, value = line.partition("=")
        if not separator or key in fields:
            raise AssertionError(f"invalid version output: {line}")
        fields[key] = value
    return fields


def _tree_sha256(root: Path) -> str:
    """Hash one named release tree by safe relative path and exact bytes."""

    digest = hashlib.sha256()
    files = sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix(),
    )
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _contains_sensitive_key(value: Any) -> bool:
    """Detect only secret-bearing JSON member names recursively."""

    sensitive = {"api_key", "credential", "password", "private_key", "secret", "token"}
    if isinstance(value, dict):
        return any(
            str(key).casefold() in sensitive or _contains_sensitive_key(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def _terminate_and_reap(process: subprocess.Popen[bytes]) -> int:
    """Terminate one test child, then kill and reap it on bounded timeout."""

    if process.poll() is None:
        process.terminate()
    try:
        return process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait(timeout=5)


def _service_cycle() -> tuple[str, str, int]:
    """Observe IDLE_READY once, then always terminate and reap the child."""

    process: subprocess.Popen[bytes] | None = None
    returncode: int | None = None
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        output_path = temporary / "service-output.log"
        with output_path.open("wb") as output:
            try:
                process = subprocess.Popen(
                    [str(ENTRYPOINT), "service-run"],
                    cwd="/",
                    env=_minimal_environment(temporary),
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                )
                deadline = time.monotonic() + 10
                while True:
                    observed = output_path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    ).splitlines()
                    if "STATE=IDLE_READY" in observed:
                        break
                    if process.poll() is not None:
                        raise AssertionError("service exited before IDLE_READY")
                    if time.monotonic() >= deadline:
                        raise AssertionError("service did not become ready")
                    time.sleep(0.05)
            finally:
                if process is not None:
                    returncode = _terminate_and_reap(process)
        observed = output_path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    if returncode is None:
        raise AssertionError("service child was not started")
    ready = "STATE=IDLE_READY" if "STATE=IDLE_READY" in observed else ""
    stopped = "STATE=STOPPED" if "STATE=STOPPED" in observed else ""
    return ready, stopped, returncode


class FakeRemoteExecutor:
    """Executor that proves preflight rejection happens before any node action."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def run(
        self,
        node: NodeRecord,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CommandResult:
        self.calls.append(tuple(str(item) for item in argv))
        return CommandResult(99, "", "TEST_ONLY_UNEXPECTED_CALL")

    def transfer_release(
        self,
        node: NodeRecord,
        release_dir: Path,
        destination: str,
    ) -> CommandResult:
        self.calls.append(("transfer_release", destination))
        return CommandResult(99, "", "TEST_ONLY_UNEXPECTED_CALL")


class W7TPSmallAgentRuntimeEntrypointTests(unittest.TestCase):
    """Exactly thirty checks matching the approved entrypoint test contract."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(
            (RELEASE / "release_manifest.json").read_text(encoding="utf-8")
        )
        cls.version_result = _run_cli("version")
        cls.version = _version_fields(cls.version_result)
        cls.health_result = _run_cli("health")
        cls.health = _state_evidence(
            cls.health_result, "PASS_W7TP_SMALL_AGENT_HEALTH"
        )
        cls.self_test_result = _run_cli("self-test")
        cls.self_test = _state_evidence(
            cls.self_test_result, "PASS_W7TP_SMALL_AGENT_SELF_TEST"
        )
        cls.checks = cls.self_test["checks"]

    def test_01_cli_source_compiles(self) -> None:
        source = CLI_SOURCE.read_text(encoding="utf-8")
        compile(source, str(CLI_SOURCE), "exec", dont_inherit=True)

    def test_02_bin_entrypoint_exists(self) -> None:
        self.assertTrue(ENTRYPOINT.is_file())
        self.assertFalse(ENTRYPOINT.is_symlink())

    def test_03_bin_entrypoint_is_executable(self) -> None:
        mode = ENTRYPOINT.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)
        self.assertTrue(os.access(ENTRYPOINT, os.X_OK))

    def test_04_version_command_succeeds(self) -> None:
        self.assertEqual(self.version_result.returncode, 0)
        self.assertEqual(len(self.version), 5)

    def test_05_version_content_is_fixed(self) -> None:
        self.assertEqual(
            self.version,
            {
                "agent_name": "w7tp-small-agent",
                "agent_version": EXPECTED_VERSION,
                "release_sha256": self.manifest["release_sha256"],
                "policy_sha256": EXPECTED_POLICY_SHA256,
                "schema_version": "w7tp-small-agent-cli/v0.1.1",
            },
        )

    def test_06_health_command_succeeds(self) -> None:
        self.assertEqual(self.health_result.returncode, 0)
        self.assertEqual(self.health["status"], "PASS")

    def test_07_health_verifies_policy_sha256(self) -> None:
        self.assertEqual(self.health["policy_sha256"], EXPECTED_POLICY_SHA256)
        self.assertEqual(self.health["checks"]["policy_sha256"], "PASS")

    def test_08_health_verifies_release_files(self) -> None:
        self.assertEqual(
            self.health["release_sha256"], self.manifest["release_sha256"]
        )
        self.assertEqual(self.health["checks"]["release_files"], "PASS")
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            installed = install_linux_release(
                home,
                RELEASE,
                service_changed=False,
            )
            installed_release = Path(installed["current"])
            self.assertFalse((installed_release / ".release_sha256").exists())
            installed_health = subprocess.run(
                [str(installed_release / "bin/w7tp-small-agent"), "health"],
                cwd="/",
                env=_minimal_environment(home),
                text=True,
                capture_output=True,
                timeout=15,
                check=False,
            )
        evidence = _state_evidence(
            installed_health,
            "PASS_W7TP_SMALL_AGENT_HEALTH",
        )
        self.assertEqual(evidence["checks"]["release_files"], "PASS")

    def test_09_self_test_command_succeeds(self) -> None:
        self.assertEqual(self.self_test_result.returncode, 0)
        self.assertEqual(self.self_test["status"], "PASS")

    def test_10_d1_projection_succeeds(self) -> None:
        self.assertEqual(self.checks["d1_projection"], "PASS")
        self.assertRegex(self.self_test["d1_projection_hash"], r"^[0-9a-f]{64}$")

    def test_11_candidate_replay_is_deterministic(self) -> None:
        replay = _state_evidence(
            _run_cli("self-test"), "PASS_W7TP_SMALL_AGENT_SELF_TEST"
        )
        self.assertEqual(self.checks["candidate_replay"], "PASS")
        self.assertEqual(replay["candidate_hash"], self.self_test["candidate_hash"])
        self.assertEqual(
            replay["d1_projection_hash"], self.self_test["d1_projection_hash"]
        )

    def test_12_total_field_pull_succeeds(self) -> None:
        self.assertEqual(self.checks["total_field_pull"], "PASS")

    def test_13_llm_push_succeeds(self) -> None:
        self.assertEqual(self.checks["llm_push"], "PASS")

    def test_14_pull_and_push_share_receive_path(self) -> None:
        self.assertEqual(self.checks["common_receive_path"], "PASS")
        self.assertEqual(
            self.self_test["common_receive_path_marker"],
            "AgentService._receive_through_gateway/v0.1",
        )

    def test_15_allow_is_the_only_commit_path(self) -> None:
        self.assertEqual(self.checks["allow_only_commit"], "PASS")

    def test_16_hold_preserves_previous(self) -> None:
        self.assertEqual(self.checks["hold_preserves_previous"], "PASS")

    def test_17_block_preserves_previous(self) -> None:
        self.assertEqual(self.checks["block_preserves_previous"], "PASS")

    def test_18_quarantine_preserves_previous(self) -> None:
        self.assertEqual(self.checks["quarantine_preserves_previous"], "PASS")

    def test_19_persona_text_does_not_enter_tfs(self) -> None:
        self.assertEqual(self.checks["persona_governance_separation"], "PASS")
        self.assertNotIn("persona_text", self.self_test_result.stdout)

    def test_20_llm_direct_commit_is_blocked(self) -> None:
        self.assertEqual(self.checks["llm_direct_commit"], "BLOCKED")

    def test_21_capabilities_do_not_disclose_secrets(self) -> None:
        result = _run_cli("capabilities")
        self.assertEqual(result.returncode, 0)
        capability = json.loads(result.stdout)
        self.assertFalse(_contains_sensitive_key(capability))
        self.assertNotIn("PRIVATE KEY", result.stdout)

    def test_22_receive_candidate_rejects_extra_member(self) -> None:
        envelope = {
            "schema_version": "w7tp-small-agent-receive-candidate/v0.1",
            "source_mode": "TOTAL_FIELD_PULL",
            "request": {},
            "previous_state": {},
            "observation_domains": {},
            "extra": True,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extra.json"
            path.write_text(json.dumps(envelope), encoding="utf-8")
            result = _run_cli("receive-candidate", str(path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("STATE=HOLD_RECEIVE_CANDIDATE_MEMBER_MISMATCH", result.stdout)

    def test_23_receive_candidate_rejects_nan_and_infinity(self) -> None:
        template = (
            '{{"schema_version":"w7tp-small-agent-receive-candidate/v0.1",'
            '"source_mode":"TOTAL_FIELD_PULL","request":{{"value":{token}}},'
            '"previous_state":{{}},"observation_domains":{{}}}}'
        )
        for token in ("NaN", "Infinity"):
            with self.subTest(token=token), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "nonfinite.json"
                path.write_text(template.format(token=token), encoding="utf-8")
                result = _run_cli("receive-candidate", str(path))
                self.assertEqual(result.returncode, 2)
                self.assertIn("STATE=HOLD_NON_FINITE_JSON_NUMBER", result.stdout)

    def test_24_service_run_enters_idle_ready(self) -> None:
        ready, _stopped, _returncode = _service_cycle()
        self.assertEqual(ready, "STATE=IDLE_READY")

    def test_25_sigterm_stops_service_cleanly(self) -> None:
        ready, stopped, returncode = _service_cycle()
        self.assertEqual(ready, "STATE=IDLE_READY")
        self.assertEqual(stopped, "STATE=STOPPED")
        self.assertEqual(returncode, 0)

    def test_26_entrypoint_runs_from_nonrelease_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = _run_cli("version", cwd=directory)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(_version_fields(result), self.version)

    def test_27_entrypoint_does_not_depend_on_external_pythonpath(self) -> None:
        result = _run_cli("health", cwd="/", pythonpath="/definitely/not/w7tp")
        evidence = _state_evidence(result, "PASS_W7TP_SMALL_AGENT_HEALTH")
        self.assertEqual(evidence["checks"]["module_imports"], "PASS")

    def test_28_security_runtime_patch_rebuild_has_identical_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "security-runtime-patch-release"
            first = build_security_runtime_patch_release(ROOT, target)
            second = build_security_runtime_patch_release(ROOT, target)
            verified = verify_security_runtime_patch_release(ROOT, target)
        expected = json.loads(
            (SECURITY_RELEASE / "release_manifest.json").read_text(encoding="utf-8")
        )["release_sha256"]
        self.assertEqual(first.release_sha256, expected)
        self.assertEqual(second.release_sha256, expected)
        self.assertEqual(verified.release_sha256, expected)

    def test_29_old_release_is_unchanged(self) -> None:
        self.assertEqual(_tree_sha256(OLD_RELEASE), EXPECTED_OLD_TREE_SHA256)
        old_manifest = json.loads(
            (OLD_RELEASE / "release_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            old_manifest["release_sha256"],
            "5d7f220b1716d0d496cd016c962b295b96654faff0fccb96e7c6eadee2cddc2a",
        )

    def test_30_deployer_rejects_release_missing_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            damaged = Path(directory) / "release"
            shutil.copytree(RELEASE, damaged)
            (damaged / "bin/w7tp-small-agent").unlink()
            node = NodeRecord(
                node_id="test-only-node",
                kind="linux",
                hostname="test-only-node.invalid",
                address="test-only-node.invalid",
                authority="OWNER_AUTHORIZED",
                authority_scope="W7TP_SMALL_AGENT_INSTALL_V0_1_ONLY",
                observation_domain="observation-domain:test/v0.1",
                connection_method="SSH",
                deployment_eligibility={
                    "status": "ELIGIBLE",
                    "reason_code": "FORMAL_NODE_AUTHORITY_RESOLVED",
                },
            )
            executor = FakeRemoteExecutor()
            result = deploy_nodes((node,), damaged, executor)[0]
        self.assertEqual(
            result.deployment_result["reason_code"],
            "HOLD_RELEASE_RUNTIME_ENTRYPOINT_MISSING",
        )
        self.assertEqual(executor.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
