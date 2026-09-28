#!/usr/bin/env python3

import os
import unittest
from unittest.mock import patch

from core.resource_arbitration import probe_ollama_cloud


class OllamaCloudResourceRegistrationTest(unittest.TestCase):
    def test_unconfigured_cloud_model_is_registered_but_held(self):
        with patch.dict(os.environ, {"TAIJI_OLLAMA_CLOUD_MODEL": ""}, clear=False):
            item = probe_ollama_cloud("http://127.0.0.1:9")
        self.assertEqual(item["RESOURCE_ID"], "OLLAMA_CLOUD")
        self.assertEqual(item["CURRENT_STATE"], "HOLD_PROVIDER_MODEL_UNCONFIGURED")
        self.assertEqual(item["AUTHORITY_CLASS"], "CANDIDATE_ONLY_NOT_D8")
        self.assertFalse(item["MODEL_REF_CONFIGURED"])
        self.assertFalse(item["CLOUD_INFERENCE_IS_D6"])
        self.assertFalse(item["DIRECT_EXTERNAL_EFFECT"])

    def test_configured_but_unreachable_cloud_model_stays_held(self):
        with patch.dict(
            os.environ,
            {"TAIJI_OLLAMA_CLOUD_MODEL": "example-cloud-model"},
            clear=False,
        ):
            item = probe_ollama_cloud("http://127.0.0.1:9")
        self.assertEqual(item["CURRENT_STATE"], "HOLD_CLOUD_MODEL_NOT_PRESENT")
        self.assertTrue(item["MODEL_REF_CONFIGURED"])
        self.assertEqual(item["CONTEXT_BINDING_STATE"], "HOLD_PROVIDER_ADAPTER_NOT_BOUND")


if __name__ == "__main__":
    unittest.main()
