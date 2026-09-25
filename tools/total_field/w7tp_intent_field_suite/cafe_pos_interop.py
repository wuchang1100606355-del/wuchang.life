"""Read-only Odoo/ADI interoperability for the shared CAFE_POS profile.

The two input surfaces remain separate for people and local-device AI, while
the rectified semantic candidate is source-bound to the same QuickClick menu.
No Odoo record, ADI internal rule, order, payment, or database write is made.
"""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from tools.total_field.quickclick_menu_snapshot import (
    build_web_data,
    source_option_ref,
    source_question_ref,
)
from tools.total_field.founder_variable_cognition_gate import (
    ALLOW,
    authorize_total_field_change,
)
from tools.total_field.w7tp_field_application_runtime import (
    CAPABILITY_REGISTRY_PATH,
    SCENARIO_ROUTE_TABLE_PATH,
    FieldApplicationError,
)
from tools.total_field.w7tp_core_encoding import (
    ENCODING_REGISTRY_VERSION,
    build_encoding_registry,
    build_surface_binding_ref,
)

from .canonical_hash import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MENU_SNAPSHOT_PATH = (
    ROOT
    / "runtime/total_field/shared_intent_field/"
    "W7TP_SHARED_8D_CAFE_POS_20260716T175836Z/"
    "cloud-menu-source/quickclick-menu-snapshot.json"
)
SUPPORTED_SURFACES = ("ODOO_HUMAN", "ADI_AI")
PREVIEW_BINDING_STATE = "DERIVED_NON_AUTHORITATIVE_PREVIEW"
PRODUCTION_BINDING_STATE = "PROVISIONED_VERIFIED_READ_ONLY_BINDINGS"
SEAL_REQUEST_STATE = "NEEDS_FOUNDER_DUAL_ROOT_AUTHORIZATION"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_object(path: Path, reason_code: str) -> dict[str, Any]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise FieldApplicationError(reason_code) from exc
    if not isinstance(value, dict):
        raise FieldApplicationError(reason_code)
    return value


def _surface(surface: str) -> str:
    normalized = str(surface).strip().upper()
    if normalized not in SUPPORTED_SURFACES:
        raise FieldApplicationError("CAFE_POS_SURFACE_NOT_SUPPORTED", "$.surface")
    return normalized


def _menu_contract(snapshot_path: Path) -> dict[str, Any]:
    snapshot_path = Path(snapshot_path)
    snapshot = _json_object(snapshot_path, "CAFE_POS_MENU_SNAPSHOT_INVALID")
    try:
        web_data = build_web_data(snapshot)
    except (KeyError, TypeError, ValueError) as exc:
        raise FieldApplicationError("CAFE_POS_MENU_SNAPSHOT_INVALID") from exc
    products = {product["sourceRef"]: product for product in web_data["products"]}
    questions: dict[str, dict[str, Any]] = {}
    options: dict[str, dict[str, Any]] = {}
    menu_id = web_data["source"]["id"]
    for group in web_data["optionGroups"]:
        for question in group["questions"]:
            question_ref = source_question_ref(menu_id, question["id"])
            if question_ref in questions:
                raise FieldApplicationError("CAFE_POS_SOURCE_QUESTION_DUPLICATE")
            questions[question_ref] = {
                **question,
                "group_id": group["id"],
                "source_ref": question_ref,
            }
            for option in question["options"]:
                option_ref = source_option_ref(menu_id, option["id"])
                if option_ref in options:
                    raise FieldApplicationError("CAFE_POS_SOURCE_OPTION_DUPLICATE")
                options[option_ref] = {
                    **option,
                    "group_id": group["id"],
                    "question_ref": question_ref,
                    "source_ref": option_ref,
                }
    return {
        "snapshot": snapshot,
        "snapshot_path": snapshot_path,
        "snapshot_file_sha256": _file_sha256(snapshot_path),
        "web_data": web_data,
        "products": products,
        "questions": questions,
        "options": options,
    }


