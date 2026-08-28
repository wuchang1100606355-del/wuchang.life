"""W7TP V2.1 incremental generative-transmission mesh adapter."""

from .app import MeshRuntime, make_server
from .core import CANONICAL_ID, CANONICAL_SHA256, CANONICAL_VERSION, MeshConflict, MeshHold
from .control import build_capability_inventory, build_task_envelope, validate_task_envelope
from .inventory import collect_snapshot
from .native_adi import NativeADIAdapter, build_native_adi_record
from .packet import BuiltTransfer, build_transfer, validate_domain_profile, validate_packet, validate_packet_profile_binding
from .receiver import MeshReceiver
from .spool import DriveSpoolProducer, produce_drive_projection_envelopes
from .transport import MeshTransport

__all__ = [
    "BuiltTransfer",
    "CANONICAL_ID",
    "CANONICAL_SHA256",
    "CANONICAL_VERSION",
    "DriveSpoolProducer",
    "MeshConflict",
    "MeshHold",
    "MeshReceiver",
    "MeshRuntime",
    "MeshTransport",
    "NativeADIAdapter",
    "build_capability_inventory",
    "build_native_adi_record",
    "build_task_envelope",
    "build_transfer",
    "collect_snapshot",
    "make_server",
    "produce_drive_projection_envelopes",
    "validate_domain_profile",
    "validate_packet",
    "validate_packet_profile_binding",
    "validate_task_envelope",
]
