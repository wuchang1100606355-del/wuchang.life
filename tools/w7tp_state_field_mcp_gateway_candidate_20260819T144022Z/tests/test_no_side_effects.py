from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from tests.support import CANDIDATE_ROOT, authorization_arguments, gateway, task_arguments


class NoSideEffectTests(unittest.TestCase):
    def test_gateway_source_has_no_shell_remote_http_or_control_plane_clients(self) -> None:
        forbidden_imports = {"subprocess", "paramiko", "requests", "httpx", "docker"}
        forbidden_names = {"eval", "exec", "compile"}
        forbidden_attributes = {"Popen"}
        for path in sorted((CANDIDATE_ROOT / "src").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(alias.name.split(".", 1)[0], forbidden_imports, path)
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".", 1)[0], forbidden_imports, path)
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        self.assertNotIn(node.func.id, forbidden_names, path)
                    if isinstance(node.func, ast.Attribute):
                        self.assertNotIn(node.func.attr, forbidden_attributes, path)
                        if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                            self.assertNotIn(node.func.attr, {"system", "popen"}, path)

    def test_fixed_probe_allowlist_is_loopback_or_absent(self) -> None:
        config = json.loads((CANDIDATE_ROOT / "config" / "allowlist.json").read_text())
        for service in config["services"]:
            self.assertIn(service["probe_host"], {None, "127.0.0.1"})

    def test_prepare_calls_do_not_create_files(self) -> None:
        def inventory() -> set[str]:
            return {
                str(path.relative_to(CANDIDATE_ROOT))
                for path in CANDIDATE_ROOT.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            }

        instance = gateway()
        before = inventory()
        instance.call_tool("prepare_task_candidate", task_arguments())
        instance.call_tool("prepare_authorization_request", authorization_arguments(instance))
        after = inventory()
        self.assertEqual(before, after)
        self.assertFalse(hasattr(instance, "execute_task"))
        self.assertFalse(hasattr(instance, "approve"))
        self.assertFalse(hasattr(instance, "consume_authorization"))


if __name__ == "__main__":
    unittest.main()
