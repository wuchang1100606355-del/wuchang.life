"""Rule-ref minimum Origin State packet with local-only reconstruction capability.

This module is a successor contract. It does not modify the existing Origin Cell
implementation, canonical pointers, or Total Field authority. The transmitted
packet carries state/coordinate references and irreducible minimum information;
the reconstruction rule body remains local.
"""

from __future__ import annotations

import contextlib
import copy
import ctypes
import hashlib
import importlib.util
import json
import mmap
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterator, Mapping

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "configs/total_field/w7tp_local_origin_state_rule_registry_v1.json"
PACKET_SCHEMA = "w7tp-8dadi-origin-state-minimum-packet/2.3-successor"
PACKET_TYPE = "ORIGIN_STATE_MINIMUM_PACKET"
PROTOCOL_VERSION = "2.3-successor"
DIMENSIONS = tuple(f"D{i}" for i in range(1, 9))
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+:-]{0,511}$")
FORBIDDEN_PACKET_KEYS = frozenset({
    "reconstruction_rules",
    "execution_order",
    "rule_body",
    "rule_body_sha256",
    "diff",
    "delta",
    "patch",
    "patch_cells",
    "compressed_payload",
    "compressed_blob",
    "literal_bytes",
    "target_artifact",
    "target_data",
    "target_payload",
    "previous_state",
    "prior_state",
})

