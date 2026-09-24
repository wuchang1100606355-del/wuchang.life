#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "products" / "eight_dimensional_generative_memory" / "w7tp_origin_cell_generative_v2.py"

SPEC = importlib.util.spec_from_file_location("w7tp_origin_cell_generative_v2", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load Origin Cell V2 candidate")
origin_cell = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(origin_cell)

def emit(name: str, state: str, **evidence):
    return {"check": name, "state": state, **evidence}

def expect_hold(fn, code: str):
    try:
        fn()
    except origin_cell.OriginCellHold as exc:
        return exc.code == code, exc.code
    except Exception as exc:
        return False, f"UNEXPECTED:{type(exc).__name__}:{exc}"
    return False, "NO_HOLD"

def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="w7tp-origin-cell-redteam-"))
    checks = []
    try:
        source = root / "source"
        receiver = root / "receiver"
        receiver.mkdir()
        origin_cell.generate_target(source, origin_cell.MIN_DATASET_MIB, variant=91)

        _, source_bytes, source_manifest = origin_cell.file_manifest(source)
        analysis = origin_cell.analyze_source_and_generate_rules(source)
        packet = origin_cell.build_rule_packet(
            source_analysis=analysis,
            generator_base_sha256=origin_cell.sha256_file(MODULE_PATH),
        )

        recipe_path = origin_cell._source_recipe_path(source)
        recipe_backup = recipe_path.read_bytes()
        recipe_path.unlink()
        ok, observed = expect_hold(
            lambda: origin_cell.analyze_source_and_generate_rules(source),
            "HOLD_SOURCE_GENERATIVE_PROVENANCE_MISSING",
        )
        checks.append(emit(
            "UNKNOWN_SOURCE_RULE_DISCOVERY",
            "GAP_CONFIRMED" if ok else "UNEXPECTED_RESULT",
            observed=observed,
            interpretation="Analyzer requires pre-existing source-side generative provenance."
        ))
        recipe_path.write_bytes(recipe_backup)

        external = root / "external-unknown"
        external.mkdir()
        random_path = external / "unseen-random.bin"
        with random_path.open("wb") as handle:
            for _ in range(8):
                handle.write(os.urandom(1024 * 1024))
        ok, observed = expect_hold(
            lambda: origin_cell.analyze_source_and_generate_rules(external),
            "HOLD_SOURCE_GENERATIVE_PROVENANCE_MISSING",
        )
        checks.append(emit(
            "EXTERNAL_UNKNOWN_HIGH_ENTROPY_SOURCE",
            "GAP_CONFIRMED" if ok else "UNEXPECTED_RESULT",
            observed=observed,
            bytes=random_path.stat().st_size,
            interpretation="No autonomous generative representation path exists for an unseen source without provenance."
        ))

        rules_only_output = root / "rules-only-output"
        rules_only_output.mkdir()
        origin_cell.execute_reconstruction_rules(
            rules_only_output,
            copy.deepcopy(packet["reconstruction_rules"]),
            copy.deepcopy(packet["execution_order"]),
        )
        _, rules_only_bytes, rules_only_manifest = origin_cell.file_manifest(rules_only_output)
        rules_only_match = rules_only_manifest == source_manifest and rules_only_bytes == source_bytes
        checks.append(emit(
            "8D_CAUSAL_ABLATION",
            "GAP_CONFIRMED" if rules_only_match else "8D_REQUIRED_BY_DATA_PATH",
            rules_only_manifest_match=rules_only_match,
            interpretation="If GAP_CONFIRMED, byte reconstruction is performed by rules + execution_order while D1-D8 govern or validate the transition."
        ))

        altered_executor = root / "altered_executor.py"
        altered_executor.write_bytes(MODULE_PATH.read_bytes() + b"\n# redteam mutation\n")
        ok, observed = expect_hold(
            lambda: origin_cell.validate_rule_packet(packet, altered_executor),
            "HOLD_GENERATOR_BASE_HASH_MISMATCH",
        )
        checks.append(emit(
            "SHARED_GENERIC_EXECUTOR_DEPENDENCY",
            "CONFIRMED" if ok else "UNEXPECTED_RESULT",
            observed=observed,
            interpretation="No target-data base is required, but the exact committed generic executor is required."
        ))

        unknown_field_packet = copy.deepcopy(packet)
        unknown_field_packet["reconstruction_rules"][0]["banana"] = "redteam-unknown-field"
        unknown_field_packet["rule_body_sha256"] = origin_cell.sha256_bytes(
            origin_cell.canonical_json_bytes(unknown_field_packet["reconstruction_rules"])
        )
        unknown_field_packet["joint_state_field"]["D6"]["rule_body_sha256"] = unknown_field_packet["rule_body_sha256"]
        unknown_field_packet["packet_sha256"] = origin_cell.packet_sha256(unknown_field_packet)
        schema_bypass = True
        schema_error = None
        try:
            origin_cell.validate_rule_packet(unknown_field_packet, MODULE_PATH)
        except Exception as exc:
            schema_bypass = False
            schema_error = f"{type(exc).__name__}:{exc}"
        checks.append(emit(
            "STRICT_RULE_SCHEMA_ALLOWLIST",
            "GAP_CONFIRMED" if schema_bypass else "REJECTED",
            validation_accepted_unknown_field=schema_bypass,
            observed_error=schema_error,
            interpretation="Validator rejects known forbidden keys but does not enforce a strict per-primitive allow-list."
        ))

        metric_packet = copy.deepcopy(packet)
        metric_packet["reconstruction_rules"][0]["opaque_text"] = "A" * 65536
        metric_packet["rule_body_sha256"] = origin_cell.sha256_bytes(
            origin_cell.canonical_json_bytes(metric_packet["reconstruction_rules"])
        )
        metric_packet["joint_state_field"]["D6"]["rule_body_sha256"] = metric_packet["rule_body_sha256"]
        metric_packet["packet_sha256"] = origin_cell.packet_sha256(metric_packet)
        literal = origin_cell.transmitted_rule_literal_bytes(metric_packet["reconstruction_rules"])
        total = len(origin_cell.canonical_json_bytes(metric_packet))
        checks.append(emit(
            "RULE_LITERAL_BYTE_METRIC",
            "METRIC_GAP_CONFIRMED" if literal == 0 else "COUNTED",
            transmitted_rule_literal_bytes=literal,
            actual_serialized_packet_bytes=total,
            interpretation="transmitted_rule_literal_bytes is not a complete information-volume metric; serialized packet bytes must remain authoritative."
        ))

        reconstructed = root / "baseline-reconstructed"
        receipt = origin_cell.reconstruct_from_rule_packet(packet, receiver, reconstructed)
        _, rebuilt_bytes, rebuilt_manifest = origin_cell.file_manifest(reconstructed)
        baseline_ok = (
            rebuilt_manifest == source_manifest
            and rebuilt_bytes == source_bytes
            and receipt["transmitted_target_bytes"] == 0
            and receipt["differential_payload_bytes"] == 0
        )
        checks.append(emit(
            "SUPPORTED_SOURCE_CLASS_BASELINE",
            "PASS" if baseline_ok else "FAIL",
            exact_manifest_match=rebuilt_manifest == source_manifest,
            exact_byte_count_match=rebuilt_bytes == source_bytes,
            transmitted_target_bytes=receipt["transmitted_target_bytes"],
            differential_payload_bytes=receipt["differential_payload_bytes"],
            packet_bytes=receipt["packet_bytes"],
            target_bytes=receipt["target_bytes"],
        ))

        output = {
            "state": "RED_TEAM_GAPS_CONFIRMED" if any("GAP" in c["state"] for c in checks) else "RED_TEAM_NO_GAPS_FOUND",
            "module": str(MODULE_PATH.relative_to(ROOT)),
            "module_sha256": origin_cell.sha256_file(MODULE_PATH),
            "checks": checks,
            "summary": {
                "supported_source_exact_reconstruction": baseline_ok,
                "target_data_base_required": False,
                "shared_generic_executor_required": True,
                "autonomous_unknown_source_rule_discovery": not any(
                    c["check"] == "UNKNOWN_SOURCE_RULE_DISCOVERY" and c["state"] == "GAP_CONFIRMED"
                    for c in checks
                ),
                "8d_required_for_byte_reconstruction": not any(
                    c["check"] == "8D_CAUSAL_ABLATION" and c["state"] == "GAP_CONFIRMED"
                    for c in checks
                ),
                "strict_rule_schema_allowlist_present": not any(
                    c["check"] == "STRICT_RULE_SCHEMA_ALLOWLIST" and c["state"] == "GAP_CONFIRMED"
                    for c in checks
                ),
            },
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)

if __name__ == "__main__":
    raise SystemExit(main())
