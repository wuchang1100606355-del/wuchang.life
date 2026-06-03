from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import hashlib
import json
import os
import urllib.request
import urllib.error

APP_NAME = "Taiji POS Google Voice Tool"
CLAW_SAFE_URL = os.getenv("CLAW_SAFE_URL", "http://taiji_claw_safe:9004")
STORE_RAW_TRANSCRIPT = os.getenv("STORE_RAW_TRANSCRIPT", "false").lower() == "true"

AUDIT_DIR = Path("/mnt/audit")
QUEUE_DIR = Path("/mnt/queue")
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
QUEUE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=APP_NAME, version="0.1.0")


class VoiceIntent(BaseModel):
    session_id: str = Field(..., min_length=3)
    device_id: str = Field(..., min_length=2)
    transcript: str = Field(..., min_length=1)
    locale: str = "zh-TW"
    source: str = "sunmi_google_business_voice"
    execute: bool = False
    confirmation_token: Optional[str] = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_obj(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def audit(event: Dict[str, Any]) -> Dict[str, Any]:
    event["timestamp"] = now_iso()
    event["event_hash"] = sha256_obj(event)
    p = AUDIT_DIR / f"{event['timestamp'].replace(':','-')}_{event['event_hash'][:16]}.json"
    p.write_text(json.dumps(event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return event


def post_json(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = CLAW_SAFE_URL + path
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return {
                "ok": True,
                "http_status": res.status,
                "body": json.loads(res.read().decode("utf-8")),
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return {
            "ok": False,
            "http_status": e.code,
            "body": parsed,
        }


def get_json(path: str) -> Dict[str, Any]:
    url = CLAW_SAFE_URL + path
    with urllib.request.urlopen(url, timeout=20) as res:
        return json.loads(res.read().decode("utf-8"))


def infer_action(text: str) -> Dict[str, str]:
    t = text.lower()

    if any(k in t for k in ["health", "狀態", "健康", "檢查", "外骨骼"]):
        return {
            "action": "health_check",
            "resource_hint": "taiji_claw_safe",
            "reply": "收到，這是狀態查詢任務。"
        }

    if any(k in t for k in ["所有權人", "owner", "super admin", "超級管理員", "授予最高"]):
        return {
            "action": "grant_owner",
            "resource_hint": "google_workspace",
            "reply": "這是最高風險權限任務，必須禁止自動化。"
        }

    if any(k in t for k in ["啟用廣告", "投放廣告", "啟動廣告", "google ads", "ad grants"]):
        return {
            "action": "enable_google_ads",
            "resource_hint": "google_ads_locked",
            "reply": "廣告帳戶目前鎖定到最終審查完成，不可啟用投放。"
        }

    if any(k in t for k in ["共享雲端硬碟", "shared drive", "冷封存盤", "建立硬碟"]):
        return {
            "action": "create_shared_drive",
            "resource_hint": "google_workspace_shared_drive",
            "reply": "這是需要確認的雲端治理任務。"
        }

    if any(k in t for k in ["上傳封存", "封存包", "冷封存", "sha256"]):
        return {
            "action": "upload_archive_bundle",
            "resource_hint": "WUCHANG_20_TAIJI_COLD_ARCHIVE",
            "reply": "這是需要確認的冷封存任務。"
        }

    return {
        "action": "voice_command_review",
        "resource_hint": "pos_voice_command",
        "reply": "收到語音指令，先列入人工確認與任務分類。"
    }


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "service": APP_NAME,
        "mode": "no_recording_text_intent_gateway",
        "claw_safe_url": CLAW_SAFE_URL,
        "store_raw_transcript": STORE_RAW_TRANSCRIPT,
        "audio_recording": False,
        "audio_file_upload": False,
    }


@app.post("/v1/pos/voice-intent")
def voice_intent(v: VoiceIntent):
    transcript_hash = sha256_text(v.transcript)
    device_hash = sha256_text(v.device_id)
    inferred = infer_action(v.transcript)

    payload = {
        "source": v.source,
        "locale": v.locale,
        "session_hash": sha256_text(v.session_id),
        "device_hash": device_hash,
        "transcript_hash": transcript_hash,
        "raw_transcript_stored": STORE_RAW_TRANSCRIPT
    }

    if STORE_RAW_TRANSCRIPT:
        payload["raw_transcript"] = v.transcript

    task_id = f"pos_voice_{v.session_id}_{transcript_hash[:10]}"

    envelope = {
        "task_id": task_id,
        "action": inferred["action"],
        "resource_hint": inferred["resource_hint"],
        "payload": payload,
        "actor": "sunmi_pos_google_voice",
        "dry_run": not v.execute,
        "confirmation_token": v.confirmation_token
    }

    if inferred["action"] == "health_check":
        claw_health = get_json("/healthz")
        result = {
            "ok": True,
            "voice_mode": "no_recording_text_intent",
            "inferred": inferred,
            "claw_health": claw_health,
            "transcript_hash": transcript_hash,
            "reply_text": "Claw Safe 狀態正常，外骨骼手臂在線。"
        }
        audit({
            "type": "pos_voice_health",
            "session_hash": sha256_text(v.session_id),
            "device_hash": device_hash,
            "transcript_hash": transcript_hash,
            "action": inferred["action"]
        })
        return result

    path = "/v1/tasks/execute" if v.execute else "/v1/tasks/dry-run"
    claw_result = post_json(path, envelope)

    event = {
        "type": "pos_voice_intent",
        "session_hash": sha256_text(v.session_id),
        "device_hash": device_hash,
        "transcript_hash": transcript_hash,
        "action": inferred["action"],
        "resource_hint": inferred["resource_hint"],
        "execute": v.execute,
        "claw_http_status": claw_result.get("http_status"),
        "claw_ok": claw_result.get("ok")
    }
    audit(event)

    return {
        "ok": True,
        "voice_mode": "no_recording_text_intent",
        "audio_saved": False,
        "transcript_hash": transcript_hash,
        "device_hash": device_hash,
        "inferred": inferred,
        "claw_result": claw_result,
        "reply_text": inferred["reply"]
    }


@app.post("/v1/audio/upload")
def reject_audio_upload():
    raise HTTPException(
        status_code=403,
        detail={
            "reason": "audio_upload_disabled",
            "rule": "此系統不接收錄音檔；請使用商米 POS / Google 商業授權語音系統完成即時語音轉文字後，只送文字 intent。"
        }
    )
