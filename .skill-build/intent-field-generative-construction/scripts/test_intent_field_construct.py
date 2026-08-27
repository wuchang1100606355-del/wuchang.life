from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import intent_field_construct as subject


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def source(source_class: str, ref: str) -> dict:
    return {"class": source_class, "ref": ref, "authority_asserted": False}


def gate(ref: str) -> dict:
    return {"status": "PASS", "evidence_refs": [ref]}


def recipe(label: str) -> dict:
    return {
        "type": "declarative_generator",
        "recipe_ref": f"synthetic://recipe/{label}",
        "parameters_sha256": digest(f"parameters-{label}"),
    }


def relational_contract() -> dict:
    evidence = lambda label: [f"synthetic://relational/{label}"]
    return {
        "mainline_relation": {
            "candidate_relation": "PARALLEL_SHADOW",
            "hard_gates": {
                "isolation": {"state": "PASS", "evidence_refs": evidence("isolation")},
                "no_effect": {"state": "PASS", "evidence_refs": evidence("no-effect")},
                "no_mainline_impact": {
                    "state": "PASS",
                    "evidence_refs": evidence("no-mainline-impact"),
                },
            },
            "missing_gates": [],
            "first_breakpoint": None,
            "shortest_continuation_route": [],
        },
        "continuation_distance": {
            axis: {
                "state": "ALIGNED",
                "evidence_refs": evidence(f"distance/{axis}"),
            }
            for axis in subject.CONTINUATION_AXES
        },
        "supply_demand_fit": {
            "old_demand_set": [
                {"id": "D1", "evidence_refs": evidence("demand/D1")}
            ],
            "new_supply_mapping": [
                {
                    "demand_id": "D1",
                    "supply_ids": ["S1"],
                    "evidence_refs": evidence("supply/S1"),
                }
            ],
            "uncovered_demands": [],
            "extra_side_effects": [],
            "unknown_dynamic_consumers": [],
            "dependency_cycles": [],
            "authority_conflicts": [],
            "recovery_route": [
                {
                    "step": step,
                    "evidence_refs": evidence(f"recovery/{step}"),
                    "rollback": {
                        "action": f"rollback-{step}",
                        "evidence_refs": evidence(f"recovery/{step}/rollback"),
                    },
                }
                for step in subject.RECOVERY_STEPS
            ],
        },
        "relational_evidence": {
            "evidence_class": "FIELD_EVIDENCE",
            "artifact_ref": "evidence/relational-evidence.json",
            "artifact_sha256": digest("relational-evidence-prebinding"),
            "stage_receipt_ref": "evidence/relational-stage-receipt.json",
            "stage_receipt_sha256": digest("relational-stage-prebinding"),
        },
    }


def journey(
    journey_id: str,
    kind: str,
    scenario: str,
    surface: str,
    role: str,
    evidence_suffix: str,
) -> dict:
    return {
        "id": journey_id,
        "kind": kind,
        "scenario": scenario,
        "surface": surface,
        "role": role,
        "goal": f"{scenario} 角色完成有界候選操作",
        "entry": f"{surface} 清楚標示的候選入口",
        "steps": ["進入候選入口", "確認操作範圍", "取得明確回饋"],
        "feedback": "顯示候選完成、拒絕或回復，且未正式啟用",
        "error_recovery": "失敗時可返回且無部分效果",
        "accessibility": "鍵盤、文字回饋與輔助技術結果等價",
        "authorization_boundary": "登入與封包均不自動升權",
        "exit": "安全返回上一頁",
        "status": "PASS",
        "evidence_refs": [f"synthetic://journey/{evidence_suffix}"],
    }


