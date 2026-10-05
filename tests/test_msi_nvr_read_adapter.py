import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import msi_nvr_read_adapter as mod


class FakeResponse:
    status_code = 200
    content = b"\xff\xd8test-jpeg\xff\xd9"


class MsiNvrReadAdapterTests(unittest.TestCase):
    def test_status_accepts_current_digest_challenge_as_reachable(self):
        fake = {
            "transport_available": True,
            "target": "192.168.50.34:554",
            "rtsp_status": 401,
            "auth_required": True,
            "auth_scheme": "digest",
        }
        with patch.object(mod, "probe", return_value=(fake, 3)):
            out = mod.status()
        self.assertEqual(out["state"], "PASS_NVR_READ_ADAPTER_REACHABLE")
        self.assertTrue(out["rtsp"]["auth_required"])
        self.assertFalse(out["mutation_performed"])
        self.assertFalse(out["rtsp"]["credentials_output"])

    def test_snapshot_requires_local_credential_binding(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                mod.NvrReadHold, "HOLD_NVR_CREDENTIAL_BINDING_REQUIRED"
            ):
                mod.snapshot(output=Path("/tmp/unused.jpg"), channel=0)

    def test_snapshot_hashes_jpeg_without_exposing_credentials(self):
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "cam01.jpg"
            env = {
                mod.USERNAME_ENV: "local-user",
                mod.PASSWORD_ENV: "local-secret",
                mod.HTTP_AUTH_ENV: "digest",
            }
            with patch.dict(os.environ, env, clear=True), patch.object(
                mod.requests, "get", return_value=FakeResponse()
            ):
                out = mod.snapshot(output=out_path, channel=0)
            self.assertEqual(out["state"], "PASS_NVR_SNAPSHOT_ACQUIRED")
            self.assertEqual(out["camera_ref"], "CAM01")
            self.assertEqual(out["channel_index"], 0)
            self.assertEqual(out_path.read_bytes(), FakeResponse.content)
            self.assertEqual(oct(out_path.stat().st_mode & 0o777), "0o600")
            self.assertFalse(out["credentials_output"])
            rendered = str(out)
            self.assertNotIn("local-user", rendered)
            self.assertNotIn("local-secret", rendered)

    def test_invalid_channel_fails_closed(self):
        with self.assertRaisesRegex(mod.NvrReadHold, "HOLD_NVR_CHANNEL_INVALID"):
            mod.snapshot(output=Path("/tmp/unused.jpg"), channel=99)


if __name__ == "__main__":
    unittest.main()
