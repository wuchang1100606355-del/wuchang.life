"""Core position-aware encoding shared by menu, Odoo, ADI, and Total Field.

Identity codes are built from stable source coordinates. Snapshot hashes seal a
version of the registry, but never re-key unchanged source entities.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any

from tools.total_field.w7tp_field_application_runtime import FieldApplicationError


ENCODING_REGISTRY_VERSION = "W7TP-CORE-ENCODING/1.0"
SOURCE_NAMESPACE = "QUICKCLICK"
SUPPORTED_SURFACES = ("ODOO_HUMAN", "ADI_AI")
SUPPORTED_ENTITY_TYPES = ("PRODUCT", "QUESTION", "OPTION")
FIELD_DIMENSIONS = {
    "D1": ("INTENT", "HAS_INTENT"),
    "D2": ("STATE", "HAS_STATE"),
    "D3": ("COORDINATE", "LOCATED_AT"),
    "D4": ("EVIDENCE", "SUPPORTED_BY"),
    "D5": ("EXECUTION", "PROPOSES_EXECUTION"),
    "D6": ("GENERATIVE_TRANSMISSION", "RECONSTRUCTS_AS"),
    "D7": ("RISK", "EXPOSES_RISK"),
    "D8": ("ENVELOPE", "ENVELOPED_BY"),
}
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
QUESTION_COORDINATE_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+:Q[1-9][0-9]*$")
OPTION_COORDINATE_PATTERN = re.compile(
    r"^[A-Za-z0-9_.-]+:Q[1-9][0-9]*:O[1-9][0-9]*$"
)


def _canonical_json(value: Any) -> str:
    def normalize(item: Any) -> Any:
        if isinstance(item, str):
            return unicodedata.normalize("NFC", item)
        if isinstance(item, dict):
            return {normalize(key): normalize(child) for key, child in item.items()}
        if isinstance(item, list):
            return [normalize(child) for child in item]
        return item

    return json.dumps(
        normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _segment(value: str, path: str) -> str:
    if not isinstance(value, str):
        raise FieldApplicationError("CORE_ENCODING_SEGMENT_INVALID", path)
    normalized = unicodedata.normalize("NFC", value)
    if not normalized or normalized != normalized.strip() or not SEGMENT_PATTERN.fullmatch(normalized):
        raise FieldApplicationError("CORE_ENCODING_SEGMENT_INVALID", path)
    return normalized


def build_source_coordinate(
    entity_type: str,
    menu_id: str,
    entity_coordinate: str,
) -> str:
    """Encode one source entity from its lowest stable identity segments."""

    if entity_type not in SUPPORTED_ENTITY_TYPES:
        raise FieldApplicationError("CORE_ENCODING_ENTITY_TYPE_INVALID", "$.entity_type")
    menu_id = _segment(menu_id, "$.menu_id")
    if not isinstance(entity_coordinate, str):
        raise FieldApplicationError("CORE_ENCODING_COORDINATE_INVALID", "$.entity_coordinate")
    entity_coordinate = unicodedata.normalize("NFC", entity_coordinate)
    patterns = {
        "PRODUCT": SEGMENT_PATTERN,
        "QUESTION": QUESTION_COORDINATE_PATTERN,
        "OPTION": OPTION_COORDINATE_PATTERN,
    }
    if not patterns[entity_type].fullmatch(entity_coordinate):
        raise FieldApplicationError("CORE_ENCODING_COORDINATE_INVALID", "$.entity_coordinate")
    return f"{SOURCE_NAMESPACE}:{menu_id}:{entity_coordinate}"


def build_surface_binding_ref(
    surface: str,
    entity_type: str,
    source_ref: str,
) -> str:
    """Encode one stable opaque surface binding without snapshot-wide re-keying."""

    if surface not in SUPPORTED_SURFACES:
        raise FieldApplicationError("CORE_ENCODING_SURFACE_INVALID", "$.surface")
    if entity_type not in SUPPORTED_ENTITY_TYPES:
        raise FieldApplicationError("CORE_ENCODING_ENTITY_TYPE_INVALID", "$.entity_type")
    explanation = explain_code(source_ref)
    if explanation["entity_type"] != entity_type:
        raise FieldApplicationError("CORE_ENCODING_ENTITY_TYPE_MISMATCH", "$.source_ref")
    digest = _canonical_sha256(
        {
            "encoding_version": ENCODING_REGISTRY_VERSION,
            "surface": surface,
            "entity_type": entity_type,
            "source_ref": source_ref,
        }
    )
    if surface == "ODOO_HUMAN":
        prefix = f"ODOO_{entity_type}_PREVIEW_REF"
    else:
        prefix = f"ADI_5D_{entity_type}_REF"
    return f"{prefix}:v1:sha256:{digest}"


def build_thing_code(
    thing_class: str,
    authority_namespace: str,
    stable_coordinate: str,
) -> str:
    """Encode any thing as an opaque, authority-scoped Total Field identity."""

    if not isinstance(thing_class, str) or not re.fullmatch(
        r"^[A-Z][A-Z0-9_]{1,63}$", thing_class
    ):
        raise FieldApplicationError("CORE_ENCODING_THING_CLASS_INVALID", "$.thing_class")
    authority_namespace = _segment(authority_namespace, "$.authority_namespace")
    if not isinstance(stable_coordinate, str) or not stable_coordinate:
        raise FieldApplicationError(
            "CORE_ENCODING_STABLE_COORDINATE_INVALID", "$.stable_coordinate"
        )
    digest = _canonical_sha256(
        {
            "encoding_version": ENCODING_REGISTRY_VERSION,
            "thing_class": thing_class,
            "authority_namespace": authority_namespace,
            "stable_coordinate": unicodedata.normalize("NFC", stable_coordinate),
        }
    )
    return f"W7TP_THING_REF:v1:{thing_class}:sha256:{digest}"


def build_field_edge_code(
    dimension: str,
    relationship: str,
    source_thing_code: str,
    target_thing_code: str,
) -> str:
    """Encode one directed relationship at an explicit D1-D8 field edge."""

    dimension_record = FIELD_DIMENSIONS.get(dimension)
    if dimension_record is None:
        raise FieldApplicationError("CORE_ENCODING_DIMENSION_INVALID", "$.dimension")
    if relationship != dimension_record[1]:
        raise FieldApplicationError(
            "CORE_ENCODING_RELATIONSHIP_DIMENSION_MISMATCH", "$.relationship"
        )
    for path, code in (
        ("$.source_thing_code", source_thing_code),
        ("$.target_thing_code", target_thing_code),
    ):
        explanation = explain_code(code)
        if explanation["code_class"] != "THING_REF":
            raise FieldApplicationError("CORE_ENCODING_THING_REF_REQUIRED", path)
    digest = _canonical_sha256(
        {
            "encoding_version": ENCODING_REGISTRY_VERSION,
            "dimension": dimension,
            "relationship": relationship,
            "source_thing_code": source_thing_code,
            "target_thing_code": target_thing_code,
        }
    )
    return f"W7TP_FIELD_EDGE_REF:v1:{dimension}:{relationship}:sha256:{digest}"


def build_packet_field_encoding(
    packet: dict[str, Any],
    profile: str,
    stable_packet_coordinate: str,
) -> dict[str, Any]:
    """Encode one complete D1-D8 packet as things and directed field edges."""

    missing = [dimension for dimension in FIELD_DIMENSIONS if dimension not in packet]
    if missing:
        raise FieldApplicationError("CORE_ENCODING_8D_PACKET_INCOMPLETE")
    profile = _segment(profile, "$.profile")
    registry = build_encoding_registry()
    packet_thing_code = build_thing_code(
        "PACKET", f"TOTAL_FIELD_{profile}", stable_packet_coordinate
    )
    dimensions: dict[str, Any] = {}
    for dimension, (thing_class, relationship) in FIELD_DIMENSIONS.items():
        thing_code = build_thing_code(
            thing_class,
            f"TOTAL_FIELD_{profile}",
            _canonical_sha256(packet[dimension]),
        )
        dimensions[dimension] = {
            "semantic_role": thing_class,
            "thing_code": thing_code,
            "relationship": relationship,
            "field_edge_code": build_field_edge_code(
                dimension,
                relationship,
                packet_thing_code,
                thing_code,
            ),
        }
    result: dict[str, Any] = {
        "schema_version": "W7TP-8D-FIELD-ENCODING/1.0",
        "registry_version": ENCODING_REGISTRY_VERSION,
        "encoding_registry_sha256": registry["content_sha256"],
        "packet_thing_code": packet_thing_code,
        "dimensions": dimensions,
        "authority": "LOCAL_TOTAL_FIELD_ONLY",
        "formal_execution_authority": False,
    }
    result["content_sha256"] = _canonical_sha256(result)
    return result


def explain_code(code: str) -> dict[str, Any]:
    """Return the position and meaning of every segment in one managed code."""

    if not isinstance(code, str) or not code or code != code.strip():
        raise FieldApplicationError("CORE_ENCODING_CODE_INVALID", "$.code")
    parts = code.split(":")
    if parts[0] == SOURCE_NAMESPACE:
        if len(parts) == 3:
            entity_type = "PRODUCT"
            meanings = (
                "SOURCE_AUTHORITY_NAMESPACE",
                "MENU_IDENTITY",
                "PRODUCT_IDENTITY_COORDINATE",
            )
        elif len(parts) == 4 and re.fullmatch(r"Q[1-9][0-9]*", parts[3]):
            entity_type = "QUESTION"
            meanings = (
                "SOURCE_AUTHORITY_NAMESPACE",
                "MENU_IDENTITY",
                "OPTION_GROUP_IDENTITY",
                "QUESTION_ORDINAL_WITHIN_GROUP",
            )
        elif (
            len(parts) == 5
            and re.fullmatch(r"Q[1-9][0-9]*", parts[3])
            and re.fullmatch(r"O[1-9][0-9]*", parts[4])
        ):
            entity_type = "OPTION"
            meanings = (
                "SOURCE_AUTHORITY_NAMESPACE",
                "MENU_IDENTITY",
                "OPTION_GROUP_IDENTITY",
                "QUESTION_ORDINAL_WITHIN_GROUP",
                "OPTION_ORDINAL_WITHIN_QUESTION",
            )
        else:
            raise FieldApplicationError("CORE_ENCODING_CODE_INVALID", "$.code")
        for index, part in enumerate(parts):
            _segment(part, f"$.code[{index + 1}]")
        return {
            "schema_version": "W7TP-CORE-CODE-EXPLANATION/1.0",
            "registry_version": ENCODING_REGISTRY_VERSION,
            "code_class": "SOURCE_COORDINATE",
            "surface": "SOURCE",
            "entity_type": entity_type,
            "positions": [
                {"position": index, "segment": segment, "meaning": meanings[index - 1]}
                for index, segment in enumerate(parts, start=1)
            ],
            "identity_stability": "UNCHANGED_WHILE_SOURCE_COORDINATE_IS_UNCHANGED",
        }

    if (
        len(parts) == 5
        and parts[0] == "W7TP_THING_REF"
        and parts[1] == "v1"
        and re.fullmatch(r"^[A-Z][A-Z0-9_]{1,63}$", parts[2])
        and parts[3] == "sha256"
        and SHA256_PATTERN.fullmatch(parts[4])
    ):
        return {
            "schema_version": "W7TP-CORE-CODE-EXPLANATION/1.0",
            "registry_version": ENCODING_REGISTRY_VERSION,
            "code_class": "THING_REF",
            "surface": "TOTAL_FIELD",
            "entity_type": parts[2],
            "positions": [
                {"position": 1, "segment": parts[0], "meaning": "TOTAL_FIELD_THING_CLASS"},
                {"position": 2, "segment": parts[1], "meaning": "ENCODING_MAJOR_VERSION"},
                {"position": 3, "segment": parts[2], "meaning": "THING_SEMANTIC_CLASS"},
                {"position": 4, "segment": parts[3], "meaning": "DIGEST_ALGORITHM"},
                {"position": 5, "segment": parts[4], "meaning": "AUTHORITY_SCOPED_IDENTITY_DIGEST"},
            ],
            "identity_stability": "UNCHANGED_WHILE_AUTHORITY_AND_STABLE_COORDINATE_ARE_UNCHANGED",
        }
    if (
        len(parts) == 6
        and parts[0] == "W7TP_FIELD_EDGE_REF"
        and parts[1] == "v1"
        and parts[2] in FIELD_DIMENSIONS
        and parts[3] == FIELD_DIMENSIONS[parts[2]][1]
        and parts[4] == "sha256"
        and SHA256_PATTERN.fullmatch(parts[5])
    ):
        return {
            "schema_version": "W7TP-CORE-CODE-EXPLANATION/1.0",
            "registry_version": ENCODING_REGISTRY_VERSION,
            "code_class": "FIELD_EDGE_REF",
            "surface": "TOTAL_FIELD",
            "entity_type": "DIRECTED_RELATIONSHIP",
            "positions": [
                {"position": 1, "segment": parts[0], "meaning": "TOTAL_FIELD_EDGE_CLASS"},
                {"position": 2, "segment": parts[1], "meaning": "ENCODING_MAJOR_VERSION"},
                {"position": 3, "segment": parts[2], "meaning": "D1_TO_D8_DIMENSION"},
                {"position": 4, "segment": parts[3], "meaning": "DIRECTED_RELATIONSHIP"},
                {"position": 5, "segment": parts[4], "meaning": "DIGEST_ALGORITHM"},
                {"position": 6, "segment": parts[5], "meaning": "SOURCE_TARGET_EDGE_DIGEST"},
            ],
            "identity_stability": "UNCHANGED_WHILE_SOURCE_TARGET_RELATIONSHIP_IS_UNCHANGED",
        }

    prefix_match = re.fullmatch(
        r"(ODOO|ADI_5D)_(PRODUCT|QUESTION|OPTION)_(PREVIEW_REF|REF)",
        parts[0],
    ) if len(parts) == 4 else None
    if (
        prefix_match is None
        or parts[1] != "v1"
        or parts[2] != "sha256"
        or not SHA256_PATTERN.fullmatch(parts[3])
    ):
        raise FieldApplicationError("CORE_ENCODING_CODE_INVALID", "$.code")
    surface = "ODOO_HUMAN" if prefix_match.group(1) == "ODOO" else "ADI_AI"
    allowed_ref_classes = (
        {"PREVIEW_REF", "REF"} if surface == "ODOO_HUMAN" else {"REF"}
    )
    if prefix_match.group(3) not in allowed_ref_classes:
        raise FieldApplicationError("CORE_ENCODING_CODE_INVALID", "$.code")
    return {
        "schema_version": "W7TP-CORE-CODE-EXPLANATION/1.0",
        "registry_version": ENCODING_REGISTRY_VERSION,
        "code_class": "SURFACE_BINDING_REF",
        "surface": surface,
        "entity_type": prefix_match.group(2),
        "positions": [
            {
                "position": 1,
                "segment": parts[0],
                "meaning": "SURFACE_ENTITY_AND_CANDIDATE_CLASS",
            },
            {"position": 2, "segment": parts[1], "meaning": "ENCODING_MAJOR_VERSION"},
            {"position": 3, "segment": parts[2], "meaning": "DIGEST_ALGORITHM"},
            {"position": 4, "segment": parts[3], "meaning": "OPAQUE_SOURCE_BINDING_DIGEST"},
        ],
        "identity_stability": "UNCHANGED_WHILE_SOURCE_COORDINATE_IS_UNCHANGED",
    }


def build_encoding_registry() -> dict[str, Any]:
    """Return the machine-verifiable core code management registry."""

    registry: dict[str, Any] = {
        "schema_version": "W7TP-CORE-ENCODING-REGISTRY/1.0",
        "state": "CORE_INVARIANT_ACTIVE",
        "registry_version": ENCODING_REGISTRY_VERSION,
        "authority": "LOCAL_TOTAL_FIELD_ONLY",
        "formats": [
            {
                "code_class": "SOURCE_PRODUCT_COORDINATE",
                "example_shape": "QUICKCLICK:{menu_id}:{product_coordinate}",
                "positions": [
                    "SOURCE_AUTHORITY_NAMESPACE",
                    "MENU_IDENTITY",
                    "PRODUCT_IDENTITY_COORDINATE",
                ],
            },
            {
                "code_class": "SOURCE_QUESTION_COORDINATE",
                "example_shape": "QUICKCLICK:{menu_id}:{option_group_id}:Q{question_ordinal}",
                "positions": [
                    "SOURCE_AUTHORITY_NAMESPACE",
                    "MENU_IDENTITY",
                    "OPTION_GROUP_IDENTITY",
                    "QUESTION_ORDINAL_WITHIN_GROUP",
                ],
            },
            {
                "code_class": "SOURCE_OPTION_COORDINATE",
                "example_shape": "QUICKCLICK:{menu_id}:{option_group_id}:Q{question_ordinal}:O{option_ordinal}",
                "positions": [
                    "SOURCE_AUTHORITY_NAMESPACE",
                    "MENU_IDENTITY",
                    "OPTION_GROUP_IDENTITY",
                    "QUESTION_ORDINAL_WITHIN_GROUP",
                    "OPTION_ORDINAL_WITHIN_QUESTION",
                ],
            },
            {
                "code_class": "SURFACE_BINDING_REF",
                "example_shape": "{surface_entity_class}:v1:sha256:{source_binding_digest}",
                "positions": [
                    "SURFACE_ENTITY_AND_CANDIDATE_CLASS",
                    "ENCODING_MAJOR_VERSION",
                    "DIGEST_ALGORITHM",
                    "OPAQUE_SOURCE_BINDING_DIGEST",
                ],
            },
            {
                "code_class": "THING_REF",
                "example_shape": "W7TP_THING_REF:v1:{thing_class}:sha256:{authority_scoped_identity_digest}",
                "positions": [
                    "TOTAL_FIELD_THING_CLASS",
                    "ENCODING_MAJOR_VERSION",
                    "THING_SEMANTIC_CLASS",
                    "DIGEST_ALGORITHM",
                    "AUTHORITY_SCOPED_IDENTITY_DIGEST",
                ],
            },
            {
                "code_class": "FIELD_EDGE_REF",
                "example_shape": "W7TP_FIELD_EDGE_REF:v1:{dimension}:{relationship}:sha256:{source_target_edge_digest}",
                "positions": [
                    "TOTAL_FIELD_EDGE_CLASS",
                    "ENCODING_MAJOR_VERSION",
                    "D1_TO_D8_DIMENSION",
                    "DIRECTED_RELATIONSHIP",
                    "DIGEST_ALGORITHM",
                    "SOURCE_TARGET_EDGE_DIGEST",
                ],
            },
        ],
        "field_dimensions": [
            {
                "dimension": dimension,
                "semantic_role": semantic_role,
                "relationship": relationship,
            }
            for dimension, (semantic_role, relationship) in FIELD_DIMENSIONS.items()
        ],
        "mutation_rules": {
            "add_entity": "ALLOCATE_ONLY_THE_NEW_SOURCE_COORDINATE_AND_BINDING",
            "delete_entity": "REMOVE_ONLY_THE_DELETED_ENTITY_FROM_ACTIVE_REGISTRY",
            "change_display_or_price": "KEEP_IDENTITY_CODE_AND_RESEAL_REGISTRY_VERSION",
            "change_source_identity": "ISSUE_NEW_CODE_AND_RETAIN_OLD_CODE_AS_RETIRED_EVIDENCE",
        },
        "invariants": [
            "BOTTOM_UP_SOURCE_COORDINATE_FIRST",
            "UNCHANGED_ENTITY_NEVER_REKEYED_BY_SNAPSHOT_CHANGE",
            "SNAPSHOT_HASH_SEALS_REGISTRY_NOT_ENTITY_IDENTITY",
            "RAW_OPTION_CODE_IS_NOT_A_UNIQUE_IDENTITY",
            "ODOO_AND_ADI_SURFACES_CONVERGE_TO_ONE_SEMANTIC_HASH",
            "EVERY_COMPLETE_8D_PACKET_HAS_EIGHT_POSITIONED_FIELD_EDGES",
            "FIELD_EDGE_CODES_NEVER_GRANT_D8_AUTHORITY",
            "NO_FORMAL_ORDER_OR_PAYMENT_AUTHORITY",
        ],
        "side_effects": {
            "db_write": False,
            "odoo_write": False,
            "adi_write": False,
            "network_call": False,
            "formal_pos_order": False,
        },
    }
    registry["content_sha256"] = _canonical_sha256(registry)
    return registry