TOP_LEVEL_KEYS = frozenset({
    "schema_version",
    "packet_type",
    "protocol_version",
    "packet_ref",
    "adi_coordinate_ref",
    "state_ref",
    "state_version_ref",
    "joint_state_field",
    "rule_binding",
    "minimum_new_information",
    "necessary_condition_refs",
    "verification",
    "packet_sha256",
})
class MinimumPacketHold(RuntimeError):
    """Stable fail-closed error for the successor packet path."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _packet_hash_basis(packet: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(packet))
    value.pop("packet_sha256", None)
    return value
def packet_sha256(packet: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(_packet_hash_basis(packet)))


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _require_ref(value: Any, code: str) -> str:
    if not isinstance(value, str) or REF_RE.fullmatch(value) is None:
        raise MinimumPacketHold(code)
    return value


def _walk_keys(value: Any) -> Iterator[str]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            yield str(key).strip().lower().replace("-", "_")
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)


def _load_json_object(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MinimumPacketHold(code) from exc
    if not isinstance(value, dict):
        raise MinimumPacketHold(code)
    return value
def _load_python_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(
        "w7tp_origin_state_local_rule_capability",
        path,
    )
    if spec is None or spec.loader is None:
        raise MinimumPacketHold("HOLD_LOCAL_RULE_IMPLEMENTATION_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_rule_registry(
    *,
    root: Path = ROOT,
    registry_path: Path = REGISTRY_PATH,
) -> dict[str, dict[str, Any]]:
    registry = _load_json_object(
        registry_path,
        "HOLD_LOCAL_RULE_REGISTRY_UNREADABLE",
    )
    if (
        registry.get("schema_id")
        != "W7TP_LOCAL_ORIGIN_STATE_RULE_REGISTRY_V1"
        or registry.get("state") != "LOCAL_ONLY_RULE_CAPABILITY_REGISTRY"
        or registry.get("cloud_visible") is not False
    ):
        raise MinimumPacketHold("HOLD_LOCAL_RULE_REGISTRY_POLICY_MISMATCH")

    entries = registry.get("rules")
    if not isinstance(entries, list) or not entries:
        raise MinimumPacketHold("HOLD_LOCAL_RULE_REGISTRY_EMPTY")
    resolved: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise MinimumPacketHold("HOLD_LOCAL_RULE_REGISTRY_ENTRY_INVALID")
        rule_ref = _require_ref(
            entry.get("rule_ref"),
            "HOLD_LOCAL_RULE_REF_INVALID",
        )
        implementation_ref = entry.get("implementation_ref")
        if not isinstance(implementation_ref, str) or not implementation_ref:
            raise MinimumPacketHold("HOLD_LOCAL_RULE_IMPLEMENTATION_REF_INVALID")
        implementation_path = (root / implementation_ref).resolve()
        try:
            implementation_path.relative_to(root.resolve())
        except ValueError as exc:
            raise MinimumPacketHold("HOLD_LOCAL_RULE_PATH_OUTSIDE_ROOT") from exc
        observed_hash = sha256_file(implementation_path)
        if observed_hash != entry.get("implementation_sha256"):
            raise MinimumPacketHold("HOLD_LOCAL_RULE_IMPLEMENTATION_HASH_MISMATCH")
        if entry.get("storage_policy") != "LOCAL_ONLY":
            raise MinimumPacketHold("HOLD_LOCAL_RULE_STORAGE_POLICY_MISMATCH")
        if entry.get("packet_rule_body_allowed") is not False:
            raise MinimumPacketHold("HOLD_PACKET_RULE_BODY_POLICY_MISMATCH")
        resolved[rule_ref] = {
            **entry,
            "implementation_path": implementation_path,
        }
    return resolved
def _resolve_rule_capability(
    packet: Mapping[str, Any],
    *,
    root: Path = ROOT,
    registry_path: Path = REGISTRY_PATH,
) -> tuple[dict[str, Any], Any]:
    binding = packet.get("rule_binding")
    if not isinstance(binding, Mapping):
        raise MinimumPacketHold("HOLD_RULE_BINDING_MISSING")
    rule_ref = _require_ref(
        binding.get("rule_ref"),
        "HOLD_LOCAL_RULE_REF_INVALID",
    )
    registry = load_rule_registry(root=root, registry_path=registry_path)
    entry = registry.get(rule_ref)
    if entry is None:
        raise MinimumPacketHold("HOLD_LOCAL_RULE_REF_UNRESOLVED")
    if binding.get("implementation_ref") != entry.get("implementation_ref"):
        raise MinimumPacketHold("HOLD_LOCAL_RULE_IMPLEMENTATION_REF_MISMATCH")
    if binding.get("implementation_sha256") != entry.get("implementation_sha256"):
        raise MinimumPacketHold("HOLD_LOCAL_RULE_HASH_MISMATCH")
    expected_keys = entry.get("minimum_information_keys")
    if binding.get("minimum_information_keys") != expected_keys:
        raise MinimumPacketHold("HOLD_MINIMUM_INFORMATION_CONTRACT_MISMATCH")
    return entry, _load_python_module(entry["implementation_path"])
def validate_minimum_packet(
    packet: Mapping[str, Any],
    *,
    root: Path = ROOT,
    registry_path: Path = REGISTRY_PATH,
) -> dict[str, Any]:
    if not isinstance(packet, Mapping) or set(packet) != TOP_LEVEL_KEYS:
        raise MinimumPacketHold("HOLD_MINIMUM_PACKET_SHAPE_INVALID")
    if packet.get("schema_version") != PACKET_SCHEMA:
        raise MinimumPacketHold("HOLD_MINIMUM_PACKET_SCHEMA_MISMATCH")
    if packet.get("packet_type") != PACKET_TYPE:
        raise MinimumPacketHold("HOLD_MINIMUM_PACKET_TYPE_MISMATCH")
    if packet.get("protocol_version") != PROTOCOL_VERSION:
        raise MinimumPacketHold("HOLD_MINIMUM_PACKET_PROTOCOL_MISMATCH")
    if packet.get("packet_sha256") != packet_sha256(packet):
        raise MinimumPacketHold("HOLD_MINIMUM_PACKET_SELF_HASH_MISMATCH")

    found_forbidden = FORBIDDEN_PACKET_KEYS.intersection(_walk_keys(packet))
    if found_forbidden:
        raise MinimumPacketHold("HOLD_MINIMUM_PACKET_RULE_OR_PAYLOAD_CONTAMINATION")

    for field in ("packet_ref", "adi_coordinate_ref", "state_ref", "state_version_ref"):
        _require_ref(packet.get(field), f"HOLD_{field.upper()}_INVALID")

    field = packet.get("joint_state_field")
    if not isinstance(field, Mapping) or any(dim not in field for dim in DIMENSIONS):
        raise MinimumPacketHold("HOLD_MINIMUM_PACKET_8D_FIELD_INCOMPLETE")
    d6 = field.get("D6")
    if (
        not isinstance(d6, Mapping)
        or d6.get("mode") != "LOCAL_RULE_REF_MINIMUM_STATE"
        or d6.get("rule_body_transmitted") is not False
        or d6.get("target_bytes_transmitted") != 0
        or d6.get("differential_payload_bytes") != 0
        or d6.get("compression_payload_bytes") != 0
        or d6.get("persistent_materialization_default") is not False
    ):
        raise MinimumPacketHold("HOLD_MINIMUM_PACKET_D6_CONTRACT_MISMATCH")

    d8 = field.get("D8")
    if (
        not isinstance(d8, Mapping)
        or d8.get("authority") != "CANDIDATE_ONLY"
        or d8.get("canonical") is not False
        or d8.get("formal_effect_authority") != "LOCAL_TOTAL_FIELD"
    ):
        raise MinimumPacketHold("HOLD_MINIMUM_PACKET_D8_BOUNDARY_INVALID")

    entry, module = _resolve_rule_capability(
        packet,
        root=root,
        registry_path=registry_path,
    )
    minimum = packet.get("minimum_new_information")
    required_keys = entry.get("minimum_information_keys")
    if not isinstance(minimum, Mapping) or set(minimum) != set(required_keys):
        raise MinimumPacketHold("HOLD_MINIMUM_INFORMATION_SHAPE_MISMATCH")
    verification = packet.get("verification")
    if (
        not isinstance(verification, Mapping)
        or set(verification)
        != {"expected_target_manifest_sha256", "expected_target_bytes"}
        or not _valid_sha256(verification.get("expected_target_manifest_sha256"))
        or not isinstance(verification.get("expected_target_bytes"), int)
        or isinstance(verification.get("expected_target_bytes"), bool)
        or verification.get("expected_target_bytes") < 0
    ):
        raise MinimumPacketHold("HOLD_MINIMUM_PACKET_VERIFICATION_INVALID")

    conditions = packet.get("necessary_condition_refs")
    if (
        not isinstance(conditions, list)
        or not conditions
        or len(conditions) != len(set(conditions))
    ):
        raise MinimumPacketHold("HOLD_MINIMUM_PACKET_CONDITIONS_INVALID")
    for value in conditions:
        _require_ref(value, "HOLD_MINIMUM_PACKET_CONDITION_REF_INVALID")
    return {"rule_entry": entry, "rule_module": module}


def _fixture_source_recipe_path(source_root: Path) -> Path:
    return source_root.parent / f"{source_root.name}.gst-source-recipe.json"


def build_fixture_minimum_packet(
    source_root: Path,
    *,
    adi_coordinate_ref: str,
    state_ref: str,
    state_version_ref: str,
    packet_ref: str,
    root: Path = ROOT,
    registry_path: Path = REGISTRY_PATH,
) -> dict[str, Any]:
    registry = load_rule_registry(root=root, registry_path=registry_path)
    rule_ref = "local-rule:w7tp-origin-cell-fixture-recipe/v2"
    entry = registry.get(rule_ref)
    if entry is None:
        raise MinimumPacketHold("HOLD_LOCAL_RULE_REF_UNRESOLVED")
    module = _load_python_module(entry["implementation_path"])
    recipe = _load_json_object(
        _fixture_source_recipe_path(source_root),
        "HOLD_SOURCE_GENERATIVE_PROVENANCE_MISSING",
    )
    if recipe.get("schema") != "w7tp-source-generative-provenance/1-candidate":
        raise MinimumPacketHold("HOLD_SOURCE_GENERATIVE_PROVENANCE_INVALID")
    minimum = {
        "dataset_mib": recipe.get("dataset_mib"),
        "variant": recipe.get("variant"),
    }
    rows, target_bytes, target_manifest = module.file_manifest(source_root)

    packet: dict[str, Any] = {
        "schema_version": PACKET_SCHEMA,
        "packet_type": PACKET_TYPE,
        "protocol_version": PROTOCOL_VERSION,
        "packet_ref": _require_ref(packet_ref, "HOLD_PACKET_REF_INVALID"),
        "adi_coordinate_ref": _require_ref(
            adi_coordinate_ref,
            "HOLD_ADI_COORDINATE_REF_INVALID",
        ),
        "state_ref": _require_ref(state_ref, "HOLD_STATE_REF_INVALID"),
        "state_version_ref": _require_ref(
            state_version_ref,
            "HOLD_STATE_VERSION_REF_INVALID",
        ),
        "joint_state_field": {
            "D1": {"intent": "RECONSTRUCT_TARGET_FROM_LOCAL_RULE_REF_AND_MINIMUM_STATE"},
            "D2": {
                "transition": "VOLATILE_WORKSET_TO_VERIFIED_TARGET",
                "target_manifest_sha256": target_manifest,
            },
            "D3": {
                "adi_coordinate_ref": adi_coordinate_ref,
                "packet_storage": "EXTERNAL_OR_LOCAL_STATE_PACKET_NODE",
                "reconstruction_location": "LOCAL_VOLATILE_MEMORY_FIRST",
            },
            "D4": {
                "rule_implementation_sha256": entry["implementation_sha256"],
                "target_files": len(rows),
            },
            "D5": {
                "execution_policy": "LOCAL_VOLATILE_RECONSTRUCTION_ONLY",
                "persistent_materialization_default": False,
                "canonical_write": False,
                "service_restart": False,
            },
            "D6": {
                "mode": "LOCAL_RULE_REF_MINIMUM_STATE",
                "rule_body_transmitted": False,
                "target_bytes_transmitted": 0,
                "differential_payload_bytes": 0,
                "compression_payload_bytes": 0,
                "persistent_materialization_default": False,
            },
            "D7": {
                "fail_closed_on_rule_ref_miss": True,
                "fail_closed_on_rule_hash_mismatch": True,
                "fail_closed_on_packet_hash_mismatch": True,
                "fail_closed_on_final_manifest_mismatch": True,
            },
            "D8": {
                "authority": "CANDIDATE_ONLY",
                "canonical": False,
                "formal_effect_authority": "LOCAL_TOTAL_FIELD",
            },
            "coupling_rule": "ALL_D1_D8_COORDINATES_BIND_ONE_GENERATION_TRANSITION",
        },
        "rule_binding": {
            "rule_ref": rule_ref,
            "implementation_ref": entry["implementation_ref"],
            "implementation_sha256": entry["implementation_sha256"],
            "minimum_information_keys": entry["minimum_information_keys"],
        },
        "minimum_new_information": minimum,
        "necessary_condition_refs": [
            "condition:local-rule-registry-required",
            "condition:volatile-workset-required",
            "condition:no-cloud-rule-body",
            "condition:final-manifest-match",
        ],
        "verification": {
            "expected_target_manifest_sha256": target_manifest,
            "expected_target_bytes": target_bytes,
        },
    }
    packet["packet_sha256"] = packet_sha256(packet)
    validate_minimum_packet(packet, root=root, registry_path=registry_path)
    return packet


def _tmpfs_available(path: Path) -> bool:
    try:
        return path.is_dir() and os.access(path, os.W_OK | os.X_OK)
    except OSError:
        return False


def probe_secret_memory() -> dict[str, Any]:
    """Probe Linux memfd_secret without retaining any payload."""

    syscall_number = 447
    libc = ctypes.CDLL(None, use_errno=True)
    fd = libc.syscall(syscall_number, 0)
    if fd < 0:
        errno_value = ctypes.get_errno()
        return {
            "supported": False,
            "errno": errno_value,
            "backend": "MEMFD_SECRET",
        }
    try:
        os.ftruncate(fd, 4096)
        region = mmap.mmap(
            fd,
            4096,
            flags=mmap.MAP_SHARED,
            prot=mmap.PROT_READ | mmap.PROT_WRITE,
        )
        try:
            region[:16] = b"W7TP_SECRET_OK!!"
            ok = region[:16] == b"W7TP_SECRET_OK!!"
        finally:
            region.close()
        return {
            "supported": bool(ok),
            "backend": "MEMFD_SECRET",
            "swap_policy": "LOCKED_NO_SWAP_BY_KERNEL_CONTRACT",
        }
    finally:
        os.close(fd)


@contextlib.contextmanager
def volatile_reconstruction(
    packet: Mapping[str, Any],
    *,
    root: Path = ROOT,
    registry_path: Path = REGISTRY_PATH,
    tmpfs_root: Path = Path("/dev/shm"),
) -> Iterator[dict[str, Any]]:
    """Reconstruct into a volatile filesystem workset and remove it on exit."""

    resolved = validate_minimum_packet(
        packet,
        root=root,
        registry_path=registry_path,
    )
    if not _tmpfs_available(tmpfs_root):
        raise MinimumPacketHold("HOLD_VOLATILE_WORKSET_UNAVAILABLE")

    entry = resolved["rule_entry"]
    module = resolved["rule_module"]
    builder = getattr(module, entry.get("builder_symbol"), None)
    executor = getattr(module, entry.get("executor_symbol"), None)
    manifest = getattr(module, entry.get("manifest_symbol"), None)
    if not all(callable(value) for value in (builder, executor, manifest)):
        raise MinimumPacketHold("HOLD_LOCAL_RULE_SYMBOL_BINDING_INVALID")

    minimum = dict(packet["minimum_new_information"])
    try:
        recipe = builder(**minimum)
    except TypeError as exc:
        raise MinimumPacketHold(
            "HOLD_MINIMUM_INFORMATION_NOT_ACCEPTED_BY_RULE"
        ) from exc
    if not isinstance(recipe, Mapping):
        raise MinimumPacketHold("HOLD_LOCAL_RULE_RECIPE_INVALID")

    workset = Path(
        tempfile.mkdtemp(prefix="w7tp-origin-state-", dir=tmpfs_root)
    )
    output_root = workset / "reconstructed"
    output_root.mkdir()
    try:
        executor(
            output_root,
            copy.deepcopy(list(recipe["rules"])),
            copy.deepcopy(list(recipe["execution_order"])),
        )
        rows, observed_bytes, observed_manifest = manifest(output_root)
        expected = packet["verification"]
        if observed_manifest != expected["expected_target_manifest_sha256"]:
            raise MinimumPacketHold("HOLD_FINAL_MANIFEST_MISMATCH")
        if observed_bytes != expected["expected_target_bytes"]:
            raise MinimumPacketHold("HOLD_FINAL_SIZE_MISMATCH")

        receipt = {
            "state": "PASS_VOLATILE_LOCAL_RULE_RECONSTRUCTION",
            "packet_sha256": packet["packet_sha256"],
            "rule_ref": packet["rule_binding"]["rule_ref"],
            "rule_body_transmitted": False,
            "target_manifest_sha256": observed_manifest,
            "target_bytes": observed_bytes,
            "target_files": len(rows),
            "workset_backend": "TMPFS_VOLATILE_FS",
            "persistent_materialization": False,
            "cleanup_on_exit": True,
            "strict_no_swap_guarantee": False,
            "candidate_authority": False,
            "execution_authorized": False,
        }
        yield {"workset_path": output_root, "receipt": receipt}
    finally:
        shutil.rmtree(workset, ignore_errors=True)


__all__ = [
    "MinimumPacketHold",
    "PACKET_SCHEMA",
    "PACKET_TYPE",
    "build_fixture_minimum_packet",
    "load_rule_registry",
    "packet_sha256",
    "probe_secret_memory",
    "validate_minimum_packet",
    "volatile_reconstruction",
]
