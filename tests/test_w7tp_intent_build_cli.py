#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/w7tp_intent_build_cli.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_open_intent_creates_intent_packet():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "INTENT_PACKET.json"
        run_cli("open-intent", "--intent-text", "驗證意圖式建構", "--out", str(out))
        packet = read_json(out)
        assert packet["packet_type"] == "INTENT_PACKET"
        assert packet["body"]["intent_text"] == "驗證意圖式建構"
        assert packet["body"]["safety_flags"]["DB_WRITE"] is False


def test_open_scope_rejects_schema_landing_first():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        intent = tmp_path / "INTENT_PACKET.json"
        field = tmp_path / "CONSTRUCTION_FIELD_PACKET.json"
        index = tmp_path / "index_sandbox.jsonl"
        scope = tmp_path / "BOUNDED_SCOPE_FROM_INTENT_PACKET.json"
        run_cli("open-intent", "--intent-text", "schema_landing_first 但我要意圖式建構", "--out", str(intent))
        run_cli("open-field", "--intent-packet", str(intent), "--out", str(field))
        run_cli("index-source", "--packets", str(intent), str(field), "--index", str(index))
        run_cli("open-scope", "--intent-packet", str(intent), "--index", str(index), "--out", str(scope))
        packet = read_json(scope)
        assert packet["body"]["bounded_scope"]["schema_landing_first_allowed"] is False
        assert "schema_landing_first" in packet["body"]["bounded_scope"]["rejected_modes"]


def build_chain(tmp_path: Path):
    intent = tmp_path / "INTENT_PACKET.json"
    field = tmp_path / "CONSTRUCTION_FIELD_PACKET.json"
    index = tmp_path / "index_sandbox.jsonl"
    scope = tmp_path / "BOUNDED_SCOPE_FROM_INTENT_PACKET.json"
    request = tmp_path / "CLOUD_CANDIDATE_REQUEST_FROM_SCOPE_PACKET.json"
    responses = tmp_path / "MOCK_CLOUD_CANDIDATE_RESPONSES.json"
    receipts = tmp_path / "TOTAL_FIELD_RECEIPTS.json"
    subfield = tmp_path / "SUBFIELD_REPORT.json"
    decision = tmp_path / "TOTAL_FIELD_FINAL_DECISION_PACKET.json"
    run_cli("open-intent", "--intent-text", "驗證意圖式建構指令化", "--out", str(intent))
    run_cli("open-field", "--intent-packet", str(intent), "--out", str(field))
    run_cli("index-source", "--packets", str(intent), str(field), "--index", str(index))
    run_cli("open-scope", "--intent-packet", str(intent), "--index", str(index), "--out", str(scope))
    run_cli("make-cloud-request", "--scope-packet", str(scope), "--out", str(request))
    run_cli("mock-cloud-response", "--request-packet", str(request), "--out", str(responses))
    run_cli("receive", "--responses", str(responses), "--request-packet", str(request), "--out", str(receipts))
    run_cli("subfield-check", "--receipts", str(receipts), "--responses", str(responses), "--out", str(subfield))
    run_cli("decide", "--receipts", str(receipts), "--subfield-report", str(subfield), "--out", str(decision))
    return request, receipts, subfield, decision


def test_make_cloud_request_is_dryrun_no_network():
    with tempfile.TemporaryDirectory() as tmp:
        request, _, _, _ = build_chain(Path(tmp))
        packet = read_json(request)
        assert packet["body"]["request_mode"] == "DRYRUN_NO_NETWORK"
        assert packet["body"]["safety_flags"]["CLOUD_REAL_CALL"] is False


def test_bad_candidate_rejected_and_good_candidate_checked_and_final_approved():
    with tempfile.TemporaryDirectory() as tmp:
        _, receipts, subfield, decision = build_chain(Path(tmp))
        receipt_packet = read_json(receipts)
        receipt_map = {r["candidate_id"]: r["receipt_decision"] for r in receipt_packet["body"]["receipts"]}
        assert receipt_map["BAD_CANDIDATE"] == "REJECT_AT_RECEIPT"
        assert receipt_map["GOOD_CANDIDATE"] == "RECEIVED_FOR_SUBFIELD_CHECK"
        report = read_json(subfield)
        assert report["body"]["candidate_reports"][0]["candidate_id"] == "GOOD_CANDIDATE"
        assert report["body"]["candidate_reports"][0]["overall"] == "PASS"
        final = read_json(decision)
        assert final["body"]["final_decision"] == "APPROVE_TO_SANDBOX_INDEX"


def test_run_demo_outputs_pass_and_safety_flags_false():
    with tempfile.TemporaryDirectory() as tmp:
        result = run_cli("run-demo", "--intent-text", "驗證意圖式建構指令化", "--out", tmp)
        out = result.stdout
        assert "STATE=PASS_INTENT_BUILD_COMMAND_DEMO" in out
        assert "FINAL_DECISION=APPROVE_TO_SANDBOX_INDEX" in out
        assert "BAD_RECEIPT_DECISION=REJECT_AT_RECEIPT" in out
        assert "DB_WRITE=FALSE" in out
        assert "CLOUD_REAL_CALL=FALSE" in out
        assert "GIT_ADD=FALSE" in out
        assert "GIT_COMMIT=FALSE" in out


if __name__ == "__main__":
    tests = [
        test_open_intent_creates_intent_packet,
        test_open_scope_rejects_schema_landing_first,
        test_make_cloud_request_is_dryrun_no_network,
        test_bad_candidate_rejected_and_good_candidate_checked_and_final_approved,
        test_run_demo_outputs_pass_and_safety_flags_false,
    ]
    for test in tests:
        test()
    print("PASS")
