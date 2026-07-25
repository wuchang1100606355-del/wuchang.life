from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from tools.total_field.w7tp_field_application_runtime import (
    CAPABILITY_REGISTRY_PATH,
    SCENARIO_ROUTE_TABLE_PATH,
    FieldApplicationError,
    main as legacy_main,
)
import tools.cloud_proxy.w7tp_openwebui_cloud_proxy as cloud_proxy
from tools.total_field.w7tp_bundle_installer import (
    BundleInstallError as BootstrapInstallError,
    install_bundle as bootstrap_install_bundle,
)
from tools.total_field.w7tp_intent_field_suite.adaptive_cognition import (
    build_cognition_update_candidate,
)
from tools.total_field.w7tp_intent_field_suite.api import PRODUCT_HTML
from tools.cloud_proxy.w7tp_openwebui_cloud_proxy import H
from tools.total_field.w7tp_intent_field_suite.canonical_hash import canonical_sha256
from tools.total_field.w7tp_intent_field_suite.cli import _release_files
from tools.total_field.w7tp_intent_field_suite.deployment import (
    ROOT,
    build_deployment_manifest,
    build_release_bundle,
    file_sha256,
    install_release_bundle,
)
from tools.total_field.w7tp_intent_field_suite.drift_monitor import evaluate_drift
from tools.total_field.w7tp_intent_field_suite.edge_queue import (
    build_sealed_snapshot,
    enqueue_packet,
    revalidate_queue,
    revalidate_queue_file,
)
from tools.total_field.w7tp_intent_field_suite.gpu_scheduler import select_execution_policy
from tools.total_field.w7tp_intent_field_suite.node_inventory import (
    parse_docker_ps_json,
    parse_tailscale_status,
)
from tools.total_field.w7tp_intent_field_suite.packet_builder import process_intent


COMPLETE_INTENTS = {
    "ASSOCIATION": {
        "requested_result": "社區服務候選",
        "service_goal": "活動規劃",
        "activity_type": "社區活動",
        "time_range": "本月",
        "audience_category": "一般居民",
    },
    "PROPERTY": {
        "requested_result": "設備檢查候選",
        "device_anonymous_id": "公共設備-A",
        "inspection_scope": "安全項目",
        "risk_level": "中",
    },
    "CAFE_POS": {
        "requested_result": "商品候選",
        "product_candidate": "飲品候選",
        "category": "咖啡",
        "price_candidate": "依現有價目",
    },
    "HOUSEHOLD": {
        "requested_result": "提醒候選",
        "reminder_content": "日常事項",
        "reminder_time": "明天",
        "anonymous_role": "家人角色-A",
    },
    "GENERIC": {
        "requested_result": "分析候選",
        "constraints": "只讀",
        "evidence_refs": ["repo 正典"],
    },
}


