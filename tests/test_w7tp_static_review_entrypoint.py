import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.total_field import w7tp_static_review_entrypoint as reviewer


class StaticReviewEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = datetime.now(timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def non_execution():
        return {key: False for key in reviewer.NON_EXECUTION_FIELDS}

    def resign_request(self, path):
        value = json.loads(path.read_text(encoding="utf-8"))
        value.pop("request_self_sha256", None)
        value["request_self_sha256"] = reviewer.sha256_bytes(reviewer.canonical_json_bytes(value))
        self.write_json(path, value)
        return value

    def resign_seal(self, path):
        value = json.loads(path.read_text(encoding="utf-8"))
        value.pop("owner_seal_self_sha256", None)
        value["owner_seal_self_sha256"] = reviewer.sha256_bytes(reviewer.canonical_json_bytes(value))
        self.write_json(path, value)
        return value

    def make_package(
        self,
        name="case",
        *,
        requested_decision=reviewer.DECISION_ACCEPT,
        include_seal=True,
        created_at=None,
        expires_at=None,
        seal_issued_at=None,
        seal_expires_at=None,
    ):
        case = self.root / name
        source = case / "source" / "candidate.json"
        self.write_json(source, {"candidate_only": True, "runtime_activation": False})
        run_id = f"TEST_STATIC_REVIEW_{name.upper().replace('-', '_')}"
        purpose = "STATIC_IMPLEMENTATION_CANDIDATE_ONLY"
        manifest_path = case / "envelope" / "SOURCE_SHA256_MANIFEST.json"
        manifest = {
            "schema_version": reviewer.SOURCE_MANIFEST_SCHEMA_VERSION,
            "packet_type": "TOTAL_FIELD_STATIC_SOURCE_MANIFEST",
            "run_id": run_id,
            "purpose": purpose,
            "manifest_self_hash_excluded": True,
            "files": [
                {
                    "path": source.relative_to(self.root).as_posix(),
                    "size_bytes": source.stat().st_size,
                    "sha256": self.sha(source),
                    "role": "static_candidate_source",
                }
            ],
            "file_count": 1,
        }
        self.write_json(manifest_path, manifest)
        request_path = case / "envelope" / "TOTAL_FIELD_STATIC_REVIEW_REQUEST.json"
        seal_path = case / "envelope" / "OWNER_SEAL.json"
        created = created_at or self.now
        expires = expires_at or (self.now + timedelta(hours=1))
        request = {
            "schema_version": reviewer.REQUEST_SCHEMA_VERSION,
            "packet_type": "TOTAL_FIELD_STATIC_REVIEW_REQUEST",
            "run_id": run_id,
            "packet_id": f"packet:{name}",
            "event_id": f"event:{name}",
            "created_at": reviewer.utc_text(created),
            "expires_at": reviewer.utc_text(expires),
            "state": "PENDING_TOTAL_FIELD_STATIC_REVIEW",
            "requested_decision": requested_decision,
            "only_request": requested_decision,
            "purpose": purpose,
            "single_use": True,
            "single_use_id": f"single-use:{name}",
            "request_self_hash_algorithm": reviewer.REQUEST_SELF_HASH_ALGORITHM,
            "source_manifest_path": manifest_path.relative_to(self.root).as_posix(),
            "source_manifest_sha256": self.sha(manifest_path),
            "owner_seal_path": seal_path.relative_to(self.root).as_posix(),
            "non_execution_assertions": self.non_execution(),
        }
        request["request_self_sha256"] = reviewer.sha256_bytes(reviewer.canonical_json_bytes(request))
        self.write_json(request_path, request)
        if include_seal:
            issued = seal_issued_at or (created + timedelta(minutes=1))
            seal_expires = seal_expires_at or min(expires, issued + timedelta(minutes=30))
            seal = {
                "schema_version": reviewer.OWNER_SEAL_SCHEMA_VERSION,
                "packet_type": "TOTAL_FIELD_STATIC_REVIEW_OWNER_SEAL",
                "seal_id": f"owner-seal:{name}",
                "run_id": run_id,
                "purpose": purpose,
                "complete_manifest_sha256": self.sha(manifest_path),
                "review_request_sha256": self.sha(request_path),
                "single_use": True,
                "single_use_id": request["single_use_id"],
                "issued_at": reviewer.utc_text(issued),
                "expires_at": reviewer.utc_text(seal_expires),
                "founder_authority_ref": reviewer.FOUNDER_AUTHORITY_REF,
                "authorization": reviewer.OWNER_AUTHORIZATION,
                "owner_seal_self_hash_algorithm": reviewer.OWNER_SEAL_SELF_HASH_ALGORITHM,
                "non_execution_assertions": self.non_execution(),
            }
            seal["owner_seal_self_sha256"] = reviewer.sha256_bytes(reviewer.canonical_json_bytes(seal))
            self.write_json(seal_path, seal)
        return {
            "case": case,
            "source": source,
            "manifest": manifest_path,
            "request": request_path,
            "seal": seal_path,
        }

    def rebind_after_manifest_change(self, package):
        request = json.loads(package["request"].read_text(encoding="utf-8"))
        request["source_manifest_sha256"] = self.sha(package["manifest"])
        self.write_json(package["request"], request)
        self.resign_request(package["request"])
        seal = json.loads(package["seal"].read_text(encoding="utf-8"))
        seal["complete_manifest_sha256"] = self.sha(package["manifest"])
        seal["review_request_sha256"] = self.sha(package["request"])
        self.write_json(package["seal"], seal)
        self.resign_seal(package["seal"])

    def review(self, package, name="result", replay_root=None):
        return reviewer.review_once(
            request_path=package["request"],
            manifest_path=package["manifest"],
            owner_seal_path=package["seal"],
            output_dir=self.root / "outputs" / name,
            repo_root=self.root,
            replay_root=replay_root,
            now=self.now + timedelta(minutes=2),
        )

    def test_valid_static_candidate_accepts_with_fixed_non_runtime_scope(self):
        result = self.review(self.make_package())
        self.assertEqual(reviewer.DECISION_ACCEPT, result["final_decision"])
        output = self.root / "outputs" / "result"
        self.assertEqual(
            {"TOTAL_FIELD_STATIC_REVIEW_RESULT.json", "REVIEW_EVIDENCE.json", "SHA256_MANIFEST.json"},
            {path.name for path in output.iterdir() if path.is_file()},
        )
        decision = json.loads((output / "TOTAL_FIELD_STATIC_REVIEW_RESULT.json").read_text(encoding="utf-8"))
        for key in (
            "runtime_update_authorized",
            "image_build_authorized",
            "image_pull_authorized",
            "image_tag_authorized",
            "container_start_authorized",
            "deployment_authorized",
            "restart_authorized",
            "db_write_authorized",
            "canonical_write_authorized",
            "pointer_write_authorized",
            "git_commit_authorized",
            "git_push_authorized",
            "side_effects_executed",
        ):
            self.assertFalse(decision[key], key)

    def test_request_schema_is_draft_2020_12_valid(self):
        package = self.make_package("schema")
        schema_path = Path(reviewer.__file__).resolve().parents[2] / "schemas/field/w7tp_total_field_static_review_request_v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        request = json.loads(package["request"].read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self.assertEqual([], list(Draft202012Validator(schema).iter_errors(request)))

    def test_missing_and_fake_owner_seals_reject(self):
        missing = self.make_package("missing-seal", include_seal=False)
        result = self.review(missing, "missing-seal")
        self.assertEqual(reviewer.DECISION_HOLD, result["final_decision"])
        self.assertIn("HOLD_STATIC_OWNER_SEAL_MISSING", result["reason_codes"])

        fake = self.make_package("fake-seal")
        seal = json.loads(fake["seal"].read_text(encoding="utf-8"))
        seal["authorization"] = "AUTHORIZE_RUNTIME_AND_STATIC_REVIEW"
        self.write_json(fake["seal"], seal)
        self.resign_seal(fake["seal"])
        result = self.review(fake, "fake-seal")
        self.assertEqual(reviewer.DECISION_BLOCK, result["final_decision"])
        self.assertIn("BLOCK_STATIC_OWNER_SEAL_AUTHORITY", result["reason_codes"])

        bad_hash = self.make_package("bad-seal-hash")
        seal = json.loads(bad_hash["seal"].read_text(encoding="utf-8"))
        seal["owner_seal_self_sha256"] = "f" * 64
        self.write_json(bad_hash["seal"], seal)
        result = self.review(bad_hash, "bad-seal-hash")
        self.assertEqual(reviewer.DECISION_HOLD, result["final_decision"])
        self.assertIn("HOLD_STATIC_SELF_HASH_MISMATCH", result["reason_codes"])

    def test_expired_request_and_owner_seal_reject(self):
        expired_request = self.make_package(
            "expired-request",
            created_at=self.now - timedelta(hours=2),
            expires_at=self.now - timedelta(hours=1),
        )
        result = self.review(expired_request, "expired-request")
        self.assertEqual(reviewer.DECISION_HOLD, result["final_decision"])
        self.assertIn("HOLD_STATIC_REQUEST_EXPIRED", result["reason_codes"])

        expired_seal = self.make_package(
            "expired-seal",
            created_at=self.now - timedelta(hours=2),
            expires_at=self.now + timedelta(hours=1),
            seal_issued_at=self.now - timedelta(hours=1),
            seal_expires_at=self.now - timedelta(minutes=1),
        )
        result = self.review(expired_seal, "expired-seal")
        self.assertEqual(reviewer.DECISION_HOLD, result["final_decision"])
        self.assertIn("HOLD_STATIC_OWNER_SEAL_EXPIRED", result["reason_codes"])

    def test_replay_rejects_same_single_use_and_seal(self):
        package = self.make_package("replay")
        replay_root = self.root / "outputs"
        first = self.review(package, "replay-first", replay_root)
        self.assertEqual(reviewer.DECISION_ACCEPT, first["final_decision"])
        second = self.review(package, "replay-second", replay_root)
        self.assertEqual(reviewer.DECISION_HOLD, second["final_decision"])
        self.assertIn("HOLD_STATIC_REPLAY", second["reason_codes"])

    def test_hash_bytes_purpose_and_run_id_mismatches_reject(self):
        for index, mismatch in enumerate(("sha256", "size_bytes", "purpose", "run_id")):
            with self.subTest(mismatch=mismatch):
                package = self.make_package(f"binding-{index}")
                if mismatch in {"sha256", "size_bytes"}:
                    manifest = json.loads(package["manifest"].read_text(encoding="utf-8"))
                    manifest["files"][0][mismatch] = "f" * 64 if mismatch == "sha256" else 999999
                    self.write_json(package["manifest"], manifest)
                    self.rebind_after_manifest_change(package)
                else:
                    seal = json.loads(package["seal"].read_text(encoding="utf-8"))
                    seal[mismatch] = f"MISMATCH_{mismatch.upper()}"
                    self.write_json(package["seal"], seal)
                    self.resign_seal(package["seal"])
                result = self.review(package, f"binding-{index}")
                self.assertIn(result["final_decision"], {reviewer.DECISION_HOLD, reviewer.DECISION_BLOCK})

    def test_runtime_build_deploy_and_field_injections_block(self):
        for index, field in enumerate(("runtime_activation", "image_build", "deploy")):
            with self.subTest(field=field):
                package = self.make_package(f"authority-{index}")
                request = json.loads(package["request"].read_text(encoding="utf-8"))
                request["non_execution_assertions"][field] = True
                self.write_json(package["request"], request)
                self.resign_request(package["request"])
                result = self.review(package, f"authority-{index}")
                self.assertEqual(reviewer.DECISION_BLOCK, result["final_decision"])
                self.assertIn("BLOCK_STATIC_FORBIDDEN_AUTHORITY_INJECTION", result["reason_codes"])

        injected = self.make_package("field-injection")
        request = json.loads(injected["request"].read_text(encoding="utf-8"))
        request["runtime_authority"] = True
        self.write_json(injected["request"], request)
        self.resign_request(injected["request"])
        result = self.review(injected, "field-injection")
        self.assertEqual(reviewer.DECISION_BLOCK, result["final_decision"])
        self.assertIn("BLOCK_STATIC_REQUEST_FIELD_INJECTION", result["reason_codes"])

    def test_path_traversal_and_symbolic_link_block(self):
        traversal = self.make_package("traversal")
        request = json.loads(traversal["request"].read_text(encoding="utf-8"))
        request["source_manifest_path"] = "../outside.json"
        self.write_json(traversal["request"], request)
        self.resign_request(traversal["request"])
        result = self.review(traversal, "traversal")
        self.assertEqual(reviewer.DECISION_BLOCK, result["final_decision"])
        self.assertIn("BLOCK_STATIC_PATH_ESCAPE", result["reason_codes"])

        symlink = self.make_package("symlink")
        link = symlink["case"] / "source" / "linked.json"
        link.symlink_to(symlink["source"])
        manifest = json.loads(symlink["manifest"].read_text(encoding="utf-8"))
        manifest["files"][0] = {
            "path": link.relative_to(self.root).as_posix(),
            "size_bytes": link.stat().st_size,
            "sha256": self.sha(link),
        }
        self.write_json(symlink["manifest"], manifest)
        self.rebind_after_manifest_change(symlink)
        result = self.review(symlink, "symlink")
        self.assertEqual(reviewer.DECISION_BLOCK, result["final_decision"])
        self.assertIn("BLOCK_STATIC_SYMBOLIC_LINK", result["reason_codes"])

    def test_self_review_blocks_entrypoint_source(self):
        package = self.make_package("self-review")
        self_source = self.root / "tools/total_field/w7tp_static_review_entrypoint.py"
        self_source.parent.mkdir(parents=True, exist_ok=True)
        self_source.write_text("candidate self source\n", encoding="utf-8")
        manifest = json.loads(package["manifest"].read_text(encoding="utf-8"))
        manifest["files"][0] = {
            "path": self_source.relative_to(self.root).as_posix(),
            "size_bytes": self_source.stat().st_size,
            "sha256": self.sha(self_source),
        }
        self.write_json(package["manifest"], manifest)
        self.rebind_after_manifest_change(package)
        result = self.review(package, "self-review")
        self.assertEqual(reviewer.DECISION_BLOCK, result["final_decision"])
        self.assertIn("BLOCK_STATIC_SELF_REVIEW", result["reason_codes"])

    def test_legacy_static_decision_vocabulary_maps_to_fixed_accept(self):
        for index, legacy in enumerate(sorted(reviewer.REQUESTED_DECISIONS - {reviewer.DECISION_ACCEPT})):
            with self.subTest(legacy=legacy):
                package = self.make_package(f"legacy-{index}", requested_decision=legacy)
                result = self.review(package, f"legacy-{index}")
                self.assertEqual(reviewer.DECISION_ACCEPT, result["final_decision"])

    def test_unknown_or_expanded_decision_vocabulary_blocks(self):
        package = self.make_package("expanded-vocabulary")
        request = json.loads(package["request"].read_text(encoding="utf-8"))
        request["requested_decision"] = "ACCEPT_STATIC_IMPLEMENTATION_AND_RUNTIME_ONLY"
        request["only_request"] = request["requested_decision"]
        self.write_json(package["request"], request)
        self.resign_request(package["request"])
        result = self.review(package, "expanded-vocabulary")
        self.assertEqual(reviewer.DECISION_BLOCK, result["final_decision"])
        self.assertIn("BLOCK_STATIC_DECISION_VOCABULARY", result["reason_codes"])


if __name__ == "__main__":
    unittest.main()
