"""Closed native-port and receiver boundaries for the candidate runtime.

This module verifies evidence; it never creates D8 authority.  All runtime
implementations are selected from explicit in-memory allowlists, never from
module names or free-form commands.
"""

from __future__ import annotations

import base64
import errno
import hashlib
import os
import stat
import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import ClassVar, Final, Iterator, Mapping, Protocol, Sequence
import unicodedata

from .canonical import (
    canonical_hash,
    canonical_json_bytes,
    canonical_json_loads,
    sha256_hex,
    sha256_ref,
    validate_sha256_hex,
    validate_sha256_ref,
)
from .models import (
    ApplyOutcome,
    ArtifactBinding,
    BindingSet,
    BindingState,
    DelegationRequest,
    EffectContract,
    EffectGateRequest,
    EffectObservation,
    EffectState,
    EvidenceLifecycleRequest,
    FlowRequest,
    Hold,
    IdempotencyClass,
    IngressRepresentationRequest,
    NativeProof,
    ObservationContext,
    PrepareContext,
    PreparedEffect,
    Quarantine,
    REQUIRED_NATIVE_CAPABILITIES,
    VerifiedEffectPermit,
    request_hash,
)
from .object_packet_store import (
    ObjectPacketStore,
    ObjectStoreConflict,
    ObjectStoreHold,
)


CAP_EXTERNAL_GATEWAY = "w7tp-external-capability-gateway"
CAP_EFFECT_GATE = "w7tp-deterministic-effect-gate"
CAP_DELEGATION = "w7tp-bounded-delegation-chain"
CAP_INFORMATION_FLOW = "w7tp-stateful-information-flow"
CAP_EVIDENCE_LIFECYCLE = "w7tp-execution-evidence-lifecycle"

MSI_MISSING_ANCHOR_REASON = (
    "MSI_CURRENT_WORKTREE_NATIVE_SKILLS_ANCHOR_MISSING"
)
MSI_BINDINGS_UNVERIFIED_REASON = (
    "MSI_CURRENT_WORKTREE_NATIVE_SKILLS_BINDINGS_UNVERIFIED"
)


class ExternalCapabilityGatewayPort(Protocol):
    def verify_ingress(
        self, request: IngressRepresentationRequest
    ) -> NativeProof: ...


class DeterministicEffectGatePort(Protocol):
    def verify_exact_authorization(
        self, request: EffectGateRequest
    ) -> VerifiedEffectPermit: ...


class BoundedDelegationChainPort(Protocol):
    def verify_delegation(self, request: DelegationRequest) -> NativeProof: ...


class StatefulInformationFlowPort(Protocol):
    def verify_flow(self, request: FlowRequest) -> NativeProof: ...


class ExecutionEvidenceLifecyclePort(Protocol):
    def verify_and_advance(
        self, request: EvidenceLifecycleRequest
    ) -> NativeProof: ...


@dataclass(frozen=True, slots=True)
class NativePorts:
    external_gateway: ExternalCapabilityGatewayPort
    effect_gate: DeterministicEffectGatePort
    delegation: BoundedDelegationChainPort
    information_flow: StatefulInformationFlowPort
    evidence_lifecycle: ExecutionEvidenceLifecyclePort


class ReceiverAdapter(Protocol):
    adapter_ref: ClassVar[str]

    def prepare(self, context: PrepareContext) -> PreparedEffect:
        """Perform read-only validation and return a sealed descriptor."""

    def observe(self, context: ObservationContext) -> EffectObservation:
        """Return receiver-backed evidence of the actual effect state."""


class EffectHandler(Protocol):
    handler_ref: ClassVar[str]
    idempotency: ClassVar[IdempotencyClass]

    def apply(
        self, prepared: PreparedEffect, exact_input: bytes
    ) -> ApplyOutcome: ...


def _native_proof_hash(
    capability_id: str,
    input_hash: str,
    verifier_ref: str,
) -> str:
    return canonical_hash(
        {
            "capability_id": capability_id,
            "input_hash": input_hash,
            "verifier_ref": verifier_ref,
        }
    )


def build_native_proof(
    capability_id: str,
    request: object,
    verifier_ref: str,
) -> NativeProof:
    """Build integrity evidence for tests or a native verifier implementation.

    This is not an authorization constructor.  Effect authorization remains a
    distinct D8 permit verified by ``require_exact_effect_permit``.
    """

    if capability_id not in REQUIRED_NATIVE_CAPABILITIES or not verifier_ref:
        raise Quarantine("NATIVE_PROOF_COORDINATE_CONFLICT")
    input_hash = request_hash(request)
    proof_hash = _native_proof_hash(capability_id, input_hash, verifier_ref)
    return NativeProof(
        capability_id=capability_id,
        input_hash=input_hash,
        proof_ref=f"sha256:{proof_hash}",
        proof_hash=proof_hash,
        verifier_ref=verifier_ref,
    )


