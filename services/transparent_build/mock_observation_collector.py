"""Static observation-pack fixtures for Sister J Transparent Build Mode.

The collector does not inspect directories, ports, Docker, services, files,
environment variables, databases, or network endpoints. It returns synthetic
design-time evidence for downstream redaction and cloud-review formatting.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from typing import Any


DRAFT_SCHEMA_ID = "sister_j.transparent_observation_draft.v0.1"
BLOCKED_SENSITIVE_PATHS = [
    ".env",
    ".env.*",
    "logs/",
    "memory/",
    "memory_zone/",
    "wuchang_memory_vault/",
    "_ollama_memory/",
    "backup_*",
    "private keys",
    "token files",
    "credential files",
]


def _base_pack(scenario: str, stage: str) -> dict[str, Any]:
    pack_id = hashlib.sha256(scenario.encode("utf-8")).hexdigest()[:12]
    return {
        "schema": DRAFT_SCHEMA_ID,
        "pack_id": f"transparent_pack_{pack_id}",
        "observation_mode": "mock_static_input_only",
        "system_role": "Taiji_Hub canonical design workspace with local Sister J observation support",
        "current_stage": stage,
        "directory_map_summary": [
            {
                "name": "docs/design/",
                "role": "design specifications visible for review",
                "status": "design_visible",
            },
            {
                "name": "schemas/",
                "role": "packet and observation contracts visible for review",
                "status": "design_visible",
            },
            {
                "name": "services/transparent_build/",
                "role": "mock-only transparent packet pipeline",
                "status": "prototype_candidate",
            },
            {
                "name": "runtime/reports/",
                "role": "design dry-run report lane only",
                "status": "report_only",
            },
        ],
        "services_status_summary": [
            {"name": "gateway", "status": "mock_not_probed", "basis": "No service probe is allowed in this MVP."},
            {"name": "odoo", "status": "mock_not_probed", "basis": "Production Odoo access is excluded."},
            {"name": "ollama", "status": "mock_not_probed", "basis": "Model service probing is excluded."},
        ],
        "ports_summary": [
            {"name": "gateway_port_candidate", "status": "unknown", "basis": "Port is not inspected in mock mode."},
            {"name": "odoo_port_candidate", "status": "unknown", "basis": "Port is not inspected in mock mode."},
        ],
        "docker_summary": {
            "status": "mock_not_probed",
            "summary": "Container state is intentionally not inspected during transparent-build design.",
        },
        "gateway_summary": {
            "status": "known_design_only",
            "summary": "Gateway is a candidate review surface; transparent build emits advice only and performs no route call.",
        },
        "odoo_boundary_summary": {
            "status": "blocked",
            "summary": "Odoo production data and direct write actions are outside this observation pack boundary.",
        },
        "ollama_models_summary": {
            "status": "mock_not_probed",
            "summary": "Model inventory is not collected in design-time mock mode.",
        },
        "topology_summary": {
            "status": "known_design_only",
            "summary": "Canonical Hub, W7TP Lite contract, and governance boundaries are reportable without live node probing.",
        },
        "known_errors": [],
        "candidate_files": [
            {
                "name": "schemas/transparent_observation_pack.schema.json",
                "role": "observation packet contract",
                "status": "candidate_for_review",
            },
            {
                "name": "services/transparent_build/mock_cloud_review_packet.py",
                "role": "advice-only packet assembler",
                "status": "mock_candidate",
            },
        ],
        "blocked_sensitive_paths": BLOCKED_SENSITIVE_PATHS,
        "open_questions": [],
        "next_recommended_actions": [],
    }


def collect_mock_observation(scenario: str = "design_baseline") -> dict[str, Any]:
    """Return one synthetic observation snapshot without probing local state."""
    if scenario == "design_baseline":
        pack = _base_pack(scenario, "design")
        pack["known_errors"] = [
            {
                "severity": "medium",
                "issue": "No live system status is intentionally collected in design mode.",
                "evidence_basis": "mock collector boundary",
                "handling": "Keep status marked mock_not_probed until a separately approved phase.",
            }
        ]
        pack["open_questions"] = [
            "Should the observation schema become a reviewed cloud-advice contract before any approved adapters exist?"
        ]
        pack["next_recommended_actions"] = [
            {"priority": 1, "action": "Review schema fields and blocked path policy.", "mode": "review_or_plan_only"}
        ]
    elif scenario == "prototype_gap":
        pack = _base_pack(scenario, "prototype")
        pack["known_errors"] = [
            {
                "severity": "high",
                "issue": "Gateway and webhook observation adapters are not defined as redacted plan-only contracts.",
                "evidence_basis": "prototype design gap",
                "handling": "Draft contract and negative tests; do not connect services.",
            }
        ]
        pack["open_questions"] = [
            "Which non-sensitive gateway and webhook fields are minimally useful to cloud review?"
        ]
        pack["next_recommended_actions"] = [
            {"priority": 1, "action": "Specify redacted gateway and webhook observation contracts.", "mode": "review_or_plan_only"},
            {"priority": 2, "action": "Add negative tests for blocked sensitive material.", "mode": "review_or_plan_only"},
        ]
    elif scenario == "audit_blocked":
        pack = _base_pack(scenario, "audit")
        pack["known_errors"] = [
            {
                "severity": "blocked",
                "issue": "Synthetic credential=DEMO_VALUE and member contact sample.person@example.invalid appeared in a proposed observation.",
                "evidence_basis": "synthetic redaction test fixture",
                "handling": "Redact before cloud review and require human boundary review.",
            },
            {
                "severity": "high",
                "issue": "Synthetic Bearer DEMO_TOKEN_VALUE must never pass to a cloud review packet.",
                "evidence_basis": "synthetic redaction test fixture",
                "handling": "Apply redaction and mark packet blocked for human decision.",
            },
        ]
        pack["open_questions"] = [
            "Was the proposed source field allowed, or must the entire observation category remain local?"
        ]
        pack["next_recommended_actions"] = [
            {"priority": 1, "action": "Hold cloud review until redaction result is inspected by a human.", "mode": "review_or_plan_only"}
        ]
    else:
        raise ValueError(f"unknown mock scenario: {scenario}")

    return copy.deepcopy(pack)


def main(argv: list[str]) -> int:
    scenario = argv[0] if argv else "design_baseline"
    print(json.dumps(collect_mock_observation(scenario), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
