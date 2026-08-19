#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RANK = {"PASS": 0, "INFO": 1, "WARN": 2, "HOLD": 3, "BLOCK": 4}
_READONLY_SQL_AUDIT = {
    "query_count": 0,
    "mutation_count": 0,
    "transaction_read_only_confirmed": False,
    "queries": [],
}
_ACTIVE_ALERTS_READONLY_QUERY = """
    SELECT COALESCE(jsonb_agg(to_jsonb(a)), '[]'::jsonb)
    FROM (
      SELECT id, run_id, event_type, alert_level, title, summary,
             evidence_ref, reverse_refs, affected_paths
      FROM d8_active_possible_alerts
      ORDER BY created_at
    ) a;
    """


def normalize_sql(sql: str) -> str:
    return " ".join(sql.split())


_READONLY_SQL_ALLOWLIST_SHA256 = {
    hashlib.sha256(normalize_sql(_ACTIVE_ALERTS_READONLY_QUERY).encode("utf-8")).hexdigest()
}


def run_psql(sql: str) -> str:
    cmd = [
        "docker",
        "compose",
        "--env-file",
        ".env.d8.local",
        "-f",
        "compose.d8.yml",
        "exec",
        "-T",
        "d8_db",
        "psql",
        "-U",
        "taiji",
        "-d",
        "taiji_d8",
        "-At",
        "-c",
        sql,
    ]
    return subprocess.check_output(cmd, cwd=ROOT, text=True).strip()


def ensure_readonly_sql(sql: str) -> None:
    forbidden = r"(?is)\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|CALL|DO|COPY|SET|RESET|PREPARE|EXECUTE|DEALLOCATE|BEGIN|START\s+TRANSACTION|COMMIT|ROLLBACK|SAVEPOINT|RELEASE)\b"
    if re.search(forbidden, sql):
        raise ValueError("SQL mutation is forbidden in read-only preflight")
    normalized = normalize_sql(sql)
    query_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    if query_hash not in _READONLY_SQL_ALLOWLIST_SHA256:
        raise ValueError("SQL is not in the read-only preflight allowlist")


def run_psql_readonly(sql: str) -> str:
    ensure_readonly_sql(sql)
    guarded_sql = (
        "SELECT current_setting('transaction_read_only');\n"
        "SELECT current_setting('default_transaction_read_only');\n"
        "SELECT pg_current_xact_id_if_assigned() IS NULL;\n"
        + sql
        + "\nSELECT pg_current_xact_id_if_assigned() IS NULL;"
    )
    containers = subprocess.check_output(
        ["docker", "ps", "--filter", "label=com.docker.compose.service=d8_db", "--format", "{{.Names}}"],
        cwd=ROOT, text=True,
    ).splitlines()
    if len(containers) != 1:
        raise RuntimeError("exactly one D8 database container is required for read-only preflight")
    cmd = [
        "docker",
        "exec",
        "-e",
        "PGOPTIONS=-c default_transaction_read_only=on",
        containers[0],
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        "taiji",
        "-d",
        "taiji_d8",
        "-At",
        "-c",
        guarded_sql,
    ]
    lines = subprocess.check_output(cmd, cwd=ROOT, text=True).splitlines()
    if len(lines) < 5 or lines[0].strip() != "on" or lines[1].strip() != "on":
        raise RuntimeError("database read-only protection is not active")
    if lines[2].strip() != "t" or lines[-1].strip() != "t":
        raise RuntimeError("read-only query assigned a transaction id")
    _READONLY_SQL_AUDIT["query_count"] += 1
    _READONLY_SQL_AUDIT["transaction_read_only_confirmed"] = True
    _READONLY_SQL_AUDIT["xid_assigned"] = False
    _READONLY_SQL_AUDIT["queries"].append({
        "statement_class": "SELECT",
        "sql_sha256": hashlib.sha256(normalize_sql(sql).encode("utf-8")).hexdigest(),
    })
    return "\n".join(lines[3:-1]).strip()


def reset_readonly_sql_audit() -> None:
    _READONLY_SQL_AUDIT.update({
        "query_count": 0,
        "mutation_count": 0,
        "transaction_read_only_confirmed": False,
        "xid_assigned": False,
        "queries": [],
    })


def readonly_sql_audit() -> dict:
    return json.loads(canonical_json(_READONLY_SQL_AUDIT))


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def load_alerts(*, read_only: bool = False) -> list[dict]:
    query = _ACTIVE_ALERTS_READONLY_QUERY
    raw = run_psql_readonly(query) if read_only else run_psql(query)
    return json.loads(raw or "[]")


