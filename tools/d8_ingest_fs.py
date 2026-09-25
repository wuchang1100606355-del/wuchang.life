#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path


RUN_PREFIX = "D8_INGEST"
DEFAULT_MAX_BYTES = 524288

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    ".venv-p8",
    ".venv-d8",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    "coverage",
    ".tox",
    ".idea",
    ".vscode",
}

SKIP_PATH_PARTS = {
    ".ssh",
    ".gnupg",
}

SKIP_REL_DIRS = {
    "runtime/d8_db",
    "runtime/p8_db",
}

TEXT_EXTS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".md",
    ".txt",
    ".rst",
    ".adoc",
    ".sql",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".csv",
    ".tsv",
    ".log",
    ".html",
    ".css",
    ".scss",
    ".xml",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".php",
    ".rb",
    ".swift",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".dockerfile",
    ".service",
}

SPECIAL_TEXT_NAMES = {
    "Dockerfile",
    "docker-compose.yml",
    "compose.yml",
    "Makefile",
    "README",
    "LICENSE",
}

SECRET_EXACT_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}

SECRET_NAME_PARTS = (
    "secret",
    "credential",
    "credentials",
    "token",
    "password",
    "passwd",
    "private_key",
    "private-key",
    "apikey",
    "api_key",
    "client_secret",
)

SECRET_SUFFIXES = (".pem", ".p12", ".pfx", ".key")

SECRET_CONTENT_PATTERNS = (
    ("PRIVATE_KEY_BLOCK", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("AWS_ACCESS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bgh[opusr]_[A-Za-z0-9_]{20,}\b")),
    ("OPENAI_STYLE_KEY", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    (
        "SECRET_ASSIGNMENT",
        re.compile(
            r"(?i)\b(password|passwd|api_key|apikey|secret|token|client_secret)\b"
            r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=:-]{16,}"
        ),
    ),
)

FLAGS = {
    "SECRET_PATH_SKIPPED": True,
    "SECRET_LIKE_CONTENT_REJECTED": True,
    "EXTERNAL_API_CALL": False,
    "PRODUCTION_DB_WRITE": False,
    "D8_LOCAL_DB_WRITE": True,
    "SERVICE_RESTART": False,
    "DEPLOY": False,
    "PRODUCTION_RELEASE": False,
    "EMBEDDING_GENERATED": False,
}


def utc_run_id() -> str:
    return RUN_PREFIX + "_" + dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")


def rel_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def is_secret_like_name(path: Path) -> bool:
    name = path.name
    lower_name = name.lower()
    if name in SECRET_EXACT_NAMES or lower_name in SECRET_EXACT_NAMES:
        return True
    if any(part in lower_name for part in SECRET_NAME_PARTS):
        return True
    return lower_name.endswith(SECRET_SUFFIXES)


def has_secret_path_part(path: Path) -> bool:
    return any(part in SKIP_PATH_PARTS for part in path.parts)


def should_skip_dir(dir_path: Path, root: Path) -> bool:
    if dir_path.name in SKIP_DIRS or has_secret_path_part(dir_path):
        return True
    rel = rel_path(dir_path, root)
    return rel in SKIP_REL_DIRS or any(rel.startswith(prefix + "/") for prefix in SKIP_REL_DIRS)


def is_supported_text_file(path: Path) -> bool:
    if path.name in SPECIAL_TEXT_NAMES:
        return True
    return path.suffix.lower() in TEXT_EXTS


def decode_text(data: bytes) -> str | None:
    if b"\x00" in data:
        return None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\x00" not in text:
            return text
    return None


def secret_content_reason(text: str) -> str | None:
    for reason, pattern in SECRET_CONTENT_PATTERNS:
        if pattern.search(text):
            return reason
    return None


def infer_domain(source_path: str) -> str:
    p = source_path.lower()
    if any(x in p for x in ("patent", "專利", "claim")):
        return "patent"
    if any(x in p for x in ("coffee", "咖啡", "bean", "roast")):
        return "coffee"
    if any(x in p for x in ("voice", "audio", "stt", "tts")):
        return "voice"
    if any(x in p for x in ("openapi", "route", "api")):
        return "api"
    if any(x in p for x in ("runtime", "report", "log")):
        return "ops"
    if any(x in p for x in ("src", "app", "server", "client")):
        return "code"
    return "taiji"


