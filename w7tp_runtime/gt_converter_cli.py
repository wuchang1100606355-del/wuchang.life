"""Command-line entrypoint for the fail-closed W7TP-GTF converter."""

from __future__ import annotations

import argparse
import json
from typing import Any

from .gt_converter import ConverterHold, NotGenerativelyReducible, pack, reconstruct, seal, verify


def _print(result: dict[str, Any]) -> None:
    for key, value in result.items():
        print(f"{key.upper()}={value}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="W7TP-GTF deterministic L1 converter")
    sub = parser.add_subparsers(dest="command", required=True)
    pack_cmd = sub.add_parser("pack")
    pack_cmd.add_argument("source")
    pack_cmd.add_argument("packet")
    pack_cmd.add_argument("--run-id")
    pack_cmd.add_argument("--target", default="reconstructed.bin")
    reconstruct_cmd = sub.add_parser("reconstruct")
    reconstruct_cmd.add_argument("packet")
    reconstruct_cmd.add_argument("output_root")
    verify_cmd = sub.add_parser("verify")
    verify_cmd.add_argument("packet")
    verify_cmd.add_argument("output")
    run_cmd = sub.add_parser("run")
    run_cmd.add_argument("source")
    run_cmd.add_argument("packet")
    run_cmd.add_argument("output_root")
    run_cmd.add_argument("seal")
    run_cmd.add_argument("--target", default="reconstructed.bin")
    run_cmd.add_argument("--run-id")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "pack":
            packet = pack(args.source, args.packet, run_id=args.run_id, target_relative_path=args.target)
            _print({"state": "PASS", "run_id": packet["run_id"], "packet_path": args.packet})
        elif args.command == "reconstruct":
            _print({"state": "PASS", **reconstruct(args.packet, args.output_root)})
        elif args.command == "verify":
            result = verify(args.packet, args.output)
            _print({"state": result["verifier_decision"], **result})
        else:
            packet = pack(
                args.source,
                args.packet,
                run_id=args.run_id,
                target_relative_path=args.target,
            )
            reconstructed = reconstruct(args.packet, args.output_root)
            result = verify(args.packet, reconstructed["output_path"])
            record = seal(args.packet, reconstructed["output_path"], args.seal, result)
            _print(record)
            return 0 if record["verifier_decision"] == "PASS" else 20
    except NotGenerativelyReducible:
        print("STATE=HOLD_NOT_GENERATIVELY_REDUCIBLE")
        return 20
    except (ConverterHold, OSError, ValueError, json.JSONDecodeError) as exc:
        print("STATE=HOLD")
        print(f"ERROR_CLASS={exc.__class__.__name__}")
        return 20
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
