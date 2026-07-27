import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.adi_native.errors import LedgerParseFailure
from core.adi_native.evidence_ledger import (
    GENESIS_HASH,
    LEGACY_HASH_V1,
    VerifiableSpacetimeSystem,
    calculate_legacy_hash_v1,
    verify_legacy_chain,
)


def make_legacy(path):
    previous = GENESIS_HASH
    records = []
    for index in (1, 2):
        record = {
            "index": index,
            "timestamp": f"2026-01-01T00:00:0{index}",
            "event_type": "fixture",
            "content": f"event-{index}",
            "actor": "legacy-actor",
            "previous_hash": previous,
        }
        record["hash"] = calculate_legacy_hash_v1(record)
        previous = record["hash"]
        records.append(record)
    path.write_text(json.dumps(records), encoding="utf-8")
    return records


def system(tmp_path):
    legacy = tmp_path / "wuchang_trust_chain.json"
    make_legacy(legacy)
    ledger = tmp_path / "wuchang_trust_chain.v2.jsonl"
    return VerifiableSpacetimeSystem(ledger, legacy_path=legacy), legacy, ledger


def append(s, suffix="1"):
    return s.append_event(
        "test",
        {"suffix": suffix},
        actor_ref="agent-ref",
        accountable_person_ref="person-ref",
    )


def test_l01_corrupt_legacy_holds_instead_of_reset(tmp_path):
    legacy = tmp_path / "wuchang_trust_chain.json"
    legacy.write_text("{broken", encoding="utf-8")
    with pytest.raises(LedgerParseFailure, match="HOLD_LEDGER_PARSE_FAILURE"):
        VerifiableSpacetimeSystem(tmp_path / "v2.jsonl", legacy_path=legacy)
    assert not (tmp_path / "v2.jsonl").exists()


def test_l02_append_only_preserves_existing_prefix(tmp_path):
    s, _, ledger = system(tmp_path)
    append(s)
    prefix = ledger.read_bytes()
    append(s, "2")
    assert ledger.read_bytes().startswith(prefix)
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 2


def test_l03_tamper_is_detected(tmp_path):
    s, _, ledger = system(tmp_path)
    append(s)
    text = ledger.read_text(encoding="utf-8").replace("event", "tampered", 1)
    ledger.write_text(text, encoding="utf-8")
    assert s.verify_chain()[0] is False


def test_l04_actor_and_accountable_person_are_separate_fields(tmp_path):
    s, _, _ = system(tmp_path)
    event = append(s)
    assert event["actor_ref"] == "agent-ref"
    assert event["accountable_person_ref"] == "person-ref"
    assert "actor" not in event


def test_l05_legacy_v1_default_and_v2_both_verify(tmp_path):
    s, legacy, _ = system(tmp_path)
    parsed = json.loads(legacy.read_text(encoding="utf-8"))
    assert all("hash_profile" not in record for record in parsed)
    assert verify_legacy_chain(legacy) == (True, "CHAIN_VALID")
    first = append(s)
    assert first["hash_profile"] == "W7TP_EVIDENCE_HASH_V2"
    assert first["legacy_file_sha256"] == hashlib.sha256(legacy.read_bytes()).hexdigest()
    assert s.verify_chain() == (True, "CHAIN_VALID")


def test_l06_concurrent_writes_keep_unique_indices_and_chain(tmp_path):
    s, legacy, ledger = system(tmp_path)

    def worker(value):
        local = VerifiableSpacetimeSystem(ledger, legacy_path=legacy)
        return append(local, str(value))

    with ThreadPoolExecutor(max_workers=2) as pool:
        events = list(pool.map(worker, (1, 2)))
    assert sorted(event["index"] for event in events) == [1, 2]
    assert s.verify_chain() == (True, "CHAIN_VALID")
