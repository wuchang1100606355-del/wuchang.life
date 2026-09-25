#!/usr/bin/env python3
"""Classify kernel error severity from local analyzer reports."""

from __future__ import annotations

import argparse

from w7tp_router_kernel_error_common import base_result, classify_severity, collect_counts, load_reports, print_json


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP router kernel error severity classifier.")
    parser.add_argument("--analysis-json", action="append", help="Analyzer JSON output.")
    args = parser.parse_args()

    payloads, sources = load_reports(args.analysis_json)
    if not payloads:
        result = base_result("w7tp_router_kernel_error_severity_classifier", "HOLD_ROUTER_KERNEL_SEVERITY_INPUT_REQUIRED")
        result.update({"reason": "Provide --analysis-json from kernel analyzers.", "analysis_sources": sources})
        return print_json(result)

    counts = collect_counts(payloads)
    severity = classify_severity(counts)
    state = "PASS_ROUTER_KERNEL_ERROR_SEVERITY_CLASSIFIED"
    if severity["severity"] in {"critical", "high"}:
        state = "HOLD_ROUTER_KERNEL_ERROR_SEVERITY_HIGH"
    elif severity["severity"] == "medium":
        state = "HOLD_ROUTER_KERNEL_ERROR_SEVERITY_REVIEW"

    result = base_result("w7tp_router_kernel_error_severity_classifier", state)
    result.update({"analysis_sources": sources, "counts": counts, "severity": severity, "repair_executed": False})
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
