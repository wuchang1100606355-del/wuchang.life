#!/usr/bin/env python3
"""Generate kernel-error mitigation advice. Advice only; no repair execution."""

from __future__ import annotations

import argparse

from w7tp_router_kernel_error_common import base_result, classify_severity, collect_counts, load_reports, print_json


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP router kernel mitigation advisor.")
    parser.add_argument("--analysis-json", action="append")
    parser.add_argument("--severity-json")
    args = parser.parse_args()

    payloads, sources = load_reports(args.analysis_json)
    if args.severity_json:
        severity_payloads, severity_sources = load_reports([args.severity_json])
        payloads.extend(severity_payloads)
        sources.extend(severity_sources)
    if not payloads:
        result = base_result("w7tp_router_kernel_mitigation_advisor", "HOLD_ROUTER_KERNEL_MITIGATION_INPUT_REQUIRED")
        result.update({"reason": "Provide analyzer or severity JSON.", "analysis_sources": sources})
        return print_json(result)

    counts = collect_counts(payloads)
    severity = classify_severity(counts)
    state = "PASS_ROUTER_KERNEL_MITIGATION_ADVICE_READY"
    if severity["severity"] in {"critical", "high"}:
        state = "HOLD_ROUTER_KERNEL_MITIGATION_HUMAN_REVIEW_REQUIRED"

    result = base_result("w7tp_router_kernel_mitigation_advisor", state)
    result.update(
        {
            "analysis_sources": sources,
            "counts": counts,
            "severity": severity,
            "repair_executed": False,
            "mitigation_advice": [
                "Keep router_capacity_guard on HOLD until USB storage errors are cleared by evidence.",
                "Do not run router repair, reboot, restart, deploy, SSH, or config changes from this flow.",
                "If USB/storage errors are present, complete local USB health/SMART/fsck evidence first.",
                "If network errors are present without storage errors, collect another read-only probe after thermal stabilization.",
                "If severe kernel markers repeat, schedule human maintenance window and preserve read-only evidence.",
                "Keep JFFS repair blocked until USB repair is completed and accepted.",
            ],
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
