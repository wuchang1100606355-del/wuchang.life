"""Founder-native absolute-time ADI product service."""

from .core import (
    ADIError,
    PACKET_SCHEMA_VERSION,
    PROTOCOL_VERSION,
    STATE_SCHEMA_VERSION,
    SpacetimeADI,
    canonical_json,
    canonical_sha256,
    spiral_position,
)

__all__ = [
    "ADIError",
    "PACKET_SCHEMA_VERSION",
    "PROTOCOL_VERSION",
    "STATE_SCHEMA_VERSION",
    "SpacetimeADI",
    "canonical_json",
    "canonical_sha256",
    "spiral_position",
]
