#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GST = ROOT / "vendor" / "origin_cell_v2" / "w7tp_origin_cell_generative_v2.py"

spec = importlib.util.spec_from_file_location("gst_vendor", GST)
if spec is None or spec.loader is None:
    raise SystemExit("HOLD_IMPORT_SPEC")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

tmp = Path(tempfile.mkdtemp(prefix="tf-skill-smoke-"))
try:
    source = tmp / "source"
    receiver = tmp / "receiver"
    output = tmp / "output"
    mod.generate_target(source, mod.MIN_DATASET_MIB, variant=11)
    receiver.mkdir()
    analysis = mod.analyze_source_and_generate_rules(source)
    packet = mod.build_rule_packet(
        source_analysis=analysis,
        generator_base_sha256=mod.sha256_file(GST),
    )
    receipt = mod.reconstruct_from_rule_packet(packet, receiver, output)
    if receipt.get("differential_payload_bytes") != 0:
        raise SystemExit("HOLD_DIFFERENTIAL_PRESENT")
    if receipt.get("target_preloaded_base_bytes") != 0:
        raise SystemExit("HOLD_PRELOADED_BASE_PRESENT")
    if receipt.get("hidden_full_transfer") is not False:
        raise SystemExit("HOLD_HIDDEN_FULL_TRANSFER")
    print("STATE=TOTAL_FIELD_GST_SKILL_SMOKE_PASS")
    print("RULE_BODY_TRANSMITTED=YES")
    print("DIFFERENTIAL_BYTES=0")
    print("TARGET_PRELOADED_BASE_BYTES=0")
    print("HIDDEN_FULL_TRANSFER=NO")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