def _authority_sources() -> dict[str, Any]:
    return {
        "scenario_route_table": {
            "path": SCENARIO_ROUTE_TABLE_PATH.relative_to(ROOT).as_posix(),
            "sha256": _file_sha256(SCENARIO_ROUTE_TABLE_PATH),
        },
        "capability_registry": {
            "path": CAPABILITY_REGISTRY_PATH.relative_to(ROOT).as_posix(),
            "sha256": _file_sha256(CAPABILITY_REGISTRY_PATH),
        },
    }


def build_preview_binding_registry(
    surface: str,
    *,
    snapshot_path: Path = DEFAULT_MENU_SNAPSHOT_PATH,
) -> dict[str, Any]:
    """Build a deterministic non-authoritative binding file for one surface."""

    surface = _surface(surface)
    contract = _menu_contract(snapshot_path)
    web_data = contract["web_data"]
    encoding_registry = build_encoding_registry()
    registry: dict[str, Any] = {
        "schema_version": "W7TP-CAFE-POS-SURFACE-BINDINGS/1.0",
        "surface": surface,
        "state": PREVIEW_BINDING_STATE,
        "production_bindings": False,
        "source_snapshot": {
            "menu_id": web_data["source"]["id"],
            "source_export_sha256": web_data["source"]["sha256"],
            "snapshot_file_sha256": contract["snapshot_file_sha256"],
            "authority_state": web_data["source"]["authorityState"],
        },
        "authority_sources": _authority_sources(),
        "encoding_registry": {
            "version": ENCODING_REGISTRY_VERSION,
            "content_sha256": encoding_registry["content_sha256"],
        },
        "product_bindings": [
            {
                "surface_ref": build_surface_binding_ref(
                    surface, "PRODUCT", source_ref
                ),
                "source_ref": source_ref,
            }
            for source_ref in sorted(contract["products"])
        ],
        "question_bindings": [
            {
                "surface_ref": build_surface_binding_ref(
                    surface, "QUESTION", source_ref
                ),
                "source_ref": source_ref,
            }
            for source_ref in sorted(contract["questions"])
        ],
        "option_bindings": [
            {
                "surface_ref": build_surface_binding_ref(
                    surface, "OPTION", source_ref
                ),
                "source_ref": source_ref,
            }
            for source_ref in sorted(contract["options"])
        ],
        "public_boundary": "OPAQUE_REF_ONLY",
        "adi_internal_rules_disclosed": False,
        "side_effects": {
            "db_write": False,
            "odoo_write": False,
            "formal_pos_order": False,
            "payment_capture": False,
            "network_call": False,
        },
    }
    registry["content_sha256"] = canonical_sha256(registry)
    return registry


def load_binding_registry(path: Path) -> dict[str, Any]:
    return _json_object(path, "CAFE_POS_BINDING_REGISTRY_INVALID")


def _binding_map(
    registry: Mapping[str, Any],
    field: str,
    expected_sources: set[str],
    surface: str,
    state: str,
) -> dict[str, str]:
    records = registry.get(field)
    if not isinstance(records, list) or len(records) != len(expected_sources):
        raise FieldApplicationError("CAFE_POS_BINDING_COVERAGE_INVALID", f"$.{field}")
    entity_type = {
        "product_bindings": "PRODUCT",
        "question_bindings": "QUESTION",
        "option_bindings": "OPTION",
    }[field]
    if surface == "ODOO_HUMAN":
        reference_class = (
            "PREVIEW_REF" if state == PREVIEW_BINDING_STATE else "REF"
        )
        prefix = f"ODOO_{entity_type}_{reference_class}:v1:sha256:"
    else:
        prefix = f"ADI_5D_{entity_type}_REF:v1:sha256:"
    by_surface: dict[str, str] = {}
    source_refs: list[str] = []
    for index, record in enumerate(records):
        path = f"$.{field}[{index}]"
        if not isinstance(record, dict) or set(record) != {"surface_ref", "source_ref"}:
            raise FieldApplicationError("CAFE_POS_BINDING_RECORD_INVALID", path)
        surface_ref = record["surface_ref"]
        source_ref = record["source_ref"]
        if (
            not isinstance(surface_ref, str)
            or not surface_ref.startswith(prefix)
            or re.fullmatch(re.escape(prefix) + r"[a-f0-9]{64}", surface_ref) is None
        ):
            raise FieldApplicationError("CAFE_POS_SURFACE_REF_INVALID", f"{path}.surface_ref")
        if not isinstance(source_ref, str) or source_ref not in expected_sources:
            raise FieldApplicationError("CAFE_POS_SOURCE_REF_INVALID", f"{path}.source_ref")
        if surface_ref in by_surface:
            raise FieldApplicationError("CAFE_POS_SURFACE_REF_DUPLICATE", f"{path}.surface_ref")
        by_surface[surface_ref] = source_ref
        source_refs.append(source_ref)
    if set(source_refs) != expected_sources or len(set(source_refs)) != len(source_refs):
        raise FieldApplicationError("CAFE_POS_BINDING_COVERAGE_INVALID", f"$.{field}")
    return by_surface


