from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts/verify/verify_sovereign_ai_member_product.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_sovereign_ai_member_product", VERIFY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sovereign_ai_member_product_source_contract() -> None:
    checks, failures = load_verifier().run_checks()
    assert failures == []
    assert checks
    assert set(checks.values()) == {"PASS"}