def valid_spec() -> dict:
    spec = {
        "intent_id": "intent-synthetic-001",
        "logical_root_id": "logical-synthetic",
        "node_id": "node-a",
        "revision": "synthetic-revision-1",
        "user_explicit": [
            {
                "id": "U1",
                "statement": "建立可回復的示範流程",
                "source": source(subject.USER_EXPLICIT, "prompt://turn/1"),
            }
        ],
        "ai_completion_hypotheses": [
            {
                "id": "H1",
                "statement": "候選流程應顯示明確錯誤回復",
                "source": source(subject.AI_HYPOTHESIS, "analysis://director/H1"),
            }
        ],
        "allowed_effects": [
            {
                "id": "E1",
                "description": "只建立隔離測試產物",
                "basis": subject.USER_EXPLICIT,
                "source_fragment_ids": ["U1"],
            }
        ],
        "perspectives": {
            "REAL_HUMAN_USER": [
                {
                    "id": "P-HUMAN-1",
                    "statement": "使用者需要看懂成功與失敗結果",
                    "source": source(subject.AI_HYPOTHESIS, "analysis://human/P1"),
                }
            ],
            "SILICON_VALLEY_DIGITAL_STARTUP_DIRECTOR_PRODUCT_OWNER": [
                {
                    "id": "P-DIRECTOR-1",
                    "statement": "先完成最小可重驗閉環",
                    "source": source(subject.AI_HYPOTHESIS, "analysis://director/P1"),
                }
            ],
        },
        "eight_d": {
            "definition": subject.HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD,
            "dynamic_depth": {
                "selected_depth": 8,
                "selection_reason_refs": ["synthetic://8d/depth/high-risk-transfer"],
                "included_dimensions": list(subject.EIGHT_D_KEYS),
                "omitted_dimensions": [],
                "escalation_triggers": ["CROSS_NODE", "EXTERNAL", "UNCERTAIN_FRONTIER"],
                "authority_effect": "NONE",
                "authority_granted": False,
                "resource_saving_only": False,
            },
            "dimensions": {
                name: gate(f"synthetic://8d/{name}") for name in subject.EIGHT_D_KEYS
            },
        },
        "adi_map": {
            "nodes": [
                {
                    "id": "N-INTENT",
                    "coordinate_ref": "adi://node-a/intent/U1",
                    "source_class": subject.USER_EXPLICIT,
                },
                {
                    "id": "N-CANDIDATE",
                    "coordinate_ref": "adi://node-a/candidate/H1",
                    "source_class": subject.AI_HYPOTHESIS,
                },
                {
                    "id": "N-EVIDENCE",
                    "coordinate_ref": "adi://node-a/evidence/trace",
                    "source_class": "FIELD_EVIDENCE",
                },
            ],
            "edges": [
                {"from": "N-INTENT", "to": "N-CANDIDATE", "relation": "constrains"},
                {"from": "N-CANDIDATE", "to": "N-EVIDENCE", "relation": "requires"},
            ],
            "unknown_frontiers": ["adi://node-a/frontier/runtime-effect"],
        },
        "pattern_recall": {
            "internal": [
                {
                    "id": "PATTERN-INTERNAL-1",
                    "source_ref": "repo://patterns/recovery",
                    "version_ref": "revision://internal/1",
                    "sha256": digest("internal-pattern"),
                }
            ],
            "external": [
                {
                    "id": "PATTERN-EXTERNAL-1",
                    "source_ref": "public-spec://example/1",
                    "version_ref": "version://1.0",
                    "sha256": digest("external-pattern"),
                    "license_status": "PASS",
                    "source_authority_status": "PASS",
                }
            ],
        },
        "architecture": {
            "status": "PASS",
            "components": [
                {
                    "id": "COMPONENT-1",
                    "kind": "isolated-candidate",
                    "interface_ref": "schema://candidate/1",
                }
            ],
            "constraints": [
                {
                    "id": "NO-ACTIVATION",
                    "status": "PASS",
                    "evidence_refs": ["policy://no-activation"],
                }
            ],
            "evidence_refs": ["synthetic://architecture/pass"],
        },
        "code_reconstruction": {
            "status": "PASS",
            "full_source_embedded": False,
            "files": [
                {
                    "path": "generated/candidate.py",
                    "action": "create",
                    "expected_sha256": digest("generated-candidate"),
                    "recipe": recipe("candidate"),
                }
            ],
            "entrypoint_refs": ["entrypoint://candidate/main"],
        },
        "closure": {
            "stages": {
                name: gate(f"synthetic://closure/{name}")
                for name in subject.CLOSURE_STAGES
            }
        },
        "runtime_completion_chain": {
            "runtime_gap_proven": True,
            "initial_gap_refs": ["synthetic://runtime-gap/G1"],
            "stages": [
                {
                    "stage": stage,
                    "attempted": True,
                    "claimed_result": "UNVERIFIED",
                    "gap_state": "GAP_PROVEN" if stage == "RUNTIME_GAP_LOCALIZATION" else None,
                    "evidence_refs": [f"synthetic://runtime-chain/{stage}"],
                }
                for stage in subject.TECHNICAL_CHAIN_STAGES
            ],
            "fallbacks": [
                {
                    "source_class": "EXTERNAL_PRIMARY_SOURCE",
                    "enabled_after_stage": subject.TECHNICAL_CHAIN_STAGES[-1],
                    "target_gap_refs": ["synthetic://runtime-gap/G1"],
                    "grants_authority": False,
                    "rerun_evidence_refs": ["synthetic://runtime-chain/fallback/rerun"],
                    "field_evidence_refs": ["synthetic://runtime-chain/fallback/field"],
                }
            ],
        },
        "user_journeys": [
            journey("J-FIRST", "HAPPY_PATH", "FIRST_TIME", "MOBILE", "first-time-user", "first"),
            journey("J-RETURNING", "HAPPY_PATH", "RETURNING", "DESKTOP", "returning-user", "returning"),
            journey("J-LOW-PERMISSION", "DENIAL_OR_RECOVERY", "LOW_PERMISSION", "DESKTOP", "low-permission-user", "low-permission"),
            journey("J-PENDING", "DENIAL_OR_RECOVERY", "PENDING_REVIEW", "MOBILE", "pending-user", "pending"),
            journey("J-APPROVED", "HAPPY_PATH", "APPROVED", "DESKTOP", "approved-user", "approved"),
            journey("J-REVOKED", "DENIAL_OR_RECOVERY", "REVOKED_OR_EXPIRED", "MOBILE", "revoked-or-expired-user", "revoked"),
            journey("J-ERROR", "DENIAL_OR_RECOVERY", "ERROR_OR_TIMEOUT_RECOVERY", "DESKTOP", "timeout-user", "error-timeout"),
        ],
        "redteam": {
            "max_rounds": 3,
            "stages": {
                name: {
                    "checks": list(checks),
                    "rounds": [
                        {
                            "round": 1,
                            "result": "PASS",
                            "issues_fixed": 1,
                            "evidence_refs": [f"synthetic://redteam/{name}/1"],
                        }
                    ],
                }
                for name, checks in subject.REDTEAM_CHECKS.items()
            },
        },
        "transfer": {
            "mode": "GENERATIVE_PROGRAM_RUBBING",
            "semantic_reconstruction": True,
            "byte_identity_claim": False,
            "full_source_embedded": False,
            "invariant": dict(subject.TRANSFER_INVARIANT),
            "recipes": [recipe("transfer")],
            "tests": [
                {
                    "id": "TEST-1",
                    "status": "PASS",
                    "evidence_ref": "synthetic://test/1",
                }
            ],
            "references": ["schema://ifgc/1.0.0"],
            "cross_node": {
                "source_node": "node-a",
                "target_node": "node-b",
                "pollution_guard": "PASS",
                "drift_guard": "PASS",
                "tamper_guard": "PASS",
                "rollback_guard": "PASS",
                "rollback_ref": "synthetic://rollback/1",
            },
        },
        "governance": {
            "lifecycle": "CANDIDATE",
            "activation": "NOT_AUTHORIZED",
            "packet_is_authorization": False,
            "ai_completion_grants_authority": False,
            "total_field_authority_ref": None,
            "authority_receipt_ref": None,
        },
        "core_functions": {
            name: {"enabled": True, "evidence_refs": [f"synthetic://core/{name}"]}
            for name in subject.CORE_FUNCTIONS
        },
        "trade_secret_boundary": dict(subject.TRADE_SECRET_BOUNDARY),
    }
    spec.update(relational_contract())
    return spec


