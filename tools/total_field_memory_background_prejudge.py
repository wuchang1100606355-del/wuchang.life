#!/usr/bin/env python3
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path.cwd()

CORE_FILES = [
    "docs/total_field/W7TP_AMBIGUOUS_INTENT_COMPLETE_FUNCTION_TABLE.md",
    "docs/total_field/W7TP_USER_EXPERIENCE_CLOUD_MINIMALITY_POLICY.md",
    "docs/total_field/WUCHANG_NONPROFIT_COMMUNITY_INDUSTRY_AND_DEVELOPER_TEST_BOUNDARY.md",
    "docs/total_field/WUCHANG_FOUNDER_DONOR_ROLE_AND_PUBLIC_INTEREST_IP_BOUNDARY.md",
    "docs/total_field/WUCHANG_SAME_PERSON_CLOSED_TEST_GOVERNANCE_BOUNDARY.md",
    "docs/total_field/TIANXIA_WEIGONG_LIVING_MINIMUM_BENEFIT_MODEL.md",
    "docs/total_field/W7TP_AI_MAIN_ROAD_IP_DEFENSE_STRATEGY.md",
    "docs/total_field/W7TP_HUMAN_USER_EXPERIENCE_PRODUCT_PRIORITY_MATRIX.md",
    "patent_poc/wuchang_adi_causal_sidecar/evidence/CLOUD_DRIVE_WISH_TREE_EVIDENCE.md",
    "patent_poc/wuchang_adi_causal_sidecar/state/VIRTUAL_STATE_TRANSITION.md",
    "patent_poc/wuchang_adi_causal_sidecar/community_design/WISH_TREE_COMMUNITY_DESIGN_UPDATE.md",
    "patent_poc/wuchang_adi_causal_sidecar/schemas/wish_tree_sidecar_event.schema.json",
    "patent_poc/wuchang_adi_causal_sidecar/policies/UX_CLOUD_MINIMALITY_GATE.md",
]

SCOPE_PATHS = [
    "docs/total_field",
    "patent_poc/wuchang_adi_causal_sidecar",
    "runtime/total_field/memory_seal",
]

SECRET_PATTERNS = [
    r"taiji_secret",
    r"BEGIN [A-Z ]*PRIVATE KEY",
    r"sk-[A-Za-z0-9_-]{20,}",
    r"refresh_token[\"':= ]",
    r"access_token[\"':= ]",
    r"client_secret[\"':= ]",
]

MUTATION_PATTERNS = [
    r"\bpsql\b.*\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE)\b",
    r"\bodoo\b.*\s-i\s",
    r"\bodoo\b.*\s-u\s",
    r"\b(service|systemctl|docker)\b.*\b(restart|reload)\b",
    r"\bgcloud\b.*\b(update|delete|create|set-iam-policy)\b",
    r"\bgit\s+push\b",
]

SAFE_CONTEXT_MARKERS = [
    r"^\s*[-*]\s*(NO|NO_|FORBIDDEN|FORBID|forbidden|Forbidden)\b",
    r"^\s*[-*]?\s*(禁止|不得|不可|不應|不允許|未允許)\b",
    r"^\s*[-*]?\s*(UNSAFE|FORBID|FORBIDDEN|禁止|不得|不可)\b",
]
PLAIN_SERVICE_RESTART_RE = re.compile(
    r"^\s*[-*]?\s*(service|systemctl|docker)\s+(restart|reload)\s*\.?$",
    re.IGNORECASE,
)

SAFE_FALSE_BOOLEAN_PATTERNS = [
    r"\"(production_db_write|odoo_install|odoo_module_install|service_restart|google_api_mutation|git_push)\"\\s*:\\s*false",
    r"'(production_db_write|odoo_install|odoo_module_install|service_restart|google_api_mutation|git_push)'\\s*:\\s*false",
]

NEGATION_WORDS = [
    "no ",
    "not ",
    "cannot",
    "must not",
    "禁止",
    "不得",
    "不可",
    "不應",
    "forbidden",
    "forbid",
]


