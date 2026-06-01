from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


VECTOR_DIMENSIONS = 64
STORE: dict[str, dict[str, Any]] = {}

app = FastAPI(title="Taiji Vector Runtime Lite", version="0.1.0")


class UpsertRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    text: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[\w\u4e00-\u9fff]+", text.lower())


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embed_text(text: str) -> list[float]:
    vector = [0.0] * VECTOR_DIMENSIONS
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % VECTOR_DIMENSIONS
        weight = 1.0 + (digest[2] / 255.0)
        vector[index] += weight
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 8) for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def safe_metadata(metadata: dict[str, str]) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, value in metadata.items():
        lowered = key.lower()
        if any(marker in lowered for marker in ("secret", "token", "key", "password", "credential")):
            continue
        safe[str(key)[:64]] = str(value)[:256]
    return safe


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "Taiji_Vector_Runtime_Lite",
        "version": "0.1.0",
        "external_api_called": False,
        "stored_items": len(STORE),
    }


@app.get("/policy")
def policy() -> dict[str, Any]:
    return {
        "policy_locked": True,
        "plaintext_persistence": False,
        "external_api_calls": False,
        "secret_material_allowed": False,
        "storage_mode": "memory_hash_and_vector_only",
        "required_gates": [
            "taiji-metric-preflight",
            "human_decision_receipt",
            "approved_external_deployment_control",
            "audit_jsonl",
            "sha256_baseline",
        ],
    }


@app.post("/vectors/upsert")
def upsert(request: UpsertRequest) -> dict[str, Any]:
    vector = embed_text(request.text)
    STORE[request.item_id] = {
        "item_id": request.item_id,
        "sha256": text_sha256(request.text),
        "vector": vector,
        "metadata": safe_metadata(request.metadata),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return {
        "ok": True,
        "item_id": request.item_id,
        "sha256": STORE[request.item_id]["sha256"],
        "plaintext_stored": False,
        "external_api_called": False,
    }


@app.post("/vectors/search")
def search(request: SearchRequest) -> dict[str, Any]:
    if not STORE:
        return {"ok": True, "matches": [], "plaintext_stored": False}
    query_vector = embed_text(request.text)
    scored = [
        {
            "item_id": item["item_id"],
            "score": round(cosine(query_vector, item["vector"]), 8),
            "sha256": item["sha256"],
            "metadata": item["metadata"],
        }
        for item in STORE.values()
    ]
    scored.sort(key=lambda item: item["score"], reverse=True)
    return {
        "ok": True,
        "matches": scored[: request.limit],
        "plaintext_stored": False,
        "external_api_called": False,
    }


@app.get("/vectors/{item_id}")
def get_item(item_id: str) -> dict[str, Any]:
    item = STORE.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="item not found")
    return {
        "item_id": item["item_id"],
        "sha256": item["sha256"],
        "metadata": item["metadata"],
        "plaintext_stored": False,
    }
