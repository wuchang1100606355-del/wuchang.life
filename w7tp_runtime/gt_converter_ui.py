"""Local-only W7TP-GTF background service and browser UI."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import secrets
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .gt_converter import ConverterFailure, GTConverter

JOB_STATES = {"QUEUED", "PACKING", "RECONSTRUCTING", "VERIFYING", "SEALING", "PASS", "HOLD", "BLOCK", "ERROR", "CANCELLED"}
RUN_ID_RE = re.compile(r"^W7TP_GTF_[A-Za-z0-9_.:-]{1,112}$")
MAX_REQUEST_BYTES = 64 * 1024 * 1024
UI_ROOT = Path(__file__).with_name("ui")


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


class JobStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.ledger = root / "ledger"
        self.jobs_root = root / "jobs"
        self.ledger.mkdir(parents=True, exist_ok=True)
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.jobs: dict[str, dict[str, Any]] = {}
        for path in self.ledger.glob("*.json"):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
                if RUN_ID_RE.fullmatch(item.get("run_id", "")) and item.get("state") in JOB_STATES:
                    self.jobs[item["run_id"]] = item
            except (OSError, ValueError):
                continue

    def save(self, job: dict[str, Any]) -> None:
        safe = {key: job.get(key) for key in ("state", "run_id", "progress", "source_name", "source_bytes", "packet_bytes", "reduction_ratio", "packet_sha256", "expected_sha256", "actual_sha256", "integrity", "authenticity", "verifier_decision", "reason_code", "packet_ready", "report_ready", "output_ready", "output_ref")}
        safe["source_name"] = html.escape(str(safe.get("source_name") or "source.bin"), quote=True)
        safe["reason_code"] = html.escape(str(safe["reason_code"]), quote=True) if safe.get("reason_code") else None
        target = self.ledger / f"{job['run_id']}.json"
        with self.lock:
            temporary = target.with_suffix(".tmp")
            temporary.write_bytes(_canonical(safe))
            os.replace(temporary, target)
            self.jobs[job["run_id"]] = safe

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self.lock:
            value = self.jobs.get(run_id)
            return dict(value) if value else None


class ConverterService:
    def __init__(self, root: Path) -> None:
        self.store = JobStore(root)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="w7tp-ui")
        self.cancelled: set[str] = set()
        self.output_claims: set[str] = set()
        self.lock = threading.RLock()
        self.csrf_token = secrets.token_urlsafe(32)

    def create(self, payload: bytes, filename: str, target_os: str, target_name: str) -> dict[str, Any]:
        if target_os not in {"portable", "windows", "linux"}:
            raise ValueError("INVALID_TARGET_OS")
        run_id = f"W7TP_GTF_{secrets.token_hex(16)}"
        job_dir = self.store.jobs_root / run_id
        job_dir.mkdir(mode=0o700)
        source = job_dir / "source.bin"
        source.write_bytes(payload)
        job = {"state": "QUEUED", "run_id": run_id, "progress": 0, "source_name": Path(filename).name, "source_bytes": len(payload), "packet_bytes": None, "reduction_ratio": None, "packet_sha256": None, "expected_sha256": None, "actual_sha256": None, "integrity": "UNVERIFIED", "authenticity": "UNVERIFIED", "verifier_decision": None, "reason_code": None, "packet_ready": False, "report_ready": False, "output_ready": False, "output_ref": target_name}
        self.store.save(job)
        self.executor.submit(self._run, job, source, target_os, target_name)
        return self.store.get(run_id) or job

    def _run(self, job: dict[str, Any], source: Path, target_os: str, target_name: str) -> None:
        run_id = job["run_id"]
        job_dir = source.parent
        packet, output_root, report = job_dir / "packet.json", job_dir / "output", job_dir / "report.json"
        output_root.mkdir()
        try:
            with self.lock:
                if target_name.casefold() in self.output_claims:
                    raise RuntimeError("CONCURRENT_OUTPUT_COLLISION")
                self.output_claims.add(target_name.casefold())
            core = GTConverter()
            for state, progress in (("PACKING", 15),):
                job.update(state=state, progress=progress); self.store.save(job)
            if run_id in self.cancelled: raise InterruptedError
            packed = core.pack(source, packet, run_id=run_id, target_relative_path=target_name, target_os=target_os)
            job.update(packet_bytes=packet.stat().st_size, reduction_ratio=round(source.stat().st_size / packet.stat().st_size, 6), packet_sha256=packed.packet_sha256, expected_sha256=packed.expected_sha256, packet_ready=True)
            job.update(state="RECONSTRUCTING", progress=40); self.store.save(job)
            if run_id in self.cancelled: raise InterruptedError
            rebuilt = core.reconstruct(packet, output_root)
            job.update(state="VERIFYING", progress=70); self.store.save(job)
            checked = core.verify(packet, rebuilt.output_path)
            job.update(actual_sha256=checked.actual_sha256, integrity=checked.integrity, authenticity=checked.authenticity, verifier_decision=checked.state, output_ready=checked.state == "PASS")
            job.update(state="SEALING", progress=90); self.store.save(job)
            core.seal(checked, report)
            job.update(state=checked.state, progress=100, report_ready=True, reason_code=checked.reason_code)
        except InterruptedError:
            job.update(state="CANCELLED", reason_code="CANCELLED_BY_USER", progress=100, output_ready=False)
        except ConverterFailure as exc:
            job.update(state=exc.state, reason_code=exc.reason_code, progress=100, output_ready=False)
        except Exception:
            job.update(state="ERROR", reason_code="INTERNAL_ERROR", progress=100, output_ready=False)
        finally:
            source.unlink(missing_ok=True)
            with self.lock: self.output_claims.discard(target_name.casefold())
            self.store.save(job)

    def cancel(self, run_id: str) -> dict[str, Any]:
        job = self.store.get(run_id)
        if not job: raise KeyError(run_id)
        self.cancelled.add(run_id)
        return job

    def close(self) -> None:
        self.executor.shutdown(wait=True, cancel_futures=False)


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address: tuple[str, int], service: ConverterService):
        if address[0] != "127.0.0.1": raise ValueError("NON_LOCAL_BIND")
        self.service = service
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server: LocalServer
    def log_message(self, format: str, *args: Any) -> None:
        return

    def _allowed(self, mutating: bool = False) -> bool:
        host = self.headers.get("Host", "")
        allowed_hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if host not in allowed_hosts: self._json(403, {"state": "BLOCK", "reason_code": "INVALID_HOST"}); return False
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://{item}" for item in allowed_hosts}:
            self._json(403, {"state": "BLOCK", "reason_code": "INVALID_ORIGIN"}); return False
        if mutating and self.headers.get("X-CSRF-Token") != self.server.service.csrf_token:
            self._json(403, {"state": "BLOCK", "reason_code": "INVALID_CSRF"}); return False
        return True

    def _json(self, status: int, value: dict[str, Any]) -> None:
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.send_header("X-Content-Type-Options", "nosniff"); self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"); self.end_headers(); self.wfile.write(body)

    def _run_id(self, path: str) -> tuple[str | None, str | None]:
        parts = path.strip("/").split("/")
        if len(parts) < 3 or parts[:2] != ["api", "jobs"] or not RUN_ID_RE.fullmatch(parts[2]): return None, None
        return parts[2], parts[3] if len(parts) == 4 else None

    def do_GET(self) -> None:
        if not self._allowed(): return
        path = urlparse(self.path).path
        if path == "/health": return self._json(200, {"state": "PASS"})
        if path == "/api/capabilities": return self._json(200, {"state": "PASS", "csrf_token": self.server.service.csrf_token, "network_allowed": False, "authenticity": "UNVERIFIED", "max_request_bytes": MAX_REQUEST_BYTES})
        if path in {"/", "/index.html", "/app.css", "/app.js"}:
            file = UI_ROOT / ("index.html" if path in {"/", "/index.html"} else path[1:])
            content = file.read_bytes(); kind = "text/html" if file.suffix == ".html" else "text/css" if file.suffix == ".css" else "text/javascript"
            self.send_response(200); self.send_header("Content-Type", f"{kind}; charset=utf-8"); self.send_header("Content-Length", str(len(content))); self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"); self.end_headers(); self.wfile.write(content); return
        run_id, artifact = self._run_id(path)
        if not run_id: return self._json(400, {"state": "BLOCK", "reason_code": "INVALID_RUN_ID"})
        job = self.server.service.store.get(run_id)
        if not job: return self._json(404, {"state": "HOLD", "reason_code": "JOB_NOT_FOUND"})
        if artifact is None: return self._json(200, job)
        mapping = {"packet": ("packet_ready", "packet.json", "application/json"), "report": ("report_ready", "report.json", "application/json"), "output": ("output_ready", f"output/{job.get('output_ref', 'reconstructed.bin')}", "application/octet-stream")}
        if artifact not in mapping: return self._json(403, {"state": "BLOCK", "reason_code": "ARBITRARY_DOWNLOAD_FORBIDDEN"})
        flag, relative, content_type = mapping[artifact]
        target = self.server.service.store.jobs_root / run_id / relative
        root = (self.server.service.store.jobs_root / run_id).resolve()
        if not job.get(flag) or target.is_symlink() or root not in target.resolve(strict=False).parents or not target.is_file(): return self._json(404, {"state": "HOLD", "reason_code": "ARTIFACT_NOT_READY"})
        body = target.read_bytes(); self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(body))); self.send_header("Content-Disposition", f'attachment; filename="{Path(relative).name}"'); self.end_headers(); self.wfile.write(body)

    def do_POST(self) -> None:
        if not self._allowed(mutating=True): return
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > MAX_REQUEST_BYTES: return self._json(413, {"state": "BLOCK", "reason_code": "REQUEST_TOO_LARGE"})
        body = self.rfile.read(length)
        if path == "/api/jobs":
            try:
                request = json.loads(body); payload = bytes.fromhex(request["source_hex"])
                if len(payload) > MAX_REQUEST_BYTES // 2: raise ValueError
                job = self.server.service.create(payload, request.get("filename", "source.bin"), request.get("target_os", "portable"), request.get("target_name", "reconstructed.bin"))
                return self._json(202, job)
            except (ValueError, KeyError, TypeError): return self._json(400, {"state": "HOLD", "reason_code": "INVALID_REQUEST"})
        run_id, artifact = self._run_id(path)
        if not run_id or artifact != "cancel": return self._json(400, {"state": "BLOCK", "reason_code": "INVALID_RUN_ID"})
        try: return self._json(202, self.server.service.cancel(run_id))
        except KeyError: return self._json(404, {"state": "HOLD", "reason_code": "JOB_NOT_FOUND"})


def create_server(host: str = "127.0.0.1", port: int = 8787, data_root: Path | None = None) -> LocalServer:
    root = data_root or Path.home() / ".w7tp_gt_converter_ui"
    return LocalServer((host, port), ConverterService(root))


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP生成式傳輸轉檔器本機服務")
    parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=8787); parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    try: server = create_server(args.host, args.port, args.data_root)
    except ValueError as exc: print(f"STATE=BLOCK\nREASON_CODE={exc}"); return 20
    print(f"STATE=PASS\nURL=http://127.0.0.1:{server.server_port}", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.shutdown(); server.service.close(); server.server_close()
    return 0


if __name__ == "__main__": raise SystemExit(main())
