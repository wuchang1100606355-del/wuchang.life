"""Deployable CLI/runtime/server composition for the V2.1 mesh adapter."""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

from .core import (
    CAPABILITY_INVENTORY_SCHEMA,
    PRIMARY_DECISION_ENGINE,
    TOTAL_FIELD_AUTHORITY_REF,
    TOTAL_FIELD_AUTHORITY_NODE_REF,
    MeshError,
    MeshHold,
    require_core,
)
from .inventory import collect_snapshot
from .journal import MeshStorage
from .native_adi import NativeADIAdapter, build_native_adi_record
from .packet import BuiltTransfer, build_transfer
from .receiver import MeshReceiver
from .spool import produce_drive_projection_envelopes
from .transport import MeshTransport


def _reject_float(value: str) -> None:
    raise MeshHold("HOLD_CONFIG_FLOAT_FORBIDDEN")


def _reject_constant(value: str) -> None:
    del value
    raise MeshHold("HOLD_CONFIG_NONFINITE_FORBIDDEN")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MeshHold("HOLD_CONFIG_DUPLICATE_KEY")
        result[key] = value
    return result


def load_config(path: str | os.PathLike[str]) -> dict[str, object]:
    try:
        raw = Path(path).read_text(encoding="utf-8")
        parsed = json.loads(
            raw,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
            object_pairs_hook=_pairs,
        )
    except OSError as exc:
        raise MeshHold("HOLD_CONFIG_READ_FAILED") from exc
    except json.JSONDecodeError as exc:
        raise MeshHold("HOLD_CONFIG_JSON_INVALID") from exc
    if not isinstance(parsed, dict):
        raise MeshHold("HOLD_CONFIG_ROOT_INVALID")
    return parsed


