#!/usr/bin/env python3
"""Verify the medical-care demo with a real Chromium session.

The verifier is read-only: it drives the public synthetic demo, records only
product-state assertions, and never submits forms or reads browser credentials.
It intentionally uses the Chrome DevTools Protocol over a local ephemeral port
so the repository does not gain a Selenium or Playwright dependency.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_URL = "https://wuchang.life/medical_care_demo/"


class VerificationError(RuntimeError):
    """Raised when Chromium or the local CDP channel cannot be verified."""


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _http_json(url: str, timeout: float = 1.0) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class CDPConnection:
    def __init__(self, websocket_url: str) -> None:
        parsed = urlparse(websocket_url)
        if parsed.scheme != "ws" or not parsed.hostname or not parsed.port:
            raise VerificationError("unsupported CDP websocket URL")
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout=10)
        self.socket.settimeout(10)
        self._next_id = 1
        self.events: list[dict[str, Any]] = []

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {parsed.path} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Origin: http://{parsed.hostname}:{parsed.port}\r\n\r\n"
        )
        self.socket.sendall(request.encode("ascii"))
        response = self._read_http_headers()
        status_line = response.split(b"\r\n", 1)[0]
        if b" 101 " not in status_line:
            raise VerificationError("Chromium rejected the local CDP websocket")
        expected = base64.b64encode(
            hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
            ).digest()
        )
        if b"sec-websocket-accept: " + expected.lower() not in response.lower():
            raise VerificationError("invalid CDP websocket handshake")

    def _read_http_headers(self) -> bytes:
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = self.socket.recv(4096)
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > 65536:
                raise VerificationError("oversized CDP handshake")
        return bytes(data)

    def _send_frame(self, payload: bytes, opcode: int = 1) -> None:
        mask = secrets.token_bytes(4)
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length <= 0xFFFF:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.socket.sendall(bytes(header) + mask + masked)

    def _read_exact(self, length: int) -> bytes:
        data = bytearray()
        while len(data) < length:
            chunk = self.socket.recv(length - len(data))
            if not chunk:
                raise VerificationError("CDP websocket closed unexpectedly")
            data.extend(chunk)
        return bytes(data)

    def _receive_message(self) -> dict[str, Any]:
        while True:
            first, second = self._read_exact(2)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            masked = bool(second & 0x80)
            mask = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(
                    value ^ mask[index % 4] for index, value in enumerate(payload)
                )
            if opcode == 8:
                raise VerificationError("CDP websocket closed")
            if opcode == 9:
                self._send_frame(payload, opcode=10)
                continue
            if opcode != 1:
                continue
            return json.loads(payload.decode("utf-8"))

    def command(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        command_id = self._next_id
        self._next_id += 1
        payload: dict[str, Any] = {"id": command_id, "method": method}
        if params:
            payload["params"] = params
        self._send_frame(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        while True:
            message = self._receive_message()
            if message.get("id") == command_id:
                if "error" in message:
                    raise VerificationError(
                        f"CDP {method} failed: {message['error'].get('message', 'unknown error')}"
                    )
                return dict(message.get("result", {}))
            if "method" in message:
                self.events.append(message)

    def close(self) -> None:
        try:
            self.socket.close()
        except OSError:
            pass


class ChromiumSession:
    def __init__(self, chromium: str | None = None) -> None:
        self.chromium = chromium or shutil.which("chromium") or shutil.which("chromium-browser")
        if not self.chromium:
            raise VerificationError("Chromium was not found")
        self._profile = tempfile.TemporaryDirectory(prefix="w7tp-medical-browser-")
        self.port = _free_local_port()
        self.process = subprocess.Popen(
            [
                self.chromium,
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-background-networking",
                "--disable-component-update",
                "--disable-sync",
                "--metrics-recording-only",
                "--no-first-run",
                "--no-default-browser-check",
                "--remote-allow-origins=*",
                "--remote-debugging-address=127.0.0.1",
                f"--remote-debugging-port={self.port}",
                f"--user-data-dir={self._profile.name}",
                "about:blank",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        target = self._wait_for_target()
        self.connection = CDPConnection(str(target["webSocketDebuggerUrl"]))

    def _wait_for_target(self) -> dict[str, Any]:
        deadline = time.monotonic() + 15
        endpoint = f"http://127.0.0.1:{self.port}/json/list"
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise VerificationError("Chromium exited before CDP became ready")
            try:
                targets = _http_json(endpoint)
                for target in targets:
                    if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                        return dict(target)
            except (OSError, ValueError):
                pass
            time.sleep(0.1)
        raise VerificationError("Chromium CDP startup timed out")

    def close(self) -> None:
        if hasattr(self, "connection"):
            self.connection.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self._profile.cleanup()


DESKTOP_EXPRESSION = r"""
(async () => {
  const checks = {};
  const details = {};
  const record = (name, value, detail = null) => {
    checks[name] = Boolean(value);
    if (detail !== null) details[name] = detail;
  };
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  await wait(300);

  record("document_ready", document.readyState === "complete", document.readyState);
  record("page_title", document.title.includes("醫病日常照護"), document.title);
  record("single_h1", document.querySelectorAll("h1").length === 1);
  record("main_landmark", Boolean(document.querySelector("main#main")));
  record("skip_link", document.querySelector("a.skip")?.getAttribute("href") === "#main");
  const bodyText = document.body.innerText;
  record(
    "device_only_llm_boundary",
    bodyText.includes("LLM 僅限使用者設備") &&
      bodyText.includes("taiji01 與合作伺服器不執行 LLM") &&
      bodyText.includes("目前不載入模型")
  );
  const redteam = document.querySelector("#care-redteam-monitor");
  const initialRedteamCycle = Number(
    document.querySelector("#care-redteam-cycle")?.textContent.match(/cycle (\d+)/)?.[1] || 0
  );
  record(
    "always_on_redteam_visible",
    redteam?.dataset.state === "MONITORING_CLEAR" &&
      redteam.innerText.includes("不使用伺服器 LLM")
  );

  const tabs = [...document.querySelectorAll("[role='tab'][data-role]")];
  const selectedTabs = () => tabs.filter((tab) => tab.getAttribute("aria-selected") === "true");
  record("three_human_role_tabs", tabs.length === 3);
  record(
    "initial_patient_view",
    selectedTabs().length === 1 && selectedTabs()[0]?.dataset.role === "patient"
  );
  const patient = document.querySelector("#role-patient");
  patient.focus();
  patient.dispatchEvent(new KeyboardEvent("keydown", {key: "ArrowRight", bubbles: true}));
  await wait(50);
  record(
    "keyboard_tab_navigation",
    document.activeElement?.id === "role-nurse" && selectedTabs()[0]?.dataset.role === "nurse"
  );
  document.querySelector("#role-doctor").click();
  record(
    "role_panel_contract",
    selectedTabs()[0]?.dataset.role === "doctor" &&
      document.querySelector("#role-panel")?.getAttribute("aria-labelledby") === "role-doctor" &&
      document.querySelector("#role-title")?.textContent.includes("醫師")
  );

  document.querySelector("[data-event='signal']").click();
  await wait(100);
  const pressedEvents = [...document.querySelectorAll(".event-button[aria-pressed='true']")];
  const contentHash = document.querySelector("#content-hash")?.textContent.trim() || "";
  record(
    "event_selection_contract",
    pressedEvents.length === 1 && pressedEvents[0]?.dataset.event === "signal"
  );
  record("browser_sha256", /^[0-9a-f]{64}$/.test(contentHash), contentHash);
  record(
    "candidate_authority_boundary",
    document.querySelector("#packet-d8")?.textContent.includes("HOLD") &&
      document.querySelector("#packet-d6")?.textContent.includes("L3")
  );

  const eventRedteamCycle = Number(
    document.querySelector("#care-redteam-cycle")?.textContent.match(/cycle (\d+)/)?.[1] || 0
  );
  record(
    "redteam_rechecks_role_and_event_transitions",
    eventRedteamCycle >= initialRedteamCycle + 3 &&
      document.querySelector("#care-redteam-cycle")?.textContent.includes("EVENT_TRANSITION") &&
      document.querySelector("#redteam-message")?.textContent.includes("候選立即隔離")
  );
  const offline = document.querySelector("#simulate-offline");
  const restore = document.querySelector("#restore-link");
  offline.click();
  await wait(25);
  record(
    "offline_queue_boundary",
    offline.disabled && !restore.disabled &&
      document.querySelector("#packet-state")?.textContent.includes("NO D8") &&
      document.querySelector("#packet-d2")?.textContent === "EDGE_OFFLINE_QUEUE"
  );
  record(
    "redteam_rechecks_offline_transition",
    document.querySelector("#care-redteam-cycle")?.textContent.includes("OFFLINE_QUEUE") &&
      redteam?.dataset.state === "MONITORING_CLEAR"
  );
  restore.click();
  await wait(25);
  record(
    "revalidation_boundary",
    !offline.disabled && restore.disabled &&
      document.querySelector("#packet-state")?.textContent.includes("HUMAN REVIEW") &&
      document.querySelector("#revalidate-label")?.textContent.includes("重驗")
  );
  record(
    "redteam_rechecks_relink_transition",
    document.querySelector("#care-redteam-cycle")?.textContent.includes("RELINK_REVALIDATION") &&
      redteam?.dataset.state === "MONITORING_CLEAR"
  );
  record(
    "live_announcement",
    document.querySelector("#demo-announcement")?.getAttribute("aria-live") === "polite" &&
      document.querySelector("#demo-announcement")?.textContent.length > 8
  );

  const visibleInteractive = [...document.querySelectorAll("a[href], button, [tabindex]")]
    .filter((node) => {
      const style = getComputedStyle(node);
      const box = node.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && box.width > 0 && box.height > 0;
    });
  const unnamed = visibleInteractive.filter((node) => {
    const name = node.getAttribute("aria-label") || node.textContent.trim() || node.getAttribute("title");
    return !name;
  });
  const undersized = visibleInteractive.filter((node) => {
    const box = node.getBoundingClientRect();
    return box.width < 24 || box.height < 24;
  });
  record("interactive_names", unnamed.length === 0, unnamed.length);
  record("minimum_target_size", undersized.length === 0, undersized.length);
  record(
    "desktop_no_horizontal_overflow",
    document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
    {scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth}
  );

  const resourceOrigins = performance.getEntriesByType("resource")
    .map((entry) => new URL(entry.name, location.href).origin);
  record(
    "same_origin_runtime_resources",
    resourceOrigins.every((origin) => origin === location.origin),
    [...new Set(resourceOrigins)]
  );
  const navigation = performance.getEntriesByType("navigation")[0];
  record("https_document", location.protocol === "https:", location.protocol);
  record("document_http_200", navigation?.responseStatus === 200, navigation?.responseStatus || null);

  return {checks, details};
})()
"""


MOBILE_EXPRESSION = r"""
(() => {
  const clientWidth = document.documentElement.clientWidth;
  const tabs = [...document.querySelectorAll("[role='tab'][data-role]")];
  const tabList = document.querySelector(".role-tabs")?.getBoundingClientRect();
  const interactive = [...document.querySelectorAll(".role-tabs button, .event-button, .demo-button")]
    .map((node) => node.getBoundingClientRect());
  return {
    checks: {
      mobile_no_horizontal_overflow: document.documentElement.scrollWidth <= clientWidth + 1,
      mobile_role_tabs_fit: Boolean(tabList) && tabList.left >= -1 && tabList.right <= clientWidth + 1,
      mobile_role_tabs_usable: tabs.length === 3 && tabs.every((tab) => tab.getBoundingClientRect().height >= 60),
      mobile_controls_target_size: interactive.every((box) => box.width >= 24 && box.height >= 24),
      reduced_motion_exposed: matchMedia("(prefers-reduced-motion: reduce)").matches
    },
    details: {
      viewport: {width: innerWidth, height: innerHeight},
      layout: {scrollWidth: document.documentElement.scrollWidth, clientWidth}
    }
  };
})()
"""


def _evaluate(connection: CDPConnection, expression: str) -> dict[str, Any]:
    result = connection.command(
        "Runtime.evaluate",
        {
            "expression": expression,
            "awaitPromise": True,
            "returnByValue": True,
            "userGesture": True,
        },
    )
    remote = result.get("result", {})
    if remote.get("subtype") == "error" or "exceptionDetails" in result:
        exception = result.get("exceptionDetails", {})
        description = str(
            remote.get("description")
            or exception.get("exception", {}).get("description")
            or exception.get("text")
            or "unknown JavaScript error"
        ).splitlines()[0][:240]
    value = remote.get("value")
    if not isinstance(value, dict):
        raise VerificationError("browser product expression returned no result")
    return value


def _wait_for_ready(connection: CDPConnection, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = connection.command(
            "Runtime.evaluate",
            {"expression": "document.readyState", "returnByValue": True},
        )
        if result.get("result", {}).get("value") == "complete":
            return
        time.sleep(0.1)
    raise VerificationError("page load timed out")


def _ax_checks(connection: CDPConnection) -> dict[str, bool]:
    tree = connection.command("Accessibility.getFullAXTree").get("nodes", [])
    visible = [node for node in tree if not node.get("ignored")]
    roles = [node.get("role", {}).get("value") for node in visible]
    tabs = [node for node in visible if node.get("role", {}).get("value") == "tab"]
    return {
        "ax_main_landmark": "main" in roles,
        "ax_navigation_landmark": "navigation" in roles,
        "ax_tablist": "tablist" in roles,
        "ax_named_human_tabs": len(tabs) == 3
        and all(str(node.get("name", {}).get("value", "")).strip() for node in tabs),
    }


def verify(url: str, chromium: str | None = None) -> dict[str, Any]:
    session = ChromiumSession(chromium)
    connection = session.connection
    try:
        for domain in ("Page", "Runtime", "Log", "Network", "Accessibility"):
            connection.command(f"{domain}.enable")
        connection.command("Page.navigate", {"url": url})
        _wait_for_ready(connection)
        desktop = _evaluate(connection, DESKTOP_EXPRESSION)
        desktop_checks = dict(desktop.get("checks", {}))
        desktop_checks.update(_ax_checks(connection))

        connection.command(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": 390,
                "height": 844,
                "deviceScaleFactor": 1,
                "mobile": True,
            },
        )
        connection.command(
            "Emulation.setEmulatedMedia",
            {
                "media": "screen",
                "features": [{"name": "prefers-reduced-motion", "value": "reduce"}],
            },
        )
        connection.command("Page.reload", {"ignoreCache": True})
        _wait_for_ready(connection)
        time.sleep(0.2)
        mobile = _evaluate(connection, MOBILE_EXPRESSION)
        mobile_checks = dict(mobile.get("checks", {}))

        exception_events = [
            event for event in connection.events if event.get("method") == "Runtime.exceptionThrown"
        ]
        error_logs = [
            event
            for event in connection.events
            if event.get("method") == "Log.entryAdded"
            and event.get("params", {}).get("entry", {}).get("level") == "error"
        ]
        failed_requests = [
            event
            for event in connection.events
            if event.get("method") == "Network.loadingFailed"
            and event.get("params", {}).get("type") not in {"Other"}
        ]
        runtime_checks = {
            "no_javascript_exceptions": not exception_events,
            "no_browser_error_logs": not error_logs,
            "no_required_resource_failures": not failed_requests,
        }
        checks = {**desktop_checks, **mobile_checks, **runtime_checks}
        failures = sorted(name for name, passed in checks.items() if not passed)
        return {
            "schema_version": "W7TP-MEDICAL-CARE-BROWSER-PRODUCT-VERIFY/1.0",
            "state": "PASS_BROWSER_PRODUCT" if not failures else "HOLD_BROWSER_PRODUCT",
            "url": url,
            "checks": checks,
            "failure_codes": failures,
            "observations": {
                "desktop": desktop.get("details", {}),
                "mobile": mobile.get("details", {}),
                "javascript_exception_count": len(exception_events),
                "browser_error_log_count": len(error_logs),
                "required_resource_failure_count": len(failed_requests),
            },
            "side_effects": {
                "db_write": False,
                "form_submit": False,
                "credential_read": False,
                "browser_profile_persisted": False,
            },
        }
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the public medical-care demo in a real Chromium browser."
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--chromium")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        report = verify(args.url, args.chromium)
    except (OSError, VerificationError, ValueError) as exc:
        report = {
            "schema_version": "W7TP-MEDICAL-CARE-BROWSER-PRODUCT-VERIFY/1.0",
            "state": "HOLD_BROWSER_PRODUCT",
            "url": args.url,
            "checks": {},
            "failure_codes": ["BROWSER_VERIFIER_RUNTIME"],
            "error": str(exc),
            "side_effects": {
                "db_write": False,
                "form_submit": False,
                "credential_read": False,
                "browser_profile_persisted": False,
            },
        }
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["state"] == "PASS_BROWSER_PRODUCT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
