import json
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "w7tp_runtime_query_indexer.py"


def run_indexer(*args, check=True):
    proc = subprocess.run(
        [sys.executable, str(TOOL), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise AssertionError(f"command failed rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return proc


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def build_fixture_tree(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    write_json(
        src / "run_packet.json",
        {
            "run_id": "RUN_A",
            "created_at": "2026-07-02T00:00:00Z",
            "packet_id": "pkt_a",
            "packet_hash": "hash_a",
            "packet_type": "TEST_PACKET",
            "schema_ref": "schema/test",
            "cloud_authority": False,
            "local_authority": "discrete_state_core",
            "decision": "PASS",
            "execution_allowed": False,
            "evidence_ref": "evidence/ref/a",
            "seal_hash": "seal_a",
            "previous_seal_hash": "seal_prev",
        },
    )
    (src / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"run_id": "RUN_JSONL", "packet_hash": "hash_jsonl", "decision": "HOLD"}),
                "{bad json line",
                json.dumps({"gate_name": "postflight", "gate_value": "PASS"}),
            ]
        ),
        encoding="utf-8",
    )
    write_json(
        src / "dead_letter" / "dead_letter_record.json",
        {
            "packet_hash": "hash_a",
            "mailbox_ref": "usb://mailbox",
            "failure_reason": "missing evidence",
            "retry_policy": "manual",
            "status": "HOLD",
        },
    )
    write_json(
        src / "public_patent_claims.json",
        {
            "package_id": "PKG_A",
            "claim_no": "1",
            "claim_text": "A non-confidential synthetic claim.",
            "topic": "runtime index",
        },
    )
    (src / "gates.md").write_text("preflight=PASS\npostflight=HOLD\n", encoding="utf-8")
    (src / "secret.json").write_text('{"access_token":"SECRET_VALUE_SHOULD_NOT_APPEAR"}', encoding="utf-8")
    (src / "audio.wav").write_bytes(b"RIFF" + b"\x00" * 32)
    return src


def build_index(tmp_path: Path):
    src = build_fixture_tree(tmp_path)
    db = tmp_path / "index.sqlite3"
    report = tmp_path / "report.json"
    run_indexer("--write-index", "--rebuild", "--db", db, "--source-root", src, "--report-json", report)
    return src, db, report


def table_names(db: Path):
    con = sqlite3.connect(db)
    try:
        return {row[0] for row in con.execute("select name from sqlite_master where type='table'")}
    finally:
        con.close()


def index_names(db: Path):
    con = sqlite3.connect(db)
    try:
        return {row[0] for row in con.execute("select name from sqlite_master where type='index'")}
    finally:
        con.close()


def test_json_artifact_can_be_indexed_and_run_id_query(tmp_path):
    _, db, _ = build_index(tmp_path)
    out = run_indexer("--db", db, "--query", "run_id", "--value", "RUN_A").stdout
    data = json.loads(out)
    assert data["STATE"] == "PASS_RUNTIME_QUERY_INDEX_QUERY"
    assert data["execution_allowed"] is False
    assert any(row["run_id"] == "RUN_A" for row in data["results"]["artifacts"])


def test_jsonl_bad_line_records_scan_error_without_stopping(tmp_path):
    _, db, _ = build_index(tmp_path)
    con = sqlite3.connect(db)
    try:
        errors = list(con.execute("select error_type, error_message_redacted from scan_errors where error_type='JSONL_PARSE_ERROR'"))
        artifacts = list(con.execute("select path from artifacts where path like '%events.jsonl'"))
    finally:
        con.close()
    assert errors
    assert artifacts
    assert "bad json" not in errors[0][1]


