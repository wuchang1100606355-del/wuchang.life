"""
title: Taiji Metric Gateway Assembly
author: Wuchang Taiji
version: 1.0.0
description: Metric Tensor Language AI gateway tool. Routes metric maps to Claw Safe, POS Voice Tool, and Device Resilience Adapter.
"""

import json
import urllib.request
import urllib.error
from typing import Optional


class Tools:
    def __init__(self):
        self.claw_url = "http://taiji_claw_safe:9004"
        self.pos_url = "http://taiji_pos_google_voice_tool:9011"
        self.device_url = "http://taiji_device_resilience_adapter:9012"

    def _get(self, url: str) -> str:
        try:
            with urllib.request.urlopen(url, timeout=20) as res:
                return res.read().decode("utf-8")
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False, indent=2)

    def _post(self, url: str, payload: dict) -> str:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                return res.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return json.dumps({"ok": False, "http_status": e.code, "error": body}, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False, indent=2)

    def gateway_health(self) -> str:
        """
        Check Claw Safe, POS Voice Tool, and Device Resilience Adapter.
        """
        return json.dumps(
            {
                "claw_safe": json.loads(self._get(self.claw_url + "/healthz")),
                "pos_voice_tool": json.loads(self._get(self.pos_url + "/healthz")),
                "device_resilience_adapter": json.loads(self._get(self.device_url + "/healthz")),
            },
            ensure_ascii=False,
            indent=2,
        )

    def metric_map(self, text: str) -> str:
        """
        Map text into MTL-AI layers and task closure categories.
        """
        t = (text or "").lower()
        layers = []

        if any(k in t for k in ["data", "privacy", "sovereign", "blind", "metric", "cloud", "archive", "hash"]):
            layers.append("D1_SOVEREIGN_BLIND_METRIC")

        if any(k in t for k in ["execute", "docker", "tailscale", "google", "odoo", "permission", "delete", "shell", "ssh", "sudo"]):
            layers.append("D2_UNFENCED_LLM_GUARDED_EXECUTION")

        if any(k in t for k in ["pos", "voice", "merchant", "ledger", "fund", "public interest"]):
            layers.append("D3_POS_ODOO_GOOGLE_PUBLIC_INTEREST_GOVERNANCE")

        if any(k in t for k in ["hardware", "mesh", "gravity", "patch", "tensor", "curvature", "chip"]):
            layers.append("H4_METRIC_TENSOR_GRAVITY_PATCH_HARDWARE_MESH")

        if any(k in t for k in ["carbon", "co2e", "esg", "emission", "energy"]):
            layers.append("C5_CARBON_METRIC_LEDGER")

        if any(k in t for k in ["cloud muscle", "drive", "workspace", "cloud run", "apps script"]):
            layers.append("G6_GATEWAY_CLOUD_MUSCLE")

        if not layers:
            layers.append("Tμν_METRIC_TENSOR_LANGUAGE_REASONING_CORE")

        return json.dumps(
            {
                "ok": True,
                "input": text,
                "root_formula": "MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ",
                "mapped_layers": layers,
                "closed_output_set": [
                    "READONLY",
                    "LOW_RISK_AUDITED",
                    "CONFIRM_REQUIRED",
                    "BLOCKED_WITH_SAFE_ALTERNATIVE"
                ],
                "rule": "Imagination may be unfenced. Execution must be guarded. Cloud is muscle, not brain."
            },
            ensure_ascii=False,
            indent=2,
        )

    def claw_classify(self, task_id: str, action: str, resource_hint: Optional[str] = "", payload_json: Optional[str] = "{}") -> str:
        """
        Send task envelope to Claw Safe for classification.
        """
        try:
            payload = json.loads(payload_json or "{}")
        except Exception:
            payload = {"raw_payload_text": payload_json}

        return self._post(
            self.claw_url + "/v1/tasks/classify",
            {
                "task_id": task_id,
                "action": action,
                "resource_hint": resource_hint,
                "payload": payload,
                "actor": "mtl_ai_gateway",
                "dry_run": True
            },
        )

    def pos_text_intent(self, session_id: str, device_id: str, transcript: str, locale: Optional[str] = "zh-TW", execute: Optional[bool] = False) -> str:
        """
        Send text intent to POS Voice Tool. Audio upload is not supported.
        """
        return self._post(
            self.pos_url + "/v1/pos/voice-intent",
            {
                "session_id": session_id,
                "device_id": device_id,
                "transcript": transcript,
                "locale": locale,
                "execute": bool(execute),
            },
        )

    def device_file_task(self, task_id: str, content: str, source: Optional[str] = "mtl_ai_gateway", metadata_json: Optional[str] = "{}") -> str:
        """
        Create a safe device resilience file task.
        """
        try:
            metadata = json.loads(metadata_json or "{}")
        except Exception:
            metadata = {"raw_metadata_text": metadata_json}

        return self._post(
            self.device_url + "/v1/file-task",
            {
                "task_id": task_id,
                "content": content,
                "source": source,
                "metadata": metadata,
            },
        )