class W7TPIntentFieldSuiteTest(unittest.TestCase):
    @staticmethod
    def _cafe_pos_total_field_request(**context_overrides):
        context = {
            "request_id": "odoo-cafe:" + "a" * 32,
            "caller_ref": "odoo-pos-config:wuchang_core.pos_config_re_main",
            "observation_domain_ref": "observation-domain:odoo-cafe:opaque",
            "receiver_ref": "tools.total_field_candidate_gateway.receive_candidate",
            "merchant_mode": "INDEPENDENT_MERCHANT_OUTSIDE_COMMUNITY",
            "community_happiness_coin_accepted": False,
            "consumer_happiness_coin_issued": False,
            "community_merchant_ticket_quota": False,
            "fund_1_to_1_to_1_binding": False,
        }
        context.update(context_overrides)
        return {
            "profile": "CAFE_POS",
            "intent": COMPLETE_INTENTS["CAFE_POS"],
            "receiver_context": context,
        }

    def test_a01_a02_five_profiles_share_runtime_and_correct_packet_types(self) -> None:
        route_table = json.loads(SCENARIO_ROUTE_TABLE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(set(route_table["routes"]), set(COMPLETE_INTENTS))
        for profile, intent in COMPLETE_INTENTS.items():
            with self.subTest(profile=profile):
                result = process_intent(profile, intent)
                self.assertEqual(result["profile"], profile)
                self.assertEqual(result["D3"]["packet_type"], route_table["routes"][profile]["packet_type"])
                self.assertEqual(result["D5"]["shared_runtime"], "tools/total_field/w7tp_field_application_runtime.py")
                self.assertEqual(set(result).intersection({f"D{n}" for n in range(1, 9)}), {f"D{n}" for n in range(1, 9)})
                self.assertEqual(len(result["content_sha256"]), 64)

    def test_a03_unknown_profile_and_capability_mismatch_hold(self) -> None:
        with self.assertRaises(FieldApplicationError) as caught:
            process_intent("UNKNOWN", {})
        self.assertEqual(caught.exception.reason_code, "SCENARIO_NOT_REGISTERED")

        route_table = json.loads(SCENARIO_ROUTE_TABLE_PATH.read_text(encoding="utf-8"))
        registry = json.loads(CAPABILITY_REGISTRY_PATH.read_text(encoding="utf-8"))
        route_table["routes"]["GENERIC"]["capability_ref"] = "MISSING"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            route_path = root / "route.json"
            registry_path = root / "registry.json"
            route_path.write_text(json.dumps(route_table), encoding="utf-8")
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            with self.assertRaises(FieldApplicationError) as mismatch:
                process_intent("GENERIC", COMPLETE_INTENTS["GENERIC"], route_table_path=route_path, capability_registry_path=registry_path)
        self.assertEqual(mismatch.exception.reason_code, "SCENARIO_CAPABILITY_REGISTRY_MISMATCH")

    def test_a04_guided_completion_is_one_question_and_preserves_state_chain(self) -> None:
        intent = {"requested_result": "分析候選"}
        first = process_intent("GENERIC", intent)
        self.assertEqual(first["state"], "NEEDS_USER_GUIDED_COMPLETION")
        self.assertEqual(first["question"]["question_id"], "generic.constraints")
        self.assertEqual(len(first["question"]["options"]), 3)
        second = process_intent(
            "GENERIC",
            intent,
            state_id=first["state_id"],
            question_id=first["question"]["question_id"],
            answer="只讀",
        )
        self.assertEqual(second["state"], "NEEDS_USER_GUIDED_COMPLETION")
        self.assertEqual(second["question"]["question_id"], "generic.evidence_refs")
        self.assertNotEqual(first["state_id"], second["state_id"])
        self.assertEqual(first["intent_content_sha256"], canonical_sha256(intent))

    def test_a04_complete_input_asks_zero_questions(self) -> None:
        result = process_intent("GENERIC", COMPLETE_INTENTS["GENERIC"])
        self.assertNotIn("question", result)
        self.assertEqual(result["D8"]["decision"], "PENDING_TOTAL_FIELD_REVIEW")
        self.assertEqual(result["redteam_drift_monitor"]["status"], "MONITORING_CLEAR")
        self.assertEqual(result["D7"]["drift_alert_count"], 0)

    def test_a04_redteam_monitor_is_always_on_during_guided_completion(self) -> None:
        result = process_intent("GENERIC", {"requested_result": "分析候選"})
        monitor = result["redteam_drift_monitor"]
        self.assertEqual(monitor["mode"], "ALWAYS_ON_EVERY_STATE_TRANSITION")
        self.assertEqual(monitor["perspective"], "REDTEAM")
        self.assertEqual(monitor["llm_execution"], "NONE_DETERMINISTIC_RULES")
        self.assertFalse(monitor["input_retained"])
        self.assertFalse(monitor["input_echoed"])

    def test_a04_redteam_drift_alert_holds_before_guided_continuation(self) -> None:
        raw = "生成式傳輸是檔案搬運"
        result = process_intent("GENERIC", {"requested_result": raw})
        self.assertEqual(result["state"], "HOLD_DETOUR_ALERT")
        self.assertEqual(result["D8"]["decision"], "HOLD_DETOUR_ALERT")
        self.assertEqual(result["redteam_drift_monitor"]["status"], "DRIFT_ALERT")
        self.assertIn(
            "GT_CORE_DEFINITION_DRIFT",
            result["D7"]["drift_alert_codes"],
        )
        self.assertNotIn(raw, json.dumps(result, ensure_ascii=False))

    def test_a04_user_device_llm_statement_does_not_false_alert(self) -> None:
        monitor = evaluate_drift({"requested_result": "llm不在伺服器運行在使用者設備運行"})
        self.assertEqual(monitor["status"], "MONITORING_CLEAR")

    def test_a05_sensitive_content_blocks_before_packet_or_hash(self) -> None:
        for intent in (
            {"password": "fixture-value"},
            {"requested_result": "write to person@example.test"},
            {"raw_audio": "fixture"},
        ):
            with self.subTest(intent=list(intent)):
                with self.assertRaises(FieldApplicationError) as caught:
                    process_intent("GENERIC", intent)
                self.assertIn(caught.exception.reason_code, {"SENSITIVE_INTENT_BLOCKED", "SENSITIVE_VALUE_BLOCKED"})
                self.assertNotIn("fixture-value", str(caught.exception))

    def test_a05_sensitive_http_hold_includes_redteam_code_without_echo(self) -> None:
        raw = "person@example.test"
        status, result = cloud_proxy.process_http_request(
            json.dumps(
                {"profile": "GENERIC", "intent": {"requested_result": raw}}
            ).encode()
        )
        self.assertEqual(status, 422)
        self.assertEqual(result["redteam_drift_monitor"]["status"], "DRIFT_ALERT")
        self.assertEqual(
            result["redteam_drift_monitor"]["alerts"][0]["code"],
            "SENSITIVE_DATA_BOUNDARY_ALERT",
        )
        self.assertNotIn(raw, json.dumps(result))

    def test_a06_authority_escalation_blocks(self) -> None:
        for key in ("d8_decision", "founder_command_ref", "formal_execution_authority"):
            with self.subTest(key=key):
                with self.assertRaises(FieldApplicationError) as caught:
                    process_intent("GENERIC", {key: "ALLOW"})
                self.assertEqual(caught.exception.reason_code, "AUTHORITY_ESCALATION_BLOCKED")

    def test_a07_determinism_unicode_and_execution_metadata_exclusion(self) -> None:
        first_intent = dict(COMPLETE_INTENTS["GENERIC"], requested_result="Cafe\u0301 候選")
        second_intent = dict(COMPLETE_INTENTS["GENERIC"], requested_result="Café 候選")
        first = process_intent("GENERIC", first_intent, execution_metadata={"observed_at": "one"})
        second = process_intent("GENERIC", second_intent, execution_metadata={"observed_at": "two"})
        self.assertEqual(first["content_sha256"], second["content_sha256"])
        self.assertNotEqual(first["execution_metadata"], second["execution_metadata"])

    def test_a08_gt_semantics_are_packet_native(self) -> None:
        result = process_intent("GENERIC", COMPLETE_INTENTS["GENERIC"])
        d6 = result["D6"]
        self.assertEqual(d6["generative_transmission"], "PROTOCOL_NATIVE_8D_STATE_FIELD_PACKET")
        self.assertTrue(d6["references"] and d6["lookup"] and d6["packet_carried_protocol"])
        self.assertTrue(d6["effect_equivalence_conditions"]["local_state_machine_judgment_required"])

    def test_a08_every_complete_packet_has_positioned_thing_and_field_edge_codes(self) -> None:
        result = process_intent("GENERIC", COMPLETE_INTENTS["GENERIC"])
        encoding = result["field_encoding"]
        self.assertEqual(set(encoding["dimensions"]), {f"D{index}" for index in range(1, 9)})
        self.assertFalse(encoding["formal_execution_authority"])
        for dimension, record in encoding["dimensions"].items():
            with self.subTest(dimension=dimension):
                self.assertTrue(record["thing_code"].startswith("W7TP_THING_REF:v1:"))
                self.assertTrue(
                    record["field_edge_code"].startswith(
                        f"W7TP_FIELD_EDGE_REF:v1:{dimension}:"
                    )
                )

    def test_a09_status_parser_tolerates_peer_map_and_redacts_identity_fields(self) -> None:
        status = {
            "Self": {"HostName": "taiji01", "OS": "linux", "Online": True, "TailscaleIPs": ["100.64.0.1"], "UserID": 42},
            "Peer": {
                "key": {"HostName": "phone", "OS": "iOS", "Online": True, "TailscaleIPs": ["100.64.0.2"], "UserID": 42}
            },
            "User": {"42": {"LoginName": "owner@example.test"}},
        }
        authority = {
            "nodes": [
                {"hostname": "taiji01", "authority": "OWNER_AUTHORIZED", "connection_method": "LOCAL_SHELL"},
                {"hostname": "phone", "authority": "OWNER_AUTHORIZED", "connection_method": None},
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "authority.json"
            path.write_text(json.dumps(authority), encoding="utf-8")
            report = parse_tailscale_status(status, authority_registry_path=path)
        encoded = json.dumps(report)
        self.assertNotIn("100.64", encoded)
        self.assertNotIn("owner@", encoded)
        self.assertEqual({node["base_transport_state"] for node in report["nodes"]}, {"INSTALLED_UNUSABLE", "CLIENT_ONLY"})
        self.assertEqual(report["scope"], "ALL_NODES_AND_CONTAINERS")
        self.assertFalse(report["runtime_mutation_authority"])
        self.assertTrue(report["containers"])
        self.assertTrue(all(not item["runtime_mutation_authority"] for item in report["containers"]))

    def test_a09_container_inventory_is_total_field_governed_without_mutation(self) -> None:
        live = json.dumps(
            {
                "Names": "wuchang_os_odoo_18",
                "Image": "odoo:18.0",
                "State": "running",
                "Status": "Up healthy",
                "Ports": "127.0.0.1:8069->8069/tcp, 8071-8072/tcp",
                "Labels": "must-not-be-returned",
                "Mounts": "must-not-be-returned",
            }
        )
        result = parse_docker_ps_json(live)
        odoo = next(item for item in result["containers"] if item["name"] == "wuchang_os_odoo_18")
        encoded = json.dumps(result)
        self.assertEqual(result["probe_state"], "LIVE_DOCKER_PS_READ_ONLY")
        self.assertEqual(odoo["governance_state"], "TOTAL_FIELD_GOVERNED_READ_ONLY")
        self.assertEqual(odoo["total_field_authority"], "OBSERVE_INDEX_CLASSIFY_ROUTE_WARN_SEAL")
        self.assertFalse(odoo["runtime_mutation_authority"])
        self.assertEqual(odoo["port_scope"], "LOCAL_ONLY")
        self.assertNotIn("must-not-be-returned", encoded)
        self.assertNotIn("127.0.0.1", encoded)

    def test_a10_cpu_is_complete_and_cloud_stays_blocked(self) -> None:
        cpu = select_execution_policy()
        llm = select_execution_policy({"usable": True, "owner_verified": True}, workload="INFERENCE")
        gpu = select_execution_policy({"usable": True, "owner_verified": True}, workload="AUDIO_VIDEO")
        self.assertEqual(cpu["execution_mode"], "CPU_BASELINE")
        self.assertTrue(cpu["cpu_complete"])
        self.assertEqual(cpu["cloud_fallback"], "BLOCK")
        self.assertEqual(llm["execution_mode"], "USER_DEVICE_LLM")
        self.assertEqual(llm["execution_location"], "USER_DEVICE_ONLY")
        self.assertFalse(llm["gpu_selected"])
        self.assertEqual(llm["server_llm_execution"], "BLOCK")
        self.assertEqual(llm["raw_prompt_upload"], "BLOCK")
        self.assertEqual(gpu["execution_mode"], "GPU_SUPPORT")
        self.assertEqual(gpu["gpu_authority"], "CANDIDATE_EXECUTION_ONLY")

    def test_a10_device_llm_boundary_is_immutable(self) -> None:
        with self.assertRaises(FieldApplicationError) as caught:
            build_cognition_update_candidate(
                {"llm_inference_location": "SERVER"}, ["evidence:test"]
            )
        self.assertEqual(caught.exception.reason_code, "COGNITION_IMMUTABLE_CONTROL_BLOCKED")

    def test_a11_a12_adaptive_cognition_cannot_change_authority(self) -> None:
        candidate = build_cognition_update_candidate(
            {"ui_detail_level": "CONCISE"}, ["evidence:test"]
        )
        self.assertEqual(candidate["state"], "COGNITION_UPDATE_CANDIDATE")
        with self.assertRaises(FieldApplicationError) as caught:
            build_cognition_update_candidate(
                {"d8_authority": "AI"}, ["evidence:test"]
            )
        self.assertEqual(caught.exception.reason_code, "COGNITION_IMMUTABLE_CONTROL_BLOCKED")

    def test_a11_offline_edge_never_assigns_d8_and_revalidates_hash_chain(self) -> None:
        snapshot = build_sealed_snapshot()
        first = process_intent("GENERIC", COMPLETE_INTENTS["GENERIC"])
        second_intent = dict(
            COMPLETE_INTENTS["GENERIC"], requested_result="內容候選"
        )
        second = process_intent("GENERIC", second_intent)
        with tempfile.TemporaryDirectory() as directory:
            queue_path = Path(directory) / "edge-queue.json"
            queued_first = enqueue_packet(
                queue_path, first, snapshot, node_id="penguin"
            )
            duplicate = enqueue_packet(
                queue_path, first, snapshot, node_id="penguin"
            )
            queued_second = enqueue_packet(
                queue_path, second, snapshot, node_id="penguin"
            )
            report = revalidate_queue_file(queue_path, snapshot)
            self.assertEqual(queued_first["queue_depth"], 1)
            self.assertEqual(duplicate["state"], "ALREADY_QUEUED")
            self.assertEqual(queued_second["queue_depth"], 2)
            self.assertEqual(report["accepted_count"], 2)
            self.assertFalse(report["formal_d8_assigned"])
            self.assertEqual(queue_path.stat().st_mode & 0o777, 0o600)

            entries = json.loads(queue_path.read_text(encoding="utf-8"))
            duplicate_report = revalidate_queue(
                entries,
                snapshot,
                seen_candidate_hashes=[first["content_sha256"]],
            )
            self.assertEqual(duplicate_report["deduplicated_count"], 1)
            entries[1]["previous_entry_sha256"] = "0" * 64
            with self.assertRaises(FieldApplicationError) as caught:
                revalidate_queue(entries, snapshot)
            self.assertIn(
                caught.exception.reason_code,
                {"EDGE_QUEUE_ENTRY_SHA256_MISMATCH", "EDGE_QUEUE_CHAIN_MISMATCH"},
            )

    def test_a13_legacy_cli_contract_remains_compatible(self) -> None:
        with patch("builtins.print") as output:
            code = legacy_main(["GENERIC", '{"requested_result":"candidate"}'])
        self.assertEqual(code, 0)
        self.assertTrue(output.called)

    def test_a13_suite_entrypoint_runs_without_pythonpath(self) -> None:
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/total_field/w7tp_field_application_runtime.py"),
                "suite",
                "policy",
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('"policy_hash"', completed.stdout)

    def test_a14_a15_a17_release_is_byte_exact_and_has_rollback(self) -> None:
        files = [
            ROOT / "tools/total_field/w7tp_field_application_runtime.py",
            ROOT / "tools/total_field/w7tp_intent_field_suite/packet_builder.py",
        ]
        manifest = build_deployment_manifest(files, "W7TP_INTENT_FIELD_TEST_001")
        self.assertEqual(manifest["artifact_transport"], "BYTE_EXACT_SHA256")
        self.assertEqual(manifest["rollback"]["mode"], "ATOMIC_RELEASE_POINTER_RESTORE")
        self.assertFalse(manifest["db_write"] or manifest["dns_write"] or manifest["router_write"])
        with tempfile.TemporaryDirectory() as directory:
            first = build_release_bundle(files, Path(directory), "W7TP_INTENT_FIELD_TEST_001")
            first_hash = first["manifest"]["artifact"]["sha256"]
            second = build_release_bundle(files, Path(directory), "W7TP_INTENT_FIELD_TEST_001")
            self.assertEqual(first_hash, second["manifest"]["artifact"]["sha256"])

    def test_a14_a15_atomic_install_health_failure_restores_previous(self) -> None:
        files = [
            ROOT / "tools/total_field/w7tp_field_application_runtime.py",
            ROOT / "tools/total_field/w7tp_intent_field_suite/packet_builder.py",
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = build_release_bundle(
                files, root / "bundle-a", "W7TP_INTENT_FIELD_INSTALL_A"
            )
            first_result = install_release_bundle(
                Path(first["artifact_path"]),
                Path(first["manifest_path"]),
                root / "install",
                health_check=lambda _path: True,
            )
            self.assertEqual(first_result["state"], "PASS")
            first_target = (root / "install/current").resolve()

            second = build_release_bundle(
                files, root / "bundle-b", "W7TP_INTENT_FIELD_INSTALL_B"
            )
            second_id = second["manifest"]["content_sha256"][:16]

            def staged_pass_promoted_fail(path: Path) -> bool:
                return path.name != second_id

            with self.assertRaises(FieldApplicationError) as caught:
                install_release_bundle(
                    Path(second["artifact_path"]),
                    Path(second["manifest_path"]),
                    root / "install",
                    health_check=staged_pass_promoted_fail,
                )
            self.assertEqual(
                caught.exception.reason_code,
                "DEPLOYMENT_HEALTH_FAILED_ROLLED_BACK",
            )
            self.assertEqual((root / "install/current").resolve(), first_target)

    def test_a14_full_release_installs_with_isolated_default_health(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = build_release_bundle(
                _release_files(),
                root / "bundle",
                "W7TP_INTENT_FIELD_FULL_INSTALL_TEST",
            )
            result = install_release_bundle(
                Path(bundle["artifact_path"]),
                Path(bundle["manifest_path"]),
                root / "install",
            )
            self.assertEqual(result["state"], "PASS")
            self.assertEqual(result["health"], "PASS")
            self.assertEqual(result["reloads_or_restarts"], [])
            self.assertTrue((root / "install/current").is_symlink())

    def test_a14_offline_node_bundle_has_self_contained_installer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = build_release_bundle(
                _release_files(),
                root / "bundle",
                "W7TP_INTENT_FIELD_OFFLINE_NODE_TEST",
            )
            bootstrap = bundle["bootstrap_installer"]
            bootstrap_path = Path(bootstrap["path"])
            self.assertTrue(bootstrap_path.is_file())
            self.assertEqual(file_sha256(bootstrap_path), bootstrap["sha256"])
            self.assertEqual(bootstrap_path.stat().st_size, bootstrap["size"])
            self.assertEqual(
                bundle["exact_install_command"],
                "python3 "
                + bootstrap_path.name
                + " --artifact "
                + Path(bundle["artifact_path"]).name
                + " --manifest "
                + Path(bundle["manifest_path"]).name
                + " --install-root ~/.local/share/w7tp-intent-field",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(bootstrap_path),
                    "--artifact",
                    bundle["artifact_path"],
                    "--manifest",
                    bundle["manifest_path"],
                    "--install-root",
                    str(root / "offline-install"),
                ],
                cwd=root / "bundle",
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            installed = json.loads(completed.stdout)
            self.assertEqual(installed["state"], "PASS")
            self.assertFalse(installed["service_mutation"])
            self.assertEqual(
                (root / "offline-install/current").resolve().name,
                bundle["manifest"]["content_sha256"][:16],
            )

    def test_a14_offline_node_installer_rejects_tampered_artifact(self) -> None:
        files = [
            ROOT / "tools/total_field/w7tp_field_application_runtime.py",
            ROOT / "tools/total_field/w7tp_bundle_installer.py",
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = build_release_bundle(
                files,
                root / "bundle",
                "W7TP_INTENT_FIELD_OFFLINE_TAMPER_TEST",
            )
            artifact_path = Path(bundle["artifact_path"])
            with artifact_path.open("ab") as handle:
                handle.write(b"tamper")
            completed = subprocess.run(
                [
                    sys.executable,
                    bundle["bootstrap_installer"]["path"],
                    "--artifact",
                    str(artifact_path),
                    "--manifest",
                    bundle["manifest_path"],
                    "--install-root",
                    str(root / "rejected-install"),
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(completed.returncode, 2)
            rejection = json.loads(completed.stdout)
            self.assertEqual(
                rejection,
                {
                    "reason_code": "DEPLOYMENT_ARTIFACT_SHA256_MISMATCH",
                    "state": "HOLD",
                },
            )
            self.assertFalse((root / "rejected-install/current").exists())

    def test_a15_offline_node_installer_restores_previous_release(self) -> None:
        first_files = [
            ROOT / "tools/total_field/w7tp_field_application_runtime.py",
            ROOT / "tools/total_field/w7tp_bundle_installer.py",
        ]
        second_files = first_files + [
            ROOT / "tools/total_field/w7tp_intent_field_suite/packet_builder.py",
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = build_release_bundle(
                first_files,
                root / "bundle-a",
                "W7TP_INTENT_FIELD_OFFLINE_ROLLBACK_A",
            )
            second = build_release_bundle(
                second_files,
                root / "bundle-b",
                "W7TP_INTENT_FIELD_OFFLINE_ROLLBACK_B",
            )
            with patch(
                "tools.total_field.w7tp_bundle_installer._health_pass",
                return_value=True,
            ):
                installed = bootstrap_install_bundle(
                    Path(first["artifact_path"]),
                    Path(first["manifest_path"]),
                    root / "install",
                )
            self.assertEqual(installed["state"], "PASS")
            previous = (root / "install/current").resolve()
            second_id = second["manifest"]["content_sha256"][:16]

            def stage_and_previous_only(path: Path) -> bool:
                return path.name != second_id

            with patch(
                "tools.total_field.w7tp_bundle_installer._health_pass",
                side_effect=stage_and_previous_only,
            ):
                with self.assertRaises(BootstrapInstallError) as caught:
                    bootstrap_install_bundle(
                        Path(second["artifact_path"]),
                        Path(second["manifest_path"]),
                        root / "install",
                    )
            self.assertEqual(
                caught.exception.reason_code,
                "DEPLOYMENT_HEALTH_FAILED_ROLLED_BACK",
            )
            self.assertEqual((root / "install/current").resolve(), previous)

    def test_a14_offline_node_installer_rejects_mutated_release_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = build_release_bundle(
                _release_files(),
                root / "bundle",
                "W7TP_INTENT_FIELD_OFFLINE_IMMUTABLE_TEST",
            )
            command = [
                sys.executable,
                bundle["bootstrap_installer"]["path"],
                "--artifact",
                bundle["artifact_path"],
                "--manifest",
                bundle["manifest_path"],
                "--install-root",
                str(root / "install"),
            ]
            installed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(installed.returncode, 0, installed.stderr + installed.stdout)
            ((root / "install/current").resolve() / "unexpected-file").write_text(
                "mutation",
                encoding="utf-8",
            )
            rejected = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(rejected.returncode, 2)
            self.assertEqual(
                json.loads(rejected.stdout),
                {
                    "reason_code": "DEPLOYMENT_EXISTING_RELEASE_CONFLICT",
                    "state": "HOLD",
                },
            )

    def test_a14_release_contains_nonprofit_commercial_boundary_sources(self) -> None:
        expected = {
            "web/governance/index.html",
            "web/property_management/index.html",
            "web/pos_promo_sandbox/index.html",
            "web/assets/cafe-pos-menu-data.js",
            "web/assets/cafe-pos-staff-flow.js",
            "web/assets/cafe-pos-ai-intent.js",
            "web/assets/cafe-pos-demo.css",
            "web/assets/cafe-pos-demo.js",
            "web/total_field_review/index.html",
            "web/total_field_review/envelope.html",
            "tests/test_cafe_pos_demo.py",
            "scripts/verify/verify_cafe_pos_browser_product.py",
            "tools/total_field/quickclick_menu_snapshot.py",
            "tools/total_field/cafe_pos_local_llm_acceptance.py",
            "tools/total_field/w7tp_bundle_installer.py",
            "docs/operations/CAFE_POS_HUMAN_AI_DESIGN_BENCHMARK_20260716.md",
            "tools/total_field/w7tp_intent_field_suite/identity_prefix.py",
            "schemas/field/w7tp_natural_person_identity_prefix.schema.json",
            "tests/test_w7tp_natural_person_identity_prefix.py",
            "docs/total_field/W7TP_MEMBER_AI_LLM_PREFIX_POLICY.md",
            "configs/w7tp_member_llm_prefix_policy.example.json",
            "runtime/total_field/shared_intent_field/W7TP_SHARED_8D_CAFE_POS_20260716T175836Z/cloud-menu-source/quickclick-menu-snapshot.json",
            "runtime/total_field/shared_intent_field/W7TP_SHARED_8D_CAFE_POS_20260716T175836Z/cloud-menu-source/README.md",
        }
        packaged = {path.relative_to(ROOT).as_posix() for path in _release_files()}
        self.assertTrue(expected.issubset(packaged))


    def test_runtime_node_authority_snapshot_is_minimized_and_source_bound(self) -> None:
        path = (
            ROOT
            / "manifests/w7tp_small_agent_node_authority_v0_1/node_authority_registry_runtime_minimized.json"
        )
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        source = ROOT / snapshot["source_path"]
        self.assertEqual(snapshot["snapshot_class"], "DERIVED_NON_AUTHORITATIVE_READ_ONLY")
        self.assertEqual(
            snapshot["source_sha256"],
            __import__("hashlib").sha256(source.read_bytes()).hexdigest(),
        )
        serialized = json.dumps(snapshot, ensure_ascii=False)
        for forbidden in ("address", "ssh_user", "owner_email", "100.", "192.168."):
            self.assertNotIn(forbidden, serialized)

    def test_schemas_accept_generated_artifacts(self) -> None:
        guided = process_intent("GENERIC", {"requested_result": "分析候選"})
        cognition = build_cognition_update_candidate({"question_order": "SAFE"}, ["evidence:test"])
        node_status = {
            "Self": {"HostName": "taiji01", "OS": "linux", "Online": True, "Self": True},
            "Peer": [],
        }
        authority = {"nodes": [{"hostname": "taiji01", "authority": "OWNER_AUTHORIZED", "connection_method": "LOCAL_SHELL"}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "authority.json"
            path.write_text(json.dumps(authority), encoding="utf-8")
            nodes = parse_tailscale_status(node_status, authority_registry_path=path)
        deployment = build_deployment_manifest(
            [ROOT / "tools/total_field/w7tp_field_application_runtime.py"],
            "W7TP_INTENT_FIELD_TEST_001",
        )
        instances = {
            "w7tp_guided_completion.schema.json": guided,
            "w7tp_adaptive_cognition.schema.json": cognition,
            "w7tp_node_capability.schema.json": nodes,
            "w7tp_deployment_manifest.schema.json": deployment,
        }
        for name, instance in instances.items():
            with self.subTest(schema=name):
                schema = json.loads((ROOT / "schemas/field" / name).read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(schema)
                Draft202012Validator(schema).validate(instance)

    def test_release_includes_total_field_container_scope_manifest(self) -> None:
        release_paths = {path.relative_to(ROOT).as_posix() for path in _release_files()}
        self.assertIn(
            "runtime/total_field/node_container_scope/TOTAL_FIELD_NODE_CONTAINER_MANIFEST_20260624.json",
            release_paths,
        )

    def test_cafe_pos_receiver_chain_uses_same_request_id_and_stays_candidate_only(self) -> None:
        request = self._cafe_pos_total_field_request()
        request_id = request["receiver_context"]["request_id"]
        status, result = cloud_proxy.process_http_request(
            json.dumps(request).encode()
        )
        self.assertEqual(status, 200, result)
        self.assertEqual(result["D8"]["decision"], "PENDING_TOTAL_FIELD_REVIEW")
        metadata = result["execution_metadata"]
        receipt = metadata["total_field_receipt"]
        self.assertEqual(metadata["request_id"], request_id)
        self.assertEqual(receipt["request_id"], request_id)
        self.assertEqual(receipt["event_ref"], request_id)
        self.assertEqual(receipt["d3_event_id"], request_id)
        self.assertTrue(receipt["same_request_id_chain"])
        self.assertEqual(receipt["receipt_state"], "PASS")
        self.assertEqual(receipt["receiver"], "receive_candidate")
        self.assertEqual(
            receipt["receiver_ref"],
            "tools.total_field_candidate_gateway.receive_candidate",
        )
        self.assertEqual(receipt["total_field_decision"], "HOLD")
        self.assertIn(
            "HOLD_OBSERVATION_DOMAIN_NOT_CONFIGURED",
            receipt["decision_reason_codes"],
        )
        self.assertEqual(receipt["gte_lifecycle"], "CANDIDATE")
        for field_name in (
            "commit_applied",
            "real_order_created",
            "payment_transaction",
            "invoice_created",
            "member_plaintext",
            "canonical_write",
            "community_happiness_coin_accepted",
            "consumer_happiness_coin_issued",
            "community_merchant_ticket_quota",
            "fund_1_to_1_to_1_binding",
        ):
            self.assertIs(receipt[field_name], False, field_name)
        unsigned = dict(receipt)
        receipt_sha256 = unsigned.pop("receipt_sha256")
        self.assertEqual(receipt_sha256, canonical_sha256(unsigned))

    def test_cafe_pos_receiver_rejects_profile_and_value_boundary_escalation(self) -> None:
        generic = self._cafe_pos_total_field_request()
        generic["profile"] = "GENERIC"
        generic["intent"] = COMPLETE_INTENTS["GENERIC"]
        status, result = cloud_proxy.process_http_request(json.dumps(generic).encode())
        self.assertEqual(status, 422)
        self.assertEqual(result["reason_code"], "TOTAL_FIELD_RECEIVER_CAFE_POS_ONLY")

        escalated = self._cafe_pos_total_field_request(
            community_happiness_coin_accepted=True
        )
        status, result = cloud_proxy.process_http_request(
            json.dumps(escalated).encode()
        )
        self.assertEqual(status, 422)
        self.assertEqual(
            result["reason_code"],
            "CAFE_POS_COMMUNITY_VALUE_BOUNDARY_REQUIRED",
        )

        malformed = self._cafe_pos_total_field_request(request_id="odoo-cafe:bad")
        status, result = cloud_proxy.process_http_request(
            json.dumps(malformed).encode()
        )
        self.assertEqual(status, 422)
        self.assertEqual(result["reason_code"], "CAFE_POS_REQUEST_ID_INVALID")

    def test_release_includes_receive_candidate_runtime_closure(self) -> None:
        release_paths = {path.relative_to(ROOT).as_posix() for path in _release_files()}
        self.assertTrue(
            {
                "tools/total_field_candidate_gateway.py",
                "tools/eightd_gte_parser_candidate.py",
                "tools/tfct_true8d_runtime_candidate.py",
                "tools/d3_coordinate_transition_candidate.py",
                "schemas/field/8d_gte_runtime_candidate_profile_v0_1.schema.json",
                "schemas/field/8d_governance_tensor_expression_candidate.schema.json",
                "runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json",
                "runtime/total_field/candidate/d3_coordinate_transition_rules_v0_3.json",
            }.issubset(release_paths)
        )

    def test_shared_http_api_health_capabilities_and_candidate(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            for path in ("/healthz", "/readyz", "/capabilities", "/v1/models", "/wuchang/intent-field", "/favicon.svg"):
                with urllib.request.urlopen(base + path, timeout=3) as response:
                    self.assertEqual(response.status, 200)
                    if path == "/healthz":
                        health = json.loads(response.read())
                        self.assertEqual(
                            health["db_startup_mode"],
                            "READ_ONLY_SCHEMA_CHECK_NO_WRITE",
                        )
                    elif path == "/capabilities":
                        capabilities = json.loads(response.read())
                        llm = capabilities["llm_execution"]
                        self.assertEqual(llm["llm_inference_location"], "USER_DEVICE_ONLY")
                        self.assertEqual(llm["server_llm_execution"], "BLOCK")
                        self.assertEqual(llm["raw_prompt_upload"], "BLOCK")
                    elif path == "/v1/models":
                        models = json.loads(response.read())
                        self.assertEqual(models["data"], [])
                        self.assertEqual(
                            models["llm_execution"]["llm_inference_location"],
                            "USER_DEVICE_ONLY",
                        )
                    elif path == "/favicon.svg":
                        self.assertEqual(
                            response.headers.get_content_type(),
                            "image/svg+xml",
                        )
            payload = json.dumps({"profile": "GENERIC", "intent": COMPLETE_INTENTS["GENERIC"]}).encode()
            request = urllib.request.Request(base + "/api/intent-field", data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=3) as response:
                result = json.loads(response.read())
            self.assertEqual(result["profile"], "GENERIC")
            self.assertEqual(result["D8"]["decision"], "PENDING_TOTAL_FIELD_REVIEW")
            chat_request = urllib.request.Request(
                base + "/v1/chat/completions",
                data=json.dumps({"messages": [{"role": "user", "content": "synthetic"}]}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(urllib.error.HTTPError) as blocked:
                urllib.request.urlopen(chat_request, timeout=3)
            self.assertEqual(blocked.exception.code, 409)
            boundary = json.loads(blocked.exception.read())
            self.assertEqual(boundary["reason_code"], "DEVICE_LLM_REQUIRED")
            self.assertEqual(
                boundary["llm_execution"]["llm_inference_location"],
                "USER_DEVICE_ONLY",
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_shared_product_redirects_unauthorized_api_to_existing_google_login(self) -> None:
        self.assertIn("LLM 只在使用者設備執行", PRODUCT_HTML)
        self.assertIn("本頁不在伺服器載入或執行模型", PRODUCT_HTML)
        self.assertIn('data-llm-execution="USER_DEVICE_ONLY"', PRODUCT_HTML)
        self.assertIn("單一共用意圖場", PRODUCT_HTML)
        self.assertIn('href="#intent">立即測試生成式傳輸</a>', PRODUCT_HTML)
        self.assertIn("整理成安全候選", PRODUCT_HTML)
        self.assertIn('aria-errormessage="intent-error"', PRODUCT_HTML)
        self.assertIn('data-example="整理一份不含個資的社區活動流程', PRODUCT_HTML)
        self.assertIn("$('preview-title').focus()", PRODUCT_HTML)
        self.assertIn("window.location.hash==='#workspace'", PRODUCT_HTML)
        self.assertLess(
            PRODUCT_HTML.index('id="workspace"'),
            PRODUCT_HTML.index('id="redteam-monitor"'),
        )
        self.assertIn('id="dimension-grid"', PRODUCT_HTML)
        self.assertIn('id="evidence-list"', PRODUCT_HTML)
        self.assertIn('id="risk-list"', PRODUCT_HTML)
        self.assertIn('id="node-grid"', PRODUCT_HTML)
        self.assertIn("總場、節點與容器可用狀態", PRODUCT_HTML)
        self.assertIn("result.containers", PRODUCT_HTML)
        self.assertIn("總場唯讀納管", PRODUCT_HTML)
        self.assertIn('id="redteam-monitor"', PRODUCT_HTML)
        self.assertIn("常駐紅隊觀點監看中", PRODUCT_HTML)
        self.assertIn("ALWAYS-ON REDTEAM", PRODUCT_HTML)
        self.assertIn("NONE_DETERMINISTIC_RULES", PRODUCT_HTML)
        self.assertIn("GT_CORE_DEFINITION_DRIFT", PRODUCT_HTML)
        self.assertNotIn("__REDTEAM_CLIENT_RULES__", PRODUCT_HTML)
        self.assertIn("const current=guided", PRODUCT_HTML)
        self.assertIn("intent[current.question.field]=answer", PRODUCT_HTML)
        self.assertNotIn("intent[guided.question.field]=answer", PRODUCT_HTML)
        self.assertIn("response.status===401", PRODUCT_HTML)
        self.assertIn("window.location.assign('/google/member/login')", PRODUCT_HTML)
        self.assertNotIn("access_token", PRODUCT_HTML)
        self.assertNotIn("client_secret", PRODUCT_HTML)

    def test_service_startup_uses_read_only_db_check_and_never_init(self) -> None:
        fake_server = unittest.mock.MagicMock()
        with (
            patch.object(sys, "argv", ["w7tp_openwebui_cloud_proxy.py"]),
            patch.object(cloud_proxy, "verify_existing_db_read_only", return_value=True),
            patch.object(cloud_proxy, "init_db", side_effect=AssertionError("DB write")),
            patch.object(cloud_proxy, "ThreadingHTTPServer", return_value=fake_server),
        ):
            self.assertEqual(cloud_proxy.main(), 0)
        fake_server.serve_forever.assert_called_once_with()

    def test_systemd_service_executes_the_content_addressed_current_release(self) -> None:
        unit = (ROOT / "deploy/systemd/w7tp-intent-field.service").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "WorkingDirectory=/home/taiji_admin/.local/share/w7tp-intent-field/current",
            unit,
        )
        self.assertIn("Environment=W7TP_STATE_ROOT=/home/taiji_admin/Taiji_Hub", unit)
        self.assertIn(
            "/home/taiji_admin/.local/share/w7tp-intent-field/current/tools/cloud_proxy/w7tp_openwebui_cloud_proxy.py",
            unit,
        )
        self.assertNotIn(
            "ExecStart=/usr/bin/python3 /home/taiji_admin/Taiji_Hub/tools/",
            unit,
        )
        self.assertIn("--host 127.0.0.1", unit)
        self.assertIn("--internal-host 172.28.0.1", unit)
        self.assertNotIn("0.0.0.0", unit)

    def test_internal_listener_accepts_only_a_distinct_private_ip(self) -> None:
        self.assertEqual(
            cloud_proxy._validated_internal_host("172.28.0.1", "127.0.0.1"),
            "172.28.0.1",
        )
        for host in ("0.0.0.0", "224.0.0.1", "127.0.0.1"):
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    cloud_proxy._validated_internal_host(host, "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
