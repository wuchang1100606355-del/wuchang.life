#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused authority-overlay deployment tests with no real node connection."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Sequence
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AUTHORITY_REGISTRY = (
    ROOT
    / "manifests/w7tp_small_agent_node_authority_v0_1/node_authority_registry.json"
)
RELEASE = ROOT / "manifests/w7tp_small_agent_release_v0_1_d27230aba7a4"
EXPECTED_NODE_IDS = (
    "taiji01",
    "MSI",
    "penguin",
    "localhost",
    "DESKTOP-OHE05SC",
    "wuchang-us-free-node",
    "V3_MIX_EDLA_GL",
    "RT-BE86U-7428",
)

from tools import deploy_w7tp_small_agent_all_nodes as deployment


def _load_registry() -> dict[str, Any]:
    """Return a detached copy of the checked-in authority registry."""

    return json.loads(AUTHORITY_REGISTRY.read_text(encoding="utf-8"))


def _registry_node(registry: dict[str, Any], node_id: str) -> dict[str, Any]:
    """Return one mutable registry node by its exact formal identifier."""

    return next(item for item in registry["nodes"] if item["node_id"] == node_id)


def _write_registry(directory: str, registry: dict[str, Any]) -> Path:
    """Write one deterministic test-only registry in a temporary directory."""

    path = Path(directory) / "node_authority_registry.json"
    path.write_text(
        json.dumps(
            registry,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _record(records: Sequence[deployment.NodeRecord], node_id: str) -> deployment.NodeRecord:
    """Return one resolved node record by exact identifier."""

    return next(item for item in records if item.node_id == node_id)


def _reason_for_registry(registry: dict[str, Any], node_id: str) -> str:
    """Resolve a temporary registry and return one stable result/error code."""

    with tempfile.TemporaryDirectory(dir=ROOT) as directory:
        path = _write_registry(directory, registry)
        try:
            result = deployment.resolve_formal_nodes(
                ROOT, authority_registry=path
            )
        except deployment.DeploymentError as error:
            return error.reason_code
    record = _record(result, node_id)
    return str(record.deployment_eligibility["reason_code"])


def _eligible_ssh_node(node_id: str) -> deployment.NodeRecord:
    """Build one test-only eligible SSH node without a real address."""

    return deployment.NodeRecord(
        node_id=node_id,
        kind="linux",
        hostname=f"{node_id}.invalid",
        address=f"{node_id}.invalid",
        authority="OWNER_AUTHORIZED",
        authority_scope="W7TP_SMALL_AGENT_INSTALL_V0_1_ONLY",
        observation_domain=f"observation-domain:test/{node_id}",
        connection_method="SSH",
        evidence_refs=(
            f"local-command:tailscale-status-json:exact-node-id={node_id}:"
            f"ipv4={node_id}.invalid:online=true",
            f"local-command:ssh-G:alias={node_id}:hostname={node_id}.invalid:"
            "port=22:parsed=true",
        ),
        deployment_eligibility={
            "status": "ELIGIBLE",
            "reason_code": "FORMAL_NODE_AUTHORITY_RESOLVED",
        },
    )


def _remote_runtime_output(command: str) -> str:
    """Return one strict Release response for the in-memory executor."""

    manifest = json.loads((RELEASE / "release_manifest.json").read_text(encoding="utf-8"))
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
    """In-memory remote executor; it never invokes a process or network API."""

    def __init__(self, failing_nodes: set[str] | None = None) -> None:
        self.failing_nodes = set(failing_nodes or ())
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.transfers: list[str] = []

    def run(
        self,
        node: deployment.NodeRecord,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> deployment.CommandResult:
        command = tuple(str(item) for item in argv)
        self.calls.append((node.node_id, command))
        if node.node_id in self.failing_nodes:
            return deployment.CommandResult(1, "", "TEST_ONLY_FAILURE")
        if (
            len(command) == 2
            and command[0].endswith("/bin/w7tp-small-agent")
            and command[1] in {"version", "health", "self-test"}
        ):
            return deployment.CommandResult(0, _remote_runtime_output(command[1]))
        if command[:2] == ("test", "-e"):
            return deployment.CommandResult(0)
        if command and command[0] == "readlink":
            return deployment.CommandResult(0, "releases/v0.0-previous\n")
        return deployment.CommandResult(0)

    def transfer_release(
        self,
        node: deployment.NodeRecord,
        release_dir: Path,
        destination: str,
    ) -> deployment.CommandResult:
        self.transfers.append(node.node_id)
        return deployment.CommandResult(0)


class W7TPSmallAgentNodeAuthorityTests(unittest.TestCase):
    """Exactly fifteen checks for registry authority and deployment gating."""

    def test_01_formal_node_list_is_complete(self) -> None:
        records = deployment.resolve_formal_nodes(
            ROOT, authority_registry=AUTHORITY_REGISTRY
        )
        self.assertEqual(tuple(item.node_id for item in records), EXPECTED_NODE_IDS)
        self.assertEqual(tuple(_load_registry()["formal_node_ids"]), EXPECTED_NODE_IDS)

    def test_02_registry_cannot_add_nonformal_node(self) -> None:
        registry = _load_registry()
        extra = copy.deepcopy(registry["nodes"][0])
        extra["node_id"] = "taiji03"
        extra["canonical_source"] = extra["canonical_source"].replace(
            "taiji01", "taiji03"
        )
        registry["nodes"].append(extra)
        registry["formal_node_ids"].append("taiji03")
        self.assertEqual(
            _reason_for_registry(registry, "taiji01"),
            "HOLD_AUTHORITY_REGISTRY_NODE_SET_MISMATCH",
        )

    def test_03_taiji01_local_identity_evidence_is_verified(self) -> None:
        records = deployment.resolve_formal_nodes(
            ROOT, authority_registry=AUTHORITY_REGISTRY
        )
        taiji01 = _record(records, "taiji01")
        self.assertEqual(taiji01.connection_method, "LOCAL_SHELL")
        self.assertEqual(taiji01.hostname, "taiji01")
        self.assertEqual(taiji01.address, "taiji01")
        self.assertIn(
            "local-command:hostname:exact=taiji01", tuple(taiji01.evidence_refs)
        )
        self.assertEqual(taiji01.deployment_eligibility["status"], "ELIGIBLE")

    def test_04_localhost_alias_is_deduplicated(self) -> None:
        registry = _load_registry()
        localhost = _registry_node(registry, "localhost")
        localhost["alias_of"] = "taiji01"
        localhost["deployment_eligibility"] = True
        localhost["reason_code"] = "ELIGIBLE_OWNER_AUTHORIZED_LOCAL_SHELL"
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = _write_registry(directory, registry)
            records = deployment.resolve_formal_nodes(ROOT, authority_registry=path)
        alias = _record(records, "localhost")
        self.assertEqual(alias.alias_of, "taiji01")
        self.assertEqual(
            alias.deployment_eligibility["reason_code"], "HOLD_ALIAS_DEDUPLICATED"
        )
        executor = FakeRemoteExecutor()
        with mock.patch.object(
            deployment,
            "preflight_release_runtime_entrypoint",
            return_value={"status": "PASS", "entrypoint": "bin/w7tp-small-agent"},
        ):
            result = deployment.deploy_nodes((alias,), RELEASE, executor)
        self.assertEqual(result[0].deployment_result["reason_code"], "HOLD_ALIAS_DEDUPLICATED")
        self.assertEqual(executor.calls, [])

    def test_05_tailscale_address_requires_exact_identity_evidence(self) -> None:
        registry = _load_registry()
        penguin = _registry_node(registry, "penguin")
        penguin["evidence_refs"] = [
            item.replace("exact-hostname=penguin", "exact-hostname=penguin-near")
            for item in penguin["evidence_refs"]
        ]
        self.assertEqual(
            _reason_for_registry(registry, "penguin"),
            "HOLD_NODE_ADDRESS_NOT_VERIFIED",
        )

    def test_06_ssh_requires_parsed_ssh_g_evidence(self) -> None:
        registry = _load_registry()
        penguin = _registry_node(registry, "penguin")
        penguin["evidence_refs"] = [
            item for item in penguin["evidence_refs"] if "ssh-G:" not in item
        ]
        self.assertEqual(
            _reason_for_registry(registry, "penguin"),
            "HOLD_CONNECTION_METHOD_NOT_VERIFIED",
        )

    def test_07_unknown_address_is_never_deployed(self) -> None:
        registry = _load_registry()
        penguin = _registry_node(registry, "penguin")
        penguin["address"] = None
        self.assertEqual(
            _reason_for_registry(registry, "penguin"),
            "HOLD_NODE_ADDRESS_NOT_VERIFIED",
        )

    def test_08_unknown_connection_method_is_never_deployed(self) -> None:
        registry = _load_registry()
        penguin = _registry_node(registry, "penguin")
        penguin["connection_method"] = "UNKNOWN"
        self.assertEqual(
            _reason_for_registry(registry, "penguin"),
            "HOLD_CONNECTION_METHOD_NOT_VERIFIED",
        )

    def test_09_router_is_always_read_only(self) -> None:
        registry = _load_registry()
        router = _registry_node(registry, "RT-BE86U-7428")
        router["deployment_eligibility"] = True
        router["connection_method"] = "SSH"
        router["reason_code"] = "ELIGIBLE_OWNER_AUTHORIZED_VERIFIED_SSH"
        self.assertEqual(
            _reason_for_registry(registry, "RT-BE86U-7428"),
            "HOLD_ROUTER_WRITE_NOT_AUTHORIZED",
        )

    def test_10_owner_scope_is_install_only(self) -> None:
        registry = _load_registry()
        taiji01 = _registry_node(registry, "taiji01")
        taiji01["authority_scope"] = "DB_ROUTER_CANONICAL_WRITE"
        self.assertEqual(
            _reason_for_registry(registry, "taiji01"),
            "HOLD_OWNER_AUTHORITY_SCOPE_INVALID",
        )

    def test_11_database_write_commands_are_forbidden(self) -> None:
        for command in (("mysql",), ("psql",), ("sqlite3", "state.db")):
            with self.subTest(command=command):
                with self.assertRaisesRegex(
                    deployment.DeploymentError, "HOLD_UNSAFE_DEPLOYMENT_COMMAND"
                ):
                    deployment._safe_command(command)

    def test_12_canonical_and_pointer_are_never_written(self) -> None:
        protected = (ROOT / deployment.ACTIVE_CANONICAL, ROOT / deployment.ACTIVE_POINTER)
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected
        }
        deployment.resolve_formal_nodes(ROOT, authority_registry=AUTHORITY_REGISTRY)
        after = {
            path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected
        }
        self.assertEqual(before, after)

    def test_13_one_node_failure_does_not_stop_next_node(self) -> None:
        first = _eligible_ssh_node("first")
        second = _eligible_ssh_node("second")
        executor = FakeRemoteExecutor({"first"})
        with mock.patch.object(
            deployment,
            "preflight_release_runtime_entrypoint",
            return_value={"status": "PASS", "entrypoint": "bin/w7tp-small-agent"},
        ):
            results = deployment.deploy_nodes((first, second), RELEASE, executor)
        self.assertEqual(results[0].deployment_result["status"], "HOLD")
        self.assertEqual(results[1].deployment_result["status"], "ALREADY_PASS")
        self.assertTrue(any(node_id == "second" for node_id, _ in executor.calls))

    def test_14_same_healthy_version_is_not_reinstalled(self) -> None:
        node = _eligible_ssh_node("already-pass")
        executor = FakeRemoteExecutor()
        with mock.patch.object(
            deployment,
            "preflight_release_runtime_entrypoint",
            return_value={"status": "PASS", "entrypoint": "bin/w7tp-small-agent"},
        ):
            result = deployment.deploy_nodes((node,), RELEASE, executor)[0]
        self.assertEqual(result.deployment_result["status"], "ALREADY_PASS")
        self.assertEqual(
            result.deployment_result["reason_code"],
            "RELEASE_ALREADY_INSTALLED_AND_HEALTHY",
        )
        self.assertEqual(executor.transfers, [])
        self.assertFalse(
            any("restart" in command for _node_id, command in executor.calls)
        )

    def test_15_reason_codes_and_release_preflight_are_stable(self) -> None:
        first = deployment.resolve_formal_nodes(
            ROOT, authority_registry=AUTHORITY_REGISTRY
        )
        second = deployment.resolve_formal_nodes(
            ROOT, authority_registry=AUTHORITY_REGISTRY
        )
        self.assertEqual(
            [item.deployment_eligibility["reason_code"] for item in first],
            [item.deployment_eligibility["reason_code"] for item in second],
        )
        taiji01 = _record(first, "taiji01")
        for _attempt in range(2):
            executor = FakeRemoteExecutor()
            result = deployment.deploy_nodes((taiji01,), RELEASE, executor)[0]
            self.assertEqual(
                result.deployment_result["reason_code"],
                "HOLD_RELEASE_RUNTIME_ENTRYPOINT_MISSING",
            )
            self.assertEqual(executor.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
