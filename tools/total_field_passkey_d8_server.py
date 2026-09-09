#!/usr/bin/env python3
"""Browser ceremony for founder-present platform-passkey D8 approval."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
from datetime import timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fido2.utils import websafe_encode
from fido2.webauthn import (
    AuthenticatorAttachment,
    AuthenticationResponse,
    PublicKeyCredentialUserEntity,
    RegistrationResponse,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from tools.total_field_passkey_d8 import (
    DEPLOY_RESTART_SCOPE,
    EXACT_REPAIR_SCOPE,
    GIT_PUSH_SCOPE,
    RECEIVE_CANDIDATE_SCOPE,
    PASSKEY_APPROVAL_SCHEMA,
    PASSKEY_APPROVAL_STATE,
    PASSKEY_CREDENTIAL_SCHEMA,
    PASSKEY_POINTER_SCHEMA,
    PasskeyD8Rejected,
    approval_challenge,
    atomic_json,
    build_server,
    canonical_json,
    iso_z,
    load_credential,
    load_json,
    normalized_scopes,
    parse_time,
    require_admitted_authenticator,
    safe_runtime_ref,
    sha256,
    utc_now,
)

CONFIG_REL = Path("configs/total_field/git_push_review_gate_v1.json")
REVIEW_SCHEMA = "W7TP_TOTAL_FIELD_GIT_PUSH_REVIEW_REGISTRATION_V1"
REVIEW_STATE = "PASS_TOTAL_FIELD_REVIEW_REGISTERED"
REQUEST_SCHEMA = "W7TP_TOTAL_FIELD_GIT_PUSH_REVIEW_REQUEST_V1"
RECEIVE_REVIEW_SCHEMA = "W7TP_TOTAL_FIELD_RECEIVE_CANDIDATE_REVIEW_REGISTRATION_V1"
RECEIVE_REQUEST_SCHEMA = "W7TP_TOTAL_FIELD_RECEIVE_CANDIDATE_REVIEW_REQUEST_V1"
EXACT_REPAIR_REVIEW_SCHEMA = "W7TP_TOTAL_FIELD_EXACT_REPAIR_REVIEW_REGISTRATION_V1"
EXACT_REPAIR_ROOT = "/home/taiji_admin/Taiji_Hub"
EXACT_REPAIR_BRANCH = "agent/moving-v-v2-taiji8d-local-canary"
EXACT_REPAIR_HEAD = "dd9b24c15e97564e19dc0a069d4cc96b735773f0"
EXACT_REPAIR_FILE = "tools/total_field_dynamic_context.py"
EXACT_REPAIR_FUNCTION = "build_dynamic_context"
EXACT_REPAIR_INTENT = "閉合第一動態上下文污染入口，使 8D/ADI 譜系資格先於語義排序"
EXACT_REPAIR_PROHIBITED_EFFECTS = [
    "DEPLOY", "SERVICE_RESTART", "POINTER_CHANGE", "CANONICAL_CHANGE",
    "RECEIVER_VERSION_CHANGE", "CROSS_LINEAGE_SUCCESSOR",
    "V2_3_TO_V2_1_PROJECTION", "HISTORICAL_FILE_DELETE",
    "GENERAL_REFACTOR", "GIT_PUSH",
]
HTML = r"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>小J 總場本機簽發</title>
<style>
body{margin:0;background:#071019;color:#eaf6ff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:680px;margin:auto;padding:28px 20px 60px}.card{background:#0d1c29;border:1px solid #28465d;border-radius:20px;padding:24px;box-shadow:0 20px 60px #0008}
h1{font-size:28px;margin:0 0 8px}.sub{color:#94bfd7;margin:0 0 24px}.state{padding:14px;border-radius:12px;background:#09141e;margin:16px 0;white-space:pre-wrap;word-break:break-word}
button{width:100%;border:0;border-radius:14px;padding:16px;margin:8px 0;font-size:18px;font-weight:700;background:#39d8a0;color:#04120d}button.secondary{background:#263d51;color:#eaf6ff}button:disabled{opacity:.45}
.rules{font-size:14px;line-height:1.65;color:#bdd5e3}.ok{color:#54e3a9}.bad{color:#ff8c8c}.label{color:#7fa9bf}
</style></head><body><main><div class="card">
<h1>小J 總場創辦人簽發</h1><p class="sub">手機沒有既有密鑰時，先以 Face ID 建立新密鑰；不需要輸入任何舊密碼。</p>
<div id="status" class="state">正在讀取簽發狀態…</div>
<button id="enrol" class="secondary">建立手機 Face ID 通行密鑰</button>
	<button id="approve">檢視並簽發本次精確作用</button>
	<button id="receive">核可原胞融合能力接收</button>
	<button id="exact-repair">核可第一污染入口精確修復</button>
	<div class="rules">只授權畫面列出的作用、分支、目標樹、檔案集合與五分鐘時限；不授權正典或活動指標修改。任一座標漂移，簽發即失效。Apple、Google、Tailscale 與瀏覽器均不是總場權威。</div>
</div></main><script>
const q=new URLSearchParams(location.search), token=q.get('bootstrap')||localStorage.getItem('w7tp-bootstrap')||'';
if(token)localStorage.setItem('w7tp-bootstrap',token);
const statusEl=document.getElementById('status');
const enc=b=>{const x=new Uint8Array(b);let s='';x.forEach(v=>s+=String.fromCharCode(v));return btoa(s).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'')};
const dec=s=>{s=s.replace(/-/g,'+').replace(/_/g,'/');while(s.length%4)s+='=';const b=atob(s),x=new Uint8Array(b.length);for(let i=0;i<b.length;i++)x[i]=b.charCodeAt(i);return x.buffer};
const post=async(path,body={})=>{const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-W7TP-Bootstrap':token},body:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw Error(j.reason||j.state||r.status);return j};
const creation=o=>{const p=o.publicKey;p.challenge=dec(p.challenge);p.user.id=dec(p.user.id);(p.excludeCredentials||[]).forEach(c=>c.id=dec(c.id));return {publicKey:p}};
const request=o=>{const p=o.publicKey;p.challenge=dec(p.challenge);(p.allowCredentials||[]).forEach(c=>c.id=dec(c.id));return {publicKey:p}};
const regJSON=c=>({id:c.id,rawId:enc(c.rawId),type:c.type,authenticatorAttachment:c.authenticatorAttachment,clientExtensionResults:c.getClientExtensionResults(),response:{clientDataJSON:enc(c.response.clientDataJSON),attestationObject:enc(c.response.attestationObject),transports:c.response.getTransports?c.response.getTransports():[]}});
const authJSON=c=>({id:c.id,rawId:enc(c.rawId),type:c.type,authenticatorAttachment:c.authenticatorAttachment,clientExtensionResults:c.getClientExtensionResults(),response:{clientDataJSON:enc(c.response.clientDataJSON),authenticatorData:enc(c.response.authenticatorData),signature:enc(c.response.signature),userHandle:c.response.userHandle?enc(c.response.userHandle):null}});
const show=(m,ok=true)=>{statusEl.textContent=m;statusEl.className='state '+(ok?'ok':'bad')};
let enrolled=false;
async function refresh(){try{const r=await fetch('/health');const j=await r.json();enrolled=Boolean(j.enrolled);const b=document.getElementById('enrol');b.disabled=false;b.textContent=enrolled?'手機沒有舊密鑰：重新建立 Face ID 通行密鑰':'首次建立手機 Face ID 通行密鑰';show(`狀態：${j.state}\n通行密鑰：${j.credential_state_zh_TW}\n簽發器：${j.signer_zh_TW}\n待簽範圍：${j.scope_zh_TW}`)}catch(e){show('無法連到總場簽發服務：'+e.message,false)}}
document.getElementById('enrol').onclick=async()=>{try{const mode=enrolled?'rotate':'register';show('即將在手機建立一把新的 Face ID 通行密鑰；這不是輸入舊密碼。舊密鑰會保留到新密鑰建立成功。');const o=await post(`/v1/passkey/${mode}/options`);const c=await navigator.credentials.create(creation(o.options));const r=await post(`/v1/passkey/${mode}/complete`,{response:regJSON(c),ceremony_id:o.ceremony_id});show(r.message_zh_TW);await refresh()}catch(e){show('新密鑰尚未建立：'+e.message,false)}};
document.getElementById('approve').onclick=async()=>{try{show('正在建立綁定本次變更的五分鐘簽發挑戰…');const o=await post('/v1/passkey/approve/options');const d=o.display;const deployment=d.deploy_node?`\n部署節點：${d.deploy_node}\n服務：${d.deploy_service}`:'';const yes=confirm(`只簽發以下作用：\n範圍：${d.scope_zh_TW}\n分支：${d.branch}\n目標樹：${d.target_tree}\n檔案數：${d.file_count}${deployment}\n有效：5 分鐘\n\n確定後請使用已登記的創辦人平台通行密鑰解鎖。`);if(!yes){show('你已取消，未簽發。',false);return}const c=await navigator.credentials.get(request(o.options));const r=await post('/v1/passkey/approve/complete',{response:authJSON(c),ceremony_id:o.ceremony_id});show(r.message_zh_TW+'\n簽發收據：'+r.approval_sha256)}catch(e){show('簽發未完成：'+e.message,false)}};
document.getElementById('receive').onclick=async()=>{try{show('正在建立只綁定原胞融合能力雜湊的五分鐘簽發挑戰…');const o=await post('/v1/passkey/receive-candidate/options');const d=o.display;const yes=confirm(`只簽發以下作用：\n範圍：${d.scope_zh_TW}\n能力：${d.candidate_id}\n能力封包：${d.candidate_packet_sha256}\n技能索引：${d.skill_index_sha256}\n有效：5 分鐘\n\n不授權部署、重啟、Git 推送或正典修改。確定後請使用已登記的創辦人平台通行密鑰解鎖。`);if(!yes){show('你已取消，未簽發。',false);return}const c=await navigator.credentials.get(request(o.options));const r=await post('/v1/passkey/receive-candidate/complete',{response:authJSON(c),ceremony_id:o.ceremony_id});show(r.message_zh_TW+'\n簽發收據：'+r.approval_sha256)}catch(e){show('簽發未完成：'+e.message,false)}};
document.getElementById('exact-repair').onclick=async()=>{try{show('正在重驗 HEAD 並建立第一污染入口五分鐘精確修復挑戰…');const o=await post('/v1/passkey/exact-repair/options');const d=o.display;const yes=confirm(`只簽發以下作用：\n範圍：${d.scope_zh_TW}\n分支：${d.branch}\nHEAD：${d.head}\n檔案：${d.file}\n函式：${d.function}\n有效：5 分鐘\n\n禁止部署、重啟、pointer／canonical 修改、跨譜系推定、一般重構與 Git 推送。確定後請使用已登記的創辦人通行密鑰解鎖。`);if(!yes){show('你已取消，未簽發。',false);return}const c=await navigator.credentials.get(request(o.options));const r=await post('/v1/passkey/exact-repair/complete',{response:authJSON(c),ceremony_id:o.ceremony_id});show(r.message_zh_TW+'\n簽發收據：'+r.approval_sha256)}catch(e){show('簽發未完成：'+e.message,false)}};
refresh();
</script></body></html>"""


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


