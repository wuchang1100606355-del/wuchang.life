#!/usr/bin/env python3
"""Render XiaoJ browser native host manifest.

This writes a local manifest under runtime/member_browser/native_host only. It
does not write Chrome/Edge system directories and does not require sudo.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "web/xiaoj_member_browser_extension/native_host/tw.taiji.xiaoj_member_browser_gateway.template.json"
OUT_DIR = ROOT / "runtime/member_browser/native_host"


def render(extension_id: str, out_dir: Path = OUT_DIR) -> Path:
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    data["path"] = str(ROOT / "tools/member_browser/xiaoj_member_browser_native_host.py")
    data["allowed_origins"] = [f"chrome-extension://{extension_id}/"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "tw.taiji.xiaoj_member_browser_gateway.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Render native host manifest without installing it.")
    parser.add_argument("--extension-id", required=True, help="Chrome/Edge extension id after loading the extension.")
    args = parser.parse_args()
    out = render(args.extension_id)
    print("STATE=PASS_NATIVE_HOST_MANIFEST_RENDERED")
    print("MANIFEST=" + str(out.relative_to(ROOT)))
    print("INSTALL_REQUIRED=MANUAL_COPY_TO_BROWSER_NATIVE_MESSAGING_HOSTS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
