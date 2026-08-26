"""Candidate evidence loop using exactly one existing isolated Receiver."""

from __future__ import annotations

import hashlib
import json
import os
import resource
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from w7tp_runtime.gt_packet_v2 import PacketV2

from .bridge import BRIDGE_MODES, PlacementPlanner, build_delta, execute_bridge
from .contracts import (
    ALGORITHM_VERSION,
    RECEIPT_SCHEMA,
    ContractError,
    build_candidate_packet,
    canonical_bytes,
    probe_resource_catalog,
    sha256_bytes,
    sha256_file,
    utc_text,
    validate_candidate_packet,
)


RECEIVER_ADAPTER_ID = "w7tp_runtime.gt_packet_v2.PacketV2.isolated_receive"
WRITE_ROOT = Path("/tmp/w7tp_controlled_experiment_v1")
FORBIDDEN_REPOSITORY_PREFIXES = (
    "runtime/total_field",
    "configs/total_field/active_total_field_authority_runtime_v1.json",
    "tools/total_field/w7tp_canonical_pointer_governance.py",
    "tools/total_field/w7tp_governed_promotion.py",
    "tools/total_field_authority_resolver.py",
    "tools/total_field_authority_runtime_bindings.py",
    "Taiji_Odoo",
    "data/secrets",
    ".env",
)


class IsolationError(RuntimeError):
    """The candidate attempted to cross its isolated write boundary."""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def require_isolated_output(path: Path) -> Path:
    if WRITE_ROOT.exists() and WRITE_ROOT.is_symlink():
        raise IsolationError("WRITE_ROOT_SYMLINK_HOLD")
    resolved = path.resolve(strict=False)
    allowed = WRITE_ROOT.resolve(strict=False)
    if not _is_relative_to(resolved, allowed) or resolved == allowed:
        raise IsolationError("OUTPUT_OUTSIDE_CANDIDATE_TMP_BOUNDARY")
    current = resolved.parent
    while _is_relative_to(current, allowed) and current != allowed:
        if current.exists() and current.is_symlink():
            raise IsolationError("OUTPUT_SYMLINK_BOUNDARY_HOLD")
        current = current.parent
    return resolved


def write_bytes_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def write_json_new(path: Path, value: object) -> None:
    write_bytes_new(path, canonical_bytes(value) + b"\n")


class SingleCandidateIngress:
    """Validation wrapper around the one pre-existing isolated Receiver."""

    receiver_adapter_id = RECEIVER_ADAPTER_ID

    def __init__(self) -> None:
        self._receiver = PacketV2()
        self._seen: set[str] = set()
        self._next_sequence = 1

    def receive(
        self,
        carrier: Path,
        output_root: Path,
        *,
        now: datetime,
    ) -> tuple[dict[str, object], object]:
        result = self._receiver.isolated_receive(carrier, output_root)
        received_path = output_root / "received.bin"
        try:
            packet = json.loads(received_path.read_bytes())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContractError("RECEIVER_PACKET_JSON_HOLD") from exc
        if not isinstance(packet, dict):
            raise ContractError("RECEIVER_PACKET_OBJECT_HOLD")
        validate_candidate_packet(packet, now=now)
        packet_hash = packet.get("packet_sha256")
        if packet_hash in self._seen:
            raise ContractError("RECEIVER_DUPLICATE_PACKET_HOLD")
        if packet.get("sequence") != self._next_sequence:
            raise ContractError("RECEIVER_SEQUENCE_HOLD")
        if sha256_file(received_path) != sha256_bytes(canonical_bytes(packet)):
            raise ContractError("RECEIVER_CONTENT_HASH_HOLD")
        self._seen.add(str(packet_hash))
        self._next_sequence += 1
        return packet, result


def _git_head(repo_root: Path) -> str:
    head = repo_root / ".git" / "HEAD"
    try:
        value = head.read_text(encoding="utf-8").strip()
        if value.startswith("ref: "):
            ref = repo_root / ".git" / value[5:]
            return ref.read_text(encoding="utf-8").strip()
        return value
    except OSError:
        return "UNKNOWN_UNVERIFIED"


