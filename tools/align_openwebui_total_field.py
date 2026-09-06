#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(
    os.getenv("TAIJI_PROJECT_ROOT", "/home/taiji_admin/Taiji_Hub")
).resolve()
DEFAULT_DB_PATH = Path(
    os.getenv(
        "OPENWEBUI_DB_PATH",
        "/home/taiji_admin/wuchang_8_0_core/open-webui/backend/data/webui.db",
    )
)
CONTRACT_PATH = (
    PROJECT_ROOT / "configs/total_field/w7tp_8dadi_d6_contract_v2_3.json"
)
TOTAL_FIELD_ENDPOINT = "http://127.0.0.1:8081/v1"
TOTAL_FIELD_MODEL = "w7tp-total-field-google"
VISIBLE_MODEL_ID = "w7tp-cloud"
LEGACY_GATE0_FUNCTION_ID = "w7tp_cb1_v0_4_missing_condition_qa"
LEGACY_ENDPOINT_PORTS = (":8787/", ":9108/")
LEGACY_SYSTEM_MARKERS = (
    "INFO_REQUIRED",
    "MISSING_CONTEXT",
    "latest command output",
    "D1_IDENTITY",
    "7D/D8",
    "Gate-0",
    "GATE0",
)


def _load_contract() -> dict[str, Any]:
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if data.get("schema_id") != "W7TP_8DADI_D6_GENERATIVE_TRANSMISSION_CONTRACT_V2_3":
        raise RuntimeError("HOLD_D6_CONTRACT_SCHEMA_MISMATCH")
    if data.get("primary_decision_engine") != "8D_ADI":
        raise RuntimeError("HOLD_D6_PRIMARY_ENGINE_MISMATCH")
    if data.get("not_d6", {}).get("cloud_to_local_model_failover") is not True:
        raise RuntimeError("HOLD_D6_INFERENCE_BOUNDARY_MISSING")
    prompt = data.get("openwebui_system_prompt_zh_tw")
    if not isinstance(prompt, str) or "D6 只指" not in prompt:
        raise RuntimeError("HOLD_D6_OPENWEBUI_PROMPT_MISSING")
    return data


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None


def _uses_visible_model(chat_data: dict[str, Any]) -> bool:
    models = chat_data.get("models")
    return isinstance(models, list) and VISIBLE_MODEL_ID in models


def _has_legacy_system(system: Any) -> bool:
    return isinstance(system, str) and any(
        marker.casefold() in system.casefold() for marker in LEGACY_SYSTEM_MARKERS
    )


def _message_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    output = message.get("output")
    return output if isinstance(output, str) else ""


def _is_legacy_assistant_message(
    message: Any,
    alignment_cutoff: int,
) -> bool:
    del alignment_cutoff
    if not isinstance(message, dict) or message.get("role") != "assistant":
        return False
    content = _message_content(message)
    return _has_legacy_system(content)


def _remove_message_ids(
    messages: list[dict[str, Any]],
    remove_ids: set[str],
) -> list[dict[str, Any]]:
    original = {
        str(message.get("id")): message
        for message in messages
        if isinstance(message, dict) and message.get("id")
    }
    for remove_id in remove_ids:
        removed = original.get(remove_id)
        if not removed:
            continue
        parent_id = removed.get("parentId")
        children = [
            str(child)
            for child in (removed.get("childrenIds") or [])
            if str(child) not in remove_ids
        ]
        parent = original.get(str(parent_id)) if parent_id else None
        if parent and str(parent.get("id")) not in remove_ids:
            parent_children = [
                str(child)
                for child in (parent.get("childrenIds") or [])
                if str(child) != remove_id and str(child) not in remove_ids
            ]
            for child in children:
                if child not in parent_children:
                    parent_children.append(child)
            parent["childrenIds"] = parent_children
        for child_id in children:
            child = original.get(child_id)
            if child:
                child["parentId"] = parent_id
    return [
        message
        for message in messages
        if isinstance(message, dict) and str(message.get("id")) not in remove_ids
    ]


