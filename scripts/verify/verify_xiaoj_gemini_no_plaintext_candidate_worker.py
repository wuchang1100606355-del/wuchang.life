#!/usr/bin/env python3
"""Verify Gemini no-plaintext candidate-worker packet contract."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "packets/product_av_ordering_ai/gemini_no_plaintext_candidate_worker_contract.json"
DOC = ROOT / "docs/product/XIAOJ_GEMINI_NO_PLAINTEXT_CANDIDATE_WORKER.md"
TOOL = ROOT / "tools/xiaoj_gemini_no_plaintext_candidate_packet.py"
PATENT_GT = ROOT / "runtime/patent_delivery/TW_W7TP_GT_V06_20260622_161730/01_說明書補強_V06_生成式傳輸.md"
PATENT_CLAIM = ROOT / "runtime/patent_delivery/TW_W7TP_GT_V06_20260622_161730/02_申請專利範圍補強_V06_生成式傳輸.md"
INVENTION_KERNEL = ROOT / "runtime/patent_delivery/W7TP_HIGH_VALUE_PATENT_CLAIM_TREE_20260630_143852/INVENTION_KERNEL.json"


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require(path: Path, needles: list[str]) -> str:
    text = read(path)
    for needle in needles:
        if needle not in text:
            fail(f"missing_text:{path.relative_to(ROOT)}:{needle}")
    return text


def load_tool():
    spec = importlib.util.spec_from_file_location("xiaoj_gemini_no_plaintext_candidate_packet_verify", TOOL)
    if spec is None or spec.loader is None:
        fail("tool_import_spec_missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def assert_no_forbidden_payload_text(packet: dict) -> None:
    cloud_payload = json.dumps(packet.get("cloud_candidate_request", {}), ensure_ascii=False)
    forbidden_patterns = [
        r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
        r"09\d{2}[- ]?\d{3}[- ]?\d{3}",
        r"\b[A-Z][12]\d{8}\b",
        r"SHOULD_NOT_SURVIVE",
        r"Bearer\s+",
        r"client_secret",
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, cloud_payload):
            fail(f"cloud_payload_leaks:{pattern}")


def main() -> int:
    contract = json.loads(read(CONTRACT))
    if contract.get("state") != "P1_CONTRACT_READY_NO_EXTERNAL_CALL":
        fail("contract_state_wrong")
    if contract.get("cloud_role") != "candidate_worker_only":
        fail("contract_cloud_role_wrong")
    if contract.get("authority_boundary", {}).get("gemini_authority") is not False:
        fail("gemini_authority_not_false")
    if contract.get("authority_boundary", {}).get("local_discrete_state_authority") is not True:
        fail("local_authority_not_true")
    if contract.get("zero_latency_local_decision", {}).get("decision_latency_class") != "LOCAL_ZERO_NETWORK_RTT":
        fail("zero_latency_class_missing")
    reality_boundary = contract.get("reality_boundary", {})
    if reality_boundary.get("llm_hallucination_allowed") != "conditional":
        fail("reality_boundary_hallucination_not_conditional")
    if reality_boundary.get("allowed_hallucination_layer") != "IMAGINED_CANDIDATE":
        fail("reality_boundary_allowed_layer_wrong")
    if reality_boundary.get("environment_provided_by_total_field") is not True:
        fail("reality_boundary_environment_not_total_field")
    if reality_boundary.get("llm_self_truth_authority") is not False:
        fail("llm_self_truth_authority_not_false")
    if reality_boundary.get("truth_boundary_ref_required") is not True:
        fail("truth_boundary_ref_not_required")
    if "evidence_anchors" not in str(reality_boundary.get("reality_discrimination_method", "")):
        fail("reality_discrimination_method_missing_evidence_anchors")
    if reality_boundary.get("real_claim_requires_evidence_ref") is not True:
        fail("real_claim_requires_evidence_ref_missing")
    if reality_boundary.get("execution_claim_requires_local_gate") is not True:
        fail("execution_claim_requires_local_gate_missing")
    if reality_boundary.get("cloud_can_mark_real_verified") is not False:
        fail("cloud_can_mark_real_verified_not_false")
    if reality_boundary.get("cloud_can_mark_executable_authorized") is not False:
        fail("cloud_can_mark_executable_not_false")
    if reality_boundary.get("total_field_distinguishes_real_or_imagined") is not True:
        fail("total_field_reality_distinction_missing")
    for key, value in contract.get("p1_side_effects", {}).items():
        if value is not False:
            fail(f"side_effect_not_false:{key}")

    require(DOC, [
        "STATE=P1_CONTRACT_READY_NO_EXTERNAL_CALL",
        "Gemini can be useful, but it must not be the authority.",
        "LLM hallucination is conditionally allowed",
        "The LLM does not become a truth authority by itself.",
        "truth_boundary_ref",
        "reality_discrimination_context_ref",
        "evidence_anchor_policy",
        "llm_self_truth_authority=false",
        "REAL_VERIFIED",
        "IMAGINED_CANDIDATE",
        "EXECUTABLE_AUTHORIZED",
        "authority decision requires zero external network round trip",
        "member_plaintext_to_cloud=false",
        "P2 can add a real Gemini connector only after a key-ref vault",
    ])
    require(PATENT_GT, [
        "不包含完整原始狀態資料",
        "最小資訊表示",
        "本地重構",
        "查表驗證",
    ])
    require(PATENT_CLAIM, [
        "接收端無須接收完整原始資料",
        "正式執行閘判定",
    ])
    kernel = json.loads(read(INVENTION_KERNEL))
    if "generative transmission packet" not in kernel.get("core_chain", []):
        fail("invention_kernel_missing_generative_transmission_packet")
    if "local reconstruction" not in kernel.get("core_chain", []):
        fail("invention_kernel_missing_local_reconstruction")

    tool = load_tool()
    secret_key = "access" + "_token=SHOULD_NOT_SURVIVE"
    packet = tool.build_packet(
        f"會員 email test@example.com 手機 0912-345-678 身分證 A123456789 {secret_key}，請給高品質回覆。",
        intent_code="member_service_reply",
        member_ref="MEMBER_REF_VERIFY_LOCAL_ONLY",
    )
    assert_no_forbidden_payload_text(packet)
    if packet.get("candidate_only") is not True:
        fail("packet_candidate_only_not_true")
    if packet.get("cloud_authority") is not False:
        fail("packet_cloud_authority_not_false")
    if packet.get("reality_mode") != "IMAGINED_CANDIDATE":
        fail("packet_reality_mode_wrong")
    if packet.get("reality_boundary", {}).get("cloud_can_mark_real_verified") is not False:
        fail("packet_cloud_can_mark_real_verified_not_false")
    if packet.get("reality_boundary", {}).get("total_field_distinguishes_real_or_imagined") is not True:
        fail("packet_total_field_reality_distinction_missing")
    if packet.get("reality_boundary", {}).get("llm_self_truth_authority") is not False:
        fail("packet_llm_self_truth_authority_not_false")
    if packet.get("reality_boundary", {}).get("real_claim_requires_evidence_ref") is not True:
        fail("packet_real_claim_evidence_policy_missing")
    if packet.get("reality_boundary", {}).get("execution_claim_requires_local_gate") is not True:
        fail("packet_execution_gate_policy_missing")
    gt = packet.get("generative_transmission", {})
    if gt.get("reality_mode") != "IMAGINED_CANDIDATE":
        fail("gt_reality_mode_wrong")
    if gt.get("member_plaintext_transmitted") is not False:
        fail("gt_member_plaintext_transmitted_not_false")
    if gt.get("raw_api_key_transmitted") is not False:
        fail("gt_raw_api_key_transmitted_not_false")
    if gt.get("full_body_transmitted") is not False:
        fail("gt_full_body_transmitted_not_false")
    local_decision = packet.get("local_zero_latency_decision", {})
    if local_decision.get("decision_latency_class") != "LOCAL_ZERO_NETWORK_RTT":
        fail("local_zero_latency_class_missing")
    if local_decision.get("execution_allowed") is not False:
        fail("local_execution_allowed_not_false")
    if local_decision.get("cloud_timeout_state") != "QUEUE_OR_HOLD_NOT_AUTHORITY":
        fail("cloud_timeout_state_wrong")
    if local_decision.get("reality_decision_before_cloud_return") != "IMAGINED_CANDIDATE_NOT_EXECUTABLE":
        fail("local_reality_decision_wrong")
    cloud_request = packet.get("cloud_candidate_request", {})
    if cloud_request.get("reality_mode") != "IMAGINED_CANDIDATE":
        fail("cloud_request_reality_mode_wrong")
    if cloud_request.get("truth_boundary_ref") != "TRUTH_BOUNDARY_REF_TOTAL_FIELD_REALITY_LAYER_V1":
        fail("cloud_request_truth_boundary_missing")
    if cloud_request.get("reality_discrimination_context_ref") != "REALITY_CONTEXT_REF_TOTAL_FIELD_EVIDENCE_ANCHORED_SANDBOX_V1":
        fail("cloud_request_reality_context_missing")
    if cloud_request.get("evidence_anchor_policy") != "real_claim_requires_local_evidence_ref_execution_claim_requires_local_gate":
        fail("cloud_request_evidence_anchor_policy_missing")
    local_verifier = packet.get("local_verifier", {})
    if local_verifier.get("llm_hallucination_allowed_only_as_candidate") is not True:
        fail("local_verifier_hallucination_boundary_missing")
    seal = packet.get("evidence_seal", {})
    for key in ["external_api_call", "raw_api_key_read", "secret_read", "member_plaintext_read", "member_plaintext_to_cloud"]:
        if seal.get("side_effects", {}).get(key) is not False:
            fail(f"seal_side_effect_not_false:{key}")
    if not {"secret_shape_redacted", "member_plaintext_shape_redacted"}.issubset(set(packet.get("redaction_flags", []))):
        fail("redaction_flags_missing")

    proc = subprocess.run(
        [sys.executable, str(TOOL), "--task", "會員 test@example.com 請候選回覆", "--pretty"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        fail(f"tool_cli_failed:{proc.stderr}")
    cli_packet = json.loads(proc.stdout)
    assert_no_forbidden_payload_text(cli_packet)

    print("STATE=PASS_XIAOJ_GEMINI_NO_PLAINTEXT_CANDIDATE_WORKER")
    print("GEMINI_AUTHORITY=FALSE")
    print("LOCAL_ZERO_NETWORK_RTT_DECISION=TRUE")
    print("MEMBER_PLAINTEXT_TO_CLOUD=FALSE")
    print("RAW_API_KEY_READ=FALSE")
    print("EXTERNAL_API_CALL=FALSE")
    print("CANDIDATE_ONLY=TRUE")
    print("LLM_HALLUCINATION=CONDITIONALLY_ALLOWED_AS_IMAGINED_CANDIDATE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
