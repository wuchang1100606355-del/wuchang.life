from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.total_field.w7tp_vertex_candidate_gateway import (
    CONFIG_PATH,
    VertexGatewayError,
    generate_with_gcloud_rest,
    load_gateway_config,
)


class _FakeHTTPResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self._body = body

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._body).encode("utf-8")


class W7TPVertexCandidateGatewayTest(unittest.TestCase):
    def test_config_is_closed_candidate_only_and_no_auto_call(self) -> None:
        config = load_gateway_config()
        self.assertEqual(config["provider"], "GOOGLE_VERTEX_AI")
        self.assertEqual(config["model"], "gemini-2.5-flash")
        self.assertEqual(config["cloud_output_authority"], "CANDIDATE_ONLY")
        self.assertEqual(config["formal_execution_authority"], "LOCAL_TOTAL_FIELD_ONLY")
        self.assertTrue(config["founder_authorization_per_request"])
        self.assertFalse(config["auto_cloud_call"])

    def test_config_rejects_cloud_auto_call(self) -> None:
        config = load_gateway_config()
        config["auto_cloud_call"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(VertexGatewayError):
                load_gateway_config(path)

    @patch("tools.total_field.w7tp_vertex_candidate_gateway.urllib.request.urlopen")
    @patch("tools.total_field.w7tp_vertex_candidate_gateway.subprocess.run")
    def test_gcloud_rest_returns_json_candidate_without_exposing_token(
        self,
        run_mock: object,
        urlopen_mock: object,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            credential_file = Path(directory) / "credential.json"
            credential_file.write_text("{}", encoding="utf-8")
            run_mock.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="fixture-access-token\n", stderr=""
            )
            urlopen_mock.return_value = _FakeHTTPResponse(
                {
                    "candidates": [
                        {
                            "finishReason": "STOP",
                            "content": {
                                "parts": [
                                    {"text": '{"candidate":'},
                                    {"text": '"fixture"}'},
                                ]
                            }
                        }
                    ]
                }
            )

            result = generate_with_gcloud_rest(
                project="fixture-project",
                location="global",
                model="gemini-2.5-flash",
                prompt="fixture prompt",
                system_instruction=["candidate only"],
                credential_file=credential_file,
            )

        self.assertEqual(result, '{"candidate":"fixture"}')
        request = urlopen_mock.call_args.args[0]
        self.assertTrue(request.full_url.startswith("https://aiplatform.googleapis.com/"))
        self.assertNotIn("fixture-access-token", result)

    def test_missing_credential_is_stable_hold(self) -> None:
        with self.assertRaises(VertexGatewayError) as caught:
            generate_with_gcloud_rest(
                project="fixture-project",
                location="global",
                model="gemini-2.5-flash",
                prompt="fixture prompt",
                system_instruction=["candidate only"],
                credential_file=CONFIG_PATH.with_name("missing-credential.json"),
            )
        self.assertEqual(str(caught.exception), "VERTEX_REST_CREDENTIAL_FILE_MISSING")


if __name__ == "__main__":
    unittest.main()
