#!/usr/bin/env python3
"""Router capacity guard decision helper. Local-only decision support."""

from __future__ import annotations

import argparse

from w7tp_router_kernel_error_common import (
    ROUTER_CAPACITY_GUARD,
    base_result,
    classify_severity,
    collect_counts,
    load_reports,
    print_json,
)


CAPACITY_GUARD_PREREQUISITES = [
    "USB errors must be resolved",
    "Thermal must be stabilized (< 70°C)",
    "JFFS repair must wait until USB is stable",
    "Kernel storage errors must be cleared",
]

CAPACITY_GUARD_NEXT_STEPS = [
    "Run local USB repair suite",
    "Run JFFS health repair suite (read-only)",
    "Run router thermal stabilization suite",
    "Re-run router capacity read-only probe after repairs",
]


def capacity_guard_payload() -> dict[str, object]:
    payload = dict(ROUTER_CAPACITY_GUARD)
    payload["prerequisites"] = list(CAPACITY_GUARD_PREREQUISITES)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP router capacity guard decision helper.")
    parser.add_argument("--analysis-json", action="append")
    parser.add_argument("--severity-json")
    parser.add_argument("--summary-json")
    parser.add_argument("--usb-repair-complete-evidence")
    args = parser.parse_args()

    paths = list(args.analysis_json or [])
    for path in [args.severity_json, args.summary_json]:
        if path:
            paths.append(path)
    payloads, sources = load_reports(paths)
    if not payloads:
        result = base_result("w7tp_router_capacity_guard_decision_helper", "PASS_LOCAL_ROUTER_CAPACITY_GUARD_DECISION_HELPER")
        result.update(
            {
                "reason": "No analyzer JSON provided; emitted guard prerequisites and next steps only.",
                "analysis_sources": sources,
                "capacity_guard": capacity_guard_payload(),
                "next_steps": list(CAPACITY_GUARD_NEXT_STEPS),
                "capacity_guard_decision": "HOLD",
                "hold_reason": "HOLD_USB_STORAGE_ERRORS_DETECTED",
                "router_capacity_guard_status": "HOLD_USB_STORAGE_ERRORS_DETECTED",
                "jffs_repair_allowed": False,
                "router_action_allowed": False,
                "command_allowed": False,
                "requires_human_approval": True,
                "repair_executed": False,
            }
        )
        return print_json(result)

    counts = collect_counts(payloads)
    severity = classify_severity(counts)
    decision = "HOLD"
    hold_reason = "HOLD_USB_STORAGE_ERRORS_DETECTED"
    if severity["severity"] in {"critical", "high"}:
        hold_reason = "HOLD_ROUTER_KERNEL_ERRORS_DETECTED"
    if counts["storage"] or counts["usb"]:
        hold_reason = "HOLD_USB_STORAGE_ERRORS_DETECTED"
    if not args.usb_repair_complete_evidence:
        hold_reason = "HOLD_USB_REPAIR_EVIDENCE_REQUIRED"

    result = base_result("w7tp_router_capacity_guard_decision_helper", "HOLD_ROUTER_CAPACITY_GUARD_DECISION")
    result.update(
        {
            "analysis_sources": sources,
            "counts": counts,
            "severity": severity,
            "capacity_guard": capacity_guard_payload(),
            "next_steps": list(CAPACITY_GUARD_NEXT_STEPS),
            "capacity_guard_decision": decision,
            "hold_reason": hold_reason,
            "usb_repair_complete_evidence": args.usb_repair_complete_evidence,
            "router_capacity_guard_status": "HOLD_USB_STORAGE_ERRORS_DETECTED",
            "jffs_repair_allowed": False,
            "router_action_allowed": False,
            "command_allowed": False,
            "requires_human_approval": True,
            "repair_executed": False,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
