#!/usr/bin/env python3
"""Versioned, non-inferential compatibility routing for transfer packet names."""

from __future__ import annotations

from typing import Any, Mapping


AMBIGUOUS_LEGACY_TYPES = frozenset(
    {"TRANSFER_PACKET", "DELTA_PACKET", "GENERATIVE_DELTA"}
)


def classify_transfer_packet(packet: Mapping[str, Any]) -> dict[str, str]:
    packet_type = packet.get("PACKET_TYPE")
    if packet_type == "D6_GENERATIVE_TRANSMISSION_PACKET":
        return {
            "ROUTE": "D6_GENERATIVE_TRANSMISSION",
            "STATE": "EXPLICIT_PACKET_TYPE",
        }
    if packet_type == "DIFFERENTIAL_TRANSFER_PACKET":
        return {"ROUTE": "DIFFERENTIAL_TRANSFER", "STATE": "EXPLICIT_PACKET_TYPE"}
    return {
        "ROUTE": "QUARANTINE",
        "STATE": "HOLD_AMBIGUOUS_TRANSFER_SEMANTICS",
    }