def matches(alert: dict, scope: dict) -> bool:
    evidence = alert.get("evidence_ref") or {}
    alert_id = str(alert.get("event_type") or "")
    text = " ".join(
        str(x).lower()
        for x in [
            alert.get("event_type"),
            alert.get("title"),
            alert.get("summary"),
            evidence.get("pattern"),
            evidence.get("possible_error"),
            evidence.get("correct_action"),
            json.dumps(alert.get("reverse_refs") or [], ensure_ascii=False),
            json.dumps(alert.get("affected_paths") or [], ensure_ascii=False),
        ]
    )
    if scope.get("human_review_required") and alert_id == "D8_ALERT_HUMAN_REVIEW_REQUIRED":
        return True
    if scope.get("pre_existing_non_d8_diff") and alert_id == "D8_ALERT_PRE_EXISTING_NON_D8_DIFF":
        return True
    if (
        "rerun_ingestion" in str(scope.get("request", "")).lower()
        and alert_id == "D8_ALERT_PHASE1_BASELINE_READY"
    ):
        return True
    if scope.get("d8_memory_count") and alert_id == "D8_ALERT_PHASE1_BASELINE_READY":
        return True
    if scope.get("file") and str(scope["file"]).lower() in text and "pre-existing" in text:
        return alert_id == "D8_ALERT_PRE_EXISTING_NON_D8_DIFF"
    return False


def decide(matched: list[dict]) -> tuple[str, str]:
    if not matched:
        return "PASS", "no active possible_alert matched task scope"
    decision = max((a.get("alert_level", "INFO") for a in matched), key=lambda level: RANK.get(level, 0))
    return decision, "matched active possible_alerts: " + ", ".join(a.get("event_type", "") for a in matched)


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_payload(payload: dict) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def evaluation_insert_projection(candidate: dict) -> dict:
    """Return the exact logical row the persistence phase would insert."""
    return {
        "run_id": candidate["run_id"],
        "task_name": candidate["task_name"],
        "task_scope": json.loads(canonical_json(candidate["task_scope"])),
        "matched_alerts": json.loads(canonical_json(candidate["matched_alerts"])),
        "decision": candidate["decision"],
        "reason": candidate["reason"],
        "executable": False,
        "pollution_guard": True,
    }


def evaluation_insert_projection_sha256(candidate: dict) -> str:
    return sha256_payload(evaluation_insert_projection(candidate))


def prepare_evaluation(
    run_id: str,
    task_name: str,
    scope: dict,
    matched: list[dict],
    decision: str,
    reason: str,
) -> dict:
    created_at = dt.datetime.now(dt.UTC)
    candidate = {
        "schema_version": "D8_GUARD_EVALUATION_CANDIDATE_V1",
        "run_id": run_id,
        "task_name": task_name,
        "task_scope": json.loads(canonical_json(scope)),
        "matched_alerts": [
            {
                "id": alert.get("id"),
                "alert_id": alert.get("event_type"),
                "alert_level": alert.get("alert_level"),
            }
            for alert in matched
        ],
        "decision": decision,
        "reason": reason,
        "executable": False,
        "pollution_guard": True,
        "authority": {
            "decision_authority": "D8_TOTAL_FIELD_GUARD",
            "persistence_authority": False,
            "production_authority": False,
        },
        "risk_gates": {
            "decision": decision,
            "matched_alert_count": len(matched),
            "allow_persistence": False,
        },
        "evidence_refs": [
            {
                "alert_id": alert.get("event_type"),
                "evidence_ref_sha256": sha256_payload({"value": alert.get("evidence_ref") or {}}),
                "reverse_refs_sha256": sha256_payload({"value": alert.get("reverse_refs") or []}),
            }
            for alert in matched
        ],
        "evaluation_payload": {
            "scope": json.loads(canonical_json(scope)),
            "matched_alert_ids": [alert.get("event_type") for alert in matched],
            "decision": decision,
            "reason": reason,
        },
        "envelope": {
            "protocol": "W7TP_D8_READ_ONLY_PREFLIGHT_V1",
            "ttl_seconds": 300,
            "nonce": uuid.uuid4().hex,
            "created_at": created_at.isoformat(),
            "verifier": "D8_GUARD_EVALUATION_VALIDATOR_V1",
            "candidate_sha256": "",
        },
    }
    candidate["envelope"]["candidate_sha256"] = sha256_payload(candidate)
    return candidate


