from __future__ import annotations

import copy
import datetime as dt
import io
import json
import os
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from w7tp_gt_mesh.app import MeshRuntime, _emit_result, make_server, render_human_summary
from w7tp_gt_mesh.core import (
    MeshConflict,
    MeshHold,
    TOTAL_FIELD_AUTHORITY_REF,
    canonical_binding,
    require_core,
    self_hash_excluding,
)
from w7tp_gt_mesh.control import build_task_envelope, validate_task_envelope
from w7tp_gt_mesh.journal import MeshStorage
from w7tp_gt_mesh.inventory import _container_metadata, _service_metadata, _tailscale_peer_topology
from w7tp_gt_mesh.known_novel_v3 import (
    TOKEN_TABLE,
    build_known_novel_v3,
    build_v3_artifact,
    lookup_profile,
    reconstruct_known_novel_v3,
    reconstruct_v3_artifact,
    repeat_to_size,
)
from w7tp_gt_mesh.native_adi import NativeADIAdapter, build_native_adi_record, native_adi_insert_url
from w7tp_gt_mesh.packet import (
    build_transfer,
    validate_domain_profile,
    validate_packet,
    validate_packet_profile_binding,
)
from w7tp_gt_mesh.receiver import MeshReceiver
from w7tp_gt_mesh.spool import DriveSpoolProducer, produce_drive_projection_envelopes
from w7tp_gt_mesh.transport import MeshTransport


FIXED = dt.datetime(2026, 8, 29, 0, 0, 0, tzinfo=dt.UTC)


def snapshot(logical_time: int, *, git: bool = False) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_id": "W7TP_GT_MESH_NODE_SNAPSHOT_V21",
        "canonical_id": "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1",
        "version": "2.1",
        "canonical_binding": canonical_binding(),
        "domain_profile": "NODE_CONTAINER_SERVICE_LISTENER_CURATED_FILE_METADATA",
        "source_node_ref": "node:source",
        "logical_root_id": "mesh-test",
        "logical_time": logical_time,
        "observed_at": f"2026-08-29T00:00:0{logical_time}Z",
        "node": {"node_id": "source", "observation_state": "OBSERVED_METADATA_ONLY"},
        "services": [{"service_id": "svc", "active_state": "active"}],
        "containers": [{"container_id": "abc", "name": "box", "state": "running"}],
        "listeners": [{"protocol": "TCP", "local_address": "127.0.0.1", "local_port": 9191}],
        "curated_files": [{"logical_path": "a.txt", "size_bytes": logical_time, "content_sha256": None}],
        "git_evidence": [],
        "probe_evidence": [{"probe": "fixture", "state": "OBSERVED"}],
        "authority_state": "EVIDENCE_ONLY",
        "live_effect_state": "NOT_ESTABLISHED_BY_METADATA",
        "runtime_integrity_boundary": "NO_SECRET_OR_PRIVATE_LOOKUP_CONTENT_READ_BY_DEFAULT",
        "zz_stable_payload": "x" * 50000,
    }
    if git:
        value["git_evidence"] = [
            {
                "dimension": "D4_EVIDENCE",
                "authority_state": "EVIDENCE_ONLY",
                "live_effect_state": "NOT_ESTABLISHED_BY_GIT",
                "root": "/bounded/root",
                "branch": "candidate",
                "head": "0" * 40,
                "remotes": [],
                "diff_count": 3,
                "dirty_is_blocker": False,
            }
        ]
    return value


