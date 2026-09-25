#!/usr/bin/env python3
"""Verify a sovereign identity-agent sandbox packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from sovereign_identity_agent import verify_identity_packet  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify sovereign identity-agent JSON.")
    parser.add_argument("identity_agent_json")
    parser.add_argument("--output")
    args = parser.parse_args()

    packet = json.loads(Path(args.identity_agent_json).read_text(encoding="utf-8"))
    result = verify_identity_packet(packet)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["DRY_RUN"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
