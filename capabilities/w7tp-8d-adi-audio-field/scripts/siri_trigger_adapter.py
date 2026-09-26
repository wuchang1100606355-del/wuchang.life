#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from audio_field import AudioFieldHold, build_candidate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON file; omit to read stdin")
    args = parser.parse_args()

    try:
        if args.input:
            payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        else:
            payload = json.load(sys.stdin)
        result = build_candidate(payload)
    except (OSError, ValueError, json.JSONDecodeError, AudioFieldHold) as exc:
        code = getattr(exc, "code", "HOLD_SIRI_AUDIO_TRIGGER_INVALID")
        print(json.dumps({
            "state": code,
            "execution_allowed": False,
            "candidate_only": True
        }, ensure_ascii=False, sort_keys=True))
        return 2

    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