def require_exact_native_proof(
    proof: NativeProof,
    request: object,
    expected_capability_id: str,
) -> NativeProof:
    """Require the proof to bind the exact request and verifier identity."""

    if proof.capability_id != expected_capability_id:
        raise Quarantine("NATIVE_PROOF_CAPABILITY_CONFLICT")
    expected_input_hash = request_hash(request)
    if proof.input_hash != expected_input_hash:
        raise Quarantine("NATIVE_PROOF_REQUEST_HASH_CONFLICT")
    expected_proof_hash = _native_proof_hash(
        proof.capability_id,
        proof.input_hash,
        proof.verifier_ref,
    )
    if proof.proof_hash != expected_proof_hash:
        raise Quarantine("NATIVE_PROOF_HASH_CONFLICT")
    if proof.proof_ref != f"sha256:{expected_proof_hash}":
        raise Quarantine("NATIVE_PROOF_REF_CONFLICT")
    return proof


def effect_permit_proof_body(
    permit: VerifiedEffectPermit,
) -> dict[str, object]:
    """Return the sealed proof body without creating D8 authority."""

    return {
        "schema_id": "W7TP_EFFECT_PERMIT_PROOF_V1",
        "request_hash": permit.bound_request_hash,
        "native_binding_ref": permit.native_binding_ref,
        "policy_allowed": permit.policy_allowed,
        "exact_d8_authorized": permit.exact_d8_authorized,
        "valid_until": permit.valid_until,
    }


def effect_permit_proof_bytes(permit: VerifiedEffectPermit) -> bytes:
    return canonical_json_bytes(effect_permit_proof_body(permit))


def effect_permit_proof_hash(permit: VerifiedEffectPermit) -> str:
    """Return the expected sealed-packet hash without granting authority."""

    return sha256_hex(effect_permit_proof_bytes(permit))


def _put_and_reload_exact_packet(
    objects: ObjectPacketStore,
    packet_ref: str,
    raw: bytes,
    *,
    unavailable_code: str,
    conflict_code: str,
    no_effect: bool,
) -> None:
    try:
        stored_ref = objects.put_exact(packet_ref, raw)
        loaded = objects.get_exact(packet_ref)
    except ObjectStoreHold as error:
        raise Hold(unavailable_code, no_effect=no_effect) from error
    except ObjectStoreConflict as error:
        raise Quarantine(conflict_code) from error
    if stored_ref != packet_ref or loaded != raw or sha256_ref(loaded) != packet_ref:
        raise Quarantine(conflict_code)


def seal_effect_permit_proof(
    permit: VerifiedEffectPermit,
    proof_store: ObjectPacketStore,
) -> VerifiedEffectPermit:
    """Persist a native verifier's decision; never decide authorization here."""

    raw = effect_permit_proof_bytes(permit)
    proof_hash = sha256_hex(raw)
    sealed = replace(
        permit,
        proof_ref=f"sha256:{proof_hash}",
        proof_hash=proof_hash,
    )
    _put_and_reload_exact_packet(
        proof_store,
        sealed.proof_ref,
        raw,
        unavailable_code="HOLD_EFFECT_PERMIT_PROOF_STORE_UNAVAILABLE",
        conflict_code="EFFECT_PERMIT_PROOF_STORE_CONFLICT",
        no_effect=True,
    )
    return sealed