def infer_object_type(path: Path) -> str:
    ext = path.suffix.lower()
    name = path.name
    if name == "Dockerfile" or ext == ".dockerfile":
        return "container"
    if ext in {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".php",
        ".rb",
        ".swift",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".html",
        ".css",
        ".scss",
    }:
        return "code"
    if ext == ".sql":
        return "sql"
    if ext in {".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".service"}:
        return "config"
    if ext in {".md", ".rst", ".adoc"}:
        return "note"
    if ext in {".json", ".jsonl", ".xml"}:
        return "data"
    if ext in {".csv", ".tsv"}:
        return "tabular"
    if ext == ".log":
        return "log"
    if ext in {".sh", ".bash", ".zsh", ".ps1"}:
        return "script"
    return "text"


def infer_risk(source_path: str) -> str:
    p = source_path.lower()
    if "prod" in p or "production" in p:
        return "prod_blocked"
    if any(x in p for x in ("patent", "專利", "claim")):
        return "patent_sensitive"
    if any(x in p for x in ("legal", "contract", "合約")):
        return "restricted"
    return "internal"


def tags_for(source_path: str, domain: str, object_type: str, risk: str) -> list[str]:
    tags = [domain, object_type, risk]
    parts = Path(source_path).parts[:3]
    tags.extend(part.lower() for part in parts if part and part not in {".", ".."})
    return sorted(set(tags))


def build_packet(path: Path, root: Path, actor: str, run_id: str, text: str, data: bytes) -> dict:
    source_path = rel_path(path, root)
    body_sha256 = hashlib.sha256(data).hexdigest()
    d8_seed = f"{actor}\0{source_path}\0{body_sha256}".encode("utf-8")
    d8_id = "d8:" + hashlib.sha256(d8_seed).hexdigest()[:40]
    domain = infer_domain(source_path)
    object_type = infer_object_type(path)
    risk = infer_risk(source_path)
    stat = path.stat()
    ext = path.suffix.lower() if path.suffix else path.name
    semantic_key = {
        "tags": tags_for(source_path, domain, object_type, risk),
        "ext": ext,
        "run_id": run_id,
        "flags": FLAGS,
    }
    return {
        "d8_id": d8_id,
        "domain": domain,
        "object_type": object_type,
        "source": "filesystem",
        "source_path": source_path,
        "source_uri": None,
        "time_version": dt.datetime.fromtimestamp(stat.st_mtime, dt.UTC),
        "actor_scope": actor,
        "intent": "classify_retrieve",
        "risk": risk,
        "semantic_key": semantic_key,
        "title": path.name,
        "body": text,
        "body_sha256": body_sha256,
        "byte_size": len(data),
        "line_count": text.count("\n") + (1 if text else 0),
    }


def scan(root: Path, actor: str, run_id: str, max_bytes: int, limit: int | None) -> tuple[list[dict], list[dict], int]:
    accepted: list[dict] = []
    rejected: list[dict] = []
    scanned = 0

    for current_root, dirs, files in os.walk(root):
        current = Path(current_root)
        dirs[:] = sorted(d for d in dirs if not should_skip_dir(current / d, root))
        for filename in sorted(files):
            path = current / filename
            source_path = rel_path(path, root)
            scanned += 1
            if is_secret_like_name(path) or has_secret_path_part(path):
                rejected.append({"path": source_path, "reason": "SECRET_LIKE_PATH"})
                continue
            if not is_supported_text_file(path):
                rejected.append({"path": source_path, "reason": "UNSUPPORTED_OR_BINARY_TYPE"})
                continue
            try:
                size = path.stat().st_size
            except OSError as exc:
                rejected.append({"path": source_path, "reason": f"STAT_FAILED:{exc.__class__.__name__}"})
                continue
            if size > max_bytes:
                rejected.append({"path": source_path, "reason": "TOO_LARGE"})
                continue
            try:
                data = path.read_bytes()
            except OSError as exc:
                rejected.append({"path": source_path, "reason": f"READ_FAILED:{exc.__class__.__name__}"})
                continue
            text = decode_text(data)
            if text is None:
                rejected.append({"path": source_path, "reason": "BINARY_OR_UNDECODABLE"})
                continue
            reason = secret_content_reason(text)
            if reason:
                rejected.append({"path": source_path, "reason": f"SECRET_LIKE_CONTENT:{reason}"})
                continue
            accepted.append(build_packet(path, root, actor, run_id, text, data))
            if limit is not None and len(accepted) >= limit:
                return accepted, rejected, scanned
    return accepted, rejected, scanned


def write_report(root: Path, report: dict) -> Path:
    reports_dir = root / "runtime" / "d8_db" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")
    path = reports_dir / f"{RUN_PREFIX}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def insert_packets(database_url: str, root: Path, run_id: str, packets: list[dict], scanned: int, rejected: int) -> int:
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise SystemExit(f"psycopg is required for non-dry-run ingestion: {exc}") from exc

    sql = """
        INSERT INTO d8_memory (
          d8_id, domain, object_type, source, source_path, source_uri,
          time_version, actor_scope, intent, risk, semantic_key, title,
          body, body_sha256, byte_size, line_count
        )
        VALUES (
          %(d8_id)s, %(domain)s, %(object_type)s, %(source)s, %(source_path)s,
          %(source_uri)s, %(time_version)s, %(actor_scope)s, %(intent)s,
          %(risk)s, %(semantic_key)s, %(title)s, %(body)s, %(body_sha256)s,
          %(byte_size)s, %(line_count)s
        )
        ON CONFLICT (d8_id) DO UPDATE SET
          domain = EXCLUDED.domain,
          object_type = EXCLUDED.object_type,
          source = EXCLUDED.source,
          source_path = EXCLUDED.source_path,
          source_uri = EXCLUDED.source_uri,
          time_version = EXCLUDED.time_version,
          actor_scope = EXCLUDED.actor_scope,
          intent = EXCLUDED.intent,
          risk = EXCLUDED.risk,
          semantic_key = EXCLUDED.semantic_key,
          title = EXCLUDED.title,
          body = EXCLUDED.body,
          body_sha256 = EXCLUDED.body_sha256,
          byte_size = EXCLUDED.byte_size,
          line_count = EXCLUDED.line_count
    """
    inserted = 0
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for packet in packets:
                row = dict(packet)
                row["semantic_key"] = Jsonb(row["semantic_key"])
                cur.execute(sql, row)
                inserted += 1
            cur.execute(
                """
                INSERT INTO d8_ingest_log (
                  run_id, root_path, scanned_count, accepted_count,
                  rejected_count, inserted_count, flags
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (run_id, str(root), scanned, len(packets), rejected, inserted, Jsonb(FLAGS)),
            )
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser(description="D8 filesystem ingestion")
    parser.add_argument("--root", required=True)
    parser.add_argument("--actor", default="user:long")
    parser.add_argument("--database-url")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    run_id = utc_run_id()
    accepted, rejected, scanned = scan(root, args.actor, run_id, args.max_bytes, args.limit)
    inserted = 0
    if not args.dry_run:
        if not args.database_url:
            raise SystemExit("--database-url is required unless --dry-run is set")
        inserted = insert_packets(args.database_url, root, run_id, accepted, scanned, len(rejected))

    report = {
        "run_id": run_id,
        "root": str(root),
        "dry_run": args.dry_run,
        "scanned": scanned,
        "accepted": len(accepted),
        "rejected": len(rejected),
        "inserted": inserted,
        "sample_accepted": [
            {
                "path": item["source_path"],
                "domain": item["domain"],
                "object_type": item["object_type"],
                "risk": item["risk"],
                "body_sha256": item["body_sha256"],
            }
            for item in accepted[:10]
        ],
        "sample_rejected": rejected[:25],
        "flags": FLAGS,
    }
    report_path = write_report(root, report)
    summary = {
        "run_id": run_id,
        "dry_run": args.dry_run,
        "scanned": scanned,
        "accepted": len(accepted),
        "rejected": len(rejected),
        "inserted": inserted,
        "REPORT": report_path.as_posix(),
    }
    print(json.dumps(summary, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
