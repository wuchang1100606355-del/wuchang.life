#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W7TP runtime artifact query indexer.

SQLite is a rebuildable local query index only. JSON/JSONL/MANIFEST/SHA256
artifacts remain authoritative.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path("runtime/index/w7tp_runtime_query.sqlite3")
DEFAULT_SOURCE_ROOTS = [
    Path("runtime"),
    Path("schemas"),
    Path("packets"),
    Path("docs/ledger"),
    Path("runtime/dead_letter"),
    Path("runtime/patent_delivery"),
]
SUPPORTED_SUFFIXES = {
    ".json",
    ".jsonl",
    ".ndjson",
    ".sha256",
    ".sha256sum",
    ".sha256sums",
    ".manifest",
    ".txt",
    ".md",
}
RAW_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".opus"}
MAX_READ_BYTES = 2 * 1024 * 1024


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS index_meta(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL UNIQUE,
  sha256 TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  run_id TEXT,
  created_at TEXT,
  file_mtime TEXT,
  indexed_at TEXT NOT NULL,
  parse_status TEXT NOT NULL,
  parse_error_redacted TEXT
);

CREATE TABLE IF NOT EXISTS packets(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  packet_id TEXT,
  packet_hash TEXT,
  packet_type TEXT,
  schema_ref TEXT,
  artifact_id INTEGER,
  cloud_authority TEXT,
  local_authority TEXT,
  FOREIGN KEY(artifact_id) REFERENCES artifacts(id)
);

CREATE TABLE IF NOT EXISTS decisions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  packet_id TEXT,
  packet_hash TEXT,
  decision TEXT,
  execution_allowed TEXT,
  failure_reason TEXT,
  evidence_ref TEXT,
  artifact_id INTEGER,
  FOREIGN KEY(artifact_id) REFERENCES artifacts(id)
);

CREATE TABLE IF NOT EXISTS dead_letters(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  packet_hash TEXT,
  mailbox_ref TEXT,
  failure_reason TEXT,
  retry_policy TEXT,
  status TEXT,
  artifact_id INTEGER,
  FOREIGN KEY(artifact_id) REFERENCES artifacts(id)
);

CREATE TABLE IF NOT EXISTS patent_claims(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  package_id TEXT,
  claim_no TEXT,
  claim_text TEXT,
  claim_hash TEXT,
  topic TEXT,
  source_file TEXT,
  artifact_id INTEGER,
  FOREIGN KEY(artifact_id) REFERENCES artifacts(id)
);

CREATE TABLE IF NOT EXISTS validation_gates(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  package_id TEXT,
  gate_name TEXT,
  gate_value TEXT,
  source_file TEXT,
  artifact_id INTEGER,
  FOREIGN KEY(artifact_id) REFERENCES artifacts(id)
);

CREATE TABLE IF NOT EXISTS evidence_seals(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seal_hash TEXT,
  packet_hash TEXT,
  decision TEXT,
  previous_seal_hash TEXT,
  artifact_id INTEGER,
  FOREIGN KEY(artifact_id) REFERENCES artifacts(id)
);