def contains_any(text: str, *needles: str) -> bool:
    lower = text.lower()
    return any(needle in lower for needle in needles)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def path_text(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def looks_like_command_text(line: str) -> bool:
    compact = line.strip().lower()
    if compact.startswith("- "):
        compact = compact[2:].strip()
    if compact.startswith("$"):
        compact = compact[1:].strip()
    compact = compact.strip("`").strip()
    if compact.endswith((".", "。")):
        return False
    # command-like fragments in policy prose should still be catchable when not clearly in prose.
    return bool(
        re.search(
            r"(?:^|[^\w])(?:odoo|git|psql|service|systemctl|docker|gcloud)\b",
            compact,
            re.IGNORECASE,
        )
    )


def is_safe_context(line: str) -> bool:
    compact = line.strip()
    if not compact:
        return False

    if any(re.search(marker, compact, re.IGNORECASE) for marker in SAFE_CONTEXT_MARKERS):
        return True

    if any(re.search(pattern, compact, re.IGNORECASE) for pattern in SAFE_FALSE_BOOLEAN_PATTERNS):
        return True

    lowered = compact.lower()
    if PLAIN_SERVICE_RESTART_RE.match(compact):
        return True
    if any(word in lowered for word in NEGATION_WORDS) and looks_like_command_text(compact):
        return True

    return False

def run(cmd):
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }

def grep_patterns(patterns, paths, classify_context=False):
    hits = []
    files = []
    for p in paths:
        base = ROOT / p
        if base.is_file():
            files.append(base)
        elif base.is_dir():
            for f in base.rglob("*"):
                if f.is_file() and ".git" not in f.parts and "__pycache__" not in f.parts:
                    if f.suffix.lower() in {".md", ".json", ".txt", ".yaml", ".yml", ".py", ".sh", ".xml", ".csv"}:
                        files.append(f)

    for f in files:
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        for lineno, line in enumerate(lines, 1):
            for pat in patterns:
                if re.search(pat, line, re.IGNORECASE):
                    safe_context = is_safe_context(line) if classify_context else False
                    blocking = classify_context and (not safe_context) and looks_like_command_text(line)
                    hits.append({
                        "path": path_text(f),
                        "line": lineno,
                        "pattern": pat,
                        "safe_context": safe_context,
                        "blocking": blocking,
                        "text_preview": line[:180],
                    })
    return hits