def _peak_ram_bytes() -> int:
    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(maximum * 1024 if sys.platform != "darwin" else maximum)


def _synthetic_inputs() -> tuple[bytes, bytes]:
    base = (
        b'{"member":"SYNTHETIC","intent":"controlled-demo","events":['
        + b'{"step":1,"state":"READY"},' * 128
        + b'{"step":2,"state":"BASE"}]}'
    )
    target = base.replace(b'"BASE"', b'"RECONSTRUCTED"') + b"\n"
    return base, target


def _independent_verify(
    *,
    packet_path: Path,
    received_path: Path,
    output_path: Path,
    expected_sha256: str,
) -> dict[str, object]:
    packet_bytes = packet_path.read_bytes()
    received = received_path.read_bytes()
    output = output_path.read_bytes()
    checks = {
        "packet_receiver_byte_identity": packet_bytes == received,
        "packet_file_hash_matches": sha256_bytes(packet_bytes) == sha256_bytes(received),
        "reconstructed_hash_matches": sha256_bytes(output) == expected_sha256,
    }
    return {
        "verifier_id": "w7tp-controlled-experiment-independent-verifier-v1",
        "result": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
    }


def _receipt(
    *,
    run_id: str,
    scenario_id: str,
    sequence: int,
    mode: str,
    packet: Mapping[str, object],
    packet_path: Path,
    carrier_path: Path,
    received_path: Path,
    output_path: Path,
    delta: Mapping[str, object],
    placement: Mapping[str, object],
    bridge: object,
    verifier: Mapping[str, object],
    source_commit: str,
    now: datetime,
) -> dict[str, object]:
    target_hash = str(packet["source"]["target_sha256"])  # type: ignore[index]
    carrier_bytes = carrier_path.stat().st_size
    metadata_bytes = packet_path.stat().st_size
    delta_bytes = len(canonical_bytes(delta))
    result = {
        "schema_id": RECEIPT_SCHEMA,
        "run_id": run_id,
        "scenario_id": scenario_id,
        "logical_time": sequence,
        "candidate_only": True,
        "authority_state": "AUTHORIZED_CANDIDATE_ONLY",
        "source_node": "MSI",
        "receiver_node": "MSI_LOCAL_CANDIDATE",
        "receiver_adapter": RECEIVER_ADAPTER_ID,
        "identity_ref": packet["identity_ref"],
        "member_ref": packet["member_ref"],
        "xiaoj_ref": packet["xiaoj_ref"],
        "commit_hash": source_commit,
        "config_hash": sha256_bytes(canonical_bytes(packet["authorization_scope"])),
        "seed_hash": sha256_bytes(b"W7TP_CONTROLLED_EXPERIMENT_V1_FIXED_SEED"),
        "baseline_id": f"{run_id}:FULL_COPY",
        "candidate_id": f"{run_id}:{mode}",
        "base_sha256": packet["source"]["base_sha256"],  # type: ignore[index]
        "index_sha256": sha256_bytes(canonical_bytes(delta)),
        "delta_sha256": sha256_bytes(bytes.fromhex(str(delta["replacement_hex"]))),
        "carrier_sha256": sha256_file(carrier_path),
        "logical_bytes": bridge.logical_bytes,
        "carrier_bytes": carrier_bytes,
        "metadata_bytes": metadata_bytes,
        "per_hop_bytes": {
            "origin_egress": carrier_bytes,
            "receiver_ingress": carrier_bytes,
            "receiver_to_bridge": received_path.stat().st_size,
            "bridge_to_verifier": output_path.stat().st_size,
        },
        "retained_bytes": {
            "base": int(packet["source"]["base_bytes"]),  # type: ignore[index]
            "index": delta_bytes,
            "delta": int(delta["replacement_bytes"]),
            "metadata": metadata_bytes,
            "checkpoint": 0,
        },
        "tokens": {
            "input": 0,
            "processed": 0,
            "method": "NONE_BYTE_WORKLOAD",
            "claim": "NO_MODEL_TOKEN_REDUCTION_CLAIM",
        },
        "latency": {
            "single_run_ns": bridge.latency_ns,
            "p50_ns": None,
            "p95_ns": None,
            "phase_c_required": True,
        },
        "peak_vram_bytes": 0,
        "peak_ram_bytes": _peak_ram_bytes(),
        "h2d_bytes": bridge.h2d_bytes,
        "d2h_bytes": bridge.d2h_bytes,
        "planned_placement": dict(placement),
        "actual_placement": dict(placement),
        "bridge_mode": mode,
        "bridge_evidence_state": bridge.evidence_state,
        "reconstructed_sha256": sha256_file(output_path),
        "expected_sha256": target_hash,
        "authorization": packet["authorization_scope"],
        "lease": {"packet_expires_at": packet["expires_at"], "state": "ACTIVE_AT_EXECUTION"},
        "revocation": {"checked": True, "revoked": False},
        "fallback": {"policy": packet["fallback"], "used": bridge.fallback_used},
        "failure_injection": "NOT_RUN_PHASE_B",
        "acceptance": "PASS" if verifier["result"] == "PASS" else "FAIL",
        "raw_evidence": {
            "packet_sha256": sha256_file(packet_path),
            "received_sha256": sha256_file(received_path),
            "output_sha256": sha256_file(output_path),
        },
        "independent_verifier": dict(verifier),
        "protected_state": {
            "member_plaintext": "EXCLUDED_SYNTHETIC_ONLY",
            "secrets": "EXCLUDED_NOT_READ",
            "canonical": "READ_ONLY_HASH_PREIMAGE_ONLY",
        },
        "algorithm_version": ALGORITHM_VERSION,
        "total_field_decision": "NOT_REVIEWED",
        "issued_at": utc_text(now),
    }
    result["receipt_sha256"] = sha256_bytes(canonical_bytes(result))
    return result


