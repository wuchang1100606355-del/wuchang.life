#!/usr/bin/env python3
"""Verify XiaoJ member browser cockpit assets and packet contracts.

This verifier is file-local and sandbox-safe. It does not call cloud services,
does not read secrets, does not read member plaintext stores, and does not write
Odoo or production databases.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COCKPIT = ROOT / "web/xiaoj_member_browser_cockpit"
EXTENSION = ROOT / "web/xiaoj_member_browser_extension"
RELEASE_SCHEMA = ROOT / "schemas/browser/xiaoj_member_browser_release_manifest_v1.schema.json"
PACKAGER = ROOT / "tools/member_browser/package_xiaoj_member_browser_release.py"
BRIDGE_SIMULATOR = ROOT / "tools/member_browser/simulate_xiaoj_browser_bridge.py"
GATEWAY = ROOT / "tools/member_browser/xiaoj_member_browser_gateway.py"
GATEWAY_SCHEMA = ROOT / "schemas/browser/xiaoj_member_browser_gateway_result_v1.schema.json"
ASSOCIATION_ADMISSION_SCHEMA = ROOT / "schemas/browser/xiaoj_association_usage_admission_packet_v1.schema.json"
GATEWAY_EXAMPLE = ROOT / "packets/examples/8d/member_browser_gateway_result_example.json"
NATIVE_HOST = ROOT / "tools/member_browser/xiaoj_member_browser_native_host.py"
NATIVE_HOST_RENDERER = ROOT / "tools/member_browser/render_xiaoj_native_host_manifest.py"
NATIVE_HOST_PROTOCOL_SMOKE = ROOT / "tools/member_browser/smoke_xiaoj_native_host_protocol.py"
NATIVE_HOST_TEMPLATE = ROOT / "web/xiaoj_member_browser_extension/native_host/tw.taiji.xiaoj_member_browser_gateway.template.json"


class IndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {k: v or "" for k, v in attrs}
        if "id" in data:
            self.ids.add(data["id"])
        if tag == "link":
            self.links.append(data.get("href", ""))
        if tag == "script":
            self.scripts.append(data.get("src", ""))


def check(condition: bool, name: str, failures: list[str]) -> None:
    print(f"{name}={'PASS' if condition else 'FAIL'}")
    if not condition:
        failures.append(name)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def verify_web_assets(failures: list[str]) -> None:
    required_files = [
        "index.html",
        "styles.css",
        "app.js",
        "manifest.webmanifest",
        "sw.js",
        "icon.svg",
    ]
    check(all((COCKPIT / f).is_file() for f in required_files), "WEB_ASSETS_PRESENT", failures)

    parser = IndexParser()
    parser.feed((COCKPIT / "index.html").read_text(encoding="utf-8"))
    required_ids = {
        "packetBtn",
        "verifyBtn",
        "cloudBtn",
        "intentText",
        "memberRef",
        "contextRef",
        "keyRef",
        "packetOut",
        "cloudOut",
        "decisionList",
        "actionQueue",
    }
    check(required_ids.issubset(parser.ids), "HTML_CONTROL_IDS_PRESENT", failures)
    check("./manifest.webmanifest" in parser.links, "PWA_MANIFEST_LINKED", failures)
    check("./app.js" in parser.scripts, "APP_JS_LINKED", failures)

    manifest = json.loads((COCKPIT / "manifest.webmanifest").read_text(encoding="utf-8"))
    check(manifest.get("display") == "standalone", "PWA_STANDALONE_DISPLAY", failures)
    check(manifest.get("scope") == "./", "PWA_SCOPE_LOCAL", failures)

    css = (COCKPIT / "styles.css").read_text(encoding="utf-8")
    check("letter-spacing" not in css, "NO_NEGATIVE_LETTER_SPACING", failures)
    check("border-radius: 8px" in css, "UI_RADIUS_EIGHT_PX_PATTERN", failures)


def verify_frontend_contract(failures: list[str]) -> None:
    js = (COCKPIT / "app.js").read_text(encoding="utf-8")
    required_strings = [
        "candidate_only: true",
        "requires_total_field_verify: true",
        "execution_allowed: false",
        "member_plaintext_transferred: false",
        "secret_transferred: false",
        "cloud_compute_ref",
        "behavior_info_ref",
        "activity_rsvp_candidate",
        "public_activity_cache_ref",
        "submit_forbidden: true",
        "dry_run: true",
        "browser_action_bus",
    ]
    check(all(s in js for s in required_strings), "FRONTEND_CONTRACT_STRINGS_PRESENT", failures)

    hard_true = [
        "SECRET_READ" + "=TRUE",
        "MEMBER_PLAINTEXT_READ" + "=TRUE",
        "RAW_AUDIO_SAVED" + "=TRUE",
        "DB_WRITE" + "=TRUE",
        "PAYMENT_CAPTURE" + "=TRUE",
        "DEPLOY" + "=TRUE",
        "SERVICE_RESTART" + "=TRUE",
    ]
    blob = "\n".join((COCKPIT / f).read_text(encoding="utf-8") for f in ["index.html", "styles.css", "app.js", "manifest.webmanifest", "sw.js"])
    check(not any(flag in blob for flag in hard_true), "NO_HARD_TRUE_FLAGS_IN_COCKPIT", failures)


def verify_extension_bridge(failures: list[str]) -> None:
    required_files = [
        "manifest.json",
        "background.js",
        "sidepanel.html",
        "sidepanel.js",
        "sidepanel.css",
        "README.md",
    ]
    check(all((EXTENSION / f).is_file() for f in required_files), "EXTENSION_ASSETS_PRESENT", failures)

    manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    permissions = set(manifest.get("permissions", []))
    expected_permissions = {"activeTab", "nativeMessaging", "scripting", "sidePanel", "storage"}
    check(manifest.get("manifest_version") == 3, "EXTENSION_MANIFEST_V3", failures)
    check(permissions == expected_permissions, "EXTENSION_MINIMUM_PERMISSION_SET", failures)
    check(manifest.get("host_permissions", []) == [], "EXTENSION_NO_HOST_PERMISSIONS", failures)
    check("cookies" not in permissions, "EXTENSION_NO_COOKIE_PERMISSION", failures)
    check(manifest.get("host_permissions", []) == [], "EXTENSION_STILL_NO_WEB_HOST_PERMISSIONS", failures)

    parser = IndexParser()
    parser.feed((EXTENSION / "sidepanel.html").read_text(encoding="utf-8"))
    required_ids = {"intentText", "actionType", "draftText", "humanConfirmed", "runBtn", "resultOut", "packetOut", "decisionText"}
    check(required_ids.issubset(parser.ids), "EXTENSION_SIDEPANEL_IDS_PRESENT", failures)

    background = (EXTENSION / "background.js").read_text(encoding="utf-8")
    sidepanel = (EXTENSION / "sidepanel.js").read_text(encoding="utf-8")
    combined = background + "\n" + sidepanel
    blocked_api_patterns = [
        "chrome.cookies",
        "document.cookie",
        "localStorage.",
        "sessionStorage.",
        ".submit()",
        "fetch(",
        "XMLHttpRequest",
        "eval(",
    ]
    check(not any(pattern in combined for pattern in blocked_api_patterns), "EXTENSION_NO_BLOCKED_BROWSER_APIS", failures)
    check('"open_sidebar_ref"' in background and '"read_text_ref"' in background and '"write_draft_ref"' in background, "EXTENSION_ALLOWED_ACTIONS_DECLARED", failures)
    check("draft_ref" in sidepanel and "draft_preview" not in sidepanel, "EXTENSION_DRAFT_REF_ONLY", failures)
    check("localDraftText" in background and "raw_draft_returned: false" in background, "EXTENSION_LOCAL_DRAFT_NOT_RETURNED", failures)
    check("selected_text_ref" in background and "raw_text_returned: false" in background, "EXTENSION_SELECTED_TEXT_REF_ONLY", failures)
    check("xiaoj.browser_bridge_return_packet.v1" in background, "EXTENSION_BRIDGE_RETURN_SCHEMA_EMITTED", failures)
    check("BROWSER_BRIDGE_RETURN_PACKET" in background, "EXTENSION_BRIDGE_RETURN_PACKET_EMITTED", failures)
    check("cloud_compute_ref" in background and "behavior_info_ref" in background and "action_trace_ref" in background, "EXTENSION_BRIDGE_RETURN_REFS_PRESENT", failures)
    check("tw.taiji.xiaoj_member_browser_gateway" in background, "EXTENSION_NATIVE_HOST_NAME_PRESENT", failures)
    check("XIAOJ_NATIVE_GATEWAY_REQUEST" in background and "native_gateway_unavailable" in background, "EXTENSION_NATIVE_GATEWAY_FALLBACK_PRESENT", failures)

    schema_path = ROOT / "schemas/browser/xiaoj_browser_bridge_return_packet_v1.schema.json"
    check(schema_path.is_file(), "BROWSER_BRIDGE_RETURN_SCHEMA_PRESENT", failures)
    if schema_path.is_file():
        try:
            from jsonschema import validate

            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            fixture = {
                "schema_version": "xiaoj.browser_bridge_return_packet.v1",
                "packet_type": "BROWSER_BRIDGE_RETURN_PACKET",
                "candidate_only": True,
                "must_not_execute": True,
                "requires_total_field_verify": True,
                "member_plaintext_transferred": False,
                "secret_transferred": False,
                "raw_browser_page_transferred": False,
                "raw_text_returned": False,
                "D1_identity": {
                    "actor_ref": "actor_ref:member_browser_extension:active_member",
                    "device_ref": "device_ref:member_browser_extension:chrome_mv3",
                    "plaintext_identity_forbidden": True,
                },
                "D2_intent": {
                    "intent_ref": "intent_ref:demo",
                    "action_type_candidate": "read_text_ref",
                    "bridge_decision": "ALLOW_LOCAL_MINIMUM_PRIVILEGE",
                },
                "D3_state": {
                    "browser_result_ref": "browser_result_ref:demo",
                    "execution_allowed": False,
                    "dry_run": True,
                    "submit_forbidden": True,
                },
                "D4_evidence": {
                    "behavior_info_ref": "behavior_ref:demo",
                    "action_trace_ref": "action_trace_ref:demo",
                    "selected_text_ref": "selected_text_ref:demo",
                    "draft_ref": "draft_ref:none",
                },
                "D5_execution": {
                    "execution_allowed": False,
                    "allowed_next_actions": ["present_candidate"],
                    "forbidden_actions": ["payment_capture"],
                    "human_confirm_required": False,
                },
                "D6_generative_transmission": {
                    "return_mode": "browser_bridge_packetized_candidate_result",
                    "cloud_compute_ref": "cloud_compute_ref:local_1b_first_extension_bridge",
                    "reconstruction_hint_ref": "reconstruct_ref:demo",
                    "cloud_candidate_only": True,
                    "member_plaintext_transferred": False,
                    "secret_transferred": False,
                },
                "D7_risk": {
                    "bridge_ok": True,
                    "decision": "ALLOW_LOCAL_MINIMUM_PRIVILEGE",
                    "reason_ref": "reason_ref:demo",
                },
                "D8_envelope": {
                    "ttl_seconds": 300,
                    "nonce": "nonce_ref:demo",
                    "created_at": "2026-06-27T00:00:00+00:00",
                    "return_packet_hash": "return_packet_hash:demo",
                    "total_field_verifier_required": True,
                    "replay_protection": True,
                },
            }
            validate(fixture, schema)
            check(True, "BROWSER_BRIDGE_RETURN_SCHEMA_VALIDATE", failures)
        except Exception as exc:
            print(f"BROWSER_BRIDGE_RETURN_SCHEMA_VALIDATE=FAIL:{exc}")
            failures.append("BROWSER_BRIDGE_RETURN_SCHEMA_VALIDATE")


def verify_native_host(failures: list[str]) -> None:
    check(NATIVE_HOST.is_file(), "NATIVE_HOST_PRESENT", failures)
    check(NATIVE_HOST_RENDERER.is_file(), "NATIVE_HOST_RENDERER_PRESENT", failures)
    check(NATIVE_HOST_PROTOCOL_SMOKE.is_file(), "NATIVE_HOST_PROTOCOL_SMOKE_PRESENT", failures)
    check(NATIVE_HOST_TEMPLATE.is_file(), "NATIVE_HOST_TEMPLATE_PRESENT", failures)
    if NATIVE_HOST_TEMPLATE.is_file():
        template = json.loads(NATIVE_HOST_TEMPLATE.read_text(encoding="utf-8"))
        check(template.get("name") == "tw.taiji.xiaoj_member_browser_gateway", "NATIVE_HOST_TEMPLATE_NAME", failures)
        check(template.get("type") == "stdio", "NATIVE_HOST_TEMPLATE_STDIO", failures)
        check("__EXTENSION_ID__" in "".join(template.get("allowed_origins", [])), "NATIVE_HOST_TEMPLATE_EXTENSION_PLACEHOLDER", failures)
    if NATIVE_HOST.is_file():
        payload = json.dumps({
            "type": "XIAOJ_NATIVE_GATEWAY_REQUEST",
            "intent": "請幫我摘要目前選取的公告文字",
            "safe_context_ref": "redacted_ref:native_verify",
            "selected_text": "公告測試",
        })
        proc = run([sys.executable, str(NATIVE_HOST), "--once-json", payload])
        ok = (
            proc.returncode == 0
            and '"candidate_only": true' in proc.stdout
            and '"member_plaintext_transferred": false' in proc.stdout
            and '"secret_transferred": false' in proc.stdout
            and '"gateway_result"' in proc.stdout
        )
        check(ok, "NATIVE_HOST_ONCE_JSON", failures)
        if not ok:
            sys.stdout.write(proc.stdout)
            sys.stderr.write(proc.stderr)
    if NATIVE_HOST_RENDERER.is_file():
        proc = run([sys.executable, str(NATIVE_HOST_RENDERER), "--extension-id", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"])
        ok = proc.returncode == 0 and "STATE=PASS_NATIVE_HOST_MANIFEST_RENDERED" in proc.stdout
        check(ok, "NATIVE_HOST_MANIFEST_RENDER", failures)
        rendered = ROOT / "runtime/member_browser/native_host/tw.taiji.xiaoj_member_browser_gateway.json"
        if rendered.is_file():
            data = json.loads(rendered.read_text(encoding="utf-8"))
            check(data.get("allowed_origins") == ["chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/"], "NATIVE_HOST_RENDERED_ALLOWED_ORIGIN", failures)
    if NATIVE_HOST_PROTOCOL_SMOKE.is_file():
        proc = run([sys.executable, str(NATIVE_HOST_PROTOCOL_SMOKE)])
        ok = proc.returncode == 0 and "STATE=PASS_XIAOJ_NATIVE_HOST_PROTOCOL" in proc.stdout
        check(ok, "NATIVE_HOST_PROTOCOL_SMOKE", failures)
        if not ok:
            sys.stdout.write(proc.stdout)
            sys.stderr.write(proc.stderr)


def verify_bridge_simulator(failures: list[str]) -> None:
    check(BRIDGE_SIMULATOR.is_file(), "BRIDGE_SIMULATOR_PRESENT", failures)
    if not BRIDGE_SIMULATOR.is_file():
        return
    proc = run([sys.executable, str(BRIDGE_SIMULATOR), "--smoke"])
    required = [
        "CASE_open_sidebar=PASS",
        "CASE_read_selected_text=PASS",
        "CASE_write_draft_unconfirmed=PASS",
        "CASE_write_draft_confirmed=PASS",
        "CASE_write_draft_sensitive=PASS",
        "CASE_write_draft_sensitive_field=PASS",
        "CASE_submit_payment_blocked=PASS",
        "CASE_cookie_read_blocked=PASS",
        "STATE=PASS_XIAOJ_BROWSER_BRIDGE_SIMULATOR",
    ]
    ok = proc.returncode == 0 and all(item in proc.stdout for item in required)
    check(ok, "BRIDGE_SIMULATOR_SMOKE", failures)
    if not ok:
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)


def verify_gateway(failures: list[str]) -> None:
    check(GATEWAY.is_file(), "GATEWAY_PRESENT", failures)
    check(GATEWAY_SCHEMA.is_file(), "GATEWAY_SCHEMA_PRESENT", failures)
    check(ASSOCIATION_ADMISSION_SCHEMA.is_file(), "ASSOCIATION_ADMISSION_SCHEMA_PRESENT", failures)
    if not GATEWAY.is_file():
        return
    proc = run([sys.executable, str(GATEWAY), "--smoke"])
    required = [
        "CASE_summary=PASS",
        "CASE_open_sidebar=PASS",
        "CASE_draft_hold=PASS",
        "CASE_activity_rsvp_hold=PASS",
        "CASE_payment_block=PASS",
        "STATE=PASS_XIAOJ_MEMBER_BROWSER_GATEWAY",
    ]
    ok = proc.returncode == 0 and all(item in proc.stdout for item in required)
    check(ok, "GATEWAY_SMOKE", failures)
    if not ok:
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
    check(GATEWAY_EXAMPLE.is_file(), "GATEWAY_EXAMPLE_PRESENT", failures)
    if GATEWAY_SCHEMA.is_file() and ASSOCIATION_ADMISSION_SCHEMA.is_file() and GATEWAY_EXAMPLE.is_file():
        try:
            from jsonschema import validate

            schema = json.loads(GATEWAY_SCHEMA.read_text(encoding="utf-8"))
            admission_schema = json.loads(ASSOCIATION_ADMISSION_SCHEMA.read_text(encoding="utf-8"))
            example = json.loads(GATEWAY_EXAMPLE.read_text(encoding="utf-8"))
            validate(example, schema)
            admission = example["association_usage_admission_packet"]
            validate(admission, admission_schema)
            example_ok = (
                example.get("state") == "CANDIDATE_READY"
                and example.get("candidate_only") is True
                and example.get("member_plaintext_transferred") is False
                and example.get("secret_transferred") is False
                and example.get("cloud_candidate_return_packet", {}).get("d5_execution", {}).get("execution_allowed") is False
                and admission.get("candidate_only") is True
                and admission.get("execution_allowed") is False
                and admission.get("member_plaintext_transferred") is False
                and admission.get("secret_transferred") is False
                and admission.get("raw_api_key_transferred") is False
                and admission.get("oauth_token_transferred") is False
                and admission.get("D5_execution", {}).get("admission_decision") == "ALLOW"
                and admission.get("D5_execution", {}).get("odoo_write_authority") is False
                and admission.get("D5_execution", {}).get("odoo_member_plaintext_read") is False
                and admission.get("D5_execution", {}).get("payment_capture_authority") is False
                and admission.get("D5_execution", {}).get("payment_data_transferred") is False
                and admission.get("D3_state", {}).get("odoo_identity_ref", "").startswith("odoo_identity_ref:")
                and admission.get("D3_state", {}).get("odoo_role_ref", "").startswith("odoo_role_ref:")
                and admission.get("D3_state", {}).get("odoo_function_item_set_ref", "").startswith("odoo_function_item_set_ref:")
                and admission.get("D3_state", {}).get("payment_tool_ref", "").startswith("payment_tool_ref:")
                and admission.get("D3_state", {}).get("management_fee_bill_ref", "").startswith("management_fee_bill_ref:")
                and admission.get("D3_state", {}).get("payment_intent_ref", "").startswith("payment_intent_ref:")
                and bool(admission.get("D4_evidence", {}).get("odoo_function_item_refs"))
                and admission.get("D4_evidence", {}).get("cloud_compute_ref", "").startswith("CLOUD_COMPUTE_REF:")
                and admission.get("D4_evidence", {}).get("behavior_info_ref", "").startswith("BEHAVIOR_INFO_REF:")
            )
            check(example_ok, "GATEWAY_EXAMPLE_SCHEMA_AND_CONTRACT", failures)
        except Exception as exc:
            print(f"GATEWAY_EXAMPLE_SCHEMA_AND_CONTRACT=FAIL:{exc}")
            failures.append("GATEWAY_EXAMPLE_SCHEMA_AND_CONTRACT")


def verify_controller_and_cloud_contract(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        packet_path = Path(tmp) / "member_browser_packet.json"
        cmd = [
            sys.executable,
            "tools/member_browser/xiaoj_member_browser_1b_controller.py",
            "--intent",
            "打開小J側邊欄並摘要我選取的公告文字，要用我偏好的簡潔模式",
            "--safe-context-ref",
            "redacted_ref:selected_text_hash_demo",
            "--member-preference-ref",
            "preference_ref:member:concise_accessible_daily",
            "--service-style-ref",
            "service_style_ref:community_xiaoj_warm_daily",
            "--cloud-compute-ref",
            "cloud_compute_ref:local_1b_first_cloud_candidate_if_needed",
            "--out",
            str(packet_path),
        ]
        generated = run(cmd)
        check(generated.returncode == 0 and packet_path.is_file(), "CONTROLLER_PACKET_GENERATED", failures)

        sdk = run([sys.executable, "sdk/python/w7tp_8d_packet.py", str(packet_path)])
        sdk_ok = sdk.returncode == 0 and '"ok": true' in sdk.stdout
        check(sdk_ok, "CONTROLLER_PACKET_SDK_VERIFY", failures)

        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        params = packet["browser_action"]["params"]
        check(packet["D4_topology"]["channel"] == "browser_action_bus", "CONTROLLER_CHANNEL_BROWSER_ACTION_BUS", failures)
        check(packet["D5_resource"]["model_tier"] == "small", "CONTROLLER_MODEL_TIER_SMALL", failures)
        check(packet["D5_resource"]["cost_policy"] == "budget_cap_ref", "CONTROLLER_COST_POLICY_REF", failures)
        check(params["member_preference_ref"].startswith("preference_ref:"), "CONTROLLER_MEMBER_PREFERENCE_REF", failures)
        check(params["cloud_compute_ref"].startswith("cloud_compute_ref:"), "CONTROLLER_CLOUD_COMPUTE_REF", failures)
        check(params["behavior_info_ref"].startswith("behavior_ref:"), "CONTROLLER_BEHAVIOR_INFO_REF", failures)
        check(params["odoo_identity_ref"].startswith("odoo_identity_ref:"), "CONTROLLER_ODOO_IDENTITY_REF", failures)
        check(params["odoo_role_ref"].startswith("odoo_role_ref:"), "CONTROLLER_ODOO_ROLE_REF", failures)
        check("odoo_function_ref:resident.activity_rsvp_candidate" in params["odoo_function_item_refs_csv"], "CONTROLLER_ODOO_ACTIVITY_RSVP_FUNCTION", failures)
        check("odoo_function_ref:resident.management_fee_payment_intent_candidate" in params["odoo_function_item_refs_csv"], "CONTROLLER_ODOO_MANAGEMENT_FEE_FUNCTION", failures)
        check(params["payment_tool_ref"].startswith("payment_tool_ref:"), "CONTROLLER_PAYMENT_TOOL_REF", failures)
        check(params["payment_capture_authority"] is False, "CONTROLLER_PAYMENT_CAPTURE_FALSE", failures)

        activity_packet_path = Path(tmp) / "member_browser_activity_packet.json"
        activity_generated = run([
            sys.executable,
            "tools/member_browser/xiaoj_member_browser_1b_controller.py",
            "--intent",
            "我要報名社區活動，請先產生候選草稿",
            "--safe-context-ref",
            "redacted_ref:community_event_notice_hash",
            "--out",
            str(activity_packet_path),
        ])
        activity_ok = activity_generated.returncode == 0 and activity_packet_path.is_file()
        check(activity_ok, "CONTROLLER_ACTIVITY_PACKET_GENERATED", failures)
        if activity_ok:
            activity_packet = json.loads(activity_packet_path.read_text(encoding="utf-8"))
            check(activity_packet["browser_action"]["action_type"] == "write_draft_ref", "CONTROLLER_ACTIVITY_RSVP_ACTION_DRAFT", failures)
            check(activity_packet["D2_intent"]["transaction_intent"] == "activity_rsvp_candidate", "CONTROLLER_ACTIVITY_RSVP_INTENT", failures)
            check(activity_packet["D6_governance"]["human_confirm_required"] is True, "CONTROLLER_ACTIVITY_RSVP_HUMAN_CONFIRM", failures)
            check(activity_packet["browser_action"]["params"]["candidate_only"] is True, "CONTROLLER_ACTIVITY_RSVP_CANDIDATE_ONLY", failures)
            check(activity_packet["browser_action"]["params"]["public_activity_cache_ref"] == "public_activity_cache_ref:web/community_activities.json", "CONTROLLER_ACTIVITY_PUBLIC_CACHE_REF", failures)

    cloud_check = run([
        sys.executable,
        "-c",
        (
            "import json;"
            "from jsonschema import validate;"
            "from pathlib import Path;"
            "from tools.cloud_proxy.w7tp_openwebui_cloud_proxy import build_cloud_candidate_return_packet,dump,h,validate_cloud_candidate_return_packet;"
            "schema=json.loads(Path('schemas/cloud_proxy/w7tp_cloud_candidate_return_packet_v1.schema.json').read_text());"
            "packet={'task_id':'TASK_abcdef123456','packet_id':'PKT_abcdef123456','D2_intent':{'intent':'member_benefit_candidate'},'D4_topology':{'cloud_lane':'safe_local_stub'}};"
            "candidate={'candidate_id':'CAND_abcdef123456','risk_flags':['member_benefit'],'must_not_execute':True,'cloud_received_packet_only':True};"
            "ret=build_cloud_candidate_return_packet(packet,h(dump(packet)),'JOB_abcdef123456',candidate,'CANDIDATE_READY');"
            "ok,reason=validate_cloud_candidate_return_packet(ret);"
            "validate(ret,schema);"
            "print('ok='+str(ok).lower());"
            "print('reason='+reason);"
            "print('cloud_compute_ref='+ret['d3_coordinate']['cloud_compute_ref']);"
            "print('behavior_info_ref='+ret['d4_evidence']['behavior_info_ref']);"
            "raise SystemExit(0 if ok and ret['d3_coordinate']['cloud_compute_ref'] and ret['d4_evidence']['behavior_info_ref'] and ret['d5_execution']['execution_allowed'] is False else 1)"
        ),
    ])
    check(cloud_check.returncode == 0, "CLOUD_RETURN_PACKET_SCHEMA_AND_REFS", failures)


def verify_release_packaging_contract(failures: list[str]) -> None:
    check(PACKAGER.is_file(), "RELEASE_PACKAGER_PRESENT", failures)
    check(RELEASE_SCHEMA.is_file(), "RELEASE_MANIFEST_SCHEMA_PRESENT", failures)
    if not PACKAGER.is_file() or not RELEASE_SCHEMA.is_file():
        return

    try:
        from jsonschema import validate

        schema = json.loads(RELEASE_SCHEMA.read_text(encoding="utf-8"))
        fixture = {
            "schema_version": "xiaoj.member_browser_release_manifest.v1",
            "release_id": "XIAOJ_MEMBER_BROWSER_20260627_000000_ABCDEF12",
            "created_at": "2026-06-27T00:00:00+00:00",
            "product_name": "小J會員主權 AI 瀏覽器座艙",
            "scope": [
                "local_1b_member_browser_controller",
                "member_preference_ref_service_style",
                "mv3_minimum_privilege_browser_bridge",
            ],
            "state": "VERIFY_PASS",
            "packages": [
                {"name": "xiaoj_member_browser_cockpit_pwa.zip", "path": "runtime/member_browser/releases/demo/packages/xiaoj_member_browser_cockpit_pwa.zip", "sha256": "a" * 64, "bytes": 1},
                {"name": "xiaoj_member_browser_extension_mv3.zip", "path": "runtime/member_browser/releases/demo/packages/xiaoj_member_browser_extension_mv3.zip", "sha256": "b" * 64, "bytes": 1},
            ],
            "included_sources": [
                {"path": f"source_{i}.txt", "sha256": "c" * 64, "bytes": 1}
                for i in range(10)
            ],
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
                "blocked_actions": ["submit_payment", "read_raw_cookie", "db_write", "deploy", "service_restart"],
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
        validate(fixture, schema)
        check(True, "RELEASE_MANIFEST_SCHEMA_VALIDATE", failures)
    except Exception as exc:
        print(f"RELEASE_MANIFEST_SCHEMA_VALIDATE=FAIL:{exc}")
        failures.append("RELEASE_MANIFEST_SCHEMA_VALIDATE")

    packager_text = PACKAGER.read_text(encoding="utf-8")
    check("COCKPIT_FILES" in packager_text and "EXTENSION_FILES" in packager_text, "RELEASE_PACKAGER_WHITELISTED_FILES", failures)
    check("zipfile.ZipFile" in packager_text and "RELEASE_MANIFEST.json" in packager_text, "RELEASE_PACKAGER_ZIP_AND_MANIFEST", failures)


def main() -> int:
    failures: list[str] = []
    verify_web_assets(failures)
    verify_frontend_contract(failures)
    verify_extension_bridge(failures)
    verify_native_host(failures)
    verify_bridge_simulator(failures)
    verify_gateway(failures)
    verify_controller_and_cloud_contract(failures)
    verify_release_packaging_contract(failures)
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RAW_AUDIO_SAVED=FALSE")
    print("DB_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    print("STATE=" + ("PASS_XIAOJ_MEMBER_BROWSER_COCKPIT" if not failures else "FAIL_XIAOJ_MEMBER_BROWSER_COCKPIT"))
    if failures:
        print("FAILURES=" + ",".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