def _validate_registry(
    registry: Mapping[str, Any],
    surface: str,
    contract: Mapping[str, Any],
    *,
    allow_unsealed_production: bool = False,
) -> dict[str, dict[str, str]]:
    expected_keys = {
        "schema_version",
        "surface",
        "state",
        "production_bindings",
        "source_snapshot",
        "authority_sources",
        "encoding_registry",
        "product_bindings",
        "question_bindings",
        "option_bindings",
        "public_boundary",
        "adi_internal_rules_disclosed",
        "side_effects",
        "content_sha256",
    }
    if not isinstance(registry, Mapping) or set(registry) != expected_keys:
        raise FieldApplicationError("CAFE_POS_BINDING_REGISTRY_INVALID")
    if registry["schema_version"] != "W7TP-CAFE-POS-SURFACE-BINDINGS/1.0":
        raise FieldApplicationError("CAFE_POS_BINDING_SCHEMA_INVALID")
    if registry["surface"] != surface:
        raise FieldApplicationError("CAFE_POS_BINDING_SURFACE_MISMATCH")
    state = registry["state"]
    if state not in {PREVIEW_BINDING_STATE, PRODUCTION_BINDING_STATE}:
        raise FieldApplicationError("CAFE_POS_BINDING_STATE_INVALID")
    if registry["production_bindings"] is not (state == PRODUCTION_BINDING_STATE):
        raise FieldApplicationError("CAFE_POS_BINDING_STATE_INVALID")
    if state == PRODUCTION_BINDING_STATE and not allow_unsealed_production:
        raise FieldApplicationError("CAFE_POS_PRODUCTION_BINDING_SEAL_NOT_VERIFIED")
    web_data = contract["web_data"]
    expected_snapshot = {
        "menu_id": web_data["source"]["id"],
        "source_export_sha256": web_data["source"]["sha256"],
        "snapshot_file_sha256": contract["snapshot_file_sha256"],
        "authority_state": web_data["source"]["authorityState"],
    }
    if registry["source_snapshot"] != expected_snapshot:
        raise FieldApplicationError("CAFE_POS_BINDING_SNAPSHOT_MISMATCH")
    if registry["authority_sources"] != _authority_sources():
        raise FieldApplicationError("CAFE_POS_BINDING_AUTHORITY_MISMATCH")
    encoding_registry = build_encoding_registry()
    if registry["encoding_registry"] != {
        "version": ENCODING_REGISTRY_VERSION,
        "content_sha256": encoding_registry["content_sha256"],
    }:
        raise FieldApplicationError("CAFE_POS_ENCODING_REGISTRY_MISMATCH")
    if registry["public_boundary"] != "OPAQUE_REF_ONLY":
        raise FieldApplicationError("CAFE_POS_BINDING_PUBLIC_BOUNDARY_INVALID")
    if registry["adi_internal_rules_disclosed"] is not False:
        raise FieldApplicationError("CAFE_POS_ADI_RULE_DISCLOSURE_BLOCKED")
    if registry["side_effects"] != {
        "db_write": False,
        "odoo_write": False,
        "formal_pos_order": False,
        "payment_capture": False,
        "network_call": False,
    }:
        raise FieldApplicationError("CAFE_POS_BINDING_SIDE_EFFECT_INVALID")
    unsigned = dict(registry)
    supplied_hash = unsigned.pop("content_sha256")
    if supplied_hash != canonical_sha256(unsigned):
        raise FieldApplicationError("CAFE_POS_BINDING_SHA256_MISMATCH")
    maps = {
        "products": _binding_map(
            registry,
            "product_bindings",
            set(contract["products"]),
            surface,
            state,
        ),
        "questions": _binding_map(
            registry,
            "question_bindings",
            set(contract["questions"]),
            surface,
            state,
        ),
        "options": _binding_map(
            registry,
            "option_bindings",
            set(contract["options"]),
            surface,
            state,
        ),
    }
    all_surface_refs = [ref for mapping in maps.values() for ref in mapping]
    if len(all_surface_refs) != len(set(all_surface_refs)):
        raise FieldApplicationError("CAFE_POS_SURFACE_REF_DUPLICATE")
    return maps


