#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


DEFAULT = Path("configs/ip/wuchang_project_source_manifest.template.json")
DEFAULT_ROOT = Path("/mnt/d/Wuchang_Project")
DECISION = "safe_metadata_inventory_only"
SECRET_KEYWORDS = (
    ".env",
    "secret",
    "client_secret",
    "key",
    "private",
    "token",
    "credential",
    "cert",
    "pem",
    "cloudflare",
    "ca.key",
    "oauth",
    "password",
)
REQUIRED_FIELDS = {
    "source_root",
    "relative_path",
    "filename",
    "extension",
    "is_directory",
    "size_bytes",
    "modified_time",
    "category",
    "possible_use",
    "ip_evidence_candidate",
    "patent_family_candidate",
    "public_disclosure_risk",
    "trade_secret_candidate",
    "secret_or_credential_risk",
    "manual_review_required",
}
FORBIDDEN_FIELDS = {
    "content",
    "excerpt",
    "full_text",
    "file_content",
    "secret_value",
    "raw_text",
}


def has_sensitive_name(path: str) -> bool:
    lowered = path.lower()
    return any(keyword in lowered for keyword in SECRET_KEYWORDS)


def classify(relative_path: str, is_directory: bool) -> tuple[str, str, bool, bool]:
    lowered = relative_path.lower()
    extension = Path(relative_path).suffix.lower()
    if has_sensitive_name(relative_path):
        if any(term in lowered for term in ("cert", "pem", "ca.key", "private_key")):
            return "certificate_or_key_risk", "metadata only; sensitive-name review required", False, True
        return "secret_or_credential_risk", "metadata only; sensitive-name review required", False, True
    if is_directory:
        return "needs_manual_review", "directory grouping for human review", False, False
    if any(term in lowered for term in ("patent", "claim", "copyright", "trade_secret", "ip_")):
        return "patent_or_ip_candidate", "candidate prior work or IP evidence", True, False
    if extension == ".quantum" or any(term in lowered for term in ("packet", "eamtp", "ictp", "quantum")):
        return "quantum_or_packet_artifact", "packet or protocol research candidate", True, False
    if any(term in lowered for term in ("openai", "gemini", "cloud", "provider", "api_bridge")):
        return "cloud_api_or_provider_bridge", "provider integration design candidate", True, False
    if any(term in lowered for term in ("odoo", "pos", "business", "merchant")):
        return "odoo_or_business_integration", "business integration reference", True, False
    if any(term in lowered for term in ("deploy", "runtime", "docker", "compose", "service")):
        return "deployment_or_runtime_script", "runtime design reference", True, False
    if any(term in lowered for term in ("dashboard", "ui", "frontend", "html")):
        return "ui_or_dashboard", "user interface reference", True, False
    if any(term in lowered for term in ("evidence", "report", "log", "audit")):
        return "evidence_log_or_report", "evidence index candidate", True, False
    if extension in {".md", ".txt", ".doc", ".docx", ".pdf"}:
        return "governance_doc", "document review candidate", True, False
    if extension in {".py", ".js", ".ts", ".h", ".c", ".cpp", ".ps1", ".bat", ".sh", ".yml", ".yaml", ".json"}:
        return "source_code", "implementation reference candidate", True, False
    return "needs_manual_review", "unclassified metadata candidate", False, False


def normalize_item(source_root: str, scan_root: Path, path: Path) -> dict[str, object]:
    relative_path = path.relative_to(scan_root).as_posix()
    stat = path.stat()
    category, possible_use, ip_candidate, sensitive = classify(relative_path, path.is_dir())
    return {
        "source_root": source_root,
        "relative_path": relative_path,
        "filename": path.name,
        "extension": path.suffix.lower(),
        "is_directory": path.is_dir(),
        "size_bytes": stat.st_size,
        "modified_time": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "category": category,
        "possible_use": possible_use,
        "ip_evidence_candidate": ip_candidate,
        "patent_family_candidate": category == "patent_or_ip_candidate",
        "public_disclosure_risk": category in {"secret_or_credential_risk", "certificate_or_key_risk"},
        "trade_secret_candidate": sensitive or category in {"patent_or_ip_candidate", "quantum_or_packet_artifact"},
        "secret_or_credential_risk": sensitive,
        "manual_review_required": sensitive or category in {"needs_manual_review", "patent_or_ip_candidate"},
    }


def scan_source_tree(source_root: str, scan_root: Path) -> list[dict[str, object]]:
    items = []
    for path in sorted(scan_root.rglob("*"), key=lambda p: p.as_posix().lower()):
        try:
            items.append(normalize_item(source_root, scan_root, path))
        except OSError:
            continue
    return items


def build_manifest(source_root: str, scan_root: Path) -> dict[str, object]:
    items = scan_source_tree(source_root, scan_root)
    categories = Counter(str(item["category"]) for item in items)
    summary = {
        "total_items": len(items),
        "total_files": sum(not bool(item["is_directory"]) for item in items),
        "total_directories": sum(bool(item["is_directory"]) for item in items),
        "high_risk_sensitive_count": sum(bool(item["secret_or_credential_risk"]) for item in items),
        "category_counts": dict(sorted(categories.items())),
    }
    return {
        "inventory_version": "WUCHANG-PROJECT-SOURCE-INVENTORY/0.1",
        "source_root": source_root,
        "mode": "metadata_only_inventory",
        "read_file_content": False,
        "copy_source_files": False,
        "secret_redaction": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "items": items,
    }


