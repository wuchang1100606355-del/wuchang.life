from __future__ import annotations

import http.client
import json
import socket
import threading
import time
import unittest
from typing import Any

import uvicorn

from tests.support import gateway
from w7tp_state_field_gateway.policy import MAX_HTTP_BODY, TOOL_NAMES, validate_bind_host
from w7tp_state_field_gateway.errors import GatewayError
from w7tp_state_field_gateway.server import MCP_PROTOCOL_VERSION, create_app


class LocalMCPServer:
    def __init__(self, gateway_instance: Any | None = None) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("127.0.0.1", 0))
        self.socket.listen(128)
        self.host, self.port = self.socket.getsockname()
        config = uvicorn.Config(
            create_app(gateway_instance or gateway()),
            host="127.0.0.1",
            port=0,
            log_level="critical",
            access_log=False,
            lifespan="off",
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(
            target=self.server.run,
            kwargs={"sockets": [self.socket]},
            daemon=True,
        )

    def __enter__(self) -> "LocalMCPServer":
        self.thread.start()
        deadline = time.monotonic() + 5.0
        while not self.server.started and time.monotonic() < deadline:
            time.sleep(0.01)
        if not self.server.started:
            raise RuntimeError("Local MCP server did not start.")
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5.0)
        self.socket.close()

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, bytes]:
        connection = http.client.HTTPConnection(self.host, self.port, timeout=3)
        default_headers = {"Host": f"127.0.0.1:{self.port}"}
        if headers:
            default_headers.update(headers)
        connection.request(method, path, body=body, headers=default_headers)
        response = connection.getresponse()
        content = response.read()
        status = response.status
        connection.close()
        return status, content

    def rpc(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        status, content = self.request(
            "POST",
            "/mcp",
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        return status, json.loads(content)

    def chunked_request(self, chunks: list[bytes]) -> tuple[int, bytes]:
        connection = http.client.HTTPConnection(self.host, self.port, timeout=3)
        connection.request(
            "POST",
            "/mcp",
            body=iter(chunks),
            headers={
                "Host": f"127.0.0.1:{self.port}",
                "Content-Type": "application/json",
            },
            encode_chunked=True,
        )
        response = connection.getresponse()
        content = response.read()
        status = response.status
        connection.close()
        return status, content


class MCPHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = LocalMCPServer()
        cls.server = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.context.__exit__(None, None, None)

    def test_actual_listener_is_exact_ipv4_loopback(self) -> None:
        self.assertEqual(self.server.host, "127.0.0.1")

    def test_initialize_tools_list_and_call(self) -> None:
        status, initialized = self.server.rpc(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "synthetic-test", "version": "1"},
                },
            }
        )
        self.assertEqual(status, 200)
        self.assertEqual(initialized["id"], 1)
        self.assertEqual(initialized["result"]["protocolVersion"], MCP_PROTOCOL_VERSION)
        status, listed = self.server.rpc(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        self.assertEqual(status, 200)
        self.assertEqual([tool["name"] for tool in listed["result"]["tools"]], list(TOOL_NAMES))
        status, called = self.server.rpc(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "list_nodes", "arguments": {}},
            }
        )
        self.assertEqual(status, 200)
        self.assertEqual(called["id"], 3)
        self.assertFalse(called["result"]["isError"])
        self.assertEqual(called["result"]["structuredContent"]["adi_index_status"], "NON_EXECUTABLE")

    def test_initialize_requires_closed_typed_parameters(self) -> None:
        status, response = self.server.rpc(
            {"jsonrpc": "2.0", "id": 11, "method": "initialize", "params": {}}
        )
        self.assertEqual(status, 400)
        self.assertEqual(response["error"]["code"], -32602)

    def test_notification_is_accepted(self) -> None:
        status, content = self.server.request(
            "POST",
            "/mcp",
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode(),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(status, 202)
        self.assertEqual(content, b"")

    def test_invalid_json_unknown_method_and_unknown_tool_fail_safely(self) -> None:
        status, parsed = self.server.request(
            "POST", "/mcp", b"{", {"Content-Type": "application/json"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(parsed)["error"]["code"], -32700)
        status, unknown_method = self.server.rpc(
            {"jsonrpc": "2.0", "id": 4, "method": "execute", "params": {}}
        )
        self.assertEqual(status, 404)
        self.assertEqual(unknown_method["error"]["code"], -32601)
        status, unknown_tool = self.server.rpc(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "execute_task", "arguments": {}},
            }
        )
        self.assertEqual(status, 200)
        self.assertTrue(unknown_tool["result"]["isError"])
        self.assertIn("DENY_UNKNOWN_TOOL", unknown_tool["result"]["content"][0]["text"])

    def test_other_paths_methods_large_body_host_and_origin_are_denied(self) -> None:
        status, _ = self.server.request("GET", "/mcp")
        self.assertEqual(status, 405)
        status, _ = self.server.request("POST", "/../mcp", b"{}", {"Content-Type": "application/json"})
        self.assertIn(status, {404, 405})
        status, _ = self.server.request(
            "POST",
            "/mcp",
            b"x" * (MAX_HTTP_BODY + 1),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(status, 413)
        status, _ = self.server.chunked_request(
            [b"x" * (MAX_HTTP_BODY // 2), b"y" * (MAX_HTTP_BODY // 2 + 1)]
        )
        self.assertEqual(status, 413)
        status, _ = self.server.request(
            "POST",
            "/mcp",
            b"{}",
            {"Content-Type": "application/json", "Host": "external.invalid"},
        )
        self.assertEqual(status, 403)
        status, _ = self.server.request(
            "POST",
            "/mcp",
            b"{}",
            {"Content-Type": "application/json", "Origin": "https://external.invalid"},
        )
        self.assertEqual(status, 403)

    def test_non_loopback_bind_spellings_are_rejected(self) -> None:
        for host in ("0.0.0.0", "::", "::1", "localhost"):
            with self.subTest(host=host):
                with self.assertRaises(GatewayError):
                    validate_bind_host(host)

    def test_backend_exception_is_not_reflected_to_model_context(self) -> None:
        synthetic_secret = "person" + "@example.invalid " + "tskey-" + "auth-SYNTHETIC1234"

        class FaultyGateway:
            def call_tool(self, _name: Any, _arguments: Any) -> dict[str, Any]:
                raise RuntimeError(synthetic_secret)

        with LocalMCPServer(FaultyGateway()) as isolated:
            status, response = isolated.rpc(
                {
                    "jsonrpc": "2.0",
                    "id": 12,
                    "method": "tools/call",
                    "params": {"name": "list_nodes", "arguments": {}},
                }
            )
        self.assertEqual(status, 200)
        serialized = json.dumps(response)
        self.assertTrue(response["result"]["isError"])
        self.assertNotIn(synthetic_secret, serialized)
        self.assertIn("BACKEND_NOT_OBSERVED", serialized)


if __name__ == "__main__":
    unittest.main()
