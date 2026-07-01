#!/usr/bin/env python3
"""Generate an auditable kernel log summary from local reports or probe output."""

from __future__ import annotations

import argparse

from w7tp_router_kernel_error_common import (
    NETWORK_PATTERN,
    STORAGE_PATTERN,
    USB_PATTERN,
    analyze_lines,
    base_result,
    classify_severity,
    collect_counts,
    load_reports,
    load_text_inputs,
    local_kernel_text,
    print_json,
    redact_line,
    source_unavailable,
)


def collect_kernel_line_summary(text: str, sample_limit: int = 120) -> dict[str, object]:
    lines = text.splitlines()
    categories = {
        "usb_lines": lambda value: "usb" in value.lower(),
        "storage_lines": lambda value: any(token in value.lower() for token in ["sd ", "sda", "sdb", "block"]),
        "network_lines": lambda value: any(token in value.lower() for token in ["eth", "link", "carrier"]),
    }
    summary: dict[str, list[str]] = {}
    counts: dict[str, int] = {}
    for key, predicate in categories.items():
        matched = [redact_line(line) for line in lines if predicate(line)]
        summary[key] = matched[:sample_limit]
        counts[key] = len(matched)
    return {"summary": summary, "summary_counts": counts, "summary_sample_limit": sample_limit}


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP router kernel log summary generator.")
    parser.add_argument("--analysis-json", action="append")
    parser.add_argument("--probe-output", action="append")
    parser.add_argument("--input", action="append")
    parser.add_argument("--skip-local-dmesg", action="store_true")
    parser.add_argument("--include-local-journal", action="store_true")
    parser.add_argument("--journal-lines", type=int, default=400)
    args = parser.parse_args()

    payloads, report_sources = load_reports(args.analysis_json)
    file_text, file_sources = load_text_inputs((args.probe_output or []) + (args.input or []))
    local_text, local_sources = local_kernel_text(not args.skip_local_dmesg and not payloads and not file_text, args.include_local_journal, args.journal_lines)
    text = "\n".join([file_text, local_text])

    analyses = {}
    if text.strip():
        analyses = {
            "usb": analyze_lines(text, USB_PATTERN, "usb", sample_limit=20),
            "storage": analyze_lines(text, STORAGE_PATTERN, "storage", sample_limit=20),
            "network": analyze_lines(text, NETWORK_PATTERN, "network", sample_limit=20),
        }
        payloads.extend(analyses.values())
    elif not payloads and source_unavailable(file_sources + local_sources):
        result = base_result("w7tp_router_kernel_log_summary_generator", "HOLD_ROUTER_KERNEL_SUMMARY_INPUT_REQUIRED")
        result.update({"reason": "Provide analyzer JSON, probe output, input file, or readable local dmesg/journal.", "sources": report_sources + file_sources + local_sources})
        return print_json(result)

    counts = collect_counts(payloads)
    severity = classify_severity(counts)
    state = "PASS_ROUTER_KERNEL_LOG_SUMMARY_GENERATED"
    if severity["severity"] in {"critical", "high"}:
        state = "HOLD_ROUTER_KERNEL_LOG_SUMMARY_HAS_HIGH_RISK"

    line_summary = collect_kernel_line_summary(text) if text.strip() else collect_kernel_line_summary("")
    result = base_result("w7tp_router_kernel_log_summary_generator", state)
    result.update(
        {
            "sources": report_sources + file_sources + local_sources,
            "counts": counts,
            "severity": severity,
            "inline_analyses": analyses,
            "summary": line_summary["summary"],
            "summary_counts": line_summary["summary_counts"],
            "summary_sample_limit": line_summary["summary_sample_limit"],
            "repair_executed": False,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