def require_exact_effect_permit(
    permit: VerifiedEffectPermit,
    request: EffectGateRequest,
    *,
    proof_store: ObjectPacketStore,
    expected_native_binding_ref: str,
    now: datetime | None = None,
) -> VerifiedEffectPermit:
    """Verify a stored proof packet, exact gate binding, freshness and D8."""

    if permit.bound_request_hash != request_hash(request):
        raise Quarantine("EFFECT_PERMIT_REQUEST_HASH_CONFLICT")
    try:
        validate_sha256_ref(expected_native_binding_ref)
    except ValueError as error:
        raise Quarantine("EFFECT_PERMIT_EXPECTED_BINDING_REF_CONFLICT") from error
    if permit.native_binding_ref != expected_native_binding_ref:
        raise Quarantine("EFFECT_PERMIT_NATIVE_BINDING_CONFLICT")
    expected_raw = effect_permit_proof_bytes(permit)
    expected_proof_hash = effect_permit_proof_hash(permit)
    if permit.proof_hash != expected_proof_hash:
        raise Quarantine("EFFECT_PERMIT_PROOF_HASH_CONFLICT")
    if permit.proof_ref != f"sha256:{expected_proof_hash}":
        raise Quarantine("EFFECT_PERMIT_PROOF_REF_CONFLICT")
    try:
        observed_raw = proof_store.get_exact(permit.proof_ref)
    except ObjectStoreHold as error:
        raise Hold(
            "HOLD_EFFECT_PERMIT_PROOF_UNAVAILABLE", no_effect=True
        ) from error
    except ObjectStoreConflict as error:
        raise Quarantine("EFFECT_PERMIT_PROOF_BYTES_CONFLICT") from error
    if observed_raw != expected_raw or sha256_ref(observed_raw) != permit.proof_ref:
        raise Quarantine("EFFECT_PERMIT_PROOF_BYTES_CONFLICT")
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise Quarantine("EFFECT_PERMIT_NAIVE_CURRENT_TIME_CONFLICT")
    if permit.valid_until <= current:
        raise Hold("HOLD_EFFECT_PERMIT_EXPIRED", no_effect=True)
    if not permit.policy_allowed:
        raise Hold("HOLD_POLICY_DENIED", no_effect=True)
    if not permit.exact_d8_authorized:
        raise Hold("HOLD_EXACT_D8_AUTHORIZATION_MISSING", no_effect=True)
    return permit


class ExactArtifactBindingVerifier(Protocol):
    """Verify bytes and manifest at the binding's explicit coordinates."""

    def verify_artifact(self, binding: ArtifactBinding) -> bool: ...

    def verify_manifest(self, binding: ArtifactBinding) -> bool: ...


def artifact_binding_hash(binding: ArtifactBinding) -> str:
    return canonical_hash(binding.sealed_body())


class StaticBindingResolver:
    """Resolve only pre-supplied bindings and require exact byte evidence."""

    def __init__(
        self,
        bindings: Sequence[ArtifactBinding],
        verifier: ExactArtifactBindingVerifier,
    ) -> None:
        by_ref: dict[str, ArtifactBinding] = {}
        for binding in bindings:
            if binding.binding_ref in by_ref:
                raise Quarantine("DUPLICATE_BINDING_REF_CONFLICT")
            by_ref[binding.binding_ref] = binding
        self._bindings = MappingProxyType(by_ref)
        self._verifier = verifier

    def require_verified_exact_set(
        self,
        binding_refs: Sequence[str],
        required_capabilities: frozenset[str] = REQUIRED_NATIVE_CAPABILITIES,
    ) -> BindingSet:
        if len(tuple(binding_refs)) != len(set(binding_refs)):
            raise Quarantine("DUPLICATE_BINDING_SELECTION_CONFLICT")

        selected: list[ArtifactBinding] = []
        for binding_ref in binding_refs:
            binding = self._bindings.get(binding_ref)
            if binding is None:
                raise Hold("HOLD_NATIVE_BINDING_UNAVAILABLE", no_effect=True)
            if binding.binding_state is not BindingState.VERIFIED:
                raise Hold("HOLD_NATIVE_BINDING_NOT_VERIFIED", no_effect=True)
            expected_hash = artifact_binding_hash(binding)
            if binding.binding_hash != expected_hash:
                raise Quarantine("NATIVE_BINDING_HASH_CONFLICT")
            if binding.binding_ref != f"sha256:{expected_hash}":
                raise Quarantine("NATIVE_BINDING_REF_CONFLICT")
            if not self._verifier.verify_artifact(binding):
                raise Quarantine("NATIVE_ARTIFACT_BYTES_CONFLICT")
            if not self._verifier.verify_manifest(binding):
                raise Quarantine("NATIVE_MANIFEST_BYTES_CONFLICT")
            selected.append(binding)

        selected_capabilities = [item.capability_id for item in selected]
        if len(selected_capabilities) != len(set(selected_capabilities)):
            raise Quarantine("DUPLICATE_NATIVE_CAPABILITY_CONFLICT")
        if frozenset(selected_capabilities) != required_capabilities:
            raise Hold("HOLD_NATIVE_CAPABILITY_SET_INCOMPLETE", no_effect=True)

        return BindingSet(
            tuple(sorted(selected, key=lambda item: item.capability_id))
        )