def _demo_html(summary: Mapping[str, object]) -> bytes:
    safe = json.dumps(summary, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>W7TP 受控試驗 Candidate</title>
<style>body{{font:16px system-ui;max-width:980px;margin:auto;padding:2rem;background:#10151d;color:#eaf2ff}}.tag{{padding:.2rem .5rem;border:1px solid #69a;border-radius:.4rem}}pre{{white-space:pre-wrap;background:#172232;padding:1rem;overflow:auto}}th,td{{padding:.5rem;border-bottom:1px solid #345;text-align:left}}</style></head>
<body><h1>W7TP 受控試驗系統 <span class="tag">CANDIDATE</span></h1>
<p>合成輸入 → 既有 Single Candidate Receiver → placement → reconstruction → independent verification → append-only receipt</p>
<p>正式狀態：<strong>NOT_REVIEWED</strong>。GPU 路徑：<strong>SIMULATED</strong>。不提供 canonical、authority、會員或 production 寫入功能。</p>
<div id="app"></div><script>const s={safe};const rows=s.scenarios.map(x=>`<tr><td>${{x.mode}}</td><td>${{x.evidence_state}}</td><td>${{x.acceptance}}</td><td>${{x.receipt_sha256}}</td></tr>`).join('');document.querySelector('#app').innerHTML=`<table><tr><th>模式</th><th>證據</th><th>驗證</th><th>Receipt</th></tr>${{rows}}</table><h2>原始狀態</h2><pre>${{JSON.stringify(s,null,2)}}</pre>`;</script></body></html>""".encode("utf-8")


def _manifest(root: Path) -> bytes:
    entries: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != "MANIFEST.sha256"):
        entries.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    return ("\n".join(entries) + "\n").encode("utf-8")


def run_controlled_demo(
    *,
    output_dir: Path,
    repo_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    now = (now or datetime.now(UTC)).astimezone(UTC)
    output = require_isolated_output(output_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(mode=0o700, exist_ok=False)
    run_id = f"W7TP_CE_{hashlib.sha256((str(output) + utc_text(now)).encode()).hexdigest()[:24]}"
    source_commit = _git_head(repo_root.resolve())
    base, target = _synthetic_inputs()
    delta = build_delta(base, target)
    catalog = probe_resource_catalog(now=now)
    write_json_new(output / "resource_catalog.json", catalog)
    planner = PlacementPlanner(catalog["resources"])  # type: ignore[arg-type]
    ingress = SingleCandidateIngress()
    scenarios: list[dict[str, object]] = []
    receipts_dir = output / "receipts"

    for sequence, mode in enumerate(BRIDGE_MODES, start=1):
        scenario_id = f"S{sequence:02d}_{mode}"
        scenario_root = output / "scenarios" / scenario_id
        packet = build_candidate_packet(
            run_id=run_id,
            task_id="SYNTHETIC_CONTROLLED_RECONSTRUCTION",
            scenario_id=scenario_id,
            sequence=sequence,
            source_version=source_commit,
            base=base,
            target=target,
            delta=delta,
            resource_ids=[
                str(item["resource_id"])
                for item in catalog["resources"]  # type: ignore[index]
                if item["authority_state"] == "AUTHORIZED_CANDIDATE_ONLY"
                and item["lease"]["state"] == "ACTIVE"
            ],
            issued_at=now,
        )
        packet_path = scenario_root / "candidate_packet.json"
        write_bytes_new(packet_path, canonical_bytes(packet))
        carrier_path = scenario_root / "carrier.html"
        carrier_run = f"W7TP_GTF_{sha256_bytes(canonical_bytes(packet))[:32]}"
        PacketV2().compose(packet_path, carrier_path, carrier_run, "candidate_packet.json", intent="DIRECT_TRANSFER_ALLOWED")
        receiver_root = scenario_root / "receiver"
        received_packet, receiver_result = ingress.receive(carrier_path, receiver_root, now=now)
        if received_packet != packet:
            raise ContractError("RECEIVER_PACKET_IDENTITY_HOLD")
        placement = planner.choose(mode, now=now)
        bridge = execute_bridge(mode, base=base, target=target, delta=delta, placement=placement)
        output_path = scenario_root / "reconstructed.bin"
        write_bytes_new(output_path, bridge.output)
        verifier = _independent_verify(
            packet_path=packet_path,
            received_path=receiver_root / "received.bin",
            output_path=output_path,
            expected_sha256=sha256_bytes(target),
        )
        receiver_evidence = asdict(receiver_result)
        receiver_evidence["packet_path"] = str(receiver_evidence["packet_path"])
        raw_evidence = {
            "schema_id": "W7TP_CONTROLLED_EXPERIMENT_RAW_EVIDENCE_V1",
            "run_id": run_id,
            "scenario_id": scenario_id,
            "packet_sha256": sha256_file(packet_path),
            "carrier_sha256": sha256_file(carrier_path),
            "received_sha256": sha256_file(receiver_root / "received.bin"),
            "output_sha256": sha256_file(output_path),
            "receiver_result": receiver_evidence,
            "verifier": verifier,
        }
        raw_path = scenario_root / "raw_evidence.json"
        write_json_new(raw_path, raw_evidence)
        receipt = _receipt(
            run_id=run_id,
            scenario_id=scenario_id,
            sequence=sequence,
            mode=mode,
            packet=packet,
            packet_path=packet_path,
            carrier_path=carrier_path,
            received_path=receiver_root / "received.bin",
            output_path=output_path,
            delta=delta,
            placement=placement.as_dict(),
            bridge=bridge,
            verifier=verifier,
            source_commit=source_commit,
            now=now,
        )
        receipt_path = receipts_dir / f"{sequence:04d}_{receipt['receipt_sha256']}.json"
        write_json_new(receipt_path, receipt)
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "mode": mode,
                "evidence_state": bridge.evidence_state,
                "acceptance": receipt["acceptance"],
                "receipt_sha256": receipt["receipt_sha256"],
                "receipt_ref": receipt_path.relative_to(output).as_posix(),
                "logical_bytes": bridge.logical_bytes,
                "bridge_input_bytes": bridge.bridge_input_bytes,
            }
        )

    summary: dict[str, object] = {
        "schema_id": "W7TP_CONTROLLED_EXPERIMENT_SUMMARY_V1",
        "state": "PHASE_B_CANDIDATE_FUNCTIONAL",
        "candidate_only": True,
        "ready_for_controlled_demo": False,
        "phase_c_required": True,
        "run_id": run_id,
        "source_commit": source_commit,
        "receiver_adapter": RECEIVER_ADAPTER_ID,
        "identity_ref": "UNKNOWN_UNVERIFIED",
        "member_ref": "UNKNOWN_UNVERIFIED",
        "session_9107": "NOT_VERIFIED",
        "total_field_decision": "NOT_REVIEWED",
        "canonical_mutation": False,
        "authority_mutation": False,
        "scenarios": scenarios,
        "claims": ["BYTE_EXACT_ON_FIXED_SYNTHETIC_PHASE_B_SCENARIO"],
        "not_verified": [
            "PHASE_C_FIVE_PAIRED_AB_RUNS",
            "P50_P95",
            "REAL_GPU_OR_VRAM",
            "MODEL_TOKEN_REDUCTION",
            "LIVE_SINGLE_RECEIVER_RECEIPT",
            "PRODUCTION_AUTHORITY_OR_CANONICAL",
        ],
        "repro_command": "python3 tools/run_w7tp_controlled_experiment_v1.py run",
    }
    summary["summary_sha256"] = sha256_bytes(canonical_bytes(summary))
    write_json_new(output / "demo_state.json", summary)
    write_bytes_new(output / "index.html", _demo_html(summary))
    write_bytes_new(output / "MANIFEST.sha256", _manifest(output))
    return summary


def verify_run(output_dir: Path) -> dict[str, object]:
    output = require_isolated_output(output_dir)
    summary_path = output / "demo_state.json"
    manifest_path = output / "MANIFEST.sha256"
    try:
        summary = json.loads(summary_path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("SUMMARY_UNAVAILABLE_OR_INVALID") from exc
    expected_summary_hash = summary.get("summary_sha256")
    summary_body = dict(summary)
    summary_body.pop("summary_sha256", None)
    checks: dict[str, bool] = {
        "summary_hash": expected_summary_hash == sha256_bytes(canonical_bytes(summary_body)),
        "candidate_only": summary.get("candidate_only") is True,
        "canonical_unchanged_by_contract": summary.get("canonical_mutation") is False,
        "authority_unchanged_by_contract": summary.get("authority_mutation") is False,
        "receiver_single": summary.get("receiver_adapter") == RECEIVER_ADAPTER_ID,
    }
    manifest_lines = manifest_path.read_text(encoding="utf-8").splitlines()
    for line in manifest_lines:
        digest, relative = line.split("  ", 1)
        checks[f"manifest:{relative}"] = sha256_file(output / relative) == digest
    receipts = sorted((output / "receipts").glob("*.json"))
    checks["receipt_count"] = len(receipts) == len(BRIDGE_MODES)
    for path in receipts:
        receipt = json.loads(path.read_bytes())
        supplied = receipt.get("receipt_sha256")
        body = dict(receipt)
        body.pop("receipt_sha256", None)
        checks[f"receipt_hash:{path.name}"] = supplied == sha256_bytes(canonical_bytes(body))
        checks[f"receipt_acceptance:{path.name}"] = receipt.get("acceptance") == "PASS"
        checks[f"receipt_d8:{path.name}"] = receipt.get("total_field_decision") == "NOT_REVIEWED"
    return {
        "schema_id": "W7TP_CONTROLLED_EXPERIMENT_INDEPENDENT_RUN_VERIFICATION_V1",
        "state": "PASS" if all(checks.values()) else "FAIL",
        "run_id": summary.get("run_id"),
        "checks": checks,
    }