def validate_evaluation(candidate: dict, *, now: dt.datetime | None = None) -> dict:
    required = {
        "schema_version", "run_id", "task_name", "task_scope", "matched_alerts",
        "decision", "reason", "executable", "pollution_guard", "authority",
        "risk_gates", "evidence_refs", "evaluation_payload", "envelope",
    }
    envelope = candidate.get("envelope") if isinstance(candidate.get("envelope"), dict) else {}
    hash_input = json.loads(canonical_json(candidate))
    claimed_hash = str(hash_input.get("envelope", {}).get("candidate_sha256") or "")
    hash_input["envelope"]["candidate_sha256"] = ""
    matched_alerts = candidate.get("matched_alerts") if isinstance(candidate.get("matched_alerts"), list) else []
    expected_payload = {
        "scope": candidate.get("task_scope"),
        "matched_alert_ids": [item.get("alert_id") for item in matched_alerts],
        "decision": candidate.get("decision"),
        "reason": candidate.get("reason"),
    }
    try:
        insert_projection = evaluation_insert_projection(candidate)
    except (KeyError, TypeError, ValueError):
        insert_projection = {}
    checks = {
        "schema": candidate.get("schema_version") == "D8_GUARD_EVALUATION_CANDIDATE_V1",
        "required_fields": required.issubset(candidate),
        "canonicalization": canonical_json(candidate) == canonical_json(json.loads(canonical_json(candidate))),
        "hash": bool(re.fullmatch(r"[0-9a-f]{64}", claimed_hash)) and claimed_hash == sha256_payload(hash_input),
        "envelope": isinstance(envelope, dict),
        "ttl": isinstance(envelope.get("ttl_seconds"), int) and 0 < envelope["ttl_seconds"] <= 300,
        "nonce": bool(re.fullmatch(r"[0-9a-f]{32}", str(envelope.get("nonce") or ""))),
        "protocol": envelope.get("protocol") == "W7TP_D8_READ_ONLY_PREFLIGHT_V1",
        "verifier": envelope.get("verifier") == "D8_GUARD_EVALUATION_VALIDATOR_V1",
        "authority": candidate.get("authority", {}).get("persistence_authority") is False and candidate.get("authority", {}).get("production_authority") is False,
        "risk_gates": candidate.get("risk_gates", {}).get("allow_persistence") is False and candidate.get("risk_gates", {}).get("decision") == candidate.get("decision"),
        "evidence_refs": isinstance(candidate.get("evidence_refs"), list),
        "evaluation_payload": candidate.get("evaluation_payload") == expected_payload,
        "insert_projection": bool(insert_projection)
        and insert_projection.get("run_id") == candidate.get("run_id")
        and insert_projection.get("task_name") == candidate.get("task_name")
        and insert_projection.get("task_scope") == candidate.get("task_scope")
        and insert_projection.get("matched_alerts") == matched_alerts
        and insert_projection.get("decision") == candidate.get("decision")
        and insert_projection.get("reason") == candidate.get("reason")
        and candidate.get("executable") is False
        and candidate.get("pollution_guard") is True
        and insert_projection.get("executable") is False
        and insert_projection.get("pollution_guard") is True,
    }
    try:
        created_at = dt.datetime.fromisoformat(str(envelope.get("created_at")))
        current = now or dt.datetime.now(dt.UTC)
        checks["ttl"] = checks["ttl"] and created_at <= current <= created_at + dt.timedelta(seconds=envelope["ttl_seconds"])
    except (TypeError, ValueError):
        checks["ttl"] = False
    return {"state": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def persist_evaluation(candidate: dict) -> None:
    validation = validate_evaluation(candidate)
    if validation["state"] != "PASS":
        raise ValueError("evaluation candidate validation failed before persistence")
    _insert_evaluation(evaluation_insert_projection(candidate))


def _insert_evaluation(projection: dict) -> None:
    sql = f"""
    INSERT INTO d8_guard_evaluations (
      run_id, task_name, task_scope, matched_alerts, decision, reason,
      executable, pollution_guard
    )
    VALUES (
      {sql_literal(projection["run_id"])},
      {sql_literal(projection["task_name"])},
      {sql_literal(canonical_json(projection["task_scope"]))}::jsonb,
      {sql_literal(canonical_json(projection["matched_alerts"]))}::jsonb,
      {sql_literal(projection["decision"])},
      {sql_literal(projection["reason"])},
      {str(projection["executable"]).lower()},
      {str(projection["pollution_guard"]).lower()}
    );
    """
    run_psql(sql)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate task scope against D8 possible alerts")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--scope-json", required=True)
    args = parser.parse_args()

    scope = json.loads(args.scope_json)
    alerts = load_alerts()
    matched = [alert for alert in alerts if matches(alert, scope)]
    decision, reason = decide(matched)
    candidate = prepare_evaluation(args.run_id, args.task_name, scope, matched, decision, reason)
    validation = validate_evaluation(candidate)
    if validation["state"] != "PASS":
        raise ValueError("evaluation candidate validation failed")
    persist_evaluation(candidate)
    summary = {
        "run_id": args.run_id,
        "task_name": args.task_name,
        "decision": decision,
        "reason": reason,
        "matched_alerts": [
            {"alert_id": a.get("event_type"), "alert_level": a.get("alert_level")}
            for a in matched
        ],
        "executable": False,
        "pollution_guard": True,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