class StaticNativeRegistry:
    """Bind verified coordinates to preconstructed, allowlisted port objects."""

    def __init__(self, ports: Mapping[str, object]) -> None:
        if not ports:
            raise ValueError("static native registry must not be empty")
        for binding_ref, port in ports.items():
            try:
                validate_sha256_ref(binding_ref)
            except ValueError as exc:
                raise ValueError("invalid static binding reference") from exc
            if isinstance(port, type):
                raise ValueError("invalid static native registry entry")
        self._ports = MappingProxyType(dict(ports))

    def bind_all_static(self, bindings: BindingSet) -> NativePorts:
        resolved: dict[str, object] = {}
        for binding in bindings.bindings:
            port = self._ports.get(binding.binding_ref)
            if port is None:
                raise Hold("HOLD_STATIC_NATIVE_ADAPTER_UNAVAILABLE", no_effect=True)
            required_method = {
                CAP_EXTERNAL_GATEWAY: "verify_ingress",
                CAP_EFFECT_GATE: "verify_exact_authorization",
                CAP_DELEGATION: "verify_delegation",
                CAP_INFORMATION_FLOW: "verify_flow",
                CAP_EVIDENCE_LIFECYCLE: "verify_and_advance",
            }.get(binding.capability_id)
            if required_method is None or not callable(
                getattr(port, required_method, None)
            ):
                raise Quarantine("STATIC_NATIVE_PORT_PROTOCOL_CONFLICT")
            resolved[binding.capability_id] = port

        if frozenset(resolved) != REQUIRED_NATIVE_CAPABILITIES:
            raise Hold("HOLD_NATIVE_CAPABILITY_SET_INCOMPLETE", no_effect=True)

        return NativePorts(
            external_gateway=resolved[CAP_EXTERNAL_GATEWAY],
            effect_gate=resolved[CAP_EFFECT_GATE],
            delegation=resolved[CAP_DELEGATION],
            information_flow=resolved[CAP_INFORMATION_FLOW],
            evidence_lifecycle=resolved[CAP_EVIDENCE_LIFECYCLE],
        )


@dataclass(frozen=True, slots=True)
class CurrentWorktreeBindingResolution:
    state: str
    reason: str
    scope: str
    root: str
    branch: str
    head: str


class CurrentWorktreeBindingResolver:
    """Make only a node/worktree-scoped observation about the native anchor."""

    def resolve_current_worktree_only(
        self,
        *,
        root: str | Path,
        branch: str,
        head: str,
        required_capabilities: frozenset[str] = REQUIRED_NATIVE_CAPABILITIES,
        anchor_relative_path: str = "capabilities",
    ) -> CurrentWorktreeBindingResolution:
        del required_capabilities  # Absence is scoped to the anchor, not global.
        root_path = Path(root)
        anchor = root_path / anchor_relative_path
        if not anchor.is_dir():
            return CurrentWorktreeBindingResolution(
                state="HOLD",
                reason=MSI_MISSING_ANCHOR_REASON,
                scope="MSI_CURRENT_WORKTREE_ONLY",
                root=str(root_path),
                branch=branch,
                head=head,
            )
        return CurrentWorktreeBindingResolution(
            state="HOLD",
            reason=MSI_BINDINGS_UNVERIFIED_REASON,
            scope="MSI_CURRENT_WORKTREE_ONLY",
            root=str(root_path),
            branch=branch,
            head=head,
        )


@dataclass(frozen=True, slots=True)
class LocalFileCoordinate:
    workspace_root: str
    workspace_id: str
    logical_path: str


_LOCAL_COORDINATE_PREFIX = "local-file-v1:"


