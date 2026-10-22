"""Isolated contract tests; dependencies are stubs, not a taiji01 live test."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import types
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "tools/total_field/stateless_msi_turn_adapter_v1.py"
EVENTS: list = []
NOW = datetime(2026, 10, 21, 2, 20, tzinfo=timezone.utc)


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class FakeBroker:
    def __init__(self, result):
        self.result = result
        self.consumed = False

    def is_consumed(self, coordinate):
        return self.consumed

    def pull(self, coordinate, *, task_ref, provider_ref, model_ref, now):
        EVENTS.append(("pull", coordinate, task_ref, provider_ref, model_ref, now))
        if task_ref != "task:T-011B" or provider_ref != "provider:MSI_OLLAMA_LOCAL" or model_ref != "model:xiaoj:latest":
            raise RuntimeError("HOLD_CONTEXT_PULL_BINDING_DRIFT")
        if self.consumed:
            raise RuntimeError("HOLD_CONTEXT_PULL_REPLAY_BLOCKED")
        self.consumed = True
        return copy.deepcopy(self.result)


def stub_imports():
    tools = types.ModuleType("tools")
    tools.__path__ = []
    tf = types.ModuleType("tools.total_field")
    tf.__path__ = []
    broker_mod = types.ModuleType("tools.total_field_dynamic_context_pull")
    broker_mod.BOOTSTRAP_SCHEMA = "w7tp-total-field-context-pull-bootstrap/1.0"
    broker_mod.TotalFieldDynamicContextPullBroker = FakeBroker
    broker_mod.canonical_sha256 = sha
    adapter_mod = types.ModuleType("tools.total_field.msi_llm_candidate_adapter")
    adapter_mod.load_model_selection_contract = lambda: {"provider_ref": "MSI_OLLAMA_LOCAL", "model_ref": "xiaoj:latest"}
    def run_candidate(**kwargs):
        EVENTS.append(("model", kwargs))
        return {"state": "CANDIDATE_READY", "candidate_only": True, "must_not_execute": True,
                "requires_total_field_verify": True, "candidate_text": "review-only", "context_ref": "test"}
    adapter_mod.run_msi_llm_candidate = run_candidate
    return {
        "tools": tools,
        "tools.total_field": tf,
        "tools.total_field_dynamic_context_pull": broker_mod,
        "tools.total_field.msi_llm_candidate_adapter": adapter_mod,
    }


# Keep stub modules scoped to loading this isolated candidate. The module
# retains the imported test doubles, while other tests keep real imports.
with patch.dict(sys.modules, stub_imports()):
    spec = importlib.util.spec_from_file_location("stateless_adapter_under_test",FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)


def fixture():
    b = {
        "schema_version": "w7tp-total-field-context-pull-bootstrap/1.0",
        "pull_coordinate": "tfctx:abcdef0123",
        "packet_ref": "packet:test:11",
        "packet_sha256": "a"*64,
        "adi_coordinate_ref": "adi:test:11",
        "context_schema_ref": "context-schema:test:11",
        "persistence_policy_ref": "policy:test:11",
        "return_coordinate": "return:test:11",
        "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
        "single_use": True,
    }
    b["bootstrap_sha256"] = sha(b)
    result = {
        "pull_coordinate": b["pull_coordinate"], "task_ref": "task:T-011B",
        "packet_ref": b["packet_ref"], "adi_coordinate_ref": b["adi_coordinate_ref"],
        "return_coordinate": b["return_coordinate"],
        "reconstruction_evidence": {"packet_sha256": b["packet_sha256"], "workset_destroyed":True,
                                   "persistent_materialization":False},
        "pull_result_sha256": "b"*64,
        "model_visible_context": {"context_ref":"context:test:11"},
    }
    return b, FakeBroker(result)


def run(b=None, broker=None, **kw):
    if b is None or broker is None:
        b, broker = fixture()
    return mod.run_stateless_msi_turn(broker=broker, bootstrap=b, member_model_visible_context={},
                     resource_decision={}, task_ref="task:T-011B", intent_ref="intent:test:11",
                     transport=lambda *args: {}, clock=lambda:NOW, **kw)


class StatelessCandidateTests(unittest.TestCase):
    def setUp(self):
        EVENTS.clear()

    def hold(self, code, b=None, broker=None, **kw):
        with self.assertRaises(mod.StatelessTurnHold) as cm:
            run(b, broker, **kw)
        self.assertEqual(cm.exception.code, code)
        self.assertFalse(any(item[0]=="model" for item in EVENTS))

    def test_fresh_turn_one_context_and_no_model_history(self):
        b, broker = fixture()
        r = run(b, broker)
        self.assertEqual(r["state"], "CANDIDATE_READY")
        self.assertTrue(broker.consumed)
        self.assertEqual([e[0] for e in EVENTS],["pull","model"])
        self.assertFalse(r["stateless_model_boundary"]["previous_turn_messages_supplied"])
        self.assertFalse(r["authority"]["execution_authorized"])
        self.assertEqual(EVENTS[1][1]["dynamic_context_pull_result"]["pull_coordinate"],b["pull_coordinate"])

    def test_second_call_same_coordinate_blocks_without_model(self):
        b, broker = fixture()
        run(b,broker)
        EVENTS.clear()
        self.hold("HOLD_STATELESS_REPLAY_BLOCKED",b,broker)

    def test_tampered_bootstrap_blocks_before_pull(self):
        b,broker=fixture()
        b["packet_ref"]="packet:tampered"
        self.hold("HOLD_STATELESS_BOOTSTRAP_HASH_MISMATCH",b,broker)
        self.assertFalse(EVENTS)

    def test_expired_bootstrap_blocks(self):
        b,broker=fixture()
        b["expires_at"]=(NOW-timedelta(minutes=1)).isoformat()
        b["bootstrap_sha256"]=sha({k:v for k,v in b.items() if k!="bootstrap_sha256"})
        self.hold("HOLD_STATELESS_CONTEXT_NOT_FRESH",b,broker)

    def test_excessively_long_ttl_blocks(self):
        b,broker=fixture()
        b["expires_at"]=(NOW+timedelta(days=1)).isoformat()
        b["bootstrap_sha256"]=sha({k:v for k,v in b.items() if k!="bootstrap_sha256"})
        self.hold("HOLD_STATELESS_CONTEXT_NOT_FRESH",b,broker)

    def test_missing_single_use_blocks(self):
        b,broker=fixture()
        b["single_use"]=False
        b["bootstrap_sha256"]=sha({k:v for k,v in b.items() if k!="bootstrap_sha256"})
        self.hold("HOLD_STATELESS_SINGLE_USE_REQUIRED",b,broker)

    def test_post_pull_binding_drift_blocks_before_model(self):
        b,broker=fixture()
        broker.result["packet_ref"]="packet:other"
        self.hold("HOLD_STATELESS_PULL_BINDING_MISMATCH",b,broker)

    def test_workset_leak_blocks_before_model(self):
        b,broker=fixture()
        broker.result["reconstruction_evidence"]["workset_destroyed"]=False
        self.hold("HOLD_STATELESS_RECONSTRUCTION_EVIDENCE_INVALID",b,broker)

    def test_missing_broker_rejected(self):
        b,broker=fixture()
        self.hold("HOLD_STATELESS_BROKER_REQUIRED",b,object())

    def test_no_previous_context_or_messages_accepted(self):
        b,broker=fixture()
        with self.assertRaises(TypeError):
            run(b, broker, conversation_history=[{"role":"user","content":"prior"}])
        self.assertFalse(EVENTS)

    def test_invalid_clock_rejected(self):
        b,broker=fixture()
        with self.assertRaises(mod.StatelessTurnHold) as cm:
            mod.run_stateless_msi_turn(broker=broker,bootstrap=b,member_model_visible_context={},
                                      resource_decision={},task_ref="task:T-011B",intent_ref="intent:test:11",
                                      clock=lambda: datetime(2026,10,21))
        self.assertEqual(cm.exception.code,"HOLD_STATELESS_CLOCK_INVALID")


if __name__ == "__main__":
    unittest.main()
