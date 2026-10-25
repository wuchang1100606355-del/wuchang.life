#!/usr/bin/env python3
"""Reconstruct a candidate-only 8D/ADI system intent field from source content.

The Founder intent is the field root.  One source enumeration extracts bounded
content contracts.  Independent child comparators consume only that frozen
index and reconstruct demand, supply, effect, dependency, relation, term,
transition, evidence, authority, reconstruction, and risk coordinates.

Git is neither required nor consulted.  Paths, hashes, and times are evidence
coordinates only; they never define design intent or causality.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


STATE = "CANDIDATE_NOT_CANONICAL"
SCHEMA_VERSION = "trace-file-8d-adi-causality/2.1"
TEXT_LIMIT = 2_000_000
COMPARATOR_NAMES = (
    "DEMAND", "SUPPLY", "EFFECT", "DEPENDENCY", "RELATION", "TERM",
    "STATE_TRANSITION", "EVIDENCE", "AUTHORITY", "RECONSTRUCTION", "RISK",
)
TECHNOLOGY_IDENTITY_AXES = (
    "MECHANISM",
    "CAUSAL_PATH",
    "DEPENDENCIES",
    "ELIMINATED_OPERATIONS",
    "COST_TOPOLOGY",
    "CARRIER_RECONSTRUCTION_VERIFICATION",
)
TEXT_SUFFIXES = {
    ".c", ".cc", ".cpp", ".css", ".go", ".h", ".hpp", ".html", ".ini",
    ".java", ".js", ".json", ".jsx", ".md", ".mjs", ".py", ".rb",
    ".rs", ".service", ".sh", ".sql", ".toml", ".ts", ".tsx", ".txt",
    ".xml", ".yaml", ".yml",
}
STRUCTURAL_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", "vendor",
}
PROTECTED_RE = re.compile(
    r"(^|[._/\-])(\.env|secret|secrets|token|password|passwd|credential|"
    r"credentials|private[_-]?key|member[_-]?plaintext|keys|\.ssh)([._/\-]|$)",
    re.IGNORECASE,
)
PROTECTED_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".sqlite", ".sqlite3", ".mdb"}
SAFE_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.:/-]{2,63}|[\u3400-\u9fff]{2,32}")
EFFECT_RE = re.compile(
    r"\b(create|build|generate|render|read|load|write|save|update|modify|delete|"
    r"remove|send|receive|execute|run|validate|verify|review|approve|reject|"
    r"route|dispatch|resolve|reconstruct|transform|convert|sync|deploy|restart)\w*\b",
    re.IGNORECASE,
)
AUTHORITY_RE = re.compile(
    r"\b(PASS|HOLD|REJECT|CANDIDATE(?:_ONLY|_NOT_CANONICAL)?|CANONICAL|"
    r"AUTHORITY|FOUNDER|TOTAL_FIELD|ALLOW|DENY|ACTIVE|SUSPENDED)\b",
    re.IGNORECASE,
)
STATE_RE = re.compile(
    r"\b(created?|loaded?|running|waiting|completed?|failed?|held|rejected?|"
    r"activated?|suspended?|retired?|superseded?|reconstructed?)\b",
    re.IGNORECASE,
)
RISK_RE = re.compile(
    r"\b(delete|drop|overwrite|deploy|restart|reboot|router|password|secret|token|"
    r"private_key|member_plaintext)\b",
    re.IGNORECASE,
)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        for row in rows:
            handle.write(canonical_bytes(row))


def exact_tokens(text: str, limit: int = 512) -> list[str]:
    values = []
    for token in TOKEN_RE.findall(text):
        folded = token.casefold()
        if not PROTECTED_RE.search(folded):
            values.append(folded)
    return sorted(set(values))[:limit]


def safe_name(value: str) -> str:
    value = re.sub(r"(?<!^)(?=[A-Z])", "_", value).casefold()
    value = re.sub(r"[^a-z0-9\u3400-\u9fff]+", "_", value).strip("_")
    return value[:80] or "unnamed_capability"


def is_protected(rel: str) -> bool:
    return PurePosixPath(rel).suffix.casefold() in PROTECTED_SUFFIXES or bool(PROTECTED_RE.search(rel))


def is_structural_dir(name: str) -> bool:
    folded = name.casefold()
    return folded in STRUCTURAL_DIRS or folded.startswith(".venv") or folded.endswith("-venv")


def is_text(rel: str, data: bytes) -> bool:
    if len(data) > TEXT_LIMIT or b"\x00" in data[:8192]:
        return False
    return Path(rel).suffix.casefold() in TEXT_SUFFIXES or bool(data.strip())


def first_summary(text: str, suffix: str) -> str | None:
    if suffix == ".py":
        try:
            value = ast.get_docstring(ast.parse(text), clean=True)
            if value:
                return value.splitlines()[0][:240]
        except SyntaxError:
            pass
    for raw in text.splitlines()[:80]:
        line = raw.strip()
        if line.startswith("#"):
            candidate = line.lstrip("# ").strip()
        elif line.startswith(("//", "/*", "*")):
            candidate = line.lstrip("/* ").rstrip("*/ ").strip()
        else:
            continue
        if len(candidate) >= 6:
            return candidate[:240]
    return None


def infer_role(rel: str, suffix: str, features: dict[str, Any]) -> str:
    declared = " ".join(features.get("declares", [])).casefold()
    summary = (features.get("summary") or "").casefold()
    combined = f"{declared} {summary}"
    if suffix in {".md", ".txt"}:
        return "DESIGN_OR_EVIDENCE_DOCUMENT"
    if suffix in {".json", ".yaml", ".yml", ".toml", ".ini"}:
        if "schema" in combined or features.get("schema_ids"):
            return "SCHEMA_CONTRACT"
        return "CONFIGURATION_OR_STATE_CONTRACT"
    if suffix == ".service":
        return "SERVICE_DEFINITION"
    if any(name.startswith("test_") or name.endswith("_test") for name in features.get("declares", [])):
        return "VERIFICATION_TEST"
    if features.get("routes"):
        return "INTERFACE_OR_CONTROLLER"
    if "main" in features.get("declares", []) or "argparse" in features.get("imports", []):
        return "ENTRYPOINT_OR_COMMAND"
    if "model" in combined:
        return "STATE_OR_DOMAIN_MODEL"
    if "validator" in combined or "verify" in combined:
        return "VALIDATOR"
    if "adapter" in combined or "bridge" in combined:
        return "ADAPTER_OR_BRIDGE"
    if suffix in {".py", ".js", ".jsx", ".mjs", ".ts", ".tsx", ".go", ".rs", ".java"}:
        return "EXECUTABLE_CAPABILITY_MODULE"
    return "STRUCTURAL_RESOURCE"


def python_features(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "declares": [], "imports": [], "calls": [], "inputs": [], "outputs": [],
        "routes": [], "parse_state": "PARSED",
    }
    try:
        tree = ast.parse(text)
    except SyntaxError:
        result["parse_state"] = "PYTHON_SYNTAX_UNRESOLVED"
        return result
    declarations: set[str] = set()
    imports: set[str] = set()
    calls: set[str] = set()
    inputs: set[str] = set()
    outputs: set[str] = set()
    routes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            declarations.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                inputs.update(arg.arg for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs])
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and decorator.args and isinstance(decorator.args[0], ast.Constant):
                        value = decorator.args[0].value
                        if isinstance(value, str) and value.startswith("/"):
                            routes.add(value)
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(("." * node.level) + node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        elif isinstance(node, ast.Return):
            if isinstance(node.value, ast.Name):
                outputs.add(node.value.id)
            elif isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name):
                    outputs.add(node.value.func.id)
                elif isinstance(node.value.func, ast.Attribute):
                    outputs.add(node.value.func.attr)
            elif node.value is not None:
                outputs.add(type(node.value).__name__)
    result.update({
        "declares": sorted(declarations), "imports": sorted(imports),
        "calls": sorted(calls), "inputs": sorted(inputs), "outputs": sorted(outputs),
        "routes": sorted(routes),
    })
    return result


def extract_features(rel: str, data: bytes, intent_tokens: set[str]) -> dict[str, Any]:
    base: dict[str, Any] = {
        "content_analyzed": False, "summary": None, "declares": [], "imports": [],
        "calls": [], "inputs": [], "outputs": [], "routes": [], "relative_refs": [],
        "schema_ids": [], "config_keys": [], "effects": [], "authority_terms": [],
        "state_terms": [], "risk_terms": [], "technical_terms": [], "intent_matches": [],
        "provides": [], "requires": [], "parse_state": "NON_TEXT_STRUCTURAL",
    }
    if not is_text(rel, data):
        return base
    text = data.decode("utf-8", "replace")
    suffix = Path(rel).suffix.casefold()
    base["content_analyzed"] = True
    base["summary"] = first_summary(text, suffix)
    base["technical_terms"] = exact_tokens(text)
    base["intent_matches"] = sorted(set(base["technical_terms"]) & intent_tokens)[:128]
    base["effects"] = sorted({m.group(1).casefold() for m in EFFECT_RE.finditer(text)})
    base["authority_terms"] = sorted({m.group(1).upper() for m in AUTHORITY_RE.finditer(text)})
    base["state_terms"] = sorted({m.group(1).casefold() for m in STATE_RE.finditer(text)})
    base["risk_terms"] = sorted({m.group(1).casefold() for m in RISK_RE.finditer(text)})
    base["relative_refs"] = sorted(set(re.findall(
        r"(?:from\s+|require\s*\(\s*|(?:path|file|source|ref)\s*[=:]\s*)['\"]([^'\"]+)['\"]", text,
        flags=re.IGNORECASE,
    )))[:256]
    base["schema_ids"] = sorted(set(re.findall(
        r"(?:schema_version|schema_id|\$id)\s*[=:]\s*['\"]([^'\"]+)['\"]", text,
        flags=re.IGNORECASE,
    )))[:128]
    base["config_keys"] = sorted(set(re.findall(
        r"(?m)^\s*([A-Z][A-Z0-9_]{2,63})\s*[=:]", text,
    )))[:256]
    if suffix == ".py":
        base.update(python_features(text))
    elif suffix in {".js", ".jsx", ".mjs", ".ts", ".tsx"}:
        base["imports"] = sorted(set(re.findall(
            r"(?:from\s+|require\s*\(\s*)['\"]([^'\"]+)['\"]", text
        )))[:256]
        base["declares"] = sorted(set(re.findall(
            r"\b(?:function|class|const|let|var)\s+([A-Za-z_$][\w$]*)", text
        )))[:512]
        base["calls"] = sorted(set(re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", text)))[:512]
        base["routes"] = sorted(set(re.findall(r"['\"](/[^'\"\s]{1,160})['\"]", text)))[:128]
        base["parse_state"] = "BOUNDED_JAVASCRIPT_CONTRACT_EXTRACTION"
    else:
        base["declares"] = sorted(set(re.findall(
            r"(?m)^\s*(?:def|class|function|service|schema|interface|type)\s+([A-Za-z_][\w.-]*)", text,
            flags=re.IGNORECASE,
        )))[:512]
        base["parse_state"] = "BOUNDED_TEXT_CONTRACT_EXTRACTION"
    provides = set(base["declares"]) | set(base["routes"]) | set(base["schema_ids"])
    if base["summary"]:
        provides.add(base["summary"])
    requires = set(base["imports"]) | set(base["relative_refs"])
    base["provides"] = sorted(provides)[:512]
    base["requires"] = sorted(requires)[:512]
    return base


def logical_name(rel: str, features: dict[str, Any]) -> dict[str, str]:
    observed = PurePosixPath(rel).name
    suffix = Path(rel).suffix
    stem_tokens = set(exact_tokens(Path(rel).stem))
    candidates = features.get("declares", []) or features.get("schema_ids", []) or features.get("routes", [])
    primary = candidates[0] if candidates else features.get("summary")
    if not primary:
        return {"value": observed, "basis": "OBSERVED_NAME_NO_CONTENT_CAPABILITY"}
    primary_tokens = set(exact_tokens(str(primary)))
    if stem_tokens & primary_tokens:
        return {"value": observed, "basis": "OBSERVED_NAME_ALIGNS_WITH_CONTENT_CAPABILITY"}
    return {"value": f"{safe_name(str(primary))}{suffix}", "basis": "RECONSTRUCTED_FROM_PRIMARY_CONTENT_CAPABILITY"}


def enumerate_source(repo: Path, output_dir: Path, intent_tokens: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    opaque_index = 0

    def onerror(exc: OSError) -> None:
        gaps.append({"type": "DIRECTORY_ENUMERATION_UNRESOLVED", "error": type(exc).__name__})

    for root, dirs, files in os.walk(repo, followlinks=False, onerror=onerror):
        root_path = Path(root)
        next_dirs: list[str] = []
        for name in sorted(dirs):
            path = root_path / name
            rel = path.relative_to(repo).as_posix()
            if path.is_symlink():
                records.append({
                    "node_id": f"file://{rel}", "path": rel, "kind": "SYMLINK_NO_FOLLOW",
                    "content_sha256": None, "size": None, "mtime_utc": None,
                    "features": {"content_analyzed": False}, "evidence_class": "OBSERVED_METADATA",
                })
            elif is_protected(rel):
                opaque_index += 1
                records.append({
                    "node_id": f"protected://P{opaque_index:06d}", "path": None,
                    "kind": "PROTECTED_OPAQUE_NODE", "content_sha256": None, "size": None,
                    "mtime_utc": None, "features": {"content_analyzed": False},
                    "evidence_class": "PROTECTED_OPAQUE",
                })
            elif is_structural_dir(name):
                records.append({
                    "node_id": f"structural://{rel}", "path": rel,
                    "kind": "STRUCTURAL_DIRECTORY_NO_DESCENT", "content_sha256": None,
                    "size": None, "mtime_utc": None, "features": {"content_analyzed": False},
                    "evidence_class": "OBSERVED_STRUCTURAL_BOUNDARY",
                })
            else:
                try:
                    if path.resolve() == output_dir or output_dir in path.resolve().parents:
                        continue
                except OSError:
                    pass
                next_dirs.append(name)
        dirs[:] = next_dirs
        public_key_stems = {name[:-4] for name in files if name.endswith(".pub")}
        for name in sorted(files):
            path = root_path / name
            rel = path.relative_to(repo).as_posix()
            try:
                resolved = path.resolve()
                if resolved == output_dir or output_dir in resolved.parents:
                    continue
            except OSError:
                pass
            if path.is_symlink():
                records.append({
                    "node_id": f"file://{rel}", "path": rel, "kind": "SYMLINK_NO_FOLLOW",
                    "content_sha256": None, "size": None, "mtime_utc": None,
                    "features": {"content_analyzed": False}, "evidence_class": "OBSERVED_METADATA",
                })
                continue
            if is_protected(rel) or name in public_key_stems:
                opaque_index += 1
                records.append({
                    "node_id": f"protected://P{opaque_index:06d}", "path": None,
                    "kind": "PROTECTED_OPAQUE_NODE", "content_sha256": None, "size": None,
                    "mtime_utc": None, "features": {"content_analyzed": False},
                    "evidence_class": "PROTECTED_OPAQUE",
                })
                continue
            try:
                before = path.stat()
                data = path.read_bytes()
                after = path.stat()
            except OSError as exc:
                gaps.append({"type": "FILE_READ_UNRESOLVED", "path": rel, "error": type(exc).__name__})
                records.append({
                    "node_id": f"file://{rel}", "path": rel, "kind": "FILE_STATE",
                    "content_sha256": None, "size": None, "mtime_utc": None,
                    "features": {"content_analyzed": False}, "evidence_class": "UNKNOWN",
                })
                continue
            stable = (
                before.st_dev == after.st_dev and before.st_ino == after.st_ino
                and before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns
            )
            features = extract_features(rel, data, intent_tokens) if stable else {"content_analyzed": False}
            if stable:
                features["role"] = infer_role(rel, Path(rel).suffix.casefold(), features)
                features["logical_name"] = logical_name(rel, features)
            records.append({
                "node_id": f"file://{rel}", "path": rel, "kind": "FILE_STATE",
                "content_sha256": sha256_bytes(data) if stable else None,
                "size": after.st_size,
                "mtime_utc": datetime.fromtimestamp(after.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
                "features": features,
                "evidence_class": "OBSERVED_CONTENT_CONTRACT" if stable else "UNKNOWN_UNSTABLE_DURING_FREEZE",
            })
    return records, gaps


def module_aliases(rel: str) -> set[str]:
    pure = PurePosixPath(rel)
    aliases = {pure.stem, rel, pure.name}
    if pure.suffix == ".py":
        dotted = ".".join(pure.with_suffix("").parts)
        aliases.add(dotted)
        if pure.name == "__init__.py":
            aliases.add(".".join(pure.parent.parts))
    return {value for value in aliases if value}


def plan_relations(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active = [r for r in records if r.get("kind") == "FILE_STATE" and r.get("path") and r.get("features", {}).get("content_analyzed")]
    alias_index: dict[str, set[str]] = defaultdict(set)
    provide_index: dict[str, set[str]] = defaultdict(set)
    path_index = {r["path"]: r["node_id"] for r in active}
    for record in active:
        for alias in module_aliases(record["path"]):
            alias_index[alias.casefold()].add(record["node_id"])
        for capability in record["features"].get("provides", []):
            provide_index[str(capability).casefold()].add(record["node_id"])
    pairs: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for record in active:
        source = record["node_id"]
        features = record["features"]
        for requirement in features.get("imports", []):
            folded = requirement.lstrip(".").casefold()
            candidates = set(alias_index.get(folded, set())) | set(alias_index.get(folded.rsplit(".", 1)[-1], set()))
            for target in sorted(candidates - {source}):
                key = (source, target, "EXPLICIT_IMPORT", requirement)
                pairs[key] = {"source_id": source, "target_id": target, "basis": "EXPLICIT_IMPORT", "demand": requirement, "supply": requirement}
        for ref in features.get("relative_refs", []):
            candidate = (PurePosixPath(record["path"]).parent / ref).as_posix()
            candidate = str(PurePosixPath(candidate))
            target = path_index.get(candidate)
            if target and target != source:
                key = (source, target, "EXPLICIT_FILE_REFERENCE", ref)
                pairs[key] = {"source_id": source, "target_id": target, "basis": "EXPLICIT_FILE_REFERENCE", "demand": ref, "supply": candidate}
        for call in features.get("calls", []):
            targets = provide_index.get(str(call).casefold(), set()) - {source}
            if len(targets) == 1:
                target = next(iter(targets))
                key = (source, target, "SYMBOL_SUPPLY_DEMAND", call)
                pairs[key] = {"source_id": source, "target_id": target, "basis": "SYMBOL_SUPPLY_DEMAND", "demand": call, "supply": call}
    return [pairs[key] for key in sorted(pairs)]


def node_projection(record: dict[str, Any], root_id: str) -> dict[str, Any]:
    features = record.get("features", {})
    path = record.get("path")
    return {
        "node_id": record["node_id"], "node_kind": record["kind"],
        "observed_path": path,
        "reconstructed_logical_name": features.get("logical_name", {"value": None, "basis": "NOT_ANALYZED"}),
        "intended_role": features.get("role", "UNKNOWN"),
        "provides": features.get("provides", []), "requires": features.get("requires", []),
        "inputs": features.get("inputs", []), "outputs": features.get("outputs", []),
        "upstream": [], "downstream": [],
        "D1_INTENT": {"field_root": root_id, "intent_matches": features.get("intent_matches", []), "product_role": features.get("role", "UNKNOWN")},
        "D2_STATE": {"state": "OBSERVED_CURRENT_SOURCE", "state_terms": features.get("state_terms", [])},
        "D3_COORDINATE": {"path": path, "namespace": "CURRENT_SOURCE", "mtime_utc": record.get("mtime_utc")},
        "D4_EVIDENCE": {"content_sha256": record.get("content_sha256"), "class": record.get("evidence_class"), "parse_state": features.get("parse_state")},
        "D5_EXECUTION": {"role": features.get("role", "UNKNOWN"), "effects": features.get("effects", []), "provides": features.get("provides", []), "requires": features.get("requires", [])},
        "D6_TECHNICAL_DEFINITION": {"terms": features.get("technical_terms", []), "schemas": features.get("schema_ids", []), "generative_transmission_claimed": False},
        "D7_HARD_RISK": {"signals": features.get("risk_terms", []), "protected_content_read": False},
        "D8_ENVELOPE": {"authority_terms": features.get("authority_terms", []), "authority": "CANDIDATE_ONLY", "total_field_decision": "NOT_RUN"},
        "ADI": {
            "state_coordinate": "OBSERVED_CURRENT_SOURCE",
            "capability_coordinate": features.get("provides", []),
            "decision_coordinate": features.get("authority_terms", []),
            "transition_coordinate": features.get("state_terms", []),
            "spatiotemporal_coordinate": {"path": path, "mtime_utc": record.get("mtime_utc")},
            "evidence_coordinate": {"sha256": record.get("content_sha256"), "class": record.get("evidence_class")},
            "reconstruction_coordinate": {"logical_name": features.get("logical_name"), "role": features.get("role"), "requires": features.get("requires", [])},
        },
    }


def edge_base(kind: str, source: dict[str, Any], target: dict[str, Any], *, basis: str, demand: Any = None, supply: Any = None) -> dict[str, Any]:
    sf = source.get("features", {})
    tf = target.get("features", {})
    explicit = basis in {"EXPLICIT_IMPORT", "EXPLICIT_FILE_REFERENCE", "SYMBOL_SUPPLY_DEMAND"}
    return {
        "source_id": source["node_id"], "target_id": target["node_id"],
        "comparison_kind": kind, "basis": basis,
        "actor": source.get("path") or source["node_id"],
        "precondition": {"demand": demand if demand is not None else sf.get("requires", [])},
        "trigger": {"intent_matches": sf.get("intent_matches", [])},
        "action": sf.get("effects", []) or "ANALYZE_OR_PROVIDE_CAPABILITY",
        "mechanism": {"explicit_reference": explicit, "supply": supply, "source_role": sf.get("role")},
        "effect": {"target_role": tf.get("role"), "outputs": sf.get("outputs", []), "product_effect": "INTENT_FIELD_CAPABILITY_CONTRIBUTION"},
        "dependency_type": basis if explicit else "INTENT_FIELD_PROJECTION",
        "relation_type": "SUPPLIES_DEMAND" if explicit else kind,
        "term_coordinate": sorted(set(sf.get("technical_terms", [])) & set(tf.get("technical_terms", [])))[:64],
        "necessity_sufficiency_evidence": {
            "necessity": "EXPLICIT_CONTENT_CONTRACT" if explicit else "CANDIDATE_FIELD_PROJECTION",
            "sufficiency": "REQUIRES_TOTAL_FIELD_ACCEPTANCE",
        },
        "failure_effect": "DEPENDENT_CAPABILITY_OR_PRODUCT_EFFECT_MAY_NOT_CLOSE" if explicit else "UNKNOWN",
        "reconstruction_conditions": {
            "source_content_sha256": source.get("content_sha256"),
            "target_content_sha256": target.get("content_sha256"),
            "basis": basis,
        },
        "evidence_reference": {
            "source_sha256": source.get("content_sha256"),
            "target_sha256": target.get("content_sha256"),
            "source_path": source.get("path"), "target_path": target.get("path"),
        },
        "evidence_class": "RECONSTRUCTED" if explicit else "INFERRED",
        "causal_status": "RECONSTRUCTED_EXPLICIT_SUPPLY_DEMAND" if explicit else "FIELD_PROJECTION_CANDIDATE",
        "authority_state": "CANDIDATE_NOT_CANONICAL",
        "D1_D8": {
            "D1": sf.get("intent_matches", []), "D2": sf.get("state_terms", []),
            "D3": source.get("path"), "D4": source.get("content_sha256"),
            "D5": {"provides": sf.get("provides", []), "requires": sf.get("requires", [])},
            "D6": {"terms": sf.get("technical_terms", []), "schemas": sf.get("schema_ids", [])},
            "D7": sf.get("risk_terms", []), "D8": {"authority": "CANDIDATE_ONLY", "total_field": "NOT_RUN"},
        },
        "ADI": {
            "state": sf.get("state_terms", []), "capability": sf.get("provides", []),
            "decision": sf.get("authority_terms", []), "transition": sf.get("state_terms", []),
            "spatiotemporal": {"source": source.get("path"), "target": target.get("path")},
            "evidence": {"source": source.get("content_sha256"), "target": target.get("content_sha256")},
            "reconstruction": {"basis": basis, "demand": demand, "supply": supply},
        },
    }


def comparator_rows(name: str, snapshot: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    index = {record["node_id"]: record for record in snapshot["records"]}
    root = index[snapshot["intent_field_root_id"]]
    files = [record for record in snapshot["records"] if record.get("kind") == "FILE_STATE" and record.get("features", {}).get("content_analyzed")]
    rows: list[dict[str, Any]] = []
    if name in {"DEPENDENCY", "RELATION"}:
        for pair in plan["pairs"]:
            source = index[pair["source_id"]]
            target = index[pair["target_id"]]
            rows.append(edge_base(name, source, target, basis=pair["basis"], demand=pair.get("demand"), supply=pair.get("supply")))
        return rows
    for record in files:
        features = record["features"]
        include = {
            "DEMAND": bool(features.get("requires") or features.get("inputs") or features.get("intent_matches")),
            "SUPPLY": bool(features.get("provides") or features.get("outputs")),
            "EFFECT": bool(features.get("effects") or features.get("role")),
            "TERM": bool(features.get("technical_terms") or features.get("schema_ids")),
            "STATE_TRANSITION": bool(features.get("state_terms")),
            "EVIDENCE": bool(record.get("content_sha256")),
            "AUTHORITY": bool(features.get("authority_terms")),
            "RECONSTRUCTION": bool(features.get("logical_name") or features.get("role")),
            "RISK": bool(features.get("risk_terms")),
        }.get(name, False)
        if not include:
            continue
        source, target = (root, record) if name == "DEMAND" else (record, root)
        rows.append(edge_base(
            name, source, target, basis="INTENT_FIELD_PROJECTION",
            demand=features.get("requires", []), supply=features.get("provides", []),
        ))
    return rows


def run_comparator(name: str, snapshot_path: Path, plan_path: Path, output_path: Path) -> int:
    snapshot_bytes = snapshot_path.read_bytes()
    plan_bytes = plan_path.read_bytes()
    snapshot = json.loads(snapshot_bytes)
    plan = json.loads(plan_bytes)
    if snapshot["snapshot_id"] != plan["snapshot_id"]:
        raise ValueError("snapshot and plan identity mismatch")
    rows = comparator_rows(name, snapshot, plan)
    snapshot_sha = sha256_bytes(snapshot_bytes)
    plan_sha = sha256_bytes(plan_bytes)
    invocation_id = str(uuid.uuid4())
    for row in rows:
        row["snapshot_sha256"] = snapshot_sha
        row["pair_plan_sha256"] = plan_sha
        row["comparator_process_id"] = os.getpid()
        row["comparator_invocation_id"] = invocation_id
    write_jsonl(output_path, rows)
    print(json.dumps({
        "state": STATE, "name": name, "process_id": os.getpid(),
        "invocation_id": invocation_id, "row_count": len(rows),
        "snapshot_sha256": snapshot_sha, "pair_plan_sha256": plan_sha,
    }, sort_keys=True))
    return 0


def validate_outputs(rows: list[dict[str, Any]], node_ids: set[str], snapshot_sha: str, plan_sha: str) -> dict[str, Any]:
    required = {
        "source_id", "target_id", "comparison_kind", "actor", "precondition", "trigger",
        "action", "mechanism", "effect", "dependency_type", "relation_type",
        "term_coordinate", "necessity_sufficiency_evidence", "failure_effect",
        "reconstruction_conditions", "evidence_reference", "evidence_class",
        "causal_status", "authority_state", "D1_D8", "ADI", "snapshot_sha256",
        "pair_plan_sha256", "comparator_process_id", "comparator_invocation_id",
    }
    findings = []
    for index, row in enumerate(rows):
        missing = sorted(required - set(row))
        if missing:
            findings.append({"row": index, "finding": "EDGE_FIELDS_MISSING", "fields": missing})
        if row.get("source_id") not in node_ids or row.get("target_id") not in node_ids:
            findings.append({"row": index, "finding": "EDGE_ENDPOINT_MISSING"})
        if row.get("snapshot_sha256") != snapshot_sha or row.get("pair_plan_sha256") != plan_sha:
            findings.append({"row": index, "finding": "COMPARATOR_HASH_BINDING_MISMATCH"})
    return {"state": "CANDIDATE_CHECK_COMPLETE" if not findings else "HOLD", "finding_count": len(findings), "findings": findings}


def technology_identity_evidence_view(
    rows: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    snapshot_sha: str,
    plan_sha: str,
) -> dict[str, Any]:
    """Export gate inputs without turning repository evidence into an identity decision."""
    explicit_rows = [
        row for row in rows
        if row.get("causal_status") == "RECONSTRUCTED_EXPLICIT_SUPPLY_DEMAND"
    ]

    def axis(status: str, level: str, row_count: int, note: str) -> dict[str, Any]:
        return {
            "status": status,
            "evidence_level": level,
            "evidence_references": {
                "snapshot_sha256": snapshot_sha,
                "pair_plan_sha256": plan_sha,
                "causal_field": "90_8D_ADI_SUPPLY_DEMAND_CAUSAL_FIELD.jsonl",
                "row_count": row_count,
            },
            "note": note,
        }

    implementation_level = "EV4_IMPLEMENTATION_EVIDENCE" if rows else "EV0_UNSUPPORTED"
    causal_level = "EV4_IMPLEMENTATION_EVIDENCE" if explicit_rows else "EV0_UNSUPPORTED"
    dependency_level = "EV4_IMPLEMENTATION_EVIDENCE" if pairs else "EV0_UNSUPPORTED"
    axes = {
        "MECHANISM": axis(
            "EVIDENCE_AVAILABLE" if rows else "UNKNOWN",
            implementation_level,
            len(rows),
            "Bounded implementation mechanisms are available; cross-technology sameness is not decided here.",
        ),
        "CAUSAL_PATH": axis(
            "EVIDENCE_AVAILABLE" if explicit_rows else "UNKNOWN",
            causal_level,
            len(explicit_rows),
            "Only explicit reconstructed supply-demand chains are supplied as candidate causal evidence.",
        ),
        "DEPENDENCIES": axis(
            "EVIDENCE_AVAILABLE" if pairs else "UNKNOWN",
            dependency_level,
            len(pairs),
            "Dependencies come from the frozen explicit pair plan.",
        ),
        "ELIMINATED_OPERATIONS": axis(
            "UNKNOWN", "EV0_UNSUPPORTED", 0,
            "A comparison baseline and reproducible elimination evidence are required.",
        ),
        "COST_TOPOLOGY": axis(
            "UNKNOWN", "EV0_UNSUPPORTED", 0,
            "No cost or complexity topology is inferred from file structure.",
        ),
        "CARRIER_RECONSTRUCTION_VERIFICATION": axis(
            "UNKNOWN", "EV0_UNSUPPORTED", 0,
            "Carrier, reconstruction, and verification require separate declared evidence.",
        ),
    }
    if tuple(axes) != TECHNOLOGY_IDENTITY_AXES:
        raise AssertionError("technology identity axes drifted")
    return {
        "schema_version": "w7tp-technology-identity-evidence/1.0",
        "state": STATE,
        "purpose": "GATE_INPUT_ONLY",
        "gate_skill_ref": "w7tp.technology-identity-audit@1.0.0",
        "candidate_decision": "INSUFFICIENT_EVIDENCE",
        "decision_authority": "SEPARATE_TECHNOLOGY_IDENTITY_GATE",
        "axes": axes,
        "effect_equivalence_not_technical_equivalence": True,
        "weighted_score_used": False,
        "patent_or_legal_conclusion": "NOT_DETERMINED",
    }


def build(repo: Path, output_dir: Path, node_ref: str, founder_intent: str, product_effect: str) -> dict[str, Any]:
    repo = repo.resolve(strict=True)
    output_dir = output_dir.resolve()
    if not repo.is_dir():
        raise ValueError("repo must be a directory")
    if output_dir.exists():
        raise ValueError("output-dir must be a new candidate coordinate")
    if not SAFE_REF_RE.fullmatch(node_ref):
        raise ValueError("node-ref must be opaque and use safe characters")
    founder_intent = founder_intent.strip()
    if not founder_intent:
        raise ValueError("founder-intent is required to form the 8D field root")
    output_dir.mkdir(parents=True, exist_ok=False)
    intent_packet = {
        "node_id": "intent://founder/current", "kind": "INTENT_FIELD_ROOT", "path": None,
        "content_sha256": sha256_bytes(founder_intent.encode()), "size": len(founder_intent.encode()),
        "mtime_utc": None, "evidence_class": "FOUNDER_SUPPLIED_INTENT",
        "features": {
            "content_analyzed": True, "summary": founder_intent[:240],
            "intent_matches": exact_tokens(founder_intent), "technical_terms": exact_tokens(founder_intent),
            "provides": ["FOUNDER_INTENT_AUTHORITY"], "requires": [product_effect or "SYSTEM_DESIGN_RECONSTRUCTION"],
            "inputs": ["FOUNDER_INTENT"], "outputs": [product_effect or "8D_ADI_SYSTEM_DESIGN_FIELD"],
            "effects": ["reconstruct"], "authority_terms": ["FOUNDER"], "state_terms": ["current"],
            "risk_terms": [], "schema_ids": [], "role": "INTENT_FIELD_ROOT",
            "logical_name": {"value": "FOUNDER_INTENT_FIELD", "basis": "FOUNDER_SUPPLIED"},
        },
    }
    intent_tokens = set(exact_tokens(founder_intent + " " + product_effect))
    records, gaps = enumerate_source(repo, output_dir, intent_tokens)
    records.sort(key=lambda item: item["node_id"])
    all_records = [intent_packet, *records]
    snapshot_core = {
        "schema_version": SCHEMA_VERSION, "state": STATE, "node_ref": node_ref,
        "intent_field_root_id": intent_packet["node_id"],
        "founder_intent_sha256": intent_packet["content_sha256"],
        "product_effect": product_effect or "8D_ADI_SYSTEM_DESIGN_FIELD",
        "source_enumeration_count": 1,
        "content_semantics": "BOUNDED_SOURCE_CONTENT_CONTRACT_ANALYSIS",
        "git_required": False, "git_consulted": False,
        "records": all_records, "coverage_gaps": gaps,
    }
    snapshot_id = sha256_bytes(canonical_bytes(snapshot_core))
    snapshot = {**snapshot_core, "snapshot_id": snapshot_id}
    pairs = plan_relations(records)
    plan = {
        "schema_version": SCHEMA_VERSION, "state": STATE, "snapshot_id": snapshot_id,
        "planner": "EXPLICIT_CONTENT_SUPPLY_DEMAND_ONLY", "source_rescan_count": 0,
        "pair_count": len(pairs), "pairs": pairs,
    }
    nodes = [node_projection(record, intent_packet["node_id"]) for record in records]
    node_map = {node["node_id"]: node for node in nodes}
    for pair in pairs:
        source_node = node_map.get(pair["source_id"])
        target_node = node_map.get(pair["target_id"])
        if source_node is not None:
            source_node["downstream"].append({
                "node_id": pair["target_id"], "basis": pair["basis"],
                "demand": pair.get("demand"), "supply": pair.get("supply"),
            })
        if target_node is not None:
            target_node["upstream"].append({
                "node_id": pair["source_id"], "basis": pair["basis"],
                "demand": pair.get("demand"), "supply": pair.get("supply"),
            })
    write_json(output_dir / "00_INTENT_FIELD_ROOT.json", intent_packet)
    write_json(output_dir / "01_FROZEN_CONTENT_INDEX.json", snapshot)
    write_jsonl(output_dir / "02_FILE_8D_ADI_STATE_NODES.jsonl", nodes)
    write_json(output_dir / "03_SUPPLY_DEMAND_PAIR_PLAN.json", plan)
    print(f"[8D] source frozen once: files={len(records)} explicit_pairs={len(pairs)}", file=sys.stderr, flush=True)
    snapshot_path = output_dir / "01_FROZEN_CONTENT_INDEX.json"
    plan_path = output_dir / "03_SUPPLY_DEMAND_PAIR_PLAN.json"
    snapshot_sha = sha256_bytes(snapshot_path.read_bytes())
    plan_sha = sha256_bytes(plan_path.read_bytes())
    rows: list[dict[str, Any]] = []
    runs = []
    for name in COMPARATOR_NAMES:
        comparator_path = output_dir / "comparators" / f"{name.casefold()}.jsonl"
        proc = subprocess.run([
            sys.executable, str(Path(__file__).resolve()), "--run-comparator", name,
            "--snapshot", str(snapshot_path), "--pair-plan", str(plan_path),
            "--comparator-output", str(comparator_path),
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode:
            raise RuntimeError(f"comparator {name} failed")
        comparator_rows_value = [json.loads(line) for line in comparator_path.read_text(encoding="utf-8").splitlines() if line]
        rows.extend(comparator_rows_value)
        child = json.loads(proc.stdout.decode().splitlines()[-1])
        runs.append(child)
        print(f"[8D] {name}: {len(comparator_rows_value)}", file=sys.stderr, flush=True)
    write_jsonl(output_dir / "90_8D_ADI_SUPPLY_DEMAND_CAUSAL_FIELD.jsonl", rows)
    node_ids = {record["node_id"] for record in all_records}
    validation = validate_outputs(rows, node_ids, snapshot_sha, plan_sha)
    reconstructed = len(pairs)
    unknowns = [
        {"node_id": record["node_id"], "finding": "CONTENT_OR_ROLE_UNRESOLVED"}
        for record in records
        if not record.get("features", {}).get("content_analyzed") or not record.get("features", {}).get("role")
    ]
    write_json(output_dir / "91_CONFLICTS_AND_UNKNOWNS.json", {
        "state": STATE, "coverage_gaps": gaps, "unknowns": unknowns,
    })
    technology_identity_evidence = technology_identity_evidence_view(
        rows, pairs, snapshot_sha, plan_sha,
    )
    write_json(
        output_dir / "92_TECHNOLOGY_IDENTITY_EVIDENCE_CANDIDATE.json",
        technology_identity_evidence,
    )
    red_team = {
        "state": STATE,
        "RED_TEAM_PRE_DEFINITION": validation["state"],
        "RED_TEAM_PRE_ACTIVATION": "NOT_APPLICABLE_WITH_EVIDENCE",
        "RED_TEAM_POST_OPERATION": "NOT_APPLICABLE_READ_ONLY_CANDIDATE",
        "checks_order": "PRODUCT_AND_8D_FIELD_FIRST_SECURITY_LAST",
        "validation": validation,
        "true_hard_risks": [],
    }
    write_json(output_dir / "93_RED_TEAM_EXECUTION_EVIDENCE.json", red_team)
    manifest_entries = []
    for path in sorted(p for p in output_dir.rglob("*") if p.is_file() and p.name != "99_SHA256_MANIFEST.json"):
        manifest_entries.append({"path": path.relative_to(output_dir).as_posix(), "sha256": sha256_bytes(path.read_bytes())})
    receipt = {
        "schema_version": SCHEMA_VERSION, "state": STATE, "run_id": output_dir.name,
        "snapshot_id": snapshot_id, "source_enumeration_count": 1,
        "source_file_count": len(records), "file_state_node_count": len(nodes),
        "explicit_supply_demand_pair_count": len(pairs),
        "reconstructed_causal_chain_count": reconstructed,
        "verified_causal_chain_count": 0,
        "causal_status": "RECONSTRUCTED_CANDIDATE_FIELD" if reconstructed else "INTENT_FIELD_MAPPED_NO_EXPLICIT_CROSS_FILE_CHAIN",
        "content_semantics": "BOUNDED_SOURCE_CONTENT_CONTRACT_ANALYSIS",
        "git_required": False, "git_consulted": False,
        "source_coverage_status": "PARTIAL_WITH_EXPLICIT_GAPS" if gaps else "COMPLETE_FOR_ENUMERATED_NONPROTECTED_PATHS",
        "unknown_count": len(unknowns),
        "protected_opaque_count": sum(1 for record in records if record["kind"] == "PROTECTED_OPAQUE_NODE"),
        "comparator_runs": runs, "snapshot_sha256": snapshot_sha, "pair_plan_sha256": plan_sha,
        "edge_contract_validation": validation["state"],
        "technology_identity_evidence_status": "GATE_INPUT_ONLY",
        "technology_identity_gate_decision": "NOT_RUN",
        "weighted_technology_identity_score_used": False,
        "patent_or_legal_conclusion": "NOT_DETERMINED",
        "original_files_modified": False, "canonical_promotion": False,
        "total_field_decision": "NOT_RUN", "files": manifest_entries,
    }
    write_json(output_dir / "99_SHA256_MANIFEST.json", receipt)
    return receipt


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="trace-8d-adi-v3-") as tmp:
        repo = Path(tmp) / "repo"
        out = Path(tmp) / "out"
        repo.mkdir()
        (repo / "order_service.py").write_text(
            '"""Accept an order and return a validated receipt."""\n'
            "from receipt_builder import build_receipt\n\n"
            "def accept_order(order):\n    return build_receipt(order)\n",
            encoding="utf-8",
        )
        (repo / "receipt_builder.py").write_text(
            '"""Build the customer-visible receipt."""\n'
            "def build_receipt(order):\n    return {'state': 'candidate', 'order': order}\n",
            encoding="utf-8",
        )
        (repo / ".env").write_text("TOKEN=do-not-read\n", encoding="utf-8")
        receipt = build(
            repo, out, "node://self-test",
            "依顧客訂單建立服務意圖場，從接單到收據形成供需閉環",
            "顧客取得可驗證收據",
        )
        if receipt["git_required"] or receipt["git_consulted"]:
            raise AssertionError("Git entered the intent-field authority path")
        if receipt["reconstructed_causal_chain_count"] < 1:
            raise AssertionError("explicit supply-demand chain was not reconstructed")
        nodes = [json.loads(line) for line in (out / "02_FILE_8D_ADI_STATE_NODES.jsonl").read_text().splitlines() if line]
        if not any(node["provides"] for node in nodes):
            raise AssertionError("content capabilities were not extracted")
        combined = b"".join(path.read_bytes() for path in out.rglob("*") if path.is_file())
        if b"do-not-read" in combined:
            raise AssertionError("protected content leaked")
        if receipt["state"] != STATE or receipt["original_files_modified"]:
            raise AssertionError("candidate-only boundary changed")
        identity_evidence = json.loads(
            (out / "92_TECHNOLOGY_IDENTITY_EVIDENCE_CANDIDATE.json").read_text()
        )
        if set(identity_evidence["axes"]) != set(TECHNOLOGY_IDENTITY_AXES):
            raise AssertionError("six-axis technology identity evidence is incomplete")
        if identity_evidence["candidate_decision"] != "INSUFFICIENT_EVIDENCE":
            raise AssertionError("evidence exporter made a technology identity decision")
        if identity_evidence["weighted_score_used"]:
            raise AssertionError("weighted technology identity score was introduced")
    print(json.dumps({"STATE": "SELF_TEST_COMPLETE", "RESULT": "INTENT_FIELD_SUPPLY_DEMAND_RECONSTRUCTED"}, sort_keys=True))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--node-ref", default="node://local")
    parser.add_argument("--founder-intent", default="")
    parser.add_argument("--product-effect", default="")
    parser.add_argument("--run-comparator", choices=COMPARATOR_NAMES)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--pair-plan", type=Path)
    parser.add_argument("--comparator-output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.run_comparator and not (args.snapshot and args.pair_plan and args.comparator_output):
        parser.error("--run-comparator requires --snapshot, --pair-plan, and --comparator-output")
    if not args.self_test and not args.run_comparator and (args.repo is None or args.output_dir is None or not args.founder_intent.strip()):
        parser.error("--repo, --output-dir, and --founder-intent are required")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        return self_test()
    if args.run_comparator:
        return run_comparator(args.run_comparator, args.snapshot, args.pair_plan, args.comparator_output)
    receipt = build(args.repo, args.output_dir, args.node_ref, args.founder_intent, args.product_effect)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