def _validated_relative_parts(logical_path: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFC", logical_path)
    if (
        not normalized
        or normalized != logical_path
        or "\\" in normalized
        or "\x00" in normalized
    ):
        raise Quarantine("TARGET_LOGICAL_PATH_CONFLICT")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise Quarantine("TARGET_LOGICAL_PATH_CONFLICT")
    return tuple(pure.parts)


def encode_local_file_coordinate(
    workspace_root: str | Path,
    workspace_id: str,
    logical_path: str,
) -> str:
    root = Path(workspace_root)
    if not root.is_absolute() or not workspace_id:
        raise Quarantine("TARGET_WORKSPACE_COORDINATE_CONFLICT")
    _validated_relative_parts(logical_path)
    raw = canonical_json_bytes(
        {
            "workspace_root": str(root),
            "workspace_id": workspace_id,
            "logical_path": logical_path,
        }
    )
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"{_LOCAL_COORDINATE_PREFIX}{encoded}"


def decode_local_file_coordinate(ref: str) -> LocalFileCoordinate:
    if not ref.startswith(_LOCAL_COORDINATE_PREFIX):
        raise Quarantine("TARGET_COORDINATE_ADAPTER_CONFLICT")
    encoded = ref[len(_LOCAL_COORDINATE_PREFIX) :]
    try:
        raw = base64.b64decode(
            encoded + "=" * (-len(encoded) % 4),
            altchars=b"-_",
            validate=True,
        )
        value = canonical_json_loads(raw)
        if set(value) != {"workspace_root", "workspace_id", "logical_path"}:
            raise ValueError("coordinate fields conflict")
        coordinate = LocalFileCoordinate(**value)
    except (TypeError, ValueError) as exc:
        raise Quarantine("TARGET_COORDINATE_ENCODING_CONFLICT") from exc
    root = Path(coordinate.workspace_root)
    if not root.is_absolute() or not coordinate.workspace_id:
        raise Quarantine("TARGET_WORKSPACE_COORDINATE_CONFLICT")
    _validated_relative_parts(coordinate.logical_path)
    if encode_local_file_coordinate(
        root, coordinate.workspace_id, coordinate.logical_path
    ) != ref:
        raise Quarantine("TARGET_COORDINATE_CANONICAL_CONFLICT")
    return coordinate


def prepared_effect_descriptor_ref(contract: EffectContract) -> str:
    """Bind the receiver descriptor to the complete sealed effect identity."""

    return sha256_ref(
        canonical_json_bytes(
            {
                "effect_contract_ref": contract.effect_contract_ref,
                "receiver_adapter_ref": contract.body.receiver_adapter_ref,
                "effect_handler_ref": contract.body.effect_handler_ref,
                "target_coordinate_ref": contract.body.target_coordinate_ref,
                "idempotency_key": contract.body.idempotency_key,
            }
        )
    )


def require_exact_prepared_effect(
    prepared: PreparedEffect,
    contract: EffectContract,
) -> PreparedEffect:
    if (
        prepared.effect_contract_ref != contract.effect_contract_ref
        or prepared.receiver_adapter_ref
        != contract.body.receiver_adapter_ref
        or prepared.effect_handler_ref != contract.body.effect_handler_ref
        or prepared.target_coordinate_ref
        != contract.body.target_coordinate_ref
        or prepared.idempotency_key != contract.body.idempotency_key
        or prepared.descriptor_ref
        != prepared_effect_descriptor_ref(contract)
    ):
        raise Quarantine("PREPARED_EFFECT_DESCRIPTOR_CONFLICT")
    return prepared


# Retained as a private compatibility alias for existing candidate callers.
_descriptor_ref = prepared_effect_descriptor_ref


def _root_and_parts(coordinate: LocalFileCoordinate) -> tuple[Path, tuple[str, ...]]:
    root = Path(coordinate.workspace_root)
    if not root.is_absolute():
        raise Quarantine("TARGET_WORKSPACE_COORDINATE_CONFLICT")
    return root, _validated_relative_parts(coordinate.logical_path)


def _require_secure_dir_fd_support() -> None:
    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_DIRECTORY")
        or os.open not in os.supports_dir_fd
        or os.stat not in os.supports_dir_fd
        or os.stat not in os.supports_follow_symlinks
    ):
        raise Hold("HOLD_SECURE_WRITE_ADAPTER_UNAVAILABLE", no_effect=True)


@contextmanager
def _open_parent_beneath(
    coordinate: LocalFileCoordinate,
) -> Iterator[tuple[int, str]]:
    root, parts = _root_and_parts(coordinate)
    _require_secure_dir_fd_support()
    close_on_exec = getattr(os, "O_CLOEXEC", 0)
    directory_flags = (
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | close_on_exec
    )
    try:
        parent_fd = os.open(root, directory_flags)
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise Quarantine(
                "TARGET_WORKSPACE_SYMLINK_OR_KIND_CONFLICT"
            ) from error
        raise Hold("HOLD_TARGET_WORKSPACE_UNAVAILABLE", no_effect=True) from error
    try:
        for component in parts[:-1]:
            try:
                next_fd = os.open(
                    component,
                    directory_flags,
                    dir_fd=parent_fd,
                )
            except FileNotFoundError as error:
                raise Hold(
                    "HOLD_TARGET_PARENT_UNAVAILABLE", no_effect=True
                ) from error
            except OSError as error:
                if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                    raise Quarantine(
                        "TARGET_PATH_SYMLINK_OR_KIND_CONFLICT"
                    ) from error
                raise Hold(
                    "HOLD_TARGET_PARENT_UNAVAILABLE", no_effect=True
                ) from error
            os.close(parent_fd)
            parent_fd = next_fd
        yield parent_fd, parts[-1]
    finally:
        os.close(parent_fd)