class IntentFieldConstructTests(unittest.TestCase):
    def assert_hold(self, spec: dict, code: str) -> None:
        with self.assertRaises(subject.ConstructionHold) as caught:
            subject.build_packet(spec)
        self.assertEqual(code, caught.exception.code)

    def test_positive_packet_separates_sources_and_never_authorizes(self) -> None:
        spec = valid_spec()
        packet = subject.build_packet(spec)
        encoded = subject.canonical_bytes(packet).decode("utf-8")
        self.assertEqual(
            [
                "CANDIDATE",
                "USER_JOURNEY_UNVERIFIED",
                "CROSS_NODE_UNVERIFIED",
                "ACTIVATION_NOT_AUTHORIZED",
            ],
            packet["states"],
        )
        self.assertNotIn(spec["user_explicit"][0]["statement"], encoded)
        self.assertNotIn(spec["ai_completion_hypotheses"][0]["statement"], encoded)
        self.assertEqual(subject.USER_EXPLICIT, packet["intent"]["allowed_effects"][0]["basis"])
        self.assertEqual("NOT_AUTHORIZED", packet["governance"]["activation"])
        self.assertFalse(packet["governance"]["packet_is_authorization"])
        self.assertEqual(
            list(subject.TECHNICAL_CHAIN_STAGES),
            [item["stage"] for item in packet["runtime_completion_chain"]["ordered_stages"]],
        )
        self.assertEqual(8, packet["eight_d"]["dynamic_depth"]["selected_depth"])
        self.assertFalse(packet["eight_d"]["dynamic_depth"]["dynamic_arrangement_is_authority"])
        self.assertEqual("NONE", packet["eight_d"]["dynamic_depth"]["authority_effect"])
        self.assertFalse(packet["eight_d"]["dynamic_depth"]["authority_granted"])
        self.assertFalse(packet["eight_d"]["dynamic_depth"]["resource_saving_only"])
        self.assertTrue(
            all(
                item["attempted"] is True and item["claimed_result"] == "UNVERIFIED"
                for item in packet["runtime_completion_chain"]["ordered_stages"]
            )
        )
        self.assertEqual(dict(subject.TRANSFER_INVARIANT), packet["transfer"]["invariant"])
        self.assertEqual(set(subject.CORE_FUNCTIONS), set(packet["core_functions"]))
        self.assertEqual(dict(subject.TRADE_SECRET_BOUNDARY), packet["trade_secret_boundary"])
        self.assertEqual("PARALLEL_SHADOW", packet["mainline_relation"]["candidate_relation"])
        self.assertEqual(set(subject.CONTINUATION_AXES), set(packet["continuation_distance"]))
        self.assertEqual(
            list(subject.RECOVERY_STEPS),
            [item["step"] for item in packet["supply_demand_fit"]["recovery_route"]],
        )

    def test_relational_fields_are_required_and_strictly_typed(self) -> None:
        for field in ("mainline_relation", "continuation_distance", "supply_demand_fit"):
            with self.subTest(field=field):
                spec = valid_spec()
                del spec[field]
                self.assert_hold(spec, "HOLD_SCHEMA_TYPE")
        spec = valid_spec()
        spec["continuation_distance"]["semantic"]["state"] = 1
        self.assert_hold(spec, "HOLD_REQUIRED_STRING")
        spec = valid_spec()
        spec["supply_demand_fit"]["uncovered_demands"] = "D1"
        self.assert_hold(spec, "HOLD_SCHEMA_TYPE")

    def test_unknown_axis_and_supply_conflict_fail_closed(self) -> None:
        spec = valid_spec()
        spec["continuation_distance"]["cross_node"]["state"] = "UNKNOWN"
        spec["mainline_relation"]["missing_gates"] = ["continuation_distance.cross_node"]
        spec["mainline_relation"]["first_breakpoint"] = "continuation_distance.cross_node"
        spec["mainline_relation"]["shortest_continuation_route"] = [
            {
                "step": "obtain detached cross-node evidence",
                "evidence_refs": ["synthetic://relational/route/cross-node"],
            }
        ]
        self.assert_hold(spec, "HOLD_RELATION_UNKNOWN_REQUIRES_HOLD")

        spec = valid_spec()
        spec["mainline_relation"]["candidate_relation"] = "REPLACE"
        spec["mainline_relation"]["hard_gates"] = {
            name: {
                "state": "PASS",
                "evidence_refs": [f"synthetic://relational/replace/{name}"],
            }
            for name in subject.RELATION_HARD_GATES["REPLACE"]
        }
        spec["supply_demand_fit"]["new_supply_mapping"] = []
        spec["supply_demand_fit"]["uncovered_demands"] = [
            {"id": "D1", "evidence_refs": ["synthetic://relational/uncovered/D1"]}
        ]
        spec["mainline_relation"]["missing_gates"] = [
            "supply_demand_fit.uncovered_demands"
        ]
        spec["mainline_relation"]["first_breakpoint"] = (
            "supply_demand_fit.uncovered_demands"
        )
        spec["mainline_relation"]["shortest_continuation_route"] = [
            {
                "step": "map remaining demand before replacement",
                "evidence_refs": ["synthetic://relational/route/map-demand"],
            }
        ]
        self.assert_hold(spec, "HOLD_SUPPLY_DEMAND_RELATION_CONFLICT")

    def test_runtime_completion_chain_requires_every_segment_in_order(self) -> None:
        spec = valid_spec()
        spec["runtime_completion_chain"]["stages"] = spec["runtime_completion_chain"]["stages"][:-1]
        self.assert_hold(spec, "HOLD_RUNTIME_CHAIN_STAGE_SET")
        spec = valid_spec()
        stages = spec["runtime_completion_chain"]["stages"]
        stages[1], stages[2] = stages[2], stages[1]
        self.assert_hold(spec, "HOLD_RUNTIME_CHAIN_ORDER")

    def test_runtime_completion_chain_requires_stage_evidence_and_gap_proof(self) -> None:
        spec = valid_spec()
        spec["runtime_completion_chain"]["stages"][3]["evidence_refs"] = []
        self.assert_hold(spec, "HOLD_REQUIRED_EMPTY")
        spec = valid_spec()
        spec["runtime_completion_chain"]["runtime_gap_proven"] = False
        self.assert_hold(spec, "HOLD_RUNTIME_GAP_NOT_PROVEN")
        spec = valid_spec()
        spec["runtime_completion_chain"]["stages"][0]["gap_state"] = "NO_GAP"
        self.assert_hold(spec, "HOLD_RUNTIME_GAP_NOT_PROVEN")
        spec = valid_spec()
        spec["runtime_completion_chain"]["stages"][0]["claimed_result"] = "PASS"
        self.assert_hold(spec, "HOLD_RUNTIME_CHAIN_GATE")

    def test_external_or_model_fallback_requires_gap_chain_and_no_authority_escalation(self) -> None:
        spec = valid_spec()
        spec["runtime_completion_chain"]["fallbacks"] = []
        self.assert_hold(spec, "HOLD_FALLBACK_UNDECLARED")
        spec = valid_spec()
        spec["runtime_completion_chain"]["fallbacks"][0]["grants_authority"] = True
        self.assert_hold(spec, "HOLD_FALLBACK_AUTHORITY_ESCALATION")
        spec = valid_spec()
        spec["runtime_completion_chain"]["fallbacks"][0]["enabled_after_stage"] = "RUNTIME_GAP_LOCALIZATION"
        self.assert_hold(spec, "HOLD_FALLBACK_STAGE")
        spec = valid_spec()
        spec["runtime_completion_chain"]["fallbacks"][0]["target_gap_refs"] = ["synthetic://runtime-gap/not-initial"]
        self.assert_hold(spec, "HOLD_FALLBACK_TARGET_GAP_REFS")
        spec = valid_spec()
        spec["runtime_completion_chain"]["fallbacks"][0]["rerun_evidence_refs"] = []
        self.assert_hold(spec, "HOLD_REQUIRED_EMPTY")
        spec = valid_spec()
        spec["adi_map"]["nodes"].append(
            {
                "id": "N-MODEL-PRIOR",
                "coordinate_ref": "adi://node-a/model-prior/runtime-gap",
                "source_class": "MODEL_PRIOR_CANDIDATE",
            }
        )
        self.assert_hold(spec, "HOLD_FALLBACK_UNDECLARED")

    def test_unused_fallback_requires_empty_gap_lists(self) -> None:
        spec = valid_spec()
        spec["pattern_recall"]["external"] = []
        spec["runtime_completion_chain"]["initial_gap_refs"] = []
        spec["runtime_completion_chain"]["fallbacks"] = []
        packet = subject.build_packet(spec)
        self.assertEqual([], packet["runtime_completion_chain"]["initial_gap_refs"])
        self.assertEqual([], packet["runtime_completion_chain"]["fallbacks"])

    def test_dynamic_8d_depth_forces_eight_on_risk_and_rejects_resource_downscope(self) -> None:
        spec = valid_spec()
        dynamic = spec["eight_d"]["dynamic_depth"]
        dynamic["selected_depth"] = 7
        dynamic["included_dimensions"] = list(subject.EIGHT_D_KEYS[:-1])
        dynamic["omitted_dimensions"] = [subject.EIGHT_D_KEYS[-1]]
        self.assert_hold(spec, "HOLD_8D_FORCE_DEPTH")
        spec = valid_spec()
        spec["eight_d"]["dynamic_depth"]["resource_saving_downscope"] = True
        self.assert_hold(spec, "HOLD_8D_RESOURCE_DOWNSCOPE")
        spec = valid_spec()
        spec["eight_d"]["dynamic_depth"]["authority_effect"] = "WRITE"
        self.assert_hold(spec, "HOLD_8D_AUTHORITY_EFFECT")
        spec = valid_spec()
        spec["eight_d"]["dynamic_depth"]["authority_granted"] = True
        self.assert_hold(spec, "HOLD_8D_AUTHORITY_EFFECT")
        spec = valid_spec()
        spec["eight_d"]["dynamic_depth"]["resource_saving_only"] = True
        self.assert_hold(spec, "HOLD_8D_RESOURCE_DOWNSCOPE")

    def test_dynamic_8d_dimension_sets_must_partition_existing_eight_faces(self) -> None:
        self.assertEqual(
            (
                "identity_source",
                "authority_governance",
                "structure_contract",
                "supply_dependency",
                "function_execution",
                "causality_validation",
                "sequence_version",
                "risk_boundary",
            ),
            subject.EIGHT_D_KEYS,
        )
        spec = valid_spec()
        spec["eight_d"]["dynamic_depth"]["included_dimensions"] = list(subject.EIGHT_D_KEYS) + ["identity_source"]
        self.assert_hold(spec, "HOLD_DUPLICATE_VALUE")
        spec = valid_spec()
        spec["eight_d"]["dynamic_depth"]["included_dimensions"] = list(subject.EIGHT_D_KEYS[:-1])
        spec["eight_d"]["dynamic_depth"]["omitted_dimensions"] = []
        spec["eight_d"]["dynamic_depth"]["selected_depth"] = 7
        self.assert_hold(spec, "HOLD_8D_DIMENSION_SET")
        spec = valid_spec()
        spec["eight_d"]["dimensions"]["ninth"] = gate("synthetic://8d/ninth")
        self.assert_hold(spec, "HOLD_8D_DIMENSION_SET")

    def test_dynamic_8d_escalation_triggers_must_match_runtime_inputs(self) -> None:
        spec = valid_spec()
        spec["eight_d"]["dynamic_depth"]["escalation_triggers"].remove("CROSS_NODE")
        self.assert_hold(spec, "HOLD_8D_ESCALATION_TRIGGER_MISSING")

    def test_legacy_writer_is_fail_closed(self) -> None:
        packet = subject.build_packet(valid_spec())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "artifacts"
            with self.assertRaises(subject.ConstructionHold) as caught:
                subject.write_artifacts(packet, output)
            self.assertEqual("HOLD_LEGACY_WRITER_DISABLED", caught.exception.code)
            self.assertFalse(output.exists())

    def test_validate_only_writes_no_output_artifacts(self) -> None:
        spec = valid_spec()
        with tempfile.TemporaryDirectory() as temporary:
            input_path = Path(temporary) / "sanitized-input.json"
            input_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                decision = subject.main(["--input", str(input_path), "--validate-only"])
            self.assertEqual(2, decision)
            self.assertFalse(json.loads(output.getvalue())["artifacts_written"])
            self.assertEqual(["sanitized-input.json"], [item.name for item in Path(temporary).iterdir()])

    def test_ai_hypothesis_cannot_enter_allowed_effects(self) -> None:
        spec = valid_spec()
        spec["allowed_effects"][0]["source_fragment_ids"] = ["H1"]
        self.assert_hold(spec, "HOLD_EFFECT_REFERENCES_NON_USER_SOURCE")

    def test_ai_completion_cannot_assert_authority(self) -> None:
        spec = valid_spec()
        spec["ai_completion_hypotheses"][0]["source"]["authority_asserted"] = True
        self.assert_hold(spec, "HOLD_SOURCE_CANNOT_GRANT_AUTHORITY")

    def test_both_product_perspectives_are_required(self) -> None:
        spec = valid_spec()
        del spec["perspectives"]["REAL_HUMAN_USER"]
        self.assert_hold(spec, "HOLD_SCHEMA_TYPE")

    def test_every_one_of_seven_redteam_stages_is_a_hard_gate(self) -> None:
        self.assertEqual(7, len(subject.REDTEAM_CHECKS))
        for stage in subject.REDTEAM_CHECKS:
            with self.subTest(stage=stage):
                spec = valid_spec()
                del spec["redteam"]["stages"][stage]
                self.assert_hold(spec, "HOLD_SCHEMA_TYPE")

    def test_unresolved_redteam_issue_holds_instead_of_false_pass(self) -> None:
        spec = valid_spec()
        spec["redteam"]["stages"]["CODE"]["rounds"][0]["result"] = "HOLD"
        self.assert_hold(spec, "HOLD_REDTEAM_UNRESOLVED")

    def test_redteam_fix_loop_is_capped_at_three(self) -> None:
        spec = valid_spec()
        rounds = spec["redteam"]["stages"]["INTENT"]["rounds"]
        for number in (2, 3, 4):
            rounds.append(
                {
                    "round": number,
                    "result": "PASS",
                    "issues_fixed": 1,
                    "evidence_refs": [f"synthetic://redteam/INTENT/{number}"],
                }
            )
        self.assert_hold(spec, "HOLD_REDTEAM_ROUND_LIMIT")

    def test_human_journey_failure_is_a_hard_gate(self) -> None:
        spec = valid_spec()
        spec["user_journeys"][1]["status"] = "HOLD"
        self.assert_hold(spec, "HOLD_USER_JOURNEY")

    def test_all_journey_scenarios_are_required(self) -> None:
        spec = valid_spec()
        spec["user_journeys"] = [
            item for item in spec["user_journeys"] if item["scenario"] != "RETURNING"
        ]
        self.assert_hold(spec, "HOLD_JOURNEY_SCENARIO_SET_INCOMPLETE")

    def test_desktop_and_mobile_or_evidenced_not_applicable_are_required(self) -> None:
        spec = valid_spec()
        for item in spec["user_journeys"]:
            item["surface"] = "DESKTOP"
        self.assert_hold(spec, "HOLD_JOURNEY_SURFACE_SET_INCOMPLETE")

    def test_full_source_embedding_is_rejected(self) -> None:
        spec = valid_spec()
        spec["code_reconstruction"]["files"][0]["content"] = "synthetic fixture"
        self.assert_hold(spec, "HOLD_FULL_SOURCE_EMBEDDED")

    def test_path_traversal_is_rejected(self) -> None:
        spec = valid_spec()
        spec["code_reconstruction"]["files"][0]["path"] = "../escape.py"
        self.assert_hold(spec, "HOLD_UNSAFE_OUTPUT_PATH")

    def test_semantic_reconstruction_cannot_claim_byte_identity(self) -> None:
        spec = valid_spec()
        spec["transfer"]["byte_identity_claim"] = True
        self.assert_hold(spec, "HOLD_FALSE_BYTE_IDENTITY_CLAIM")

    def test_placeholder_secret_field_name_is_not_misclassified(self) -> None:
        spec = valid_spec()
        spec["synthetic_extension"] = {"password": "placeholder-only"}
        packet = subject.build_packet(spec)
        self.assertIn("CANDIDATE", packet["states"])

    def test_true_secret_and_member_plaintext_values_are_rejected(self) -> None:
        spec = valid_spec()
        spec["synthetic_extension"] = {"password": "raw-secret-value"}
        self.assert_hold(spec, "HOLD_SENSITIVE_FIELD")
        spec = valid_spec()
        spec["synthetic_extension"] = {"member_email": "member@example.com"}
        self.assert_hold(spec, "HOLD_SENSITIVE_FIELD")

    def test_external_pattern_requires_license_and_source_authority(self) -> None:
        spec = valid_spec()
        spec["pattern_recall"]["external"][0]["license_status"] = "UNKNOWN"
        self.assert_hold(spec, "HOLD_EXTERNAL_LICENSE")

    def test_cross_node_pollution_guard_is_required(self) -> None:
        spec = valid_spec()
        spec["transfer"]["cross_node"]["pollution_guard"] = "HOLD"
        self.assert_hold(spec, "HOLD_CROSS_NODE_GATE")

    def test_transfer_invariant_is_exact(self) -> None:
        spec = valid_spec()
        spec["transfer"]["invariant"]["recipe_semantics"] = "DRIFTED"
        self.assert_hold(spec, "HOLD_GENERATIVE_TRANSFER_SEMANTIC_DRIFT")

    def test_core_functions_are_exact_enabled_public_refs(self) -> None:
        spec = valid_spec()
        spec["core_functions"]["EXTRA"] = {"enabled": True, "evidence_refs": ["synthetic://core/extra"]}
        self.assert_hold(spec, "HOLD_CORE_FUNCTIONS")
        spec = valid_spec()
        spec["core_functions"]["ANALYSIS"]["enabled"] = False
        self.assert_hold(spec, "HOLD_CORE_FUNCTIONS")
        spec = valid_spec()
        spec["core_functions"]["TRANSFER"]["evidence_refs"] = []
        self.assert_hold(spec, "HOLD_REQUIRED_EMPTY")

    def test_trade_secret_boundary_is_exact_public_contract_only(self) -> None:
        spec = valid_spec()
        spec["trade_secret_boundary"]["weights_included"] = True
        self.assert_hold(spec, "HOLD_TRADE_SECRET_BOUNDARY")
        spec = valid_spec()
        spec["trade_secret_boundary"]["public_contract_only"] = False
        self.assert_hold(spec, "HOLD_TRADE_SECRET_BOUNDARY")

    def test_disabled_legacy_writer_never_overwrites_existing_output(self) -> None:
        packet = subject.build_packet(valid_spec())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "artifacts"
            output.mkdir()
            (output / "existing.txt").write_text("fixture", encoding="utf-8")
            with self.assertRaises(subject.ConstructionHold) as caught:
                subject.write_artifacts(packet, output)
            self.assertEqual("HOLD_LEGACY_WRITER_DISABLED", caught.exception.code)
            self.assertEqual("fixture", (output / "existing.txt").read_text())


if __name__ == "__main__":
    unittest.main()
