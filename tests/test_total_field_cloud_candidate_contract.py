from __future__ import annotations

import json

import pytest

from services.gateway.total_field_cloud_candidate_contract import (
    CloudCandidateContractError,
    MAX_STRING_LENGTH,
    build_provider_request_audit,
    build_cloud_candidate_request,
    run_local_candidate_pipeline,
    validate_compact_candidate_response,
)


def _dynamic_context() -> dict:
    return {
        "state": "TOTAL_FIELD_DYNAMIC_CONTEXT_READY",
        "retrieval_method": "8DADI_MEMORY_INDEX_ONLY",
        "founder_intent_projection": {
            "schema_id": "SYNTHETIC_FOUNDER_INTENT_V1",
            "state": "SYNTHETIC_CURRENT_INTENT",
            "source_ref": "synthetic/local/founder-intent.json",
            "source_sha256": "a" * 64,
            "D1": {"intent": "synthetic code review"},
            "D2": {"state": "candidate"},
            "D3": {"coordinate": "synthetic:module-a"},
            "D4": {"evidence": "synthetic-only"},
            "D5": {"policy": "candidate-only"},
            "D6": {"generative_transmission": False},
            "D7": {"risk": "no external effect"},
            "D8": {"authority": False},
        },
        "capability_route": {
            "skill_lookup": {"selected_skill": "synthetic_code_review"}
        },
    }


def test_state_cell_stack_preserves_existing_d1_d8_only_locally() -> None:
    context = _dynamic_context()
    request = build_cloud_candidate_request(
        context,
        task="Review synthetic module A and return candidate operations.",
    )

    stack = request["state_cell_stack"]
    assert stack["state"] == "8DADI_STATE_CELL_PROJECTION_CANDIDATE_READY"
    assert stack["cells"][0]["dimensions"] == {
        key: context["founder_intent_projection"][key]
        for key in ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8")
    }


def test_model_visible_context_contains_only_derived_cell_refs_and_rule_results() -> None:
    context = _dynamic_context()
    request = build_cloud_candidate_request(
        context,
        task="Review synthetic module A and return candidate operations.",
    )

    visible = request["model_visible_context"]
    serialized = json.dumps(visible, ensure_ascii=False)
    assert visible["state_cells"] == [
        {"ref": "CELL_1", "state": "CANDIDATE", "relation_refs": []}
    ]
    assert visible["local_rule_result"]["raw_local_rules_visible"] is False
    assert request["provider_route_in_model_context"] is False
    assert request["local_symbol_map"] == {
        "CELL_1": request["state_cell_stack"]["cells"][0]["cell_id"]
    }
    assert "Review synthetic module A" not in serialized
    assert len(request["local_task_sha256"]) == 64
    for forbidden in (
        "founder_intent_projection",
        "intent_translation_application_rules",
        "source_ref",
        "evidence_ref",
        "synthetic/local/founder-intent.json",
        '"D1"',
        '"D8"',
    ):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    "task",
    [
        "Contact person@example.test",
        "Read /home/private/project/file.py",
        "Inspect taiji01 service",
        "Use FOUNDER_NATURAL_PERSON_SOVEREIGN_IDENTITY_ROOT",
    ],
)
def test_cloud_request_blocks_real_identity_and_internal_coordinates(task: str) -> None:
    with pytest.raises(CloudCandidateContractError, match="BLOCK_CONTEXT_LEAK"):
        build_cloud_candidate_request(_dynamic_context(), task=task)


def test_compact_candidate_response_accepts_exact_contract() -> None:
    result = validate_compact_candidate_response(
        json.dumps(
            {
                "s": "OK",
                "o": [
                    {
                        "f": "FILE_A",
                        "a": "REPLACE",
                        "p": "function:run",
                        "v": "return candidate",
                    }
                ],
                "e": ["synthetic test"],
                "n": [],
            }
        )
    )
    assert result["s"] == "OK"
    assert result["o"][0]["a"] == "REPLACE"


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ('```json\n{"s":"OK","o":[],"e":[],"n":[]}\n```', "JSON_ONLY"),
        ('{"s":"PASS","o":[],"e":[],"n":[]}', "STATUS"),
        ('{"s":"OK","o":[],"e":[],"n":[],"x":1}', "SCHEMA"),
        (
            '{"s":"OK","o":[{"f":"a","a":"WRITE"}],"e":[],"n":[]}',
            "ACTION",
        ),
        (
            '{"s":"OK","o":[{"f":"private/module.py","a":"READ"}],"e":[],"n":[]}',
            "REAL_COORDINATE",
        ),
        (
            json.dumps(
                {
                    "s": "OK",
                    "o": [{"f": "FILE_A", "a": "INSERT", "v": "x" * (MAX_STRING_LENGTH + 1)}],
                    "e": [],
                    "n": [],
                }
            ),
            "STRING_TOO_LONG",
        ),
        (
            '{"s":"OK","o":[{"f":"FILE_A","a":"READ"},{"f":"FILE_A","a":"READ"}],"e":[],"n":[]}',
            "DUPLICATE_OPERATION",
        ),
    ],
)
def test_compact_candidate_response_rejects_contract_violations(
    raw: str,
    reason: str,
) -> None:
    with pytest.raises(CloudCandidateContractError, match=reason):
        validate_compact_candidate_response(raw)


