"""不依賴外部套件的直接測試執行器。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import traceback


ROOT = Path(__file__).resolve().parent


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"無法載入測試：{path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    passed = 0
    failed = 0
    for filename in ("test_sovereign_xiaoj.py", "test_competition_assets.py"):
        module = load(ROOT / filename)
        for name in sorted(item for item in vars(module) if item.startswith("test_")):
            try:
                getattr(module, name)()
                print(f"通過 {filename}::{name}")
                passed += 1
            except Exception:
                print(f"失敗 {filename}::{name}")
                traceback.print_exc()
                failed += 1
    print(f"測試總結：通過={passed}，失敗={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
