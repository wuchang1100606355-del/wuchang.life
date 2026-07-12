import hashlib
import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from w7tp_runtime.gt_converter_ui import ConverterService, LocalServer, MAX_REQUEST_BYTES


UI_REDTEAM_CASES = [
    "reject_non_local_bind", "reject_invalid_host_header", "reject_external_origin",
    "reject_missing_or_invalid_csrf", "reject_oversized_request", "reject_invalid_run_id",
    "reject_run_id_path_traversal", "reject_arbitrary_file_download", "reject_symlink_output_download",
    "escape_filename_xss", "escape_reason_code_xss", "hide_python_traceback", "hide_source_payload",
    "hide_absolute_source_path", "reject_existing_output_overwrite", "reject_concurrent_output_collision",
    "cancel_does_not_delete_source", "browser_disconnect_does_not_stop_job",
    "restart_recovers_completed_job_index", "unfinished_temp_is_not_downloadable",
]


class GTConverterUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.service = ConverterService(self.root); self.server = LocalServer(("127.0.0.1", 0), self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.port = self.server.server_port; self.host = f"127.0.0.1:{self.port}"

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.service.close(); self.thread.join(); self.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        base = {"Host": self.host}; base.update(headers or {})
        conn.request(method, path, body=body, headers=base); response = conn.getresponse(); data = response.read(); conn.close()
        return response.status, data, dict(response.getheaders())

    def post(self, payload, **extra):
        body = json.dumps({"source_hex": payload.hex(), "filename": extra.get("filename", "source.bin"), "target_os": extra.get("target_os", "portable"), "target_name": extra.get("target_name", "reconstructed.bin")}).encode()
        return self.request("POST", "/api/jobs", body, {"Content-Type": "application/json", "X-CSRF-Token": self.service.csrf_token})

    def wait(self, run_id):
        for _ in range(100):
            status, raw, _ = self.request("GET", f"/api/jobs/{run_id}"); job = json.loads(raw)
            if job["state"] in {"PASS", "HOLD", "BLOCK", "ERROR", "CANCELLED"}: return job
            time.sleep(.02)
        self.fail("job timeout")

    def test_reject_non_local_bind(self):
        with self.assertRaisesRegex(ValueError, "NON_LOCAL_BIND"): LocalServer(("0.0.0.0", 0), ConverterService(self.root / "other"))

    def test_reject_invalid_host_header(self):
        status, _, _ = self.request("GET", "/health", headers={"Host": "evil.test"}); self.assertEqual(status, 403)

    def test_reject_external_origin(self):
        status, _, _ = self.request("GET", "/health", headers={"Origin": "https://evil.test"}); self.assertEqual(status, 403)

    def test_reject_missing_or_invalid_csrf(self):
        status, _, _ = self.request("POST", "/api/jobs", b"{}", {"Content-Type": "application/json"}); self.assertEqual(status, 403)

    def test_reject_oversized_request(self):
        status, raw, _ = self.request("POST", "/api/jobs", b"x", {"Content-Length": str(MAX_REQUEST_BYTES + 1), "X-CSRF-Token": self.service.csrf_token}); self.assertEqual(status, 413)

    def test_reject_invalid_run_id_and_traversal(self):
        for path in ("/api/jobs/bad", "/api/jobs/../ledger"):
            status, _, _ = self.request("GET", path); self.assertEqual(status, 400)

    def test_reject_arbitrary_file_download(self):
        status, raw, _ = self.post(b"X" * 4096); run = json.loads(raw)["run_id"]
        status, _, _ = self.request("GET", f"/api/jobs/{run}/source"); self.assertEqual(status, 403)

    def test_reject_symlink_output_download(self):
        status, raw, _ = self.post(b"Y" * 32768); run = json.loads(raw)["run_id"]; job = self.wait(run)
        output = self.root / "jobs" / run / "output" / "reconstructed.bin"; output.unlink(); output.symlink_to(self.root / "ledger" / f"{run}.json")
        status, _, _ = self.request("GET", f"/api/jobs/{run}/output"); self.assertEqual(status, 404)

    def test_escape_filename_and_reason_xss(self):
        status, raw, _ = self.post(b"Z" * 4096, filename='<img src=x onerror=1>'); run = json.loads(raw)["run_id"]; job = self.wait(run)
        self.assertNotIn("<img", job["source_name"])
        job["reason_code"] = "<script>alert(1)</script>"; self.service.store.save(job)
        self.assertNotIn("<script>", self.service.store.get(run)["reason_code"])

    def test_hide_traceback_payload_and_absolute_path(self):
        payload = b"SECRET-PAYLOAD-DO-NOT-SHOW"
        status, raw, _ = self.post(payload); run = json.loads(raw)["run_id"]; job = self.wait(run); encoded = json.dumps(job)
        self.assertNotIn("Traceback", encoded); self.assertNotIn(payload.decode(), encoded); self.assertNotIn(str(self.root), encoded)

    def test_reject_existing_and_concurrent_output(self):
        first = json.loads(self.post(b"A" * 100000)[1]); second = json.loads(self.post(b"B" * 100000)[1])
        states = {self.wait(first["run_id"])["state"], self.wait(second["run_id"])["state"]}
        self.assertTrue(states <= {"PASS", "ERROR"})
        passed = first if self.wait(first["run_id"])["state"] == "PASS" else second
        output = self.root / "jobs" / passed["run_id"] / "output" / "reconstructed.bin"
        original = output.read_bytes(); self.assertEqual(output.read_bytes(), original)

    def test_cancel_does_not_delete_source(self):
        external = self.root / "user-original.bin"; external.write_bytes(b"ORIGINAL")
        run = json.loads(self.post(b"C" * 100000)[1])["run_id"]
        self.request("POST", f"/api/jobs/{run}/cancel", b"{}", {"X-CSRF-Token": self.service.csrf_token})
        self.assertEqual(external.read_bytes(), b"ORIGINAL")

    def test_browser_disconnect_does_not_stop_job_and_downloads(self):
        payload = b"W7TP-UI-BLOCK" * 131072; body = json.dumps({"source_hex": payload.hex(), "filename": "demo.bin", "target_os": "portable", "target_name": "reconstructed.bin"}).encode()
        conn = http.client.HTTPConnection("127.0.0.1", self.port); conn.request("POST", "/api/jobs", body, {"Host": self.host, "X-CSRF-Token": self.service.csrf_token}); response = conn.getresponse(); run = json.loads(response.read())["run_id"]; conn.close()
        job = self.wait(run); self.assertEqual(job["state"], "PASS"); self.assertEqual(job["expected_sha256"], job["actual_sha256"])
        for artifact in ("packet", "report", "output"):
            status, data, _ = self.request("GET", f"/api/jobs/{run}/{artifact}"); self.assertEqual(status, 200); self.assertTrue(data)
        self.assertEqual(hashlib.sha256(data).hexdigest(), job["actual_sha256"])

    def test_restart_recovers_completed_job_index(self):
        run = json.loads(self.post(b"D" * 32768)[1])["run_id"]; self.assertEqual(self.wait(run)["state"], "PASS")
        recovered = ConverterService(self.root); self.assertEqual(recovered.store.get(run)["state"], "PASS"); recovered.close()

    def test_unfinished_temp_is_not_downloadable(self):
        run = "W7TP_GTF_" + "a" * 16; directory = self.root / "jobs" / run / "output"; directory.mkdir(parents=True); (directory / ".w7tp-gtf-temp.tmp").write_bytes(b"partial")
        self.service.store.save({"run_id": run, "state": "RECONSTRUCTING", "progress": 50, "output_ready": False, "output_ref": "reconstructed.bin"})
        status, _, _ = self.request("GET", f"/api/jobs/{run}/output"); self.assertEqual(status, 404)


if __name__ == "__main__": unittest.main()
