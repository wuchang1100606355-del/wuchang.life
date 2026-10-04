from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from tools.total_field.w7tp_founder_passkey_v1 import (
    scope_challenge,
    verify_authorization_passkey,
)
from tools.total_field.w7tp_t007_g4_activation_v1 import activate, EFFECT

ROOT = Path("/home/taiji_admin/Taiji_Hub").resolve()
REC = ROOT / "Taiji_Governance/candidates/t007_v23_global_successor_20261002T124541Z/authorization/field_completion_recovery_20261004T220131Z"
REQUEST = REC / "G4_FIELD_COMPLETION_REQUEST.json"
ASSERTION = REC / "PASSKEY_ASSERTION.json"
AUTH = REC / "FOUNDER_G4_AUTHORIZATION.json"
RECEIPT = REC / "G4_FIELD_COMPLETION_RECEIPT.json"
REOBS = REC / "POST_COMPLETION_REOBSERVATION.json"
CREDENTIAL = ROOT / "Taiji_Governance/candidates/t007_v23_global_successor_20261002T124541Z/authorization/FOUNDER_PASSKEY_CREDENTIAL_PUBLIC.json"
REPLAY = ROOT / "runtime/total_field/replay/t007_g4_field_completion"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_new(path: Path, value: dict) -> None:
    if path.exists():
        raise RuntimeError(f"refusing overwrite: {path}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_git(*args: str) -> str:
    p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip() or p.stdout.strip()}")
    return p.stdout.strip()


def main() -> int:
    if not REQUEST.is_file() or not ASSERTION.is_file() or not CREDENTIAL.is_file():
        raise RuntimeError("required request/assertion/credential missing")
    if AUTH.exists() or RECEIPT.exists() or REOBS.exists():
        raise RuntimeError("recovery output already exists")

    req = json.loads(REQUEST.read_text(encoding="utf-8"))
    assertion = json.loads(ASSERTION.read_text(encoding="utf-8"))
    auth = {
        "schema_id": "W7TP_T007_G4_FOUNDER_AUTHORIZATION_V1",
        "state": "FOUNDER_G4_AUTHORIZATION_APPROVED",
        "task_id": "T-007",
        "authorized_effect": EFFECT,
        "completion_mode": "CURRENT_FIELD_AFTER_ACTIVATION",
        "single_use": True,
        "request_ref": ref(REQUEST),
        "request_sha256": sha(REQUEST),
        "expires_at": req["expires_at"],
        "webauthn": {
            "scope_challenge": scope_challenge(req),
            "credential_ref": ref(CREDENTIAL),
            "credential_sha256": sha(CREDENTIAL),
            "assertion_ref": ref(ASSERTION),
            "assertion_sha256": sha(ASSERTION),
        },
    }
    verified = verify_authorization_passkey(ROOT, auth, scope=req)
    auth["passkey_assertion_verified"] = True
    auth["verified_sign_count"] = verified.sign_count
    write_new(AUTH, auth)

    out = activate(ROOT, REQUEST, AUTH, REPLAY, RECEIPT)

    pointer = ROOT / "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
    authority = ROOT / "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
    field = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_CANONICAL.json"
    router = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"
    field_doc = json.loads(field.read_text(encoding="utf-8"))
    router_doc = json.loads(router.read_text(encoding="utf-8"))

    expected_dims = {
        "D1": "Intent",
        "D2": "State",
        "D3": "Coordinate",
        "D4": "Evidence",
        "D5": "Execution/Policy",
        "D6": "Generative State Transmission",
        "D7": "Risk/Isolation",
        "D8": "Envelope/Authority",
    }

    def dims(doc: dict) -> dict:
        return {d.get("id"): d.get("field_en", d.get("field")) for d in doc.get("dimensions", [])}

    checks = {
        "receipt_activated": out.get("state") == "ACTIVATED",
        "completion_mode": out.get("completion_mode") == "CURRENT_FIELD_AFTER_ACTIVATION",
        "pointer_preserved_v23": sha(pointer) == req["bindings"]["canonical_pointer_preimage"]["sha256"],
        "authority_preserved": sha(authority) == req["bindings"]["authority_preimage"]["sha256"],
        "field_sha": sha(field) == req["bindings"]["current_state_field_successor"]["sha256"],
        "router_sha": sha(router) == req["bindings"]["current_state_field_router_successor"]["sha256"],
        "field_version": field_doc.get("version") == "2.3",
        "router_version": router_doc.get("version") == "2.3",
        "field_semantics": field_doc.get("semantics") == "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD",
        "router_semantics": router_doc.get("semantics") == "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD",
        "field_dimensions": dims(field_doc) == expected_dims,
        "router_dimensions": dims(router_doc) == expected_dims,
    }
    if not all(checks.values()):
        raise RuntimeError("post completion reobservation failed: " + json.dumps(checks, sort_keys=True))

    reobs = {
        "schema_id": "W7TP_T007_FIELD_COMPLETION_REOBSERVATION_V1",
        "state": "PASS_FIELD_COMPLETION_REOBSERVATION",
        "task_id": "T-007",
        "request_sha256": sha(REQUEST),
        "authorization_sha256": sha(AUTH),
        "activation_receipt_sha256": sha(RECEIPT),
        "pointer_sha256": sha(pointer),
        "authority_sha256": sha(authority),
        "current_state_field_sha256": sha(field),
        "current_state_field_router_sha256": sha(router),
        "checks": checks,
    }
    write_new(REOBS, reobs)

    staged_before = run_git("diff", "--cached", "--name-only")
    if staged_before:
        raise RuntimeError("unexpected pre-existing staged changes: " + staged_before)

    allowed = [
        ref(REC / "DYNAMIC_CONTEXT_PULL_RECEIPT.json"),
        ref(REC / "AUTO_FINALIZE_FIELD_COMPLETION.py"),
        ref(REQUEST),
        ref(ASSERTION),
        ref(AUTH),
        ref(RECEIPT),
        ref(REOBS),
        ref(field),
        ref(router),
    ]
    run_git("add", "--", *allowed)
    run_git("diff", "--cached", "--check")
    run_git("commit", "-m", "fix(t007): complete V2.3 current 8D field activation")
    run_git("push", "origin", "codex/current-live-state-consolidation-20260915")

    print(json.dumps({
        "state": "COMPLETED_AND_PUSHED",
        "task_id": "T-007",
        "sign_count": verified.sign_count,
        "receipt_sha256": out["receipt_sha256"],
        "field_sha256": sha(field),
        "router_sha256": sha(router),
        "head": run_git("rev-parse", "HEAD"),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
