from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT / "tools" / "total_field" / "xiaoj_adi_moving_v_shadow_adapter.py"
)
SPEC = importlib.util.spec_from_file_location("xiaoj_moving_v_shadow", MODULE_PATH)
assert SPEC and SPEC.loader
shadow = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = shadow
SPEC.loader.exec_module(shadow)


def config() -> dict:
    path = (
        ROOT
        / "configs"
        / "total_field"
        / "w7tp_xiaoj_adi_moving_v_shadow_v1.candidate.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def safe_policy(_path: Path) -> dict:
    return {
        "active": True,
        "status": "ACTIVE",
        "policy_version": "test",
        "cache_scope": "flow_template_only",
        "raw_plaintext_cache_allowed": False,
        "payment_cache_allowed": False,
        "secret_material_included": False,
        "member_plaintext_included": False,
    }


def memory(available: int = 16 * 1024**3) -> dict:
    return {
        "total_bytes": 24 * 1024**3,
        "available_bytes": available,
        "swap_total_bytes": 4 * 1024**3,
        "swap_free_bytes": 4 * 1024**3,
    }


def fetcher(active_models: int = 0):
    def fetch(url: str, _timeout: float):
        if url.endswith("/state"):
            payload = {
                "intent_field_loaded": True,
                "memory_field_loaded": True,
                "topology_field_loaded": True,
                "policy_gate_active": True,
            }
        elif url.endswith("/intent-field/status"):
            payload = {
                "service_name": "xiaoj-intent-field",
                "mode": "containerized_intent_field",
                "governance": "local_first_human_reviewed",
                "hardwalls_enabled": True,
                "cloud_allowed": False,
                "pii_allowed": False,
                "secrets_allowed": False,
            }
        elif url.endswith("/api/ps"):
            payload = {
                "models": [
                    {
                        "name": f"model-{index}",
                        "size": 1024,
                        "size_vram": 512,
                    }
                    for index in range(active_models)
                ]
            }
        elif url.endswith("/openapi.json"):
            payload = {"openapi": "3.1.0", "paths": {"/api/openclaw/ask": {}}}
        else:
            payload = {"gateway": "online", "service": "taiji-gateway"}
        return payload, 200, 2

    return fetch


def sample(
    *,
    available: int = 16 * 1024**3,
    active_models: int = 0,
    monotonic_ns: int = 1,
    endpoint_ok: bool = True,
    safe_status: bool = True,
) -> dict:
    cfg = config()
    return {
        "monotonic_ns": monotonic_ns,
        "endpoints": {
            "intent_state": {
                "ok": endpoint_ok,
                "latency_ms": 2,
            }
        },
        "intent_state": deepcopy(cfg["required_intent_state"]),
        "intent_status": {
            **deepcopy(cfg["required_intent_status"]),
            "hardwalls_enabled": safe_status,
        },
        "intent_cache_policy": safe_policy(Path("unused")),
        "host_memory": {
            "available_bytes": available,
            "swap_used_bytes": 0,
        },
        "ollama": {"active_model_count": active_models, "active_models": []},
    }


def passing_performance() -> dict:
    return {
        "sample_count_uint": 60,
        "observation_ns_uint": 600_000_000_000,
        "protected_working_set_bytes_uint": 1024**3,
        "p95_latency_regression_bp_uint": 100,
        "false_miss_rate_bp_uint": 25,
        "preload_hit_rate_bp_uint": 8500,
        "oom_event_count_uint": 0,
        "swap_thrashing": False,
        "protected_eviction_violation_count_uint": 0,
        "reconstruction_hash_mismatch_count_uint": 0,
    }


def test_candidate_is_irreversibly_shadow_only():
    cfg = config()
    shadow.validate_config(cfg)
    assert cfg["status"] == "SHADOW_ONLY"
    assert cfg["mode"] == "OBSERVE_RECOMMEND_NO_EFFECT"
    assert cfg["authority"]["applies_change"] is False
    assert all(
        cfg["authority"][f"{effect}_allowed"] is False
        for effect in shadow.FORBIDDEN_EFFECTS
    )


def test_config_rejects_runtime_effect_or_non_loopback_source():
    cfg = config()
    cfg["authority"]["memory_limit_change_allowed"] = True
    try:
        shadow.validate_config(cfg)
    except shadow.ShadowConfigurationError as exc:
        assert "memory_limit_change" in str(exc)
    else:
        raise AssertionError("runtime effect escaped shadow gate")

    cfg = config()
    cfg["sources"]["intent_state_url"] = "https://example.com/state"
    try:
        shadow.validate_config(cfg)
    except shadow.ShadowConfigurationError as exc:
        assert "LOCAL_LOOPBACK" in str(exc)
    else:
        raise AssertionError("external endpoint escaped loopback gate")


def test_collect_sample_joins_live_source_shapes_without_raw_bodies():
    cfg = config()
    observed = shadow.collect_sample(
        cfg,
        fetch_json=fetcher(active_models=1),
        read_memory=lambda: memory(),
        read_policy=safe_policy,
    )
    assert observed["intent_state"]["memory_field_loaded"] is True
    assert observed["intent_status"]["hardwalls_enabled"] is True
    assert observed["ollama"]["active_model_count"] == 1
    assert observed["claw"]["openapi_present"] is True
    assert observed["host_memory"]["available_bytes"] == 16 * 1024**3
    assert "raw_body" not in json.dumps(observed)


def test_missing_endpoint_fails_closed():
    cfg = config()
    summary, decision = shadow.evaluate_shadow_samples(
        cfg, [sample(endpoint_ok=False)]
    )
    assert summary["endpoint_failure_count"] == 1
    assert decision["reason"] == "HOLD_REQUIRED_ENDPOINT_UNAVAILABLE"
    assert decision["applies_change"] is False


def test_unsafe_intent_status_fails_closed():
    cfg = config()
    _, decision = shadow.evaluate_shadow_samples(cfg, [sample(safe_status=False)])
    assert decision["reason"] == "HOLD_INTENT_HARDWALL_STATUS_UNSAFE"


def test_idle_model_state_keeps_current_limit():
    cfg = config()
    _, decision = shadow.evaluate_shadow_samples(cfg, [sample(active_models=0)])
    assert decision["reason"] == "HOLD_NO_ACTIVE_MODEL_WORKLOAD"
    assert decision["proposed_limit_bytes"] == decision["current_limit_bytes"]
    assert decision["applies_change"] is False


def test_host_pressure_emits_decrease_candidate_without_applying_it():
    cfg = config()
    current = cfg["adaptive_budget"]["current_limit_bytes"]
    step = cfg["adaptive_budget"]["step_bytes"]
    _, decision = shadow.evaluate_shadow_samples(
        cfg,
        [sample(available=1024**3, active_models=1)],
    )
    assert decision["proposed_limit_bytes"] == current - step
    assert "PRESSURE_DECREASE_CANDIDATE" in decision["reason"]
    assert decision["applies_change"] is False


def test_active_model_without_performance_evidence_holds_increase():
    cfg = config()
    current = cfg["adaptive_budget"]["current_limit_bytes"]
    step = cfg["adaptive_budget"]["step_bytes"]
    _, decision = shadow.evaluate_shadow_samples(cfg, [sample(active_models=1)])
    assert decision["proposed_limit_bytes"] == current + step
    assert decision["reason"] == "HOLD_PERFORMANCE_EVIDENCE_ABSENT"
    assert decision["applies_change"] is False


def test_passing_performance_emits_candidate_only():
    cfg = config()
    samples = [
        sample(active_models=1, monotonic_ns=1),
        sample(active_models=1, monotonic_ns=600_000_000_001),
    ]
    _, decision = shadow.evaluate_shadow_samples(
        cfg, samples, passing_performance()
    )
    assert decision["state"] == "PASS_BUDGET_ADJUSTMENT_CANDIDATE_ONLY"
    assert decision["applies_change"] is False
    assert decision["next_gate"].startswith("SEPARATE_TOTAL_FIELD")


def test_latency_regression_blocks_candidate():
    cfg = config()
    evidence = passing_performance()
    evidence["p95_latency_regression_bp_uint"] = 501
    _, decision = shadow.evaluate_shadow_samples(
        cfg, [sample(active_models=1)], evidence
    )
    assert decision["state"] == "HOLD_BUDGET_ADJUSTMENT"
    assert decision["reason"] == "HOLD_P95_LATENCY_REGRESSION"
    assert decision["applies_change"] is False


def test_report_encodes_zero_effects_and_no_authority():
    cfg = config()
    samples = [sample()]
    summary, decision = shadow.evaluate_shadow_samples(cfg, samples)
    config_path = (
        ROOT
        / "configs"
        / "total_field"
        / "w7tp_xiaoj_adi_moving_v_shadow_v1.candidate.json"
    )
    report = shadow.build_report(
        cfg, config_path, samples, summary, decision, None
    )
    assert all(value is False for value in report["effects"].values())
    assert report["governance"]["total_field_runtime_decision"] is None
    assert report["governance"]["live_canary_authorized"] is False
