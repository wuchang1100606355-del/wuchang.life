from __future__ import annotations

import argparse
from pathlib import Path

from .capabilities import command_decrypt_once, command_probe, command_seal, command_self_test
from .contract import (
    ADI_CAPABILITY_COORDINATES,
    DEFAULT_AUDIT,
    DEFAULT_DECISION_DIR,
    DEFAULT_RESCUE_DIR,
    DEFAULT_USED_DIR,
)
from .governance import create_human_decision
from .rescue import command_rescue_snapshot


def add_local_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--local-auth-env",
        help="Environment variable containing local authorization secret for this use.",
    )
    parser.add_argument(
        "--local-auth-file",
        type=Path,
        help="Local file containing authorization secret for this use. Content is never printed.",
    )


def add_human_decision_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--human-decision",
        type=Path,
        help="Required human decision receipt for this command.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Taiji system total probe and one-time decrypt tool.")
    parser.set_defaults(func=command_probe)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(parser)

    subparsers = parser.add_subparsers(dest="command")

    decision = subparsers.add_parser("human-decision", help="Create a local human decision receipt.")
    decision.add_argument(
        "--scope",
        required=True,
        choices=[
            "probe",
            "seal",
            "decrypt-once",
            "self-test",
            "rescue-snapshot",
            "red-blue-exchange",
            "all",
        ],
    )
    decision.add_argument("--decision", choices=["allow", "deny"], default="allow")
    decision.add_argument("--expires-at", required=True, help="ISO-8601 timestamp with timezone.")
    decision.add_argument("--human-proof-env")
    decision.add_argument("--human-proof-file", type=Path)
    decision.add_argument("--output-dir", type=Path, default=DEFAULT_DECISION_DIR)
    decision.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(decision)
    decision.set_defaults(
        func=create_human_decision,
        adi_coordinate=ADI_CAPABILITY_COORDINATES["human-decision"],
    )

    probe = subparsers.add_parser("probe", help="Print or write hardware-bound probe metadata.")
    probe.add_argument("--output", type=Path)
    probe.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(probe)
    add_human_decision_arg(probe)
    probe.set_defaults(
        func=command_probe,
        adi_coordinate=ADI_CAPABILITY_COORDINATES["probe"],
    )

    seal = subparsers.add_parser("seal", help="Create a hardware-bound one-time envelope.")
    seal.add_argument("--input", required=True, type=Path)
    seal.add_argument("--output", required=True, type=Path)
    seal.add_argument("--passphrase-env")
    seal.add_argument("--passphrase-file", type=Path)
    seal.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(seal)
    add_human_decision_arg(seal)
    seal.set_defaults(
        func=command_seal,
        adi_coordinate=ADI_CAPABILITY_COORDINATES["seal"],
    )

    decrypt = subparsers.add_parser("decrypt-once", help="Decrypt one envelope once on this hardware.")
    decrypt.add_argument("--envelope", required=True, type=Path)
    decrypt.add_argument("--output", required=True, type=Path)
    decrypt.add_argument("--used-dir", type=Path, default=DEFAULT_USED_DIR)
    decrypt.add_argument("--passphrase-env")
    decrypt.add_argument("--passphrase-file", type=Path)
    decrypt.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(decrypt)
    add_human_decision_arg(decrypt)
    decrypt.set_defaults(
        func=command_decrypt_once,
        adi_coordinate=ADI_CAPABILITY_COORDINATES["decrypt-once"],
    )

    self_test = subparsers.add_parser("self-test", help="Run a non-secret local crypto self-test.")
    self_test.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(self_test)
    add_human_decision_arg(self_test)
    self_test.set_defaults(
        func=command_self_test,
        adi_coordinate=ADI_CAPABILITY_COORDINATES["self-test"],
    )

    rescue = subparsers.add_parser("rescue-snapshot", help="Write an AI context-loss rescue snapshot.")
    rescue.add_argument("--output-dir", type=Path, default=DEFAULT_RESCUE_DIR)
    rescue.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(rescue)
    add_human_decision_arg(rescue)
    rescue.set_defaults(
        func=command_rescue_snapshot,
        adi_coordinate=ADI_CAPABILITY_COORDINATES["rescue-snapshot"],
    )
    return parser
