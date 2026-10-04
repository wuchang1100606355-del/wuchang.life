from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shutil import copy2
import re as regex

from tools.total_field import w7tp_successor_rebind_reviewer_v1 as reviewer
from tools.total_field import w7tp_successor_rebind_seal_v1 as sealer


SOURCE_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = (
    "w7tp_total_field_successor_rebind_review_request_v2.schema.json",
    "w7tp_total_field_successor_rebind_decision_v2.schema.json",
    "w7tp_total_field_successor_rebind_receipt_v2.schema.json",
    "w7tp_total_field_successor_rebind_seal_v2.schema.json",
)
ROOT_DOCS = (
    "00_FOUNDER_DIRECTIVE.json",
    "01_V23_GLOBAL_SUCCESSOR_CONTRACT_CANDIDATE.json",
    "02_CURRENT_8D_FIELD_V23_SUCCESSOR_CANDIDATE.json",
    "03_ACTIVE_CONSUMER_REBIND_MATRIX.json",
    "04_AUTHORITY_POINTER_SUCCESSOR_RECEIPT_CANDIDATE.json",
    "05_GAP_CLOSURE_STATUS.json",
)
COMPLETION_DOCS = tuple(sorted(reviewer.GLOBAL_COMPLETION_MANIFEST_FILES))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GlobalSuccessorG2SidecarTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        schema_dir = self.root / "schemas/field"
        schema_dir.mkdir(parents=True)
        for name in SCHEMAS:
            copy2(SOURCE_ROOT / "schemas/field" / name, schema_dir / name)
        self.now = datetime(2026, 10, 4, 5, 30, tzinfo=timezone.utc)
        self._build_fixture()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def _resign_request(self) -> None:
        request = self._load(self.request_path)
        request.pop("request_self_sha256", None)
        request["request_self_sha256"] = reviewer.sha256_bytes(
            reviewer.canonical_json_bytes(request)
        )
        write_json(self.request_path, request)

    def _postimage_content(self, consumer_ref: str) -> str:
        if consumer_ref == reviewer.GLOBAL_RETIRED_ADAPTER:
            return (
                '"""Append-only V2.3 review-candidate to Canonical V2.1 adapter.\n'
                "This historical compatibility adapter is not in the active release.\n"
                '"""\n'
            )
        return (
            f'# postimage for {consumer_ref}\n'
            f'ACTIVE_SUCCESSOR_ID = "{reviewer.GLOBAL_SUCCESSOR_ID}"\n'
            'active_canonical_binding = True\n'
        )

    def _skill_name(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        match = regex.search(r"(?m)^name:\s*([^\n]+)$", text)
        if match is None:
            raise AssertionError(f"missing skill name: {path}")
        return match.group(1).strip().strip("\"'")

    def _build_skill_successor(self) -> Path:
        # Use the real NLC source bytes so the installed-skill binding remains testable.
        nlc_ref = ".skill-build/w7tp-8d-adi-natural-language-control/SKILL.md"
        nlc_path = self.root / nlc_ref
        nlc_path.parent.mkdir(parents=True, exist_ok=True)
        copy2(SOURCE_ROOT / nlc_ref, nlc_path)

        skill_defs = {
            "w7tp-8d-adi-natural-language-control": (
                nlc_ref,
                "ACTIVE_EXECUTABLE",
            ),
            "w7tp-test-native": (
                "capabilities/w7tp-test-native/SKILL.md",
                "REGISTERED_NATIVE",
            ),
            "w7tp-test-source": (
                "capabilities/w7tp-test-source/SKILL.md",
                "SOURCE_PRESENT",
            ),
        }
        bindings: dict[str, dict] = {}
        for skill_id, (skill_ref, state) in skill_defs.items():
            source = self.root / skill_ref
            source.parent.mkdir(parents=True, exist_ok=True)
            if skill_id != "w7tp-8d-adi-natural-language-control":
                source.write_text(
                    f"---\nname: {skill_id}\ndescription: test\n---\n",
                    encoding="utf-8",
                )
            bindings[skill_id] = {
                "target_skill_id": skill_id,
                "skill_ref": skill_ref,
                "skill_sha256": sha(source),
                "binding_state": state,
            }

        native_ref = reviewer.GLOBAL_NATIVE_SKILL_INDEX_REF
        native_path = self.root / native_ref
        write_json(
            native_path,
            {
                "state": "TEST_NATIVE_INDEX",
                "skills": ["w7tp-test-native"],
            },
        )
        legacy_ref = reviewer.GLOBAL_SKILL_MATRIX_PREDECESSOR
        legacy_path = self.root / legacy_ref
        write_json(
            legacy_path,
            {
                "state": "LEGACY_TEST_ONLY",
                "binding_count": 5,
            },
        )

        path = (
            self.root
            / "manifests/total_field/w7tp_skill_id_binding_matrix_v2_3/BINDING_MATRIX.json"
        )
        write_json(
            path,
            {
                "schema_version": reviewer.GLOBAL_SKILL_SCOPE_SCHEMA,
                "binding_count": len(bindings),
                "canonical_target": {
                    "canonical_id": reviewer.GLOBAL_SUCCESSOR_ID,
                    "version": "2.3",
                },
                "scope_roots": list(reviewer.GLOBAL_SKILL_SCOPE_ROOTS),
                "active_skill_ids": ["w7tp-8d-adi-natural-language-control"],
                "registered_native_skill_ids": ["w7tp-test-native"],
                "native_skill_index": {
                    "ref": native_ref,
                    "sha256": sha(native_path),
                },
                "legacy_v21_identity_lineage": {
                    "ref": legacy_ref,
                    "sha256": sha(legacy_path),
                    "role": "HISTORY_ONLY_NOT_CURRENT_SKILL_SCOPE",
                },
                "bindings": bindings,
            },
        )
        return path

    def _write_skill_scope_observation(self) -> None:
        legacy_matrix_ref = (
            "manifests/total_field/"
            "w7tp_five_skill_id_binding_matrix_v2_3_candidate/BINDING_MATRIX.json"
        )
        legacy_matrix_path = self.root / legacy_matrix_ref
        legacy_matrix_path.parent.mkdir(parents=True, exist_ok=True)
        copy2(SOURCE_ROOT / legacy_matrix_ref, legacy_matrix_path)
        legacy_matrix = self._load(legacy_matrix_path)

        legacy_entries = []
        for skill_id, binding in legacy_matrix["bindings"].items():
            contract_ref = binding["candidate_contract_ref"]
            contract_path = self.root / contract_ref
            contract_path.parent.mkdir(parents=True, exist_ok=True)
            copy2(SOURCE_ROOT / contract_ref, contract_path)
            contract = self._load(contract_path)
            resolution = contract.get("implementation_resolution") or {}
            legacy_entries.append(
                {
                    "target_skill_id": skill_id,
                    "source_key": binding["source_key"],
                    "contract_ref": contract_ref,
                    "contract_sha256": sha(contract_path),
                    "implementation_status": resolution.get("status"),
                    "technical_identity": resolution.get("technical_identity"),
                    "manifest_status": contract.get("manifest_status"),
                    "candidate_executable": contract.get("candidate_executable"),
                    "activation": contract.get("activation"),
                    "canonical": contract.get("canonical"),
                    "d8_authorized": contract.get("d8_authorized"),
                }
            )

        repo_entries = []
        for root_ref in reviewer.GLOBAL_SKILL_SCOPE_ROOTS:
            base = self.root / root_ref
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("SKILL.md")):
                skill_ref = path.relative_to(self.root).as_posix()
                item = {
                    "skill_id": self._skill_name(path),
                    "skill_ref": skill_ref,
                    "sha256": sha(path),
                    "bytes": path.stat().st_size,
                    "manifest_ref": None,
                }
                repo_entries.append(item)

        installed_entries = []
        installed_root = Path("/home/taiji_admin/.codex/skills")
        for path in sorted(installed_root.glob("*/SKILL.md")):
            skill_id = self._skill_name(path)
            matches = [item for item in repo_entries if item["skill_id"] == skill_id]
            source_hashes = [item["sha256"] for item in matches]
            installed_entries.append(
                {
                    "skill_id": skill_id,
                    "installed_ref": str(path.resolve()),
                    "sha256": sha(path),
                    "bytes": path.stat().st_size,
                    "repo_source_refs": [item["skill_ref"] for item in matches],
                    "repo_source_sha256": source_hashes,
                    "matches_repo_source_bytes": (
                        sha(path) in source_hashes if source_hashes else None
                    ),
                }
            )

        native_path = self.root / reviewer.GLOBAL_NATIVE_SKILL_INDEX_REF
        native = self._load(native_path)
        value = {
            "schema_id": "W7TP_V23_SKILL_SCOPE_REOBSERVATION_V1",
            "state": "OBSERVED_PARTITIONED_SCOPE_NO_IDENTITY_INVENTION",
            "task_ref": "T-007",
            "observed_at": self.now.isoformat(),
            "scope_boundaries": {
                "repo_skill_source_roots": [
                    "capabilities/**/SKILL.md",
                    ".skill-build/**/SKILL.md",
                ],
                "codex_installed_custom_root": "/home/taiji_admin/.codex/skills/*/SKILL.md",
                "codex_system_skills_excluded": True,
                "legacy_vcp_contract_roots": [
                    item["source_key"] for item in legacy_entries
                ],
                "claim": (
                    "Complete only for explicitly enumerated current skill planes; "
                    "no identity inference."
                ),
            },
            "native_skill_index": {
                "ref": reviewer.GLOBAL_NATIVE_SKILL_INDEX_REF,
                "sha256": sha(native_path),
                "state": native["state"],
                "skills": native["skills"],
            },
            "repo_skill_sources": repo_entries,
            "codex_installed_custom_skills": installed_entries,
            "legacy_five_vcp_candidate_identities": legacy_entries,
            "conclusions": {
                "legacy_five_vcp_is_complete_skill_scope": False,
                "legacy_five_vcp_promoted_or_activated": False,
                "missing_or_unproven_legacy_identity_is_not_invented": True,
                "installed_skill_does_not_imply_total_field_authority": True,
                "repo_file_exists_does_not_imply_installed_or_loaded": True,
                "nlc_repo_source_matches_installed_bytes": all(
                    item["matches_repo_source_bytes"] is True
                    for item in installed_entries
                    if item["skill_id"] == "w7tp-8d-adi-natural-language-control"
                ),
            },
            "self_hash_algorithm": "SHA256_CANONICAL_JSON_EXCLUDING_SELF_SHA256_V1",
        }
        value["self_sha256"] = reviewer.sha256_bytes(
            reviewer.canonical_json_bytes(value)
        )
        write_json(
            self.completion / "SKILL_SCOPE_REOBSERVATION_V23.json",
            value,
        )

    def _build_fixture(self) -> None:
        self.pointer_ref = "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
        self.field_ref = "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_CANONICAL.json"
        self.router_ref = "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"
        self.authority_ref = "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
        write_json(self.root / self.pointer_ref, {"state": "ACTIVE_CANONICAL", "version": "2.1"})
        write_json(self.root / self.field_ref, {"state": "ACTIVE_LEGACY_FIELD"})
        write_json(self.root / self.router_ref, {"state": "ACTIVE_LEGACY_ROUTER_FIELD"})
        write_json(
            self.root / self.authority_ref,
            {"node_id": "taiji01", "state": "ACTIVE_TOTAL_FIELD_AUTHORITY"},
        )
        self.pointer_sha = sha(self.root / self.pointer_ref)
        self.field_sha = sha(self.root / self.field_ref)
        self.router_sha = sha(self.root / self.router_ref)
        self.authority_sha = sha(self.root / self.authority_ref)

        self.run_id = "T007_V23_GLOBAL_SUCCESSOR_TEST"
        self.candidate_rel = Path("Taiji_Governance/candidates/t007_test")
        self.candidate = self.root / self.candidate_rel
        self.completion = self.candidate / reviewer.GLOBAL_REVIEW_COMPLETION_DIR

        write_json(
            self.candidate / ROOT_DOCS[0],
            {
                "founder": "\u6c5f\u653f\u9686",
                "run_id": self.run_id,
                "state": "USER_EXPLICIT_FOUNDER_DIRECTIVE",
                "replacement_boundary": {
                    "replace_active_v21_authority_consumption": True,
                    "replace_active_v21_runtime_consumption": True,
                    "replace_active_v21_skill_binding": True,
                    "preserve_historical_v21_evidence": True,
                },
            },
        )
        write_json(
            self.candidate / ROOT_DOCS[1],
            {
                "state": "CANDIDATE_FOR_FORMAL_TOTAL_FIELD_REVIEW",
                "task_id": "T-007",
                "migration_mode": "APPEND_ONLY_SUCCESSOR",
                "predecessor": {
                    "pointer_ref": self.pointer_ref,
                    "pointer_sha256": self.pointer_sha,
                    "version": "2.1",
                },
                "proposed_successor": {
                    "canonical_id": reviewer.GLOBAL_SUCCESSOR_ID,
                    "version": "2.3",
                    "dimension_contract": {
                        "D1": "Intent",
                        "D2": "State",
                        "D3": "Coordinate",
                        "D4": "Evidence",
                        "D5": "Execution/Policy",
                        "D6": "Generative State Transmission",
                        "D7": "Risk/Isolation",
                        "D8": "Envelope/Authority",
                        "mode": "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD",
                        "sequential_pipeline_definition_forbidden": True,
                    },
                    "d6_contract": {"difference_analysis_is_transmission": False},
                },
            },
        )
        write_json(self.candidate / ROOT_DOCS[2], {"state": "SUPERSEDED_PLAN_ONLY"})
        write_json(self.candidate / ROOT_DOCS[4], {"state": "SUPERSEDED_PLAN_ONLY"})
        write_json(self.candidate / ROOT_DOCS[5], {"state": "TEST_ONLY"})

        skill_matrix = self._build_skill_successor()
        postimage_hashes: dict[str, str] = {}
        consumers: list[dict] = []
        for consumer_ref in sorted(reviewer.GLOBAL_REQUIRED_ACTIVE_CONSUMERS):
            action = "REBIND_TO_V23_SUCCESSOR"
            if consumer_ref == reviewer.GLOBAL_RETIRED_ADAPTER:
                action = "RETIRE_FROM_ACTIVE_PATH; retain historical compatibility only"
            elif consumer_ref == reviewer.GLOBAL_SKILL_MATRIX_PREDECESSOR:
                action = "CREATE_V23_SUCCESSOR_MATRIX_AND_REBIND_ACTIVE_CONSUMERS"
            elif consumer_ref == self.field_ref:
                action = "SUPERSEDE_WITH_V23_CURRENT_FIELD_AFTER_FORMAL_REVIEW"
            elif consumer_ref == self.pointer_ref:
                action = "G4_LAST_STEP_ONLY_AFTER_G1_G3_AND_PROMOTION_AUTHORITY"
            item: dict = {"path": consumer_ref, "action": action}
            if consumer_ref in reviewer.GLOBAL_POSTIMAGE_CONSUMER_PREIMAGES:
                if consumer_ref == reviewer.GLOBAL_SKILL_MATRIX_PREDECESSOR:
                    postimage = skill_matrix
                else:
                    postimage = self.root / consumer_ref
                    postimage.parent.mkdir(parents=True, exist_ok=True)
                    postimage.write_text(self._postimage_content(consumer_ref), encoding="utf-8")
                postimage_ref = postimage.relative_to(self.root).as_posix()
                postimage_sha = sha(postimage)
                required = (
                    ["Append-only V2.3 review-candidate to Canonical V2.1 adapter"]
                    if consumer_ref == reviewer.GLOBAL_RETIRED_ADAPTER
                    else (
                        [reviewer.GLOBAL_SUCCESSOR_ID]
                        if consumer_ref == reviewer.GLOBAL_SKILL_MATRIX_PREDECESSOR
                        else [reviewer.GLOBAL_ACTIVE_BINDING_LITERAL]
                    )
                )
                forbidden = (
                    []
                    if consumer_ref == reviewer.GLOBAL_RETIRED_ADAPTER
                    else sorted(reviewer.GLOBAL_OLD_ACTIVE_DIMENSION_LITERALS)
                )
                if consumer_ref == "tools/total_field/w7tp_intent_field_suite/cli.py":
                    forbidden.extend(
                        [
                            reviewer.GLOBAL_RETIRED_ADAPTER,
                            reviewer.GLOBAL_SKILL_MATRIX_PREDECESSOR,
                        ]
                    )
                item.update(
                    {
                        "preimage_sha256": reviewer.GLOBAL_POSTIMAGE_CONSUMER_PREIMAGES[consumer_ref],
                        "postimage_ref": postimage_ref,
                        "postimage_sha256": postimage_sha,
                        "downstream_validation": "PASS",
                        "content_constraints": {
                            "required_literals": required,
                            "forbidden_literals": forbidden,
                        },
                    }
                )
                postimage_hashes[consumer_ref] = postimage_sha
            consumers.append(item)
        write_json(
            self.candidate / ROOT_DOCS[3],
            {
                "run_id": self.run_id,
                "state": "CANDIDATE_REBIND_EVIDENCE",
                "consumers": consumers,
                "history_policy": (
                    "V2.1 strings in evidence, receipts, preimages, release archives, migration history, "
                    "and legacy adapters are not rewritten merely to remove the version number."
                ),
            },
        )

        # Explicit read-only legacy evidence is outside the active postimage set.
        legacy = self.root / "tools/total_field/w7tp_canonical_v2_1_legacy_adapter.py"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(
            'LEGACY_MODE = "READ_ONLY"\nD6 = "D6 Sovereign Privacy Field"\n',
            encoding="utf-8",
        )

        self.root_manifest = self.candidate / "SHA256_MANIFEST.json"
        self._write_root_manifest()

        self.record_id = "task-state:T-007:0123456789abcdef"
        self.record_sha = "a" * 64
        self.dynamic_context = {
            "adi_record_id": self.record_id,
            "record_sha256": self.record_sha,
            "maximum_age_seconds": 3600,
            "packet_sha256": "6" * 64,
            "context_ref": "context:task-state:T-007:" + "6" * 16,
            "pulled_at": reviewer.utc_text(self.now),
        }

        self.downstream_receipt = self.completion / "REOBSERVATION_REVIEWER_EXTENSION_20261003.json"
        write_json(
            self.downstream_receipt,
            {
                "schema_id": "W7TP_T007_GLOBAL_SUCCESSOR_REVIEWER_EXTENSION_REOBSERVATION_V1",
                "task_id": "T-007",
                "node": "taiji01",
                "scope": reviewer.GLOBAL_REVIEW_SCOPE,
                "state": "GLOBAL_CANONICAL_SUCCESSOR_MODE_IMPLEMENTED",
                "result": "PASS",
                "consumer_postimages": postimage_hashes,
                "current_field_preimages": {
                    "current_field": {"ref": self.field_ref, "sha256": self.field_sha},
                    "current_field_router": {"ref": self.router_ref, "sha256": self.router_sha},
                },
                "dynamic_context": self.dynamic_context,
            },
        )

        self.field_sidecar = self.completion / "CURRENT_8D_FIELD_SUCCESSOR.json"
        self._write_field_sidecar()
        self.authority_sidecar = self.completion / "AUTHORITY_SUCCESSOR_RECEIPT_CANDIDATE.json"
        write_json(
            self.authority_sidecar,
            {
                "schema_id": "W7TP_AUTHORITY_SUCCESSOR_EVIDENCE_CANDIDATE_V2",
                "state": "CANDIDATE_NOT_FORMAL",
                "formal": False,
                "successor": {"ref": self.authority_ref, "sha256": self.authority_sha},
                "removed_effects": [],
                "non_effect_fields_equal": {
                    "contract_state": True,
                    "formal_decision_authority": True,
                    "formal_seal_authority": True,
                    "node_id": True,
                    "prohibited_effects": True,
                    "state": True,
                },
                "append_only_policy": {
                    "overwrite_predecessor": False,
                    "rewrite_gst_d8": False,
                    "grant_added_effects_by_this_receipt": False,
                },
                "formal_acceptance_ref": None,
                "original_transition_event_ref": None,
            },
        )
        self.contract_sidecar = self.completion / "GLOBAL_SUCCESSOR_CONTRACT.json"
        self._write_completion_contract()
        for name in ("REGRESSION_SPEC.md", "REOBSERVATION.json", "validate_candidate.py"):
            path = self.completion / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"test fixture {name}\n", encoding="utf-8")
        self._write_skill_scope_observation()
        self.completion_manifest = self.completion / "SHA256_MANIFEST.json"
        self._write_completion_manifest()

        self.founder_ref = "authority/TEST_FOUNDER_AUTHORIZATION.json"
        write_json(
            self.root / self.founder_ref,
            {"founder": "\u6c5f\u653f\u9686", "state": "TEST_ONLY"},
        )
        self.request_path = self.root / "request.json"
        self._write_request()
        self._write_atom()

    def _write_root_manifest(self) -> None:
        write_json(
            self.root_manifest,
            {
                "run_id": self.run_id,
                "files": {
                    name: {
                        "bytes": (self.candidate / name).stat().st_size,
                        "sha256": sha(self.candidate / name),
                    }
                    for name in ROOT_DOCS
                },
            },
        )

    def _write_field_sidecar(self) -> None:
        existing = self._load(self.field_sidecar) if self.field_sidecar.is_file() else {}
        value = {
            "schema_id": "W7TP_CURRENT_8D_FIELD_V23_SUCCESSOR_CANDIDATE_V2",
            "state": "CANDIDATE_NOT_ACTIVE",
            "activation": False,
            "predecessors": [
                {"ref": self.router_ref, "sha256": self.router_sha},
                {"ref": self.field_ref, "sha256": self.field_sha},
            ],
            "supersedes_candidate": {
                "ref": (self.candidate_rel / ROOT_DOCS[2]).as_posix(),
                "sha256": sha(self.candidate / ROOT_DOCS[2]),
            },
            "definition_source": {
                "ref": (self.candidate_rel / ROOT_DOCS[0]).as_posix(),
                "sha256": sha(self.candidate / ROOT_DOCS[0]),
            },
            "semantics": "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD",
            "representation": "TASK_PROJECTION_NOT_EIGHT_FIXED_FIELDS_OR_EIGHT_STEPS",
            "scope": {
                "total_field": "ALL_NODES",
                "dimensions": "TRUE_8D_ALL",
                "router_boundary": "INCLUDED",
                "scan_mode": "PATH_METADATA_ONLY",
            },
            "nodes": [
                {"node_id": "taiji01", "kind": "linux"},
                {
                    "node_id": "RT-BE86U-7428",
                    "kind": "ASUSWRT-Merlin router",
                    "role": "physical_network_boundary",
                },
            ],
            "safety_flags": {
                "PATH_METADATA_ONLY": True,
                "FILE_CONTENT_READ": False,
                "CONFIG_READ": False,
                "NVRAM_WRITE": False,
                "FIREWALL_WRITE": False,
                "ROUTER_REBOOT": False,
                "SECRET_READ": False,
                "MEMBER_PLAINTEXT_READ": False,
                "DB_WRITE": False,
                "SERVICE_RESTART": False,
                "DEPLOY": False,
                "PRODUCTION_RELEASE": False,
            },
            "dimensions": [
                {"id": "D1", "field_en": "Intent"},
                {"id": "D2", "field_en": "State"},
                {"id": "D3", "field_en": "Coordinate"},
                {"id": "D4", "field_en": "Evidence"},
                {"id": "D5", "field_en": "Execution/Policy"},
                {"id": "D6", "field_en": "Generative State Transmission"},
                {"id": "D7", "field_en": "Risk/Isolation"},
                {"id": "D8", "field_en": "Envelope/Authority"},
            ],
            "coupled_constraints": {
                "privacy": "retained as a governed concern, not D6 identity",
                "routing": "retained as capability and policy, not D7 identity",
                "difference_analysis": "差異分析能力，不等於生成式狀態傳輸。",
                "authority": "Founder and local Total Field authority remain distinct",
            },
            "downstream_validation": {
                "state": "PASS",
                "scope": reviewer.GLOBAL_REVIEW_SCOPE,
                "receipt_ref": self.downstream_receipt.relative_to(self.root).as_posix(),
                "receipt_sha256": sha(self.downstream_receipt),
            },
            "formal_total_field_decision_ref": None,
        }
        value.update(existing)
        value["downstream_validation"] = {
            "state": "PASS",
            "scope": reviewer.GLOBAL_REVIEW_SCOPE,
            "receipt_ref": self.downstream_receipt.relative_to(self.root).as_posix(),
            "receipt_sha256": sha(self.downstream_receipt),
        }
        write_json(self.field_sidecar, value)

    def _write_completion_contract(self) -> None:
        existing = self._load(self.contract_sidecar) if self.contract_sidecar.is_file() else {}
        source_bindings = {
            self.pointer_ref: self.pointer_sha,
            self.field_ref: self.field_sha,
            self.router_ref: self.router_sha,
            self.authority_ref: self.authority_sha,
            (self.candidate_rel / "SHA256_MANIFEST.json").as_posix(): sha(self.root_manifest),
        }
        value = {
            "schema_id": "W7TP_V21_TO_V23_GLOBAL_SUCCESSOR_REVIEW_COMPLETION_V1",
            "state": "CANDIDATE_ONLY",
            "task_id": "T-007",
            "version_transition": {"from": "2.1", "mode": "APPEND_ONLY_SUCCESSOR", "to": "2.3"},
            "extends": {
                "ref": (self.candidate_rel / ROOT_DOCS[1]).as_posix(),
                "sha256": sha(self.candidate / ROOT_DOCS[1]),
            },
            "field_successor": {
                "ref": self.field_sidecar.relative_to(self.root).as_posix(),
                "sha256": sha(self.field_sidecar),
            },
            "authority_successor_receipt": {
                "ref": self.authority_sidecar.relative_to(self.root).as_posix(),
                "sha256": sha(self.authority_sidecar),
            },
            "predecessor_pointer": {"ref": self.pointer_ref, "sha256": self.pointer_sha},
            "dimension_contract": {
                "D1": "Intent",
                "D2": "State",
                "D3": "Coordinate",
                "D4": "Evidence",
                "D5": "Execution/Policy",
                "D6": "Generative State Transmission",
                "D7": "Risk/Isolation",
                "D8": "Envelope/Authority",
                "mode": "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD",
                "sequential_pipeline_definition_forbidden": True,
            },
            "closure": {
                "G1": "CANDIDATE_REQUIRES_FORMAL_REVIEW",
                "G2": "CANDIDATE_REQUIRES_CONSUMER_VALIDATION_AND_ACCEPTANCE",
                "G3": "CANDIDATE_REQUIRES_APPEND_ONLY_FORMAL_ACCEPTANCE",
                "G4": "NOT_RUN",
            },
            "non_effects": {
                "deployed": False,
                "formal_decision_created": False,
                "pointer_changed": False,
                "runtime_changed": False,
            },
            "promotion_plan": {"enabled": False},
            "dynamic_context": {
                "adi_record_id": self.record_id,
                "record_sha256": self.record_sha,
                "promotion_authorized_by_dynamic_context": False,
            },
            "source_bindings": [
                {"ref": ref, "sha256": digest}
                for ref, digest in source_bindings.items()
            ],
        }
        value.update(existing)
        value["extends"] = {
            "ref": (self.candidate_rel / ROOT_DOCS[1]).as_posix(),
            "sha256": sha(self.candidate / ROOT_DOCS[1]),
        }
        value["field_successor"] = {
            "ref": self.field_sidecar.relative_to(self.root).as_posix(),
            "sha256": sha(self.field_sidecar),
        }
        value["authority_successor_receipt"] = {
            "ref": self.authority_sidecar.relative_to(self.root).as_posix(),
            "sha256": sha(self.authority_sidecar),
        }
        value["source_bindings"] = [
            {"ref": ref, "sha256": digest} for ref, digest in source_bindings.items()
        ]
        write_json(self.contract_sidecar, value)

    def _write_completion_manifest(self) -> None:
        write_json(
            self.completion_manifest,
            {
                "schema_id": "W7TP_GLOBAL_SUCCESSOR_REVIEW_COMPLETION_MANIFEST_V1",
                "files": {name: sha(self.completion / name) for name in COMPLETION_DOCS},
            },
        )

    def _write_request(self) -> None:
        package_map = {
            key: (self.candidate_rel / name).as_posix()
            for key, name in reviewer.GLOBAL_REQUIRED_PACKAGE_FILES.items()
        }
        request = {
            "schema_version": reviewer.GLOBAL_REQUEST_SCHEMA_VERSION,
            "packet_type": "TOTAL_FIELD_SUCCESSOR_REBIND_REVIEW_REQUEST",
            "review_scope": reviewer.GLOBAL_REVIEW_SCOPE,
            "request_id": "request:T007:G2:SIDECAR:UNIT",
            "run_id": self.run_id,
            "task_id": "T-007",
            "canonical_ref": self.pointer_ref,
            "predecessor_pointer_sha256": self.pointer_sha,
            "predecessor_version": "2.1",
            "successor_version": "2.3",
            "candidate_root": self.candidate_rel.as_posix(),
            "manifest_sha256": sha(self.root_manifest),
            "package_bindings": {
                key: {"ref": ref, "sha256": sha(self.root / ref)}
                for key, ref in package_map.items()
            },
            "live_bindings": {
                "current_field": {"ref": self.field_ref, "sha256": self.field_sha},
                "current_field_router": {"ref": self.router_ref, "sha256": self.router_sha},
                "total_field_authority": {"ref": self.authority_ref, "sha256": self.authority_sha},
            },
            "dynamic_context": self.dynamic_context,
            "nonce": "nonce:sha256:" + "b" * 64,
            "created_at": reviewer.utc_text(self.now),
            "expires_at": reviewer.utc_text(self.now + timedelta(minutes=5)),
            "replay_guard": {
                "single_use": True,
                "domain": "T007_G2_SIDECAR_UNIT",
                "ledger_ref": "test:ledger",
                "on_replay": reviewer.DECISION_HOLD,
            },
            "authority_pointer_ref": self.authority_ref,
            "authority_pointer_sha256": self.authority_sha,
            "founder_authorization_ref": self.founder_ref,
            "founder_authorization_sha256": sha(self.root / self.founder_ref),
            "requested_decision": reviewer.DECISION_APPROVED,
            "contract_mode": "CANDIDATE_CONTRACT_ONLY",
            "request_self_hash_algorithm": reviewer.REQUEST_SELF_HASH_ALGORITHM,
            "non_execution_assertions": {field: False for field in reviewer.NON_EXECUTION_FIELDS},
        }
        request["request_self_sha256"] = reviewer.sha256_bytes(
            reviewer.canonical_json_bytes(request)
        )
        write_json(self.request_path, request)

    def _write_atom(self) -> None:
        self.atom = {
            "id": self.record_id,
            "record_sha256": self.record_sha,
            "time_slot": int(self.now.timestamp()),
            "payload": {
                "knowledge_type": "OBSERVED_TASK_STATE_COORDINATE",
                "state": "TASK_STATE_SNAPSHOT_INDEXED",
                "D1_INTENT": {"task_ref": "task:T-007"},
                "D2_STATE": {
                    "current": "DOING",
                    "snapshot_sha256": "1" * 64,
                },
                "D3_COORDINATE": {
                    "git_branch": "codex/current-live-state-consolidation-20260915",
                    "support_native_adi_packet_sha256": "2" * 64,
                },
                "D4_EVIDENCE": {
                    "task_state_sha256": "3" * 64,
                    "selected_actions_sha256": "4" * 64,
                    "checkpoint_sha256": "5" * 64,
                    "selected_action_refs": ["A-T007-TEST"],
                },
                "D5_EXECUTION": {
                    "reconstruction_scope": "LOCAL_TASK_STATE_ONLY",
                    "task_dirty_zero_required": True,
                },
                "D6_GST": {
                    "packet_contract": "ORIGIN_STATE_MINIMUM_PACKET",
                    "reconstruction": "LOCAL_VOLATILE_ON_PULL",
                    "rule_body_location": "LOCAL_ONLY",
                    "rule_ref": "local-rule:w7tp-task-state-ledger-reconstruction/v1",
                    "compression": False,
                    "differential": False,
                },
                "D7_RISK": {
                    "source_hash_drift": "FAIL_CLOSED",
                    "missing_action_ref": "FAIL_CLOSED",
                    "missing_adi_record": "FAIL_CLOSED",
                },
                "D8_AUTHORITY": {
                    "candidate_only": True,
                    "canonical": False,
                    "formal_effect_authority": "LOCAL_TOTAL_FIELD",
                    "model_authority": False,
                    "provider_authority": False,
                },
            },
        }

    def _refresh_bindings(self) -> None:
        self._write_root_manifest()
        self._write_field_sidecar()
        self._write_completion_contract()
        self._write_completion_manifest()
        self._write_request()
        self._write_atom()

    def _review(self) -> dict:
        return reviewer.review_once(
            request_path=self.request_path,
            repo_root=self.root,
            now=self.now + timedelta(seconds=30),
            test_mode=True,
            tracked_checker=lambda _: True,
            native_adi_loader=lambda _: self.atom,
        )

    def _consumer(self, consumer_ref: str) -> dict:
        matrix = self._load(self.candidate / ROOT_DOCS[3])
        return next(item for item in matrix["consumers"] if item["path"] == consumer_ref)

    def test_full_sidecar_postimages_skills_and_global_downstream_receipt_pass(self) -> None:
        result = self._review()
        self.assertEqual(result["decision"], reviewer.DECISION_APPROVED)
        self.assertFalse(result["formal"])
        self.assertTrue(all(value == "PASS" for value in result["receipt_document"]["checks"].values()))

        decision_path = self.root / "decision.json"
        receipt_path = self.root / "receipt.json"
        write_json(decision_path, result["decision_document"])
        write_json(receipt_path, result["receipt_document"])
        seal = sealer.create_seal(
            manifest_path=self.root_manifest,
            manifest_sha256=sha(self.root_manifest),
            decision_path=decision_path,
            receipt_path=receipt_path,
            authority_pointer_path=self.root / self.authority_ref,
            authority_pointer_sha256=self.authority_sha,
            repo_root=self.root,
            now=self.now + timedelta(minutes=1),
            test_mode=True,
            tracked_checker=lambda _: True,
        )
        self.assertEqual(seal["seal_state"], "TEST_SEAL_ONLY")

    def test_wrong_sidecar_successor_version_is_rejected(self) -> None:
        contract = self._load(self.contract_sidecar)
        contract["version_transition"]["to"] = "2.2"
        write_json(self.contract_sidecar, contract)
        self._refresh_bindings()
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_G2_COMPLETION_CONTRACT_BINDING"])

    def test_expired_request_evidence_holds(self) -> None:
        request = self._load(self.request_path)
        request["created_at"] = reviewer.utc_text(self.now - timedelta(minutes=10))
        request["expires_at"] = reviewer.utc_text(self.now - timedelta(minutes=5))
        write_json(self.request_path, request)
        self._resign_request()
        result = self._review()
        self.assertEqual(result["reason_codes"], ["HOLD_REQUEST_EXPIRED"])

    def test_missing_consumer_postimage_evidence_is_rejected(self) -> None:
        matrix = self._load(self.candidate / ROOT_DOCS[3])
        matrix["consumers"][0].pop("postimage_sha256", None)
        write_json(self.candidate / ROOT_DOCS[3], matrix)
        self._refresh_bindings()
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_CONSUMER_POSTIMAGE_EVIDENCE_MISSING"])

    def test_consumer_postimage_path_mismatch_is_rejected(self) -> None:
        matrix = self._load(self.candidate / ROOT_DOCS[3])
        item = next(row for row in matrix["consumers"] if row["path"] == "tools/d8_guard_eval.py")
        item["postimage_ref"] = "tools/total_field/w7tp_intent_field_suite/edge_queue.py"
        write_json(self.candidate / ROOT_DOCS[3], matrix)
        self._refresh_bindings()
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_CONSUMER_POSTIMAGE_PATH_MISMATCH"])

    def test_declared_postimage_hash_mismatch_is_rejected(self) -> None:
        matrix = self._load(self.candidate / ROOT_DOCS[3])
        item = next(row for row in matrix["consumers"] if row["path"] == "tools/d8_guard_eval.py")
        item["postimage_sha256"] = "f" * 64
        write_json(self.candidate / ROOT_DOCS[3], matrix)
        self._refresh_bindings()
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_CONSUMER_POSTIMAGE_HASH_DRIFT"])

    def test_missing_router_field_preimage_is_rejected(self) -> None:
        field = self._load(self.field_sidecar)
        field["predecessors"] = [field["predecessors"][1]]
        write_json(self.field_sidecar, field)
        self._refresh_bindings()
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_G2_CURRENT_FIELD_SIDECAR_SEMANTICS"])

    def test_missing_skill_source_is_rejected(self) -> None:
        missing = self.root / "capabilities/w7tp-test-source/SKILL.md"
        missing.unlink()
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_G2_SKILL_SCOPE_MISMATCH"])

    def test_new_unbound_skill_source_is_rejected(self) -> None:
        extra = self.root / "capabilities/w7tp-test-extra/SKILL.md"
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text(
            "---\nname: w7tp-test-extra\ndescription: extra\n---\n",
            encoding="utf-8",
        )
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_G2_SKILL_SCOPE_MISMATCH"])

    def test_unisolated_old_d6_d7_active_semantics_are_rejected(self) -> None:
        consumer_ref = "tools/d8_guard_eval.py"
        postimage = self.root / consumer_ref
        postimage.write_text(
            postimage.read_text(encoding="utf-8") + "D6 Sovereign Privacy Field\n",
            encoding="utf-8",
        )
        matrix = self._load(self.candidate / ROOT_DOCS[3])
        item = next(row for row in matrix["consumers"] if row["path"] == consumer_ref)
        item["postimage_sha256"] = sha(postimage)
        write_json(self.candidate / ROOT_DOCS[3], matrix)
        self._refresh_bindings()
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_CONSUMER_FORBIDDEN_CONTENT_PRESENT"])

    def test_content_change_cannot_reuse_old_downstream_receipt(self) -> None:
        consumer_ref = "tools/d8_guard_eval.py"
        postimage = self.root / consumer_ref
        postimage.write_text(
            postimage.read_text(encoding="utf-8") + "SAFE_REFACTOR = True\n",
            encoding="utf-8",
        )
        matrix = self._load(self.candidate / ROOT_DOCS[3])
        item = next(row for row in matrix["consumers"] if row["path"] == consumer_ref)
        item["postimage_sha256"] = sha(postimage)
        write_json(self.candidate / ROOT_DOCS[3], matrix)
        self._refresh_bindings()
        result = self._review()
        self.assertEqual(
            result["reason_codes"],
            ["REJECT_G2_DOWNSTREAM_ARTIFACT_BINDING_MISMATCH"],
        )

    def test_local_native_lookup_receipt_cannot_masquerade_as_global_review(self) -> None:
        receipt = self._load(self.downstream_receipt)
        receipt["schema_id"] = "W7TP_NATIVE_LOOKUP_RECEIPT_V1"
        receipt["scope"] = "LOCAL_NATIVE_LOOKUP"
        write_json(self.downstream_receipt, receipt)
        self._refresh_bindings()
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_G2_GLOBAL_DOWNSTREAM_RECEIPT_SCOPE"])

    def test_task_state_dynamic_context_missing_d6_is_rejected(self) -> None:
        self.atom["payload"].pop("D6_GST")
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_NATIVE_ADI_DYNAMIC_CONTEXT_SCOPE"])

    def test_task_state_dynamic_context_differential_true_is_rejected(self) -> None:
        self.atom["payload"]["D6_GST"]["differential"] = True
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_NATIVE_ADI_DYNAMIC_CONTEXT_SCOPE"])

    def test_difference_analysis_must_remain_analysis_not_transmission(self) -> None:
        field = self._load(self.field_sidecar)
        field["coupled_constraints"]["difference_analysis"] = "differential transmission"
        write_json(self.field_sidecar, field)
        self._refresh_bindings()
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_G2_CURRENT_FIELD_SIDECAR_SEMANTICS"])

    def test_future_native_adi_timestamp_beyond_clock_skew_holds(self) -> None:
        self.atom["time_slot"] = int((self.now + timedelta(minutes=2)).timestamp())
        result = self._review()
        self.assertEqual(result["reason_codes"], ["HOLD_NATIVE_ADI_DYNAMIC_CONTEXT_NOT_FRESH"])

    def test_wrong_root_instead_of_completion_sidecar_is_rejected(self) -> None:
        request = self._load(self.request_path)
        root_contract_ref = (self.candidate_rel / ROOT_DOCS[1]).as_posix()
        request["package_bindings"]["successor_contract"] = {
            "ref": root_contract_ref,
            "sha256": sha(self.root / root_contract_ref),
        }
        write_json(self.request_path, request)
        self._resign_request()
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_GLOBAL_PACKAGE_REF_MISMATCH"])

    def test_completion_leaf_drift_without_manifest_refresh_is_rejected(self) -> None:
        regression = self.completion / "REGRESSION_SPEC.md"
        regression.write_text("drifted after manifest\n", encoding="utf-8")
        result = self._review()
        self.assertEqual(result["reason_codes"], ["REJECT_G2_COMPLETION_MANIFEST_HASH_DRIFT"])

    def test_explicit_read_only_legacy_adapter_is_not_an_active_collision(self) -> None:
        legacy = self.root / "tools/total_field/w7tp_canonical_v2_1_legacy_adapter.py"
        self.assertIn("D6 Sovereign Privacy Field", legacy.read_text(encoding="utf-8"))
        self.assertEqual(self._review()["decision"], reviewer.DECISION_APPROVED)


if __name__ == "__main__":
    unittest.main()