def main():
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "runtime/total_field/background_prejudge"
    out_dir.mkdir(parents=True, exist_ok=True)

    files = []
    missing = []
    for rel in CORE_FILES:
        p = ROOT / rel
        if p.exists():
            files.append({
                "path": rel,
                "exists": True,
                "sha256": sha256_file(p),
            })
        else:
            missing.append(rel)
            files.append({
                "path": rel,
                "exists": False,
                "sha256": None,
            })

    dry_reports = []
    report_dir = ROOT / "patent_poc/wuchang_adi_causal_sidecar/runtime/patent_evidence"
    if report_dir.exists():
        for f in sorted(report_dir.glob("*.json")):
            if (
                f.name.startswith("WUCHANG_WISH_TREE_ADI_LAUNCH_DRY_RUN_")
                or f.name.startswith("WUCHANG_WISH_TREE_ADI_FIRE_DRY_RUN_")
                or f.name.startswith("UX_CLOUD_MINIMALITY_GATE_SEAL_")
            ):
                dry_reports.append({
                    "path": str(f.relative_to(ROOT)),
                    "sha256": sha256_file(f),
                })

    git_status = run(["git", "status", "--short", "--", *SCOPE_PATHS])
    secret_hits = grep_patterns(SECRET_PATTERNS, SCOPE_PATHS)
    mutation_hits = grep_patterns(MUTATION_PATTERNS, SCOPE_PATHS, classify_context=True)
    blocking_mutation_hits = [h for h in mutation_hits if h.get("blocking")]
    safe_mutation_text_hits = [h for h in mutation_hits if h.get("safe_context")]
    false_positive_avoided_count = len(safe_mutation_text_hits)
    mutation_text = " ".join(h["text_preview"] for h in blocking_mutation_hits)

    l1 = not missing
    l2 = l1 and bool(dry_reports)
    git_clean = git_status["stdout"].strip() == ""
    l3 = l2 and git_clean

    blockers = []
    if missing:
        blockers.append("MISSING_CORE_FILES")
    if secret_hits:
        blockers.append("SECRET_PATTERN_FOUND")
    if blocking_mutation_hits:
        blockers.append("PRODUCTION_MUTATION_PATTERN_FOUND")

    if blockers:
        state = "HOLD_BACKGROUND_PREJUDGE"
        decision = "HOLD"
    elif l3:
        state = "PASS_L3_GIT_SEALED_MEMORY"
        decision = "ALLOW"
    elif l2:
        state = "PASS_L1_L2_MEMORY_HOLD_L3_GIT_SEAL"
        decision = "REVIEW_FOR_L3_SEAL"
    elif l1:
        state = "PASS_L1_DOC_MEMORY_HOLD_L2_EVIDENCE"
        decision = "REVIEW_FOR_EVIDENCE"
    else:
        state = "HOLD_INCOMPLETE_MEMORY"
        decision = "HOLD"

    report = {
        "schema": "TOTAL_FIELD_BACKGROUND_PREJUDGE_REPORT_V1",
        "state": state,
        "decision": decision,
        "timestamp_utc": now,
        "l1_doc_memory": l1,
        "l2_evidence_memory": l2,
        "l3_git_sealed_memory": l3,
        "missing_core_files": missing,
        "core_files": files,
        "dry_run_reports": dry_reports,
        "git_status_short": git_status["stdout"].splitlines(),
        "secret_hits": secret_hits,
        "mutation_hits": mutation_hits,
        "blocking_mutation_hits": blocking_mutation_hits,
        "safe_mutation_text_hits": safe_mutation_text_hits,
        "safe_mutation_text_hit_count": len(safe_mutation_text_hits),
        "false_positive_avoided_count": false_positive_avoided_count,
        "production_mutation_detected": bool(blocking_mutation_hits),
        "odoo_install_detected": contains_any(mutation_text, "odoo -i", "odoo -u"),
        "service_restart_detected": contains_any(mutation_text, "service restart", "systemctl", "docker restart"),
        "google_api_mutation_detected": contains_any(mutation_text, "gcloud"),
        "git_push_detected": contains_any(mutation_text, "git push"),
        "blockers": blockers,
        "allowed_next": [
            "human_review",
            "exact_file_commit_tag_if_no_blockers",
        ],
        "forbidden_next": [
            "auto_commit_without_human_review",
            "odoo_install",
            "odoo_update",
            "psql_write",
            "service_restart",
            "google_api_mutation",
            "git_push",
        ],
        "production_db_write": False,
        "odoo_install": False,
        "service_restart": False,
        "google_api_mutation": False,
    }

    canonical = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    report["report_hash"] = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    out = out_dir / f"TOTAL_FIELD_BACKGROUND_PREJUDGE_{now}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("STATE=" + state)
    print("DECISION=" + decision)
    print("REPORT=" + str(out))
    print("REPORT_HASH=" + report["report_hash"])
    print("L1_DOC_MEMORY=" + str(l1).upper())
    print("L2_EVIDENCE_MEMORY=" + str(l2).upper())
    print("L3_GIT_SEALED_MEMORY=" + str(l3).upper())
    print("MISSING_COUNT=" + str(len(missing)))
    print("DRY_REPORT_COUNT=" + str(len(dry_reports)))
    print("SECRET_HIT_COUNT=" + str(len(secret_hits)))
    print("MUTATION_HIT_COUNT=" + str(len(mutation_hits)))
    print("BLOCKING_MUTATION_HIT_COUNT=" + str(len(blocking_mutation_hits)))
    print("SAFE_MUTATION_TEXT_HIT_COUNT=" + str(len(safe_mutation_text_hits)))
    print("FALSE_POSITIVE_AVOIDED_COUNT=" + str(false_positive_avoided_count))
    print("BACKGROUND_PREJUDGE_STATE=" + ("ALLOW" if not blockers else "HOLD"))
    print("GIT_DIRTY=" + str(not git_clean).upper())

if __name__ == "__main__":
    main()