def _remove_legacy_assistant_messages(
    chat_data: dict[str, Any],
    alignment_cutoff: int,
) -> int:
    top_messages = chat_data.get("messages")
    history = chat_data.get("history")
    history_messages = (
        history.get("messages")
        if isinstance(history, dict) and isinstance(history.get("messages"), dict)
        else {}
    )
    candidates: dict[str, dict[str, Any]] = {}
    if isinstance(top_messages, list):
        for message in top_messages:
            if isinstance(message, dict) and message.get("id"):
                candidates[str(message["id"])] = message
    for message_id, message in history_messages.items():
        if isinstance(message, dict):
            candidates[str(message_id)] = message
    remove_ids = {
        message_id
        for message_id, message in candidates.items()
        if _is_legacy_assistant_message(message, alignment_cutoff)
    }
    if not remove_ids:
        return 0

    if isinstance(top_messages, list):
        chat_data["messages"] = _remove_message_ids(top_messages, remove_ids)
    if isinstance(history, dict):
        history_list = [
            message
            for message in history_messages.values()
            if isinstance(message, dict)
        ]
        kept_history = _remove_message_ids(history_list, remove_ids)
        history["messages"] = {
            str(message["id"]): message
            for message in kept_history
            if message.get("id")
        }
        current_id = str(history.get("currentId") or "")
        if current_id in remove_ids:
            kept_children = [
                str(child_id)
                for child_id in (candidates[current_id].get("childrenIds") or [])
                if str(child_id) in history["messages"]
            ]
            if kept_children:
                history["currentId"] = kept_children[-1]
            elif history["messages"]:
                parent_id = candidates[current_id].get("parentId")
                while parent_id and str(parent_id) in remove_ids:
                    parent_id = candidates[str(parent_id)].get("parentId")
                if parent_id and str(parent_id) in history["messages"]:
                    history["currentId"] = str(parent_id)
                else:
                    history["currentId"] = next(reversed(history["messages"]))
            else:
                history["currentId"] = None
    return len(remove_ids)


