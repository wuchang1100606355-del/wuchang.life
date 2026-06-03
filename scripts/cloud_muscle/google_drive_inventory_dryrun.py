#!/usr/bin/env python3
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

FORBIDDEN = [
    "private_key",
    "client_secret",
    "refresh_token",
    "access_token",
    "password",
    "BEGIN PRIVATE KEY",
]

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def reject_secret_text(text: str):
    lower = text.lower()
    for k in FORBIDDEN:
        if k.lower() in lower:
            raise SystemExit(f"REFUSE_TO_WRITE_SECRET_MATERIAL: {k}")

def main():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception as e:
        raise SystemExit(
            "Missing packages. Run:\n"
            "python3 -m venv .venv_cloud_muscle\n"
            "source .venv_cloud_muscle/bin/activate\n"
            "pip install --upgrade google-api-python-client google-auth\n"
            f"\nImport error: {e}"
        )

    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not key_path:
        raise SystemExit("GOOGLE_APPLICATION_CREDENTIALS is not set.")

    p = Path(key_path).expanduser()
    if not p.exists():
        raise SystemExit(f"Credential file not found: {p}")

    if p.stat().st_mode & 0o077:
        raise SystemExit(f"Credential file permissions too open. Run: chmod 600 {p}")

    config = json.loads(Path("config/cloud_muscle/google_drive_inventory.config.json").read_text(encoding="utf-8"))
    scopes = config["scopes"]

    creds = service_account.Credentials.from_service_account_file(str(p), scopes=scopes)
    actor = getattr(creds, "service_account_email", "unknown-service-account")

    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    resp = service.files().list(
        pageSize=int(config.get("max_results", 20)),
        fields="files(id,name,mimeType,modifiedTime,driveId,owners(emailAddress,displayName),webViewLink)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        corpora="allDrives"
    ).execute()

    files = resp.get("files", [])
    safe_items = []
    for f in files:
        item = {
            "id_hash": sha256_text(f.get("id", "")) if f.get("id") else "",
            "name": f.get("name", ""),
            "mimeType": f.get("mimeType", ""),
            "modifiedTime": f.get("modifiedTime", ""),
            "driveId_hash": sha256_text(f.get("driveId", "")) if f.get("driveId") else "",
            "owner_count": len(f.get("owners", [])),
            "webViewLink_present": bool(f.get("webViewLink")),
        }
        safe_items.append(item)

    result = {
        "type": "GOOGLE_DRIVE_INVENTORY_DRYRUN_RESULT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "readonly_dryrun",
        "actor_hash": sha256_text(actor),
        "scope_hashes": [sha256_text(s) for s in scopes],
        "item_count": len(safe_items),
        "items": safe_items,
        "rule": "No private key, token, raw credential, or file content stored.",
    }

    raw = json.dumps(result, ensure_ascii=False, sort_keys=True)
    reject_secret_text(raw)
    result["audit_hash"] = sha256_text(raw)

    out_dir = Path("reports/cloud_muscle")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"google_drive_inventory_dryrun_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{result['audit_hash'][:12]}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    mem_dir = Path("data/service_account_memory")
    mem_dir.mkdir(parents=True, exist_ok=True)
    mem = mem_dir / "capability_memory.json"
    if mem.exists():
        db = json.loads(mem.read_text(encoding="utf-8"))
    else:
        db = {
            "type": "SERVICE_ACCOUNT_CAPABILITY_MEMORY_DB",
            "records": [],
            "rule": "No private keys, no service_account_json, no tokens, no raw credentials."
        }

    db["records"].append({
        "timestamp": result["timestamp"],
        "service_account_alias": "google_drive_inventory_worker",
        "actor_hash": result["actor_hash"],
        "action": "drive_inventory_dryrun",
        "risk": "L0_READONLY",
        "result": "success",
        "scope_hashes": result["scope_hashes"],
        "audit_ref": str(out),
        "audit_hash": result["audit_hash"]
    })
    db["updated_at"] = result["timestamp"]
    mem.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "status": "GOOGLE_DRIVE_CLOUD_MUSCLE_CONNECTED_DRYRUN",
        "items": len(safe_items),
        "audit": str(out),
        "audit_hash": result["audit_hash"]
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
