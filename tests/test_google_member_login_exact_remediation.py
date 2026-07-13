from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts/verify/verify_google_member_login_exact_remediation.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_google_member_login_exact_remediation", VERIFY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_google_member_login_exact_remediation_source_contract() -> None:
    assert load_verifier().verify() == []