CREATE TABLE IF NOT EXISTS scan_errors(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file TEXT NOT NULL,
  error_type TEXT NOT NULL,
  error_message_redacted TEXT,
  line_no INTEGER,
  indexed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_artifacts_sha256 ON artifacts(sha256);
CREATE INDEX IF NOT EXISTS idx_artifacts_run_id ON artifacts(run_id);
CREATE INDEX IF NOT EXISTS idx_packets_packet_id ON packets(packet_id);
CREATE INDEX IF NOT EXISTS idx_packets_packet_hash ON packets(packet_hash);
CREATE INDEX IF NOT EXISTS idx_decisions_packet_hash ON decisions(packet_hash);
CREATE INDEX IF NOT EXISTS idx_dead_letters_packet_hash ON dead_letters(packet_hash);
CREATE INDEX IF NOT EXISTS idx_patent_claims_claim_no ON patent_claims(claim_no);
CREATE INDEX IF NOT EXISTS idx_validation_gates_gate ON validation_gates(gate_name, gate_value);
CREATE INDEX IF NOT EXISTS idx_evidence_seals_packet_hash ON evidence_seals(packet_hash);
CREATE INDEX IF NOT EXISTS idx_evidence_seals_seal_hash ON evidence_seals(seal_hash);
"""


SECRET_PATTERNS = [
    ("PRIVATE_KEY_BLOCK", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("API_KEY_PATTERN_HIT", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})\b")),
    ("SECRET_PATTERN_HIT", re.compile(r"\b(?:access_token|refresh_token|client_secret|api_key|secret|password|router_password)\b['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_./+=:-]{8,}", re.IGNORECASE)),
]
OTHER_RISK_PATTERNS = [
    ("RAW_AUDIO_MARKER_HIT", re.compile(r"\b(?:raw_audio|audio/wav|audio/mpeg|audio_blob)\b", re.IGNORECASE)),
    ("WHY_IT_RUNS_HIT", re.compile(r"WHY_IT_RUNS")),
    ("PRIVATE_WEIGHT_HIT", re.compile(r"\b(?:private_weight|model_weight|完整查表|完整表格|lookup table full)\b", re.IGNORECASE)),
    ("MEMBER_PLAINTEXT_PATTERN_HIT", re.compile(r"\b(?:raw_member)\b|完整會員|會員明文|身分證|身份證|完整電話|完整地址", re.IGNORECASE)),
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def iter_files(source_roots: List[Path]) -> Iterable[Path]:
    seen: set[Path] = set()
    for root in source_roots:
        base = root if root.is_absolute() else ROOT / root
        if not base.exists():
            continue
        if base.is_file():
            candidates = [base]
        else:
            candidates = [p for p in base.rglob("*") if p.is_file()]
        for path in candidates:
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            suffix = path.suffix.lower()
            if suffix in SUPPORTED_SUFFIXES or suffix in RAW_AUDIO_SUFFIXES:
                yield path


def file_mtime(path: Path) -> str:
    return dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_text_limited(path: Path, max_bytes: int) -> Tuple[Optional[str], str]:
    size = path.stat().st_size
    if path.suffix.lower() in RAW_AUDIO_SUFFIXES:
        return None, "HOLD_SENSITIVE"
    if size > max_bytes:
        return None, "SKIP_TOO_LARGE"
    return path.read_text(encoding="utf-8", errors="replace"), "PARSED"


def risk_scan(text: Optional[str], path: Path) -> List[Dict[str, Any]]:
    risks: List[Dict[str, Any]] = []
    if path.suffix.lower() in RAW_AUDIO_SUFFIXES:
        return [{"error_type": "RAW_AUDIO_EXTENSION_HIT", "hit_count": 1, "line_no": None}]
    if text is None:
        return risks
    for error_type, pattern in SECRET_PATTERNS + OTHER_RISK_PATTERNS:
        count = len(pattern.findall(text))
        if count:
            risks.append({"error_type": error_type, "hit_count": count, "line_no": None})
    return risks


def artifact_type(path: Path, text: Optional[str]) -> str:
    lower_path = safe_rel(path).lower()
    lower_text = (text or "").lower()
    if "dead_letter" in lower_path:
        return "dead_letter"
    if "patent" in lower_path or "claim" in lower_path:
        return "patent"
    if "seal" in lower_path or "seal_hash" in lower_text:
        return "evidence_seal"
    if "packet_id" in lower_text or "packet_hash" in lower_text:
        return "packet"
    if "decision" in lower_text or "execution_allowed" in lower_text:
        return "decision"
    if "pass" in lower_text or "hold" in lower_text or "validation" in lower_text or "gate" in lower_text:
        return "validation"
    return "artifact"


def as_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def find_first(obj: Any, keys: List[str]) -> Optional[Any]:
    if isinstance(obj, dict):
        for key in keys:
            if key in obj:
                return obj[key]
        for value in obj.values():
            found = find_first(value, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_first(value, keys)
            if found is not None:
                return found
    return None


def iter_json_objects(text: str, path: Path) -> Tuple[List[Any], List[Dict[str, Any]]]:
    suffix = path.suffix.lower()
    errors: List[Dict[str, Any]] = []
    objects: List[Any] = []
    if suffix in {".jsonl", ".ndjson"}:
        for lineno, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                objects.append(json.loads(line))
            except json.JSONDecodeError:
                errors.append({
                    "source_file": safe_rel(path),
                    "error_type": "JSONL_PARSE_ERROR",
                    "error_message_redacted": "redacted JSONL parse error",
                    "line_no": lineno,
                })
    elif suffix == ".json" or suffix == ".manifest":
        try:
            objects.append(json.loads(text))
        except json.JSONDecodeError:
            errors.append({
                "source_file": safe_rel(path),
                "error_type": "JSON_PARSE_ERROR",
                "error_message_redacted": "redacted JSON parse error",
                "line_no": None,
            })
    return objects, errors


def text_gate_rows(text: str, source_file: str) -> List[Dict[str, Optional[str]]]:
    rows = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        upper = stripped.upper()
        for value in ("PASS", "HOLD", "FAIL"):
            if value not in upper:
                continue
            gate_name = stripped.split("=", 1)[0].strip("- `:")[:120] if "=" in stripped else f"line_{lineno}"
            rows.append({
                "package_id": None,
                "gate_name": gate_name or f"line_{lineno}",
                "gate_value": value,
                "source_file": source_file,
            })
            break
    return rows


def is_public_claim_source(path: Path) -> bool:
    lower = safe_rel(path).lower()
    if any(marker in lower for marker in ("private", "non_public", "non-public")):
        return False
    if "confidential" in lower and not any(marker in lower for marker in ("non-confidential", "non_confidential")):
        return False
    return any(marker in lower for marker in ("non-confidential", "non_confidential", "public", "sanitized"))


def extraction_rows(obj: Any, path: Path, source_file: str) -> Dict[str, List[Dict[str, Optional[str]]]]:
    packet_id = as_text(find_first(obj, ["packet_id"]))
    packet_hash = as_text(find_first(obj, ["packet_hash"]))
    packet_type = as_text(find_first(obj, ["packet_type"]))
    schema_ref = as_text(find_first(obj, ["schema_ref"]))
    decision = as_text(find_first(obj, ["decision", "verifier_decision", "route_decision", "backend_decision"]))
    execution_allowed = as_text(find_first(obj, ["execution_allowed"]))
    evidence_ref = as_text(find_first(obj, ["evidence_ref"]))
    seal_hash = as_text(find_first(obj, ["seal_hash", "seal"]))
    claim_text = as_text(find_first(obj, ["claim_text"]))
    claim_no = as_text(find_first(obj, ["claim_no", "claim_number"]))
    gate_name = as_text(find_first(obj, ["gate_name", "name"]))
    gate_value = as_text(find_first(obj, ["gate_value", "STATE", "state"]))

    rows: Dict[str, List[Dict[str, Optional[str]]]] = {
        "packets": [],
        "decisions": [],
        "dead_letters": [],
        "patent_claims": [],
        "validation_gates": [],
        "evidence_seals": [],
    }

    if any([packet_id, packet_hash, packet_type, schema_ref]):
        rows["packets"].append({
            "packet_id": packet_id,
            "packet_hash": packet_hash,
            "packet_type": packet_type,
            "schema_ref": schema_ref,
            "cloud_authority": as_text(find_first(obj, ["cloud_authority"])),
            "local_authority": as_text(find_first(obj, ["local_authority"])),
        })

    if any([decision, execution_allowed, evidence_ref]):
        rows["decisions"].append({
            "packet_id": packet_id,
            "packet_hash": packet_hash,
            "decision": decision,
            "execution_allowed": execution_allowed,
            "failure_reason": as_text(find_first(obj, ["failure_reason"])),
            "evidence_ref": evidence_ref,
        })

    if "dead_letter" in source_file.lower() or as_text(find_first(obj, ["mailbox_ref", "mailbox_backend_path"])):
        rows["dead_letters"].append({
            "packet_hash": packet_hash,
            "mailbox_ref": as_text(find_first(obj, ["mailbox_ref", "mailbox_backend_path"])),
            "failure_reason": as_text(find_first(obj, ["failure_reason"])),
            "retry_policy": as_text(find_first(obj, ["retry_policy", "retryable"])),
            "status": as_text(find_first(obj, ["status", "decision"])),
        })

    if claim_no or claim_text or "claim" in source_file.lower() or "patent" in source_file.lower():
        safe_claim_text = claim_text if claim_text and is_public_claim_source(path) else None
        rows["patent_claims"].append({
            "package_id": as_text(find_first(obj, ["package_id"])),
            "claim_no": claim_no,
            "claim_text": safe_claim_text,
            "claim_hash": sha256_text(claim_text) if claim_text else as_text(find_first(obj, ["claim_hash"])),
            "topic": as_text(find_first(obj, ["topic"])),
            "source_file": source_file,
        })

    if gate_name or gate_value:
        value = gate_value
        if value and value.upper() not in {"PASS", "HOLD", "FAIL"}:
            upper = value.upper()
            value = next((v for v in ("PASS", "HOLD", "FAIL") if v in upper), value)
        rows["validation_gates"].append({
            "package_id": as_text(find_first(obj, ["package_id"])),
            "gate_name": gate_name or "STATE",
            "gate_value": value,
            "source_file": source_file,
        })

    if seal_hash:
        rows["evidence_seals"].append({
            "seal_hash": seal_hash,
            "packet_hash": packet_hash,
            "decision": decision,
            "previous_seal_hash": as_text(find_first(obj, ["previous_seal_hash"])),
        })
    return rows


def merge_rows(target: Dict[str, List[Dict[str, Optional[str]]]], incoming: Dict[str, List[Dict[str, Optional[str]]]]) -> None:
    for key, rows in incoming.items():
        target.setdefault(key, []).extend(rows)


def scan_file(path: Path, indexed_at: str, max_bytes: int = MAX_READ_BYTES) -> Dict[str, Any]:
    rel = safe_rel(path)
    sha = sha256_file(path)
    text, parse_status = read_text_limited(path, max_bytes)
    risks = risk_scan(text, path)
    if risks:
        parse_status = "HOLD_SENSITIVE"
    atype = artifact_type(path, text)
    rows: Dict[str, List[Dict[str, Optional[str]]]] = {
        "packets": [],
        "decisions": [],
        "dead_letters": [],
        "patent_claims": [],
        "validation_gates": [],
        "evidence_seals": [],
    }
    parse_errors: List[Dict[str, Any]] = []
    run_id = None
    created_at = None

    if text is not None and parse_status != "HOLD_SENSITIVE":
        objects, json_errors = iter_json_objects(text, path)
        parse_errors.extend(json_errors)
        for obj in objects:
            run_id = run_id or as_text(find_first(obj, ["run_id", "RUN_ID"]))
            created_at = created_at or as_text(find_first(obj, ["created_at", "timestamp", "created_at_unix"]))
            merge_rows(rows, extraction_rows(obj, path, rel))
        for row in text_gate_rows(text, rel):
            rows["validation_gates"].append(row)

    artifact = {
        "path": rel,
        "sha256": sha,
        "artifact_type": atype,
        "run_id": run_id,
        "created_at": created_at,
        "file_mtime": file_mtime(path),
        "indexed_at": indexed_at,
        "parse_status": parse_status if not parse_errors else "PARTIAL_PARSE",
        "parse_error_redacted": None if not parse_errors else f"redacted parse errors count={len(parse_errors)}",
    }

    scan_errors = []
    for risk in risks:
        scan_errors.append({
            "source_file": rel,
            "error_type": risk["error_type"],
            "error_message_redacted": f"redacted sensitive pattern hit count={risk['hit_count']}",
            "line_no": risk.get("line_no"),
            "indexed_at": indexed_at,
        })
    for error in parse_errors:
        scan_errors.append({**error, "indexed_at": indexed_at})

    return {
        "artifact": artifact,
        "rows": rows,
        "scan_errors": scan_errors,
    }


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA_SQL)


def insert_scan(con: sqlite3.Connection, scan: Dict[str, Any]) -> None:
    artifact = scan["artifact"]
    cur = con.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO artifacts(path, sha256, artifact_type, run_id, created_at, file_mtime, indexed_at, parse_status, parse_error_redacted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact["path"],
            artifact["sha256"],
            artifact["artifact_type"],
            artifact["run_id"],
            artifact["created_at"],
            artifact["file_mtime"],
            artifact["indexed_at"],
            artifact["parse_status"],
            artifact["parse_error_redacted"],
        ),
    )
    artifact_id = cur.execute("SELECT id FROM artifacts WHERE path=?", (artifact["path"],)).fetchone()[0]

    for row in scan["rows"]["packets"]:
        cur.execute(
            "INSERT INTO packets(packet_id, packet_hash, packet_type, schema_ref, artifact_id, cloud_authority, local_authority) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row.get("packet_id"), row.get("packet_hash"), row.get("packet_type"), row.get("schema_ref"), artifact_id, row.get("cloud_authority"), row.get("local_authority")),
        )
    for row in scan["rows"]["decisions"]:
        cur.execute(
            "INSERT INTO decisions(packet_id, packet_hash, decision, execution_allowed, failure_reason, evidence_ref, artifact_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row.get("packet_id"), row.get("packet_hash"), row.get("decision"), row.get("execution_allowed"), row.get("failure_reason"), row.get("evidence_ref"), artifact_id),
        )
    for row in scan["rows"]["dead_letters"]:
        cur.execute(
            "INSERT INTO dead_letters(packet_hash, mailbox_ref, failure_reason, retry_policy, status, artifact_id) VALUES (?, ?, ?, ?, ?, ?)",
            (row.get("packet_hash"), row.get("mailbox_ref"), row.get("failure_reason"), row.get("retry_policy"), row.get("status"), artifact_id),
        )
    for row in scan["rows"]["patent_claims"]:
        cur.execute(
            "INSERT INTO patent_claims(package_id, claim_no, claim_text, claim_hash, topic, source_file, artifact_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row.get("package_id"), row.get("claim_no"), row.get("claim_text"), row.get("claim_hash"), row.get("topic"), row.get("source_file"), artifact_id),
        )
    for row in scan["rows"]["validation_gates"]:
        cur.execute(
            "INSERT INTO validation_gates(package_id, gate_name, gate_value, source_file, artifact_id) VALUES (?, ?, ?, ?, ?)",
            (row.get("package_id"), row.get("gate_name"), row.get("gate_value"), row.get("source_file"), artifact_id),
        )
    for row in scan["rows"]["evidence_seals"]:
        cur.execute(
            "INSERT INTO evidence_seals(seal_hash, packet_hash, decision, previous_seal_hash, artifact_id) VALUES (?, ?, ?, ?, ?)",
            (row.get("seal_hash"), row.get("packet_hash"), row.get("decision"), row.get("previous_seal_hash"), artifact_id),
        )
    for row in scan["scan_errors"]:
        cur.execute(
            "INSERT INTO scan_errors(source_file, error_type, error_message_redacted, line_no, indexed_at) VALUES (?, ?, ?, ?, ?)",
            (row["source_file"], row["error_type"], row.get("error_message_redacted"), row.get("line_no"), row["indexed_at"]),
        )


def scan_sources(source_roots: List[Path], max_bytes: int = MAX_READ_BYTES) -> Dict[str, Any]:
    indexed_at = now_iso()
    scans = []
    for path in iter_files(source_roots):
        scans.append(scan_file(path, indexed_at, max_bytes=max_bytes))
    return {
        "STATE": "PASS_RUNTIME_QUERY_INDEX_SCAN",
        "indexed_at": indexed_at,
        "source_roots": [str(root) for root in source_roots],
        "artifact_count": len(scans),
        "hold_sensitive_count": sum(1 for item in scans if item["artifact"]["parse_status"] == "HOLD_SENSITIVE"),
        "scan_error_count": sum(len(item["scan_errors"]) for item in scans),
        "artifacts": [item["artifact"] for item in scans],
        "scan_errors": [err for item in scans for err in item["scan_errors"]],
        "scans": scans,
    }


def write_report(path: Optional[Path], report: Dict[str, Any]) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_report = {k: v for k, v in report.items() if k != "scans"}
    path.write_text(json.dumps(safe_report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_index(db_path: Path, scan_report: Dict[str, Any], rebuild: bool) -> None:
    if rebuild and db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        init_db(con)
        con.execute("INSERT OR REPLACE INTO index_meta(key, value) VALUES (?, ?)", ("schema_version", "v1"))
        con.execute("INSERT OR REPLACE INTO index_meta(key, value) VALUES (?, ?)", ("indexed_at", scan_report["indexed_at"]))
        con.execute("INSERT OR REPLACE INTO index_meta(key, value) VALUES (?, ?)", ("authority", "rebuildable_query_index_only"))
        for scan in scan_report["scans"]:
            insert_scan(con, scan)
        con.commit()
    finally:
        con.close()


def rows_to_dicts(cur: sqlite3.Cursor, rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    names = [description[0] for description in cur.description]
    return [dict(zip(names, row)) for row in rows]


def query_db(db_path: Path, mode: str, value: str) -> Dict[str, Any]:
    if not db_path.exists():
        raise SystemExit(f"query index not found: {db_path}")
    con = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        if mode == "run_id":
            cur.execute("SELECT path, sha256, artifact_type, run_id, parse_status FROM artifacts WHERE run_id=?", (value,))
            results = {"artifacts": rows_to_dicts(cur, cur.fetchall())}
        elif mode == "sha256":
            cur.execute("SELECT path, sha256, artifact_type, run_id, parse_status FROM artifacts WHERE sha256=?", (value,))
            results = {"artifacts": rows_to_dicts(cur, cur.fetchall())}
        elif mode == "packet_hash":
            results = {}
            for table in ("packets", "decisions", "dead_letters", "evidence_seals"):
                cur.execute(f"SELECT * FROM {table} WHERE packet_hash=?", (value,))
                results[table] = rows_to_dicts(cur, cur.fetchall())
        elif mode == "claim_no":
            cur.execute("SELECT package_id, claim_no, claim_text, claim_hash, topic, source_file FROM patent_claims WHERE claim_no=?", (value,))
            results = {"patent_claims": rows_to_dicts(cur, cur.fetchall())}
        elif mode == "gate":
            cur.execute("SELECT package_id, gate_name, gate_value, source_file FROM validation_gates WHERE gate_value=?", (value,))
            results = {"validation_gates": rows_to_dicts(cur, cur.fetchall())}
        else:
            raise SystemExit(f"unsupported query mode: {mode}")
    finally:
        con.close()
    return {
        "STATE": "PASS_RUNTIME_QUERY_INDEX_QUERY",
        "db": str(db_path),
        "query": mode,
        "value": value,
        "execution_allowed": False,
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or query a rebuildable W7TP runtime artifact SQLite index.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite DB path")
    parser.add_argument("--source-root", action="append", default=[], help="source root to scan; may be used multiple times")
    parser.add_argument("--dry-run", action="store_true", help="scan only; do not write SQLite")
    parser.add_argument("--write-index", action="store_true", help="explicitly authorize SQLite index writes")
    parser.add_argument("--rebuild", action="store_true", help="with --write-index, delete old index and rebuild")
    parser.add_argument("--report-json", help="write scan report JSON")
    parser.add_argument("--query", choices=["run_id", "sha256", "packet_hash", "claim_no", "gate"], help="query mode")
    parser.add_argument("--value", help="query value")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db)

    if args.query:
        if not args.value:
            raise SystemExit("--value is required with --query")
        result = query_db(db_path, args.query, args.value)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    source_roots = [Path(item) for item in args.source_root] if args.source_root else DEFAULT_SOURCE_ROOTS
    report = scan_sources(source_roots)
    report["dry_run"] = not args.write_index
    report["db"] = str(db_path)
    report["write_index"] = bool(args.write_index)
    report["rebuild"] = bool(args.rebuild and args.write_index)

    if args.write_index:
        write_index(db_path, report, rebuild=args.rebuild)
        report["STATE"] = "PASS_RUNTIME_QUERY_INDEX_WRITE"
    else:
        report["STATE"] = "PASS_RUNTIME_QUERY_INDEX_DRY_RUN"

    write_report(Path(args.report_json) if args.report_json else None, report)
    printable = {k: v for k, v in report.items() if k not in {"scans"}}
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
