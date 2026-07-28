from __future__ import annotations

from pathlib import Path

from tools import d8_guard_eval
from tools.total_field import w7tp_true8d_contract_sandbox as true8d
from tools.total_field.w7tp_intent_field_suite import cli
from tools.total_field.w7tp_intent_field_suite.adaptive_cognition import active_policy
from tools.total_field.w7tp_intent_field_suite.canonical_hash import canonical_sha256
from tools.total_field.w7tp_intent_field_suite.edge_queue import (
    CANONICAL_V2_1_SHA256,
    LEGACY_CANONICAL_V2_SHA256,
    build_sealed_snapshot,
    validate_sealed_snapshot,
)


ACTIVE_PATH = (
    "docs/total_field/"
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1.md"
)
LEGACY_PATH = (
    "docs/total_field/"
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"
)


def test_d8_guard_binds_active_v2_1_and_preserves_legacy_parent() -> None:
    assert d8_guard_eval.ACTIVE_GTP_CANONICAL == ACTIVE_PATH
    assert d8_guard_eval.ACTIVE_GTP_CANONICAL_SHA256 == CANONICAL_V2_1_SHA256
    assert d8_guard_eval.LEGACY_GTP_CANONICAL_V2 == LEGACY_PATH
    assert (
        d8_guard_eval.LEGACY_GTP_CANONICAL_V2_SHA256
        == LEGACY_CANONICAL_V2_SHA256
    )
    assert d8_guard_eval._path_context_class(
        d8_guard_eval.ROOT / LEGACY_PATH, ""
    ) == "legacy_canonical_parent"


def test_d8_guard_recognizes_all_five_v2_1_lock_drifts() -> None:
    samples = {
        "GTP-TD-007": "W7TP 是 semantic communication。",
        "GTP-TD-008": "ADI 只有單層，而且是一般資料庫主鍵。",
        "GTP-TD-009": "系統會輸出完整 H64-TD 映射表。",
        "GTP-TD-010": "W7TP 現行實際送件為21項請求項。",
        "GTP-TD-011": "歷史狀態採原地覆寫。",
    }
    for expected_rule, text in samples.items():
        result = d8_guard_eval.scan_technical_definition_drift(
            text, "review.md"
        )
        assert expected_rule in {
            finding["rule_id"] for finding in result["findings"]
        }


def test_edge_snapshot_generates_v2_1_and_reads_v2_legacy() -> None:
    active = build_sealed_snapshot()
    assert active["schema_version"] == "W7TP-SEALED-EDGE-SNAPSHOT/1.1"
    assert active["canonical_v2_1_sha256"] == CANONICAL_V2_1_SHA256
    assert active["canonical_parent_v2_sha256"] == LEGACY_CANONICAL_V2_SHA256
    assert validate_sealed_snapshot(active)["canonical_version"] == "2.1"

    legacy = {
        "schema_version": "W7TP-SEALED-EDGE-SNAPSHOT/1.0",
        "authority": "READ_ONLY_CANDIDATE_ONLY",
        "canonical_v2_sha256": LEGACY_CANONICAL_V2_SHA256,
        "scenario_route_table_sha256": "a" * 64,
        "capability_registry_sha256": "b" * 64,
        "profile_packet_types": {},
        "generative_transmission": "PROTOCOL_NATIVE_8D_INTENT_FIELD_PACKET",
        "offline_output_level": "L3_CANDIDATE_ONLY",
        "cloud_fallback": "BLOCK",
        "founder_root_included": False,
        "mutable": False,
    }
    legacy["content_sha256"] = canonical_sha256(legacy)
    assert validate_sealed_snapshot(legacy)["canonical_version"] == "2.0"


def test_policy_and_release_inventory_bind_v2_1_and_retain_v2() -> None:
    policy = active_policy()
    assert policy["version"] == "1.1.0"
    assert policy["source_refs"] == [f"repo:{ACTIVE_PATH}"]
    assert policy["legacy_source_refs"] == [f"repo:{LEGACY_PATH}"]
    assert policy["migration_mode"] == "APPEND_ONLY_SUCCESSOR"
    release_paths = {path.relative_to(cli.ROOT).as_posix() for path in cli._release_files()}
    assert ACTIVE_PATH in release_paths
    assert LEGACY_PATH in release_paths
    assert "schemas/field/w7tp_true8d_projection_contract_v2.schema.json" in release_paths
    assert "schemas/field/w7tp_true8d_projection_contract_v2_1.schema.json" in release_paths
    assert "tools/total_field/w7tp_true8d_contract_sandbox.py" in release_paths


def test_true8d_generates_v2_1_and_accepts_explicit_v2_legacy_input() -> None:
    route = {
        "packet_type": "TEST",
        "capability_ref": "capability:test",
        "destination_field": "TOTAL_FIELD",
        "service_contract_ref": "service:test",
    }
    active_input = true8d._common("D1", "GENERIC", "INTENT", route)
    assert active_input["contract_version"] == true8d.ACTIVE_CONTRACT_VERSION
    assert active_input["canonical_schema_ref"] == true8d.ACTIVE_CANONICAL_SCHEMA_REF
    assert true8d.validate_common_input(active_input, "D1") == active_input

    legacy_input = dict(active_input)
    legacy_input["contract_version"] = true8d.LEGACY_CONTRACT_VERSION
    legacy_input["canonical_schema_ref"] = true8d.LEGACY_CANONICAL_SCHEMA_REF
    assert true8d.validate_common_input(legacy_input, "D1") == legacy_input

    result = true8d.run_shadow_case("GENERIC", "INTENT")
    assert result["state"] == "PASS"
    assert result["rule_refs"] == [
        "rule:atomic-barrier:v2_1",
        "rule:d7-hard-risk:v2_1",
        "rule:readonly-shadow:v2_1",
    ]
