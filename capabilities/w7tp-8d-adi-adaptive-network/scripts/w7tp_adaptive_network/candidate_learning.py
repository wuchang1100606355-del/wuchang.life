from __future__ import annotations

from collections import defaultdict
from typing import Any


FIXED_POLICY_PRIORITY = ("LAN_IPV4", "TAILSCALE_IPV4", "NATIVE_IPV6", "TAILSCALE_IPV6")


def build_learning_candidate(
    current_paths: list[dict[str, Any]],
    historical_path_matrices: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    matrices = [*(historical_path_matrices or []), {"paths": current_paths}]
    for matrix in matrices:
        for path in matrix.get("paths", []):
            path_type = path.get("path_type")
            if path_type in FIXED_POLICY_PRIORITY:
                samples[path_type].append(path)

    statistics: list[dict[str, Any]] = []
    for path_type in FIXED_POLICY_PRIORITY:
        records = samples.get(path_type, [])
        if not records:
            continue
        successes = sum(_sample_success(record) for record in records)
        scores = [float(record.get("candidate_score", 0.0)) for record in records]
        statistics.append(
            {
                "path_type": path_type,
                "sample_count": len(records),
                "successful_samples": successes,
                "success_rate": round(successes / len(records), 6),
                "mean_candidate_score": round(sum(scores) / len(scores), 3),
            }
        )

    priority_index = {value: index for index, value in enumerate(FIXED_POLICY_PRIORITY)}
    observed_order = [
        item["path_type"]
        for item in sorted(
            statistics,
            key=lambda item: (
                -item["success_rate"],
                -item["mean_candidate_score"],
                priority_index[item["path_type"]],
            ),
        )
    ]
    return {
        "state": "CANDIDATE_LEARNING_ONLY",
        "history_sample_count": sum(item["sample_count"] for item in statistics),
        "path_statistics": statistics,
        "observed_performance_order": observed_order,
        "fixed_policy_priority": list(FIXED_POLICY_PRIORITY),
        "can_override_policy_priority": False,
        "can_modify_founder_authority": False,
        "can_modify_canonical": False,
        "can_modify_d8_authority": False,
        "use": "future probe ordering and candidate evidence only",
    }


def _sample_success(path: dict[str, Any]) -> int:
    base = bool(
        path.get("available") and path.get("host_reachable") and path.get("service_reachable")
    )
    if path.get("path_type") in {"NATIVE_IPV6", "TAILSCALE_IPV6"}:
        base = base and bool(path.get("qualified"))
    return int(base)

