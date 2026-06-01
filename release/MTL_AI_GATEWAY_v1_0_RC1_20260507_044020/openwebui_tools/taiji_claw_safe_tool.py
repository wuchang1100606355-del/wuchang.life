"""
title: Taiji Claw Safe Bridge
author: Wuchang Taiji
version: 0.1.0
description: Open WebUI cockpit bridge to Taiji Claw Safe broker. Sends task envelopes only.
"""

import json
import urllib.request
import urllib.error
from typing import Optional


class Tools:
    def __init__(self):
        self.base_url = "http://taiji_claw_safe:9004"

    def _post(self, path: str, payload: dict) -> str:
        url = self.base_url + path
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                body = res.read().decode("utf-8")
                return body
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return json.dumps(
                {
                    "ok": False,
                    "http_status": e.code,
                    "error": body,
                },
                ensure_ascii=False,
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {
                    "ok": False,
                    "error": str(e),
                    "hint": "Check Docker network: open-webui and taiji_claw_safe must share taiji-ai network.",
                },
                ensure_ascii=False,
                indent=2,
            )

    def _get(self, path: str) -> str:
        url = self.base_url + path
        try:
            with urllib.request.urlopen(url, timeout=20) as res:
                return res.read().decode("utf-8")
        except Exception as e:
            return json.dumps(
                {
                    "ok": False,
                    "error": str(e),
                },
                ensure_ascii=False,
                indent=2,
            )

    def claw_health(self) -> str:
        """
        Check Taiji Claw Safe broker health.
        """
        return self._get("/healthz")

    def claw_classify(
        self,
        task_id: str,
        action: str,
        resource_hint: Optional[str] = "",
        payload_json: Optional[str] = "{}",
    ) -> str:
        """
        Classify a task envelope before execution.
        """
        try:
            payload = json.loads(payload_json or "{}")
        except Exception:
            payload = {"raw_payload_text": payload_json}

        return self._post(
            "/v1/tasks/classify",
            {
                "task_id": task_id,
                "action": action,
                "resource_hint": resource_hint,
                "payload": payload,
                "actor": "openwebui_local_ai",
                "dry_run": True,
            },
        )

    def claw_dry_run(
        self,
        task_id: str,
        action: str,
        resource_hint: Optional[str] = "",
        payload_json: Optional[str] = "{}",
    ) -> str:
        """
        Dry-run a task envelope. This never performs real cloud/Odoo execution.
        """
        try:
            payload = json.loads(payload_json or "{}")
        except Exception:
            payload = {"raw_payload_text": payload_json}

        return self._post(
            "/v1/tasks/dry-run",
            {
                "task_id": task_id,
                "action": action,
                "resource_hint": resource_hint,
                "payload": payload,
                "actor": "openwebui_local_ai",
                "dry_run": True,
            },
        )

    def claw_execute_queue_only(
        self,
        task_id: str,
        action: str,
        resource_hint: Optional[str] = "",
        payload_json: Optional[str] = "{}",
        confirmation_token: Optional[str] = "",
    ) -> str:
        """
        Queue an approved task through Claw Safe.
        L2 requires confirmation_token=CONFIRM_L2.
        L3 is always blocked by Claw Safe.
        MVP queues only; it does not perform real Google/Odoo execution.
        """
        try:
            payload = json.loads(payload_json or "{}")
        except Exception:
            payload = {"raw_payload_text": payload_json}

        return self._post(
            "/v1/tasks/execute",
            {
                "task_id": task_id,
                "action": action,
                "resource_hint": resource_hint,
                "payload": payload,
                "confirmation_token": confirmation_token or None,
                "actor": "openwebui_local_ai",
                "dry_run": False,
            },
        )

    def claw_audit_latest(self) -> str:
        """
        List latest Claw Safe audit events.
        """
        return self._get("/v1/audit")