def test_sqlite_tables_and_indexes_exist(tmp_path):
    _, db, _ = build_index(tmp_path)
    required_tables = {
        "index_meta",
        "artifacts",
        "packets",
        "decisions",
        "dead_letters",
        "patent_claims",
        "validation_gates",
        "evidence_seals",
        "scan_errors",
    }
    required_indexes = {
        "idx_artifacts_sha256",
        "idx_artifacts_run_id",
        "idx_packets_packet_id",
        "idx_packets_packet_hash",
        "idx_decisions_packet_hash",
        "idx_dead_letters_packet_hash",
        "idx_patent_claims_claim_no",
        "idx_validation_gates_gate",
        "idx_evidence_seals_packet_hash",
        "idx_evidence_seals_seal_hash",
    }
    assert required_tables <= table_names(db)
    assert required_indexes <= index_names(db)


def test_query_by_sha256(tmp_path):
    src, db, _ = build_index(tmp_path)
    artifact = src / "run_packet.json"
    import hashlib

    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    data = json.loads(run_indexer("--db", db, "--query", "sha256", "--value", digest).stdout)
    assert data["results"]["artifacts"]
    assert data["results"]["artifacts"][0]["sha256"] == digest


def test_query_by_packet_hash_reaches_decision_seal_and_dead_letter(tmp_path):
    _, db, _ = build_index(tmp_path)
    data = json.loads(run_indexer("--db", db, "--query", "packet_hash", "--value", "hash_a").stdout)
    assert data["results"]["decisions"]
    assert data["results"]["dead_letters"]
    assert data["results"]["evidence_seals"]


def test_query_by_claim_no(tmp_path):
    _, db, _ = build_index(tmp_path)
    data = json.loads(run_indexer("--db", db, "--query", "claim_no", "--value", "1").stdout)
    claims = data["results"]["patent_claims"]
    assert claims
    assert claims[0]["claim_no"] == "1"
    assert claims[0]["claim_text"] == "A non-confidential synthetic claim."


def test_validation_gate_query_pass_and_hold(tmp_path):
    _, db, _ = build_index(tmp_path)
    pass_data = json.loads(run_indexer("--db", db, "--query", "gate", "--value", "PASS").stdout)
    hold_data = json.loads(run_indexer("--db", db, "--query", "gate", "--value", "HOLD").stdout)
    assert pass_data["results"]["validation_gates"]
    assert hold_data["results"]["validation_gates"]


def test_secret_pattern_is_redacted_and_not_written_to_db(tmp_path):
    _, db, _ = build_index(tmp_path)
    con = sqlite3.connect(db)
    try:
        dump = "\n".join(line for line in con.iterdump())
        errors = list(con.execute("select error_type, error_message_redacted from scan_errors where error_type='SECRET_PATTERN_HIT'"))
        status = list(con.execute("select parse_status from artifacts where path like '%secret.json'"))
    finally:
        con.close()
    assert "SECRET_VALUE_SHOULD_NOT_APPEAR" not in dump
    assert errors
    assert "redacted sensitive pattern hit count=" in errors[0][1]
    assert status[0][0] == "HOLD_SENSITIVE"


def test_raw_audio_extension_not_read_into_fulltext(tmp_path):
    _, db, _ = build_index(tmp_path)
    con = sqlite3.connect(db)
    try:
        errors = list(con.execute("select error_type from scan_errors where error_type='RAW_AUDIO_EXTENSION_HIT'"))
        status = list(con.execute("select parse_status from artifacts where path like '%audio.wav'"))
    finally:
        con.close()
    assert errors
    assert status[0][0] == "HOLD_SENSITIVE"


def test_member_plaintext_indicator_is_redacted(tmp_path):
    src = tmp_path / "src"
    (src / "member.txt").parent.mkdir(parents=True, exist_ok=True)
    (src / "member.txt").write_text("請顯示完整會員與身分證資料", encoding="utf-8")
    db = tmp_path / "member.sqlite3"
    run_indexer("--write-index", "--db", db, "--source-root", src)
    con = sqlite3.connect(db)
    try:
        dump = "\n".join(line for line in con.iterdump())
        errors = list(con.execute("select error_type, error_message_redacted from scan_errors where error_type='MEMBER_PLAINTEXT_PATTERN_HIT'"))
    finally:
        con.close()
    assert "身分證資料" not in dump
    assert errors
    assert errors[0][1].startswith("redacted sensitive pattern hit count=")