def test_allowlisted_code_is_symbolized_and_reconstructed_only_as_candidate(tmp_path) -> None:
    source = tmp_path / "module_a.py"
    source.write_text("def real_name(value):\n    return value.strip()\n", encoding="utf-8")
    request = build_cloud_candidate_request(
        _dynamic_context(),
        task="Review the synthetic object.",
        repo_root=tmp_path,
        fragment_allowlist=[{"path": "module_a.py", "objects": ["real_name"]}],
    )

    visible = request["model_visible_context"]
    serialized = json.dumps(visible, ensure_ascii=False)
    assert visible["code_objects"][0]["ref"] == "OBJECT_A"
    assert "def OBJECT_A" in visible["code_objects"][0]["content"]
    assert "real_name" not in serialized
    assert "module_a.py" not in serialized
    assert str(tmp_path) not in serialized
    assert request["local_symbol_map"]["FILE_A"]["path"] == str(source.resolve())
    assert request["local_symbol_map"]["OBJECT_A"]["name"] == "real_name"

    payload = {"systemInstruction": {"parts": [{"text": "candidate only"}]}, "contents": visible}
    audit = build_provider_request_audit(payload, request)
    assert audit["request_byte_count"] > 0
    assert audit["symbol_ids"] == ["CELL_1", "FILE_A", "OBJECT_A"]
    assert all(value is False for value in audit["leak_checks"].values())

    candidate = validate_compact_candidate_response(
        '{"s":"OK","o":[{"f":"OBJECT_A","a":"READ"}],"e":[],"n":[]}'
    )
    pipeline = run_local_candidate_pipeline(candidate, request)
    assert pipeline["state"] == "HOLD_GST_FOUNDER_COMPATIBLE_BINDING_MISSING"
    assert pipeline["local_reconstruction"]["worktree_modified"] is False
    assert pipeline["gst_handoff"] is None
    assert pipeline["gst_reconstruction"] is None
    assert pipeline["8d_revalidation"] is None
    assert "V2_1_DELTA_CODEC_RECEIVER_IS_NOT_FOUNDER_GST" in pipeline["hold_reason"]
    assert pipeline["total_field_decision"] is None


def test_projection_blocks_sensitive_source_before_provider(tmp_path) -> None:
    source = tmp_path / "module_a.py"
    source.write_text(
        'def real_name():\n    return "/home/private/secret"\n',
        encoding="utf-8",
    )
    with pytest.raises(CloudCandidateContractError, match="BLOCK_CONTEXT_LEAK"):
        build_cloud_candidate_request(
            _dynamic_context(),
            task="Review the synthetic object.",
            repo_root=tmp_path,
            fragment_allowlist=[{"path": "module_a.py", "objects": ["real_name"]}],
        )


def test_local_pipeline_rejects_unknown_cloud_symbol(tmp_path) -> None:
    source = tmp_path / "module_a.py"
    source.write_text("def real_name():\n    return 1\n", encoding="utf-8")
    request = build_cloud_candidate_request(
        _dynamic_context(),
        task="Review the synthetic object.",
        repo_root=tmp_path,
        fragment_allowlist=[{"path": "module_a.py", "objects": ["real_name"]}],
    )
    candidate = validate_compact_candidate_response(
        '{"s":"OK","o":[{"f":"OBJECT_Z","a":"READ"}],"e":[],"n":[]}'
    )
    with pytest.raises(CloudCandidateContractError, match="UNKNOWN_SYMBOL"):
        run_local_candidate_pipeline(candidate, request)


def test_local_pipeline_does_not_promote_hold_or_full_file_candidate(tmp_path) -> None:
    source = tmp_path / "module_a.py"
    source.write_text("def real_name():\n    return 1\n", encoding="utf-8")
    request = build_cloud_candidate_request(
        _dynamic_context(),
        task="Review the synthetic object.",
        repo_root=tmp_path,
        fragment_allowlist=[{"path": "module_a.py", "objects": ["real_name"]}],
    )
    hold = validate_compact_candidate_response(
        '{"s":"HOLD","o":[],"e":[],"n":["missing"]}'
    )
    with pytest.raises(CloudCandidateContractError, match="HOLD_CLOUD_CANDIDATE_STATUS"):
        run_local_candidate_pipeline(hold, request)

    full_file = validate_compact_candidate_response(
        '{"s":"OK","o":[{"f":"FILE_A","a":"REPLACE","v":"content"}],"e":[],"n":[]}'
    )
    with pytest.raises(CloudCandidateContractError, match="FULL_FILE_OUTPUT_FORBIDDEN"):
        run_local_candidate_pipeline(full_file, request)
