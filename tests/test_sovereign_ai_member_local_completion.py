from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts/verify/verify_sovereign_ai_member_local_completion.py"


def test_sovereign_ai_member_local_completion_contract() -> None:
    spec = importlib.util.spec_from_file_location(
        "verify_sovereign_ai_member_local_completion", VERIFY_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checks, failures = module.run_checks()
    assert failures == []
    assert checks
    assert set(checks.values()) == {"PASS"}
