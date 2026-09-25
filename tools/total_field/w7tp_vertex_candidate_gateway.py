#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config/w7tp_vertex_candidate_gateway.json"
RESOURCE_TOKEN = re.compile(r"^[A-Za-z0-9._:-]+$")


class VertexGatewayError(ValueError):
    """Stable transport/configuration failure without credential material."""


def load_gateway_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VertexGatewayError("VERTEX_GATEWAY_CONFIG_READ_FAILED") from exc
    expected = {
        "schema_version",
        "provider",
        "project",
        "location",
        "model",
        "credential_file_ref",
        "cloud_output_authority",
        "formal_execution_authority",
        "founder_authorization_per_request",
        "auto_cloud_call",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise VertexGatewayError("VERTEX_GATEWAY_CONFIG_INVALID")
    fixed = {
        "schema_version": "W7TP-VERTEX-CANDIDATE-GATEWAY/1.0",
        "provider": "GOOGLE_VERTEX_AI",
        "cloud_output_authority": "CANDIDATE_ONLY",
        "formal_execution_authority": "LOCAL_TOTAL_FIELD_ONLY",
        "founder_authorization_per_request": True,
        "auto_cloud_call": False,
    }
    if any(value.get(key) != expected_value for key, expected_value in fixed.items()):
        raise VertexGatewayError("VERTEX_GATEWAY_GOVERNANCE_INVALID")
    for key in ("project", "location", "model"):
        token = value.get(key)
        if not isinstance(token, str) or not RESOURCE_TOKEN.fullmatch(token):
            raise VertexGatewayError("VERTEX_GATEWAY_RESOURCE_INVALID")
    credential_ref = value.get("credential_file_ref")
    if not isinstance(credential_ref, str) or not credential_ref:
        raise VertexGatewayError("VERTEX_GATEWAY_CREDENTIAL_REF_INVALID")
    return value


def generate_with_gcloud_rest(
    *,
    project: str,
    location: str,
    model: str,
    prompt: str,
    system_instruction: list[str],
    credential_file: Path,
) -> str:
    """Call Vertex generateContent through gcloud ADC without logging a token."""

    for token in (project, location, model):
        if not RESOURCE_TOKEN.fullmatch(token):
            raise VertexGatewayError("VERTEX_REST_RESOURCE_INVALID")
    if not credential_file.is_file():
        raise VertexGatewayError("VERTEX_REST_CREDENTIAL_FILE_MISSING")

    command_env = os.environ.copy()
    command_env["CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE"] = str(credential_file)
    try:
        token_result = subprocess.run(
            ["gcloud", "auth", "print-access-token", "--quiet"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
            env=command_env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise VertexGatewayError("VERTEX_REST_ACCESS_TOKEN_FAILED") from exc
    access_token = token_result.stdout.strip()
    if not access_token:
        raise VertexGatewayError("VERTEX_REST_ACCESS_TOKEN_EMPTY")

    host = (
        "aiplatform.googleapis.com"
        if location == "global"
        else f"{location}-aiplatform.googleapis.com"
    )
    endpoint = (
        f"https://{host}/v1/projects/{project}/locations/{location}"
        f"/publishers/google/models/{model}:generateContent"
    )
    request_body = {
        "systemInstruction": {
            "parts": [{"text": "\n".join(system_instruction)}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "maxOutputTokens": 16384,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_body = json.loads(response.read().decode("utf-8"))
        candidate = response_body["candidates"][0]
        finish_reason = candidate.get("finishReason")
        if finish_reason != "STOP":
            raise VertexGatewayError(
                f"VERTEX_REST_FINISH_REASON:{finish_reason or 'MISSING'}"
            )
        parts = candidate["content"]["parts"]
        if not isinstance(parts, list):
            raise TypeError("candidate parts must be a list")
        text = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        IndexError,
        TypeError,
    ) as exc:
        raise VertexGatewayError("VERTEX_REST_GENERATION_FAILED") from exc
    if not isinstance(text, str) or not text.strip():
        raise VertexGatewayError("VERTEX_REST_RESPONSE_EMPTY")
    return text


def emit(key: str, value: Any) -> None:
    print(f"{key}={value}")


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def extract_json(text: str) -> tuple[Any, bool]:
    text = text.strip()

    try:
        return json.loads(text), True
    except json.JSONDecodeError:
        pass

    fenced = re.search(
        r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced:
        try:
            return json.loads(fenced.group(1)), True
        except json.JSONDecodeError:
            pass

    first_object = text.find("{")
    last_object = text.rfind("}")
    if first_object >= 0 and last_object > first_object:
        try:
            return json.loads(text[first_object:last_object + 1]), True
        except json.JSONDecodeError:
            pass

    return {"raw_candidate_text": text}, False


def main() -> int:
    try:
        gateway_config = load_gateway_config()
    except VertexGatewayError as exc:
        emit("STATE", "HOLD_VERTEX_GATEWAY_CONFIG_INVALID")
        emit("REASON_CODE", str(exc))
        return 7

    parser = argparse.ArgumentParser(
        description="W7TP unified Vertex candidate gateway"
    )
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--project",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT", gateway_config["project"]),
    )
    parser.add_argument(
        "--location",
        default=os.environ.get("W7TP_VERTEX_LOCATION", gateway_config["location"]),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("W7TP_VERTEX_MODEL", gateway_config["model"]),
    )
    args = parser.parse_args()

    prompt_path = Path(args.prompt_file)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    authorized = (
        os.environ.get("FOUNDER_EXPLICIT_CLOUD_AUTHORIZATION") == "YES"
        or os.environ.get("W7TP_FOUNDER_EXPLICIT_CLOUD_AUTHORIZATION") == "YES"
    )

    if not authorized:
        emit("STATE", "HOLD_FOUNDER_CLOUD_AUTHORIZATION_REQUIRED")
        return 2

    if not prompt_path.is_file() or prompt_path.stat().st_size == 0:
        emit("STATE", "HOLD_PROMPT_NOT_FOUND")
        emit("PROMPT", prompt_path)
        return 3

    prompt = prompt_path.read_text(encoding="utf-8")
    prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    request_record = {
        "schema": "w7tp.vertex.candidate.request.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": args.project,
        "location": args.location,
        "prompt_file": str(prompt_path),
        "prompt_sha256": prompt_sha256,
        "cloud_output_authority": "CANDIDATE_ONLY",
        "formal_execution_authority": "LOCAL_TOTAL_FIELD_ONLY",
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
    }
    write_json(out / "CLOUD_REQUEST_RECORD.json", request_record)

    sdk_available = True
    try:
        from google.oauth2 import service_account
        import google.auth
        import vertexai
        from vertexai.generative_models import GenerationConfig, GenerativeModel
    except Exception:
        sdk_available = False

    credentials = None
    credential_source = "APPLICATION_DEFAULT_CREDENTIALS"

    configured_key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    configured_ref = Path(gateway_config["credential_file_ref"])
    repo_key = configured_ref if configured_ref.is_absolute() else ROOT / configured_ref
    rest_credential_file: Path | None = None

    if sdk_available:
        try:
            if configured_key and Path(configured_key).is_file():
                credentials = service_account.Credentials.from_service_account_file(
                    configured_key
                )
                credential_source = "GOOGLE_APPLICATION_CREDENTIALS"
            elif repo_key.is_file():
                credentials = service_account.Credentials.from_service_account_file(
                    str(repo_key)
                )
                credential_source = "REPO_SERVICE_ACCOUNT_FILE"
            else:
                credentials, detected_project = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                if not args.project and detected_project:
                    args.project = detected_project
        except Exception:
            emit("STATE", "HOLD_GOOGLE_AUTH_FAILED")
            emit("REASON_CODE", "GOOGLE_AUTH_INITIALIZATION_FAILED")
            return 5

        vertexai.init(
            project=args.project,
            location=args.location,
            credentials=credentials,
        )
    else:
        if configured_key and Path(configured_key).is_file():
            rest_credential_file = Path(configured_key)
            credential_source = "GOOGLE_APPLICATION_CREDENTIALS_GCLOUD_REST"
        elif repo_key.is_file():
            rest_credential_file = repo_key
            credential_source = "REPO_SERVICE_ACCOUNT_GCLOUD_REST"
        else:
            emit("STATE", "HOLD_GOOGLE_AUTH_FAILED")
            emit("REASON_CODE", "VERTEX_REST_CREDENTIAL_FILE_MISSING")
            return 5

    requested_models = []
    if args.model:
        requested_models.append(args.model)

    requested_models.extend([
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash-001",
        "gemini-1.5-pro-001",
    ])

    models = []
    for model_name in requested_models:
        if model_name and model_name not in models:
            models.append(model_name)

    system_instruction = [
        "You are a cloud candidate generator.",
        "Cloud output is candidate-only.",
        "Formal execution authority belongs only to the local W7TP Total Field.",
        "Return one valid JSON object only.",
        "Do not output credentials, tokens, passwords, raw member plaintext, or hidden reasoning.",
        "Do not claim implementation, benchmark, patentability, or legal effect without evidence.",
    ]

    model_errors: list[dict[str, str]] = []
    response_text = ""
    used_model = ""

    for model_name in models:
        try:
            if sdk_available:
                model = GenerativeModel(
                    model_name,
                    system_instruction=system_instruction,
                )
                response = model.generate_content(
                    prompt,
                    generation_config=GenerationConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                        max_output_tokens=8192,
                    ),
                )
                response_text = response.text or ""
            else:
                assert rest_credential_file is not None
                response_text = generate_with_gcloud_rest(
                    project=args.project,
                    location=args.location,
                    model=model_name,
                    prompt=prompt,
                    system_instruction=system_instruction,
                    credential_file=rest_credential_file,
                )
            used_model = model_name
            if response_text.strip():
                break
            model_errors.append({
                "model": model_name,
                "error": "EMPTY_RESPONSE",
            })
        except Exception as exc:
            model_errors.append({
                "model": model_name,
                "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
            })

    if not response_text.strip():
        write_json(out / "MODEL_ATTEMPT_ERRORS.json", model_errors)
        emit("STATE", "HOLD_VERTEX_ALL_MODELS_FAILED")
        emit("PROJECT", args.project)
        emit("LOCATION", args.location)
        emit("ERROR_REPORT", out / "MODEL_ATTEMPT_ERRORS.json")
        return 6

    raw_response = {
        "schema": "w7tp.vertex.raw_candidate.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": args.project,
        "location": args.location,
        "model": used_model,
        "credential_source": credential_source,
        "prompt_sha256": prompt_sha256,
        "candidate_text": response_text,
        "candidate_only": True,
    }
    write_json(out / "CLOUD_RAW_CANDIDATE.json", raw_response)

    normalized_content, json_parse_pass = extract_json(response_text)

    normalized = {
        "schema": "w7tp.vertex.normalized_candidate.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_model": used_model,
        "source_prompt_sha256": prompt_sha256,
        "json_parse": "PASS" if json_parse_pass else "WRAPPED_RAW_TEXT",
        "authority": "CANDIDATE_ONLY",
        "formal_execution_authority": "LOCAL_TOTAL_FIELD_ONLY",
        "candidate": normalized_content,
    }
    write_json(out / "CLOUD_NORMALIZED_CANDIDATE.json", normalized)

    normalized_bytes = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    normalized_sha256 = hashlib.sha256(normalized_bytes).hexdigest()

    forbidden_execution_markers = [
        '"db_write": true',
        '"deploy": true',
        '"restart": true',
        '"router_write": true',
        '"formal_submission": true',
        "DELETE_ORIGINAL_FILE",
        "AUTONOMOUS_CLOUD_AUTHORITY",
    ]
    normalized_scan = normalized_bytes.decode("utf-8", errors="replace").lower()
    detected = [
        marker
        for marker in forbidden_execution_markers
        if marker.lower() in normalized_scan
    ]

    verdict_state = (
        "HOLD_CANDIDATE_HARD_RISK_MARKER_DETECTED"
        if detected
        else "PASS_CANDIDATE_RECEIVED_LOCAL_REVIEW_REQUIRED"
    )

    verdict = {
        "schema": "w7tp.total_field.local_candidate_verdict.v1",
        "state": verdict_state,
        "candidate_sha256": normalized_sha256,
        "cloud_request": "PASS",
        "cloud_response": "PASS",
        "local_normalization": "PASS",
        "canonical_drift_check": "PENDING_LOCAL_REVIEW",
        "hard_risk_check": "HOLD" if detected else "PASS_PRELIMINARY",
        "detected_hard_risk_markers": detected,
        "accepted_count": 0,
        "corrected_count": 0,
        "held_count": 1,
        "rejected_count": 0,
        "trade_secret_quarantine_count": 0,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "formal_submission": False,
        "next": (
            "總場逐項比對候選內容，產生 ACCEPT、ACCEPT_WITH_CORRECTION、"
            "HOLD_FOR_EVIDENCE、REJECT_TECHNICAL_DRIFT、"
            "REJECT_OVERCLAIM 或 TRADE_SECRET_QUARANTINE 裁決。"
        ),
    }
    write_json(out / "FINAL_LOCAL_VERDICT.json", verdict)

    manifest = {
        "schema": "w7tp.vertex.candidate.gateway.manifest.v1",
        "files": {
            "request": "CLOUD_REQUEST_RECORD.json",
            "raw_candidate": "CLOUD_RAW_CANDIDATE.json",
            "normalized_candidate": "CLOUD_NORMALIZED_CANDIDATE.json",
            "local_verdict": "FINAL_LOCAL_VERDICT.json",
        },
        "model_attempt_errors": model_errors,
        "candidate_sha256": normalized_sha256,
    }
    write_json(out / "MANIFEST.json", manifest)

    emit("STATE", verdict_state)
    emit("CLOUD_PROVIDER", "GOOGLE_VERTEX_AI")
    emit("CLOUD_MODEL", used_model)
    emit("CLOUD_REQUEST", "PASS")
    emit("CLOUD_RESPONSE", "PASS")
    emit("LOCAL_NORMALIZATION", "PASS")
    emit("CANONICAL_DRIFT_CHECK", "PENDING_LOCAL_REVIEW")
    emit(
        "HARD_RISK_CHECK",
        "HOLD" if detected else "PASS_PRELIMINARY",
    )
    emit("CANDIDATE_SHA256", normalized_sha256)
    emit("OUT", out)
    emit("FINAL_LOCAL_VERDICT", out / "FINAL_LOCAL_VERDICT.json")
    emit("DB_WRITE", "NO")
    emit("DEPLOY", "NO")
    emit("RESTART", "NO")
    emit("ROUTER_WRITE", "NO")
    emit("FORMAL_SUBMISSION", "NO")
    emit("NEXT", verdict["next"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