def write_inventory_md(path: Path, manifest: dict[str, object]) -> None:
    summary = manifest["summary"]
    assert isinstance(summary, dict)
    categories = summary["category_counts"]
    assert isinstance(categories, dict)
    ranked = sorted(categories.items(), key=lambda item: (-int(item[1]), str(item[0])))
    category_rows = "\n".join(f"| `{name}` | {count} |" for name, count in ranked)
    candidates = [
        name for name, _ in ranked
        if name in {
            "patent_or_ip_candidate",
            "quantum_or_packet_artifact",
            "source_code",
            "governance_doc",
            "cloud_api_or_provider_bridge",
            "odoo_or_business_integration",
            "evidence_log_or_report",
        }
    ]
    candidate_text = ", ".join(f"`{name}`" for name in candidates) or "`needs_manual_review`"
    text = f"""# Wuchang Project Source Inventory

Status: `metadata-only / plan-only`

## Authorization

The user identified `D:\\Wuchang_Project` as their past development material
and authorized read-only inventory. The user also authorized non-sensitive
self-authored material to be referenced or improved for Wuchang Smart Cloud /
XiaoJ / W7TP. This M28A output intentionally remains metadata-only.

## Source And Time

- Source root: `{manifest["source_root"]}`
- Generated at: `{manifest["generated_at"]}`
- Mode: `metadata_only_inventory`

## Inventory Summary

| Measure | Count |
| --- | ---: |
| Total files | {summary["total_files"]} |
| Total directories | {summary["total_directories"]} |
| High-risk sensitive-name items | {summary["high_risk_sensitive_count"]} |

## Category Summary

| Category | Items |
| --- | ---: |
{category_rows}

## Top Candidate Categories

Candidate metadata groups for later human IP review: {candidate_text}.

## Sensitive Material Boundary

This inventory does not contain source-file contents or original secret
material. Paths matching sensitive keywords are metadata-only records marked
`secret_or_credential_risk=true` and require manual review.

## Next Actions

1. Human-review the protocol, source-code, governance, provider-bridge, and IP-candidate metadata groups.
2. Isolate sensitive-name records from any future content review.
3. Open a separately bounded task before quoting or adapting selected non-sensitive source content.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def validate_manifest(manifest: dict[str, object]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if manifest.get("mode") != "metadata_only_inventory":
        errors.append("mode_must_be_metadata_only_inventory")
    if manifest.get("read_file_content") is not False:
        errors.append("read_file_content_must_be_false")
    if manifest.get("copy_source_files") is not False:
        errors.append("copy_source_files_must_be_false")
    if manifest.get("secret_redaction") is not True:
        errors.append("secret_redaction_must_be_true")

    items = manifest.get("items", [])
    if not isinstance(items, list):
        return errors + ["items_must_be_array"], warnings
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"item_not_object:{index}")
            continue
        missing_fields = REQUIRED_FIELDS - set(item)
        if missing_fields:
            errors.append(f"missing_item_field:{index}:{sorted(missing_fields)[0]}")
        prohibited = FORBIDDEN_FIELDS & set(item)
        if prohibited:
            errors.append(f"forbidden_item_field:{index}:{sorted(prohibited)[0]}")
        path_text = f"{item.get('relative_path', '')}/{item.get('filename', '')}"
        if has_sensitive_name(path_text) and item.get("secret_or_credential_risk") is not True:
            errors.append(f"sensitive_name_not_flagged:{index}")
    return errors, warnings


def resolve_scan_root(source: str) -> Path:
    path = Path(source)
    if path.is_dir():
        return path
    if os.name == "nt" and source.lower().startswith("/mnt/") and len(source) > 6:
        drive = source[5].upper()
        suffix = source[7:].replace("/", "\\")
        windows_path = Path(f"{drive}:\\{suffix}")
        if windows_path.is_dir():
            return windows_path
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or lint metadata-only Wuchang project inventory.")
    parser.add_argument("--source", default=str(DEFAULT_ROOT))
    parser.add_argument("--manifest", default=str(DEFAULT))
    parser.add_argument("--markdown", default="docs/ip/WUCHANG_PROJECT_SOURCE_INVENTORY.md")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not args.validate_only:
        scan_root = resolve_scan_root(args.source)
        if not scan_root.is_dir():
            print(json.dumps({
                "decision": "rejected",
                "errors": ["source_root_not_accessible"],
                "warnings": [],
                "raw_source_copied": False,
                "secret_detected": False,
                "file_content_read": False,
            }, indent=2))
            return 2
        manifest = build_manifest(args.source, scan_root)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_inventory_md(Path(args.markdown), manifest)
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}

    errors, warnings = validate_manifest(manifest) if isinstance(manifest, dict) else (["manifest_must_be_object"], [])
    decision = DECISION if not errors else "rejected"
    print(json.dumps({
        "decision": decision,
        "errors": errors,
        "warnings": warnings,
        "raw_source_copied": False,
        "secret_detected": False,
        "file_content_read": False,
    }, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
