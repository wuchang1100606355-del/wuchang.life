#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused deployment-package tests; no formal node connection is permitted."""

from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RELEASE = ROOT / "manifests/w7tp_small_agent_release_v0_1_3_d27230aba7a4"
VECTOR = ROOT / "tests/fixtures/w7tp_small_agent_deployment_vectors.json"

from tools import deploy_w7tp_small_agent_all_nodes as deployment
from tools.build_w7tp_small_agent_release import verify_security_runtime_patch_release
from tools.deploy_w7tp_small_agent_all_nodes import (
    CommandResult,
    DeploymentError,
    NodeRecord,
    _atomic_symlink,
    _eligibility,
    _remote_rollback,
    _safe_command,
    compare_node_results,
    deploy_nodes,
    install_linux_release,
    resolve_formal_nodes,
)
from tools.w7tp_small_agent_healthcheck import _verify_release
from tools.w7tp_small_agent_service_runner import (
    AgentService,
    ServiceError,
    _run_fixture_decision,
    build_capability_manifest,
    canonical_sha256,
    run_self_test,
)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _eligible_node(node_id: str = "test-node") -> NodeRecord:
    return NodeRecord(
        node_id=node_id,
        kind="linux",
        hostname=f"{node_id}.invalid",
        address=f"{node_id}.invalid",
        authority={"deployment_authorized": True},
        observation_domain={"ref": "observation/test/v0.1"},
        connection_method="SSH",
        deployment_eligibility={
            "status": "ELIGIBLE",
            "reason_code": "FORMAL_NODE_AUTHORITY_RESOLVED",
        },
    )


def _remote_runtime_output(command: str) -> str:
    """Return one strict current-Release response for the in-memory executor."""

    manifest = _json(RELEASE / "release_manifest.json")
    identity = deployment._manifest_runtime_identity(manifest)
    if command == "version":
        return (
            "agent_name=w7tp-small-agent\n"
            f"agent_version={identity['release_version']}\n"
            f"release_sha256={identity['release_sha256']}\n"
            f"policy_sha256={identity['policy_sha256']}\n"
            f"schema_version={manifest['release_identity']['schema_version']}\n"
        )
    evidence = {
        **identity,
        "status": "PASS",
        "checks": dict(deployment.HEALTH_REQUIRED_CHECKS),
    }
    state = "PASS_W7TP_SMALL_AGENT_HEALTH"
    if command == "self-test":
        state = "PASS_W7TP_SMALL_AGENT_SELF_TEST"
        evidence.update(
            {
                "checks": dict(deployment.SELF_TEST_REQUIRED_CHECKS),
                "candidate_hash": "0" * 64,
                "d1_projection_hash": "1" * 64,
                "common_receive_path_marker": (
                    "AgentService._receive_through_gateway/v0.1"
                ),
                "gateway_fixture_mode": "TEST_ONLY",
            }
        )
    return f"STATE={state}\n{deployment._canonical_json(evidence)}\n"


