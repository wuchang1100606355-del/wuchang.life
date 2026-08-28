"""Stable, non-reflective gateway errors."""

from __future__ import annotations


class GatewayError(Exception):
    """An expected fail-closed error safe to expose to an MCP client."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


class PolicyDenied(GatewayError):
    """A policy decision that stopped execution before a backend call."""
