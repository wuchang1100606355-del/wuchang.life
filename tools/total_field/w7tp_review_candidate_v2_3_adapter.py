#!/usr/bin/env python3
"""Fail-closed 2.3 review-candidate to Canonical V2 reconstruction adapter.

The adapter is a local, read-only candidate constructor.  It never calls the
runtime receiver and never grants lifecycle, registry, deploy, DB, or router
authority.  Fields absent from the 2.3 source must arrive in a hash-bound
sidecar request; no semantic defaults are inferred from names or prose.
"""

from __future__ import annotations

from collections.abc import Collection, Iterator, Mapping
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

from tools.total_field.w7tp_intent_field_suite.canonical_hash import (
    canonical_json,
    canonical_sha256,
)


ROOT = Path(__file__).resolve().parents[2]
IDENTITY_MAP_REF = (
    "manifests/total_field/w7tp_five_skill_id_binding_matrix_v1/BINDING_MATRIX.json"
)
IDENTITY_MAP_PATH = ROOT / IDENTITY_MAP_REF
IDENTITY_MAP_SCHEMA_PATH = (
    ROOT / "schemas/field/w7tp_five_skill_id_binding_matrix_v1.schema.json"
)
ADAPTER_REQUEST_SCHEMA_PATH = (
    ROOT / "schemas/field/w7tp_review_candidate_v2_3_adapter_request_v1.schema.json"
)
CANONICAL_SCHEMA_PATH = (
    ROOT / "schemas/w7tp_8d_multipurpose_packet_canonical_v2.schema.json"
)
PACKAGE_MANIFEST_SCHEMA_PATH = (
    ROOT / "schemas/field/variable_cognition_package_manifest.schema.json"
)

REQUEST_SELF_HASH_ALGORITHM = (
    "SHA256_CANONICAL_JSON_EXCLUDING_REQUEST_SELF_SHA256/1.0"
)
CANONICAL_PACKET_HASH_ALGORITHM = (
    "SHA256_CANONICAL_JSON_EXCLUDING_BOTH_ENVELOPE_SHA256_FIELDS/1.0"
)
CANONICAL_ID = "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2"
CANONICAL_VERSION = "2.0.0"
CANONICAL_CORE = "UNIFIED_MULTIPURPOSE_8D_PACKET"
CANONICAL_RECONSTRUCTION_CORE = [
    "NON_FLOAT_DETERMINISTIC_LOOKUP",
    "INTEGER_STATE_TRANSITION",
    "RULE_EXPANSION",
    "REFERENCE_RESOLUTION",
    "COORDINATE_RECONSTRUCTION",
    "EQUIVALENT_STATE_GENERATION",
    "TOTAL_FIELD_VERIFICATION",
]
TECHNOLOGY_FLAGS = {
    "packet_carries_transport_protocol": True,
    "packet_carries_reconstruction_conditions": True,
    "packet_carries_reconstruction_contract": True,
    "packet_carries_verification_method": True,
    "packet_carries_verification_contract": True,
    "model_required": False,
    "llm_required": False,
    "neural_network_required": False,
    "floating_point_inference_required": False,
    "diffusion_required": False,
    "latent_codec": False,
    "neural_codec": False,
}
FORBIDDEN_EFFECT_TO_HARD_RISK = {
    "LIVE_DB_WRITE": "DB_WRITE",
    "DEPLOY": "DEPLOY",
    "ROUTER_WRITE": "ROUTER_WRITE",
}
NO_SIDE_EFFECTS = {
    "file_write": False,
    "network": False,
    "database_write": False,
    "deploy": False,
    "restart": False,
    "router_write": False,
    "registry_write": False,
    "canonical_write": False,
    "runtime_receiver_call": False,
}


class AdapterError(ValueError):
    """A stable HOLD/BLOCK result from the fail-closed adapter."""

    def __init__(
        self,
        reason_code: str,
        path: str = "$",
        *,
        decision: str = "HOLD",
    ) -> None:
        self.reason_code = reason_code
        self.path = path
        self.decision = decision
        super().__init__(f"{decision}:{reason_code}:{path}")


def _reject_float(token: str) -> Any:
    raise ValueError(f"floating point JSON value is forbidden: {token}")