class MeshRuntime:
    def __init__(self, config: Mapping[str, object]) -> None:
        require_core()
        runtime_root = config.get("runtime_root")
        node_id = config.get("node_id")
        if not isinstance(runtime_root, str) or not runtime_root:
            raise MeshHold("HOLD_RUNTIME_ROOT_REQUIRED")
        if not isinstance(node_id, str) or not node_id:
            raise MeshHold("HOLD_NODE_ID_REQUIRED")
        self.config = dict(config)
        self.storage = MeshStorage(runtime_root)
        self.receiver = MeshReceiver(self.storage, receiver_node_ref=f"node:{node_id}")
        self.transport = MeshTransport(self.storage)
        native_adi_url = config.get("native_adi_url")
        if native_adi_url is not None and node_id != "taiji01":
            raise MeshHold("HOLD_NATIVE_ADI_AUTHORITY_NODE_ONLY")
        self.native_adi = (
            NativeADIAdapter(
                self.storage,
                base_url=str(native_adi_url),
                timeout_seconds=int(config.get("native_adi_timeout_seconds", 10)),
            )
            if native_adi_url is not None
            else None
        )
        self.last_native_adi_result: dict[str, object] | None = None

    def close(self) -> None:
        self.storage.close()

    def __enter__(self) -> "MeshRuntime":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback
        self.close()

    def collect(self) -> BuiltTransfer:
        source_node_ref = f"node:{self.config['node_id']}"
        logical_time = self.storage.journal.next_logical_time(source_node_ref)
        snapshot = collect_snapshot(self.config, logical_time=logical_time)
        authority_ref = self.config.get("authority_ref", TOTAL_FIELD_AUTHORITY_REF)
        authority_node_ref = self.config.get("total_field_authority_node_ref", TOTAL_FIELD_AUTHORITY_NODE_REF)
        decision_engine = self.config.get("primary_decision_engine", PRIMARY_DECISION_ENGINE)
        decision_engine_role = self.config.get("primary_decision_engine_role", "PRIMARY_DECISION_ENGINE_NOT_AUTHORITY")
        namespace = self.config.get("namespace", "w7tp.mesh.node-state.v21")
        ttl = self.config.get("ttl_seconds", 300)
        if (
            authority_ref != TOTAL_FIELD_AUTHORITY_REF
            or authority_node_ref != TOTAL_FIELD_AUTHORITY_NODE_REF
            or decision_engine != PRIMARY_DECISION_ENGINE
            or decision_engine_role != "PRIMARY_DECISION_ENGINE_NOT_AUTHORITY"
            or not isinstance(namespace, str)
            or isinstance(ttl, bool)
            or not isinstance(ttl, int)
        ):
            raise MeshHold("HOLD_PACKET_CONFIG_INVALID")
        transfer = build_transfer(
            self.storage,
            snapshot,
            authority_ref=authority_ref,
            namespace=namespace,
            ttl_seconds=ttl,
        )
        if self.native_adi is not None:
            record = build_native_adi_record(
                source_node_ref=str(snapshot["source_node_ref"]),
                packet_id=str(transfer.packet["envelope"]["packet_id"]),
                packet_ref=transfer.packet_ref,
                observed_at=str(snapshot["observed_at"]),
                local_logical_time=transfer.logical_time,
                snapshot_ref=transfer.target_snapshot_ref,
                capability_ref=transfer.capability_inventory_ref,
                reconstruction_ref=transfer.target_snapshot_ref,
                receipt_ref="receipt:LOCAL_SOURCE_BUILD_NO_REMOTE_RECEIPT",
                authority_state="TOTAL_FIELD_UNIQUE_AUTHORITY_PACKET_CANDIDATE",
            )
            self.last_native_adi_result = self.native_adi.insert_or_queue(record)
        return transfer

    def latest_outbound(self) -> dict[str, object]:
        records = list(self.storage.journal.records("outbound"))
        if not records:
            raise MeshHold("HOLD_NO_OUTBOUND_PACKET")
        return max(records, key=lambda item: int(item.get("logical_time", 0)))

    def send_latest(self, peer_url: str) -> dict[str, object]:
        outbound = self.latest_outbound()
        carrier_ref = outbound.get("carrier_ref")
        if not isinstance(carrier_ref, str):
            raise MeshHold("HOLD_OUTBOUND_CARRIER_REF")
        carrier = self.storage.get_artifact(carrier_ref)
        timeout = self.config.get("http_timeout_seconds", 10)
        if isinstance(timeout, bool) or not isinstance(timeout, int):
            raise MeshHold("HOLD_HTTP_TIMEOUT_INVALID")
        return self.transport.send(
            carrier,
            carrier_ref=carrier_ref,
            peer_url=peer_url,
            timeout_seconds=timeout,
        )

    def spool_transfer(self, transfer: BuiltTransfer) -> tuple[Path, ...]:
        spool_root = self.config.get("drive_spool_root")
        if not isinstance(spool_root, str) or not spool_root:
            raise MeshHold("HOLD_DRIVE_SPOOL_ROOT_REQUIRED")
        snapshot = self.storage.get_artifact(transfer.target_snapshot_ref)
        lineage_records = [
            item
            for item in self.storage.journal.records("lineage")
            if item.get("packet_ref") == transfer.packet_ref
        ]
        if len(lineage_records) != 1:
            raise MeshHold("HOLD_LINEAGE_CARDINALITY")
        receipts = [
            item
            for item in self.storage.journal.records("receipts")
            if item.get("packet_ref") == transfer.packet_ref
        ]
        return produce_drive_projection_envelopes(
            spool_root,
            snapshot=snapshot,
            packet=transfer.packet,
            profile=transfer.profile,
            lineage=lineage_records[0],
            capability_inventory=transfer.capability_inventory,
            receipts=receipts,
        )

    def spool_received(
        self,
        carrier: Mapping[str, object],
        receipt: Mapping[str, object],
    ) -> tuple[Path, ...]:
        spool_root = self.config.get("drive_spool_root")
        if not isinstance(spool_root, str) or not spool_root:
            return ()
        packet = carrier.get("packet")
        object_packets = carrier.get("object_packets")
        if not isinstance(packet, Mapping) or not isinstance(object_packets, list):
            raise MeshHold("HOLD_RECEIVED_SPOOL_CARRIER_INVALID")
        profiles = [
            item.get("artifact")
            for item in object_packets
            if isinstance(item, Mapping)
            and isinstance(item.get("artifact"), Mapping)
            and item["artifact"].get("schema_id") == "W7TP_GT_MESH_DOMAIN_PROFILE_V21"
        ]
        if len(profiles) != 1:
            raise MeshHold("HOLD_RECEIVED_SPOOL_PROFILE_CARDINALITY")
        capabilities = [
            item.get("artifact")
            for item in object_packets
            if isinstance(item, Mapping)
            and isinstance(item.get("artifact"), Mapping)
            and item["artifact"].get("schema_id") == CAPABILITY_INVENTORY_SCHEMA
        ]
        if len(capabilities) != 1:
            raise MeshHold("HOLD_RECEIVED_SPOOL_CAPABILITY_CARDINALITY")
        target_ref = receipt.get("target_snapshot_ref")
        packet_ref = receipt.get("packet_ref")
        if not isinstance(target_ref, str) or not isinstance(packet_ref, str):
            raise MeshHold("HOLD_RECEIVED_SPOOL_RECEIPT_REFS")
        snapshot = self.storage.get_artifact(target_ref)
        lineages = [
            item
            for item in self.storage.journal.records("lineage")
            if item.get("packet_ref") == packet_ref
            and item.get("receiver_node_ref") == self.receiver.receiver_node_ref
        ]
        if len(lineages) != 1:
            raise MeshHold("HOLD_RECEIVED_SPOOL_LINEAGE_CARDINALITY")
        return produce_drive_projection_envelopes(
            spool_root,
            snapshot=snapshot,
            packet=packet,
            profile=profiles[0],
            lineage=lineages[0],
            capability_inventory=capabilities[0],
            receipts=[receipt],
        )

    def publish_received_native_adi(
        self,
        carrier: Mapping[str, object],
        receipt: Mapping[str, object],
    ) -> dict[str, object] | None:
        if self.native_adi is None:
            return None
        packet = carrier.get("packet")
        object_packets = carrier.get("object_packets")
        if not isinstance(packet, Mapping) or not isinstance(object_packets, list):
            raise MeshHold("HOLD_NATIVE_ADI_RECEIVED_CARRIER")
        profiles = [
            item.get("artifact")
            for item in object_packets
            if isinstance(item, Mapping)
            and isinstance(item.get("artifact"), Mapping)
            and item["artifact"].get("schema_id") == "W7TP_GT_MESH_DOMAIN_PROFILE_V21"
        ]
        if len(profiles) != 1:
            raise MeshHold("HOLD_NATIVE_ADI_PROFILE_CARDINALITY")
        profile = profiles[0]
        control_plane = profile.get("control_plane")
        if not isinstance(control_plane, Mapping):
            raise MeshHold("HOLD_NATIVE_ADI_CONTROL_PLANE")
        target_snapshot_ref = receipt.get("target_snapshot_ref")
        if not isinstance(target_snapshot_ref, str):
            raise MeshHold("HOLD_NATIVE_ADI_TARGET_SNAPSHOT_REF")
        reconstructed_snapshot = self.storage.get_artifact(target_snapshot_ref)
        record = build_native_adi_record(
            source_node_ref=str(receipt.get("source_node_ref")),
            packet_id=str(receipt.get("packet_id")),
            packet_ref=str(receipt.get("packet_ref")),
            observed_at=str(reconstructed_snapshot.get("observed_at")),
            local_logical_time=int(receipt.get("logical_time")),
            snapshot_ref=target_snapshot_ref,
            capability_ref=str(control_plane.get("capability_inventory_ref")),
            reconstruction_ref=target_snapshot_ref,
            receipt_ref=str(receipt.get("receipt_ref")),
            authority_state=str(receipt.get("authority_state")),
        )
        result = self.native_adi.insert_or_queue(record)
        self.last_native_adi_result = result
        return result

    def cycle(self) -> dict[str, object]:
        transfer = self.collect()
        projected = self.spool_transfer(transfer) if self.config.get("drive_spool_root") else ()
        peers = self.config.get("peers", [])
        if not isinstance(peers, list):
            raise MeshHold("HOLD_PEERS_CONFIG_INVALID")
        results: list[dict[str, object]] = []
        for item in peers:
            if not isinstance(item, Mapping) or not isinstance(item.get("peer_id"), str) or not isinstance(item.get("url"), str):
                raise MeshHold("HOLD_PEER_CONFIG_INVALID")
            result = self.transport.send(
                transfer.carrier,
                carrier_ref=transfer.carrier_ref,
                peer_url=str(item["url"]),
                timeout_seconds=int(self.config.get("http_timeout_seconds", 10)),
            )
            results.append({"peer_id": item["peer_id"], "result": result})
        return {
            "state": "PASS_CYCLE_COMPLETED_WITH_ORTHOGONAL_PEER_RESULTS",
            "packet_ref": transfer.packet_ref,
            "carrier_ref": transfer.carrier_ref,
            "logical_time": transfer.logical_time,
            "transfer_mode": transfer.transfer_mode,
            "drive_projection_count": len(projected),
            "peer_results": results,
            "native_adi_result": self.last_native_adi_result,
            "authority_ref": TOTAL_FIELD_AUTHORITY_REF,
            "authority_node_ref": TOTAL_FIELD_AUTHORITY_NODE_REF,
            "primary_decision_engine": PRIMARY_DECISION_ENGINE,
            "decision_engine_authority_state": "NOT_AUTHORITY",
            "authority_state": "TOTAL_FIELD_AUTHORITY_REQUIRED_PACKET_CANDIDATE",
        }


