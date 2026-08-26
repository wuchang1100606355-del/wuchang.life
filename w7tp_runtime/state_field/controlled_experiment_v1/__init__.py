"""Candidate-only W7TP controlled experiment loop.

The package is deliberately isolated from Total Field authority, canonical
pointer, promotion, Odoo, and production-session modules.
"""

from .pipeline import run_controlled_demo, verify_run

__all__ = ["run_controlled_demo", "verify_run"]
