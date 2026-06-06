from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.w7tp_d6_linter import lint_w7tp_request
from services.w7tp_evidence_ledger import commit_evidence
from services.w7tp_state_hash import state_seal
from services.w7tp_ui_adapter import compile_packet
from services.w7tp_ui_models import IntentCompileIn


def main() -> None:
    safe = lint_w7tp_request("read current W7TP state")
    assert safe["allowed"] is True
    assert safe["state"] == "TRANSACTION_COMMITTED"

    blocked = lint_w7tp_request("test fake sk-proj-xxxxxxxxxxxxxxxx token")
    assert blocked["allowed"] is False
    assert blocked["state"] == "HARDWALL_BLOCKED"
    assert blocked["dead_letter"] is True

    compiled = compile_packet(IntentCompileIn(intent="read state hash", actor="verify", node="MSI-WSL"))
    assert compiled["D8_State_FSM"] == "TRANSACTION_COMMITTED"

    seal = state_seal({"verify": True}, "TRANSACTION_COMMITTED", "MSI-WSL", 1, {"d": 8})
    assert seal["ok"] is True
    assert len(seal["packet_hash"]) == 64
    assert len(seal["state_hash"]) == 64

    commit = commit_evidence(
        packet={"verify": True},
        state=blocked["state"],
        decision=blocked,
        hash_data=seal,
        source="verify_w7tp_ui_adapter",
    )
    assert commit["ok"] is True
    assert Path(commit["ledger_path"]).exists()
    assert commit["dead_letter_path"]
    assert Path(commit["dead_letter_path"]).exists()

    print("VERIFY_OK")


if __name__ == "__main__":
    main()
