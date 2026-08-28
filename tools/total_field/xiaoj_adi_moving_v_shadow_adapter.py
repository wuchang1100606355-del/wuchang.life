#!/usr/bin/env python3
"""Observe XiaoJ/ADI runtime signals and emit Moving-V budget candidates.

This adapter is deliberately incapable of applying a memory limit, cancelling
generation work, unloading RAM/VRAM, deleting files, or restarting services.
It joins live, local-only observations to the existing Moving-V budget gate and
emits an immutable shadow report for later Total Field review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.moving_v_preload_cleanup_candidate import (  # noqa: E402
    BudgetPerformanceEvidence,
    BudgetPerformanceGate,
    evaluate_budget_adjustment_candidate,
)


DEFAULT_CONFIG_PATH = (
    ROOT
    / "configs"
    / "total_field"
    / "w7tp_xiaoj_adi_moving_v_shadow_v1.candidate.json"
)

SHADOW_STATUS = "SHADOW_ONLY"
SHADOW_MODE = "OBSERVE_RECOMMEND_NO_EFFECT"
FORBIDDEN_EFFECTS = (
    "memory_limit_change",
    "job_cancellation",
    "ram_vram_unload",
    "file_delete",
    "canonical_source_delete",
    "service_restart",
    "remote_write",
)

FetchJson = Callable[[str, float], tuple[Mapping[str, Any], int, int]]
ReadMemory = Callable[[], Mapping[str, int]]
ReadPolicy = Callable[[Path], Mapping[str, Any]]


class ShadowConfigurationError(ValueError):
    """Raised when the candidate attempts to escape shadow-only operation."""


def canonical_sha256(value: Any) -> str:
    body = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ShadowConfigurationError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def _require_loopback_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise ShadowConfigurationError("SHADOW_SOURCE_MUST_BE_LOCAL_LOOPBACK_HTTP")


def validate_config(config: Mapping[str, Any]) -> None:
    if config.get("status") != SHADOW_STATUS:
        raise ShadowConfigurationError("SHADOW_STATUS_REQUIRED")
    if config.get("mode") != SHADOW_MODE:
        raise ShadowConfigurationError("SHADOW_MODE_REQUIRED")

    authority = config.get("authority")
    if not isinstance(authority, Mapping):
        raise ShadowConfigurationError("SHADOW_AUTHORITY_OBJECT_REQUIRED")
    if authority.get("applies_change") is not False:
        raise ShadowConfigurationError("APPLIES_CHANGE_MUST_BE_FALSE")
    if authority.get("runtime_effects_allowed") is not False:
        raise ShadowConfigurationError("RUNTIME_EFFECTS_MUST_BE_FALSE")
    for effect in FORBIDDEN_EFFECTS:
        if authority.get(f"{effect}_allowed") is not False:
            raise ShadowConfigurationError(f"FORBIDDEN_EFFECT_NOT_FALSE:{effect}")

    sources = config.get("sources")
    if not isinstance(sources, Mapping):
        raise ShadowConfigurationError("SHADOW_SOURCES_OBJECT_REQUIRED")
    urls = [
        sources.get("intent_state_url"),
        sources.get("intent_status_url"),
        sources.get("ollama_process_url"),
        sources.get("claw_capability_url"),
    ]
    gateway_urls = sources.get("gateway_health_urls")
    if not isinstance(gateway_urls, list) or not gateway_urls:
        raise ShadowConfigurationError("GATEWAY_HEALTH_URLS_REQUIRED")
    urls.extend(gateway_urls)
    for url in urls:
        if not isinstance(url, str):
            raise ShadowConfigurationError("SHADOW_SOURCE_URL_REQUIRED")
        _require_loopback_url(url)

    sampling = config.get("sampling")
    if not isinstance(sampling, Mapping):
        raise ShadowConfigurationError("SAMPLING_OBJECT_REQUIRED")
    sample_count = sampling.get("sample_count")
    interval = sampling.get("interval_seconds")
    timeout = sampling.get("timeout_seconds")
    if not isinstance(sample_count, int) or isinstance(sample_count, bool):
        raise ShadowConfigurationError("SAMPLE_COUNT_MUST_BE_INTEGER")
    if not 1 <= sample_count <= 120:
        raise ShadowConfigurationError("SAMPLE_COUNT_OUT_OF_RANGE")
    if not isinstance(interval, (int, float)) or not 0 <= interval <= 60:
        raise ShadowConfigurationError("SAMPLE_INTERVAL_OUT_OF_RANGE")
    if not isinstance(timeout, (int, float)) or not 0.1 <= timeout <= 10:
        raise ShadowConfigurationError("SAMPLE_TIMEOUT_OUT_OF_RANGE")

    budget = config.get("adaptive_budget")
    if not isinstance(budget, Mapping):
        raise ShadowConfigurationError("ADAPTIVE_BUDGET_OBJECT_REQUIRED")
    fields = (
        "current_limit_bytes",
        "minimum_candidate_bytes",
        "maximum_candidate_bytes",
        "step_bytes",
        "minimum_host_reserve_bytes",
        "protected_working_set_floor_bytes",
    )
    for field in fields:
        value = budget.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ShadowConfigurationError(f"BUDGET_UINT_REQUIRED:{field}")
    if not (
        budget["minimum_candidate_bytes"]
        <= budget["current_limit_bytes"]
        <= budget["maximum_candidate_bytes"]
    ):
        raise ShadowConfigurationError("CURRENT_LIMIT_OUTSIDE_CANDIDATE_RANGE")
    if budget["step_bytes"] == 0:
        raise ShadowConfigurationError("ADAPTIVE_STEP_MUST_BE_POSITIVE")


def _http_json(url: str, timeout_seconds: float) -> tuple[Mapping[str, Any], int, int]:
    started = time.perf_counter_ns()
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
        status = int(getattr(response, "status", 200))
        body = response.read(2_000_000)
    elapsed_ms = max(0, (time.perf_counter_ns() - started) // 1_000_000)
    value = json.loads(body.decode("utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("HTTP_JSON_OBJECT_REQUIRED")
    return value, status, elapsed_ms


def read_proc_meminfo(path: Path = Path("/proc/meminfo")) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        parts = raw.strip().split()
        if not parts or not parts[0].isdigit():
            continue
        multiplier = 1024 if len(parts) > 1 and parts[1].lower() == "kb" else 1
        values[key] = int(parts[0]) * multiplier
    return {
        "total_bytes": values.get("MemTotal", 0),
        "available_bytes": values.get("MemAvailable", 0),
        "swap_total_bytes": values.get("SwapTotal", 0),
        "swap_free_bytes": values.get("SwapFree", 0),
    }


def read_intent_cache_policy(path: Path) -> dict[str, Any]:
    try:
        value = load_json_object(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "active": False,
            "status": "unavailable",
            "error_type": type(exc).__name__,
        }
    active = value.get("status") == "ACTIVE" and value.get("policy_active") is True
    return {
        "active": active,
        "status": value.get("status", "UNKNOWN"),
        "policy_version": value.get("policy_version", "unknown"),
        "cache_scope": value.get("cache_scope", "unknown"),
        "raw_plaintext_cache_allowed": value.get("raw_plaintext_cache_allowed"),
        "payment_cache_allowed": value.get("payment_cache_allowed"),
        "secret_material_included": value.get("secret_material_included"),
        "member_plaintext_included": value.get("member_plaintext_included"),
    }


def _observe(
    name: str,
    url: str,
    timeout_seconds: float,
    fetch_json: FetchJson,
) -> tuple[dict[str, Any], Mapping[str, Any] | None]:
    try:
        value, status, latency_ms = fetch_json(url, timeout_seconds)
    except Exception as exc:  # fail closed; report only the exception class
        return (
            {
                "name": name,
                "url": url,
                "ok": False,
                "http_status": None,
                "latency_ms": None,
                "error_type": type(exc).__name__,
            },
            None,
        )
    return (
        {
            "name": name,
            "url": url,
            "ok": status == 200,
            "http_status": status,
            "latency_ms": latency_ms,
            "error_type": None,
        },
        value,
    )


def collect_sample(
    config: Mapping[str, Any],
    *,
    fetch_json: FetchJson = _http_json,
    read_memory: ReadMemory = read_proc_meminfo,
    read_policy: ReadPolicy = read_intent_cache_policy,
) -> dict[str, Any]:
    validate_config(config)
    sources = config["sources"]
    timeout_seconds = float(config["sampling"]["timeout_seconds"])

    endpoint_results: dict[str, dict[str, Any]] = {}
    payloads: dict[str, Mapping[str, Any] | None] = {}
    named_urls = {
        "intent_state": sources["intent_state_url"],
        "intent_status": sources["intent_status_url"],
        "ollama_process": sources["ollama_process_url"],
        "claw_capability": sources["claw_capability_url"],
    }
    for index, url in enumerate(sources["gateway_health_urls"]):
        named_urls[f"gateway_{index}"] = url
    for name, url in named_urls.items():
        observation, payload = _observe(name, url, timeout_seconds, fetch_json)
        endpoint_results[name] = observation
        payloads[name] = payload

    intent_state_source = payloads.get("intent_state") or {}
    intent_status_source = payloads.get("intent_status") or {}
    ollama_source = payloads.get("ollama_process") or {}
    claw_source = payloads.get("claw_capability") or {}
    models = ollama_source.get("models")
    if not isinstance(models, list):
        models = []
    model_summary = []
    for item in models:
        if not isinstance(item, Mapping):
            continue
        model_summary.append(
            {
                "name": item.get("name") or item.get("model") or "unknown",
                "size_bytes": item.get("size", 0),
                "size_vram_bytes": item.get("size_vram", 0),
            }
        )

    cache_policy_path = ROOT / sources["intent_cache_policy_path"]
    memory = dict(read_memory())
    swap_used = max(
        0,
        int(memory.get("swap_total_bytes", 0))
        - int(memory.get("swap_free_bytes", 0)),
    )
    return {
        "sampled_at_utc": datetime.now(timezone.utc).isoformat(),
        "monotonic_ns": time.monotonic_ns(),
        "endpoints": endpoint_results,
        "intent_state": {
            key: intent_state_source.get(key)
            for key in config["required_intent_state"]
        },
        "intent_status": {
            key: intent_status_source.get(key)
            for key in (
                "service_name",
                "mode",
                "governance",
                *config["required_intent_status"].keys(),
            )
        },
        "intent_cache_policy": dict(read_policy(cache_policy_path)),
        "ollama": {
            "active_model_count": len(model_summary),
            "active_models": model_summary,
        },
        "claw": {
            "openapi_present": isinstance(claw_source.get("openapi"), str),
            "path_count": len(claw_source.get("paths", {}))
            if isinstance(claw_source.get("paths"), Mapping)
            else 0,
        },
        "host_memory": {
            "total_bytes": int(memory.get("total_bytes", 0)),
            "available_bytes": int(memory.get("available_bytes", 0)),
            "swap_total_bytes": int(memory.get("swap_total_bytes", 0)),
            "swap_used_bytes": swap_used,
        },
    }


def _percentile_95(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, ((95 * len(ordered) + 99) // 100) - 1)
    return ordered[index]


def summarize_samples(
    config: Mapping[str, Any], samples: list[Mapping[str, Any]]
) -> dict[str, Any]:
    if not samples:
        return {
            "sample_count": 0,
            "observation_ns": 0,
            "endpoint_failure_count": 0,
            "intent_ready_sample_count": 0,
            "cache_policy_ready_sample_count": 0,
            "active_model_count_max": 0,
            "host_available_min_bytes": 0,
            "endpoint_latency_p95_ms": None,
        }

    latencies: list[int] = []
    endpoint_failures = 0
    intent_ready = 0
    status_ready = 0
    policy_ready = 0
    available_values: list[int] = []
    swap_used_values: list[int] = []
    active_model_counts: list[int] = []
    for sample in samples:
        endpoints = sample.get("endpoints", {})
        if isinstance(endpoints, Mapping):
            for endpoint in endpoints.values():
                if not isinstance(endpoint, Mapping):
                    endpoint_failures += 1
                    continue
                if endpoint.get("ok") is not True:
                    endpoint_failures += 1
                latency = endpoint.get("latency_ms")
                if isinstance(latency, int) and not isinstance(latency, bool):
                    latencies.append(latency)
        state = sample.get("intent_state", {})
        if isinstance(state, Mapping) and all(
            state.get(key) == expected
            for key, expected in config["required_intent_state"].items()
        ):
            intent_ready += 1
        status = sample.get("intent_status", {})
        if isinstance(status, Mapping) and all(
            status.get(key) == expected
            for key, expected in config["required_intent_status"].items()
        ):
            status_ready += 1
        policy = sample.get("intent_cache_policy", {})
        if (
            isinstance(policy, Mapping)
            and policy.get("active") is True
            and policy.get("raw_plaintext_cache_allowed") is False
            and policy.get("payment_cache_allowed") is False
            and policy.get("secret_material_included") is False
            and policy.get("member_plaintext_included") is False
        ):
            policy_ready += 1
        memory = sample.get("host_memory", {})
        if isinstance(memory, Mapping):
            available_values.append(int(memory.get("available_bytes", 0)))
            swap_used_values.append(int(memory.get("swap_used_bytes", 0)))
        ollama = sample.get("ollama", {})
        if isinstance(ollama, Mapping):
            active_model_counts.append(int(ollama.get("active_model_count", 0)))

    monotonic_values = [
        int(sample.get("monotonic_ns", 0))
        for sample in samples
        if isinstance(sample.get("monotonic_ns"), int)
    ]
    observation_ns = (
        max(monotonic_values) - min(monotonic_values)
        if len(monotonic_values) >= 2
        else 0
    )
    return {
        "sample_count": len(samples),
        "observation_ns": observation_ns,
        "endpoint_failure_count": endpoint_failures,
        "intent_ready_sample_count": intent_ready,
        "intent_status_safe_sample_count": status_ready,
        "cache_policy_ready_sample_count": policy_ready,
        "active_model_count_max": max(active_model_counts, default=0),
        "host_available_min_bytes": min(available_values, default=0),
        "host_available_last_bytes": available_values[-1] if available_values else 0,
        "swap_used_max_bytes": max(swap_used_values, default=0),
        "endpoint_latency_p95_ms": _percentile_95(latencies),
    }


def _hold(current: int, proposed: int, reason: str) -> dict[str, Any]:
    return {
        "state": "HOLD_SHADOW_ADAPTATION",
        "current_limit_bytes": current,
        "proposed_limit_bytes": proposed,
        "reason": reason,
        "applies_change": False,
        "next_gate": "COLLECT_OR_REPAIR_REQUIRED_EVIDENCE",
    }


def evaluate_shadow_samples(
    config: Mapping[str, Any],
    samples: list[Mapping[str, Any]],
    performance_evidence: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    validate_config(config)
    summary = summarize_samples(config, samples)
    budget = config["adaptive_budget"]
    current = int(budget["current_limit_bytes"])

    if not samples:
        return summary, _hold(current, current, "HOLD_NO_SHADOW_SAMPLES")
    if summary["endpoint_failure_count"]:
        return summary, _hold(current, current, "HOLD_REQUIRED_ENDPOINT_UNAVAILABLE")
    if summary["intent_ready_sample_count"] != summary["sample_count"]:
        return summary, _hold(current, current, "HOLD_INTENT_OR_MEMORY_FIELD_NOT_READY")
    if summary["intent_status_safe_sample_count"] != summary["sample_count"]:
        return summary, _hold(current, current, "HOLD_INTENT_HARDWALL_STATUS_UNSAFE")
    if summary["cache_policy_ready_sample_count"] != summary["sample_count"]:
        return summary, _hold(current, current, "HOLD_INTENT_CACHE_POLICY_UNSAFE")

    available = int(summary["host_available_min_bytes"])
    reserve = int(budget["minimum_host_reserve_bytes"])
    step = int(budget["step_bytes"])
    minimum = int(budget["minimum_candidate_bytes"])
    maximum = int(budget["maximum_candidate_bytes"])
    active_models = int(summary["active_model_count_max"])

    if available < reserve:
        proposed = max(minimum, current - step)
        return summary, _hold(
            current,
            proposed,
            "HOLD_SHADOW_PRESSURE_DECREASE_CANDIDATE_REQUIRES_PERFORMANCE_EVIDENCE",
        )
    if active_models == 0:
        return summary, _hold(current, current, "HOLD_NO_ACTIVE_MODEL_WORKLOAD")

    proposed = min(maximum, current + step)
    if performance_evidence is None:
        return summary, _hold(current, proposed, "HOLD_PERFORMANCE_EVIDENCE_ABSENT")

    required_evidence_fields = (
        "sample_count_uint",
        "observation_ns_uint",
        "protected_working_set_bytes_uint",
        "p95_latency_regression_bp_uint",
        "false_miss_rate_bp_uint",
        "preload_hit_rate_bp_uint",
        "oom_event_count_uint",
        "swap_thrashing",
        "protected_eviction_violation_count_uint",
        "reconstruction_hash_mismatch_count_uint",
    )
    if any(field not in performance_evidence for field in required_evidence_fields):
        return summary, _hold(current, proposed, "HOLD_PERFORMANCE_EVIDENCE_INCOMPLETE")

    host_after_adjustment = max(0, available - max(0, proposed - current))
    evidence = BudgetPerformanceEvidence(
        sample_count_uint=int(performance_evidence["sample_count_uint"]),
        observation_ns_uint=int(performance_evidence["observation_ns_uint"]),
        host_available_after_adjustment_bytes_uint=host_after_adjustment,
        protected_working_set_bytes_uint=max(
            int(performance_evidence["protected_working_set_bytes_uint"]),
            int(budget["protected_working_set_floor_bytes"]),
        ),
        p95_latency_regression_bp_uint=int(
            performance_evidence["p95_latency_regression_bp_uint"]
        ),
        false_miss_rate_bp_uint=int(performance_evidence["false_miss_rate_bp_uint"]),
        preload_hit_rate_bp_uint=int(performance_evidence["preload_hit_rate_bp_uint"]),
        oom_event_count_uint=int(performance_evidence["oom_event_count_uint"]),
        swap_thrashing=performance_evidence["swap_thrashing"],
        protected_eviction_violation_count_uint=int(
            performance_evidence["protected_eviction_violation_count_uint"]
        ),
        reconstruction_hash_mismatch_count_uint=int(
            performance_evidence["reconstruction_hash_mismatch_count_uint"]
        ),
    )
    gate = BudgetPerformanceGate(**config["performance_gate"])
    decision = evaluate_budget_adjustment_candidate(
        current_limit_bytes=current,
        proposed_limit_bytes=proposed,
        gate=gate,
        evidence=evidence,
    )
    return summary, {
        "state": decision.state,
        "current_limit_bytes": decision.current_limit_bytes,
        "proposed_limit_bytes": decision.proposed_limit_bytes,
        "reason": decision.reason,
        "applies_change": False,
        "next_gate": "SEPARATE_TOTAL_FIELD_RUNTIME_DECISION_AND_REVERSIBLE_CANARY",
    }


def build_report(
    config: Mapping[str, Any],
    config_path: Path,
    samples: list[Mapping[str, Any]],
    summary: Mapping[str, Any],
    recommendation: Mapping[str, Any],
    performance_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "report_version": "W7TP-XIAOJ-ADI-MOVING-V-SHADOW-REPORT/1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract_id": config["contract_id"],
        "mode": SHADOW_MODE,
        "config_path": str(config_path.relative_to(ROOT)),
        "config_sha256": canonical_sha256(config),
        "sources": {
            "xiaoj_intent_field": "LIVE_LOOPBACK_READ_ONLY",
            "ollama_process_state": "LIVE_LOOPBACK_READ_ONLY",
            "gateway_health": "LIVE_LOOPBACK_READ_ONLY",
            "claw_capability": "LIVE_LOOPBACK_READ_ONLY",
            "host_memory": "LOCAL_PROCFS_READ_ONLY",
            "intent_cache_policy": "LOCAL_POLICY_METADATA_ONLY",
            "performance_evidence": "PROVIDED"
            if performance_evidence is not None
            else "NOT_PROVIDED",
        },
        "summary": dict(summary),
        "recommendation": dict(recommendation),
        "samples": samples,
        "effects": {
            "applies_change": False,
            "memory_limit_changed": False,
            "job_cancelled": False,
            "ram_vram_unloaded": False,
            "file_deleted": False,
            "canonical_source_deleted": False,
            "service_restarted": False,
            "remote_write": False,
        },
        "governance": {
            "total_field_runtime_decision": None,
            "live_canary_authorized": False,
            "shadow_observation_authorized_by_mode": True,
        },
    }


def default_report_path(config: Mapping[str, Any]) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    reporting = config["reporting"]
    return ROOT / reporting["directory"] / f"{reporting['filename_prefix']}_{stamp}.json"


def write_new_report(path: Path, report: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"SHADOW_REPORT_ALREADY_EXISTS:{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--samples", type=int)
    parser.add_argument("--interval-seconds", type=float)
    parser.add_argument("--performance-evidence", type=Path)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = args.config.resolve()
    config = load_json_object(config_path)
    if args.samples is not None:
        config["sampling"]["sample_count"] = args.samples
    if args.interval_seconds is not None:
        config["sampling"]["interval_seconds"] = args.interval_seconds
    validate_config(config)

    performance_evidence = (
        load_json_object(args.performance_evidence.resolve())
        if args.performance_evidence
        else None
    )
    samples: list[Mapping[str, Any]] = []
    sample_count = int(config["sampling"]["sample_count"])
    interval = float(config["sampling"]["interval_seconds"])
    for index in range(sample_count):
        samples.append(collect_sample(config))
        if index + 1 < sample_count and interval:
            time.sleep(interval)

    summary, recommendation = evaluate_shadow_samples(
        config, samples, performance_evidence
    )
    report = build_report(
        config,
        config_path,
        samples,
        summary,
        recommendation,
        performance_evidence,
    )
    output_path = args.output.resolve() if args.output else default_report_path(config)
    if not args.no_write:
        write_new_report(output_path, report)
    print(
        json.dumps(
            {
                "report_path": None if args.no_write else str(output_path),
                "summary": summary,
                "recommendation": recommendation,
                "applies_change": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
