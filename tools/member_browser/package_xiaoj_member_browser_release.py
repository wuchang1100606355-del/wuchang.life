#!/usr/bin/env python3
"""Package XiaoJ member browser cockpit and extension release.

This tool is local file packaging only. It does not call external APIs, does
not read secrets, does not read member plaintext stores, and does not touch
Odoo, POS, service, router, or production databases.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE_SCHEMA = ROOT / "schemas/browser/xiaoj_member_browser_release_manifest_v1.schema.json"
VERIFY_SCRIPT = ROOT / "scripts/verify/verify_xiaoj_member_browser_cockpit.py"
RELEASE_ROOT = ROOT / "runtime/member_browser/releases"

COCKPIT_FILES = [
    "web/xiaoj_member_browser_cockpit/index.html",
    "web/xiaoj_member_browser_cockpit/styles.css",
    "web/xiaoj_member_browser_cockpit/app.js",
    "web/xiaoj_member_browser_cockpit/manifest.webmanifest",
    "web/xiaoj_member_browser_cockpit/sw.js",
    "web/xiaoj_member_browser_cockpit/icon.svg",
]

EXTENSION_FILES = [
    "web/xiaoj_member_browser_extension/manifest.json",
    "web/xiaoj_member_browser_extension/background.js",
    "web/xiaoj_member_browser_extension/sidepanel.html",
    "web/xiaoj_member_browser_extension/sidepanel.css",
    "web/xiaoj_member_browser_extension/sidepanel.js",
    "web/xiaoj_member_browser_extension/README.md",
    "web/xiaoj_member_browser_extension/native_host/tw.taiji.xiaoj_member_browser_gateway.template.json",
]

CONTRACT_FILES = [
    "web/index.html",
    "web/community_activities.json",
    "tools/member_browser/xiaoj_member_browser_1b_controller.py",
    "tools/member_browser/Modelfile.xiaoj-member-browser-1b",
    "schemas/8d/xiaoj_8d_action_packet.schema.json",
    "schemas/browser/xiaoj_association_usage_admission_packet_v1.schema.json",
    "schemas/browser/xiaoj_browser_bridge_return_packet_v1.schema.json",
    "schemas/browser/xiaoj_member_browser_gateway_result_v1.schema.json",
    "schemas/browser/xiaoj_member_browser_release_manifest_v1.schema.json",
    "schemas/cloud_proxy/w7tp_cloud_candidate_return_packet_v1.schema.json",
    "docs/total_field/XIAOJ_MEMBER_BROWSER_1B_CONTROL_SPEC.md",
    "docs/total_field/XIAOJ_SOVEREIGN_1B_PRODUCT_GOAL_ACCEPTANCE.md",
    "docs/total_field/W7TP_CLOUD_COMPUTE_PACKETIZED_RETURN_SPEC.md",
    "docs/website/WUCHANG_ASSOCIATION_PLATFORM_ROLE_MAP.md",
    "docs/website/WUCHANG_ASSOCIATION_WEBSITE_QUALITY_UPGRADE.md",
    "packets/examples/8d/member_browser_1b_action_example.json",
    "packets/examples/8d/member_browser_gateway_result_example.json",
    "scripts/verify/verify_xiaoj_member_browser_cockpit.py",
    "scripts/verify/verify_xiaoj_member_browser_release.py",
    "scripts/verify/verify_xiaoj_sovereign_1b_product_goal.py",
    "tools/member_browser/package_xiaoj_member_browser_release.py",
    "tools/member_browser/render_xiaoj_native_host_manifest.py",
    "tools/member_browser/simulate_xiaoj_browser_bridge.py",
    "tools/member_browser/smoke_xiaoj_native_host_protocol.py",
    "tools/member_browser/xiaoj_member_browser_native_host.py",
    "tools/member_browser/xiaoj_member_browser_gateway.py",
]

ALL_SOURCE_FILES = COCKPIT_FILES + EXTENSION_FILES + CONTRACT_FILES

HARD_PATTERNS = [
    re.compile("SECRET_READ" + "=TRUE"),
    re.compile("MEMBER_PLAINTEXT_READ" + "=TRUE"),
    re.compile("RAW_AUDIO_SAVED" + "=TRUE"),
    re.compile("RAW_API_KEY_OUTPUT" + "=TRUE"),
    re.compile("DB_WRITE" + "=TRUE"),
    re.compile("DB_EXECUTE" + "=TRUE"),
    re.compile("PAYMENT_CAPTURE" + "=TRUE"),
    re.compile("DEPLOY" + "=TRUE"),
    re.compile("PRODUCTION_RELEASE" + "=TRUE"),
    re.compile("SERVICE_RESTART" + "=TRUE"),
    re.compile(r"DROP\s+TABLE", re.I),
    re.compile(r"DROP\s+DATABASE", re.I),
    re.compile("TRUN" + "CATE", re.I),
    re.compile(r"DELETE\s+FROM", re.I),
    re.compile(r"UPDATE\s+.+\s+SET", re.I),
    re.compile(r"ALTER\s+TABLE\s+.+\s+DROP", re.I),
]


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def ensure_sources() -> None:
    missing = [p for p in ALL_SOURCE_FILES if not (ROOT / p).is_file()]
    if missing:
        raise SystemExit("MISSING_SOURCE_FILES=" + ",".join(missing))


def run_verifier() -> str:
    proc = subprocess.run([sys.executable, str(VERIFY_SCRIPT)], cwd=ROOT, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit("COCKPIT_VERIFIER=FAIL")
    return proc.stdout


def hard_scan() -> list[str]:
    hits: list[str] = []
    for rel in ALL_SOURCE_FILES:
        path = ROOT / rel
        if path.suffix.lower() not in {".py", ".js", ".json", ".md", ".html", ".css", ".svg", ".webmanifest"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in HARD_PATTERNS:
            if pattern.search(text):
                hits.append(rel + ":" + pattern.pattern)
    return hits


def copy_files(files: list[str], dest: Path, strip_prefix: str) -> None:
    for rel in files:
        src = ROOT / rel
        target_rel = Path(rel).relative_to(Path(strip_prefix))
        out = dest / target_rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)


def zip_dir(source: Path, target_zip: Path) -> None:
    with zipfile.ZipFile(target_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            zf.write(path, path.relative_to(source))


def write_member_readme(release_dir: Path, release_id: str) -> Path:
    readme = release_dir / "MEMBER_INSTALL_README.md"
    readme.write_text(
        "\n".join(
            [
                "# 小J會員主權 AI 瀏覽器交付包",
                "",
                f"RELEASE_ID={release_id}",
                "STATE=VERIFY_PASS",
                "",
                "## 內容",
                "",
                "- `packages/xiaoj_member_browser_extension_mv3.zip`: Chrome/Edge MV3 extension bridge.",
                "- `packages/xiaoj_member_browser_cockpit_pwa.zip`: 小J會員 PWA 座艙。",
                "- `RELEASE_MANIFEST.json`: 檔案、雜湊、安全旗標與驗證狀態。",
                "- `SHA256SUMS.tsv`: 交付包檔案雜湊。",
                "- `RELEASE_VERIFY_REPORT.json`: active release 驗證摘要。",
                "- `XIAOJ_SOVEREIGN_1B_PRODUCT_GOAL_ACCEPTANCE.md`: 總目標驗收矩陣。",
                "",
                "## 對接平台",
                "",
                "此交付包對應協會首頁的六大平台入口：",
                "",
                "- 商業聯合銷售平台。",
                "- 物業管理平台。",
                "- 會員登入平台。",
                "- 社區許願樹平台。",
                "- 社區幣/票券兌換平台。",
                "- 社區活動平台。",
                "",
                "目前公開活動 seed 包含：五常公園熱舞社運動社團，每週一至週五 20:00-21:00 於五常公園，可供社區婦女參與。",
                "",
                "小J可協助查詢、摘要、翻譯、草稿、活動 RSVP 候選、管理費支付意圖候選與平台導引；正式下單、付款、報名送出、Odoo 寫入與資料修改仍需會員確認及總場 verifier。",
                "",
                "## 安全邊界",
                "",
                "- 不含 API key、OAuth token、password、cookie 或 localStorage。",
                "- 不含會員姓名、電話、地址、身分證、raw audio。",
                "- Extension 無 host permissions，無 cookie permission。",
                "- Extension 只允許 `open_sidebar_ref`、`read_text_ref`、確認後 `write_draft_ref`。",
                "- 所有雲端或瀏覽器結果回傳皆為 candidate-only ref packet。",
                "",
                "## 會員安裝流程",
                "",
                "1. 解壓 `xiaoj_member_browser_extension_mv3.zip`。",
                "2. 在 Chrome/Edge 開啟擴充功能頁面。",
                "3. 開啟開發人員模式，選擇載入未封裝項目。",
                "4. 選擇解壓後的 extension 資料夾。",
                "5. 開啟側邊欄，先測試 `read_text_ref`。",
                "6. 若要啟用本機總場 gateway，取得 extension id 後執行：",
                "   `tools/member_browser/render_xiaoj_native_host_manifest.py --extension-id <extension_id>`。",
                "7. 將產生的 native host manifest 手動複製到瀏覽器指定 NativeMessagingHosts 位置。",
                "",
                "## Safety Flags",
                "",
                "SECRET_READ=FALSE",
                "MEMBER_PLAINTEXT_READ=FALSE",
                "RAW_AUDIO_SAVED=FALSE",
                "DB_WRITE=FALSE",
                "PAYMENT_CAPTURE=FALSE",
                "SERVICE_RESTART=FALSE",
                "DEPLOY=FALSE",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return readme


def build_manifest(release_dir: Path, release_id: str, package_paths: list[Path]) -> dict:
    sources = []
    for rel in ALL_SOURCE_FILES:
        path = ROOT / rel
        sources.append({"path": rel, "sha256": sha256_file(path), "bytes": path.stat().st_size})

    packages = []
    for path in package_paths:
        packages.append({
            "name": path.name,
            "path": relative(path),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        })

    return {
        "schema_version": "xiaoj.member_browser_release_manifest.v1",
        "release_id": release_id,
        "created_at": now_utc().isoformat(),
        "product_name": "小J會員主權 AI 瀏覽器座艙",
        "scope": [
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
        ],
        "state": "VERIFY_PASS",
        "packages": packages,
        "included_sources": sources,
        "safety_flags": {
            "SECRET_READ": False,
            "MEMBER_PLAINTEXT_READ": False,
            "RAW_AUDIO_SAVED": False,
            "DB_WRITE": False,
            "PAYMENT_CAPTURE": False,
            "SERVICE_RESTART": False,
            "DEPLOY": False,
        },
        "browser_boundary": {
            "allowed_actions": ["open_sidebar_ref", "read_text_ref", "write_draft_ref"],
            "blocked_actions": [
                "submit_payment",
                "submit_order_without_human",
                "read_raw_cookie",
                "read_raw_local_storage",
                "password_or_token_field",
                "free_mouse_control",
                "db_write",
                "odoo_write",
                "pos_write",
                "deploy",
                "service_restart",
            ],
            "host_permissions": [],
            "cookie_permission": False,
        },
        "verification": {
            "cockpit_verifier": "PASS",
            "release_manifest_schema": "PASS",
            "sha256_manifest": "PASS",
            "hard_scan": "PASS",
        },
    }


def validate_manifest(manifest: dict) -> None:
    try:
        from jsonschema import validate
    except Exception as exc:
        raise SystemExit(f"JSONSCHEMA_IMPORT=FAIL:{exc}") from exc
    schema = json.loads(RELEASE_SCHEMA.read_text(encoding="utf-8"))
    validate(manifest, schema)


def write_sha256_manifest(release_dir: Path, paths: list[Path]) -> Path:
    out = release_dir / "SHA256SUMS.tsv"
    lines = ["sha256\tbytes\tpath"]
    for path in paths:
        lines.append(f"{sha256_file(path)}\t{path.stat().st_size}\t{relative(path)}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def package_release() -> Path:
    ensure_sources()
    run_verifier()
    hits = hard_scan()
    if hits:
        raise SystemExit("HARD_SCAN=FAIL:" + ",".join(hits))

    stamp = now_utc().strftime("%Y%m%d_%H%M%S")
    digest = hashlib.sha256(stamp.encode()).hexdigest()[:8].upper()
    release_id = f"XIAOJ_MEMBER_BROWSER_{stamp}_{digest}"
    release_dir = RELEASE_ROOT / release_id
    packages_dir = release_dir / "packages"
    cockpit_dir = release_dir / "cockpit_pwa"
    extension_dir = release_dir / "extension_mv3"
    release_dir.mkdir(parents=True, exist_ok=False)
    packages_dir.mkdir(parents=True, exist_ok=True)

    copy_files(COCKPIT_FILES, cockpit_dir, "web/xiaoj_member_browser_cockpit")
    copy_files(EXTENSION_FILES, extension_dir, "web/xiaoj_member_browser_extension")
    readme = write_member_readme(release_dir, release_id)

    cockpit_zip = packages_dir / "xiaoj_member_browser_cockpit_pwa.zip"
    extension_zip = packages_dir / "xiaoj_member_browser_extension_mv3.zip"
    zip_dir(cockpit_dir, cockpit_zip)
    zip_dir(extension_dir, extension_zip)

    manifest = build_manifest(release_dir, release_id, [cockpit_zip, extension_zip])
    validate_manifest(manifest)
    manifest_path = release_dir / "RELEASE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))

    sha_path = write_sha256_manifest(release_dir, [cockpit_zip, extension_zip, manifest_path, readme])
    report = {
        "state": "PASS_XIAOJ_MEMBER_BROWSER_RELEASE_PACKAGED",
        "release_id": release_id,
        "release_dir": relative(release_dir),
        "manifest": relative(manifest_path),
        "sha256_manifest": relative(sha_path),
        "packages": [relative(cockpit_zip), relative(extension_zip)],
        "safety_flags": manifest["safety_flags"],
    }
    (release_dir / "RELEASE_VERIFY_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    active = RELEASE_ROOT.parent / "ACTIVE_XIAOJ_MEMBER_BROWSER_RELEASE.json"
    active.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("STATE=PASS_XIAOJ_MEMBER_BROWSER_RELEASE_PACKAGED")
    print("RELEASE_ID=" + release_id)
    print("RELEASE_DIR=" + relative(release_dir))
    print("MANIFEST=" + relative(manifest_path))
    print("SHA256SUMS=" + relative(sha_path))
    print("ACTIVE_RELEASE=" + relative(active))
    for item in report["packages"]:
        print("PACKAGE=" + item)
    return release_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Package XiaoJ member browser release.")
    parser.add_argument("--package", action="store_true", help="Create a release package under runtime/member_browser/releases.")
    args = parser.parse_args()
    if not args.package:
        parser.error("use --package")
    package_release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
