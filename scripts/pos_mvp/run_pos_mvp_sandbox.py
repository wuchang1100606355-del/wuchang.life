#!/usr/bin/env python3
from pathlib import Path
import runpy
import sys

ROOT = Path("/home/taiji_admin/Taiji_Hub")
API = ROOT / "runtime/sandbox/pos_mvp_autodev/api/pos_mvp_api.py"

if __name__ == "__main__":
    sys.argv = [str(API), *(sys.argv[1:] or ["demo"])]
    runpy.run_path(str(API), run_name="__main__")