def build_binding_seal_request(
    binding_registry: Mapping[str, Any],
    *,
    snapshot_path: Path = DEFAULT_MENU_SNAPSHOT_PATH,
) -> dict[str, Any]:
    """Build a content-addressed request for the existing Founder dual-root gate."""

    if not isinstance(binding_registry, Mapping):
        raise FieldApplicationError("CAFE_POS_BINDING_REGISTRY_INVALID")
    surface = _surface(binding_registry.get("surface", ""))
    contract = _menu_contract(snapshot_path)
    _validate_registry(
        binding_registry,
        surface,
        contract,
        allow_unsealed_production=True,
    )
    if binding_registry["state"] != PRODUCTION_BINDING_STATE:
        raise FieldApplicationError("CAFE_POS_PRODUCTION_BINDING_REGISTRY_REQUIRED")
    request: dict[str, Any] = {
        "schema_version": "W7TP-CAFE-POS-BINDING-SEAL-REQUEST/1.0",
        "state": SEAL_REQUEST_STATE,
        "profile": "CAFE_POS",
        "surface": surface,
        "binding_registry": {
            "state": binding_registry["state"],
            "content_sha256": binding_registry["content_sha256"],
            "product_count": len(binding_registry["product_bindings"]),
            "question_count": len(binding_registry["question_bindings"]),
            "option_count": len(binding_registry["option_bindings"]),
        },
        "source_snapshot": dict(binding_registry["source_snapshot"]),
        "authority_sources": dict(binding_registry["authority_sources"]),
        "encoding_registry": dict(binding_registry["encoding_registry"]),
        "requested_effect": "ENABLE_VERIFIED_READ_ONLY_BINDINGS_FOR_L3_RECTIFICATION",
        "governance_authority": "VERIFIED_FOUNDER_DUAL_ROOT_ONLY",
        "D8": {
            "decision": "PENDING_FOUNDER_TOTAL_FIELD_SEAL",
            "formal_execution_authority": False,
        },
        "candidate_only": True,
        "side_effects": {
            "secret_read": False,
            "db_write": False,
            "odoo_write": False,
            "adi_write": False,
            "formal_pos_order": False,
            "payment_capture": False,
            "network_call": False,
        },
    }
    request["content_sha256"] = canonical_sha256(request)
    return request