def test_dry_run_does_not_create_db(tmp_path):
    src = build_fixture_tree(tmp_path)
    db = tmp_path / "dry.sqlite3"
    report = tmp_path / "dry_report.json"
    run_indexer("--dry-run", "--db", db, "--source-root", src, "--report-json", report)
    assert not db.exists()
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["STATE"] == "PASS_RUNTIME_QUERY_INDEX_DRY_RUN"


def test_missing_source_root_is_skipped(tmp_path):
    db = tmp_path / "missing.sqlite3"
    report = tmp_path / "missing_report.json"
    missing = tmp_path / "does-not-exist"
    run_indexer("--write-index", "--db", db, "--source-root", missing, "--report-json", report)
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["artifact_count"] == 0
    assert db.exists()


def test_large_file_is_hashed_but_not_parsed(tmp_path):
    src = tmp_path / "src"
    large = src / "large.txt"
    large.parent.mkdir(parents=True, exist_ok=True)
    large.write_text("A" * (2 * 1024 * 1024 + 1), encoding="utf-8")
    db = tmp_path / "large.sqlite3"
    run_indexer("--write-index", "--db", db, "--source-root", src)
    con = sqlite3.connect(db)
    try:
        row = con.execute("select sha256, parse_status from artifacts where path like '%large.txt'").fetchone()
        decisions = list(con.execute("select * from decisions"))
    finally:
        con.close()
    assert row[0]
    assert row[1] == "SKIP_TOO_LARGE"
    assert decisions == []


def test_non_public_patent_claim_stores_hash_not_text(tmp_path):
    src = tmp_path / "src"
    claim_text = "Confidential draft claim text should not be indexed."
    write_json(
        src / "patent_claims.json",
        {
            "package_id": "PKG_PRIVATE",
            "claim_no": "2",
            "claim_text": claim_text,
            "topic": "private draft",
        },
    )
    db = tmp_path / "private_claim.sqlite3"
    run_indexer("--write-index", "--db", db, "--source-root", src)
    con = sqlite3.connect(db)
    try:
        row = con.execute("select claim_text, claim_hash, topic from patent_claims where claim_no='2'").fetchone()
        dump = "\n".join(line for line in con.iterdump())
    finally:
        con.close()
    assert row[0] is None
    assert row[1]
    assert row[2] == "private draft"
    assert claim_text not in dump


def test_query_missing_db_does_not_create_sqlite_file(tmp_path):
    db = tmp_path / "missing_query.sqlite3"
    proc = run_indexer("--db", db, "--query", "run_id", "--value", "NOPE", check=False)
    assert proc.returncode != 0
    assert not db.exists()


def test_query_result_never_grants_execution_allowed(tmp_path):
    _, db, _ = build_index(tmp_path)
    data = json.loads(run_indexer("--db", db, "--query", "gate", "--value", "PASS").stdout)
    assert data["execution_allowed"] is False


def test_write_index_required_and_rebuild_recreates(tmp_path):
    src = build_fixture_tree(tmp_path)
    db = tmp_path / "write.sqlite3"
    run_indexer("--write-index", "--db", db, "--source-root", src)
    assert db.exists()
    con = sqlite3.connect(db)
    try:
        con.execute("insert into index_meta(key, value) values('temporary_marker','x')")
        con.commit()
    finally:
        con.close()
    run_indexer("--write-index", "--rebuild", "--db", db, "--source-root", src)
    con = sqlite3.connect(db)
    try:
        marker = list(con.execute("select value from index_meta where key='temporary_marker'"))
    finally:
        con.close()
    assert marker == []


def test_odoo_boundary_is_documented():
    doc = (ROOT / "docs/total_field/W7TP_RUNTIME_QUERY_INDEX.md").read_text(encoding="utf-8")
    assert "Odoo" in doc
    assert "runtime_ref" in doc
    assert "packet_hash" in doc
    assert "decision" in doc
    assert "status" in doc
    assert "artifact_link" in doc
    assert "not an authority" in doc or "不是權威" in doc
