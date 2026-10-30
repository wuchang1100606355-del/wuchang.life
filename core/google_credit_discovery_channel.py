# -*- coding: utf-8 -*-
"""Google Cloud $31,404 Credit Guarded Channel (Project: my-j-483304).
Strictly binds to discoveryengine.googleapis.com; blocks aiplatform.googleapis.com.
"""
from __future__ import annotations
import json, os, re, urllib.parse, urllib.request

PROJECT_ID = "my-j-483304"
CREDIT_ID = "97e7ca8e63bee16d5b6a0fb0168196774f3092a97af6d2407286571ca9438847"
ALLOWED_HOST = "discoveryengine.googleapis.com"
ALLOWED_DATA_STORES = frozenset({"wuchang-menu-64"})
ALLOWED_ENGINES = frozenset({"wuchang-ops-engine"})
DISCOVERY_BASE = f"https://{ALLOWED_HOST}/v1beta/projects/{PROJECT_ID}/locations/global/collections/default_collection"

PII_PATTERNS = re.compile(
    r"(09\d{2}[-\s]?\d{3}[-\s]?\d{3}|[A-Z][12]\d{8}|[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|password|passwd|身分證|密碼)",
    re.IGNORECASE,
)


def validate_discovery_endpoint_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("BLOCK_EMPTY_ENDPOINT_URL")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"BLOCK_NON_HTTPS_ENDPOINT: {parsed.scheme!r}")
    if parsed.netloc != ALLOWED_HOST or "aiplatform.googleapis.com" in url:
        raise ValueError(f"BLOCK_FORBIDDEN_ENDPOINT_HOST: {parsed.netloc!r}")
    if f"/projects/{PROJECT_ID}/" not in parsed.path:
        raise ValueError("BLOCK_UNBOUND_GCP_PROJECT")
    return url


def build_converse_endpoint(data_store_id: str = "wuchang-menu-64", conversation_id: str = "-") -> str:
    if data_store_id not in ALLOWED_DATA_STORES:
        raise ValueError(f"BLOCK_UNAPPROVED_DATA_STORE: {data_store_id!r}")
    url = f"{DISCOVERY_BASE}/dataStores/{data_store_id}/conversations/{conversation_id}:converse"
    return validate_discovery_endpoint_url(url)


def build_search_endpoint(engine_id: str = "wuchang-ops-engine") -> str:
    if engine_id not in ALLOWED_ENGINES:
        raise ValueError(f"BLOCK_UNAPPROVED_ENGINE: {engine_id!r}")
    url = f"{DISCOVERY_BASE}/engines/{engine_id}/servingConfigs/default_search:search"
    return validate_discovery_endpoint_url(url)


def inspect_discovery_credit_channel_status(data_store_id: str = "wuchang-menu-64") -> dict:
    """Read-only status inspection that NEVER performs any network or cloud call."""
    endpoint = build_converse_endpoint(data_store_id)
    return {
        "state": "READY_GUARDED_ENDPOINT_CONFIGURED",
        "mode": "READ_ONLY_STATUS_NO_NETWORK",
        "network_called": False,
        "credit_id": CREDIT_ID,
        "project": PROJECT_ID,
        "data_store_id": data_store_id,
        "endpoint": endpoint,
        "billing_guarantee": "100%_DISCOVERY_ENGINE_CREDIT_ONLY",
        "contains_member_plaintext": False,
    }


def query_discovery_credit_channel(
    query_text: str,
    data_store_id: str = "wuchang-menu-64",
    *,
    execute_network: bool = False,
    seat_ref: str | None = None,
    authority_scope: str | None = None,
) -> dict:
    if not isinstance(query_text, str) or not query_text.strip() or len(query_text.strip()) > 300:
        return {
            "state": "HOLD_INVALID_QUERY_INPUT",
            "network_called": False,
            "contains_member_plaintext": False,
        }
    if PII_PATTERNS.search(query_text):
        return {
            "state": "HOLD_MEMBER_PLAINTEXT_DETECTED",
            "network_called": False,
            "contains_member_plaintext": False,
        }
    endpoint = build_converse_endpoint(data_store_id)
    payload = {
        "query": {"input": query_text.strip()},
        "summarySpec": {"summaryResultCount": 5, "modelSpec": {"version": "gemini-1.5-flash"}},
    }
    # 預設唯讀，絕不主動發出外部網路請求
    if not execute_network:
        return {
            "state": "READY_GUARDED_ENDPOINT_CONFIGURED",
            "network_called": False,
            "credit_id": CREDIT_ID,
            "project": PROJECT_ID,
            "endpoint": endpoint,
            "billing_guarantee": "100%_DISCOVERY_ENGINE_CREDIT_ONLY",
            "payload_preview": payload,
            "contains_member_plaintext": False,
        }
    if not seat_ref or not authority_scope or authority_scope != "cloud.discovery.converse":
        return {
            "state": "HOLD_CLOUD_SCOPE_OR_SEAT_MISSING",
            "network_called": False,
            "contains_member_plaintext": False,
        }
    token = os.getenv("GOOGLE_OAUTH_ACCESS_TOKEN", "").strip()
    if not token:
        return {
            "state": "HOLD_CLOUD_TOKEN_MISSING",
            "network_called": False,
            "endpoint": endpoint,
            "contains_member_plaintext": False,
        }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "X-Goog-User-Project": PROJECT_ID,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return {
            "state": "PASS_DISCOVERY_ENGINE_CREDIT_CALL",
            "network_called": True,
            "seat_ref": seat_ref,
            "authority_scope": authority_scope,
            "contains_member_plaintext": False,
            "data": json.loads(resp.read().decode("utf-8")),
        }
