from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.container_compose_candidate_generator import (  # noqa: E402
    FORBIDDEN_RUNTIME_ACTIONS,
    generate_compose_candidate,
    load_candidate_map,
    to_yaml_like,
    verify_candidate_map,
)


MAP_PATH = ROOT / "configs" / "total_field" / "container_compose_candidate_map.json"


class ContainerComposeCandidateGeneratorTests(unittest.TestCase):
    def test_load_candidate_map(self):
        data = load_candidate_map(MAP_PATH)
        self.assertEqual(data["mode"], "candidate_only_no_deploy")

    def test_verify_candidate_map(self):
        data = load_candidate_map(MAP_PATH)
        result = verify_candidate_map(data)
        self.assertEqual(result["decision"], "PASS_CANDIDATE_MAP_SAFE_FOR_DRY_GENERATION")
        self.assertGreaterEqual(result["service_count"], 1)
        self.assertFalse(result["deployable_now"])

    def test_forbidden_runtime_actions_are_declared(self):
        data = load_candidate_map(MAP_PATH)
        declared = set(data["forbidden_runtime_actions"])
        self.assertTrue(FORBIDDEN_RUNTIME_ACTIONS.issubset(declared))

    def test_generated_compose_is_candidate_only(self):
        data = load_candidate_map(MAP_PATH)
        candidate = generate_compose_candidate(data)

        self.assertEqual(candidate["state"], "CONTAINER_COMPOSE_GENERATED_CANDIDATE_ONLY_NO_DEPLOY")
        self.assertFalse(candidate["x-w7tp-policy"]["deploy"])
        self.assertFalse(candidate["x-w7tp-policy"]["restart"])
        self.assertFalse(candidate["x-w7tp-policy"]["db_write"])
        self.assertFalse(candidate["x-w7tp-policy"]["router_write"])
        self.assertFalse(candidate["x-w7tp-policy"]["production_activation"])

    def test_generated_services_never_create_or_restart(self):
        data = load_candidate_map(MAP_PATH)
        candidate = generate_compose_candidate(data)

        for service in candidate["services"].values():
            self.assertFalse(service["x-w7tp-authority-inside-container"])
            self.assertFalse(service["x-w7tp-create-now"])
            self.assertFalse(service["x-w7tp-restart-now"])
            self.assertEqual(service["profiles"], ["candidate-only-no-deploy"])

    def test_yaml_like_contains_no_runtime_command(self):
        data = load_candidate_map(MAP_PATH)
        text = to_yaml_like(generate_compose_candidate(data))

        self.assertIn("candidate-only-no-deploy", text)
        self.assertNotIn("docker compose up", text)
        self.assertNotIn("docker compose restart", text)
        self.assertNotIn("docker system prune", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
