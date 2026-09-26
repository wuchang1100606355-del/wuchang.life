from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.total_field_dynamic_context_pull import (
    DynamicContextPullHold,
    TotalFieldDynamicContextPullBroker,
    canonical_sha256,
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
origin = load_module(ORIGIN_PATH, "origin_for_context_pull_test")
minimum = load_module(MINIMUM_PATH, "minimum_for_context_pull_test")


class DynamicContextPullTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not Path("/dev/shm").is_dir():
            raise unittest.SkipTest("/dev/shm unavailable")
        cls.base = Path(
            tempfile.mkdtemp(
                prefix="w7tp-context-pull-test-",
                dir="/dev/shm",
            )
        )
        cls.source = cls.base / "source"
        origin.generate_target(
            cls.source,
            origin.MIN_DATASET_MIB,
            variant=31,
        )
        cls.packet = minimum.build_fixture_minimum_packet(
            cls.source,
            adi_coordinate_ref="adi:test:context-pull",
            state_ref="state:test:context-pull",
            state_version_ref="state-version:test:31",
            packet_ref="packet:test:context-pull:31",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.base, ignore_errors=True)

    def future_expiry(self, minutes: int = 10) -> str:
        return (
            datetime.now(timezone.utc) + timedelta(minutes=minutes)
        ).isoformat()
    def good_builder(self, workset, packet, receipt):
        self.assertTrue(workset.is_dir())
        return {
            "context_ref": "context:test:bounded:31",
            "state_projection": {
                "task_state": "READY",
                "target_manifest_sha256": receipt[
                    "target_manifest_sha256"
                ],
            },
            "evidence_refs": ["evidence:test:context-pull:31"],
            "capability_refs": ["capability:test:reasoning-organ"],
            "acceptance_conditions": [
                "condition:test:final-manifest-match"
            ],
            "schema_refs": ["schema:test:model-visible-context:v1"],
            "interface_refs": ["interface:test:candidate-return:v1"],
            "non_core_rule_capsule_refs": [
                "rule-capsule:test:formatting-only:v1"
            ],
        }

    def register(self, broker, *, builder=None):
        return broker.register(
            packet=self.packet,
            task_ref="task:NLDEV-005",
            provider_ref="provider:gemini-code-assist",
            model_ref="model:gemini-code-assist:current",
            expires_at=self.future_expiry(),
            return_coordinate="total-field:candidate-gateway:llm-push",
            context_builder=builder or self.good_builder,
        )

    def pull(self, broker, bootstrap):
        return broker.pull(
            bootstrap["pull_coordinate"],
            task_ref="task:NLDEV-005",
            provider_ref="provider:gemini-code-assist",
            model_ref="model:gemini-code-assist:current",
        )
    def test_bootstrap_is_pointer_only(self) -> None:
        broker = TotalFieldDynamicContextPullBroker()
        bootstrap = self.register(broker)
        encoded = json.dumps(
            bootstrap,
            ensure_ascii=False,
            sort_keys=True,
        )
        self.assertIn("pull_coordinate", bootstrap)
        self.assertIn("packet_ref", bootstrap)
        self.assertIn("adi_coordinate_ref", bootstrap)
        self.assertNotIn("model_visible_context", bootstrap)
        self.assertNotIn("minimum_new_information", encoded)
        self.assertNotIn("reconstruction_rules", encoded)
        self.assertNotIn("local-rule:", encoded)
        supplied = bootstrap["bootstrap_sha256"]
        basis = dict(bootstrap)
        basis.pop("bootstrap_sha256")
        self.assertEqual(supplied, canonical_sha256(basis))

    def test_exact_pull_reconstructs_then_destroys_workset(self) -> None:
        broker = TotalFieldDynamicContextPullBroker()
        bootstrap = self.register(broker)
        result = self.pull(broker, bootstrap)
        self.assertEqual(
            result["model_visible_context"]["state_projection"][
                "task_state"
            ],
            "READY",
        )
        self.assertTrue(
            result["reconstruction_evidence"]["workset_destroyed"]
        )
        self.assertFalse(
            result["reconstruction_evidence"][
                "persistent_materialization"
            ]
        )
        encoded = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("local-rule:", encoded)
        self.assertNotIn("reconstruction_rules", encoded)
        self.assertFalse(result["authority"]["provider_authority"])
        self.assertFalse(result["authority"]["model_authority"])
    def test_replay_is_blocked(self) -> None:
        broker = TotalFieldDynamicContextPullBroker()
        bootstrap = self.register(broker)
        self.pull(broker, bootstrap)
        with self.assertRaisesRegex(
            DynamicContextPullHold,
            "HOLD_CONTEXT_PULL_REPLAY_BLOCKED",
        ):
            self.pull(broker, bootstrap)

    def test_provider_model_and_task_are_exact_bound(self) -> None:
        cases = [
            (
                {"provider_ref": "provider:other"},
                "HOLD_CONTEXT_PULL_PROVIDER_DRIFT",
            ),
            (
                {"model_ref": "model:other"},
                "HOLD_CONTEXT_PULL_MODEL_DRIFT",
            ),
            (
                {"task_ref": "task:other"},
                "HOLD_CONTEXT_PULL_TASK_DRIFT",
            ),
        ]
        for updates, code in cases:
            broker = TotalFieldDynamicContextPullBroker()
            bootstrap = self.register(broker)
            kwargs = {
                "task_ref": "task:NLDEV-005",
                "provider_ref": "provider:gemini-code-assist",
                "model_ref": "model:gemini-code-assist:current",
            }
            kwargs.update(updates)
            with self.assertRaisesRegex(DynamicContextPullHold, code):
                broker.pull(bootstrap["pull_coordinate"], **kwargs)
            self.assertFalse(
                broker.is_consumed(bootstrap["pull_coordinate"])
            )
    def test_expired_coordinate_is_blocked_before_reconstruction(self) -> None:
        broker = TotalFieldDynamicContextPullBroker()
        bootstrap = self.register(broker)
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        with self.assertRaisesRegex(
            DynamicContextPullHold,
            "HOLD_CONTEXT_PULL_EXPIRED",
        ):
            broker.pull(
                bootstrap["pull_coordinate"],
                task_ref="task:NLDEV-005",
                provider_ref="provider:gemini-code-assist",
                model_ref="model:gemini-code-assist:current",
                now=future,
            )
        self.assertFalse(
            broker.is_consumed(bootstrap["pull_coordinate"])
        )

    def test_forbidden_context_content_fails_closed_and_consumes(self) -> None:
        def bad_builder(workset, packet, receipt):
            self.assertTrue(workset.is_dir())
            value = self.good_builder(workset, packet, receipt)
            value["state_projection"]["password"] = "forbidden"
            return value

        broker = TotalFieldDynamicContextPullBroker()
        bootstrap = self.register(broker, builder=bad_builder)
        with self.assertRaisesRegex(
            DynamicContextPullHold,
            "HOLD_CONTEXT_FORBIDDEN_KEY",
        ):
            self.pull(broker, bootstrap)
        self.assertTrue(
            broker.is_consumed(bootstrap["pull_coordinate"])
        )
    def test_persistence_boundary_is_references_only(self) -> None:
        broker = TotalFieldDynamicContextPullBroker()
        bootstrap = self.register(broker)
        result = self.pull(broker, bootstrap)
        policy = result["persistence_policy"]
        self.assertEqual(
            policy["mode"],
            "EPHEMERAL_CONTEXT_REFERENCES_ONLY",
        )
        self.assertFalse(
            policy["dynamic_context_persistence_allowed"]
        )
        self.assertFalse(policy["full_state_persistence_allowed"])
        self.assertFalse(policy["core_rule_persistence_allowed"])
        self.assertFalse(
            policy["personal_plaintext_persistence_allowed"]
        )
        persistent = result["persistent_refs"]
        self.assertNotIn("model_visible_context", persistent)
        self.assertIn("packet_ref", persistent)
        self.assertIn("adi_coordinate_ref", persistent)

    def test_broker_exposes_no_enumeration_api(self) -> None:
        broker = TotalFieldDynamicContextPullBroker()
        self.assertFalse(hasattr(broker, "list_requests"))
        self.assertFalse(hasattr(broker, "list_coordinates"))
        self.assertFalse(hasattr(broker, "enumerate"))


if __name__ == "__main__":
    unittest.main()
