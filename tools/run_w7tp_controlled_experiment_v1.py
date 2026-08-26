#!/usr/bin/env python3
"""Repository-style wrapper for the candidate-only controlled experiment."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from w7tp_runtime.state_field.controlled_experiment_v1.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
