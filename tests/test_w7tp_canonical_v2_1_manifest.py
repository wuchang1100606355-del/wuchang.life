import copy
import hashlib
import json
import unicodedata
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_ROOT = ROOT / "manifests/total_field/w7tp_canonical_v2_1"
CANONICAL_MANIFEST = MANIFEST_ROOT / "CANONICAL_MANIFEST.json"
CONSUMER_INVENTORY = MANIFEST_ROOT / "V2_CONSUMER_INVENTORY.json"
SHA256_MANIFEST = MANIFEST_ROOT / "SHA256_MANIFEST.json"
BINDING_MATRIX = (
    ROOT
    / "manifests/total_field/w7tp_five_skill_id_binding_matrix_v2_1"
    / "BINDING_MATRIX.json"
)
BINDING_SCHEMA = (
    ROOT / "schemas/field/w7tp_five_skill_id_binding_matrix_v2_1.schema.json"
)


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized_sha256_without(value: dict, field: str) -> str:
    payload = copy.deepcopy(value)
    payload.pop(field)
    encoded = unicodedata.normalize(
        "NFC",
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_canonical_manifest_binds_parent_successor_and_inventory():
    manifest = json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8"))
    inventory = json.loads(CONSUMER_INVENTORY.read_text(encoding="utf-8"))

    assert manifest["version"] == "2.1"
    assert manifest["migration_mode"] == "APPEND_ONLY_SUCCESSOR"
    assert manifest["locks_matched"] == 12
    assert manifest["parent"]["sha256"] == (
        "a5281f229ced0943072cce373125be16f0d361b9352a71094ad5450a6022d5d0"
    )
    assert _raw_sha256(ROOT / manifest["parent"]["path"]) == manifest["parent"]["sha256"]
    assert _raw_sha256(ROOT / manifest["canonical"]["path"]) == manifest["canonical"]["sha256"]
    assert _raw_sha256(ROOT / manifest["machine_schema"]["path"]) == (
        manifest["machine_schema"]["sha256"]
    )
    assert _raw_sha256(CONSUMER_INVENTORY) == manifest["consumer_inventory"]["sha256"]
    assert inventory["consumer_count"] == len(inventory["consumers"])
    assert inventory["upgraded_count"] == inventory["consumer_count"]
    assert inventory["vpn"]["deployment_nodes"] == ["taiji01"]


def test_binding_matrix_is_append_only_schema_valid_and_self_hash_bound():
    matrix = json.loads(BINDING_MATRIX.read_text(encoding="utf-8"))
    schema = json.loads(BINDING_SCHEMA.read_text(encoding="utf-8"))

    jsonschema.Draft202012Validator(schema).validate(matrix)
    assert matrix["parent_matrix"]["migration_mode"] == "APPEND_ONLY_SUCCESSOR"
    assert _raw_sha256(ROOT / matrix["parent_matrix"]["manifest_ref"]) == (
        matrix["parent_matrix"]["manifest_file_sha256"]
    )
    assert _raw_sha256(ROOT / matrix["parent_matrix"]["schema_ref"]) == (
        matrix["parent_matrix"]["schema_file_sha256"]
    )
    assert matrix["binding_matrix_self_sha256"] == _normalized_sha256_without(
        matrix,
        "binding_matrix_self_sha256",
    )


def test_sha256_manifest_is_path_bounded_and_exact():
    manifest = json.loads(SHA256_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["hash_algorithm"] == "SHA-256"
    assert manifest["manifest_self_sha256"] == _normalized_sha256_without(
        manifest,
        "manifest_self_sha256",
    )
    assert manifest["file_count"] == len(manifest["files"])
    for item in manifest["files"]:
        relative = Path(item["path"])
        assert not relative.is_absolute()
        assert ".." not in relative.parts
        assert _raw_sha256(ROOT / relative) == item["sha256"]
