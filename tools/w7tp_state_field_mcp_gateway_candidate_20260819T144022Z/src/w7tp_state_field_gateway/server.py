"""Local-only JSON-RPC MCP Streamable HTTP candidate transport."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .errors import GatewayError
from .gateway import StateFieldGateway
from .policy import BIND_HOST, MAX_HTTP_BODY, validate_bind_host, validate_integer
from .redaction import redact_text

MCP_PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "w7tp-state-field-mcp-gateway-candidate"
SERVER_VERSION = "0.1.0-candidate"


def _rpc_error(request_id: Any, code: int, message: str, data_code: str | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": redact_text(message, 512)}
    if data_code is not None:
        error["data"] = {"policy_code": data_code}
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _rpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def create_app(gateway: StateFieldGateway | None = None) -> FastAPI:
    """Create an app with no docs, static files, resources, or arbitrary routes."""

    bounded_gateway = gateway or StateFieldGateway()
    app = FastAPI(
        title=SERVER_NAME,
        version=SERVER_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def enforce_loopback_request(request: Request, call_next: Any) -> Response:
        client_host = request.client.host if request.client is not None else ""
        if client_host != BIND_HOST:
            return JSONResponse(
                _rpc_error(None, -32001, "Only loopback clients are permitted.", "DENY_NON_LOOPBACK_CLIENT"),
                status_code=403,
            )
        host_header = request.headers.get("host", "")
        if host_header.split(":", 1)[0] != BIND_HOST:
            return JSONResponse(
                _rpc_error(None, -32002, "The Host header is outside the loopback boundary.", "DENY_HOST"),
                status_code=403,
            )
        origin = request.headers.get("origin")
        if origin is not None:
            parsed_origin = urlsplit(origin)
            try:
                origin_port_valid = parsed_origin.port is not None
            except ValueError:
                origin_port_valid = False
            if (
                parsed_origin.scheme != "http"
                or parsed_origin.hostname != BIND_HOST
                or not origin_port_valid
                or parsed_origin.username is not None
                or parsed_origin.password is not None
            ):
                return JSONResponse(
                    _rpc_error(None, -32003, "The Origin header is outside the loopback boundary.", "DENY_ORIGIN"),
                    status_code=403,
                )
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                parsed_length = int(content_length)
                if parsed_length < 0 or parsed_length > MAX_HTTP_BODY:
                    return JSONResponse(
                        _rpc_error(None, -32600, "Request body exceeds the policy limit.", "DENY_BODY_SIZE"),
                        status_code=413,
                    )
            except ValueError:
                return JSONResponse(
                    _rpc_error(None, -32600, "Invalid Content-Length header.", "DENY_SCHEMA"),
                    status_code=400,
                )
        return await call_next(request)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {
            "status": "candidate-ready",
            "bind_policy": BIND_HOST,
            "formal_activation": False,
            "remote_reachability": False,
        }

    @app.post("/mcp")
    async def mcp(request: Request) -> Response:
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return JSONResponse(
                _rpc_error(None, -32600, "Content-Type must be application/json.", "DENY_CONTENT_TYPE"),
                status_code=415,
            )
        body_parts: list[bytes] = []
        body_size = 0
        async for chunk in request.stream():
            body_size += len(chunk)
            if body_size > MAX_HTTP_BODY:
                return JSONResponse(
                    _rpc_error(
                        None,
                        -32600,
                        "Request body exceeds the policy limit.",
                        "DENY_BODY_SIZE",
                    ),
                    status_code=413,
                )
            body_parts.append(chunk)
        body = b"".join(body_parts)
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JSONResponse(_rpc_error(None, -32700, "Parse error."), status_code=400)
        if not isinstance(payload, Mapping) or payload.get("jsonrpc") != "2.0":
            return JSONResponse(_rpc_error(payload.get("id") if isinstance(payload, Mapping) else None, -32600, "Invalid Request."), status_code=400)
        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params", {})
        if not isinstance(method, str) or not isinstance(params, Mapping):
            return JSONResponse(_rpc_error(request_id, -32600, "Invalid Request."), status_code=400)
        if method == "notifications/initialized":
            return Response(status_code=202)
        if request_id is None:
            return Response(status_code=202)
        if method == "initialize":
            if (
                set(params) - {"protocolVersion", "capabilities", "clientInfo"}
                or not isinstance(params.get("protocolVersion"), str)
                or not isinstance(params.get("capabilities"), Mapping)
                or not isinstance(params.get("clientInfo"), Mapping)
            ):
                return JSONResponse(
                    _rpc_error(request_id, -32602, "Invalid initialize parameters."),
                    status_code=400,
                )
            result = {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "Local candidate only. Eight focused allowlisted tools; no shell, arbitrary path, "
                    "remote execution, credential intake, formal authority, deployment, or landing."
                ),
            }
            return JSONResponse(
                _rpc_result(request_id, result),
                headers={"MCP-Protocol-Version": MCP_PROTOCOL_VERSION},
            )
        if method == "ping":
            return JSONResponse(_rpc_result(request_id, {}))
        if method == "tools/list":
            if set(params) - {"cursor"}:
                return JSONResponse(_rpc_error(request_id, -32602, "Invalid tool-list parameters."), status_code=400)
            return JSONResponse(_rpc_result(request_id, {"tools": bounded_gateway.list_tool_definitions()}))
        if method == "tools/call":
            if set(params) != {"name", "arguments"}:
                return JSONResponse(_rpc_error(request_id, -32602, "Invalid tool-call parameters."), status_code=400)
            try:
                envelope = bounded_gateway.call_tool(params["name"], params["arguments"])
            except GatewayError as exc:
                result = {
                    "content": [{"type": "text", "text": f"{exc.code}: {exc.safe_message}"}],
                    "isError": True,
                }
                return JSONResponse(_rpc_result(request_id, result))
            except Exception:
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": "BACKEND_NOT_OBSERVED: The bounded backend failed safely.",
                        }
                    ],
                    "isError": True,
                }
                return JSONResponse(_rpc_result(request_id, result))
            structured = bounded_gateway.to_mcp_structured_content(envelope)
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    }
                ],
                "structuredContent": structured,
                "isError": False,
            }
            return JSONResponse(_rpc_result(request_id, result))
        return JSONResponse(_rpc_error(request_id, -32601, "Method not found."), status_code=404)

    return app


app = create_app()


def run_server(host: str, port: int) -> None:
    """Run only on exact IPv4 loopback; configuration cannot widen the bind."""

    validate_bind_host(host)
    safe_port = validate_integer(port, "port", 0, 65_535)
    uvicorn.run(app, host=BIND_HOST, port=safe_port, access_log=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local-only W7TP MCP candidate.")
    parser.add_argument("--host", default=BIND_HOST)
    parser.add_argument("--port", default=8765, type=int)
    arguments = parser.parse_args()
    run_server(arguments.host, arguments.port)


if __name__ == "__main__":
    main()
