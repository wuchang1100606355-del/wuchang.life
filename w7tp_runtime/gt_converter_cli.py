"""Stable product CLI for the offline W7TP-GTF converter."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from .gt_converter import ConverterFailure, GTConverter, OperationResult, PROTOCOL_VERSION

EXIT_CODES = {"PASS": 0, "HOLD": 10, "BLOCK": 20, "ERROR": 40}


def _print(result: OperationResult) -> None:
    for key, value in asdict(result).items():
        if value is not None:
            text = str(value).replace("\r", "\\r").replace("\n", "\\n")
            print(f"{key.upper()}={text}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="W7TP-GTF deterministic offline converter")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities")
    pack = sub.add_parser("pack"); pack.add_argument("--source", required=True); pack.add_argument("--packet", required=True); pack.add_argument("--target", default="reconstructed.bin"); pack.add_argument("--run-id")
    inspect = sub.add_parser("inspect"); inspect.add_argument("--packet", required=True)
    reconstruct = sub.add_parser("reconstruct"); reconstruct.add_argument("--packet", required=True); reconstruct.add_argument("--output-root", required=True)
    verify = sub.add_parser("verify"); verify.add_argument("--packet", required=True); verify.add_argument("--reconstructed", required=True)
    run = sub.add_parser("run"); run.add_argument("--source", required=True); run.add_argument("--packet", required=True); run.add_argument("--output-root", required=True); run.add_argument("--report", required=True); run.add_argument("--target", default="reconstructed.bin"); run.add_argument("--run-id")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    converter = GTConverter()
    try:
        if args.command == "capabilities":
            print(f"STATE=PASS\nPROTOCOL_VERSION={PROTOCOL_VERSION}\nNETWORK_ALLOWED=False\nAUTHENTICITY=UNVERIFIED")
            return 0
        if args.command == "pack": result = converter.pack(Path(args.source), Path(args.packet), run_id=args.run_id, target_relative_path=args.target)
        elif args.command == "inspect": result = converter.inspect(Path(args.packet))
        elif args.command == "reconstruct": result = converter.reconstruct(Path(args.packet), Path(args.output_root))
        elif args.command == "verify": result = converter.verify(Path(args.packet), Path(args.reconstructed))
        else:
            packed = converter.pack(Path(args.source), Path(args.packet), run_id=args.run_id, target_relative_path=args.target)
            reconstructed = converter.reconstruct(Path(args.packet), Path(args.output_root))
            result = converter.verify(Path(args.packet), reconstructed.output_path)
            converter.seal(result, Path(args.report))
        _print(result)
        return EXIT_CODES[result.state]
    except ConverterFailure as exc:
        print(f"STATE={exc.state}\nREASON_CODE={exc.reason_code}")
        return EXIT_CODES[exc.state]
    except (OSError, ValueError) as exc:
        print(f"STATE=ERROR\nREASON_CODE={exc.__class__.__name__.upper()}")
        return EXIT_CODES["ERROR"]


if __name__ == "__main__":
    raise SystemExit(main())
