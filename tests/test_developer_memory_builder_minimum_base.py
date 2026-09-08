from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.developer_memory_builder import initialize_minimum_base


def _seed(path: Path, *, grants_execution: bool = False) -> Path:
    payload = {
        "schema_id": "W7TP_8DADI_FOUNDER_INTENT_REENTRY_V1",
        "state": "ACTIVE_FOUNDER_TARGET_LOCK_REQUIRES_LIVE_REOBSERVATION",
        **{f"D{index}": {} for index in range(1, 9)},
        "natural_language_execution_contract": {},
        "network_policy": {},
        "legacy_boundary": {},
        "authority_boundary": {
            "ai_is_authority": False,
            "this_packet_grants_execution_authority": grants_execution,
        },
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


class MinimumDeveloperMemoryBaseTests(unittest.TestCase):
    def test_initializes_only_minimum_fail_closed_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_minimum_base(
                root=root,
                founder_seed_path=_seed(root / "seed.json"),
                created_at="2026-09-08T00:00:00Z",
            )
            self.assertEqual(
                result["state"], "PASS_MINIMUM_DEVELOPER_MEMORY_BASE_INITIALIZED"
            )
            self.assertFalse(result["private_memory_copied"])
            self.assertFalse(result["canonical_changed"])
            self.assertFalse(result["d8_granted"])
            self.assertEqual(len(result["files_changed"]), 6)
            index = (
                root / "runtime/developer_memory/indexes/memory_index.jsonl"
            ).read_text(encoding="utf-8")
            self.assertEqual(len(index.splitlines()), 1)

    def test_rejects_partial_or_existing_base(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = _seed(root / "seed.json")
            initialize_minimum_base(root=root, founder_seed_path=seed)
            with self.assertRaisesRegex(
                ValueError, "DEVELOPER_MEMORY_BASE_ALREADY_EXISTS_OR_PARTIAL"
            ):
                initialize_minimum_base(root=root, founder_seed_path=seed)

    def test_rejects_seed_that_grants_execution_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(
                ValueError, "FOUNDER_SEED_MAY_NOT_GRANT_EXECUTION_AUTHORITY"
            ):
                initialize_minimum_base(
                    root=root,
                    founder_seed_path=_seed(
                        root / "seed.json", grants_execution=True
                    ),
                )


if __name__ == "__main__":
    unittest.main()