def make_server(runtime: MeshRuntime, host: str, port: int, max_body_bytes: int) -> ThreadingHTTPServer:
    core = require_core()

    class Handler(BaseHTTPRequestHandler):
        server_version = "W7TPGTMeshV21/1"

        def log_message(self, format: str, *args: object) -> None:
            del format, args

        def _reply(self, status: int, value: Mapping[str, object]) -> None:
            raw = core.canonical_json_bytes(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            if self.path != "/healthz":
                self._reply(404, {"state": "NOT_FOUND"})
                return
            self._reply(
                200,
                {
                    "state": "LIVE_SERVICE_PRESENCE_ONLY",
                    "canonical_id": "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1",
                    "carrier_authority": "NONE",
                    "authority_ref": TOTAL_FIELD_AUTHORITY_REF,
                    "authority_node_ref": TOTAL_FIELD_AUTHORITY_NODE_REF,
                    "primary_decision_engine": PRIMARY_DECISION_ENGINE,
                    "decision_engine_authority_state": "NOT_AUTHORITY",
                    "final_authority_granted": False,
                },
            )

        def do_POST(self) -> None:
            if self.path.rstrip("/") != "/v2.1/packets":
                self._reply(404, {"state": "NOT_FOUND"})
                return
            length_text = self.headers.get("Content-Length")
            if length_text is None or not length_text.isdigit():
                self._reply(411, {"state": "HOLD", "reason_code": "CONTENT_LENGTH_REQUIRED"})
                return
            length = int(length_text)
            if length < 1 or length > max_body_bytes:
                self._reply(413, {"state": "HOLD", "reason_code": "CARRIER_BODY_SIZE_INVALID"})
                return
            raw = self.rfile.read(length)
            try:
                carrier = core.canonical_json_loads(raw, require_canonical=True)
                if not isinstance(carrier, dict):
                    raise MeshHold("HOLD_CARRIER_NOT_OBJECT")
                receipt = runtime.receiver.receive(carrier)
                runtime.spool_received(carrier, receipt)
                runtime.publish_received_native_adi(carrier, receipt)
            except MeshError as exc:
                self._reply(409, {"state": "HOLD", "reason_code": exc.code})
                return
            except Exception:
                self._reply(500, {"state": "HOLD", "reason_code": "INTERNAL_RECEIVER_FAILURE"})
                return
            self._reply(200, receipt)

    return ThreadingHTTPServer((host, port), Handler)


def _emit(value: Mapping[str, object]) -> None:
    sys.stdout.buffer.write(require_core().canonical_json_bytes(value) + b"\n")


def render_human_summary(value: Mapping[str, object], config: Mapping[str, object]) -> str:
    """Render the required final human-facing Traditional Chinese summary."""

    node_id = str(config.get("node_id") or value.get("node_id") or "UNKNOWN")
    result_state = str(value.get("state") or value.get("delivery_state") or "UNKNOWN")
    packet_ref = str(value.get("packet_ref") or "UNKNOWN")
    transfer_mode = str(value.get("transfer_mode") or "UNKNOWN")
    container_state = "已啟用容器與相關資源的唯讀索引" if isinstance(config.get("containers"), Mapping) and config["containers"].get("enabled", True) is True else "本次未啟用容器索引，狀態保持未知"
    transfer_labels = {
        "DIRECT_TRANSFER_BASELINE": "完整正典基線傳輸",
        "W7TP_GENERATIVE_DELTA": "相對既有基線的增量差分傳輸",
        "W7TP_ADI_KNOWN_NOVEL_V3": "已知／新穎區塊座標生成式傳輸",
    }
    transfer_text = transfer_labels.get(transfer_mode, "本次沒有可確認的傳輸模式")
    reason_code = str(value.get("reason_code") or "")
    if "CORE" in reason_code:
        hold_reason = "既有 W7TP 核心子集尚不可用，無法安全建立或驗證封包"
    elif "AUTHORITY" in reason_code:
        hold_reason = "總場權威參照或授權條件不符合既定契約"
    elif "TTL" in reason_code or "TIME" in reason_code:
        hold_reason = "封包時效或整數時間座標不符合驗證條件"
    elif "CONFIG" in reason_code or "URL" in reason_code:
        hold_reason = "節點設定或受控端點座標不完整或不合法"
    elif "NATIVE_ADI" in reason_code:
        hold_reason = "taiji01 的既有 Native ADI 端點目前無法完成受控寫入或回應驗證"
    elif "CARRIER" in reason_code or "HTTP" in reason_code:
        hold_reason = "節點間承載路徑目前不可用或回應不符合契約"
    else:
        hold_reason = "必要證據、相依或交叉驗證條件尚未全部滿足"
    if result_state.startswith("HOLD"):
        result_text = f"本輪已安全暫停，因為{hold_reason}；沒有把未知狀態補成成功。"
        risk = "暫停原因已保留為可追查證據；修復最短缺失條件前，不會執行控制或升格權威。"
    elif result_state.startswith("PASS"):
        result_text = f"本輪流程已完成，採用{transfer_text}；封包證據參照為（{packet_ref}）。"
        risk = "控制執行器尚未接線；未觀測或不可用狀態保持未知，封包與 Drive 投影不自行成為實際執行效果。"
    else:
        result_text = f"本輪結果尚未形成可確認結論；{transfer_text}，相關封包證據參照為（{packet_ref}）。"
        risk = "結果仍需後續可驗證證據；目前不執行控制，也不把節點、模型、承載或投影升格為權威。"
    return "\n".join(
        [
            "人類繁中摘要",
            "意圖：以 W7TP V2.1 8D 狀態場封包，增量傳輸並精確重建節點與容器 metadata。",
            "總場理由：TOTAL_FIELD 是唯一邏輯權威；taiji01 是 verifier／Native ADI primary／state sealer／receipt issuer，8D_ADI 只負責主要決策，MSI 與 Drive 只做來源、驗證及投影。",
            f"節點／容器：本次處理節點為 {node_id}；{container_state}；Tailscale 安全拓撲與硬體能力只依實際觀測或未知狀態建立索引。",
            f"結果：{result_text}",
            f"風險／未知：{risk}",
        ]
    )


def _emit_result(value: Mapping[str, object], config: Mapping[str, object]) -> None:
    _emit(value)
    sys.stdout.write(render_human_summary(value, config) + "\n")
    sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="w7tp-gt-mesh-v21")
    parser.add_argument("--config", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--spool", action="store_true")
    send_parser = sub.add_parser("send")
    send_parser.add_argument("--peer-url", required=True)
    sub.add_parser("cycle")
    sub.add_parser("retry")
    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--host")
    serve_parser.add_argument("--port", type=int)
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        with MeshRuntime(config) as runtime:
            if args.command == "doctor":
                _emit_result(
                    {
                        "state": "PASS_CORE_READY",
                        "node_id": config.get("node_id"),
                        "authority_ref": TOTAL_FIELD_AUTHORITY_REF,
                        "authority_node_ref": TOTAL_FIELD_AUTHORITY_NODE_REF,
                        "primary_decision_engine": PRIMARY_DECISION_ENGINE,
                        "decision_engine_authority_state": "NOT_AUTHORITY",
                        "control_execution_state": "NOT_WIRED_NO_SIDE_EFFECT",
                    },
                    config,
                )
            elif args.command == "collect":
                transfer = runtime.collect()
                projected = runtime.spool_transfer(transfer) if args.spool else ()
                _emit_result(
                    {
                        "state": "PASS_TRANSFER_BUILT_CANDIDATE_ONLY",
                        "packet_ref": transfer.packet_ref,
                        "carrier_ref": transfer.carrier_ref,
                        "target_snapshot_ref": transfer.target_snapshot_ref,
                        "logical_time": transfer.logical_time,
                        "transfer_mode": transfer.transfer_mode,
                        "drive_projection_count": len(projected),
                    },
                    config,
                )
            elif args.command == "send":
                _emit_result(runtime.send_latest(args.peer_url), config)
            elif args.command == "cycle":
                _emit_result(runtime.cycle(), config)
            elif args.command == "retry":
                results = runtime.transport.retry_pending(timeout_seconds=int(config.get("http_timeout_seconds", 10)))
                native_results = runtime.native_adi.retry_pending() if runtime.native_adi is not None else []
                _emit_result(
                    {
                        "state": "PASS_RETRY_CYCLE_COMPLETE",
                        "result_count": len(results),
                        "results": results,
                        "native_adi_result_count": len(native_results),
                        "native_adi_results": native_results,
                    },
                    config,
                )
            elif args.command == "serve":
                host = args.host or str(config.get("listen_host", "127.0.0.1"))
                port = args.port or int(config.get("listen_port", 9191))
                max_body = int(config.get("max_body_bytes", 16 * 1024 * 1024))
                server = make_server(runtime, host, port, max_body)
                try:
                    server.serve_forever(poll_interval=1)
                finally:
                    server.server_close()
    except MeshError as exc:
        failure = {"state": "HOLD", "reason_code": exc.code}
        try:
            summary_config = config
        except UnboundLocalError:
            summary_config = {}
        _emit_result(failure, summary_config)
        return 2
    return 0
