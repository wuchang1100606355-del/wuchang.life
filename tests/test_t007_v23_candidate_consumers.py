from __future__ import annotations

import copy
import hashlib
import importlib
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


POSTIMAGES = Path(__file__).resolve().parents[1]
DELIVERABLE = POSTIMAGES.parent
if str(POSTIMAGES) not in sys.path:
    sys.path.insert(0, str(POSTIMAGES))


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_module(monkeypatch: pytest.MonkeyPatch, name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def _candidate_module():
    return importlib.import_module("tools.total_field.w7tp_v2_3_candidate_source")


def _install_consumer_dependencies(monkeypatch: pytest.MonkeyPatch) -> type[ValueError]:
    class FieldApplicationError(ValueError):
        def __init__(self, reason_code: str, path: str = "$") -> None:
            super().__init__(f"{reason_code}:{path}")
            self.reason_code = reason_code
            self.path = path

    runtime = types.ModuleType("tools.total_field.w7tp_field_application_runtime")
    runtime.FieldApplicationError = FieldApplicationError
    runtime.SCENARIO_ROUTE_TABLE_PATH = Path("not-used-route-table.json")
    runtime.CAPABILITY_REGISTRY_PATH = Path("not-used-capability-registry.json")
    runtime.device_llm_execution_policy = lambda: {
        "llm_inference_location": "USER_DEVICE_ONLY",
        "model_context_upload": "BLOCK",
        "raw_prompt_upload": "BLOCK",
        "server_llm_execution": "BLOCK",
        "transaction_authority": "NONE",
        "cloud_fallback": "BLOCK",
    }
    monkeypatch.setitem(
        sys.modules,
        "tools.total_field.w7tp_field_application_runtime",
        runtime,
    )

    canonical_hash = types.ModuleType(
        "tools.total_field.w7tp_intent_field_suite.canonical_hash"
    )
    canonical_hash.canonical_sha256 = _canonical_sha256
    canonical_hash.normalize_content = lambda value: json.loads(_canonical_json(value))
    monkeypatch.setitem(
        sys.modules,
        "tools.total_field.w7tp_intent_field_suite.canonical_hash",
        canonical_hash,
    )
    return FieldApplicationError


def test_candidate_source_exact_binding_and_fail_closed_tamper() -> None:
    source = _candidate_module()
    contract = source.load_candidate_source_contract()
    result = source.validate_candidate_source_contract(contract)
    binding = source.candidate_source_binding()

    assert result == {
        "state": "PASS_CANDIDATE_SOURCE_PREFLIGHT",
        "candidate_id": "W7TP_8D_ADI_V2_3",
        "version": "2.3",
        "candidate_only": True,
        "canonical": False,
        "d8_authorized": False,
        "contract_self_sha256": "815ca3c13dce2ac140978cf7070ee09cc32a840dc1cae2a47da4aef54e0720fc",
        "source_revision_id": "ANLCKQngZKaKNPqTJtoWJgOGEZDmDiIu_XcrBq24Ibuho1v7G0ZS3J7DFZaqOsi76DB_EhL_0V1LG2DZZyllQidUFAHBEco1ZvRhBWID38A",
        "source_content_sha256": "dfd9147a5d053764025f318cd49213cdb3ce9df6fa017ec0ad62ad08821f9597",
        "formal_authority_unchanged": True,
    }
    assert binding["contract_file_sha256"] == _file_sha256(source.CONTRACT_PATH)
    assert binding["candidate_only"] is True
    assert binding["canonical"] is False
    assert binding["d8_authorized"] is False
    assert binding["external_effect"] is False
    assert binding["formal_authority_baseline"]["version"] == "2.1"

    cases = []
    wrong_revision = copy.deepcopy(contract)
    wrong_revision["source_observation"]["primary"]["revision_id"] = "wrong"
    cases.append((wrong_revision, "HOLD_V23_CANDIDATE_SOURCE_DRIFT"))
    promoted = copy.deepcopy(contract)
    promoted["authority_boundary"]["canonical"] = True
    cases.append((promoted, "HOLD_V23_CANDIDATE_AUTHORITY_DRIFT"))
    d8_promoted = copy.deepcopy(contract)
    d8_promoted["authority_boundary"]["d8_authorized"] = True
    cases.append((d8_promoted, "HOLD_V23_CANDIDATE_AUTHORITY_DRIFT"))
    external_effect = copy.deepcopy(contract)
    external_effect["forbidden_effects"]["external_effect"] = True
    cases.append((external_effect, "HOLD_V23_CANDIDATE_FORBIDDEN_EFFECT"))
    wrong_self_hash = copy.deepcopy(contract)
    wrong_self_hash["contract_self_sha256"] = "0" * 64
    cases.append((wrong_self_hash, "HOLD_V23_CANDIDATE_SELF_HASH_MISMATCH"))

    for candidate, reason in cases:
        with pytest.raises(source.CandidateSourceError) as exc:
            source.validate_candidate_source_contract(candidate)
        assert exc.value.reason_code == reason


def test_five_skill_candidate_contracts_are_hash_bound_but_non_executable() -> None:
    matrix_path = (
        POSTIMAGES
        / "manifests/total_field/w7tp_five_skill_id_binding_matrix_v2_3_candidate/BINDING_MATRIX.json"
    )
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    target_ids = {
        "w7tp.total-field.skill-governance",
        "w7tp.intent-field-construction",
        "w7tp.reconstruct-private-media",
        "w7tp.wuchang.community-announcement-xiaoj",
        "w7tp.generative-transmission",
    }

    assert matrix["state"] == "CANDIDATE_EVIDENCE_ONLY_NOT_FORMAL"
    assert set(matrix["bindings"]) == target_ids
    assert matrix["readiness"] == {
        "source_located_count": 2,
        "implementation_not_located_count": 3,
        "formal_manifest_count": 0,
        "exact_formal_manifest_count_required": 5,
        "formal_review_eligible": False,
        "native_skill_substitution_allowed": False,
    }
    assert not any(matrix["forbidden_effects"].values())
    assert matrix["formal_authority_baseline"]["version"] == "2.1"
    assert matrix["formal_authority_baseline"]["unchanged"] is True

    located = 0
    missing = 0
    for target_id, binding in matrix["bindings"].items():
        contract_path = POSTIMAGES / binding["candidate_contract_ref"]
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        assert binding["target_skill_id"] == target_id
        assert binding["candidate_contract_sha256"] == _file_sha256(contract_path)
        assert contract["target_skill_id"] == target_id
        assert contract["candidate_executable"] is False
        assert contract["activation"] is False
        assert contract["canonical"] is False
        assert contract["d8_authorized"] is False
        assert not (POSTIMAGES / contract["intended_manifest_path"]).exists()
        status = contract["implementation_resolution"]["status"]
        located += status == "SOURCE_LOCATED_IDENTITY_EQUIVALENCE_NOT_PROVEN"
        missing += status == "IMPLEMENTATION_NOT_LOCATED_IN_BOUNDED_COORDINATES"
    assert (located, missing) == (2, 3)

    native = json.loads(
        (POSTIMAGES / "capabilities/W7TP_NATIVE_SKILLS_INDEX.json").read_text(
            encoding="utf-8"
        )
    )
    assert target_ids.isdisjoint(native["skills"])


def test_adaptive_edge_guard_and_scene_consumers_follow_active_authority_pointer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    FieldApplicationError = _install_consumer_dependencies(monkeypatch)
    source = _candidate_module()
    candidate = source.candidate_source_binding()
    active = source.active_canonical_binding()
    suite_dir = POSTIMAGES / "tools/total_field/w7tp_intent_field_suite"

    adaptive = _load_module(
        monkeypatch,
        "tools.total_field.w7tp_intent_field_suite.adaptive_cognition_t007",
        suite_dir / "adaptive_cognition.py",
    )
    policy = adaptive.active_policy()
    assert policy["successor_candidate_source"] == candidate
    assert policy["active_canonical_binding"] == active
    assert policy["source_refs"] == [f"repo:{active['canonical_path']}"]
    assert policy["successor_candidate_id"] == "W7TP_8D_ADI_V2_3"
    assert policy["migration_mode"] == "APPEND_ONLY_SUCCESSOR"
    unsigned_policy = dict(policy)
    supplied_policy_hash = unsigned_policy.pop("policy_hash")
    assert supplied_policy_hash == _canonical_sha256(unsigned_policy)

    edge = _load_module(
        monkeypatch,
        "tools.total_field.w7tp_intent_field_suite.edge_queue_t007",
        suite_dir / "edge_queue.py",
    )
    route_path = tmp_path / "routes.json"
    registry_path = tmp_path / "registry.json"
    canonical_path = tmp_path / "v2.1.md"
    route_path.write_text(
        json.dumps({"routes": {"demo": {"packet_type": "L3"}}}),
        encoding="utf-8",
    )
    registry_path.write_text(json.dumps({"capabilities": {}}), encoding="utf-8")
    canonical_path.write_text("isolated fixture", encoding="utf-8")
    monkeypatch.setattr(edge, "_file_sha256", lambda _path: edge.CANONICAL_V2_1_SHA256)
    snapshot = edge.build_sealed_snapshot(
        route_table_path=route_path,
        capability_registry_path=registry_path,
        canonical_v2_path=canonical_path,
    )
    serialized_snapshot = json.loads(json.dumps(snapshot))
    validated = edge.validate_sealed_snapshot(serialized_snapshot)
    assert validated["state"] == "PASS"
    assert validated["canonical_version"] == active["version"]
    assert validated["successor_candidate_version"] == "2.3"
    assert validated["active_authority_pointer_bound"] is True
    assert snapshot["active_canonical_binding"] == active
    assert snapshot["successor_candidate_source"] == candidate

    tampered = copy.deepcopy(snapshot)
    tampered["successor_candidate_source"]["canonical"] = True
    unsigned_tampered = dict(tampered)
    unsigned_tampered.pop("content_sha256")
    tampered["content_sha256"] = _canonical_sha256(unsigned_tampered)
    with pytest.raises(FieldApplicationError) as exc:
        edge.validate_sealed_snapshot(tampered)
    assert exc.value.reason_code == "EDGE_SNAPSHOT_INVALID"

    legacy = {
        "schema_version": "W7TP-SEALED-EDGE-SNAPSHOT/1.1",
        "authority": "READ_ONLY_CANDIDATE_ONLY",
        "canonical_v2_1_sha256": edge.CANONICAL_V2_1_SHA256,
        "canonical_parent_v2_sha256": edge.LEGACY_CANONICAL_V2_SHA256,
        "offline_output_level": "L3_CANDIDATE_ONLY",
        "cloud_fallback": "BLOCK",
        "founder_root_included": False,
        "mutable": False,
    }
    legacy["content_sha256"] = _canonical_sha256(legacy)
    assert edge.validate_sealed_snapshot(legacy)["canonical_version"] == "2.1"

    guard = _load_module(
        monkeypatch,
        "t007_d8_guard_eval",
        POSTIMAGES / "tools/d8_guard_eval.py",
    )
    scan = guard.scan_technical_definition_drift(
        "W7TP packet reconstruction remains verified by the local Total Field.",
        "docs/isolated-candidate-observation.md",
    )
    assert scan["successor_candidate_source"] == candidate
    assert scan["active_canonical_sha256"] == active["canonical_sha256"]
    assert scan["non_executable"] is True
    assert scan["writeback"] is False

    founder = types.ModuleType("tools.total_field.founder_variable_cognition_gate")
    founder.ALLOW = "ALLOW"
    founder.evaluate_founder_identity_gate = lambda *_args, **_kwargs: {"state": "HOLD"}
    monkeypatch.setitem(
        sys.modules, "tools.total_field.founder_variable_cognition_gate", founder
    )
    session = types.ModuleType(
        "tools.total_field.xiaoj_member_bound_session_candidate"
    )
    session.evaluate_session = lambda *_args, **_kwargs: {"state": "HOLD"}
    session.receive_cloud_fragment = lambda *_args, **_kwargs: {"state": "HOLD"}
    monkeypatch.setitem(
        sys.modules,
        "tools.total_field.xiaoj_member_bound_session_candidate",
        session,
    )
    gateway = types.ModuleType("tools.total_field_candidate_gateway")
    gateway.receive_candidate = lambda *_args, **_kwargs: {"state": "HOLD"}
    monkeypatch.setitem(sys.modules, "tools.total_field_candidate_gateway", gateway)
    bridge = _load_module(
        monkeypatch,
        "t007_wuchang_three_org_container_scene_bridge",
        POSTIMAGES / "tools/total_field/wuchang_three_org_container_scene_bridge.py",
    )
    packet = bridge.build_eight_d_media_transport_packet(
        domain="IMAGE",
        verification_level="L3_CANDIDATE",
    )
    assert packet["successor_candidate_source"] == candidate
    assert packet["canonical_id"] == active["canonical_id"]
    assert packet["version"] == active["version"]
    assert packet["canonical_binding"]["sha256"] == active["canonical_sha256"]
    assert "successor_candidate_source" not in packet["core_packet"]
    assert (
        packet["core_packet"]["authority_boundary"]["final_decision_authority"]
        == "LOCAL_TOTAL_FIELD"
    )


def test_release_file_behavior_contains_candidate_dependencies_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_consumer_dependencies(monkeypatch)

    core_encoding = types.ModuleType("tools.total_field.w7tp_core_encoding")
    core_encoding.build_encoding_registry = lambda: {}
    core_encoding.explain_code = lambda *_args, **_kwargs: {}
    monkeypatch.setitem(sys.modules, "tools.total_field.w7tp_core_encoding", core_encoding)

    package = "tools.total_field.w7tp_intent_field_suite"
    stubs = {
        "adaptive_cognition": {"active_policy": lambda: {}},
        "cafe_pos_interop": {
            "DEFAULT_MENU_SNAPSHOT_PATH": Path("menu.json"),
            "build_binding_seal_request": lambda *_a, **_k: {},
            "build_preview_binding_registry": lambda *_a, **_k: {},
            "load_binding_registry": lambda *_a, **_k: {},
            "rectify_surface_candidate": lambda *_a, **_k: {},
        },
        "deployment": {
            "ROOT": POSTIMAGES,
            "build_release_bundle": lambda *_a, **_k: {},
            "install_release_bundle": lambda *_a, **_k: {},
        },
        "edge_queue": {
            "build_sealed_snapshot": lambda *_a, **_k: {},
            "enqueue_packet": lambda *_a, **_k: {},
            "revalidate_queue_file": lambda *_a, **_k: {},
        },
        "node_inventory": {"collect_inventory": lambda *_a, **_k: {}},
        "packet_builder": {"process_intent": lambda *_a, **_k: {}},
    }
    for suffix, attributes in stubs.items():
        module = types.ModuleType(f"{package}.{suffix}")
        for key, value in attributes.items():
            setattr(module, key, value)
        monkeypatch.setitem(sys.modules, f"{package}.{suffix}", module)

    cli = _load_module(
        monkeypatch,
        f"{package}.cli_t007",
        POSTIMAGES / "tools/total_field/w7tp_intent_field_suite/cli.py",
    )
    release_paths = {
        path.relative_to(POSTIMAGES).as_posix() for path in cli._release_files()
    }
    required = {
        "tools/total_field/w7tp_v2_3_candidate_source.py",
        "schemas/field/w7tp_v2_3_candidate_source_contract_v1.schema.json",
        "manifests/total_field/w7tp_8d_adi_v2_3_candidate_source/CONTRACT.json",
        "manifests/total_field/w7tp_five_skill_id_binding_matrix_v2_3_candidate/BINDING_MATRIX.json",
        "govern-total-field-skills/total-field-skill-candidate-contract.json",
        "build-intent-field/total-field-skill-candidate-contract.json",
        "reconstruct-private-media/total-field-skill-candidate-contract.json",
        "wuchang.community-announcement-xiaoj/total-field-skill-candidate-contract.json",
        "w7tp-generative-transmission/total-field-skill-candidate-contract.json",
        "tests/test_t007_v23_candidate_consumers.py",
    }
    assert required <= release_paths
    assert "tools/total_field/w7tp_review_candidate_v2_3_adapter_v2_1.py" not in release_paths
    assert "scripts/verify/verify_w7tp_canonical_v2_1.py" not in release_paths
