from __future__ import annotations

import json
import sqlite3
import stat
import pytest
from pathlib import Path

from tools.align_openwebui_total_field import (
    LEGACY_GATE0_FUNCTION_ID,
    TOTAL_FIELD_ENDPOINT,
    TOTAL_FIELD_MODEL,
    VISIBLE_MODEL_ID,
    align,
)


def _create_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE config (
            id INTEGER PRIMARY KEY,
            data JSON NOT NULL,
            version INTEGER NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE model (
            id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            base_model_id TEXT,
            name TEXT NOT NULL,
            meta TEXT NOT NULL,
            params TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT 1
        );
        CREATE TABLE function (
            id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            meta TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            valves TEXT,
            is_active INTEGER NOT NULL,
            is_global INTEGER NOT NULL
        );
        CREATE TABLE chat (
            id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            share_id TEXT,
            archived INTEGER NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            chat JSON,
            pinned BOOLEAN,
            meta JSON NOT NULL DEFAULT '{}',
            folder_id TEXT
        );
        """
    )
    config = {
        "openai": {
            "api_base_urls": [
                "http://localhost:8787/v1",
                "http://127.0.0.1:9108/v1",
            ],
            "api_keys": ["opaque-secret-a", "opaque-secret-b"],
            "api_configs": {
                "0": {"enable": True, "auth_type": "bearer"},
                "1": {"enable": True, "auth_type": "bearer"},
            },
        }
    }
    connection.execute(
        "INSERT INTO config (id, data, version) VALUES (1, ?, 0)",
        (json.dumps(config),),
    )
    connection.execute(
        "INSERT INTO model VALUES (?, ?, ?, ?, ?, ?, 0, 0, 1)",
        (
            VISIBLE_MODEL_ID,
            "founder",
            None,
            "W7TP Cloud",
            "{}",
            json.dumps({"system": "STATE=INFO_REQUIRED latest command output"}),
        ),
    )
    connection.execute(
        "INSERT INTO function VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, 1, 1)",
        (
            LEGACY_GATE0_FUNCTION_ID,
            "founder",
            "Gate-0",
            "filter",
            "preserved historical source",
            "{}",
            "{}",
        ),
    )
    chat_data = {
        "models": [VISIBLE_MODEL_ID],
        "system": "GATE0_FILTER_ACTIVE=True MISSING_CONTEXT",
        "messages": [
            {
                "id": "m1",
                "role": "user",
                "content": "保留使用者訊息",
                "parentId": None,
                "childrenIds": ["m2"],
                "timestamp": 1,
            },
            {
                "id": "m2",
                "role": "assistant",
                "content": "STATE=INFO_REQUIRED",
                "parentId": "m1",
                "childrenIds": ["m3"],
                "model": VISIBLE_MODEL_ID,
                "timestamp": 1,
            },
            {
                "id": "m3",
                "role": "assistant",
                "content": "這是應保留的舊助理內容",
                "parentId": "m2",
                "childrenIds": [],
                "model": VISIBLE_MODEL_ID,
                "timestamp": 1,
            },
        ],
        "history": {
            "currentId": "m2",
            "messages": {
                "m1": {
                    "id": "m1",
                    "role": "user",
                    "content": "保留使用者訊息",
                    "parentId": None,
                    "childrenIds": ["m2"],
                    "timestamp": 1,
                },
                "m2": {
                    "id": "m2",
                    "role": "assistant",
                    "content": "STATE=INFO_REQUIRED",
                    "parentId": "m1",
                    "childrenIds": ["m3"],
                    "model": VISIBLE_MODEL_ID,
                    "timestamp": 1,
                },
                "m3": {
                    "id": "m3",
                    "role": "assistant",
                    "content": "這是應保留的舊助理內容",
                    "parentId": "m2",
                    "childrenIds": [],
                    "model": VISIBLE_MODEL_ID,
                    "timestamp": 1,
                },
            },
        },
    }
    connection.execute(
        "INSERT INTO chat VALUES (?, ?, ?, NULL, 0, CURRENT_TIMESTAMP, "
        "CURRENT_TIMESTAMP, ?, 0, '{}', NULL)",
        ("chat-1", "founder", "test", json.dumps(chat_data)),
    )
    connection.commit()
    connection.close()


def test_alignment_snapshots_then_repairs_only_known_drift(tmp_path: Path) -> None:
    db_path = tmp_path / "webui.db"
    _create_database(db_path)

    result = align(db_path, apply=True)

    assert result["state"] == "ALIGNED"
    assert result["files_deleted"] == 0
    assert result["changes"]["gate0_rows"] == 1
    assert result["changes"]["chat_rows"] == 1
    assert result["changes"]["assistant_messages_removed"] == 1
    assert "opaque-secret" not in json.dumps(result)

    backup_path = Path(result["backup_path"])
    assert backup_path.is_file()
    assert stat.S_IMODE(backup_path.stat().st_mode) == 0o600

    connection = sqlite3.connect(db_path)
    config = json.loads(connection.execute("SELECT data FROM config").fetchone()[0])
    assert config["openai"]["api_base_urls"][0] == TOTAL_FIELD_ENDPOINT
    assert config["openai"]["api_configs"]["1"]["enable"] is False
    assert config["openai"]["api_keys"] == ["opaque-secret-a", "opaque-secret-b"]
    model = connection.execute(
        "SELECT base_model_id, params FROM model WHERE id = ?",
        (VISIBLE_MODEL_ID,),
    ).fetchone()
    assert model[0] == TOTAL_FIELD_MODEL
    model_params = json.loads(model[1])
    assert "D6 只指" in model_params["system"]
    assert model_params["temperature"] == 0.2
    assert model_params["top_p"] == 0.9
    assert model_params["stream_response"] is False
    function = connection.execute(
        "SELECT is_active, is_global, content FROM function WHERE id = ?",
        (LEGACY_GATE0_FUNCTION_ID,),
    ).fetchone()
    assert function == (0, 0, "preserved historical source")
    chat = json.loads(connection.execute("SELECT chat FROM chat").fetchone()[0])
    assert [message["id"] for message in chat["messages"]] == ["m1", "m3"]
    assert chat["messages"][0]["content"] == "保留使用者訊息"
    assert chat["messages"][0]["childrenIds"] == ["m3"]
    assert chat["messages"][1]["parentId"] == "m1"
    assert list(chat["history"]["messages"]) == ["m1", "m3"]
    assert chat["history"]["messages"]["m1"]["content"] == "保留使用者訊息"
    assert chat["history"]["currentId"] == "m3"
    assert "D6 只指" in chat["system"]
    connection.close()

    second = align(db_path, apply=True)
    assert second["state"] == "ALIGNED"
    assert "backup_path" not in second


def test_alignment_supports_openwebui_011_key_value_config(tmp_path: Path) -> None:
    db_path = tmp_path / "webui-011.db"
    _create_database(db_path)
    connection = sqlite3.connect(db_path)
    legacy = json.loads(connection.execute("SELECT data FROM config").fetchone()[0])
    connection.execute("DROP TABLE config")
    connection.execute(
        "CREATE TABLE config (key TEXT PRIMARY KEY, value JSON, updated_at DATETIME)"
    )
    connection.execute(
        "INSERT INTO config VALUES (?, ?, CURRENT_TIMESTAMP)",
        ("openai.api_base_urls", json.dumps(legacy["openai"]["api_base_urls"])),
    )
    connection.execute(
        "INSERT INTO config VALUES (?, ?, CURRENT_TIMESTAMP)",
        ("openai.api_configs", json.dumps(legacy["openai"]["api_configs"])),
    )
    connection.execute(
        "INSERT INTO config VALUES (?, ?, CURRENT_TIMESTAMP)",
        ("openai.api_keys", json.dumps(legacy["openai"]["api_keys"])),
    )
    connection.commit()
    connection.close()

    result = align(db_path, apply=True)
    assert result["state"] == "ALIGNED"

    connection = sqlite3.connect(db_path)
    rows = dict(connection.execute("SELECT key, value FROM config").fetchall())
    assert json.loads(rows["openai.api_base_urls"])[0] == TOTAL_FIELD_ENDPOINT
    assert json.loads(rows["openai.api_configs"])["1"]["enable"] is False
    assert json.loads(rows["openai.api_keys"]) == [
        "opaque-secret-a",
        "opaque-secret-b",
    ]
    connection.close()


def test_malformed_openwebui_011_config_fails_closed_before_writes(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "webui-malformed-011.db"
    _create_database(db_path)
    connection = sqlite3.connect(db_path)
    legacy = json.loads(connection.execute("SELECT data FROM config").fetchone()[0])
    connection.execute("DROP TABLE config")
    connection.execute(
        "CREATE TABLE config (key TEXT PRIMARY KEY, value JSON, updated_at DATETIME)"
    )
    connection.execute(
        "INSERT INTO config VALUES (?, ?, CURRENT_TIMESTAMP)",
        ("openai.api_base_urls", "not-json"),
    )
    connection.execute(
        "INSERT INTO config VALUES (?, ?, CURRENT_TIMESTAMP)",
        ("openai.api_configs", json.dumps(legacy["openai"]["api_configs"])),
    )
    connection.commit()
    connection.close()
    before = db_path.read_bytes()

    with pytest.raises(RuntimeError, match="HOLD_OPENWEBUI_OPENAI_CONFIG_MALFORMED"):
        align(db_path, apply=True)

    assert db_path.read_bytes() == before
    assert not (db_path.parent / "rollback").exists()


def test_unknown_config_schema_fails_closed_before_writes(tmp_path: Path) -> None:
    db_path = tmp_path / "webui-unknown-config.db"
    _create_database(db_path)
    connection = sqlite3.connect(db_path)
    connection.execute("DROP TABLE config")
    connection.execute("CREATE TABLE config (name TEXT PRIMARY KEY, payload JSON)")
    connection.execute("INSERT INTO config VALUES (?, ?)", ("openai", "{}"))
    connection.commit()
    connection.close()
    before = db_path.read_bytes()

    with pytest.raises(RuntimeError, match="HOLD_OPENWEBUI_CONFIG_SCHEMA_UNSUPPORTED"):
        align(db_path, apply=True)

    assert db_path.read_bytes() == before
    assert not (db_path.parent / "rollback").exists()