def evaluate_binding_seal_request(
    binding_registry: Mapping[str, Any],
    *,
    founder_identity_request: Mapping[str, Any] | None = None,
    sealed_founder_root: Mapping[str, Any] | None = None,
    snapshot_path: Path = DEFAULT_MENU_SNAPSHOT_PATH,
) -> dict[str, Any]:
    """Evaluate, but never persist, a production binding seal request."""

    request = build_binding_seal_request(
        binding_registry,
        snapshot_path=snapshot_path,
    )
    identity_request = dict(founder_identity_request or {})
    authorization = authorize_total_field_change(
        "FOUNDER",
        identity_request,
        sealed_founder_root,
    )
    identity_gate = authorization["identity_gate"]
    decision = identity_gate["decision"]
    state_by_decision = {
        "ALLOW": "VERIFIED_TOTAL_FIELD_BINDING_SEAL",
        "HOLD": "HOLD_FOUNDER_ROOT_NOT_PROVISIONED_OR_INVALID",
        "BLOCK": "BLOCK_FOUNDER_DUAL_ROOT_VERIFICATION_FAILED",
    }
    command_ref = identity_request.get("founder_command_ref")
    command_ref_sha256 = (
        canonical_sha256(str(command_ref))
        if isinstance(command_ref, str) and command_ref.strip()
        else None
    )
    seal_payload = {
        "seal_request_content_sha256": request["content_sha256"],
        "binding_registry_content_sha256": request["binding_registry"]
        ["content_sha256"],
        "principal_ref": identity_gate["principal_ref"],
        "founder_command_ref_sha256": command_ref_sha256,
        "governance_authority": "VERIFIED_FOUNDER_DUAL_ROOT_ONLY",
    }
    binding_seal_ref = (
        f"total-field-binding-seal-sha256:{canonical_sha256(seal_payload)}"
        if decision == ALLOW
        else None
    )
    result: dict[str, Any] = {
        "schema_version": "W7TP-CAFE-POS-BINDING-SEAL-EVALUATION/1.0",
        "state": state_by_decision[decision],
        "decision": decision,
        "reason_code": identity_gate["reason_code"],
        "profile": "CAFE_POS",
        "surface": request["surface"],
        "seal_request_content_sha256": request["content_sha256"],
        "binding_registry_content_sha256": request["binding_registry"]
        ["content_sha256"],
        "identity_gate": {
            "decision": decision,
            "reason_code": identity_gate["reason_code"],
            "checks": dict(identity_gate["checks"]),
            "principal_ref": identity_gate["principal_ref"],
        },
        "founder_command_ref_sha256": command_ref_sha256,
        "binding_seal_ref": binding_seal_ref,
        "candidate_only": True,
        "formal_execution_authority": False,
        "side_effects": {
            "secret_read": False,
            "db_write": False,
            "odoo_write": False,
            "adi_write": False,
            "formal_pos_order": False,
            "payment_capture": False,
            "network_call": False,
        },
    }
    result["content_sha256"] = canonical_sha256(result)
    return result