class MeshTests(unittest.TestCase):
    def test_cli_final_output_is_human_traditional_chinese_summary(self) -> None:
        value = {
            "state": "PASS_CYCLE_COMPLETED_WITH_ORTHOGONAL_PEER_RESULTS",
            "packet_ref": "sha256:" + "0" * 64,
            "transfer_mode": "DIRECT_TRANSFER_BASELINE",
        }
        config = {"node_id": "taiji01", "containers": {"enabled": True}}
        summary = render_human_summary(value, config)
        for heading in ("意圖：", "總場理由：", "節點／容器：", "結果：", "風險／未知："):
            self.assertIn(heading, summary)
        human_sections = summary.splitlines()[1:]
        self.assertEqual(5, len(human_sections))
        for section in human_sections:
            self.assertGreaterEqual(sum("\u4e00" <= character <= "\u9fff" for character in section), 8)
        for machine_fragment in ("state=", "packet_ref=", "transfer_mode=", "reason="):
            self.assertNotIn(machine_fragment, summary)
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="utf-8")
        with mock.patch("w7tp_gt_mesh.app.sys.stdout", stream):
            _emit_result(value, config)
            stream.flush()
        lines = raw.getvalue().decode("utf-8").splitlines()
        self.assertTrue(lines[0].startswith("{"))
        self.assertTrue(lines[-1].startswith("風險／未知："))

    def test_deploy_routes_total_field_and_drive_without_msi_authority(self) -> None:
        config_root = Path(__file__).resolve().parents[1] / "deploy" / "configs"
        configs = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in config_root.glob("*.json")
        }
        for name in ("taiji02", "taiji03", "wuchang-us-free-node"):
            self.assertEqual({"msi", "taiji01"}, {peer["peer_id"] for peer in configs[name]["peers"]})
        self.assertIn("taiji01", {peer["peer_id"] for peer in configs["msi"]["peers"]})
        for name, config in configs.items():
            self.assertEqual(TOTAL_FIELD_AUTHORITY_REF, config["authority_ref"], name)
            self.assertEqual("node:taiji01", config["total_field_authority_node_ref"], name)
            self.assertEqual("8D_ADI", config["primary_decision_engine"], name)
            self.assertEqual(
                "PRIMARY_DECISION_ENGINE_NOT_AUTHORITY",
                config["primary_decision_engine_role"],
                name,
            )
            if name == "taiji01":
                self.assertEqual("http://127.0.0.1:9110", config["native_adi_url"])
            else:
                self.assertNotIn("native_adi_url", config)
        manifest = json.loads(
            (Path(__file__).resolve().parents[1] / "deploy" / "deployment-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(["msi", "taiji01"], manifest["route_contract"]["remote_nodes_to"])
        self.assertEqual("node:taiji01", manifest["total_field_authority_node_ref"])
        self.assertEqual("TELEMETRY_TASK_VALIDATION_ONLY_NO_EXECUTOR", manifest["candidate_control_endpoint_state"])
        self.assertNotIn("control_authority_endpoint", manifest)

    def test_total_field_authority_control_contract_and_scheduler_interface(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as runtime_dir:
            with MeshStorage(runtime_dir) as storage:
                transfer = build_transfer(
                    storage,
                    snapshot(1),
                    authority_ref=TOTAL_FIELD_AUTHORITY_REF,
                    namespace="w7tp.mesh.control.test",
                    now=FIXED,
                )
                self.assertEqual(TOTAL_FIELD_AUTHORITY_REF, transfer.packet["envelope"]["authority_ref"])
                self.assertEqual("TOTAL_FIELD", transfer.profile["authority_contract"]["unique_authority"])
                self.assertEqual("8D_ADI", transfer.profile["authority_contract"]["decision_engine"])
                self.assertEqual(
                    "PRIMARY_DECISION_ENGINE",
                    transfer.profile["authority_contract"]["decision_engine_role"],
                )
                self.assertEqual(
                    "NOT_AUTHORITY",
                    transfer.profile["authority_contract"]["decision_engine_authority_state"],
                )
                self.assertEqual(
                    transfer.capability_inventory_ref,
                    transfer.profile["control_plane"]["capability_inventory_ref"],
                )
                self.assertEqual(
                    "NOT_WIRED_NO_SIDE_EFFECT",
                    transfer.capability_inventory["control_execution_state"],
                )
                self.assertEqual(["node:source"], transfer.capability_inventory["targets"]["node_refs"])
                self.assertEqual(1, len(transfer.capability_inventory["targets"]["container_refs"]))
                with self.assertRaises(MeshHold):
                    build_transfer(
                        storage,
                        snapshot(2),
                        authority_ref="authority:not-total-field",
                        namespace="w7tp.mesh.control.test",
                        now=FIXED,
                    )

                task = build_task_envelope(
                    task_id="task-1",
                    target_kind="CONTAINER",
                    target_ref="container:source:box",
                    action_ref="action:CONTAINER_SCHEDULE",
                    intent_ref="intent:PLACE_WORKLOAD",
                    capability_inventory_ref=transfer.capability_inventory_ref,
                    authority_seal_ref="seal:TOTAL_FIELD_EXTERNAL_VERIFICATION_REQUIRED",
                    logical_time=1,
                    nonce="0123456789abcdef",
                    ttl_seconds=300,
                    cpu_threads=2,
                    ram_bytes=1024,
                    gpu_memory_mib=0,
                    container_runtime_ref="runtime:docker",
                )
                validate_task_envelope(task)
                self.assertFalse(task["execution_permitted"])
                tampered = copy.deepcopy(task)
                tampered["authority"]["decision_engine_authority_state"] = "AUTHORITY"
                with self.assertRaises(MeshHold):
                    validate_task_envelope(tampered)

    def test_taiji01_native_adi_record_hook_is_small_and_non_executing(self) -> None:
        self.assertEqual(
            "http://127.0.0.1:9110/v1/adi/insert",
            native_adi_insert_url("http://127.0.0.1:9110"),
        )
        with tempfile.TemporaryDirectory(dir="/tmp") as runtime_dir:
            config = {
                "node_id": "taiji01",
                "logical_root_id": "mesh-test",
                "runtime_root": runtime_dir,
                "native_adi_url": "http://127.0.0.1:9110",
                "services": [],
                "containers": {"enabled": False},
                "listeners": {"enabled": False},
                "curated_files": [],
                "git_evidence_roots": [],
            }
            with MeshRuntime(config) as runtime, mock.patch(
                "w7tp_gt_mesh.app.collect_snapshot", return_value=snapshot(1)
            ), mock.patch.object(
                NativeADIAdapter,
                "insert_or_queue",
                return_value={"state": "PASS_NATIVE_ADI_INSERT"},
            ) as insert:
                transfer = runtime.collect()
            record = insert.call_args.args[0]
            self.assertEqual(1787961601, record["time_slot"])
            self.assertEqual(transfer.logical_time, record["payload"]["local_logical_time"])
            self.assertEqual(
                {
                    "source_node_ref",
                    "packet_id",
                    "snapshot_sha256",
                    "capability_ref",
                    "reconstruction_ref",
                    "receipt_ref",
                    "authority_state",
                    "local_logical_time",
                },
                set(record["payload"]),
            )
            self.assertLess(len(require_core().canonical_json_bytes(record["payload"])), 64 * 1024)
            self.assertFalse(any(isinstance(value, float) for value in record.values()))

            direct_record = build_native_adi_record(
                source_node_ref=str(record["payload"]["source_node_ref"]),
                packet_id=str(transfer.packet["envelope"]["packet_id"]),
                packet_ref=transfer.packet_ref,
                observed_at="2026-08-29T00:00:01Z",
                local_logical_time=transfer.logical_time,
                snapshot_ref=transfer.target_snapshot_ref,
                capability_ref=transfer.capability_inventory_ref,
                reconstruction_ref=transfer.target_snapshot_ref,
                receipt_ref="receipt:test",
                authority_state="CANDIDATE_EVIDENCE_ONLY",
            )
            self.assertEqual(record["id"], direct_record["id"])

    def test_native_adi_exact_retry_and_append_only_conflict(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as runtime_dir:
            with MeshStorage(runtime_dir) as storage:
                record = build_native_adi_record(
                    source_node_ref="node:source",
                    packet_id="packet-1",
                    packet_ref="sha256:" + "1" * 64,
                    observed_at="2026-08-29T00:00:01Z",
                    local_logical_time=1,
                    snapshot_ref="sha256:" + "2" * 64,
                    capability_ref="sha256:" + "3" * 64,
                    reconstruction_ref="sha256:" + "2" * 64,
                    receipt_ref="receipt:local",
                    authority_state="CANDIDATE_EVIDENCE_ONLY",
                )
                response_body = json.dumps(
                    {
                        "state": "PASS",
                        "record": {
                            "id": record["id"],
                            "time_slot": record["time_slot"],
                            "collision_index": 0,
                            "spiral_position": [0, 0],
                            "payload": record["payload"],
                            "record_sha256": "4" * 64,
                        },
                    },
                    separators=(",", ":"),
                ).encode("utf-8")
                response = mock.MagicMock()
                response.__enter__.return_value.read.return_value = response_body
                adapter = NativeADIAdapter(storage, base_url="http://127.0.0.1:9110")
                with mock.patch("w7tp_gt_mesh.native_adi.urllib.request.urlopen", return_value=response):
                    first = adapter.insert(record)
                    second = adapter.insert(record)
                self.assertEqual(first["receipt_ref"], second["receipt_ref"])
                self.assertEqual(1, len(list(storage.journal.records("native_adi_receipts"))))
                conflict = urllib.error.HTTPError(adapter.url, 422, "conflict", {}, None)
                with mock.patch("w7tp_gt_mesh.native_adi.urllib.request.urlopen", side_effect=conflict):
                    with self.assertRaises(MeshConflict):
                        adapter.insert(record)

    def test_live_v3_vectors_and_noncontiguous_known_novel_blocks(self) -> None:
        vector = bytes.fromhex(
            "57374733000000200000001000000001000000010000000001000102030405060708090a0b0c0d0e0f"
        )
        state, known, novel = reconstruct_known_novel_v3(vector)
        self.assertEqual((1, 1), (known, novel))
        self.assertEqual(
            "e4e9c435d99a1b4a87d725d209a3aea5ed69f6cf4eff36db6041b6c2961bc5c8",
            __import__("hashlib").sha256(state).hexdigest(),
        )
        block_size = 16
        target = b"".join(
            [
                repeat_to_size(TOKEN_TABLE[0], block_size),
                bytes(range(16)),
                repeat_to_size(TOKEN_TABLE[2], block_size),
                bytes(reversed(range(16))),
                repeat_to_size(TOKEN_TABLE[1], block_size),
            ]
        )
        body, known, novel = build_known_novel_v3(target, block_size=block_size)
        rebuilt, observed_known, observed_novel = reconstruct_known_novel_v3(body)
        self.assertEqual(target, rebuilt)
        self.assertEqual((3, 2), (known, novel))
        self.assertEqual((known, novel), (observed_known, observed_novel))

        economic_target = b"".join(
            repeat_to_size(TOKEN_TABLE[index % 4], block_size)
            if index not in {17, 83}
            else bytes([index]) * block_size
            for index in range(100)
        )
        candidate = build_v3_artifact(economic_target, block_sizes=[block_size])
        self.assertIsNotNone(candidate)
        artifact, artifact_raw = candidate
        self.assertLess(len(artifact_raw), len(economic_target))
        self.assertEqual(
            economic_target,
            reconstruct_v3_artifact(artifact, carried_lookup_profile=lookup_profile()),
        )
        tampered_lookup = lookup_profile()
        tampered_lookup["lookup_version"] = "TAMPERED"
        with self.assertRaises(Exception):
            reconstruct_v3_artifact(artifact, carried_lookup_profile=tampered_lookup)

        strict_target = repeat_to_size(TOKEN_TABLE[0], 16) + bytes(range(16))
        strict_artifact, _ = build_v3_artifact(strict_target, block_sizes=[16])
        self.assertEqual((1, 1), (strict_artifact["known_count"], strict_artifact["novel_count"]))
        for key in ("block_size", "known_count", "novel_count", "body_bytes", "target_bytes"):
            with self.subTest(strict_integer=key):
                bad_numeric = copy.deepcopy(strict_artifact)
                bad_numeric[key] = True
                with self.assertRaises(Exception):
                    reconstruct_v3_artifact(bad_numeric, carried_lookup_profile=lookup_profile())
        bad_block_binding = copy.deepcopy(strict_artifact)
        bad_block_binding["block_size"] = 8
        with self.assertRaises(Exception):
            reconstruct_v3_artifact(bad_block_binding, carried_lookup_profile=lookup_profile())

    def test_build_transfer_economic_gate_selects_v3_and_receiver_rebuilds(self) -> None:
        core = require_core()
        chosen = None
        for prefix_pad in range(13):
            for suffix_pad in range(13):
                candidate = {
                    "schema_id": "W7TP_GT_MESH_NODE_SNAPSHOT_V21",
                    "canonical_id": "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1",
                    "version": "2.1",
                    "canonical_binding": canonical_binding(),
                    "source_node_ref": "node:v3source",
                    "logical_time": 1,
                    "observed_at": "2026-08-29T00:00:01Z",
                    "aa_pad": "p" * prefix_pad,
                    "zz_known": "W7TP-KNOWN-A|" * 2000,
                    "zzz_tail": "q" * suffix_pad,
                }
                raw = core.canonical_json_bytes(candidate)
                known_offset = raw.index(b"W7TP-KNOWN-A|")
                if known_offset % 13 == 0 and len(raw) % 13 == 0:
                    chosen = candidate
                    break
            if chosen is not None:
                break
        self.assertIsNotNone(chosen)
        chosen_raw = core.canonical_json_bytes(chosen)
        chosen_v3 = build_v3_artifact(chosen_raw)
        self.assertIsNotNone(chosen_v3)
        self.assertLess(
            len(chosen_v3[1]),
            len(chosen_raw),
            (len(chosen_v3[1]), len(chosen_raw), chosen_v3[0]["block_size"], chosen_v3[0]["known_count"], chosen_v3[0]["novel_count"]),
        )
        with tempfile.TemporaryDirectory(dir="/tmp") as sender_dir, tempfile.TemporaryDirectory(dir="/tmp") as receiver_dir:
            with MeshStorage(sender_dir) as sender, MeshStorage(receiver_dir) as receiver_store:
                transfer = build_transfer(
                    sender,
                    chosen,
                    authority_ref=TOTAL_FIELD_AUTHORITY_REF,
                    namespace="w7tp.mesh.v3",
                    ttl_seconds=300,
                    now=FIXED,
                )
                self.assertEqual("W7TP_ADI_KNOWN_NOVEL_V3", transfer.transfer_mode)
                economic = transfer.profile["transfer"]["economic_gate"]
                self.assertGreater(economic["v3_lookup_profile_bytes"], 0)
                self.assertGreater(economic["v3_lookup_object_packet_bytes"], economic["v3_lookup_profile_bytes"])
                self.assertEqual(
                    economic["selected_marginal_carrier_bytes"],
                    min(
                        value
                        for value in (
                            economic["direct_marginal_carrier_bytes"],
                            economic["single_delta_marginal_carrier_bytes"],
                            economic["v3_marginal_carrier_bytes"],
                        )
                        if value is not None
                    ),
                )
                receipt = MeshReceiver(receiver_store, receiver_node_ref="node:receiver").receive(
                    transfer.carrier, now=FIXED + dt.timedelta(seconds=1)
                )
                self.assertEqual(transfer.target_snapshot_ref, receipt["target_snapshot_ref"])

    def test_economic_gate_counts_lookup_and_can_choose_direct_over_smaller_v3_payload(self) -> None:
        core = require_core()
        chosen = None
        lookup = lookup_profile()
        for repeats in range(20, 161):
            for prefix_pad in range(13):
                for suffix_pad in range(13):
                    candidate = {
                        "source_node_ref": "node:economic",
                        "logical_time": 1,
                        "aa_pad": "p" * prefix_pad,
                        "zz_known": "W7TP-KNOWN-A|" * repeats,
                        "zzz_tail": "q" * suffix_pad,
                    }
                    raw = core.canonical_json_bytes(candidate)
                    if raw.index(b"W7TP-KNOWN-A|") % 13 or len(raw) % 13:
                        continue
                    v3_result = build_v3_artifact(raw, block_sizes=[13])
                    if v3_result is None:
                        continue
                    v3_artifact, v3_raw = v3_result
                    direct_objects = [{"object_ref": core.sha256_ref(raw), "artifact": candidate}]
                    v3_objects = [
                        {"object_ref": core.sha256_ref(v3_raw), "artifact": v3_artifact},
                        {
                            "object_ref": core.sha256_ref(core.canonical_json_bytes(lookup)),
                            "artifact": lookup,
                        },
                    ]
                    direct_cost = len(core.canonical_json_bytes(direct_objects)) - 2
                    v3_cost = len(core.canonical_json_bytes(v3_objects)) - 2
                    if len(v3_raw) < len(raw) and v3_cost > direct_cost:
                        chosen = candidate
                        break
                if chosen is not None:
                    break
            if chosen is not None:
                break
        self.assertIsNotNone(chosen)
        with tempfile.TemporaryDirectory(dir="/tmp") as runtime_dir:
            with MeshStorage(runtime_dir) as storage:
                transfer = build_transfer(
                    storage,
                    chosen,
                    authority_ref=TOTAL_FIELD_AUTHORITY_REF,
                    namespace="w7tp.mesh.economic.test",
                    now=FIXED,
                )
        economic = transfer.profile["transfer"]["economic_gate"]
        self.assertLess(economic["v3_block_token_payload_bytes"], economic["direct_payload_bytes"])
        self.assertGreater(economic["v3_marginal_carrier_bytes"], economic["direct_marginal_carrier_bytes"])
        self.assertEqual("DIRECT_TRANSFER_BASELINE", transfer.transfer_mode)

    def test_user_service_scope_and_container_subobject_metadata(self) -> None:
        service_output = "Id=w7tp.service\nLoadState=loaded\nActiveState=active\nSubState=running\nUnitFileState=enabled\nMainPID=42\n"
        with mock.patch("w7tp_gt_mesh.inventory.platform.system", return_value="Linux"), mock.patch(
            "w7tp_gt_mesh.inventory._run", return_value=(service_output, "OBSERVED")
        ) as run:
            services, probe = _service_metadata([{"name": "w7tp.service", "scope": "user"}])
        self.assertEqual("user", services[0]["scope"])
        self.assertEqual("OBSERVED", probe["state"])
        self.assertEqual(["systemctl", "--user", "show"], run.call_args.args[0][:3])

        rows = [
            ('{"ID":"cid","Image":"repo:tag","Names":"box","State":"running","Status":"Up","Ports":"9191/tcp"}\n', "OBSERVED"),
            ('{"ID":"iid","Repository":"repo","Tag":"tag","Digest":"sha256:abc","Size":"1MB"}\n', "OBSERVED"),
            ('{"Name":"vol","Driver":"local","Scope":"local"}\n', "OBSERVED"),
            ('{"ID":"nid","Name":"net","Driver":"bridge","Scope":"local"}\n', "OBSERVED"),
        ]
        with mock.patch("w7tp_gt_mesh.inventory.shutil.which", return_value="/usr/bin/docker"), mock.patch(
            "w7tp_gt_mesh.inventory._run", side_effect=rows
        ) as run:
            containers, images, volumes, networks, container_probe = _container_metadata(
                {"enabled": True, "engines": ["docker"], "names": []}
            )
        self.assertEqual((1, 1, 1, 1), (len(containers), len(images), len(volumes), len(networks)))
        self.assertEqual("OBSERVED", container_probe["subobject_states"]["images"])
        self.assertEqual(["docker", "images", "--no-trunc"], run.call_args_list[1].args[0][:3])

    def test_bounded_tailscale_peer_topology_safe_fields(self) -> None:
        status = json.dumps(
            {
                "Peer": {
                    "opaque-map-key-not-retained": {
                        "ID": "node-remote-1",
                        "HostName": "phone",
                        "DNSName": "phone.example.ts.net.",
                        "OS": "android",
                        "TailscaleIPs": ["100.64.0.9", "fd7a:115c:a1e0::9"],
                        "Online": True,
                        "Active": False,
                        "KeyExpiry": "2026-12-01T00:00:00Z",
                        "UserID": 42,
                        "PublicKey": "not-retained",
                        "Endpoints": ["203.0.113.1:12345"],
                    }
                }
            }
        )
        with mock.patch("w7tp_gt_mesh.inventory.shutil.which", return_value="/usr/bin/tailscale"), mock.patch(
            "w7tp_gt_mesh.inventory._run", return_value=(status, "OBSERVED")
        ) as run:
            nodes, evidence = _tailscale_peer_topology({"tailscale_peer_limit": 8})
        self.assertEqual(["tailscale", "status", "--json"], run.call_args.args[0])
        self.assertEqual("OBSERVED", evidence["state"])
        self.assertEqual("node-remote-1", nodes[0]["node_id"])
        serialized = json.dumps(nodes, sort_keys=True)
        self.assertNotIn("UserID", serialized)
        self.assertNotIn("PublicKey", serialized)
        self.assertNotIn("Endpoints", serialized)

    def test_core_is_required_and_float_is_rejected(self) -> None:
        core = require_core()
        with self.assertRaises(Exception):
            core.canonical_json_bytes({"bad": 1.25})

    def test_baseline_delta_receive_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as sender_dir, tempfile.TemporaryDirectory(dir="/tmp") as receiver_dir:
            with MeshStorage(sender_dir) as sender, MeshStorage(receiver_dir) as receiver_store:
                first = build_transfer(
                    sender,
                    snapshot(1),
                    authority_ref=TOTAL_FIELD_AUTHORITY_REF,
                    namespace="w7tp.mesh.test",
                    ttl_seconds=300,
                    now=FIXED,
                )
                self.assertEqual("DIRECT_TRANSFER_BASELINE", first.transfer_mode)
                receiver = MeshReceiver(receiver_store, receiver_node_ref="node:receiver")
                first_receipt = receiver.receive(first.carrier, now=FIXED + dt.timedelta(seconds=1))
                self.assertEqual("PASS_EXACT_CANONICAL_JSON_HASH", first_receipt["reconstruction_state"])
                self.assertEqual(first.target_snapshot_ref, first_receipt["target_snapshot_ref"])

                second = build_transfer(
                    sender,
                    snapshot(2),
                    authority_ref=TOTAL_FIELD_AUTHORITY_REF,
                    namespace="w7tp.mesh.test",
                    ttl_seconds=300,
                    now=FIXED + dt.timedelta(seconds=2),
                )
                self.assertEqual("W7TP_GENERATIVE_DELTA", second.transfer_mode)
                second_receipt = receiver.receive(second.carrier, now=FIXED + dt.timedelta(seconds=3))
                self.assertEqual(second.target_snapshot_ref, second_receipt["target_snapshot_ref"])
                self.assertEqual(
                    require_core().canonical_json_bytes(snapshot(2)),
                    receiver_store.get_bytes(second.target_snapshot_ref),
                )
                replay = receiver.receive(second.carrier, now=FIXED + dt.timedelta(seconds=4))
                self.assertEqual("PASS_IDEMPOTENT_ALREADY_RECEIVED", replay["delivery_state"])

    def test_ttl_and_exact_packet_schema_holds(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as sender_dir, tempfile.TemporaryDirectory(dir="/tmp") as receiver_dir:
            with MeshStorage(sender_dir) as sender, MeshStorage(receiver_dir) as receiver_store:
                transfer = build_transfer(
                    sender,
                    snapshot(1),
                    authority_ref=TOTAL_FIELD_AUTHORITY_REF,
                    namespace="w7tp.mesh.test",
                    ttl_seconds=5,
                    now=FIXED,
                )
                validate_packet(transfer.packet)
                bad = copy.deepcopy(transfer.packet)
                bad["unexpected"] = True
                with self.assertRaises(MeshHold):
                    validate_packet(bad)
                replay_mismatch = copy.deepcopy(transfer.packet)
                replay_tuple = replay_mismatch["adi"]["replay_protection"]["tuple"]
                replay_tuple["packet_id"] = "different-packet-id"
                replay_sha = require_core().sha256_hex(require_core().canonical_json_bytes(replay_tuple))
                replay_mismatch["adi"]["replay_protection"]["tuple_sha256"] = replay_sha
                replay_mismatch["adi"]["packet_layer"]["decision_index"] = replay_sha
                replay_mismatch["envelope"]["canonical_json_sha256"] = self_hash_excluding(
                    replay_mismatch,
                    container_key="envelope",
                    hash_key="canonical_json_sha256",
                )
                with self.assertRaises(MeshConflict):
                    validate_packet(replay_mismatch)
                time_mismatch = copy.deepcopy(transfer.packet)
                time_mismatch["adi"]["system_layer"]["logical_time"] = 2
                time_mismatch["lineage"]["logical_time"] = 3
                time_mismatch["envelope"]["canonical_json_sha256"] = self_hash_excluding(
                    time_mismatch,
                    container_key="envelope",
                    hash_key="canonical_json_sha256",
                )
                with self.assertRaises(MeshConflict):
                    validate_packet(time_mismatch)
                profile_mismatch = copy.deepcopy(transfer.profile)
                profile_mismatch["nonce"] = "fedcba9876543210"
                with self.assertRaises(MeshConflict):
                    validate_packet_profile_binding(transfer.packet, profile_mismatch)
                flat = copy.deepcopy(transfer.profile)
                flat["coupling"]["flat_field_model"] = True
                with self.assertRaises(MeshHold):
                    validate_domain_profile(flat)
                receiver = MeshReceiver(receiver_store, receiver_node_ref="node:receiver")
                with self.assertRaises(MeshHold) as captured:
                    receiver.receive(transfer.carrier, now=FIXED + dt.timedelta(seconds=6))
                self.assertEqual("HOLD_PACKET_TTL_EXPIRED", captured.exception.code)

    def test_pinned_machine_schema_if_available(self) -> None:
        schema_path = os.environ.get("W7TP_V21_SCHEMA_PATH")
        if not schema_path or not Path(schema_path).is_file():
            self.skipTest("pinned machine schema path not supplied")
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema verifier unavailable")
        with tempfile.TemporaryDirectory(dir="/tmp") as sender_dir:
            with MeshStorage(sender_dir) as sender:
                transfer = build_transfer(
                    sender,
                    snapshot(1),
                    authority_ref=TOTAL_FIELD_AUTHORITY_REF,
                    namespace="w7tp.mesh.test",
                    now=FIXED,
                )
                schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
                jsonschema.Draft202012Validator(schema).validate(transfer.packet)

    def test_drive_projection_and_07_github_gate(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as sender_dir, tempfile.TemporaryDirectory(dir="/tmp") as spool_dir:
            with MeshStorage(sender_dir) as sender:
                projected_snapshot = snapshot(1, git=True)
                projected_snapshot["discovered_nodes"] = [
                    {
                        "node_id": "remote-1",
                        "node_name": "phone",
                        "dns_name": "phone.example.ts.net.",
                        "operating_system": "android",
                        "addresses": ["100.64.0.9"],
                        "online": True,
                        "active": False,
                        "key_expiry": "2026-12-01T00:00:00Z",
                        "observation_state": "OBSERVED",
                    }
                ]
                transfer = build_transfer(
                    sender,
                    projected_snapshot,
                    authority_ref=TOTAL_FIELD_AUTHORITY_REF,
                    namespace="w7tp.mesh.test",
                    now=FIXED,
                )
                lineage = next(item for item in sender.journal.records("lineage") if item["packet_ref"] == transfer.packet_ref)
                paths = produce_drive_projection_envelopes(
                    spool_dir,
                    snapshot=projected_snapshot,
                    packet=transfer.packet,
                    profile=transfer.profile,
                    lineage=lineage,
                )
                self.assertTrue(any("07_GITHUB" in path.parts for path in paths))
                self.assertTrue(any("discovered" in path.parts and "remote-1" in path.parts for path in paths))
                core = require_core()
                for path in paths:
                    envelope = core.canonical_json_loads(path.read_bytes(), require_canonical=True)
                    claimed = envelope.pop("envelope_sha256")
                    self.assertEqual(claimed, core.sha256_hex(core.canonical_json_bytes(envelope)))
                producer = DriveSpoolProducer(spool_dir)
                with self.assertRaises(MeshHold):
                    producer.emit(
                        "07_GITHUB/source/bad.json",
                        {"dimension": "D3_COORDINATE"},
                        source_node_ref="node:source",
                        packet_id="packet",
                        logical_time=1,
                    )

    def test_http_push_receive_spool_and_performance_evidence(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as sender_dir, tempfile.TemporaryDirectory(dir="/tmp") as receiver_dir, tempfile.TemporaryDirectory(dir="/tmp") as spool_dir:
            with MeshStorage(sender_dir) as sender:
                transfer = build_transfer(
                    sender,
                    snapshot(1, git=True),
                    authority_ref=TOTAL_FIELD_AUTHORITY_REF,
                    namespace="w7tp.mesh.test",
                    ttl_seconds=3600,
                )
                config = {
                    "node_id": "receiver",
                    "logical_root_id": "mesh-test",
                    "runtime_root": receiver_dir,
                    "drive_spool_root": spool_dir,
                }
                with MeshRuntime(config) as receiver_runtime:
                    server = make_server(receiver_runtime, "127.0.0.1", 0, 8 * 1024 * 1024)
                    thread = threading.Thread(target=server.serve_forever, daemon=True)
                    thread.start()
                    try:
                        result = MeshTransport(sender).send(
                            transfer.carrier,
                            carrier_ref=transfer.carrier_ref,
                            peer_url=f"http://127.0.0.1:{server.server_address[1]}",
                        )
                    finally:
                        server.shutdown()
                        server.server_close()
                        thread.join(timeout=5)
                self.assertEqual(transfer.packet_ref, result["packet_ref"])
                self.assertEqual(transfer.target_snapshot_ref, result["target_snapshot_ref"])
                self.assertGreater(result["carrier_bytes"], 0)
                self.assertGreater(result["receipt_bytes"], 0)
                self.assertGreater(result["round_trip_ns"], 0)
                self.assertEqual(
                    "OBJECT_PACKET_COST_NOT_COMPLETE_HTTP_BENCHMARK",
                    result["economic_gate_scope"],
                )
                self.assertEqual(
                    "CODEC_COMPATIBILITY_ONLY_NOT_MESH_END_TO_END_BENCHMARK",
                    result["w7g3_fixed_vector_relation"],
                )
                self.assertTrue(any("08_RECEIPTS" in path.parts for path in Path(spool_dir).rglob("*.json")))

    def test_cycle_collect_spool_and_each_peer(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as runtime_dir, tempfile.TemporaryDirectory(dir="/tmp") as spool_dir:
            config = {
                "node_id": "source",
                "logical_root_id": "mesh-test",
                "runtime_root": runtime_dir,
                "drive_spool_root": spool_dir,
                "services": [],
                "containers": {"enabled": False},
                "listeners": {"enabled": False},
                "curated_files": [],
                "git_evidence_roots": [],
                "peers": [
                    {"peer_id": "one", "url": "http://127.0.0.1:9998"},
                    {"peer_id": "two", "url": "http://127.0.0.1:9999"},
                ],
            }
            with MeshRuntime(config) as runtime:
                with mock.patch.object(
                    runtime.transport,
                    "send",
                    side_effect=[{"delivery_state": "PASS_ONE"}, {"delivery_state": "PASS_TWO"}],
                ) as send:
                    result = runtime.cycle()
                self.assertEqual(2, send.call_count)
                self.assertEqual(2, len(result["peer_results"]))
                self.assertGreater(result["drive_projection_count"], 0)

    def test_artifacts_do_not_embed_raw_technical_secrets(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as runtime_dir:
            with MeshStorage(runtime_dir) as storage:
                transfer = build_transfer(
                    storage,
                    snapshot(1),
                    authority_ref=TOTAL_FIELD_AUTHORITY_REF,
                    namespace="w7tp.mesh.test",
                    now=FIXED,
                )
                text = require_core().canonical_json_bytes(
                    {"packet": transfer.packet, "profile": transfer.profile, "carrier": transfer.carrier}
                ).decode("utf-8").lower()
                self.assertNotIn("raw_credential", text)
                self.assertNotIn("secret_value", text)


if __name__ == "__main__":
    unittest.main()
