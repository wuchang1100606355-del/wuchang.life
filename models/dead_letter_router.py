# -*- coding: utf-8 -*-
"""
Wuchang Intruder Dead Letter Router
五常入侵者死信箱路由器

Purpose:
- Route intruder-like / anti-governance command events into dead-letter queue.
- Preserve sanitized evidence.
- Never execute the command.

Safety:
- readonly logic
- no SSH
- no process kill
- no auto-start
- no system modification
- no secret read
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


DEAD_LETTER_DIR = Path("runtime/dead_letter")
DEAD_LETTER_JSONL = DEAD_LETTER_DIR / "intruder_dead_letter.jsonl"

SECRET_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*[^,\s]+"),
    re.compile(r"(?i)(token|api[_-]?key|secret|credential)\s*[:=]\s*[^,\s]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"(?i)\.env[^\s]*"),
]

INTRUDER_DECISIONS = {
    "INTRUDER_CHANNEL",
    "ANTI_GOVERNANCE_TAMPER",
    "COMMAND_CHANNEL_COMPROMISED_OR_UNVERIFIED",
    "UNVERIFIED_HARMFUL_COMMAND",
    "FUSE_INTRUDER_CHANNEL",
    "ROLLBACK_PRESERVATION",
    "FUSE_CHANNEL",
}

INTRUDER_FLAGS = {
    "harm_others_rights",
    "harm_privacy",
    "publish_precise_location",
    "publish_address_phone_identity",
    "expose_emergency_private_data",
    "output_token_password_private_key_credentials",
    "steal_or_output_token_password_key_credentials",
    "bypass_human_review",
    "harm_reputation_or_moral_character",
    "impersonate_identity",
    "damage_system_integrity",
    "disable_guardrails",
    "erase_evidence",
    "external_publish_unreviewed",
    "fuse_break_whole_system",
    "disable_founder_sovereignty",
    "lock_out_local_human_control",
    "delete_governance_policy",
}


@dataclass(frozen=True)
class DeadLetterRecord:
    record_type: str
    ts: str
    event_id: str
    route_reason: str
    original_decision: str
    sanitized_event: Dict[str, Any]
    readonly_enforced: bool
    execution_blocked: bool
    human_review_required: bool
    sha256: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_text(value: str) -> str:
    s = str(value)
    for pat in SECRET_PATTERNS:
        s = pat.sub("[REDACTED_SECRET]", s)
    # 粗略遮蔽疑似長 token
    s = re.sub(r"\b[A-Za-z0-9_\-]{32,}\b", "[REDACTED_LONG_TOKEN]", s)
    return s[:2000]


def sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if any(x in lk for x in ["password", "passwd", "token", "secret", "credential", "private_key", "apikey", "api_key"]):
                clean[k] = "[REDACTED_SECRET_FIELD]"
            else:
                clean[k] = sanitize(v)
        return clean
    if isinstance(obj, list):
        return [sanitize(x) for x in obj[:100]]
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    return redact_text(str(obj))


def event_id_from_event(event: Dict[str, Any]) -> str:
    raw = json.dumps(event, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def should_dead_letter(event: Dict[str, Any]) -> tuple[bool, str, str]:
    decision = str(
        event.get("decision")
        or event.get("channel_status")
        or event.get("command_channel_status")
        or event.get("status")
        or ""
    ).upper()

    flags = set()
    for key in ["risk_flags", "flags", "harm_flags"]:
        val = event.get(key, [])
        if isinstance(val, list):
            flags.update(str(x).lower() for x in val)

    if decision in INTRUDER_DECISIONS:
        return True, f"decision={decision}", decision

    hit_flags = flags & INTRUDER_FLAGS
    if hit_flags:
        return True, "flags=" + ",".join(sorted(hit_flags)), decision or "FLAG_MATCH"

    text = json.dumps(event, ensure_ascii=False).lower()
    keyword_hits = [
        "bypass_human_review",
        "erase_evidence",
        "private key",
        "credentials",
        "disable_founder_sovereignty",
        "fuse_break_whole_system",
        "harm_privacy",
    ]
    for kw in keyword_hits:
        if kw in text:
            return True, f"keyword={kw}", decision or "KEYWORD_MATCH"

    return False, "no_dead_letter_condition", decision or "NONE"


def write_dead_letter(event: Dict[str, Any]) -> DeadLetterRecord | None:
    DEAD_LETTER_DIR.mkdir(parents=True, exist_ok=True)

    should_route, reason, decision = should_dead_letter(event)
    if not should_route:
        return None

    clean_event = sanitize(event)
    eid = str(clean_event.get("event_id") or clean_event.get("command_id") or event_id_from_event(clean_event))

    record_no_hash = DeadLetterRecord(
        record_type="INTRUDER_DEAD_LETTER",
        ts=now_iso(),
        event_id=eid,
        route_reason=reason,
        original_decision=decision,
        sanitized_event=clean_event,
        readonly_enforced=True,
        execution_blocked=True,
        human_review_required=True,
        sha256=None,
    )

    raw_no_hash = json.dumps(asdict(record_no_hash), ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(raw_no_hash.encode("utf-8")).hexdigest()

    record = DeadLetterRecord(
        **{**asdict(record_no_hash), "sha256": digest}
    )

    line = json.dumps(asdict(record), ensure_ascii=False, sort_keys=True)
    with DEAD_LETTER_JSONL.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    gz_path = DEAD_LETTER_DIR / f"{eid}_{digest[:12]}.json.gz"
    with gzip.open(gz_path, "wt", encoding="utf-8") as gz:
        gz.write(json.dumps(asdict(record), ensure_ascii=False, indent=2, sort_keys=True))

    sha_path = gz_path.with_suffix(gz_path.suffix + ".sha256")
    sha_path.write_text(f"{digest}  {gz_path.name}\n", encoding="utf-8")

    return record


def demo_event() -> Dict[str, Any]:
    return {
        "event_id": "demo_intruder_dead_letter",
        "claimed_actor": "admin",
        "channel": "remote_session",
        "decision": "INTRUDER_CHANNEL",
        "risk_flags": [
            "bypass_human_review",
            "harm_privacy",
            "output_token_password_private_key_credentials",
        ],
        "summary": "remote command attempts to bypass review and output credentials",
        "payload_preview": "token=SHOULD_NOT_BE_STORED password=SHOULD_NOT_BE_STORED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--stdin", action="store_true")
    args = parser.parse_args()

    if args.demo:
        event = demo_event()
    elif args.stdin:
        event = json.load(sys.stdin)
    else:
        print("Use --demo or --stdin", file=sys.stderr)
        return 2

    record = write_dead_letter(event)
    if record is None:
        print(json.dumps({
            "routed": False,
            "reason": "no_dead_letter_condition",
            "readonly": True,
        }, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps({
        "routed": True,
        "dead_letter": str(DEAD_LETTER_JSONL),
        "event_id": record.event_id,
        "sha256": record.sha256,
        "execution_blocked": True,
        "human_review_required": True,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
