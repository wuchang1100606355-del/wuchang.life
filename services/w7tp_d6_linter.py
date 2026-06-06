from __future__ import annotations

import json
import re
from typing import Any


BLOCK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE | re.DOTALL))
    for name, pattern in (
        ("OPENAI_SECRET_KEY", r"\bsk-[A-Za-z0-9_\-]{8,}"),
        ("OPENAI_PROJECT_KEY", r"\bsk-proj-[A-Za-z0-9_\-]{8,}"),
        ("SLACK_BOT_TOKEN", r"\bxoxb-[A-Za-z0-9_\-]{8,}"),
        ("GITHUB_PAT", r"\bghp_[A-Za-z0-9_]{8,}"),
        ("PRIVATE_KEY_BLOCK", r"PRIVATE KEY"),
        ("PASSWORD_ASSIGNMENT", r"\bpassword\s*="),
        ("SECRET_ASSIGNMENT", r"\bsecret\s*="),
        ("TOKEN_ASSIGNMENT", r"\btoken\s*="),
        ("CREDENTIAL_TEXT", r"\bcredential\b"),
        ("RM_RF", r"\brm\s+-rf\b"),
        ("CHMOD_777", r"\bchmod\s+777\b"),
        ("CURL_PIPE_SH", r"\bcurl\b[^|]*\|\s*sh\b"),
        ("SYSTEMD_RESTART", r"\bsudo\s+systemctl\s+restart\b"),
        ("DOCKER_COMPOSE_DOWN", r"\bdocker\s+compose\s+down\b"),
        ("DATABASE_DROP", r"\bdatabase\s+drop\b"),
        ("BYPASS_HUMAN_REVIEW", r"\bbypass\s+human\s+review\b"),
        ("DISABLE_GOVERNANCE", r"\bdisable\s+governance\b"),
        ("ERASE_LEDGER", r"\berase\s+ledger\b"),
        ("DELETE_EVIDENCE", r"\bdelete\s+evidence\b"),
    )
)

SYNC_PATTERNS = re.compile(r"\b(sync|timeout|network drift|latency|phase drift|retry)\b", re.IGNORECASE)
PRIVACY_PATTERNS = re.compile(
    r"\b(privacy|pii|plaintext|plain text|personal data|phone|address|redact)\b",
    re.IGNORECASE,
)


def _flatten(intent: str | None, packet: dict[str, Any] | None, context: dict[str, Any] | None) -> str:
    payload = {"intent": intent or "", "packet": packet or {}, "context": context or {}}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def lint_w7tp_request(
    intent: str | None = None,
    packet: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = _flatten(intent, packet, context)
    hits = [name for name, pattern in BLOCK_PATTERNS if pattern.search(text)]
    if hits:
        return {
            "allowed": False,
            "state": "HARDWALL_BLOCKED",
            "bagua": "GEN",
            "reason": "D6_HARDWALL_BLOCKED",
            "dead_letter": True,
            "rules": hits,
        }
    if SYNC_PATTERNS.search(text):
        return {
            "allowed": True,
            "state": "PHASE_SYNCING",
            "bagua": "XUN",
            "reason": "D5_PHASE_SYNC_REQUIRED",
            "dead_letter": False,
            "rules": ["PHASE_SYNC_DRIFT"],
        }
    if PRIVACY_PATTERNS.search(text):
        return {
            "allowed": True,
            "state": "DATA_REDACTED_BLIND",
            "bagua": "KAN",
            "reason": "D5_REDACTION_REQUIRED",
            "dead_letter": False,
            "rules": ["PRIVACY_REDACTION"],
        }
    return {
        "allowed": True,
        "state": "TRANSACTION_COMMITTED",
        "bagua": "DUI",
        "reason": "D6_SAFE",
        "dead_letter": False,
        "rules": ["DEFAULT_ALLOW"],
    }