class PasskeyApplication:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.config = load_json(self.root / CONFIG_REL, "PASSKEY_CONFIG_INVALID")
        self.passkey = self.config.get("passkey_verifier") or {}
        if self.passkey.get("enabled") is not True:
            raise PasskeyD8Rejected("PASSKEY_VERIFIER_NOT_ACTIVE")
        self.server = build_server(
            str(self.passkey["rp_id"]), str(self.passkey["rp_name"]), str(self.passkey["expected_origin"])
        )
        self.state_root = self.root.joinpath(*PurePosixPath(str(self.passkey["runtime_state_ref"])).parts)
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.bootstrap_path = self.state_root / "bootstrap.token"
        if not self.bootstrap_path.exists() and not (self.root / str(self.passkey["credential_ref"])).exists():
            self.bootstrap_path.write_text(secrets.token_urlsafe(32), encoding="ascii")
            os.chmod(self.bootstrap_path, 0o600)

    def bootstrap_token(self) -> str:
        return self.bootstrap_path.read_text(encoding="ascii").strip() if self.bootstrap_path.exists() else ""

    def require_bootstrap(self, supplied: str) -> None:
        expected = self.bootstrap_token()
        if expected and not supplied and self.passkey.get("local_bootstrap_without_token") is True:
            return
        if expected and not secrets.compare_digest(supplied, expected):
            raise PasskeyD8Rejected("首次註冊碼不符")

    def credential_path(self) -> Path:
        return self.root.joinpath(*PurePosixPath(str(self.passkey["credential_ref"])).parts)

    def health(self) -> dict[str, Any]:
        enrolled = self.credential_path().is_file()
        return {
            "state": "READY_FOR_LOCAL_APPROVAL" if enrolled else "READY_FOR_LOCAL_ENROLMENT",
            "enrolled": enrolled,
            "credential_state_zh_TW": "已註冊" if enrolled else "尚未註冊",
            "signer_zh_TW": "創辦人已登記的平台通行密鑰",
            "scope_zh_TW": "只允許精確、單次、五分鐘內的正式 Git 推送、指定服務部署重啟或綁定雜湊的候選能力接收",
            "provider_is_authority": False,
            "total_field_is_effect_authority": True,
        }

    def require_client(self, user_agent: str) -> None:
        required = str(self.passkey.get("required_client_user_agent_contains") or "")
        if required and required not in user_agent:
            raise PasskeyD8Rejected("簽發裝置不符合總場限制")

    def register_options(self, supplied: str, user_agent: str, *, rotate: bool = False) -> dict[str, Any]:
        credential_path = self.credential_path()
        if credential_path.exists() and not rotate:
            raise PasskeyD8Rejected("通行密鑰已註冊，禁止覆寫")
        if rotate and not credential_path.exists():
            raise PasskeyD8Rejected("尚無舊密鑰，請使用首次建立")
        self.require_bootstrap(supplied)
        self.require_client(user_agent)
        ceremony_id = secrets.token_hex(16)
        previous_credential_sha256 = sha256(credential_path.read_bytes()) if rotate else None
        options, state = self.server.register_begin(
            PublicKeyCredentialUserEntity(
                id=b"w7tp-total-field-founder",
                name="W7TP Founder",
                display_name="W7TP 總場創辦人",
            ),
            resident_key_requirement=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
            authenticator_attachment=None,
        )
        issued = utc_now()
        atomic_json(
            self.state_root / f"register-{ceremony_id}.json",
            {
                "state": state,
                "mode": "ROTATE" if rotate else "REGISTER",
                "issued_at": iso_z(issued),
                "expires_at": iso_z(issued + timedelta(seconds=int(self.passkey["maximum_ttl_seconds"]))),
                "previous_credential_sha256": previous_credential_sha256,
            },
        )
        return {"state": "PASSKEY_REGISTRATION_CHALLENGE_READY", "ceremony_id": ceremony_id, "options": dict(options)}

    def register_complete(
        self, supplied: str, user_agent: str, body: Mapping[str, Any], *, rotate: bool = False
    ) -> dict[str, Any]:
        self.require_bootstrap(supplied)
        self.require_client(user_agent)
        ceremony_id = str(body.get("ceremony_id") or "")
        pending = self.state_root / f"register-{ceremony_id}.json"
        if not pending.is_file():
            raise PasskeyD8Rejected("註冊挑戰不存在或已失效")
        pending_record = load_json(pending, "PASSKEY_REGISTRATION_STATE_INVALID")
        expected_mode = "ROTATE" if rotate else "REGISTER"
        if pending_record.get("mode") != expected_mode:
            raise PasskeyD8Rejected("註冊模式不符")
        if utc_now() > parse_time(pending_record.get("expires_at")):
            raise PasskeyD8Rejected("註冊挑戰已超過五分鐘")
        credential_path = self.credential_path()
        if rotate:
            if not credential_path.is_file():
                raise PasskeyD8Rejected("舊密鑰已不存在")
            previous_sha256 = sha256(credential_path.read_bytes())
            if previous_sha256 != pending_record.get("previous_credential_sha256"):
                raise PasskeyD8Rejected("註冊期間舊密鑰已漂移")
        elif credential_path.exists():
            raise PasskeyD8Rejected("通行密鑰已註冊，禁止覆寫")
        else:
            previous_sha256 = None
        state = pending_record.get("state")
        response = body.get("response")
        if not isinstance(state, Mapping) or not isinstance(response, Mapping):
            raise PasskeyD8Rejected("註冊回應無效")
        parsed = RegistrationResponse.from_dict(response)
        auth_data = self.server.register_complete(state, parsed)
        if not auth_data.is_user_verified() or auth_data.credential_data is None:
            raise PasskeyD8Rejected("創辦人平台通行密鑰使用者解鎖驗證未成立")
        authenticator_attachment = require_admitted_authenticator(
            response,
            allow_hybrid_mobile=self.passkey.get("hybrid_mobile_passkey_allowed") is True,
        )
        credential = auth_data.credential_data
        transports = list(((response.get("response") or {}).get("transports") or []))
        record = {
            "schema_id": PASSKEY_CREDENTIAL_SCHEMA,
            "state": "ENROLLED_USER_VERIFIED",
            "enrolled_at": iso_z(utc_now()),
            "rp_id": self.passkey["rp_id"],
            "expected_origin": self.passkey["expected_origin"],
            "credential_id_b64url": websafe_encode(credential.credential_id),
            "attested_credential_data_b64url": websafe_encode(bytes(credential)),
            "aaguid_b64url": websafe_encode(bytes(credential.aaguid)),
            "transports": transports,
            "authenticator_attachment": authenticator_attachment,
            "authenticator_profile": (
                "HYBRID_MOBILE_PLATFORM" if authenticator_attachment == "cross-platform" else "DEVICE_BOUND_PLATFORM"
            ),
            "sign_count": int(auth_data.counter),
            "user_verification": True,
            "attestation_is_final_authority": False,
            "provider_is_authority": False,
        }
        atomic_json(credential_path, record)
        active_credential_sha256 = sha256(credential_path.read_bytes())
        if rotate:
            rotation_receipt = {
                "schema_id": "W7TP_TOTAL_FIELD_PASSKEY_CREDENTIAL_ROTATION_RECEIPT_V1",
                "state": "PASS_ATOMIC_CREDENTIAL_ROTATION",
                "rotated_at": iso_z(utc_now()),
                "previous_credential_sha256": previous_sha256,
                "active_credential_sha256": active_credential_sha256,
                "authenticator_attachment": authenticator_attachment,
                "transports": transports,
                "user_verification": True,
                "provider_is_authority": False,
            }
            atomic_json(self.state_root / f"credential-rotation-{ceremony_id}.json", rotation_receipt)
            pointer_path = self.root.joinpath(
                *PurePosixPath(str(self.passkey["active_approval_pointer_ref"])).parts
            )
            if pointer_path.is_file():
                atomic_json(
                    pointer_path,
                    {
                        "schema_id": PASSKEY_POINTER_SCHEMA,
                        "state": "INVALIDATED_BY_CREDENTIAL_ROTATION",
                        "previous_pointer_sha256": sha256(pointer_path.read_bytes()),
                        "active_credential_sha256": active_credential_sha256,
                        "updated_at": iso_z(utc_now()),
                    },
                )
        pending.unlink(missing_ok=True)
        self.bootstrap_path.unlink(missing_ok=True)
        return {
            "state": "PASS_LOCAL_PASSKEY_ROTATED" if rotate else "PASS_LOCAL_PASSKEY_ENROLLED",
            "message_zh_TW": (
                "手機 Face ID 新密鑰已安全取代舊密鑰；請按下方按鈕簽發本次推送。"
                if rotate
                else "手機 Face ID 通行密鑰已建立；請按下方按鈕簽發本次推送。"
            ),
        }

    def _request(self) -> tuple[Path, dict[str, Any]]:
        path = self.root.joinpath(*PurePosixPath(str(self.passkey["review_request_ref"])).parts)
        request = load_json(path, "TOTAL_FIELD_REVIEW_REQUEST_INVALID")
        if request.get("schema_id") != REQUEST_SCHEMA or request.get("registration_state") != "REGISTERED_FOR_REVIEW":
            raise PasskeyD8Rejected("總場審查請求尚未完成登記")
        d3, d8 = request.get("D3_COORDINATE"), request.get("D8_ENVELOPE_AUTHORITY")
        if not isinstance(d3, Mapping) or not isinstance(d8, Mapping):
            raise PasskeyD8Rejected("總場審查請求缺少精確座標")
        scopes = normalized_scopes(d8.get("requested_scopes", d8.get("requested_scope")))
        allowed_scopes = {(GIT_PUSH_SCOPE,), (GIT_PUSH_SCOPE, DEPLOY_RESTART_SCOPE)}
        if scopes not in allowed_scopes or d8.get("maximum_ttl_seconds") != self.passkey["maximum_ttl_seconds"]:
            raise PasskeyD8Rejected("總場審查請求範圍不符")
        deployment = (request.get("D5_EXECUTION_POLICY") or {}).get("deployment")
        if DEPLOY_RESTART_SCOPE in scopes:
            if not isinstance(deployment, Mapping):
                raise PasskeyD8Rejected("總場審查請求缺少精確部署座標")
            admitted_deployments = (
                {
                    "target_node": "taiji01",
                    "repository_root": "/home/taiji_admin/Taiji_Hub",
                    "service": "taiji_edge_gateway.service",
                    "application": "services.gateway.main:app",
                    "active_port": 9002,
                    "canary_port": 9003,
                    "carrier": "LAN",
                },
                {
                    "target_node": "MSI_WSL",
                    "repository_root": "/home/taiji_admin/Taiji_Hub",
                    "service": "xiaoj-intent-field",
                    "application": "services.xiaoj_intent_field.app:app",
                    "active_port": 9107,
                    "canary_port": 0,
                    "carrier": "LOCAL_DOCKER_COMPOSE",
                },
            )
            if not any(
                all(deployment.get(key) == value for key, value in expected.items())
                for expected in admitted_deployments
            ):
                raise PasskeyD8Rejected("總場審查請求部署座標不符")
        elif deployment is not None:
            raise PasskeyD8Rejected("Git-only 審查請求不得攜帶部署座標")
        return path, request

    def _receive_candidate_request(self) -> tuple[Path, dict[str, Any]]:
        path = self.root.joinpath(
            *PurePosixPath(str(self.passkey["receive_candidate_review_request_ref"])).parts
        )
        request = load_json(path, "TOTAL_FIELD_RECEIVE_CANDIDATE_REQUEST_INVALID")
        if (
            request.get("schema_id") != RECEIVE_REQUEST_SCHEMA
            or request.get("registration_state") != "REGISTERED_FOR_REVIEW"
        ):
            raise PasskeyD8Rejected("總場候選能力接收請求尚未完成登記")
        d3 = request.get("D3_COORDINATE")
        d8 = request.get("D8_ENVELOPE_AUTHORITY")
        if not isinstance(d3, Mapping) or not isinstance(d8, Mapping):
            raise PasskeyD8Rejected("總場候選能力接收請求缺少精確座標")
        scopes = normalized_scopes(d8.get("requested_scopes", d8.get("requested_scope")))
        if scopes != (RECEIVE_CANDIDATE_SCOPE,):
            raise PasskeyD8Rejected("總場候選能力接收請求範圍不符")
        if d8.get("maximum_ttl_seconds") != self.passkey["maximum_ttl_seconds"]:
            raise PasskeyD8Rejected("總場候選能力接收請求時限不符")
        if d3.get("candidate_id") != "w7tp_8d_adi_origin_cell_fusion":
            raise PasskeyD8Rejected("總場候選能力接收識別不符")
        for field in (
            "candidate_packet_sha256",
            "skill_index_sha256",
            "skill_source_manifest_sha256",
            "dynamic_context_sha256",
        ):
            value = str(d3.get(field) or "")
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise PasskeyD8Rejected("總場候選能力接收雜湊無效")
        policy = request.get("D5_EXECUTION_POLICY")
        if not isinstance(policy, Mapping):
            raise PasskeyD8Rejected("總場候選能力接收政策缺失")
        if (
            policy.get("requested_action") != "RECEIVE_CANDIDATE_FOR_GOVERNED_USE"
            or policy.get("deploy") is not False
            or policy.get("restart") is not False
            or policy.get("git_push") is not False
            or policy.get("canonical_pointer_write") is not False
            or policy.get("active_pointer_write") is not False
        ):
            raise PasskeyD8Rejected("總場候選能力接收政策越界")
        return path, request

    def approve_options(self, user_agent: str) -> dict[str, Any]:
        self.require_client(user_agent)
        credential_record, credential = load_credential(self.root, self.passkey)
        request_path, request = self._request()
        d3 = request["D3_COORDINATE"]
        scopes = normalized_scopes(
            request["D8_ENVELOPE_AUTHORITY"].get("requested_scopes")
        )
        deployment = request["D5_EXECUTION_POLICY"].get("deployment")
        deploy_requested = DEPLOY_RESTART_SCOPE in scopes
        nonce = websafe_encode(secrets.token_bytes(32))
        ceremony_id = secrets.token_hex(16)
        issued = utc_now()
        expires = issued + timedelta(seconds=int(self.passkey["maximum_ttl_seconds"]))
        artifact_rel = f"runtime/total_field/authority_artifacts/W7TP_DEVICE_PASSKEY_D8_{issued.strftime('%Y%m%dT%H%M%SZ')}_{nonce[:12]}"
        review_ref = f"{artifact_rel}/GIT_PUSH_REVIEW_REGISTRATION.json"
        review = {
            "schema_id": REVIEW_SCHEMA,
            "state": REVIEW_STATE,
            "review_registered": True,
            "total_field_decision": "ALLOW_FORMAL_GIT_PUSH_AND_EXACT_DEPLOY_RESTART" if deploy_requested else "ALLOW_FORMAL_GIT_PUSH",
            "reviewed_at": iso_z(issued),
            "review_request_ref": _relative(self.root, request_path),
            "review_request_packet_sha256": request["packet_sha256"],
            "base_commit": d3["base_commit"],
            "target_tree": d3["target_tree"],
            "branch": d3["branch"],
            "remote_name": d3["remote_name"],
            "remote_url_sha256": d3["remote_url_sha256"],
            "allowed_paths_sha256": request["D4_EVIDENCE"]["changed_paths_sha256"],
            "authorized_scopes": list(scopes),
            "founder_user_verification": "ENROLLED_PLATFORM_PASSKEY_REQUIRED",
            "model_is_authority": False,
            "provider_is_authority": False,
        }
        if deploy_requested:
            review["deployment"] = deployment
        review_bytes = json.dumps(review, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        constraints = {
            "review_registration_ref": review_ref,
            "review_registration_sha256": sha256(review_bytes),
            "base_commit": d3["base_commit"],
            "target_tree": d3["target_tree"],
            "branch": d3["branch"],
            "remote_name": d3["remote_name"],
            "remote_url_sha256": d3["remote_url_sha256"],
            "allowed_paths_sha256": request["D4_EVIDENCE"]["changed_paths_sha256"],
            "single_commit_only": True,
            "formal_submission": True,
            "git_push": True,
            "deploy": deploy_requested,
            "restart": deploy_requested,
            "canonical_pointer_write": False,
            "active_pointer_write": False,
            "single_use_authorization_required": True,
            "replay_protected": True,
            "authority_signature_required": True,
        }
        if deploy_requested:
            constraints["deployment"] = deployment
        claims = {
            "scope": GIT_PUSH_SCOPE,
            "scopes": list(scopes),
            "issued_at": iso_z(issued),
            "expires_at": iso_z(expires),
            "request_ref": _relative(self.root, request_path),
            "request_source_sha256": sha256(request_path.read_bytes()),
            "request_packet_sha256": request["packet_sha256"],
            "review_registration_sha256": constraints["review_registration_sha256"],
            "authority_scope_constraints": constraints,
            "provider_is_authority": False,
            "model_is_authority": False,
        }
        challenge = approval_challenge(claims, nonce)
        options, webauthn_state = self.server.authenticate_begin(
            [credential],
            user_verification=UserVerificationRequirement.REQUIRED,
            challenge=challenge,
        )
        pending_record = {
            "state": "PENDING_LOCAL_DEVICE_UNLOCK",
            "ceremony_id": ceremony_id,
            "nonce_b64url": nonce,
            "issued_at": iso_z(issued),
            "expires_at": iso_z(expires),
            "artifact_ref": artifact_rel,
            "review": review,
            "signed_claims": claims,
            "webauthn_state": webauthn_state,
            "credential_sha256": sha256(self.credential_path().read_bytes()),
            "credential_id_b64url": credential_record["credential_id_b64url"],
            "review_filename": "GIT_PUSH_REVIEW_REGISTRATION.json",
            "approval_filename": "GIT_PUSH_PASSKEY_APPROVAL.json",
        }
        atomic_json(self.state_root / f"approve-{ceremony_id}.json", pending_record)
        return {
            "state": "LOCAL_DEVICE_UNLOCK_CHALLENGE_READY",
            "ceremony_id": ceremony_id,
            "options": dict(options),
            "display": {
                "branch": d3["branch"],
                "target_tree": d3["target_tree"],
                "file_count": len(d3.get("changed_paths") or []),
                "ttl_seconds": self.passkey["maximum_ttl_seconds"],
                "scope_zh_TW": "正式 Git 推送＋精確部署與重啟" if deploy_requested else "僅正式 Git 推送",
                "deploy_node": deployment["target_node"] if deploy_requested else None,
                "deploy_service": deployment["service"] if deploy_requested else None,
            },
        }

    def _exact_repair_constraints(self) -> dict[str, Any]:
        if self.root.as_posix() != EXACT_REPAIR_ROOT:
            raise PasskeyD8Rejected("精確修復 repository root 已漂移")
        branch = subprocess.run(
            ["git", "branch", "--show-current"], cwd=self.root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        target_state = subprocess.run(
            ["git", "status", "--porcelain", "--", EXACT_REPAIR_FILE], cwd=self.root,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        source = (self.root / EXACT_REPAIR_FILE).read_text(encoding="utf-8")
        if branch != EXACT_REPAIR_BRANCH or head != EXACT_REPAIR_HEAD:
            raise PasskeyD8Rejected("精確修復 branch 或 HEAD 已漂移")
        if target_state:
            raise PasskeyD8Rejected("精確修復目標檔已有未提交差異")
        if f"def {EXACT_REPAIR_FUNCTION}(" not in source:
            raise PasskeyD8Rejected("精確修復函式座標不存在")
        return {
            "repo_root": EXACT_REPAIR_ROOT,
            "branch": branch,
            "head": head,
            "file": EXACT_REPAIR_FILE,
            "function": EXACT_REPAIR_FUNCTION,
            "intent": EXACT_REPAIR_INTENT,
            "allowed_effect": EXACT_REPAIR_SCOPE,
            "prohibited_effects": list(EXACT_REPAIR_PROHIBITED_EFFECTS),
            "formal_submission": False,
            "git_push": False,
            "deploy": False,
            "restart": False,
            "canonical_pointer_write": False,
            "active_pointer_write": False,
            "single_use_authorization_required": True,
            "replay_protected": True,
            "authority_signature_required": True,
        }

    def approve_exact_repair_options(self, user_agent: str) -> dict[str, Any]:
        self.require_client(user_agent)
        credential_record, credential = load_credential(self.root, self.passkey)
        constraints = self._exact_repair_constraints()
        nonce = websafe_encode(secrets.token_bytes(32))
        ceremony_id = secrets.token_hex(16)
        issued = utc_now()
        expires = issued + timedelta(seconds=int(self.passkey["maximum_ttl_seconds"]))
        artifact_rel = (
            "runtime/total_field/authority_artifacts/"
            f"W7TP_EXACT_REPAIR_PASSKEY_D8_{issued.strftime('%Y%m%dT%H%M%SZ')}_{nonce[:12]}"
        )
        review_ref = f"{artifact_rel}/EXACT_REPAIR_REVIEW_REGISTRATION.json"
        review = {
            "schema_id": EXACT_REPAIR_REVIEW_SCHEMA,
            "state": REVIEW_STATE,
            "review_registered": True,
            "total_field_decision": "ALLOW_EXACT_MINIMAL_REPAIR_ONLY",
            "reviewed_at": iso_z(issued),
            "authorized_scopes": [EXACT_REPAIR_SCOPE],
            **constraints,
            "founder_user_verification": "ENROLLED_PLATFORM_PASSKEY_REQUIRED",
            "model_is_authority": False,
            "provider_is_authority": False,
        }
        review_bytes = json.dumps(review, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        constraints["review_registration_ref"] = review_ref
        constraints["review_registration_sha256"] = sha256(review_bytes)
        request_packet_sha256 = sha256(canonical_json(constraints))
        claims = {
            "scope": EXACT_REPAIR_SCOPE,
            "scopes": [EXACT_REPAIR_SCOPE],
            "issued_at": iso_z(issued),
            "expires_at": iso_z(expires),
            "request_packet_sha256": request_packet_sha256,
            "review_registration_sha256": constraints["review_registration_sha256"],
            "authority_scope_constraints": constraints,
            "provider_is_authority": False,
            "model_is_authority": False,
        }
        challenge = approval_challenge(claims, nonce)
        options, webauthn_state = self.server.authenticate_begin(
            [credential], user_verification=UserVerificationRequirement.REQUIRED,
            challenge=challenge,
        )
        pending_record = {
            "state": "PENDING_LOCAL_DEVICE_UNLOCK",
            "ceremony_id": ceremony_id,
            "nonce_b64url": nonce,
            "issued_at": iso_z(issued),
            "expires_at": iso_z(expires),
            "artifact_ref": artifact_rel,
            "review": review,
            "signed_claims": claims,
            "webauthn_state": webauthn_state,
            "credential_sha256": sha256(self.credential_path().read_bytes()),
            "credential_id_b64url": credential_record["credential_id_b64url"],
            "review_filename": "EXACT_REPAIR_REVIEW_REGISTRATION.json",
            "approval_filename": "EXACT_REPAIR_PASSKEY_APPROVAL.json",
        }
        atomic_json(self.state_root / f"approve-{ceremony_id}.json", pending_record)
        return {
            "state": "LOCAL_DEVICE_UNLOCK_CHALLENGE_READY",
            "ceremony_id": ceremony_id,
            "options": dict(options),
            "display": {
                **{key: constraints[key] for key in ("branch", "head", "file", "function")},
                "ttl_seconds": self.passkey["maximum_ttl_seconds"],
                "scope_zh_TW": "僅第一動態上下文污染入口精確修復",
            },
        }

    def approve_receive_candidate_options(self, user_agent: str) -> dict[str, Any]:
        self.require_client(user_agent)
        credential_record, credential = load_credential(self.root, self.passkey)
        request_path, request = self._receive_candidate_request()
        d3 = request["D3_COORDINATE"]
        nonce = websafe_encode(secrets.token_bytes(32))
        ceremony_id = secrets.token_hex(16)
        issued = utc_now()
        expires = issued + timedelta(seconds=int(self.passkey["maximum_ttl_seconds"]))
        artifact_rel = (
            "runtime/total_field/authority_artifacts/"
            f"W7TP_RECEIVE_CANDIDATE_PASSKEY_D8_{issued.strftime('%Y%m%dT%H%M%SZ')}_{nonce[:12]}"
        )
        review_ref = f"{artifact_rel}/RECEIVE_CANDIDATE_REVIEW_REGISTRATION.json"
        review = {
            "schema_id": RECEIVE_REVIEW_SCHEMA,
            "state": REVIEW_STATE,
            "review_registered": True,
            "total_field_decision": "ALLOW_RECEIVE_CANDIDATE_FOR_GOVERNED_USE",
            "reviewed_at": iso_z(issued),
            "review_request_ref": _relative(self.root, request_path),
            "review_request_packet_sha256": request["packet_sha256"],
            "candidate_id": d3["candidate_id"],
            "candidate_packet_sha256": d3["candidate_packet_sha256"],
            "skill_index_sha256": d3["skill_index_sha256"],
            "skill_source_manifest_sha256": d3["skill_source_manifest_sha256"],
            "dynamic_context_sha256": d3["dynamic_context_sha256"],
            "authorized_scopes": [RECEIVE_CANDIDATE_SCOPE],
            "founder_user_verification": "ENROLLED_PLATFORM_PASSKEY_REQUIRED",
            "model_is_authority": False,
            "provider_is_authority": False,
        }
        review_bytes = (
            json.dumps(review, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
            + b"\n"
        )
        constraints = {
            "review_registration_ref": review_ref,
            "review_registration_sha256": sha256(review_bytes),
            "candidate_id": d3["candidate_id"],
            "candidate_packet_sha256": d3["candidate_packet_sha256"],
            "skill_index_sha256": d3["skill_index_sha256"],
            "skill_source_manifest_sha256": d3["skill_source_manifest_sha256"],
            "dynamic_context_sha256": d3["dynamic_context_sha256"],
            "receive_candidate": True,
            "formal_submission": False,
            "git_push": False,
            "deploy": False,
            "restart": False,
            "canonical_pointer_write": False,
            "active_pointer_write": False,
            "single_use_authorization_required": True,
            "replay_protected": True,
            "authority_signature_required": True,
        }
        claims = {
            "scope": RECEIVE_CANDIDATE_SCOPE,
            "scopes": [RECEIVE_CANDIDATE_SCOPE],
            "issued_at": iso_z(issued),
            "expires_at": iso_z(expires),
            "request_ref": _relative(self.root, request_path),
            "request_source_sha256": sha256(request_path.read_bytes()),
            "request_packet_sha256": request["packet_sha256"],
            "review_registration_sha256": constraints["review_registration_sha256"],
            "authority_scope_constraints": constraints,
            "provider_is_authority": False,
            "model_is_authority": False,
        }
        challenge = approval_challenge(claims, nonce)
        options, webauthn_state = self.server.authenticate_begin(
            [credential],
            user_verification=UserVerificationRequirement.REQUIRED,
            challenge=challenge,
        )
        pending_record = {
            "state": "PENDING_LOCAL_DEVICE_UNLOCK",
            "ceremony_id": ceremony_id,
            "nonce_b64url": nonce,
            "issued_at": iso_z(issued),
            "expires_at": iso_z(expires),
            "artifact_ref": artifact_rel,
            "review": review,
            "signed_claims": claims,
            "webauthn_state": webauthn_state,
            "credential_sha256": sha256(self.credential_path().read_bytes()),
            "credential_id_b64url": credential_record["credential_id_b64url"],
            "review_filename": "RECEIVE_CANDIDATE_REVIEW_REGISTRATION.json",
            "approval_filename": "RECEIVE_CANDIDATE_PASSKEY_APPROVAL.json",
        }
        atomic_json(self.state_root / f"approve-{ceremony_id}.json", pending_record)
        return {
            "state": "LOCAL_DEVICE_UNLOCK_CHALLENGE_READY",
            "ceremony_id": ceremony_id,
            "options": dict(options),
            "display": {
                "candidate_id": d3["candidate_id"],
                "candidate_packet_sha256": d3["candidate_packet_sha256"],
                "skill_index_sha256": d3["skill_index_sha256"],
                "ttl_seconds": self.passkey["maximum_ttl_seconds"],
                "scope_zh_TW": "僅接收本次雜湊綁定的原胞融合候選能力",
            },
        }

    def approve_complete(self, user_agent: str, body: Mapping[str, Any]) -> dict[str, Any]:
        self.require_client(user_agent)
        ceremony_id = str(body.get("ceremony_id") or "")
        pending_path = self.state_root / f"approve-{ceremony_id}.json"
        if not pending_path.is_file():
            raise PasskeyD8Rejected("簽發挑戰不存在或已失效")
        pending = load_json(pending_path, "PASSKEY_APPROVAL_STATE_INVALID")
        if utc_now() > parse_time(pending["expires_at"]):
            raise PasskeyD8Rejected("簽發挑戰已超過五分鐘")
        response = body.get("response")
        if not isinstance(response, Mapping):
            raise PasskeyD8Rejected("簽發回應無效")
        credential_record, credential = load_credential(self.root, self.passkey)
        authenticator_attachment = require_admitted_authenticator(
            response,
            credential_record,
            allow_hybrid_mobile=self.passkey.get("hybrid_mobile_passkey_allowed") is True,
        )
        verified = self.server.authenticate_complete(pending["webauthn_state"], [credential], response)
        parsed = AuthenticationResponse.from_dict(response)
        if verified.credential_id != credential.credential_id or not parsed.response.authenticator_data.is_user_verified():
            raise PasskeyD8Rejected("創辦人平台通行密鑰使用者解鎖驗證未成立")
        claims = pending["signed_claims"]
        if claims["scope"] == EXACT_REPAIR_SCOPE:
            current_constraints = self._exact_repair_constraints()
            for field in ("review_registration_ref", "review_registration_sha256"):
                current_constraints[field] = claims["authority_scope_constraints"][field]
            if current_constraints != claims["authority_scope_constraints"]:
                raise PasskeyD8Rejected("簽發期間精確修復座標已漂移")
            if sha256(canonical_json(current_constraints)) != claims["request_packet_sha256"]:
                raise PasskeyD8Rejected("簽發期間精確修復作用封包已漂移")
        else:
            current_request_path = safe_runtime_ref(
                self.root, claims["request_ref"], suffix="REQUEST.json",
            )
            current_request = load_json(current_request_path, "TOTAL_FIELD_REVIEW_REQUEST_INVALID")
            if sha256(current_request_path.read_bytes()) != claims["request_source_sha256"]:
                raise PasskeyD8Rejected("簽發期間審查請求已漂移")
            if current_request.get("packet_sha256") != claims["request_packet_sha256"]:
                raise PasskeyD8Rejected("簽發期間作用封包已漂移")
        artifact = self.root.joinpath(*PurePosixPath(pending["artifact_ref"]).parts)
        if artifact.exists():
            raise PasskeyD8Rejected("簽發收據座標已存在")
        artifact.mkdir(parents=True, exist_ok=False)
        review_path = artifact / str(
            pending.get("review_filename") or "GIT_PUSH_REVIEW_REGISTRATION.json"
        )
        assertion_path = artifact / "PASSKEY_ASSERTION.json"
        approval_path = artifact / str(
            pending.get("approval_filename") or "GIT_PUSH_PASSKEY_APPROVAL.json"
        )
        atomic_json(review_path, pending["review"])
        assertion_record = {
            "schema_id": "W7TP_TOTAL_FIELD_PASSKEY_ASSERTION_EVIDENCE_V1",
            "state": "SEALED_WEBAUTHN_ASSERTION",
            "webauthn_state": pending["webauthn_state"],
            "assertion": dict(response),
        }
        atomic_json(assertion_path, assertion_record)
        approval = {
            "schema_id": PASSKEY_APPROVAL_SCHEMA,
            "state": PASSKEY_APPROVAL_STATE,
            "scope": claims["scope"],
            "scopes": claims["scopes"],
            "issued_at": pending["issued_at"],
            "expires_at": pending["expires_at"],
            "nonce_b64url": pending["nonce_b64url"],
            "challenge_sha256": sha256(approval_challenge(claims, pending["nonce_b64url"])),
            "signed_claims": claims,
            "authority_scope_constraints": claims["authority_scope_constraints"],
            "credential_ref": self.passkey["credential_ref"],
            "credential_sha256": pending["credential_sha256"],
            "assertion_ref": _relative(self.root, assertion_path),
            "assertion_sha256": sha256(assertion_path.read_bytes()),
            "user_verification": True,
            "authenticator_attachment": authenticator_attachment,
            "single_use": True,
            "provider_is_authority": False,
            "model_is_authority": False,
            "receive_candidate_authorized": bool(
                claims["authority_scope_constraints"].get("receive_candidate")
            ),
            "exact_minimal_repair_authorized": claims["scope"] == EXACT_REPAIR_SCOPE,
            "deploy_authorized": bool(
                claims["authority_scope_constraints"].get("deploy")
            ),
            "restart_authorized": bool(
                claims["authority_scope_constraints"].get("restart")
            ),
            "canonical_mutation_authorized": False,
        }
        atomic_json(approval_path, approval)
        pointer_path = self.root.joinpath(*PurePosixPath(str(self.passkey["active_approval_pointer_ref"])).parts)
        pointer = {
            "schema_id": PASSKEY_POINTER_SCHEMA,
            "state": "ACTIVE_SINGLE_USE",
            "approval_ref": _relative(self.root, approval_path),
            "approval_sha256": sha256(approval_path.read_bytes()),
            "updated_at": iso_z(utc_now()),
        }
        atomic_json(pointer_path, pointer)
        pending_path.unlink(missing_ok=True)
        return {
            "state": "PASS_LOCAL_DEVICE_UNLOCK_D8_APPROVAL_ISSUED",
            "message_zh_TW": (
                "創辦人平台通行密鑰解鎖驗證成立；本次雜湊綁定的原胞融合候選能力接收已取得單次五分鐘簽發。"
                if claims["scope"] == RECEIVE_CANDIDATE_SCOPE
                else (
                    "創辦人通行密鑰驗證成立；本次第一污染入口精確修復已取得單次五分鐘簽發。"
                    if claims["scope"] == EXACT_REPAIR_SCOPE
                    else (
                        "創辦人平台通行密鑰解鎖驗證成立；本次精確推送與太極一號指定服務部署重啟已取得單次五分鐘簽發。"
                        if claims["authority_scope_constraints"].get("deploy")
                        else "創辦人平台通行密鑰解鎖驗證成立；本次僅限精確 Git 推送已取得單次五分鐘簽發。"
                    )
                )
            ),
            "approval_sha256": pointer["approval_sha256"],
        }


class Handler(BaseHTTPRequestHandler):
    app: PasskeyApplication

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("passkey-d8 " + (fmt % args) + "\n")

    def _json(self, value: Mapping[str, Any], status: int = 200) -> None:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/":
            payload = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == "/health":
            self._json(self.app.health())
        else:
            self._json({"state": "NOT_FOUND"}, 404)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 256_000:
                raise PasskeyD8Rejected("請求大小無效")
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, Mapping):
                raise PasskeyD8Rejected("請求格式無效")
            token = self.headers.get("X-W7TP-Bootstrap", "")
            user_agent = self.headers.get("User-Agent", "")
            route = self.path.split("?", 1)[0]
            if route == "/v1/passkey/register/options":
                result = self.app.register_options(token, user_agent)
            elif route == "/v1/passkey/register/complete":
                result = self.app.register_complete(token, user_agent, body)
            elif route == "/v1/passkey/rotate/options":
                result = self.app.register_options(token, user_agent, rotate=True)
            elif route == "/v1/passkey/rotate/complete":
                result = self.app.register_complete(token, user_agent, body, rotate=True)
            elif route == "/v1/passkey/approve/options":
                result = self.app.approve_options(user_agent)
            elif route == "/v1/passkey/approve/complete":
                result = self.app.approve_complete(user_agent, body)
            elif route == "/v1/passkey/receive-candidate/options":
                result = self.app.approve_receive_candidate_options(user_agent)
            elif route == "/v1/passkey/receive-candidate/complete":
                result = self.app.approve_complete(user_agent, body)
            elif route == "/v1/passkey/exact-repair/options":
                result = self.app.approve_exact_repair_options(user_agent)
            elif route == "/v1/passkey/exact-repair/complete":
                result = self.app.approve_complete(user_agent, body)
            else:
                self._json({"state": "NOT_FOUND"}, 404)
                return
            self._json(result)
        except (PasskeyD8Rejected, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self._json({"state": "HOLD_DEVICE_PASSKEY_D8", "reason": str(exc)}, 400)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9120)
    args = parser.parse_args()
    app = PasskeyApplication(Path(args.repo_root))
    Handler.app = app
    print(json.dumps({"state": "READY", "url": f"{app.passkey['expected_origin']}/?bootstrap={app.bootstrap_token()}"}, ensure_ascii=False), flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