def _decimal_string(value: Any, path: str) -> str:
    if isinstance(value, bool):
        raise FieldApplicationError("CAFE_POS_PRICE_INVALID", path)
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise FieldApplicationError("CAFE_POS_PRICE_INVALID", path) from exc
    if not decimal.is_finite():
        raise FieldApplicationError("CAFE_POS_PRICE_INVALID", path)
    normalized = format(decimal, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def rectify_surface_candidate(
    surface: str,
    candidate: Mapping[str, Any],
    *,
    binding_registry: Mapping[str, Any] | None = None,
    founder_identity_request: Mapping[str, Any] | None = None,
    sealed_founder_root: Mapping[str, Any] | None = None,
    snapshot_path: Path = DEFAULT_MENU_SNAPSHOT_PATH,
) -> dict[str, Any]:
    """Rectify one human or AI candidate into the shared semantic line flow."""

    surface = _surface(surface)
    contract = _menu_contract(snapshot_path)
    registry = (
        dict(binding_registry)
        if binding_registry is not None
        else build_preview_binding_registry(surface, snapshot_path=snapshot_path)
    )
    production_registry = registry.get("state") == PRODUCTION_BINDING_STATE
    maps = _validate_registry(
        registry,
        surface,
        contract,
        allow_unsealed_production=production_registry,
    )
    binding_seal_evaluation = None
    if production_registry:
        binding_seal_evaluation = evaluate_binding_seal_request(
            registry,
            founder_identity_request=founder_identity_request,
            sealed_founder_root=sealed_founder_root,
            snapshot_path=snapshot_path,
        )
        if binding_seal_evaluation["decision"] != ALLOW:
            raise FieldApplicationError(
                "CAFE_POS_PRODUCTION_BINDING_SEAL_NOT_VERIFIED"
            )
    if not isinstance(candidate, Mapping) or set(candidate) != {
        "product_ref",
        "quantity",
        "selections",
    }:
        raise FieldApplicationError("CAFE_POS_CANDIDATE_INVALID")
    product_ref = candidate["product_ref"]
    quantity = candidate["quantity"]
    selections = candidate["selections"]
    if not isinstance(product_ref, str) or product_ref not in maps["products"]:
        raise FieldApplicationError("CAFE_POS_UNKNOWN_PRODUCT_REF", "$.product_ref")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 99:
        raise FieldApplicationError("CAFE_POS_QUANTITY_INVALID", "$.quantity")
    if not isinstance(selections, Mapping) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in selections.items()
    ):
        raise FieldApplicationError("CAFE_POS_SELECTIONS_INVALID", "$.selections")

    source_product_ref = maps["products"][product_ref]
    product = contract["products"][source_product_ref]
    allowed_group_ids = set(product["optionGroupIds"])
    allowed_questions = {
        source_ref: question
        for source_ref, question in contract["questions"].items()
        if question["group_id"] in allowed_group_ids
    }
    source_selections: dict[str, str] = {}
    for surface_question_ref, surface_option_ref in selections.items():
        source_question_ref = maps["questions"].get(surface_question_ref)
        source_option_ref = maps["options"].get(surface_option_ref)
        if source_question_ref is None or source_question_ref not in allowed_questions:
            raise FieldApplicationError(
                "CAFE_POS_UNKNOWN_PRODUCT_QUESTION", "$.selections"
            )
        if source_option_ref is None:
            raise FieldApplicationError("CAFE_POS_UNKNOWN_SOURCE_OPTION", "$.selections")
        option = contract["options"][source_option_ref]
        if option["question_ref"] != source_question_ref:
            raise FieldApplicationError("CAFE_POS_OPTION_QUESTION_MISMATCH", "$.selections")
        source_selections[source_question_ref] = source_option_ref

    missing = [
        question["displayName"]
        for source_ref, question in allowed_questions.items()
        if question["required"] and source_ref not in source_selections
    ]
    if missing:
        raise FieldApplicationError("CAFE_POS_REQUIRED_OPTION_MISSING", "$.selections")

    normalized_selections: list[dict[str, Any]] = []
    delta_total = Decimal("0")
    for source_question_ref, question in allowed_questions.items():
        source_option_ref = source_selections.get(source_question_ref)
        if source_option_ref is None:
            continue
        option = contract["options"][source_option_ref]
        delta = Decimal(_decimal_string(option["priceDelta"], "$.option.price_delta"))
        delta_total += delta
        normalized_selections.append(
            {
                "source_question_ref": source_question_ref,
                "source_option_ref": source_option_ref,
                "product_question_coordinate": (
                    f"{source_product_ref}:{question['id']}"
                ),
                "product_option_coordinate": f"{source_product_ref}:{option['id']}",
                "question_name": question["displayName"],
                "option_name": option["displayName"],
                "selection_mode": question["selectionMode"],
                "price_delta": _decimal_string(delta, "$.option.price_delta"),
            }
        )

    base_price = Decimal(_decimal_string(product["price"], "$.product.price"))
    unit_price = base_price + delta_total
    line_total = unit_price * quantity
    semantic_candidate = {
        "schema_version": "W7TP-CAFE-POS-RECTIFIED-LINE/1.0",
        "profile": "CAFE_POS",
        "source_authority": {
            "menu_id": contract["web_data"]["source"]["id"],
            "source_export_sha256": contract["web_data"]["source"]["sha256"],
            "snapshot_file_sha256": contract["snapshot_file_sha256"],
        },
        "product": {
            "source_product_ref": source_product_ref,
            "source_product_id": product["sourceProductId"],
            "source_product_code": product["sourceProductCode"],
            "name": product["name"],
            "major_category": product["category"],
            "source_category": product["sourceCategory"],
        },
        "quantity": quantity,
        "selections": normalized_selections,
        "pricing_candidate": {
            "currency": "TWD",
            "base_price": _decimal_string(base_price, "$.product.price"),
            "option_delta_total": _decimal_string(delta_total, "$.option_delta_total"),
            "unit_price": _decimal_string(unit_price, "$.unit_price"),
            "line_total": _decimal_string(line_total, "$.line_total"),
        },
        "line_key": "|".join(
            [source_product_ref]
            + [
                f"{selection['source_question_ref']}={selection['source_option_ref']}"
                for selection in normalized_selections
            ]
        ),
    }
    semantic_content_sha256 = canonical_sha256(semantic_candidate)
    binding_ready = (
        production_registry
        and binding_seal_evaluation is not None
        and binding_seal_evaluation["decision"] == ALLOW
    )
    binding_hold = (
        "HOLD_ODOO_PRODUCT_BINDINGS_NOT_PROVISIONED"
        if surface == "ODOO_HUMAN"
        else "HOLD_ADI_BINDINGS_NOT_PROVISIONED"
    )
    reason_codes = [] if binding_ready else [binding_hold]
    reason_codes.extend(
        [
            "HOLD_FORMAL_POS_ORDER_RELEASE_EVIDENCE_REQUIRED",
            "HOLD_HUMAN_D8_CONFIRMATION_REQUIRED",
        ]
    )
    result: dict[str, Any] = {
        "schema_version": "W7TP-CAFE-POS-INTEROP-CANDIDATE/1.0",
        "state": "L3_CANDIDATE_HUMAN_D8_REQUIRED",
        "profile": "CAFE_POS",
        "candidate_only": True,
        "surface": surface,
        "binding_registry": {
            "state": registry["state"],
            "content_sha256": registry["content_sha256"],
            "encoding_version": registry["encoding_registry"]["version"],
            "encoding_registry_sha256": registry["encoding_registry"]
            ["content_sha256"],
            "total_field_binding_seal_ref": (
                binding_seal_evaluation["binding_seal_ref"]
                if binding_seal_evaluation is not None
                else None
            ),
            "product_count": len(registry["product_bindings"]),
            "question_count": len(registry["question_bindings"]),
            "option_count": len(registry["option_bindings"]),
        },
        "source_snapshot": {
            **registry["source_snapshot"],
            "scenario_route_table_sha256": registry["authority_sources"]
            ["scenario_route_table"]["sha256"],
            "capability_registry_sha256": registry["authority_sources"]
            ["capability_registry"]["sha256"],
        },
        "total_field": {
            "shared_runtime": "tools/total_field/w7tp_field_application_runtime.py",
            "profile": "CAFE_POS",
            "rectifier": "W7TP_CAFE_POS_TOTAL_FIELD_RECTIFIER",
            "same_semantic_flow": True,
        },
        "semantic_candidate": semantic_candidate,
        "semantic_content_sha256": semantic_content_sha256,
        "production_gate": {
            "state": "HOLD",
            "binding_readiness": (
                "VERIFIED_READ_ONLY" if binding_ready else "PREVIEW_ONLY"
            ),
            "reason_codes": reason_codes,
            "formal_pos_order": False,
            "human_d8_confirmation_required": True,
        },
        "D8": {
            "decision": "PENDING_TOTAL_FIELD_REVIEW",
            "formal_execution_authority": False,
        },
        "execution_metadata": {
            "input_surface": surface,
            "surface_specific_data_excluded_from_semantic_hash": True,
            "llm_execution": (
                "USER_DEVICE_ONLY" if surface == "ADI_AI" else "NONE"
            ),
        },
        "redteam_drift_monitor": {
            "mode": "ALWAYS_ON_EVERY_STATE_TRANSITION",
            "status": "MONITORING_CLEAR",
            "checked_boundaries": [
                "SOURCE_SNAPSHOT",
                "BINDING_COVERAGE",
                "OPTION_COORDINATE",
                "ADI_RULE_PRIVACY",
                "FORMAL_ORDER",
                "PAYMENT",
                "DB_WRITE",
                "SERVER_LLM",
            ],
        },
        "side_effects": {
            "db_write": False,
            "odoo_write": False,
            "adi_write": False,
            "formal_pos_order": False,
            "payment_capture": False,
            "network_call": False,
            "server_llm": False,
        },
    }
    envelope_content = {
        key: value for key, value in result.items() if key != "execution_metadata"
    }
    result["envelope_content_sha256"] = canonical_sha256(envelope_content)
    return result
