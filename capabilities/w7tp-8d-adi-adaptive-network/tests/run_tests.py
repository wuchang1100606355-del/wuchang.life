#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path


TEST_FILE = Path(__file__).with_name("test_adaptive_network.py")


def main() -> int:
    spec = importlib.util.spec_from_file_location("test_adaptive_network", TEST_FILE)
    if spec is None or spec.loader is None:
        print("STATE=HOLD_TEST_MODULE_LOAD")
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tests = sorted(
        (name, value)
        for name, value in vars(module).items()
        if name.startswith("test_") and callable(value)
    )
    failures = 0
    for name, test in tests:
        try:
            test()
            print(f"PASS {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"TESTS={len(tests)} FAILURES={failures}")
    print("STATE=PASS_CANDIDATE_TESTS" if failures == 0 else "STATE=HOLD_CANDIDATE_TESTS")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
