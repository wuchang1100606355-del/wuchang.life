"""Non-destructive command-line entrypoint for core run and verify."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from .pipeline import WRITE_ROOT, run_controlled_demo, verify_run


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="W7TP candidate-only controlled experiment")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="create one new synthetic candidate run")
    run.add_argument("--output-dir", type=Path)
    run.add_argument("--repo-root", type=Path, default=Path.cwd())
    verify = sub.add_parser("verify", help="independently verify a completed run")
    verify.add_argument("run_dir", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "run":
        now = datetime.now(UTC)
        output = args.output_dir
        if output is None:
            stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
            output = WRITE_ROOT / f"run_{stamp}_{os.getpid()}"
        summary = run_controlled_demo(output_dir=output, repo_root=args.repo_root, now=now)
        result = {"output_dir": str(output.resolve()), "summary": summary}
    elif args.command == "verify":
        result = verify_run(args.run_dir)
    else:
        result = verify_run(args.run_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    state = result.get("state", result.get("summary", {}).get("state"))
    return 1 if state == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