def _reject_constant(token: str) -> Any:
    raise ValueError(f"non-finite JSON value is forbidden: {token}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json_bytes(raw: bytes, reason_code: str) -> dict[str, Any]:
    """Parse exact UTF-8 JSON bytes while rejecting floats and duplicate keys."""

    try:
        value = json.loads(
            raw.decode("utf-8"),
            parse_float=_reject_float,
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise AdapterError(reason_code) from exc
    if not isinstance(value, dict):
        raise AdapterError(reason_code)
    return value


def _load_json(path: Path, reason_code: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AdapterError(reason_code, str(path)) from exc
    return strict_json_bytes(raw, reason_code)


def _json_path(parts: Collection[Any]) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += "." + str(part)
    return path


def _validate_schema(
    value: Any,
    schema_path: Path,
    reason_code: str,
) -> None:
    schema = _load_json(schema_path, "HOLD_SCHEMA_UNAVAILABLE")
    try:
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(value),
            key=lambda error: [str(item) for item in error.absolute_path],
        )
    except Exception as exc:
        raise AdapterError("HOLD_SCHEMA_DEFINITION_INVALID", str(schema_path)) from exc
    if errors:
        raise AdapterError(reason_code, _json_path(errors[0].absolute_path))


def _sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError as exc:
        raise AdapterError("HOLD_FILE_HASH_UNAVAILABLE", str(path)) from exc


def _copy_json(value: Any, reason_code: str = "HOLD_NON_CANONICAL_JSON") -> Any:
    try:
        return json.loads(canonical_json(value))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AdapterError(reason_code) from exc


def request_self_sha256(request: Mapping[str, Any]) -> str:
    """Return the request self-hash, excluding only request_self_sha256."""

    unsigned = _copy_json(dict(request), "HOLD_ADAPTER_REQUEST_NOT_CANONICAL_JSON")
    unsigned.pop("request_self_sha256", None)
    return canonical_sha256(unsigned)


def with_request_self_hash(request: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copied request with a deterministic non-signature self-hash."""

    sealed = _copy_json(dict(request), "HOLD_ADAPTER_REQUEST_NOT_CANONICAL_JSON")
    sealed["request_self_hash_algorithm"] = REQUEST_SELF_HASH_ALGORITHM
    sealed.pop("request_self_sha256", None)
    sealed["request_self_sha256"] = canonical_sha256(sealed)
    return sealed


def _relative_manifest_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts or "." in path.parts:
        raise AdapterError("HOLD_MANIFEST_PATH_UNSAFE", value)
    return path


def validate_identity_map(
    identity_map: Mapping[str, Any] | None = None,
    *,
    workspace_root: Path = ROOT,
) -> dict[str, Any]:
    """Validate schema, self-hash, tuple hashes, uniqueness, and Canonical pins."""

    if identity_map is not None and not isinstance(identity_map, Mapping):
        raise AdapterError("HOLD_IDENTITY_MAP_OBJECT_REQUIRED")
    mapping = (
        _load_json(IDENTITY_MAP_PATH, "HOLD_IDENTITY_MAP_UNAVAILABLE")
        if identity_map is None
        else _copy_json(dict(identity_map), "HOLD_IDENTITY_MAP_NOT_CANONICAL_JSON")
    )
    _validate_schema(
        mapping,
        IDENTITY_MAP_SCHEMA_PATH,
        "HOLD_IDENTITY_MAP_SCHEMA_INVALID",
    )

    unsigned = deepcopy(mapping)
    supplied_self_hash = unsigned.pop("binding_matrix_self_sha256")
    if canonical_sha256(unsigned) != supplied_self_hash:
        raise AdapterError("HOLD_IDENTITY_MAP_HASH_MISMATCH")

    bindings = mapping["bindings"]
    package_schema_pin = mapping["package_manifest_schema"]
    if len(bindings) != 5:
        raise AdapterError("HOLD_IDENTITY_MAP_NOT_EXACTLY_FIVE", "$.bindings")

    source_keys: set[str] = set()
    package_ids: set[str] = set()
    manifest_paths: set[str] = set()
    for target_skill_id, entry in bindings.items():
        if entry["target_skill_id"] != target_skill_id:
            raise AdapterError(
                "HOLD_IDENTITY_MAP_TARGET_MISMATCH",
                f"$.bindings.{target_skill_id}",
            )
        unsigned_entry = dict(entry)
        supplied_entry_hash = unsigned_entry.pop("identity_binding_sha256")
        if canonical_sha256(unsigned_entry) != supplied_entry_hash:
            raise AdapterError(
                "HOLD_IDENTITY_BINDING_HASH_MISMATCH",
                f"$.bindings.{target_skill_id}.identity_binding_sha256",
            )
        expected_path = f"{entry['source_key']}/total-field-skill-manifest.json"
        if entry["manifest_path"] != expected_path:
            raise AdapterError(
                "HOLD_IDENTITY_MAP_MANIFEST_PATH_MISMATCH",
                f"$.bindings.{target_skill_id}.manifest_path",
            )
        if entry["manifest_schema_ref"] != package_schema_pin["ref"]:
            raise AdapterError(
                "HOLD_IDENTITY_MAP_MANIFEST_SCHEMA_REF_MISMATCH",
                f"$.bindings.{target_skill_id}.manifest_schema_ref",
            )
        _relative_manifest_path(entry["manifest_path"])
        source_keys.add(entry["source_key"])
        package_ids.add(entry["package_id"])
        manifest_paths.add(entry["manifest_path"])

    if not all(len(values) == 5 for values in (source_keys, package_ids, manifest_paths)):
        raise AdapterError("HOLD_DUPLICATE_SKILL_SOURCE_OR_PACKAGE_ID", "$.bindings")

    root = workspace_root.resolve()
    target = mapping["canonical_target"]
    for ref_key, hash_key in (
        ("canonical_doc_ref", "canonical_doc_file_sha256"),
        ("machine_schema_ref", "machine_schema_file_sha256"),
    ):
        relative = _relative_manifest_path(target[ref_key])
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise AdapterError("HOLD_CANONICAL_TARGET_PATH_ESCAPE", target[ref_key]) from exc
        if not path.is_file() or _sha256_file(path) != target[hash_key]:
            raise AdapterError("HOLD_CANONICAL_TARGET_HASH_MISMATCH", target[ref_key])

    package_schema_relative = _relative_manifest_path(package_schema_pin["ref"])
    package_schema_path = (root / package_schema_relative).resolve()
    try:
        package_schema_path.relative_to(root)
    except ValueError as exc:
        raise AdapterError(
            "HOLD_PACKAGE_MANIFEST_SCHEMA_PATH_ESCAPE",
            package_schema_pin["ref"],
        ) from exc
    if (
        not package_schema_path.is_file()
        or _sha256_file(package_schema_path) != package_schema_pin["file_sha256"]
    ):
        raise AdapterError(
            "HOLD_PACKAGE_MANIFEST_SCHEMA_HASH_MISMATCH",
            package_schema_pin["ref"],
        )

    return mapping


def _resolved_source_path(workspace_root: Path, relative_value: str) -> Path:
    relative = _relative_manifest_path(relative_value)
    root = workspace_root.resolve()
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise AdapterError("HOLD_MANIFEST_SYMLINK_FORBIDDEN", relative_value)
    resolved = current.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AdapterError("HOLD_MANIFEST_PATH_ESCAPE", relative_value) from exc
    return resolved


def inspect_skill_manifest_bindings(
    identity_map: Mapping[str, Any] | None = None,
    *,
    workspace_root: Path = ROOT,
) -> dict[str, Any]:
    """Return measured manifest state; missing hashes are null, never placeholders."""

    try:
        mapping = validate_identity_map(identity_map, workspace_root=workspace_root)
        manifest_schema_path = _resolved_source_path(
            workspace_root,
            mapping["package_manifest_schema"]["ref"],
        )
        manifest_schema = _load_json(
            manifest_schema_path,
            "HOLD_PACKAGE_MANIFEST_SCHEMA_UNAVAILABLE",
        )
        try:
            Draft202012Validator.check_schema(manifest_schema)
        except Exception as exc:
            raise AdapterError(
                "HOLD_PACKAGE_MANIFEST_SCHEMA_INVALID",
                mapping["package_manifest_schema"]["ref"],
            ) from exc
        validator = Draft202012Validator(manifest_schema)
        results: dict[str, dict[str, Any]] = {}
        seen_hashes: set[str] = set()

        for target_skill_id in sorted(mapping["bindings"]):
            entry = mapping["bindings"][target_skill_id]
            source_key = entry["source_key"]
            path = _resolved_source_path(workspace_root, entry["manifest_path"])
            result = {
                "target_skill_id": target_skill_id,
                "source_key": source_key,
                "package_id": entry["package_id"],
                "manifest_path": entry["manifest_path"],
                "manifest_file_sha256": None,
                "package_payload_sha256_declared": None,
                "package_payload_hash_verified": False,
                "state": "MISSING",
            }
            results[source_key] = result
            if not path.is_file():
                continue

            try:
                raw = path.read_bytes()
            except OSError as exc:
                raise AdapterError(
                    "HOLD_MANIFEST_READ_FAILED",
                    entry["manifest_path"],
                ) from exc
            manifest_hash = hashlib.sha256(raw).hexdigest()
            manifest = strict_json_bytes(raw, "HOLD_MANIFEST_JSON_INVALID")
            errors = sorted(
                validator.iter_errors(manifest),
                key=lambda error: [str(item) for item in error.absolute_path],
            )
            if errors:
                raise AdapterError(
                    "HOLD_MANIFEST_SCHEMA_INVALID",
                    f"{entry['manifest_path']}:{_json_path(errors[0].absolute_path)}",
                )
            if manifest["package_id"] != entry["package_id"]:
                raise AdapterError(
                    "HOLD_MANIFEST_PACKAGE_ID_MISMATCH",
                    entry["manifest_path"],
                )
            if manifest["lifecycle_state"] != "CANDIDATE":
                raise AdapterError(
                    "HOLD_MANIFEST_NOT_CANDIDATE",
                    entry["manifest_path"],
                )
            if manifest_hash in seen_hashes:
                raise AdapterError(
                    "HOLD_DUPLICATE_MANIFEST_FILE_HASH",
                    entry["manifest_path"],
                )
            seen_hashes.add(manifest_hash)
            result.update(
                {
                    "manifest_file_sha256": manifest_hash,
                    "package_payload_sha256_declared": manifest["sha256"],
                    "state": "PRESENT_SCHEMA_VALID_CANDIDATE",
                }
            )

        missing = [
            item["manifest_path"] for item in results.values() if item["state"] == "MISSING"
        ]
        if missing:
            return {
                "state": "HOLD_MISSING_SOURCE_MANIFEST",
                "reason_code": "HOLD_MANIFEST_MISSING",
                "required_count": 5,
                "present_count": 5 - len(missing),
                "manifest_aggregate_sha256": None,
                "bindings": results,
                "candidate_only": True,
                "authority_granted": False,
                "side_effects": dict(NO_SIDE_EFFECTS),
            }

        lines = [
            f"{results[key]['manifest_file_sha256']}  {results[key]['manifest_path']}\n"
            for key in sorted(results)
        ]
        aggregate = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
        return {
            "state": "PASS_EXACT_FIVE_MANIFESTS_HASH_BOUND",
            "reason_code": None,
            "required_count": 5,
            "present_count": 5,
            "manifest_aggregate_sha256": aggregate,
            "bindings": results,
            "candidate_only": True,
            "authority_granted": False,
            "side_effects": dict(NO_SIDE_EFFECTS),
        }
    except AdapterError as exc:
        return {
            "state": f"{exc.decision}_MANIFEST_BINDING",
            "reason_code": exc.reason_code,
            "path": exc.path,
            "required_count": 5,
            "present_count": None,
            "manifest_aggregate_sha256": None,
            "bindings": {},
            "candidate_only": True,
            "authority_granted": False,
            "side_effects": dict(NO_SIDE_EFFECTS),
        }
    except Exception:
        return {
            "state": "HOLD_MANIFEST_BINDING",
            "reason_code": "HOLD_MANIFEST_BINDING_INTERNAL_ERROR",
            "path": "$",
            "required_count": 5,
            "present_count": None,
            "manifest_aggregate_sha256": None,
            "bindings": {},
            "candidate_only": True,
            "authority_granted": False,
            "side_effects": dict(NO_SIDE_EFFECTS),
        }


def canonical_packet_sha256(packet: Mapping[str, Any]) -> str:
    """Hash a Canonical packet while excluding both duplicated envelope hashes."""

    basis = _copy_json(dict(packet), "HOLD_CANONICAL_PACKET_NOT_CANONICAL_JSON")
    envelope = basis.get("envelope")
    dimensions = basis.get("dimensions")
    if not isinstance(envelope, dict) or not isinstance(dimensions, dict):
        raise AdapterError("HOLD_CANONICAL_PACKET_ENVELOPE_MISSING")
    dimension_envelope = dimensions.get("D8_ENVELOPE")
    if not isinstance(dimension_envelope, dict):
        raise AdapterError("HOLD_CANONICAL_PACKET_DIMENSION_ENVELOPE_MISSING")
    envelope.pop("sha256", None)
    dimension_envelope.pop("sha256", None)
    return canonical_sha256(basis)


def verify_canonical_packet_hash(packet: Mapping[str, Any]) -> bool:
    try:
        root_hash = packet["envelope"]["sha256"]
        dimension_hash = packet["dimensions"]["D8_ENVELOPE"]["sha256"]
        return root_hash == dimension_hash == canonical_packet_sha256(packet)
    except (AdapterError, KeyError, TypeError):
        return False


def _parse_utc(value: str, path: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise AdapterError("HOLD_PACKET_TIME_INVALID", path) from exc
    if parsed.tzinfo is None:
        raise AdapterError("HOLD_PACKET_TIMEZONE_REQUIRED", path)
    return parsed.astimezone(timezone.utc)


def _authority_injection(source_packet: Any) -> None:
    if not isinstance(source_packet, Mapping):
        return
    proposed = source_packet.get("d2_state")
    proposed_values = proposed.get("proposed") if isinstance(proposed, Mapping) else None
    if isinstance(proposed_values, list) and any(
        value == "ACTIVE" for value in proposed_values
    ):
        raise AdapterError(
            "BLOCK_AUTHORITY_INJECTION",
            "$.source_packet.d2_state.proposed",
            decision="BLOCK",
        )

    def walk(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                child = f"{path}.{key}"
                if (
                    key == "final_decision"
                    and isinstance(nested, str)
                    and nested in {"ALLOW", "ACTIVE", "PASS"}
                ):
                    raise AdapterError("BLOCK_AUTHORITY_INJECTION", child, decision="BLOCK")
                if key in {"authority_granted", "commit_applied"} and nested is True:
                    raise AdapterError("BLOCK_AUTHORITY_INJECTION", child, decision="BLOCK")
                walk(nested, child)
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                walk(nested, f"{path}[{index}]")

    walk(source_packet, "$.source_packet")


def _iter_leaf_paths(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key in sorted(value):
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from _iter_leaf_paths(value[key], f"{path}/{escaped}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_leaf_paths(item, f"{path}/{index}")
    else:
        yield path or "/", value


def _dimension_profile_ref(source_packet: Mapping[str, Any], key: str) -> dict[str, str]:
    return {
        "profile_ref": f"w7tp-v2.3:{key}:sha256:{canonical_sha256(source_packet[key])}"
    }


def _projection_ledger(source_packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    dimension_targets = {
        "d1_intent": "/dimensions/D1_INTENT/profile_ref",
        "d2_state": "/dimensions/D2_STATE/profile_ref",
        "d3_coordinate": "/dimensions/D3_COORDINATE/profile_ref",
        "d4_evidence": "/dimensions/D4_EVIDENCE/profile_ref",
        "d5_execution": "/dimensions/D5_EXECUTION/profile_ref",
    }
    ledger: list[dict[str, Any]] = []
    for source_path, source_value in _iter_leaf_paths(source_packet):
        top = source_path.split("/", 2)[1]
        classification = "EVIDENCE_ONLY"
        targets = ["/dimensions/D6_GENERATIVE_TRANSMISSION/references"]
        if source_path == "/packet_id":
            classification = "DIRECT"
            targets = ["/envelope/packet_id", "/dimensions/D8_ENVELOPE/packet_id"]
        elif source_path == "/packet_canonical_id":
            classification = "DIRECT"
            targets = ["/canonical_id"]
        elif source_path.startswith("/d5_execution/forbidden_effects/"):
            classification = "NORMALIZED_BY_EXACT_RULE"
            targets = [
                "/dimensions/D5_EXECUTION/profile_ref",
                "/risk/hard_risks",
                "/dimensions/D7_RISK/hard_risks",
            ]
        elif top in dimension_targets:
            classification = "NORMALIZED_BY_EXACT_RULE"
            targets = [dimension_targets[top]]
        elif source_path == "/d6_transmission/protocol":
            classification = "DIRECT"
            targets = ["/dimensions/D6_GENERATIVE_TRANSMISSION/protocol"]
        elif source_path == "/d7_risk/nonce":
            classification = "DIRECT"
            targets = ["/envelope/nonce", "/dimensions/D8_ENVELOPE/nonce"]
        elif source_path in {
            "/d7_risk/issued_at",
            "/d7_risk/expires_at",
            "/d7_risk/replay_window",
        }:
            classification = "NORMALIZED_BY_EXACT_RULE"
            targets = ["/envelope/ttl_seconds", "/transmission_packet/ttl"]
        ledger.append(
            {
                "source_path": source_path,
                "source_value_sha256": canonical_sha256(source_value),
                "classification": classification,
                "target_paths": targets,
            }
        )
    return ledger


def _validate_cross_bindings(request: Mapping[str, Any]) -> None:
    """Reject contradictory sidecar fields before any Canonical projection."""

    requirements = request["canonical_requirements"]
    d6 = requirements["d6"]
    generation = requirements["generation"]
    transmission = requirements["transmission"]
    verification = requirements["verification"]
    source = request["source_packet"]
    comparisons = (
        (d6["routing"], transmission["routing"], "$.canonical_requirements.transmission.routing"),
        (
            d6["merge_conditions"],
            transmission["merge_conditions"],
            "$.canonical_requirements.transmission.merge_conditions",
        ),
        (
            d6["generation_rules"],
            generation["generation_rules"],
            "$.canonical_requirements.generation.generation_rules",
        ),
        (
            d6["reconstruction_contract"],
            generation["reconstruction_contract"],
            "$.canonical_requirements.generation.reconstruction_contract",
        ),
        (
            d6["verification_contract"],
            generation["verification_contract"],
            "$.canonical_requirements.generation.verification_contract",
        ),
        (
            d6["verification_contract"],
            verification["contract_ref"],
            "$.canonical_requirements.verification.contract_ref",
        ),
        (
            requirements["envelope"]["authority_ref"],
            source["d8_envelope"]["key_registry_id"],
            "$.canonical_requirements.envelope.authority_ref",
        ),
    )
    for left, right, path in comparisons:
        if left != right:
            raise AdapterError("HOLD_CANONICAL_BINDING_INCONSISTENT", path)


def _build_canonical_packet(
    request: Mapping[str, Any],
    manifest_state: Mapping[str, Any],
    ttl_seconds: int,
) -> dict[str, Any]:
    source = request["source_packet"]
    requirements = request["canonical_requirements"]
    d6_requirements = requirements["d6"]
    generation_requirements = requirements["generation"]
    transmission_requirements = requirements["transmission"]
    reconstruction_requirements = requirements["reconstruction"]
    verification_requirements = requirements["verification"]
    envelope_requirements = requirements["envelope"]

    dimension_refs = {
        key: _dimension_profile_ref(source, key)
        for key in (
            "d1_intent",
            "d2_state",
            "d3_coordinate",
            "d4_evidence",
            "d5_execution",
        )
    }
    source_packet_ref = (
        "w7tp-v2.3-source-packet:sha256:" + request["source_packet_canonical_sha256"]
    )
    identity_map_ref = "w7tp-five-skill-identity-map:sha256:" + request[
        "identity_map_self_sha256"
    ]
    adapter_request_ref = (
        "w7tp-v2.3-adapter-request:sha256:" + request["request_self_sha256"]
    )
    manifest_refs = [
        f"w7tp-skill-manifest:{source_key}:sha256:{item['manifest_file_sha256']}"
        for source_key, item in sorted(manifest_state["bindings"].items())
    ]
    references = sorted(
        set(
            d6_requirements["references"]
            + [source_packet_ref, identity_map_ref, adapter_request_ref]
            + manifest_refs
        )
    )
    transmission_references = sorted(
        set(transmission_requirements["references"] + references)
    )

    d6 = {
        "protocol": source["d6_transmission"]["protocol"],
        "routing": d6_requirements["routing"],
        "segmentation": d6_requirements["segmentation"],
        "merge_conditions": list(d6_requirements["merge_conditions"]),
        "lookup": {"profile_ref": requirements["lookup_profile_ref"]},
        "references": references,
        "generation_rules": list(d6_requirements["generation_rules"]),
        "reconstruction_contract": d6_requirements["reconstruction_contract"],
        "verification_contract": d6_requirements["verification_contract"],
        "residual": list(d6_requirements["residual"]),
        "refill_policy": d6_requirements["refill_policy"],
        "on_demand_materialization": d6_requirements["on_demand_materialization"],
    }
    risk = {
        "hard_risks": ["DB_WRITE", "DEPLOY", "ROUTER_WRITE"],
        "decision": "HOLD",
    }
    envelope = {
        "packet_id": source["packet_id"],
        "authority_ref": envelope_requirements["authority_ref"],
        "version": envelope_requirements["version"],
        "ttl_seconds": ttl_seconds,
        "nonce": source["d7_risk"]["nonce"],
        "verifier_ref": envelope_requirements["verifier_ref"],
        "seal_policy": envelope_requirements["seal_policy"],
    }
    state_profile = {"profile_ref": source["d2_state"]["state_profile"]}
    coordinate_profile = {"profile_ref": source["d3_coordinate"]["coordinate_profile"]}
    lookup_profile = {"profile_ref": requirements["lookup_profile_ref"]}
    packet = {
        "canonical_id": source["packet_canonical_id"],
        "version": CANONICAL_VERSION,
        "packet_core": CANONICAL_CORE,
        "technology_flags": dict(TECHNOLOGY_FLAGS),
        "dimensions": {
            "D1_INTENT": dimension_refs["d1_intent"],
            "D2_STATE": dimension_refs["d2_state"],
            "D3_COORDINATE": dimension_refs["d3_coordinate"],
            "D4_EVIDENCE": dimension_refs["d4_evidence"],
            "D5_EXECUTION": dimension_refs["d5_execution"],
            "D6_GENERATIVE_TRANSMISSION": d6,
            "D7_RISK": deepcopy(risk),
            "D8_ENVELOPE": deepcopy(envelope),
        },
        "domain_profile": {
            "domain": requirements["domain"],
            "state_profile": state_profile,
            "coordinate_profile": coordinate_profile,
            "lookup_profile": lookup_profile,
            "generation_profile": {"profile_ref": requirements["generation_profile_ref"]},
            "reconstruction_profile": {
                "profile_ref": requirements["reconstruction_profile_ref"]
            },
            "verification_profile": {"profile_ref": requirements["verification_profile_ref"]},
        },
        "generation_packet": {
            "state": state_profile,
            "coordinate": coordinate_profile,
            "lookup": lookup_profile,
            "generation_rule": list(generation_requirements["generation_rules"]),
            "reconstruction_contract": generation_requirements[
                "reconstruction_contract"
            ],
            "verification_contract": generation_requirements["verification_contract"],
            "target_equivalence": generation_requirements["target_equivalence"],
        },
        "transmission_packet": {
            "routing": transmission_requirements["routing"],
            "path": list(transmission_requirements["path"]),
            "segment": transmission_requirements["segment"],
            "order": transmission_requirements["order"],
            "ttl": ttl_seconds,
            "reference": transmission_references,
            "hash": request["source_packet_raw_sha256"],
            "merge_condition": list(transmission_requirements["merge_conditions"]),
            "delivery_state": "HOLD",
        },
        "composition_mode": requirements["composition_mode"],
        "reconstruction": {
            "core": list(CANONICAL_RECONSTRUCTION_CORE),
            "zero_prior_content_receiver": reconstruction_requirements[
                "zero_prior_content_receiver"
            ],
            "materialization": reconstruction_requirements["materialization"],
            "economic_mode": reconstruction_requirements["economic_mode"],
        },
        "verification": {
            "level": verification_requirements["level"],
            "method_ref": verification_requirements["method_ref"],
            "contract_ref": verification_requirements["contract_ref"],
            "decision": "HOLD",
        },
        "risk": deepcopy(risk),
        "envelope": deepcopy(envelope),
    }
    packet_hash = canonical_packet_sha256(packet)
    packet["envelope"]["sha256"] = packet_hash
    packet["dimensions"]["D8_ENVELOPE"]["sha256"] = packet_hash
    return packet


def _hold_receipt(
    error: AdapterError,
    source_packet_raw_sha256: str | None,
) -> dict[str, Any]:
    return {
        "state": f"{error.decision}_ADAPTER_CONTRACT",
        "decision": error.decision,
        "reason_code": error.reason_code,
        "path": error.path,
        "source_schema_version": "2.3",
        "target_canonical_version": CANONICAL_VERSION,
        "source_packet_raw_sha256": source_packet_raw_sha256,
        "source_packet_canonical_sha256": None,
        "request_self_sha256": None,
        "identity_map_self_sha256": None,
        "manifest_aggregate_sha256": None,
        "canonical_packet_sha256": None,
        "canonical_packet": None,
        "projection_ledger": [],
        "candidate_only": True,
        "authority_granted": False,
        "side_effects": dict(NO_SIDE_EFFECTS),
    }


def adapt_review_candidate_v2_3(
    source_packet_bytes: bytes,
    adapter_request: Mapping[str, Any],
    *,
    workspace_root: Path = ROOT,
    identity_map: Mapping[str, Any] | None = None,
    now: datetime | None = None,
    seen_nonces: Collection[str] = (),
) -> dict[str, Any]:
    """Reconstruct a separate Canonical V2 L3 candidate or return HOLD/BLOCK."""

    raw_hash: str | None = None
    try:
        if not isinstance(source_packet_bytes, bytes):
            raise AdapterError("HOLD_SOURCE_PACKET_BYTES_REQUIRED")
        raw_hash = hashlib.sha256(source_packet_bytes).hexdigest()
        if not isinstance(adapter_request, Mapping):
            raise AdapterError("HOLD_ADAPTER_REQUEST_OBJECT_REQUIRED")
        request = _copy_json(
            dict(adapter_request),
            "HOLD_ADAPTER_REQUEST_NOT_CANONICAL_JSON",
        )
        _authority_injection(request.get("source_packet"))
        _validate_schema(
            request,
            ADAPTER_REQUEST_SCHEMA_PATH,
            "HOLD_ADAPTER_REQUEST_SCHEMA_INVALID",
        )
        if request["request_self_hash_algorithm"] != REQUEST_SELF_HASH_ALGORITHM:
            raise AdapterError("HOLD_REQUEST_SELF_HASH_ALGORITHM")
        if request_self_sha256(request) != request["request_self_sha256"]:
            raise AdapterError("HOLD_REQUEST_SELF_HASH_MISMATCH")
        _validate_cross_bindings(request)

        parsed_source = strict_json_bytes(
            source_packet_bytes,
            "HOLD_SOURCE_PACKET_JSON_INVALID",
        )
        if parsed_source != request["source_packet"]:
            raise AdapterError("HOLD_SOURCE_PACKET_BYTES_OBJECT_MISMATCH")
        if raw_hash != request["source_packet_raw_sha256"]:
            raise AdapterError("HOLD_SOURCE_PACKET_RAW_HASH_MISMATCH")
        source_canonical_hash = canonical_sha256(parsed_source)
        if source_canonical_hash != request["source_packet_canonical_sha256"]:
            raise AdapterError("HOLD_SOURCE_PACKET_CANONICAL_HASH_MISMATCH")

        mapping = validate_identity_map(identity_map, workspace_root=workspace_root)
        if request["identity_map_ref"] != IDENTITY_MAP_REF:
            raise AdapterError("HOLD_IDENTITY_MAP_REF_MISMATCH")
        if request["identity_map_self_sha256"] != mapping["binding_matrix_self_sha256"]:
            raise AdapterError("HOLD_IDENTITY_MAP_HASH_MISMATCH")

        manifest_state = inspect_skill_manifest_bindings(
            mapping,
            workspace_root=workspace_root,
        )
        if manifest_state["state"] != "PASS_EXACT_FIVE_MANIFESTS_HASH_BOUND":
            raise AdapterError(
                manifest_state.get("reason_code") or "HOLD_MANIFEST_BINDING_INCOMPLETE",
                manifest_state.get("path", "$.manifest_bindings"),
            )
        for source_key, measured in manifest_state["bindings"].items():
            supplied = request["manifest_bindings"][source_key]
            expected = {
                "manifest_path": measured["manifest_path"],
                "manifest_file_sha256": measured["manifest_file_sha256"],
                "package_id": measured["package_id"],
            }
            if supplied != expected:
                raise AdapterError(
                    "HOLD_MANIFEST_FILE_HASH_MISMATCH",
                    f"$.manifest_bindings.{source_key}",
                )
            source_hash = parsed_source["d4_evidence"]["skill_manifest_hashes"][
                source_key
            ]
            if source_hash != measured["manifest_file_sha256"]:
                raise AdapterError(
                    "HOLD_SOURCE_MANIFEST_HASH_MISMATCH",
                    f"$.source_packet.d4_evidence.skill_manifest_hashes.{source_key}",
                )

        issued_at = _parse_utc(parsed_source["d7_risk"]["issued_at"], "$.d7_risk.issued_at")
        expires_at = _parse_utc(
            parsed_source["d7_risk"]["expires_at"],
            "$.d7_risk.expires_at",
        )
        delta = (expires_at - issued_at).total_seconds()
        if delta <= 0 or not delta.is_integer():
            raise AdapterError("HOLD_PACKET_TTL_INVALID", "$.d7_risk")
        ttl_seconds = int(delta)
        if int(parsed_source["d7_risk"]["replay_window"]) != ttl_seconds:
            raise AdapterError("HOLD_TTL_REPLAY_WINDOW_MISMATCH", "$.d7_risk.replay_window")
        evaluated_at = now or datetime.now(timezone.utc)
        if evaluated_at.tzinfo is None:
            raise AdapterError("HOLD_EVALUATION_TIMEZONE_REQUIRED")
        evaluated_at = evaluated_at.astimezone(timezone.utc)
        if evaluated_at < issued_at:
            raise AdapterError("HOLD_PACKET_NOT_YET_VALID", "$.d7_risk.issued_at")
        if evaluated_at >= expires_at:
            raise AdapterError("HOLD_PACKET_EXPIRED", "$.d7_risk.expires_at")
        if parsed_source["d7_risk"]["nonce"] in seen_nonces:
            raise AdapterError("HOLD_REPLAY_DETECTED", "$.d7_risk.nonce")

        canonical_packet = _build_canonical_packet(request, manifest_state, ttl_seconds)
        _validate_schema(
            canonical_packet,
            CANONICAL_SCHEMA_PATH,
            "HOLD_CANONICAL_INSTANCE_SCHEMA_INVALID",
        )
        if canonical_packet["risk"] != canonical_packet["dimensions"]["D7_RISK"]:
            raise AdapterError("HOLD_DUPLICATED_D7_PROJECTION_MISMATCH")
        if canonical_packet["envelope"] != canonical_packet["dimensions"]["D8_ENVELOPE"]:
            raise AdapterError("HOLD_DUPLICATED_D8_PROJECTION_MISMATCH")
        if not verify_canonical_packet_hash(canonical_packet):
            raise AdapterError("HOLD_CANONICAL_PACKET_HASH_MISMATCH")

        ledger = _projection_ledger(parsed_source)
        return {
            "state": "PASS_ADAPTER_CONTRACT_RECONSTRUCTED_CANDIDATE",
            "decision": "HOLD",
            "reason_code": "HOLD_AWAITING_FOUNDER_LOCAL_SEAL_AND_TOTAL_FIELD_REVIEW",
            "source_schema_version": "2.3",
            "target_canonical_version": CANONICAL_VERSION,
            "source_packet_raw_sha256": raw_hash,
            "source_packet_canonical_sha256": source_canonical_hash,
            "request_self_sha256": request["request_self_sha256"],
            "identity_map_self_sha256": mapping["binding_matrix_self_sha256"],
            "manifest_aggregate_sha256": manifest_state["manifest_aggregate_sha256"],
            "canonical_packet_hash_algorithm": CANONICAL_PACKET_HASH_ALGORITHM,
            "canonical_packet_sha256": canonical_packet["envelope"]["sha256"],
            "source_packet": deepcopy(parsed_source),
            "canonical_packet": canonical_packet,
            "projection_ledger": ledger,
            "source_leaf_count": len(ledger),
            "unclassified_source_paths": [],
            "candidate_only": True,
            "authority_granted": False,
            "side_effects": dict(NO_SIDE_EFFECTS),
        }
    except AdapterError as exc:
        return _hold_receipt(exc, raw_hash)
    except Exception:
        return _hold_receipt(
            AdapterError("HOLD_UNEXPECTED_ADAPTER_FAILURE"),
            raw_hash,
        )


__all__ = [
    "ADAPTER_REQUEST_SCHEMA_PATH",
    "AdapterError",
    "CANONICAL_PACKET_HASH_ALGORITHM",
    "IDENTITY_MAP_PATH",
    "IDENTITY_MAP_REF",
    "adapt_review_candidate_v2_3",
    "canonical_packet_sha256",
    "inspect_skill_manifest_bindings",
    "request_self_sha256",
    "strict_json_bytes",
    "validate_identity_map",
    "verify_canonical_packet_hash",
    "with_request_self_hash",
]