def _secure_lstat_at(
    parent_fd: int,
    leaf_name: str,
    *,
    no_effect: bool,
) -> os.stat_result | None:
    try:
        return os.stat(
            leaf_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise Quarantine(
                "TARGET_PATH_SYMLINK_OR_KIND_CONFLICT"
            ) from error
        raise Hold(
            "HOLD_TARGET_OBSERVATION_UNAVAILABLE",
            no_effect=no_effect,
        ) from error


def _open_new_file_beneath(
    coordinate: LocalFileCoordinate,
    mode: int = 0o600,
) -> int:
    _require_secure_dir_fd_support()
    close_on_exec = getattr(os, "O_CLOEXEC", 0)
    with _open_parent_beneath(coordinate) as (parent_fd, leaf_name):
        try:
            return os.open(
                leaf_name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | close_on_exec,
                mode,
                dir_fd=parent_fd,
            )
        except FileExistsError as error:
            raise Quarantine("TARGET_ALREADY_EXISTS_CONFLICT") from error
        except OSError as error:
            if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                raise Quarantine(
                    "TARGET_PATH_SYMLINK_OR_KIND_CONFLICT"
                ) from error
            raise Hold("HOLD_TARGET_WRITE_UNAVAILABLE") from error


def _hash_regular_file_at(
    parent_fd: int,
    leaf_name: str,
    expected_metadata: os.stat_result,
) -> tuple[str, int, int, int, int]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= os.O_NOFOLLOW
    try:
        fd = os.open(leaf_name, flags, dir_fd=parent_fd)
    except FileNotFoundError as error:
        raise Quarantine("TARGET_CHANGED_DURING_OBSERVATION") from error
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise Quarantine(
                "TARGET_PATH_SYMLINK_OR_KIND_CONFLICT"
            ) from error
        raise Hold("HOLD_TARGET_OBSERVATION_UNAVAILABLE") from error
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise Quarantine("TARGET_KIND_CONFLICT")
        if (
            metadata.st_dev,
            metadata.st_ino,
        ) != (
            expected_metadata.st_dev,
            expected_metadata.st_ino,
        ):
            raise Quarantine("TARGET_CHANGED_DURING_OBSERVATION")
        digest = hashlib.sha256()
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            digest.update(block)
        after = os.fstat(fd)
        if (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise Quarantine("TARGET_CHANGED_DURING_OBSERVATION")
        return (
            digest.hexdigest(),
            after.st_size,
            after.st_dev,
            after.st_ino,
            after.st_mtime_ns,
        )
    finally:
        os.close(fd)


class LocalCreateFileReceiverAdapter:
    adapter_ref = "receiver.local.create-new-file.v1"

    def __init__(
        self,
        workspace_root: str | Path,
        workspace_id: str,
        *,
        objects: ObjectPacketStore,
    ) -> None:
        self._workspace_root = _validated_runtime_root(workspace_root)
        if not workspace_id:
            raise Quarantine("TARGET_WORKSPACE_BINDING_CONFLICT")
        if not isinstance(objects, ObjectPacketStore):
            raise Quarantine("RECEIVER_EVIDENCE_STORE_CONFLICT")
        self._workspace_id = workspace_id
        self._objects = objects

    def _coordinate(self, ref: str) -> LocalFileCoordinate:
        coordinate = decode_local_file_coordinate(ref)
        if (
            coordinate.workspace_root != str(self._workspace_root)
            or coordinate.workspace_id != self._workspace_id
        ):
            raise Quarantine("TARGET_WORKSPACE_BINDING_CONFLICT")
        return coordinate

    def _seal_evidence(self, evidence: Mapping[str, object]) -> str:
        raw = canonical_json_bytes(dict(evidence))
        ref = sha256_ref(raw)
        _put_and_reload_exact_packet(
            self._objects,
            ref,
            raw,
            unavailable_code="HOLD_RECEIVER_EVIDENCE_STORE_UNAVAILABLE",
            conflict_code="RECEIVER_EVIDENCE_STORE_CONFLICT",
            no_effect=False,
        )
        return ref

    def prepare(self, context: PrepareContext) -> PreparedEffect:
        contract = context.contract
        coordinate = self._coordinate(
            contract.body.target_coordinate_ref
        )
        with _open_parent_beneath(coordinate) as (parent_fd, leaf_name):
            metadata = _secure_lstat_at(
                parent_fd,
                leaf_name,
                no_effect=True,
            )
        if metadata is not None:
            raise Hold("HOLD_TARGET_ALREADY_EXISTS", no_effect=True)
        validate_sha256_ref(contract.body.effect_input_ref)
        return PreparedEffect(
            effect_contract_ref=contract.effect_contract_ref,
            receiver_adapter_ref=contract.body.receiver_adapter_ref,
            effect_handler_ref=contract.body.effect_handler_ref,
            descriptor_ref=prepared_effect_descriptor_ref(contract),
            target_coordinate_ref=contract.body.target_coordinate_ref,
            idempotency_key=contract.body.idempotency_key,
        )

    def observe(self, context: ObservationContext) -> EffectObservation:
        contract = context.contract
        prepared = require_exact_prepared_effect(context.prepared, contract)
        started_event_ref = context.started_event_ref
        try:
            if started_event_ref is None:
                raise ValueError("started event ref is required")
            validate_sha256_ref(started_event_ref)
        except ValueError as error:
            raise Quarantine(
                "OBSERVATION_STARTED_EVENT_REF_CONFLICT"
            ) from error
        coordinate = self._coordinate(
            prepared.target_coordinate_ref
        )
        expected_hash = contract.body.effect_input_ref.removeprefix("sha256:")
        validate_sha256_hex(expected_hash)

        with _open_parent_beneath(coordinate) as (parent_fd, leaf_name):
            metadata = _secure_lstat_at(
                parent_fd,
                leaf_name,
                no_effect=False,
            )
            parent = os.fstat(parent_fd)
            if not stat.S_ISDIR(parent.st_mode):
                raise Quarantine("TARGET_PARENT_KIND_CONFLICT")

            if metadata is None:
                evidence = {
                    "schema_id": "W7TP_LOCAL_FILE_OBSERVATION_V1",
                    "effect_state": EffectState.ABSENT,
                    "effect_contract_ref": contract.effect_contract_ref,
                    "started_event_ref": started_event_ref,
                    "target_coordinate_ref": prepared.target_coordinate_ref,
                    "parent_dev": parent.st_dev,
                    "parent_ino": parent.st_ino,
                    "parent_mtime_ns": parent.st_mtime_ns,
                    "observation_method": "DIR_FD_NOFOLLOW_FSTAT",
                }
                ref = self._seal_evidence(evidence)
                return EffectObservation(
                    effect_state=EffectState.ABSENT,
                    observation_ref=ref,
                    evidence_ref=ref,
                )

            if not stat.S_ISREG(metadata.st_mode):
                evidence = {
                    "schema_id": "W7TP_LOCAL_FILE_OBSERVATION_V1",
                    "effect_state": EffectState.UNKNOWN,
                    "effect_contract_ref": contract.effect_contract_ref,
                    "started_event_ref": started_event_ref,
                    "target_coordinate_ref": prepared.target_coordinate_ref,
                    "observed_mode": stat.S_IFMT(metadata.st_mode),
                    "parent_dev": parent.st_dev,
                    "parent_ino": parent.st_ino,
                    "observation_method": "DIR_FD_NOFOLLOW_FSTAT",
                }
                ref = self._seal_evidence(evidence)
                return EffectObservation(
                    effect_state=EffectState.UNKNOWN,
                    observation_ref=ref,
                    evidence_ref=ref,
                )

            actual_hash, size, dev, inode, mtime_ns = _hash_regular_file_at(
                parent_fd,
                leaf_name,
                metadata,
            )
            state = (
                EffectState.COMPLETE
                if actual_hash == expected_hash
                else EffectState.PARTIAL
            )
            evidence = {
                "schema_id": "W7TP_LOCAL_FILE_OBSERVATION_V1",
                "effect_state": state,
                "effect_contract_ref": contract.effect_contract_ref,
                "started_event_ref": started_event_ref,
                "target_coordinate_ref": prepared.target_coordinate_ref,
                "actual_hash": actual_hash,
                "size_bytes": size,
                "device": dev,
                "inode": inode,
                "mtime_ns": mtime_ns,
                "parent_dev": parent.st_dev,
                "parent_ino": parent.st_ino,
                "observation_method": "DIR_FD_NOFOLLOW_FSTAT_STREAM_HASH",
            }
            ref = self._seal_evidence(evidence)
            return EffectObservation(
                effect_state=state,
                observation_ref=ref,
                evidence_ref=ref,
                actual_hash=actual_hash,
            )


class LocalCreateFileEffectHandler:
    handler_ref = "effect.local.create-new-file.v1"
    idempotency = IdempotencyClass.IDEMPOTENT

    def __init__(
        self,
        workspace_root: str | Path,
        workspace_id: str,
    ) -> None:
        self._workspace_root = _validated_runtime_root(workspace_root)
        if not workspace_id:
            raise Quarantine("TARGET_WORKSPACE_BINDING_CONFLICT")
        self._workspace_id = workspace_id

    def _coordinate(self, ref: str) -> LocalFileCoordinate:
        coordinate = decode_local_file_coordinate(ref)
        if (
            coordinate.workspace_root != str(self._workspace_root)
            or coordinate.workspace_id != self._workspace_id
        ):
            raise Quarantine("TARGET_WORKSPACE_BINDING_CONFLICT")
        return coordinate

    def apply(
        self, prepared: PreparedEffect, exact_input: bytes
    ) -> ApplyOutcome:
        coordinate = self._coordinate(
            prepared.target_coordinate_ref
        )
        fd = _open_new_file_beneath(coordinate)
        try:
            view = memoryview(exact_input)
            written = 0
            while written < len(view):
                count = os.write(fd, view[written:])
                if count <= 0:
                    raise OSError("short local effect write")
                written += count
            os.fsync(fd)
        finally:
            os.close(fd)
        actual_hash = sha256_hex(exact_input)
        return ApplyOutcome(result_ref=f"sha256:{actual_hash}")


_ADAPTER_BACKING: dict[str, ReceiverAdapter] = {}
_HANDLER_BACKING: dict[str, EffectHandler] = {}
_LOCAL_RUNTIME_BINDING: tuple[str, str, str] | None = None
_LOCAL_RUNTIME_LOCK = threading.Lock()

ADAPTERS: Final[Mapping[str, ReceiverAdapter]] = MappingProxyType(
    _ADAPTER_BACKING
)
HANDLERS: Final[Mapping[str, EffectHandler]] = MappingProxyType(
    _HANDLER_BACKING
)


def _validated_runtime_root(root: str | Path) -> Path:
    requested = Path(root)
    if not requested.is_absolute():
        raise Quarantine("TARGET_WORKSPACE_BINDING_CONFLICT")
    try:
        metadata = requested.lstat()
        resolved = requested.resolve(strict=True)
    except OSError as exc:
        raise Hold("HOLD_TARGET_WORKSPACE_UNAVAILABLE", no_effect=True) from exc
    if requested.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise Quarantine("TARGET_WORKSPACE_BINDING_CONFLICT")
    return resolved


def configure_local_create_file_runtime(
    workspace_root: str | Path,
    workspace_id: str,
    *,
    objects: ObjectPacketStore,
) -> None:
    """Install the one fixed local receiver boundary for this process."""

    global _LOCAL_RUNTIME_BINDING
    resolved = _validated_runtime_root(workspace_root)
    if not workspace_id:
        raise Quarantine("TARGET_WORKSPACE_BINDING_CONFLICT")
    if not isinstance(objects, ObjectPacketStore):
        raise Quarantine("RECEIVER_EVIDENCE_STORE_CONFLICT")
    binding = (str(resolved), workspace_id, str(objects.root))
    with _LOCAL_RUNTIME_LOCK:
        if _LOCAL_RUNTIME_BINDING is not None:
            raise Quarantine("LOCAL_RUNTIME_ALREADY_CONFIGURED")
        _ADAPTER_BACKING[LocalCreateFileReceiverAdapter.adapter_ref] = (
            LocalCreateFileReceiverAdapter(
                resolved,
                workspace_id,
                objects=objects,
            )
        )
        _HANDLER_BACKING[LocalCreateFileEffectHandler.handler_ref] = (
            LocalCreateFileEffectHandler(resolved, workspace_id)
        )
        _LOCAL_RUNTIME_BINDING = binding


def resolve_static_adapter(ref: str) -> ReceiverAdapter:
    adapter = ADAPTERS.get(ref)
    if adapter is None:
        raise Hold("HOLD_RECEIVER_ADAPTER_UNAVAILABLE", no_effect=True)
    return adapter


def resolve_static_handler(ref: str) -> EffectHandler:
    handler = HANDLERS.get(ref)
    if handler is None:
        raise Hold("HOLD_EFFECT_HANDLER_UNAVAILABLE", no_effect=True)
    return handler
