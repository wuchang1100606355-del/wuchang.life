from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tools import gemini_code_assist_a2a_candidate as adapter
from tools.total_field_dynamic_context_pull import (
    TotalFieldDynamicContextPullBroker,
)


ROOT = Path(__file__).resolve().parents[1]
ORIGIN_PATH = ROOT / (
    "products/eight_dimensional_generative_memory/"
    "w7tp_origin_cell_generative_v2.py"
)
MINIMUM_PATH = ROOT / (
    "products/eight_dimensional_generative_memory/"
    "w7tp_origin_state_minimum_packet_v1.py"
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
origin = load_module(ORIGIN_PATH, "origin_for_gemini_a2a_test")
minimum = load_module(MINIMUM_PATH, "minimum_for_gemini_a2a_test")


class GeminiA2APointerFirstTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not Path("/dev/shm").is_dir():
            raise unittest.SkipTest("/dev/shm unavailable")
        cls.base = Path(
            tempfile.mkdtemp(
                prefix="w7tp-gemini-a2a-test-",
                dir="/dev/shm",
            )
        )
        cls.source = cls.base / "source"
        origin.generate_target(
            cls.source,
            origin.MIN_DATASET_MIB,
            variant=41,
        )
        cls.packet = minimum.build_fixture_minimum_packet(
            cls.source,
            adi_coordinate_ref="adi:test:gemini-a2a",
            state_ref="state:test:gemini-a2a",
            state_version_ref="state-version:test:41",
            packet_ref="packet:test:gemini-a2a:41",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.base, ignore_errors=True)
    def builder(self, workset, packet, receipt):
        self.assertTrue(workset.is_dir())
        return {
            "context_ref": "context:test:gemini-a2a:41",
            "state_projection": {
                "state": "READY",
                "manifest": receipt["target_manifest_sha256"],
            },
            "evidence_refs": ["evidence:test:gemini-a2a:41"],
            "capability_refs": ["capability:test:gemini-a2a"],
            "acceptance_conditions": [
                "condition:test:candidate-only"
            ],
            "schema_refs": ["schema:test:gemini-a2a:v1"],
            "interface_refs": ["interface:test:total-field-return"],
            "non_core_rule_capsule_refs": [],
        }

    def broker_and_bootstrap(self):
        broker = TotalFieldDynamicContextPullBroker()
        bootstrap = broker.register(
            packet=self.packet,
            task_ref="task:NLDEV-005",
            provider_ref=adapter.PROVIDER_REF,
            model_ref=adapter.MODEL_REF,
            expires_at=(
                datetime.now(timezone.utc) + timedelta(minutes=10)
            ).isoformat(),
            return_coordinate="total-field:candidate-gateway:llm-push",
            context_builder=self.builder,
        )
        return broker, bootstrap

    def stream_pair(self, bootstrap):
        first_text = (
            '{"state":"CANDIDATE_ONLY","action":"PULL_CONTEXT",'
            '"pull_coordinate":"' + bootstrap["pull_coordinate"] + '",'
            '"bootstrap_sha256":"' + bootstrap["bootstrap_sha256"] + '"}'
        )
        second_text = (
            '{"state":"CANDIDATE_ONLY",'
            '"context_ref":"context:test:gemini-a2a:41",'
            '"candidate":{"assessment":"CONTEXT_RECEIVED"}}'
        )
        return [
            {
                "task_id": "task-a2a-1",
                "context_id": "context-a2a-1",
                "text": first_text,
                "text_sha256": "1" * 64,
                "final_state": "input-required",
                "provider_model": "gemini-test",
                "usage_metadata": {},
            },
            {
                "task_id": "task-a2a-1",
                "context_id": "context-a2a-1",
                "text": second_text,
                "text_sha256": "2" * 64,
                "final_state": "input-required",
                "provider_model": "gemini-test",
                "usage_metadata": {"totalTokenCount": 1},
            },
        ]

    def test_pointer_first_candidate_returns_to_total_field(self) -> None:
        broker, bootstrap = self.broker_and_bootstrap()
        with (
            patch.object(
                adapter,
                "discover_a2a",
                return_value={
                    "url": "http://127.0.0.1:1/",
                    "agent_version": "test",
                    "resource_id": "GEMINI_CODE_ASSIST",
                },
            ),
            patch.object(
                adapter,
                "_send_stream",
                side_effect=self.stream_pair(bootstrap),
            ),
        ):
            result = adapter.run_pointer_first_candidate(
                broker=broker,
                bootstrap=bootstrap,
                task_ref="task:NLDEV-005",
                candidate_instruction="Return a bounded candidate.",
            )
        self.assertEqual(
            result["state"],
            "PASS_GEMINI_A2A_POINTER_FIRST_CANDIDATE",
        )
        self.assertEqual(
            result["total_field"]["final_decision"],
            "ALLOW",
        )
        self.assertEqual(
            result["total_field"]["fixed_point_status"],
            "REACHED",
        )
        self.assertFalse(result["workspace_mutated"])
        self.assertFalse(
            result["raw_source_body_submitted_to_total_field"]
        )
    def test_wrong_pull_coordinate_stops_before_pull(self) -> None:
        broker, bootstrap = self.broker_and_bootstrap()
        responses = self.stream_pair(bootstrap)
        responses[0]["text"] = (
            '{"state":"CANDIDATE_ONLY","action":"PULL_CONTEXT",'
            '"pull_coordinate":"tfctx:wrong",'
            '"bootstrap_sha256":"' + bootstrap["bootstrap_sha256"] + '"}'
        )
        with (
            patch.object(
                adapter,
                "discover_a2a",
                return_value={
                    "url": "http://127.0.0.1:1/",
                    "agent_version": "test",
                    "resource_id": "GEMINI_CODE_ASSIST",
                },
            ),
            patch.object(adapter, "_send_stream", side_effect=responses),
        ):
            with self.assertRaisesRegex(
                adapter.GeminiA2AHold,
                "HOLD_GEMINI_A2A_PULL_COORDINATE_DRIFT",
            ):
                adapter.run_pointer_first_candidate(
                    broker=broker,
                    bootstrap=bootstrap,
                    task_ref="task:NLDEV-005",
                    candidate_instruction="Return a bounded candidate.",
                )
        self.assertFalse(
            broker.is_consumed(bootstrap["pull_coordinate"])
        )
    def test_candidate_authority_claim_is_blocked(self) -> None:
        broker, bootstrap = self.broker_and_bootstrap()
        responses = self.stream_pair(bootstrap)
        responses[1]["text"] = (
            '{"state":"CANDIDATE_ONLY",'
            '"context_ref":"context:test:gemini-a2a:41",'
            '"candidate":{"authority_granted":true}}'
        )
        with (
            patch.object(
                adapter,
                "discover_a2a",
                return_value={
                    "url": "http://127.0.0.1:1/",
                    "agent_version": "test",
                    "resource_id": "GEMINI_CODE_ASSIST",
                },
            ),
            patch.object(adapter, "_send_stream", side_effect=responses),
        ):
            with self.assertRaisesRegex(
                adapter.GeminiA2AHold,
                "HOLD_GEMINI_A2A_AUTHORITY_CLAIM_BLOCKED",
            ):
                adapter.run_pointer_first_candidate(
                    broker=broker,
                    bootstrap=bootstrap,
                    task_ref="task:NLDEV-005",
                    candidate_instruction="Return a bounded candidate.",
                )
        self.assertTrue(
            broker.is_consumed(bootstrap["pull_coordinate"])
        )
    def test_total_field_hold_is_not_reported_as_pass(self) -> None:
        broker, bootstrap = self.broker_and_bootstrap()
        with (
            patch.object(
                adapter,
                "discover_a2a",
                return_value={
                    "url": "http://127.0.0.1:1/",
                    "agent_version": "test",
                    "resource_id": "GEMINI_CODE_ASSIST",
                },
            ),
            patch.object(
                adapter,
                "_send_stream",
                side_effect=self.stream_pair(bootstrap),
            ),
            patch.object(
                adapter,
                "llm_push",
                return_value={
                    "final_decision": "HOLD",
                    "fixed_point_status": "NOT_REACHED",
                    "commit_applied": False,
                    "decision_reason_codes": ["TEST_HOLD"],
                },
            ),
        ):
            with self.assertRaisesRegex(
                adapter.GeminiA2AHold,
                "HOLD_GEMINI_A2A_TOTAL_FIELD:HOLD:NOT_REACHED",
            ):
                adapter.run_pointer_first_candidate(
                    broker=broker,
                    bootstrap=bootstrap,
                    task_ref="task:NLDEV-005",
                    candidate_instruction="Return a bounded candidate.",
                )


if __name__ == "__main__":
    unittest.main()
