"""CLI for the shared W7TP intent-field product layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.total_field.w7tp_field_application_runtime import FieldApplicationError
from tools.total_field.w7tp_core_encoding import build_encoding_registry, explain_code

from .adaptive_cognition import active_policy
from .cafe_pos_interop import (
    DEFAULT_MENU_SNAPSHOT_PATH,
    build_binding_seal_request,
    build_preview_binding_registry,
    load_binding_registry,
    rectify_surface_candidate,
)
from .deployment import ROOT, build_release_bundle, install_release_bundle
from .edge_queue import (
    build_sealed_snapshot,
    enqueue_packet,
    revalidate_queue_file,
)
from .node_inventory import collect_inventory
from .packet_builder import process_intent


SCHEMA_FILES = (
    "schemas/field/founder_identity_gate.schema.json",
    "schemas/field/w7tp_guided_completion.schema.json",
    "schemas/field/w7tp_node_capability.schema.json",
    "schemas/field/w7tp_adaptive_cognition.schema.json",
    "schemas/field/w7tp_cafe_pos_interop_candidate.schema.json",
    "schemas/field/w7tp_cafe_pos_binding_seal.schema.json",
    "schemas/field/w7tp_core_encoding_registry.schema.json",
    "schemas/field/w7tp_deployment_manifest.schema.json",
    "schemas/field/w7tp_natural_person_identity_prefix.schema.json",
    "schemas/field/w7tp_identity_projection.schema.json",
)


def _json_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise FieldApplicationError("INTENT_OBJECT_REQUIRED")
    return parsed


def _release_files() -> list[Path]:
    suite = ROOT / "tools/total_field/w7tp_intent_field_suite"
    files = [
        ROOT / "tools/deploy_w7tp_small_agent_all_nodes.py",
        ROOT / "tools/total_field/w7tp_field_application_runtime.py",
        ROOT / "tools/total_field/founder_variable_cognition_gate.py",
        ROOT / "tools/cloud_proxy/w7tp_openwebui_cloud_proxy.py",
        ROOT / "tools/odoo/configure_google_member_provider.py",
        ROOT / "deploy/systemd/w7tp-intent-field.service",
        ROOT / "manifests/w7tp_small_agent_node_authority_v0_1/node_authority_registry_runtime_minimized.json",
        ROOT / "runtime/total_field/node_container_scope/TOTAL_FIELD_NODE_CONTAINER_MANIFEST_20260624.json",
        ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/controllers/main.py",
        ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/services/account_linking.py",
        ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/services/oauth_config.py",
        ROOT / "scripts/verify/verify_google_member_login_exact_remediation.py",
        ROOT / "scripts/verify/verify_member_oauth_pre_activation_remediations.py",
        ROOT / "tests/test_founder_variable_cognition_gate.py",
        ROOT / "tests/test_google_member_provider_configuration.py",
        ROOT / "tests/test_google_nonprofit_website_review.py",
        ROOT / "tests/test_member_oauth_pre_activation_remediations.py",
        ROOT / "tests/test_cafe_pos_demo.py",
        ROOT / "tests/test_cafe_pos_interop.py",
        ROOT / "tests/test_medical_care_demo.py",
        ROOT / "tests/test_w7tp_field_application_runtime.py",
        ROOT / "tests/test_w7tp_intent_field_suite.py",
        ROOT / "tests/test_w7tp_natural_person_identity_prefix.py",
        ROOT / "tests/test_w7tp_identity_projection_landing.py",
        ROOT / "deploy/caddy/w7tp-odoo-identity-projection.caddy",
        ROOT / "tests/test_wuchang_nonprofit_homepage_boundaries.py",
        ROOT / "web/index.html",
        ROOT / "web/method/index.html",
        ROOT / "web/medical_care_demo/index.html",
        ROOT / "web/assets/medical-care-demo.css",
        ROOT / "web/assets/medical-care-demo.js",
        ROOT / "web/assets/wuchang-site-design.css",
        ROOT / "web/sitemap.xml",
        ROOT / "web/governance/index.html",
        ROOT / "web/property_management/index.html",
        ROOT / "web/pos_promo_sandbox/index.html",
        ROOT / "web/assets/cafe-pos-menu-data.js",
        ROOT / "web/assets/cafe-pos-staff-flow.js",
        ROOT / "web/assets/cafe-pos-ai-intent.js",
        ROOT / "web/assets/cafe-pos-demo.css",
        ROOT / "web/assets/cafe-pos-demo.js",
        ROOT / "web/total_field_review/index.html",
        ROOT / "web/total_field_review/envelope.html",
        ROOT / "scripts/verify/verify_google_nonprofit_website.py",
        ROOT / "scripts/verify/verify_medical_care_browser_product.py",
        ROOT / "scripts/verify/verify_cafe_pos_browser_product.py",
        ROOT / "scripts/verify/verify_shared_intent_browser_product.py",
        ROOT / "scripts/verify/verify_wuchang_website_quality.py",
        ROOT / "scripts/verify/verify_wuchang_public_site_design.py",
        ROOT / "tools/total_field/quickclick_menu_snapshot.py",
        ROOT / "tools/total_field/cafe_pos_local_llm_acceptance.py",
        ROOT / "tools/total_field/w7tp_bundle_installer.py",
        ROOT / "tools/total_field/w7tp_core_encoding.py",
        ROOT / "docs/operations/CAFE_POS_HUMAN_AI_DESIGN_BENCHMARK_20260716.md",
        ROOT / "docs/total_field/W7TP_CORE_FIELD_ENCODING_MANAGEMENT_V1.md",
        ROOT / "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md",
        ROOT / "docs/total_field/W7TP_FOUNDER_IDENTITY_ROOT_AND_VARIABLE_COGNITION_PACKAGE_CANONICAL.md",
        ROOT / "docs/total_field/W7TP_MEMBER_AI_LLM_PREFIX_POLICY.md",
        ROOT / "configs/w7tp_member_llm_prefix_policy.example.json",
        ROOT / "runtime/total_field/shared_intent_field/W7TP_SHARED_8D_CAFE_POS_20260716T175836Z/cloud-menu-source/quickclick-menu-snapshot.json",
        ROOT / "runtime/total_field/shared_intent_field/W7TP_SHARED_8D_CAFE_POS_20260716T175836Z/cloud-menu-source/README.md",
    ]
    files.extend(path for path in suite.glob("*.py") if path.is_file())
    files.extend(ROOT / relative for relative in SCHEMA_FILES)
    files.extend(
        [
            ROOT / "runtime/total_field/secondary_cloud/scenario_route_table.json",
            ROOT / "runtime/total_field/secondary_cloud/capability_registry.json",
        ]
    )
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shared W7TP 8D intent-field suite")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("profile")
    build.add_argument("intent_json")
    build.add_argument("--interactive", action="store_true")
    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("--probe", action="store_true")
    subparsers.add_parser("policy")
    release = subparsers.add_parser("release")
    release.add_argument("--run-id", required=True)
    release.add_argument("--output", type=Path, required=True)
    subparsers.add_parser("snapshot")
    queue = subparsers.add_parser("edge-queue")
    queue.add_argument("profile")
    queue.add_argument("intent_json")
    queue.add_argument("--node-id", required=True)
    queue.add_argument("--queue", type=Path, required=True)
    revalidate = subparsers.add_parser("edge-revalidate")
    revalidate.add_argument("--queue", type=Path, required=True)
    install = subparsers.add_parser("install")
    install.add_argument("--artifact", type=Path, required=True)
    install.add_argument("--manifest", type=Path, required=True)
    install.add_argument("--install-root", type=Path, required=True)
    cafe_bindings = subparsers.add_parser("cafe-pos-bindings")
    cafe_bindings.add_argument("surface", choices=("ODOO_HUMAN", "ADI_AI"))
    cafe_bindings.add_argument(
        "--snapshot", type=Path, default=DEFAULT_MENU_SNAPSHOT_PATH
    )
    cafe_rectify = subparsers.add_parser("cafe-pos-rectify")
    cafe_rectify.add_argument("surface", choices=("ODOO_HUMAN", "ADI_AI"))
    cafe_rectify.add_argument("candidate_json")
    cafe_rectify.add_argument("--bindings", type=Path)
    cafe_rectify.add_argument(
        "--snapshot", type=Path, default=DEFAULT_MENU_SNAPSHOT_PATH
    )
    cafe_seal_request = subparsers.add_parser("cafe-pos-binding-seal-request")
    cafe_seal_request.add_argument("--bindings", type=Path, required=True)
    cafe_seal_request.add_argument(
        "--snapshot", type=Path, default=DEFAULT_MENU_SNAPSHOT_PATH
    )
    subparsers.add_parser("encoding-registry")
    encoding_explain = subparsers.add_parser("encoding-explain")
    encoding_explain.add_argument("code")
    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            intent = _json_object(args.intent_json)
            result = process_intent(args.profile, intent, execution_metadata={"surface": "CLI"})
            while args.interactive and result.get("state") == "NEEDS_USER_GUIDED_COMPLETION":
                question = result["question"]
                answer = input(f"{question['prompt']} ").strip()
                result = process_intent(
                    args.profile,
                    intent,
                    state_id=result["state_id"],
                    question_id=question["question_id"],
                    answer=answer,
                    execution_metadata={"surface": "INTERACTIVE_CLI"},
                )
                intent[question["field"]] = answer
        elif args.command == "inventory":
            result = collect_inventory(probe=args.probe)
        elif args.command == "policy":
            result = active_policy()
        elif args.command == "release":
            result = build_release_bundle(_release_files(), args.output, args.run_id)
        elif args.command == "snapshot":
            result = build_sealed_snapshot()
        elif args.command == "edge-queue":
            snapshot = build_sealed_snapshot()
            packet = process_intent(
                args.profile,
                _json_object(args.intent_json),
                execution_metadata={"surface": "OFFLINE_EDGE_CLI"},
            )
            result = enqueue_packet(
                args.queue,
                packet,
                snapshot,
                node_id=args.node_id,
            )
        elif args.command == "edge-revalidate":
            result = revalidate_queue_file(
                args.queue,
                build_sealed_snapshot(),
            )
        elif args.command == "install":
            result = install_release_bundle(
                args.artifact,
                args.manifest,
                args.install_root,
            )
        elif args.command == "cafe-pos-bindings":
            result = build_preview_binding_registry(
                args.surface,
                snapshot_path=args.snapshot,
            )
        elif args.command == "cafe-pos-rectify":
            result = rectify_surface_candidate(
                args.surface,
                _json_object(args.candidate_json),
                binding_registry=(
                    load_binding_registry(args.bindings) if args.bindings else None
                ),
                snapshot_path=args.snapshot,
            )
        elif args.command == "cafe-pos-binding-seal-request":
            result = build_binding_seal_request(
                load_binding_registry(args.bindings),
                snapshot_path=args.snapshot,
            )
        elif args.command == "encoding-registry":
            result = build_encoding_registry()
        else:
            result = explain_code(args.code)
    except (FieldApplicationError, json.JSONDecodeError) as exc:
        reason = exc.reason_code if isinstance(exc, FieldApplicationError) else "INTENT_JSON_INVALID"
        path = exc.path if isinstance(exc, FieldApplicationError) else "$"
        print(json.dumps({"state": "HOLD", "reason_code": reason, "path": path}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
