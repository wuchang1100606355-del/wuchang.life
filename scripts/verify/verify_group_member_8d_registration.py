#!/usr/bin/env python3
import ast
import csv
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MEMBER = ROOT / "Taiji_Odoo/addons/wuchang_member_registration"
GOOGLE = ROOT / "Taiji_Odoo/addons/wuchang_google_member_login"
LINE = ROOT / "Taiji_Odoo/addons/wuchang_line_login"
EVIDENCE = ROOT / "runtime/total_field/evidence/TOTAL_FIELD_GROUP_MEMBER_8D_REGISTRATION_20260621_224359"


REQUIRED_FILES = [
    MEMBER / "__manifest__.py",
    MEMBER / "models/member_registration.py",
    MEMBER / "controllers/main.py",
    MEMBER / "views/group_member_registration_views.xml",
    MEMBER / "security/ir.model.access.csv",
    GOOGLE / "controllers/main.py",
    GOOGLE / "__manifest__.py",
    LINE / "controllers/main.py",
    LINE / "__manifest__.py",
    ROOT / "docs/evidence/GROUP_MEMBER_8D_REGISTRATION.md",
    EVIDENCE / "GROUP_MEMBER_8D_CODE_SEAL.json",
    EVIDENCE / "README_GROUP_MEMBER_8D_REGISTRATION.md",
    EVIDENCE / "sha256_manifest.txt",
]


REQUIRED_MODEL_STRINGS = [
    '_name = "wuchang.member.group.registration.batch"',
    '_name = "wuchang.member.group.registration.packet"',
    "D1_IDENTITY",
    "D2_INTENT",
    "D3_STATE",
    "D4_TOPOLOGY",
    "D5_RESOURCE",
    "D6_GOVERNANCE",
    "D7_VERIFICATION",
    "D8_ENVELOPE",
    "hash_provider_ref",
    "CONFIRM_DRY_RUN",
    "runtime/total_field/evidence",
]


REQUIRED_ROUTE_STRINGS = [
    "/wuchang/member/register/group/<string:packet_ref>",
    "/wuchang/member/register/group/<string:packet_ref>/claim",
    "/wuchang/member/register/group/<string:packet_ref>/confirm_dry_run",
    "/wuchang/member/register/group/<string:packet_ref>/status",
]


FORBIDDEN_PATTERNS = [
    r"login\.tailscale\.com/admin/invite",
    r"client_secret\s*=\s*['\"][^'\"]+['\"]",
    r"access_token\s*=\s*['\"][^'\"]+['\"]",
    r"refresh_token\s*=\s*['\"][^'\"]+['\"]",
    r"id_token\s*=\s*['\"][^'\"]+['\"]",
    r"sk-[A-Za-z0-9]{16,}",
]


def fail(message):
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def read(path):
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def check_python_syntax(paths):
    for path in paths:
        ast.parse(read(path), filename=str(path))


def check_required_strings():
    model_text = read(MEMBER / "models/member_registration.py")
    controller_text = read(MEMBER / "controllers/main.py")
    for needle in REQUIRED_MODEL_STRINGS:
        if needle not in model_text:
            fail(f"model_missing:{needle}")
    for needle in REQUIRED_ROUTE_STRINGS:
        if needle not in controller_text:
            fail(f"route_missing:{needle}")


def check_manifests():
    member_manifest = ast.literal_eval(read(MEMBER / "__manifest__.py"))
    google_manifest = ast.literal_eval(read(GOOGLE / "__manifest__.py"))
    line_manifest = ast.literal_eval(read(LINE / "__manifest__.py"))
    if "views/group_member_registration_views.xml" not in member_manifest.get("data", []):
        fail("member_manifest_missing_group_views")
    if "wuchang_member_registration" not in google_manifest.get("depends", []):
        fail("google_manifest_missing_member_registration_dependency")
    if "wuchang_member_registration" not in line_manifest.get("depends", []):
        fail("line_manifest_missing_member_registration_dependency")


def check_security_csv():
    with (MEMBER / "security/ir.model.access.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    model_ids = {row["model_id:id"] for row in rows}
    required = {
        "model_wuchang_member_group_registration_batch",
        "model_wuchang_member_group_registration_packet",
    }
    missing = required - model_ids
    if missing:
        fail("security_missing:" + ",".join(sorted(missing)))


def check_oauth_group_hook():
    google_text = read(GOOGLE / "controllers/main.py")
    line_text = read(LINE / "controllers/main.py")
    required = [
        "wuchang_group_packet_ref",
        "wuchang_group_auth_ref",
        "hash_subject",
        "google_member_masked",
        "line_member_masked",
    ]
    joined = google_text + "\n" + line_text
    for needle in required:
        if needle not in joined:
            fail(f"oauth_hook_missing:{needle}")


def check_evidence():
    seal = json.loads(read(EVIDENCE / "GROUP_MEMBER_8D_CODE_SEAL.json"))
    if seal.get("state") != "GROUP_MEMBER_8D_REGISTRATION_PATCH_READY":
        fail("seal_state_drift")
    safety = seal.get("safety", {})
    for flag in [
        "formal_db_write",
        "formal_pos_write",
        "payment_capture",
        "service_restart",
        "deploy",
        "production_release",
        "secret_read",
        "member_plaintext_read",
    ]:
        if safety.get(flag) is not False:
            fail(f"safety_flag_not_false:{flag}")
    manifest_dir = EVIDENCE
    for line in read(EVIDENCE / "sha256_manifest.txt").splitlines():
        digest, name = line.split(maxsplit=1)
        path = manifest_dir / name.strip()
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            fail(f"sha256_mismatch:{name}")


def check_forbidden_strings():
    targets = [
        MEMBER / "models/member_registration.py",
        MEMBER / "controllers/main.py",
        MEMBER / "views/group_member_registration_views.xml",
        GOOGLE / "controllers/main.py",
        LINE / "controllers/main.py",
        ROOT / "docs/evidence/GROUP_MEMBER_8D_REGISTRATION.md",
        EVIDENCE / "GROUP_MEMBER_8D_CODE_SEAL.json",
        EVIDENCE / "README_GROUP_MEMBER_8D_REGISTRATION.md",
    ]
    for path in targets:
        text = read(path)
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text):
                fail(f"forbidden_string:{path.relative_to(ROOT)}:{pattern}")


def main():
    for path in REQUIRED_FILES:
        if not path.exists():
            fail(f"missing_required_file:{path.relative_to(ROOT)}")
    check_python_syntax([
        MEMBER / "models/member_registration.py",
        MEMBER / "controllers/main.py",
        GOOGLE / "controllers/main.py",
        LINE / "controllers/main.py",
    ])
    check_manifests()
    check_required_strings()
    check_security_csv()
    check_oauth_group_hook()
    check_evidence()
    check_forbidden_strings()
    print("STATE=PASS_GROUP_MEMBER_8D_REGISTRATION_PATCH_READY")
    print("GROUP_REGISTER_ROUTE=/wuchang/member/register/group/<packet_ref>")
    print("FORMAL_DB_WRITE=FALSE")
    print("FORMAL_POS_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    print("PRODUCTION_RELEASE=FALSE")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")


if __name__ == "__main__":
    main()
