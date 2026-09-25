#!/usr/bin/env python3
"""Verify the active XiaoJ member browser release artifact.

This verifier reads local release files only. It does not call external APIs,
does not read secrets, does not read member plaintext stores, and does not
touch Odoo, POS, service, router, payment, or production databases.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

from jsonschema import validate


ROOT = Path(__file__).resolve().parents[2]
ACTIVE = ROOT / "runtime/member_browser/ACTIVE_XIAOJ_MEMBER_BROWSER_RELEASE.json"
RELEASE_SCHEMA = ROOT / "schemas/browser/xiaoj_member_browser_release_manifest_v1.schema.json"

EXPECTED_SCOPE = {
    "local_1b_member_browser_controller",
    "member_preference_ref_service_style",
    "mv3_minimum_privilege_browser_bridge",
    "no_plaintext_8d_return_packets",
    "cloud_compute_ref_behavior_info_ref",
    "association_usage_admission_packet",
    "six_platform_association_website_entry",
    "community_activity_rsvp_candidate",
    "public_activity_cache_ref",
    "odoo_role_function_refs",
    "management_fee_payment_intent_candidate",
    "sovereign_1b_product_goal_acceptance",
}

EXPECTED_SOURCES = {
    "web/index.html",
    "web/community_activities.json",
    "web/xiaoj_member_browser_cockpit/app.js",
    "web/xiaoj_member_browser_extension/manifest.json",
    "tools/member_browser/xiaoj_member_browser_1b_controller.py",
    "tools/member_browser/xiaoj_member_browser_gateway.py",
    "tools/member_browser/xiaoj_member_browser_native_host.py",
    "scripts/verify/verify_xiaoj_member_browser_cockpit.py",
    "scripts/verify/verify_xiaoj_member_browser_release.py",
    "scripts/verify/verify_xiaoj_sovereign_1b_product_goal.py",
    "docs/website/WUCHANG_ASSOCIATION_PLATFORM_ROLE_MAP.md",
    "docs/total_field/XIAOJ_MEMBER_BROWSER_1B_CONTROL_SPEC.md",
    "docs/total_field/XIAOJ_SOVEREIGN_1B_PRODUCT_GOAL_ACCEPTANCE.md",
    "schemas/8d/xiaoj_8d_action_packet.schema.json",
}

COCKPIT_ZIP_FILES = {
    "app.js",
    "icon.svg",
    "index.html",
    "manifest.webmanifest",
    "styles.css",
    "sw.js",
}

EXTENSION_ZIP_FILES = {
    "README.md",
    "background.js",
    "manifest.json",
    "native_host/tw.taiji.xiaoj_member_browser_gateway.template.json",
    "sidepanel.css",
    "sidepanel.html",
    "sidepanel.js",
}

HARD_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_-]{12,}"), "secret literal"),
    (re.compile("SECRET_READ" + "=TRUE"), "SECRET_READ true"),
    (re.compile("MEMBER_PLAINTEXT_READ" + "=TRUE"), "MEMBER_PLAINTEXT_READ true"),
    (re.compile("RAW_API_KEY_OUTPUT" + "=TRUE"), "RAW_API_KEY_OUTPUT true"),
    (re.compile("RAW_AUDIO_SAVED" + "=TRUE"), "RAW_AUDIO_SAVED true"),
    (re.compile("DB_WRITE" + "=TRUE"), "DB_WRITE true"),
    (re.compile("PAYMENT_CAPTURE" + "=TRUE"), "PAYMENT_CAPTURE true"),
    (re.compile("SERVICE_RESTART" + "=TRUE"), "SERVICE_RESTART true"),
    (re.compile("DEPLOY" + "=TRUE"), "DEPLOY true"),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def fail(message: str) -> None:
    print(f"FAIL={message}")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RAW_AUDIO_SAVED=FALSE")
    print("DB_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    print("STATE=HOLD_XIAOJ_MEMBER_BROWSER_RELEASE")
    sys.exit(1)


def load_json(path: Path) -> dict:
    if not path.is_file():
        fail(f"missing file: {rel(path)}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_sha256sum(path: Path) -> dict[str, tuple[str, int]]:
    if not path.is_file():
        fail(f"missing sha256 manifest: {rel(path)}")
    rows: dict[str, tuple[str, int]] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line_no == 1:
            if line != "sha256\tbytes\tpath":
                fail("sha256 header mismatch")
            continue
        digest, size, item_path = line.split("\t", 2)
        rows[item_path] = (digest, int(size))
    return rows


def assert_false_flags(flags: dict, label: str) -> None:
    expected = {
        "SECRET_READ",
        "MEMBER_PLAINTEXT_READ",
        "RAW_AUDIO_SAVED",
        "DB_WRITE",
        "PAYMENT_CAPTURE",
        "SERVICE_RESTART",
        "DEPLOY",
    }
    if set(flags) != expected:
        fail(f"{label} safety flag set mismatch")
    bad = [key for key, value in flags.items() if value is not False]
    if bad:
        fail(f"{label} safety flag not false: {bad}")


def scan_text(label: str, text: str) -> None:
    for regex, reason in HARD_PATTERNS:
        if regex.search(text):
            fail(f"{label} hard pattern: {reason}")


def verify_zip(path: Path, expected_files: set[str]) -> None:
    if not path.is_file():
        fail(f"missing package: {rel(path)}")
    with zipfile.ZipFile(path) as zf:
        names = {name for name in zf.namelist() if not name.endswith("/")}
        if names != expected_files:
            fail(f"{path.name} zip files mismatch: {sorted(names)}")
        for name in names:
            raw = zf.read(name)
            if name.endswith((".js", ".json", ".html", ".css", ".md", ".svg", ".webmanifest")):
                scan_text(f"{path.name}:{name}", raw.decode("utf-8"))
        if path.name.endswith("cockpit_pwa.zip"):
            app = zf.read("app.js").decode("utf-8")
            for snippet in [
                "activity_rsvp_candidate",
                "public_activity_cache_ref",
                "cloud_compute_ref",
                "behavior_info_ref",
                "candidate_only: true",
                "requires_total_field_verify: true",
            ]:
                if snippet not in app:
                    fail(f"cockpit app missing snippet: {snippet}")
        if path.name.endswith("extension_mv3.zip"):
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            if manifest.get("host_permissions") != []:
                fail("extension host_permissions not empty")
            if "cookies" in manifest.get("permissions", []):
                fail("extension requests cookie permission")


def verify_public_activity() -> None:
    data = load_json(ROOT / "web/community_activities.json")
    activities = data.get("activities") or []
    item = next((row for row in activities if row.get("activity_ref") == "activity_ref:wuchang_park_hot_dance_weekday_2000"), None)
    if not item:
        fail("missing public hot dance activity")
    expected = {
        "title": "五常公園熱舞社運動社團",
        "location_label": "五常公園",
        "schedule_label": "每週一至週五 20:00-21:00",
        "audience_ref": "audience_ref:community_women",
    }
    for key, value in expected.items():
        if item.get(key) != value:
            fail(f"activity {key} mismatch")
    for key in ["candidate_only", "requires_total_field_verify"]:
        if item.get(key) is not True:
            fail(f"activity {key} is not true")
    for key in ["member_plaintext_transferred", "raw_audio_saved", "payment_required"]:
        if item.get(key) is not False:
            fail(f"activity {key} is not false")


def main() -> int:
    active = load_json(ACTIVE)
    if active.get("state") != "PASS_XIAOJ_MEMBER_BROWSER_RELEASE_PACKAGED":
        fail("active release state mismatch")
    assert_false_flags(active.get("safety_flags") or {}, "active")

    manifest_path = ROOT / active["manifest"]
    sha_path = ROOT / active["sha256_manifest"]
    release_dir = ROOT / active["release_dir"]
    manifest = load_json(manifest_path)
    validate(manifest, load_json(RELEASE_SCHEMA))
    if manifest.get("release_id") != active.get("release_id"):
        fail("release id mismatch")
    if not release_dir.is_dir():
        fail("release dir missing")
    assert_false_flags(manifest.get("safety_flags") or {}, "manifest")

    if not EXPECTED_SCOPE.issubset(set(manifest.get("scope") or [])):
        fail("release scope missing expected product capabilities")

    source_map = {row["path"]: row for row in manifest.get("included_sources") or []}
    missing_sources = sorted(EXPECTED_SOURCES - set(source_map))
    if missing_sources:
        fail(f"manifest missing expected sources: {missing_sources}")
    for source_path, row in source_map.items():
        path = ROOT / source_path
        if not path.is_file():
            fail(f"included source missing: {source_path}")
        if row["sha256"] != sha256_file(path) or row["bytes"] != path.stat().st_size:
            fail(f"included source hash mismatch: {source_path}")

    package_map = {row["path"]: row for row in manifest.get("packages") or []}
    sha_rows = parse_sha256sum(sha_path)
    for package_path, row in package_map.items():
        path = ROOT / package_path
        if row["sha256"] != sha256_file(path) or row["bytes"] != path.stat().st_size:
            fail(f"package hash mismatch: {package_path}")
        if package_path not in sha_rows:
            fail(f"package absent from sha256 manifest: {package_path}")
        if sha_rows[package_path] != (row["sha256"], row["bytes"]):
            fail(f"sha256 manifest row mismatch: {package_path}")

    for item_path in [active["manifest"], str(Path(active["release_dir"]) / "MEMBER_INSTALL_README.md")]:
        path = ROOT / item_path
        if item_path not in sha_rows:
            fail(f"sha256 manifest missing row: {item_path}")
        if sha_rows[item_path] != (sha256_file(path), path.stat().st_size):
            fail(f"sha256 manifest hash mismatch: {item_path}")

    package_paths = [ROOT / path for path in active.get("packages") or []]
    if len(package_paths) != 2:
        fail("active release package count mismatch")
    for path in package_paths:
        if path.name == "xiaoj_member_browser_cockpit_pwa.zip":
            verify_zip(path, COCKPIT_ZIP_FILES)
        elif path.name == "xiaoj_member_browser_extension_mv3.zip":
            verify_zip(path, EXTENSION_ZIP_FILES)
        else:
            fail(f"unexpected package name: {path.name}")

    readme = (release_dir / "MEMBER_INSTALL_README.md").read_text(encoding="utf-8")
    for snippet in [
        "六大平台入口",
        "五常公園熱舞社運動社團",
        "每週一至週五 20:00-21:00",
        "活動 RSVP 候選",
        "PAYMENT_CAPTURE=FALSE",
    ]:
        if snippet not in readme:
            fail(f"member readme missing snippet: {snippet}")
    scan_text("member readme", readme)
    verify_public_activity()

    boundary = manifest.get("browser_boundary") or {}
    if set(boundary.get("allowed_actions") or []) != {"open_sidebar_ref", "read_text_ref", "write_draft_ref"}:
        fail("browser allowed action boundary mismatch")
    if boundary.get("host_permissions") != [] or boundary.get("cookie_permission") is not False:
        fail("browser host/cookie boundary mismatch")

    print("STATE=PASS_XIAOJ_MEMBER_BROWSER_RELEASE")
    print("RELEASE_ID=" + active["release_id"])
    print("RELEASE_DIR=" + active["release_dir"])
    print("MANIFEST=" + active["manifest"])
    print("PUBLIC_ACTIVITY_CACHE=web/community_activities.json")
    print("PACKAGE_COUNT=2")
    print(f"SOURCE_COUNT={len(source_map)}")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RAW_AUDIO_SAVED=FALSE")
    print("DB_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
