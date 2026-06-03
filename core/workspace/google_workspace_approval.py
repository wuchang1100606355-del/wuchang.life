import time, uuid, json, sqlite3
from pathlib import Path

DB = Path("data/workspace_approval.db")
DB.parent.mkdir(parents=True, exist_ok=True)

ALLOWED_ACTIONS = {
    "drive_list": {"scope": "drive.metadata.readonly", "risk": "low", "description": "列出 Drive 檔案中繼資料"},
    "drive_read": {"scope": "drive.readonly", "risk": "medium", "description": "讀取授權 Drive 檔案"},
    "gmail_draft": {"scope": "gmail.compose", "risk": "medium", "description": "建立 Gmail 草稿"},
    "calendar_read": {"scope": "calendar.readonly", "risk": "low", "description": "讀取 Calendar"},
    "calendar_create": {"scope": "calendar.events", "risk": "medium", "description": "建立 Calendar 事件"}
}

def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS workspace_requests (
        request_id TEXT PRIMARY KEY,
        action TEXT,
        payload_json TEXT,
        status TEXT,
        created_at REAL,
        approved_at REAL,
        executed_at REAL,
        result_json TEXT
    )""")
    con.commit()
    con.close()

def workspace_state():
    init_db()
    return {
        "version": "Wuchang-GoogleWorkspace-ApprovalGateway-v1",
        "name": "小J Google Workspace 核准閘道",
        "status": "active",
        "rule": "Local LLM proposes; user approves; gateway executes.",
        "allowed_actions": ALLOWED_ACTIONS,
        "db": str(DB)
    }

def propose_action(action: str, payload: dict):
    init_db()
    if action not in ALLOWED_ACTIONS:
        return {"ok": False, "error": "action_not_allowed", "allowed_actions": list(ALLOWED_ACTIONS)}
    rid = str(uuid.uuid4())
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO workspace_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (rid, action, json.dumps(payload, ensure_ascii=False), "pending_user_approval", time.time(), None, None, None)
    )
    con.commit()
    con.close()
    return {
        "ok": True,
        "request_id": rid,
        "status": "pending_user_approval",
        "action": action,
        "scope_required": ALLOWED_ACTIONS[action]["scope"],
        "risk": ALLOWED_ACTIONS[action]["risk"],
        "payload_preview": payload
    }

def approve_action(request_id: str):
    init_db()
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        "UPDATE workspace_requests SET status=?, approved_at=? WHERE request_id=? AND status=?",
        ("approved", time.time(), request_id, "pending_user_approval")
    )
    con.commit()
    changed = cur.rowcount
    con.close()
    return {"ok": bool(changed), "request_id": request_id, "status": "approved" if changed else "not_found_or_not_pending"}

def execute_action(request_id: str):
    init_db()
    con = sqlite3.connect(DB)
    cur = con.cursor()
    row = cur.execute("SELECT action, payload_json, status FROM workspace_requests WHERE request_id=?", (request_id,)).fetchone()
    if not row:
        con.close()
        return {"ok": False, "error": "request_not_found"}
    action, payload_json, status = row
    if status != "approved":
        con.close()
        return {"ok": False, "error": "not_approved", "status": status}
    payload = json.loads(payload_json)
    result = {
        "executed": False,
        "mode": "dry_run_until_google_oauth_connected",
        "action": action,
        "payload": payload,
        "message": "已通過使用者核准；等待 Google OAuth 憑證接入後執行。"
    }
    cur.execute(
        "UPDATE workspace_requests SET status=?, executed_at=?, result_json=? WHERE request_id=?",
        ("dry_run_done", time.time(), json.dumps(result, ensure_ascii=False), request_id)
    )
    con.commit()
    con.close()
    return {"ok": True, "request_id": request_id, "result": result}

def list_requests():
    init_db()
    con = sqlite3.connect(DB)
    cur = con.cursor()
    rows = cur.execute("SELECT request_id, action, status, created_at FROM workspace_requests ORDER BY created_at DESC LIMIT 20").fetchall()
    con.close()
    return {"version": "Wuchang-Workspace-RequestList-v1", "requests": [
        {"request_id": r[0], "action": r[1], "status": r[2], "created_at": r[3]} for r in rows
    ]}