class FakeRemoteExecutor:
    """In-memory executor used to prove orchestration without network access."""

    def __init__(self, failing_nodes: set[str] | None = None) -> None:
        self.failing_nodes = set(failing_nodes or ())
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.transfers: list[tuple[str, str]] = []

    def run(
        self,
        node: NodeRecord,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CommandResult:
        command = tuple(str(item) for item in argv)
        self.calls.append((node.node_id, command))
        if node.node_id in self.failing_nodes:
            return CommandResult(1, "", "TEST_ONLY_FAILURE")
        if (
            len(command) == 2
            and command[0].endswith("/bin/w7tp-small-agent")
            and command[1] in {"version", "health", "self-test"}
        ):
            return CommandResult(0, _remote_runtime_output(command[1]))
        if command[:2] == ("test", "-e"):
            return CommandResult(0)
        if command and command[0] == "readlink":
            return CommandResult(0, "releases/v0.0-previous\n")
        if command and command[0] == "sha256sum":
            from tools.deploy_w7tp_small_agent_all_nodes import _service_content

            return CommandResult(0, canonical_sha256(_service_content()) + "  service\n")
        return CommandResult(0)

    def transfer_release(
        self, node: NodeRecord, release_dir: Path, target: str
    ) -> CommandResult:
        self.transfers.append((node.node_id, target))
        return CommandResult(0)


class W7TPSmallAgentDeploymentTests(unittest.TestCase):
    """Exactly thirty focused checks required by the deployment contract."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.vector = _json(VECTOR)
        cls.self_test = run_self_test(cls.vector)

    def test_01_release_manifest_replay(self) -> None:
        first = verify_security_runtime_patch_release(ROOT, RELEASE)
        second = verify_security_runtime_patch_release(ROOT, RELEASE)
        self.assertEqual(first.release_sha256, second.release_sha256)
        self.assertEqual(first.files, second.files)

    def test_02_all_release_file_hashes_are_correct(self) -> None:
        verified = _verify_release(RELEASE)
        self.assertEqual(
            verified["release_sha256"],
            "1c87fcddf3ca65045a1dace9efa8fa98e04aba489798c414b35ef1982c1d6052",
        )

    def test_03_install_into_temporary_linux_home(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = install_linux_release(Path(directory), RELEASE, service_changed=False)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(Path(result["current"]).is_dir())

    def test_04_same_version_is_not_reinstalled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            install_linux_release(home, RELEASE, service_changed=False)
            result = install_linux_release(home, RELEASE, service_changed=False)
            self.assertEqual(result["status"], "ALREADY_PASS")
            self.assertFalse(result["restart_required"])

    def test_05_different_content_does_not_overwrite_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home = base / "home"
            mutated = base / "release"
            shutil.copytree(RELEASE, mutated)
            install_linux_release(home, RELEASE, service_changed=False)
            (mutated / "UNINSTALL_ROLLBACK.md").write_text(
                "TEST_ONLY_DIFFERENT_CONTENT\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                DeploymentError, "HOLD_RELEASE_RUNTIME_HEALTHCHECK_FAILED"
            ):
                install_linux_release(home, mutated, service_changed=False)

    def test_06_current_switch_is_atomic_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first = base / "first"
            second = base / "second"
            first.mkdir()
            second.mkdir()
            current = base / "current"
            _atomic_symlink(first, current)
            _atomic_symlink(second, current)
            self.assertTrue(current.is_symlink())
            self.assertEqual(current.resolve(), second.resolve())
            self.assertFalse((base / "current.next").exists())

    def test_07_remote_rollback_restores_previous_target(self) -> None:
        node = _eligible_node()
        executor = FakeRemoteExecutor()
        result = _remote_rollback(
            node,
            executor,
            "releases/v0.0-previous",
            "~/.local/share/w7tp-small-agent/current",
            "~/.local/share/w7tp-small-agent/current.next",
        )
        self.assertEqual(
            result.deployment_result["reason_code"],
            "HOLD_DEPLOYMENT_FAILED_ROLLED_BACK",
        )
        self.assertIn((node.node_id, ("systemctl", "--user", "is-active", "--quiet", "w7tp-small-agent.service")), executor.calls)

    def test_08_capability_manifest_is_valid(self) -> None:
        manifest = build_capability_manifest(self.vector["capability_manifest"])
        self.assertEqual(manifest.agent_version.version, self.vector["release_version"])
        self.assertIn("SUBMIT_CANDIDATE", manifest.execution_permissions)

    def test_09_service_commands_are_user_level_and_safe(self) -> None:
        command = _safe_command(
            ("systemctl", "--user", "restart", "w7tp-small-agent.service")
        )
        self.assertEqual(command[1], "--user")

    def test_10_root_commands_are_rejected(self) -> None:
        with self.assertRaisesRegex(DeploymentError, "HOLD_UNSAFE_DEPLOYMENT_COMMAND"):
            _safe_command(("sudo", "systemctl", "restart", "w7tp-small-agent"))
        with self.assertRaisesRegex(
            DeploymentError, "HOLD_SYSTEM_SERVICE_AUTHORITY_FORBIDDEN"
        ):
            _safe_command(("systemctl", "restart", "w7tp-small-agent.service"))

    def test_11_firewall_commands_are_rejected(self) -> None:
        for command in (("iptables", "-L"), ("nft", "list", "ruleset")):
            with self.assertRaisesRegex(
                DeploymentError, "HOLD_UNSAFE_DEPLOYMENT_COMMAND"
            ):
                _safe_command(command)

    def test_12_router_is_never_deployment_eligible(self) -> None:
        result = _eligibility(
            {
                "node_id": "router-test",
                "kind": "ASUSWRT-Merlin router",
                "hostname": "router.invalid",
                "address": "192.0.2.1",
                "authority": True,
                "observation_domain": {"ref": "observation/router/test"},
                "connection_method": "SSH",
            }
        )
        self.assertEqual(result["reason_code"], "HOLD_ROUTER_WRITE_NOT_AUTHORIZED")

    def test_13_database_commands_are_rejected(self) -> None:
        for command in (("psql",), ("mysql",), ("sqlite3", "test.db")):
            with self.assertRaisesRegex(
                DeploymentError, "HOLD_UNSAFE_DEPLOYMENT_COMMAND"
            ):
                _safe_command(command)

    def test_14_total_field_pull_fixed_fixture_passes(self) -> None:
        self.assertEqual(self.self_test["total_field_pull"], "TEST_ONLY_PASS")

    def test_15_llm_push_fixed_fixture_passes(self) -> None:
        self.assertEqual(self.self_test["llm_push"], "TEST_ONLY_PASS")

    def test_16_both_candidate_modes_use_common_receive_path(self) -> None:
        allow = self.vector["gateway_results"]["ALLOW"]
        pull = _run_fixture_decision(self.vector, allow, "TOTAL_FIELD_PULL")
        push = _run_fixture_decision(self.vector, allow, "LLM_PUSH")
        self.assertEqual(pull["common_receive_path"], push["common_receive_path"])

    def test_17_allow_is_the_only_commit_decision(self) -> None:
        self.assertEqual(self.self_test["allow_only_commit"], "PASS")
        self.assertEqual(self.self_test["commit_gates"]["ALLOW"], "PASS")

    def test_18_non_allow_decisions_preserve_previous(self) -> None:
        expected = canonical_sha256(self.vector["previous_state"])
        for decision in ("HOLD", "BLOCK", "QUARANTINE"):
            result = _run_fixture_decision(
                self.vector, self.vector["gateway_results"][decision], "TOTAL_FIELD_PULL"
            )
            self.assertFalse(result["commit_applied"])
            self.assertEqual(result["committed_hash"], expected)

    def test_19_missing_asset_returns_stable_error(self) -> None:
        vector = copy.deepcopy(self.vector)
        vector["candidate"]["asset_refs"] = ["asset/test/missing/v0.1"]
        with self.assertRaisesRegex(ServiceError, "MISSING_ASSET") as caught:
            AgentService()._prepare_agent(vector)
        self.assertEqual(caught.exception.reason_code, "MISSING_ASSET")

    def test_20_version_mismatch_returns_stable_error(self) -> None:
        vector = copy.deepcopy(self.vector)
        vector["candidate"]["required_agent_version"] = "v9.9-test-only"
        with self.assertRaisesRegex(ServiceError, "VERSION_MISMATCH") as caught:
            AgentService()._prepare_agent(vector)
        self.assertEqual(caught.exception.reason_code, "VERSION_MISMATCH")

    def test_21_missing_connection_method_is_held(self) -> None:
        result = _eligibility(
            {
                "kind": "linux",
                "hostname": "node.invalid",
                "address": "node.invalid",
                "authority": True,
                "observation_domain": {"ref": "observation/test/v0.1"},
            }
        )
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("connection_method", result["missing_fields"])

    def test_22_release_contains_no_raw_secret_markers(self) -> None:
        forbidden = (
            b"-----BEGIN PRIVATE KEY-----",
            b"-----BEGIN OPENSSH PRIVATE KEY-----",
            b"sk-proj-",
            b"AKIA",
        )
        for path in sorted(item for item in RELEASE.rglob("*") if item.is_file()):
            content = path.read_bytes()
            self.assertFalse(any(marker in content for marker in forbidden), path.name)

    def test_23_identical_node_results_match(self) -> None:
        nodes = resolve_formal_nodes(ROOT)
        first = compare_node_results(nodes, nodes)
        second = compare_node_results(nodes, copy.deepcopy(nodes))
        self.assertEqual(first["status"], "MATCH")
        self.assertEqual(first["result_hash"], second["result_hash"])

    def test_24_different_node_results_report_difference_paths(self) -> None:
        left = (_eligible_node("node-a"),)
        right = (
            NodeRecord(
                **{
                    **left[0].__dict__,
                    "deployment_result": {"status": "HOLD", "reason_code": "TEST_ONLY"},
                }
            ),
        )
        comparison = compare_node_results(left, right)
        self.assertEqual(comparison["status"], "MISMATCH")
        self.assertTrue(comparison["difference_paths"])

    def test_25_one_node_failure_does_not_stop_next_node(self) -> None:
        bad = _eligible_node("bad")
        good = _eligible_node("good")
        executor = FakeRemoteExecutor({"bad"})
        results = deploy_nodes((bad, good), RELEASE, executor, service_changed=False)
        self.assertEqual(results[0].deployment_result["status"], "HOLD")
        self.assertEqual(results[1].deployment_result["status"], "ALREADY_PASS")
        self.assertTrue(any(node_id == "good" for node_id, _ in executor.calls))

    def test_26_already_pass_remote_node_is_not_reinstalled(self) -> None:
        node = _eligible_node()
        executor = FakeRemoteExecutor()
        result = deploy_nodes((node,), RELEASE, executor, service_changed=False)[0]
        self.assertEqual(result.deployment_result["status"], "ALREADY_PASS")
        self.assertFalse(executor.transfers)
        self.assertFalse(any(command[0] in {"cp", "install"} for _, command in executor.calls))

    def test_27_rollback_manifest_is_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            install_linux_release(home, RELEASE, service_changed=False)
            rollback_path = (
                home
                / ".local/share/w7tp-small-agent/rollback/v0.1.3-d27230aba7a4.json"
            )
            rollback = _json(rollback_path)
            self.assertEqual(rollback["agent_version"], "v0.1.3-d27230aba7a4")
            self.assertIn("previous_current", rollback)
            self.assertTrue(rollback["rollback_requires_owner_confirmation"])

    def test_28_router_records_execute_no_write_commands(self) -> None:
        nodes = resolve_formal_nodes(ROOT)
        router = tuple(
            node
            for node in nodes
            if node.deployment_eligibility["reason_code"]
            == "HOLD_ROUTER_WRITE_NOT_AUTHORIZED"
        )
        executor = FakeRemoteExecutor()
        result = deploy_nodes(router, RELEASE, executor)
        self.assertEqual(len(router), 1)
        self.assertEqual(result[0].deployment_result["status"], "HOLD")
        self.assertEqual(executor.calls, [])

    def test_29_llm_ingress_cannot_commit_directly(self) -> None:
        self.assertEqual(self.self_test["llm_direct_commit"], "BLOCKED")
        self.assertEqual(self.self_test["persona_governance_separation"], "PASS")

    def test_30_error_codes_are_stable(self) -> None:
        observed = []
        for _ in range(2):
            try:
                _safe_command(("reboot",))
            except DeploymentError as error:
                observed.append(error.reason_code)
        self.assertEqual(
            observed,
            ["HOLD_UNSAFE_DEPLOYMENT_COMMAND", "HOLD_UNSAFE_DEPLOYMENT_COMMAND"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
