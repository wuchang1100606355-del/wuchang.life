#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / ".skill-build" / "total-field-intent-state-cell-gst"
GST = SKILL / "vendor" / "origin_cell_v2" / "w7tp_origin_cell_generative_v2.py"
GST_MANIFEST = SKILL / "vendor" / "origin_cell_v2" / "w7tp_origin_cell_generative_v2_manifest.json"

EXPECTED_GST_SHA256 = "5902d92fd5132bc916df9296696ee79f07b1c7ec2f7f8645f85ebc8ad296a254"

REQUIRED_PATHS = [
    ROOT / ".skill-build" / "intent-field-generative-construction" / "SKILL.md",
    ROOT / "tools" / "total_field_dynamic_context.py",
    ROOT / "services" / "gateway" / "total_field_cloud_candidate_contract.py",
    ROOT / "tools" / "total_field" / "formal_review_entry_candidate.py",
    GST,
    GST_MANIFEST,
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def fail(reason: str) -> None:
    print("STATE=HOLD_TOTAL_FIELD_GST_SKILL_BINDING")
    print(f"REASON={reason}")
    raise SystemExit(2)

for path in REQUIRED_PATHS:
    if not path.is_file():
        fail(f"MISSING_PATH:{path}")

if sha256(GST) != EXPECTED_GST_SHA256:
    fail("TRUE_GST_SHA256_MISMATCH")

try:
    manifest = json.loads(GST_MANIFEST.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError):
    fail("TRUE_GST_MANIFEST_INVALID")

successor = manifest.get("successor", {})
mainline = manifest.get("mainline_candidate", {})
authority = manifest.get("authority", {})
if successor.get("d6_mode") != "SOURCE_GENERATED_RULE_BODY":
    fail("TRUE_GST_D6_MODE_DRIFT")
if mainline.get("target_bytes_embedded") is not False:
    fail("TRUE_GST_TARGET_BYTES_CONTAMINATION")
if mainline.get("differential_payload_allowed") is not False:
    fail("TRUE_GST_DIFFERENTIAL_CONTAMINATION")
if mainline.get("patch_cell_allowed") is not False:
    fail("TRUE_GST_PATCH_CELL_CONTAMINATION")
if authority.get("candidate_only") is not True or authority.get("canonical") is not False:
    fail("TRUE_GST_AUTHORITY_BOUNDARY_DRIFT")

text = GST.read_text(encoding="utf-8")
for forbidden in ("build_delta(", "apply_delta(", "W7TP_GENERATIVE_DELTA", '"generator_base_required": True'):
    if forbidden in text:
        fail(f"FORBIDDEN_ACTIVE_GST_SEMANTIC:{forbidden}")

try:
    tree = ast.parse(text, filename=str(GST))
except SyntaxError:
    fail("TRUE_GST_SOURCE_PARSE_FAILED")
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        names = {alias.name.split(".")[0] for alias in node.names}
        if names.intersection({"gzip", "zlib", "bz2", "lzma", "zipfile", "tarfile"}):
            fail("TRUE_GST_COMPRESSION_IMPORT_FORBIDDEN")
    elif isinstance(node, ast.ImportFrom):
        module = (node.module or "").split(".")[0]
        if module in {"gzip", "zlib", "bz2", "lzma", "zipfile", "tarfile"}:
            fail("TRUE_GST_COMPRESSION_IMPORT_FORBIDDEN")
    elif isinstance(node, ast.Call):
        func = node.func
        name = func.id if isinstance(func, ast.Name) else (
            func.attr if isinstance(func, ast.Attribute) else ""
        )
        if name in {"compress", "decompress", "build_delta", "apply_delta"}:
            fail(f"TRUE_GST_FORBIDDEN_CALL:{name}")

spec = importlib.util.spec_from_file_location("gst_skill_vendor", GST)
if spec is None or spec.loader is None:
    fail("TRUE_GST_IMPORT_SPEC_FAILED")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

required_symbols = (
    "analyze_source_and_generate_rules",
    "build_rule_packet",
    "execute_reconstruction_rules",
    "reconstruct_from_rule_packet",
)
for symbol in required_symbols:
    if not callable(getattr(module, symbol, None)):
        fail(f"MISSING_SYMBOL:{symbol}")

dc = (ROOT / "tools" / "total_field_dynamic_context.py").read_text(encoding="utf-8")
if "def build_8dadi_state_cell_projection(" not in dc:
    fail("STATE_CELL_PROJECTION_NOT_FOUND")

print("STATE=TOTAL_FIELD_GST_SKILL_BINDINGS_VERIFIED_CANDIDATE")
print(f"TRUE_GST_SHA256={sha256(GST)}")
print("INTENT_FIELD_BINDING=FOUND")
print("STATE_CELL_BINDING=FOUND")
print("CLOUD_CANDIDATE_BINDING=FOUND")
print("FORMAL_REVIEW_CANDIDATE_BINDING=FOUND")
print("TRUE_GST_BINDING=FOUND")
print("SKILL_AUTHORITY=NONE")
print("RUNTIME_EFFECT=NONE")