def _config_changes(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    changed = 0
    openai = data.get("openai")
    if not isinstance(openai, dict):
        return data, changed
    urls = openai.get("api_base_urls")
    configs = openai.get("api_configs")
    if not isinstance(urls, list):
        return data, changed
    if not isinstance(configs, dict):
        configs = {}
        openai["api_configs"] = configs

    for index, value in enumerate(urls):
        url = str(value or "")
        config = configs.get(str(index))
        if not isinstance(config, dict):
            config = {}
            configs[str(index)] = config
        if ":8787/" in url:
            if urls[index] != TOTAL_FIELD_ENDPOINT:
                urls[index] = TOTAL_FIELD_ENDPOINT
                changed += 1
            if config.get("enable") is not True:
                config["enable"] = True
                changed += 1
        elif ":9108/" in url and config.get("enable") is not False:
            config["enable"] = False
            changed += 1
    return data, changed


def _config_columns(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(config)").fetchall()
    }


def _read_openai_config(
    connection: sqlite3.Connection,
) -> tuple[dict[str, Any], str]:
    """同時支援 0.8 單列 JSON 與 0.11 按鍵儲存，不讀出 API 金鑰。"""
    columns = _config_columns(connection)
    if {"key", "value"}.issubset(columns):
        rows = dict(
            connection.execute(
                "SELECT key, value FROM config WHERE key IN (?, ?)",
                ("openai.api_base_urls", "openai.api_configs"),
            ).fetchall()
        )
        return {
            "openai": {
                "api_base_urls": _json_value(rows.get("openai.api_base_urls")),
                "api_configs": _json_value(rows.get("openai.api_configs")),
            }
        }, "KEY_VALUE"
    if {"id", "data"}.issubset(columns):
        row = connection.execute(
            "SELECT data FROM config ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return (_json_object(row[0]) if row else {}), "LEGACY_JSON"
    raise RuntimeError("HOLD_OPENWEBUI_CONFIG_SCHEMA_UNSUPPORTED")


def _validate_openai_config_shape(data: dict[str, Any]) -> None:
    openai = data.get("openai")
    if not isinstance(openai, dict):
        raise RuntimeError("HOLD_OPENWEBUI_OPENAI_CONFIG_MALFORMED")
    if not isinstance(openai.get("api_base_urls"), list):
        raise RuntimeError("HOLD_OPENWEBUI_OPENAI_CONFIG_MALFORMED")
    if not isinstance(openai.get("api_configs"), dict):
        raise RuntimeError("HOLD_OPENWEBUI_OPENAI_CONFIG_MALFORMED")


def _inspect(
    connection: sqlite3.Connection,
    prompt: str,
    model_profile: dict[str, Any],
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "endpoint_aligned": False,
        "inactive_unknown_9108": True,
        "model_aligned": False,
        "gate0_inactive": True,
        "legacy_chat_count": 0,
        "legacy_assistant_message_count": 0,
    }
    alignment_cutoff = 0
    data, _ = _read_openai_config(connection)
    if data:
        openai = data.get("openai") if isinstance(data.get("openai"), dict) else {}
        urls = openai.get("api_base_urls") if isinstance(openai, dict) else []
        configs = openai.get("api_configs") if isinstance(openai, dict) else {}
        state["endpoint_aligned"] = TOTAL_FIELD_ENDPOINT in (urls or [])
        for index, url in enumerate(urls or []):
            if ":9108/" in str(url):
                config = configs.get(str(index), {}) if isinstance(configs, dict) else {}
                if not isinstance(config, dict) or config.get("enable") is not False:
                    state["inactive_unknown_9108"] = False

    row = connection.execute(
        "SELECT base_model_id, params, is_active, updated_at FROM model WHERE id = ?",
        (VISIBLE_MODEL_ID,),
    ).fetchone()
    if row:
        params = _json_object(row[1])
        state["model_aligned"] = (
            row[0] == TOTAL_FIELD_MODEL
            and params.get("system") == prompt
            and params.get("temperature") == model_profile["temperature"]
            and params.get("top_p") == model_profile["top_p"]
            and params.get("stream_response") is model_profile["stream_response"]
            and bool(row[2])
        )
        alignment_cutoff = int(row[3] or 0)

    row = connection.execute(
        "SELECT is_active, is_global FROM function WHERE id = ?",
        (LEGACY_GATE0_FUNCTION_ID,),
    ).fetchone()
    if row:
        state["gate0_inactive"] = not bool(row[0]) and not bool(row[1])

    for (raw_chat,) in connection.execute("SELECT chat FROM chat"):
        chat_data = _json_object(raw_chat)
        if (
            _uses_visible_model(chat_data)
            and chat_data.get("system") != prompt
            and _has_legacy_system(chat_data.get("system"))
        ):
            state["legacy_chat_count"] += 1
        candidates = []
        if isinstance(chat_data.get("messages"), list):
            candidates.extend(chat_data["messages"])
        history = chat_data.get("history")
        if isinstance(history, dict) and isinstance(history.get("messages"), dict):
            candidates.extend(history["messages"].values())
        message_ids = {
            str(message.get("id"))
            for message in candidates
            if isinstance(message, dict)
            and message.get("id")
            and _is_legacy_assistant_message(message, alignment_cutoff)
        }
        state["legacy_assistant_message_count"] += len(message_ids)
    state["aligned"] = (
        state["endpoint_aligned"]
        and state["inactive_unknown_9108"]
        and state["model_aligned"]
        and state["gate0_inactive"]
        and state["legacy_chat_count"] == 0
        and state["legacy_assistant_message_count"] == 0
    )
    return state


def _backup_database(db_path: Path) -> Path:
    backup_dir = db_path.parent / "rollback"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / (
        f"webui.before_d6_alignment.{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.db"
    )
    source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    target = sqlite3.connect(backup_path)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    backup_path.chmod(0o600)
    return backup_path


def _apply(
    connection: sqlite3.Connection,
    prompt: str,
    model_profile: dict[str, Any],
) -> dict[str, int]:
    counts = {
        "config_field_changes": 0,
        "model_rows": 0,
        "gate0_rows": 0,
        "chat_rows": 0,
        "assistant_message_rows": 0,
        "assistant_messages_removed": 0,
    }
    now = int(time.time())
    data, config_mode = _read_openai_config(connection)
    if data:
        data, changes = _config_changes(data)
        if changes:
            if config_mode == "KEY_VALUE":
                openai = data["openai"]
                for key, value in (
                    ("openai.api_base_urls", openai["api_base_urls"]),
                    ("openai.api_configs", openai["api_configs"]),
                ):
                    connection.execute(
                        "UPDATE config SET value = ?, updated_at = CURRENT_TIMESTAMP "
                        "WHERE key = ?",
                        (json.dumps(value, ensure_ascii=False, separators=(",", ":")), key),
                    )
            else:
                row = connection.execute(
                    "SELECT id FROM config ORDER BY id DESC LIMIT 1"
                ).fetchone()
                connection.execute(
                    "UPDATE config SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (
                        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                        row[0],
                    ),
                )
            counts["config_field_changes"] = changes

    row = connection.execute(
        "SELECT params, base_model_id FROM model WHERE id = ?",
        (VISIBLE_MODEL_ID,),
    ).fetchone()
    if row:
        params = _json_object(row[0])
        desired_params = {
            "system": prompt,
            "temperature": model_profile["temperature"],
            "top_p": model_profile["top_p"],
            "stream_response": model_profile["stream_response"],
        }
        if row[1] != TOTAL_FIELD_MODEL or any(
            params.get(key) != value for key, value in desired_params.items()
        ):
            params.update(desired_params)
            connection.execute(
                "UPDATE model SET base_model_id = ?, params = ?, updated_at = ? WHERE id = ?",
                (
                    TOTAL_FIELD_MODEL,
                    json.dumps(params, ensure_ascii=False, separators=(",", ":")),
                    now,
                    VISIBLE_MODEL_ID,
                ),
            )
            counts["model_rows"] = 1

    cursor = connection.execute(
        "UPDATE function SET is_active = 0, is_global = 0, updated_at = ? "
        "WHERE id = ? AND (is_active != 0 OR is_global != 0)",
        (now, LEGACY_GATE0_FUNCTION_ID),
    )
    counts["gate0_rows"] = max(cursor.rowcount, 0)

    model_row = connection.execute(
        "SELECT updated_at FROM model WHERE id = ?",
        (VISIBLE_MODEL_ID,),
    ).fetchone()
    alignment_cutoff = int(model_row[0] or now) if model_row else now
    rows = connection.execute("SELECT id, chat FROM chat").fetchall()
    for chat_id, raw_chat in rows:
        chat_data = _json_object(raw_chat)
        changed = False
        if (
            _uses_visible_model(chat_data)
            and
            chat_data.get("system") != prompt
            and _has_legacy_system(chat_data.get("system"))
        ):
            chat_data["system"] = prompt
            counts["chat_rows"] += 1
            changed = True
        removed = _remove_legacy_assistant_messages(chat_data, alignment_cutoff)
        if removed:
            counts["assistant_message_rows"] += 1
            counts["assistant_messages_removed"] += removed
            changed = True
        if changed:
            connection.execute(
                "UPDATE chat SET chat = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (
                    json.dumps(chat_data, ensure_ascii=False, separators=(",", ":")),
                    chat_id,
                ),
            )
    return counts


