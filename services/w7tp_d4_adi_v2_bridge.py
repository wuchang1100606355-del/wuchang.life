"""W7TP production UI -> existing ADI V2 evidence ledger bridge.

No new D8 authority is issued here.
No membership plaintext is persisted by this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sys
from pathlib import Path
from typing import Any

from services.w7tp_evidence_ledger import (
    commit_evidence as _original_commit_evidence
)
from core.adi_native.evidence_ledger import VerifiableSpacetimeSystem
from tools.total_field.d4_adi_v2_record_wiring import (
    append_fact,
    append_privacy_access,
    verify,
)

ROOT = Path("/home/taiji_admin/Taiji_Hub")
AUDIT = Path("/home/taiji_admin/W7TP_AUDIT_SNAPSHOTS")
CONFIG = AUDIT / "w7tp_ui_bridge_config_v1.json"
LEDGER = AUDIT / "w7tp_ui_events_adi_v2.jsonl"
ORIGINAL_LEDGER = ROOT / "runtime/ledger/w7tp_ui_events.jsonl"

SAFE_EVENT = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), default=str
    ).encode("utf-8")

def _ledger():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if LEDGER.is_symlink():
        raise RuntimeError("ADI_V2_LEDGER_SYMLINK")
    return VerifiableSpacetimeSystem(
        LEDGER,
        legacy_file_sha256=config["legacy_file_sha256"],
        legacy_chain_head=config["legacy_chain_head"],
    )

def record_privacy_access(
    *, request_id, requester_ref, accountable_person_ref,
    authority_ref, purpose, disclosed_fields, result,
):
    """Governed audit API; caller must supply actual access facts."""
    ledger = _ledger()
    event = append_privacy_access(
        ledger,
        request_id=request_id,
        requester_ref=requester_ref,
        accountable_person_ref=accountable_person_ref,
        authority_ref=authority_ref,
        purpose=purpose,
        disclosed_fields=disclosed_fields,
        result=result,
    )
    verify(ledger)
    return event

def commit_evidence(
    packet: dict[str, Any] | None = None,
    state: str | None = None,
    decision: dict[str, Any] | None = None,
    hash_data: dict[str, Any] | None = None,
    source: str | None = None,
    event_type: str = "w7tp_ui_commit",
) -> dict[str, Any]:
    """Call existing writer once and return its original result unchanged."""
    before = (
        ORIGINAL_LEDGER.stat().st_size
        if ORIGINAL_LEDGER.is_file() else 0
    )

    result = _original_commit_evidence(
        packet, state, decision, hash_data, source, event_type
    )

    after = (
        ORIGINAL_LEDGER.stat().st_size
        if ORIGINAL_LEDGER.is_file() else 0
    )

    if after <= before:
        return result

    try:
        event_name = str(event_type)
        if SAFE_EVENT.fullmatch(event_name) is None:
            event_name = "HASHED_EVENT_TYPE"

        correlation = _sha(_canonical({
            "packet": packet,
            "state": state,
            "decision": decision,
            "hash_data": hash_data,
            "source": source,
            "event_type": event_type,
        }))

        ledger = _ledger()
        append_fact(
            ledger,
            event_id="sha256:" + correlation,
            action=event_name,
            actor_ref="service:w7tp_ui_adapter",
            accountable_person_ref=(
                "responsibility:identity_binding_unresolved"
            ),
            result="ORIGINAL_EVENT_COMMITTED",
        )
        verify(ledger)
    except Exception as exc:
        sys.stderr.write(
            "W7TP_ADI_V2_AUDIT_HOLD:"
            + type(exc).__name__ + "\n"
        )

    return result
