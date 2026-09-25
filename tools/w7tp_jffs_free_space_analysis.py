#!/usr/bin/env python3
"""Local JFFS free-space analysis. Does not access router."""

from __future__ import annotations

import argparse

from w7tp_jffs_repair_common import base_result, load_text_inputs, parse_jffs_df, print_json, run_cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP local JFFS free-space analysis.")
    parser.add_argument("--probe-output", action="append", help="Router read-only probe text output to analyze.")
    parser.add_argument("--skip-local-df", action="store_true", help="Do not run local df -h.")
    args = parser.parse_args()

    proc = {"stdout": "", "returncode": None}
    if not args.skip_local_df:
        proc = run_cmd(["df", "-h"], stdout_limit=200000)
    probe_text, probe_sources = load_text_inputs(args.probe_output)
    combined = "\n".join([proc.get("stdout", ""), probe_text])
    analysis = parse_jffs_df(combined)

    state = "PASS_LOCAL_JFFS_FREE_SPACE_ANALYSIS"
    if analysis["free_space_low"]:
        state = "HOLD_JFFS_FREE_SPACE_LOW"

    result = base_result("w7tp_jffs_free_space_analysis", state)
    result.update(
        {
            "df_output": proc.get("stdout", ""),
            "df_command": proc,
            "probe_sources": probe_sources,
            "jffs_detected": analysis["jffs_detected"],
            "analysis": analysis,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