def align(db_path: Path, apply: bool) -> dict[str, Any]:
    contract = _load_contract()
    prompt = str(contract["openwebui_system_prompt_zh_tw"])
    persona_overlay = contract.get("openwebui_persona_overlay_zh_tw")
    if not isinstance(persona_overlay, str) or not persona_overlay.strip():
        raise RuntimeError("HOLD_OPENWEBUI_PERSONA_OVERLAY_MISSING")
    prompt = f"{prompt}\n\n{persona_overlay.strip()}"
    model_profile = contract.get("model_runtime_profile")
    if not isinstance(model_profile, dict):
        raise RuntimeError("HOLD_MODEL_RUNTIME_PROFILE_MISSING")
    if not db_path.is_file():
        raise RuntimeError(f"HOLD_OPENWEBUI_DB_NOT_FOUND:{db_path}")

    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        before = _inspect(connection, prompt, model_profile)
    finally:
        connection.close()

    result: dict[str, Any] = {
        "state": "ALIGNED" if before["aligned"] else "DRIFT_OBSERVED",
        "mode": "APPLY" if apply else "CHECK",
        "before": before,
        "files_deleted": 0,
        "secrets_printed": False,
    }
    if not apply or before["aligned"]:
        result["after"] = before
        return result

    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        data, _ = _read_openai_config(connection)
        _validate_openai_config_shape(data)
    finally:
        connection.close()

    backup_path = _backup_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        counts = _apply(connection, prompt, model_profile)
        connection.commit()
        after = _inspect(connection, prompt, model_profile)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    result.update(
        {
            "state": "ALIGNED" if after["aligned"] else "HOLD_ALIGNMENT_INCOMPLETE",
            "backup_path": str(backup_path),
            "changes": counts,
            "after": after,
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="對齊 OpenWebUI 至既有總場入口，並停用精確識別的舊 Gate-0 污染。"
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = align(args.db.resolve(), apply=args.apply)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("state") == "ALIGNED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
