import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "property_rtsp_probe.py"
SPEC = importlib.util.spec_from_file_location("property_rtsp_probe", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PropertyRtspProbeTests(unittest.TestCase):
    def test_rejects_credentials_in_url(self):
        with self.assertRaisesRegex(ValueError, "Do not place credentials"):
            MODULE.parse_target("rtsp://operator:secret@example.test/live")

    def test_per_request_dns_override_is_added_to_curl_config(self):
        config = MODULE.curl_config(
            MODULE.parse_target("rtsp://nvr.example.test:8554/live"),
            "DESCRIBE",
            2.0,
            None,
            None,
            "192.0.2.34",
        )
        self.assertIn('resolve = "nvr.example.test:8554:192.0.2.34"', config)

    def test_dns_override_requires_an_ip_address(self):
        with self.assertRaises(ValueError):
            MODULE.curl_config(
                MODULE.parse_target("rtsp://nvr.example.test/live"),
                "DESCRIBE",
                2.0,
                None,
                None,
                "not-an-ip",
            )

    def test_final_response_uses_last_authentication_round(self):
        raw = (
            'RTSP/1.0 401 Unauthorized\r\nWWW-Authenticate: Digest realm="NVR"\r\n\r\n'
            "RTSP/1.0 200 OK\r\nContent-Type: application/sdp\r\n\r\n"
            "v=0\r\nm=video 0 RTP/AVP 96\r\na=rtpmap:96 H264/90000\r\n"
        )
        status, headers, body = MODULE.final_rtsp_response(raw)
        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/sdp")
        self.assertIn("m=video", body)

    def test_sdp_summary_exposes_metadata_only(self):
        summary = MODULE.sdp_summary(
            "v=0\r\nm=video 0 RTP/AVP 96\r\na=rtpmap:96 H265/90000\r\n"
            "m=audio 0 RTP/AVP 0\r\na=rtpmap:0 PCMU/8000\r\n"
        )
        self.assertEqual(summary["video_tracks"], 1)
        self.assertEqual(summary["audio_tracks"], 1)
        self.assertEqual(summary["codecs"], ["H265", "PCMU"])

    @mock.patch.object(MODULE.shutil, "which", return_value="/usr/bin/curl")
    @mock.patch.object(MODULE.subprocess, "run")
    def test_probe_reports_auth_required_without_leaking_challenge(self, run, _which):
        run.return_value = mock.Mock(
            stdout=(
                'RTSP/1.0 401 Unauthorized\r\n'
                'WWW-Authenticate: Digest realm="NVR_RTSP", nonce="private"\r\n\r\n'
            ),
            returncode=0,
        )
        result, exit_code = MODULE.probe(
            MODULE.parse_target("rtsp://192.0.2.1:554/"),
            "DESCRIBE",
            2.0,
            None,
            None,
        )
        self.assertEqual(exit_code, 3)
        self.assertEqual(result["decision"], "rtsp_authentication_required")
        self.assertEqual(result["auth_scheme"], "digest")
        self.assertNotIn("private", str(result))
        self.assertFalse(result["credentials_output"])

    def test_credentials_are_not_added_to_process_arguments(self):
        config = MODULE.curl_config(
            MODULE.parse_target("rtsp://192.0.2.1/live"),
            "DESCRIBE",
            2.0,
            "operator",
            "secret",
        )
        self.assertIn('user = "operator:secret"', config)
        with mock.patch.object(MODULE.shutil, "which", return_value="/usr/bin/curl"), mock.patch.object(
            MODULE.subprocess, "run"
        ) as run:
            run.return_value = mock.Mock(stdout="", returncode=28)
            MODULE.probe(
                MODULE.parse_target("rtsp://192.0.2.1/live"),
                "DESCRIBE",
                2.0,
                "operator",
                "secret",
            )
        self.assertEqual(run.call_args.args[0], ["curl", "--config", "-"])
        self.assertNotIn("secret", str(run.call_args.args[0]))

    @mock.patch.object(MODULE.shutil, "which", return_value="/usr/bin/curl")
    @mock.patch.object(MODULE.subprocess, "run")
    def test_probe_distinguishes_transport_failure(self, run, _which):
        run.return_value = mock.Mock(stdout="", returncode=7)
        result, exit_code = MODULE.probe(
            MODULE.parse_target("rtsp://192.0.2.1:554/"),
            "DESCRIBE",
            2.0,
            None,
            None,
        )
        self.assertEqual(exit_code, 4)
        self.assertEqual(result["decision"], "rtsp_transport_unavailable")
        self.assertFalse(result["transport_available"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
