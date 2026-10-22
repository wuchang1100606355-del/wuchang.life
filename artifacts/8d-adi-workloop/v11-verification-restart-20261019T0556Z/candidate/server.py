#!/usr/bin/env python3
"""Isolated Founder-domain WebAuthn candidate signer.

Reuses installed python-fido2 cryptographic verifier and existing code-server
authenticated HTTPS proxy; NEVER issues founder root or D8 authority.
"""
from __future__ import annotations
import base64, hashlib, hmac, json, os, secrets, sys, threading, subprocess, importlib.util
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from fido2.server import Fido2Server
from fido2.webauthn import (
    AttestedCredentialData, PublicKeyCredentialRpEntity,
    PublicKeyCredentialUserEntity, ResidentKeyRequirement,
    UserVerificationRequirement, RegistrationResponse, AuthenticationResponse,
)

ROOT = Path("/home/taiji_admin/Taiji_Hub")
BASE = Path("/tmp/w7tp_d4_redteam_8CYJzxxe")
VIEW_REQUEST = BASE / "V6_D4_READONLY_CHALLENGE_24H_20261018T035355Z.json"
VIEW_REQUEST_SHA256 = "0611f792ef3f14a7e6797bf5501eefb9bc2a1383eb7b511343f68446577e81fa"
STATE_DIR = BASE / "V7_MOBILE_DEVICE_SIGNATURE_CANDIDATE"
CRED_PATH = STATE_DIR / "mobile_candidate_public_credential.json"
RECEIPT_DIR = STATE_DIR / "signature_receipts"
INDEPENDENT_VERIFIER=BASE / "v7_independent_webauthn_proof_verifier.py"
INDEPENDENT_VERIFIER_SHA256="821cac65ae0254240f063128b5013034d0d5ae74f048fde4db0de553398455f4"
FOUND_ROOT_GATE = ROOT / "tools/total_field/founder_variable_cognition_gate.py"
FOUND_ROOT_GATE_SHA256 = "54e21e92d5a2371b4c33d907da31a58e2c2d0fcb1c44707b02b71f94f37ad66e"
HOSTNAME = "taiji01.tailea1eef.ts.net"
RP_ORIGIN = "https://" + HOSTNAME + ":8444"
CLIENT_HOSTS = {HOSTNAME + ":8444", "127.0.0.1:9122", "localhost:9122"}
MAX_CEREMONY = timedelta(minutes=5)
CHALLENGE_TASK = "D4_BROKER_ISSUANCE_TRUST_BINDING"
CHALLENGE_EFFECT = "AUTHORIZE_SINGLE_USE_D4_BROKER_ISSUANCE_STATIC_REVIEW_ONLY"
PORT = 9122

fido = Fido2Server(
    PublicKeyCredentialRpEntity(id=HOSTNAME, name="W7TP 8D ADI 已有身分根｜裝置簽章"),
    verify_origin=lambda origin: origin == RP_ORIGIN,
)
lock = threading.RLock()
registrations: dict[str, dict] = {}
signatures: dict[str, dict] = {}

def utcnow():
    return datetime.now(timezone.utc)

def timestamp(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)

def jsonbytes(value):
    return json.dumps(value, ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def b64enc(data):
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

def b64dec(s):
    return base64.urlsafe_b64decode(s + "=" * ((4-len(s)%4)%4))

def hold(code):
    raise PermissionError(code)

def read_json_file(path, size_limit=32768):
    if path.is_symlink() or path.resolve(strict=True) != path:
        hold("HOLD_PATH_ESCAPE")
    with path.open("rb") as f:
        raw = f.read(size_limit+1)
    if len(raw)>size_limit:
        hold("HOLD_SOURCE_OVERSIZE")
    return raw, json.loads(raw)

def load_scope():
    raw, data = read_json_file(VIEW_REQUEST)
    if not hmac.compare_digest(sha(raw), VIEW_REQUEST_SHA256):
        hold("HOLD_SCOPE_HASH_DRIFT")
    if data.get("authorization") is not None or not data.get("not_a_formal_d8_approval"):
        hold("HOLD_SCOPE_AUTHORITY_DRIFT")
    if data.get("state") != "PENDING_REAL_FOUNDER_WEBAUTHN_ASSERTION":
        hold("HOLD_SCOPE_STATE_INVALID")
    s = data.get("scope") or {}
    if s.get("task_id") != CHALLENGE_TASK or s.get("effect") != CHALLENGE_EFFECT or s.get("node_id") != "taiji01":
        hold("HOLD_SCOPE_COORDINATE_DRIFT")
    if s.get("scope") != "STATIC_REVIEW_AND_ISOLATED_TEST_ONLY" or s.get("single_use") is not True:
        hold("HOLD_SCOPE_EFFECT_DRIFT")
    if utcnow() >= parse_time(s["expires_at"]) or utcnow() < parse_time(s["created_at"]):
        hold("HOLD_SCOPE_EXPIRED")
    if (parse_time(s["expires_at"])-parse_time(s["created_at"])).total_seconds()!=86400:
        hold("HOLD_SCOPE_TTL_DRIFT")
    if sha(FOUND_ROOT_GATE.read_bytes()) != FOUND_ROOT_GATE_SHA256:
        hold("HOLD_FOUNDER_GATE_SOURCE_DRIFT")
    source_bindings = s.get("source_bindings") or {}
    permitted_paths = {
        "isolated_v4_report": BASE / "V4_CRYPTO_ISOLATED_RESULTS.json",
        "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json": ROOT / "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json",
        "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json": ROOT / "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json",
        "scripts/verify/verify_task_context_precedence_gate.sh": ROOT / "scripts/verify/verify_task_context_precedence_gate.sh",
        "tools/total_field/w7tp_ed25519_verifier.py": ROOT / "tools/total_field/w7tp_ed25519_verifier.py",
        "tools/total_field/w7tp_founder_passkey_v1.py": ROOT / "tools/total_field/w7tp_founder_passkey_v1.py",
        "tools/total_field/w7tp_static_review_entrypoint.py": ROOT / "tools/total_field/w7tp_static_review_entrypoint.py",
        "tools/total_field_dynamic_context_pull.py": ROOT / "tools/total_field_dynamic_context_pull.py",
    }
    if set(source_bindings) != set(permitted_paths):
        hold("HOLD_DYNAMIC_CONTEXT_SOURCE_SET_DRIFT")
    for ref, path in permitted_paths.items():
        bound = source_bindings[ref]
        if path.is_symlink() or path.resolve(strict=True) != path:
            hold("HOLD_DYNAMIC_CONTEXT_SOURCE_PATH_DRIFT")
        if not isinstance(bound, dict) or bound.get("size_bytes") != path.stat().st_size or not hmac.compare_digest(bound.get("sha256", ""), sha(path.read_bytes())):
            hold("HOLD_DYNAMIC_CONTEXT_SOURCE_HASH_DRIFT")
    try:
        head = subprocess.check_output(
            ["/usr/bin/git", "-C", str(ROOT), "rev-parse", "HEAD"],
            text=True, timeout=2, env={"PATH": "/usr/bin:/bin"}
        ).strip()
    except (OSError, subprocess.SubprocessError):
        hold("HOLD_CURRENT_HEAD_UNKNOWN")
    if head != s.get("git_head_observed"):
        hold("HOLD_CURRENT_HEAD_DRIFT")
    # Existing real Total Field authority cannot be inferred from this test key.
    return data

def atomic_json_new(path, obj):
    data=json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False).encode()+b"\n"
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(data);f.flush();os.fsync(f.fileno())
    return sha(data)

def get_credential():
    if not CRED_PATH.is_file():
        return None
    _,r=read_json_file(CRED_PATH)
    if r.get("status")!="UNBOUND_MOBILE_DEVICE_KEY_CANDIDATE" or r.get("rp_id")!=HOSTNAME or r.get("origin")!=RP_ORIGIN:
        hold("HOLD_CREDENTIAL_STATE_DRIFT")
    return r

def get_credential_data():
    r=get_credential()
    if r is None: return None
    return AttestedCredentialData(b64dec(r["credential_data_b64url"]))

def independent_verify(receipt_id):
    if sha(INDEPENDENT_VERIFIER.read_bytes())!=INDEPENDENT_VERIFIER_SHA256:
        hold("HOLD_INDEPENDENT_VERIFIER_SOURCE_DRIFT")
    spec=importlib.util.spec_from_file_location("v7_independent_immutable_review", INDEPENDENT_VERIFIER)
    verifier=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    return verifier.verify_receipt(receipt_id)

def check_no_replay(pending):
    if utcnow()>parse_time(pending["expires_at"]):
        hold("HOLD_WEBAUTHN_CEREMONY_EXPIRED")
    scope=load_scope()
    if pending["request_sha256"]!=VIEW_REQUEST_SHA256 or pending["scope_challenge"]!=scope["scope_challenge"]:
        hold("HOLD_SIGNATURE_SCOPE_DRIFT")
    return scope

def start_registration():
    with lock:
        scope=load_scope()
        if get_credential() is not None:
            hold("HOLD_DEVICE_CREDENTIAL_ALREADY_ENROLLED")
        ceremony_id=secrets.token_urlsafe(24)
        options,state=fido.register_begin(
            PublicKeyCredentialUserEntity(
                id=b"w7tp-v7-provisional-mobile-device-key",
                name="W7TP Mobile Device Candidate",
                display_name="小J 設備簽章候選（尚未獲創辦人權威）",
            ),
            resident_key_requirement=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
            authenticator_attachment=None,
        )
        registrations[ceremony_id]={
            "state":state,"expires_at":timestamp(utcnow()+MAX_CEREMONY),
            "request_sha256":VIEW_REQUEST_SHA256,
            "scope_challenge":scope["scope_challenge"],
        }
        return {"state":"CANDIDATE_MOBILE_CREDENTIAL_REGISTRATION_CHALLENGE",
                "ceremony_id":ceremony_id,"options":dict(options),
                "notice":"Only a provisional device credential; NOT founder identity or D8 authority."}

def complete_registration(body):
    with lock:
        ceremony_id=str(body.get("ceremony_id",""))
        pending=registrations.pop(ceremony_id,None)
        if not pending:hold("HOLD_REGISTRATION_CEREMONY_MISSING_OR_REPLAY")
        check_no_replay(pending)
        if get_credential() is not None:hold("HOLD_DEVICE_CREDENTIAL_ALREADY_ENROLLED")
        response=body.get("response")
        if not isinstance(response,dict):hold("HOLD_REGISTRATION_RESPONSE_REQUIRED")
        parsed=RegistrationResponse.from_dict(response)
        auth=fido.register_complete(pending["state"],parsed)
        if not auth.is_user_verified() or auth.credential_data is None:
            hold("HOLD_WEBAUTHN_USER_VERIFICATION_ABSENT")
        if response.get("authenticatorAttachment") not in ("platform","cross-platform"):
            hold("HOLD_WEBAUTHN_PLATFORM_ATTESTATION_REQUIRED")
        record={
            "schema":"W7TP_V7_MOBILE_CREDENTIAL_CANDIDATE_V1",
            "status":"UNBOUND_MOBILE_DEVICE_KEY_CANDIDATE",
            "created_at":timestamp(utcnow()),
            "rp_id":HOSTNAME,"origin":RP_ORIGIN,
            "credential_data_b64url":b64enc(bytes(auth.credential_data)),
            "credential_id_b64url":b64enc(auth.credential_data.credential_id),
            "credential_attachment":response["authenticatorAttachment"],
            "verified_user_presence":auth.is_user_present(),
            "verified_user_verification":auth.is_user_verified(),
            "founder_identity_root_bound":False,"D8_EFFECT_AUTHORIZED":False,
        }
        credential_digest=atomic_json_new(CRED_PATH,record)
        return {"state":"PASS_WEBAUTHN_DEVICE_REGISTRATION_CANDIDATE_ONLY",
                "credential_sha256":credential_digest,"founder_identity_root_bound":False,
                "D8_EFFECT_AUTHORIZED":False,
                "message":"Face ID 裝置通行密鑰已建立（只作簽章候選）；尚未綁定既有創辦人身分根。"}

def start_signature():
    with lock:
        scope=load_scope()
        cred=get_credential_data()
        if cred is None:hold("HOLD_MOBILE_CREDENTIAL_NOT_ENROLLED")
        ceremony_id=secrets.token_urlsafe(24)
        # Cryptographically bind an unpredictable 256-bit challenge to the
        # exact frozen 24-hour request and its precise D4 effect.
        random_nonce=secrets.token_hex(32)
        tosign={
          "request_sha256":VIEW_REQUEST_SHA256,
          "scope_challenge":scope["scope_challenge"],
          "task_id":CHALLENGE_TASK,"effect":CHALLENGE_EFFECT,
          "nonce":random_nonce,
        }
        challenge=hashlib.sha256(jsonbytes(tosign)).digest()
        options,state=fido.authenticate_begin(
            [cred],user_verification=UserVerificationRequirement.REQUIRED,
            challenge=challenge,
        )
        signatures[ceremony_id]={
            "state":state,"issued_at":timestamp(utcnow()),
            "expires_at":timestamp(utcnow()+MAX_CEREMONY),
            "request_sha256":VIEW_REQUEST_SHA256,
            "scope_challenge":scope["scope_challenge"],
            "canonical_signing_payload":tosign,
            "challenge_b64url":b64enc(challenge),
            "credential_sha256":sha(CRED_PATH.read_bytes()),
        }
        return {
          "state":"PENDING_CANDIDATE_DEVICE_SIGNATURE",
          "ceremony_id":ceremony_id,"options":dict(options),
          "display":{
            "task_id":CHALLENGE_TASK,"effect":CHALLENGE_EFFECT,
            "request_sha256":VIEW_REQUEST_SHA256,
            "scope_expires_at":scope["scope"]["expires_at"],
            "sign_challenge_ttl_seconds":300,
            "founder_root_bound":False,
            "D8_EFFECT_AUTHORIZED":False,
          },
        }

def complete_signature(body):
    with lock:
        ceremony_id=str(body.get("ceremony_id",""))
        pending=signatures.pop(ceremony_id,None)
        if pending is None:hold("HOLD_SIGNING_CEREMONY_MISSING_OR_REPLAY")
        check_no_replay(pending)
        if sha(CRED_PATH.read_bytes())!=pending["credential_sha256"]:
            hold("HOLD_CREDENTIAL_HASH_DRIFT")
        response=body.get("response")
        if not isinstance(response,dict):hold("HOLD_SIGNATURE_RESPONSE_REQUIRED")
        parsed=AuthenticationResponse.from_dict(response)
        verified=fido.authenticate_complete(pending["state"],[get_credential_data()],parsed)
        if verified.credential_id!=get_credential_data().credential_id:
            hold("HOLD_CREDENTIAL_BINDING_MISMATCH")
        if not parsed.response.authenticator_data.is_user_verified() or not parsed.response.authenticator_data.is_user_present():
            hold("HOLD_USER_VERIFICATION_REQUIRED")
        if not hmac.compare_digest(pending["state"]["challenge"],pending["challenge_b64url"]):
            hold("HOLD_CHALLENGE_BINDING_DRIFT")
        # A signed device assertion is not a Founder-root proof.
        sys.path.insert(0,str(ROOT))
        from tools.total_field.founder_variable_cognition_gate import evaluate_founder_identity_gate
        gate=evaluate_founder_identity_gate({},None)
        if gate["decision"]!="HOLD":
            hold("HOLD_UNEXPECTED_FOUNDER_ROOT_GATE_RESULT")
        source={
            "assertion":response,"webauthn_state":pending["state"],
            "scope_sha256":VIEW_REQUEST_SHA256,
            "challenge_b64url":pending["challenge_b64url"],
            "signed_payload":pending["canonical_signing_payload"],
            "credential_sha256":pending["credential_sha256"],
            "issued_at":pending["issued_at"],
            "expires_at":pending["expires_at"],
        }
        receipt_id=secrets.token_hex(16)
        evidence_path=RECEIPT_DIR/(receipt_id+"_assertion.json")
        proof_sha=atomic_json_new(evidence_path,source)
        decision={
          "schema":"W7TP_V7_TOTAL_FIELD_PROVISIONAL_SIGNATURE_RECEIPT_V1",
          "state":"PASS_CRYPTO_SIGNATURE_ONLY_HOLD_FOUNDER_ROOT",
          "receipt_id":receipt_id,
          "signed_at":timestamp(utcnow()),
          "challenge_request_sha256":VIEW_REQUEST_SHA256,
          "credential_sha256":pending["credential_sha256"],
          "assertion_sha256":proof_sha,
          "assertion_ref":str(evidence_path),
          "original_effect":CHALLENGE_EFFECT,
          "original_task":CHALLENGE_TASK,
          "crypto_webauthn_signature_verified":True,
          "webauthn_user_verified":True,
          "dynamic_context_trusted_issuer_verified":False,
          "founder_identity_root_bound":False,
          "founder_gate_decision":gate["decision"],
          "founder_gate_reason":gate["reason_code"],
          "D4_TRUTH_VERIFIED":False,
          "D8_EFFECT_AUTHORIZED":False,
          "authorization_effects":[],
          "can_resume_formal_task":False,
        }
        decision["receipt_sha256"]=sha(jsonbytes(decision))
        out=RECEIPT_DIR/(receipt_id+"_decision.json")
        atomic_json_new(out,decision)
        independently_verified=independent_verify(receipt_id)
        if independently_verified.get("signature_verified") is not True or independently_verified.get("D8_EFFECT_AUTHORIZED") is not False:
            hold("HOLD_INDEPENDENT_CRYPTO_VERIFIER_NOT_CLOSED")
        return {
          "state":decision["state"],
          "receipt_id":receipt_id,
          "receipt_sha256":decision["receipt_sha256"],
          "webauthn_signature_verified":True,
          "independent_total_field_evidence_verifier":independently_verified["decision"],
          "D8_EFFECT_AUTHORIZED":False,
          "message":"iPhone 通行密鑰已完成真實簽章及驗章；因創辦人身分根未完成可信綁定，正式總場 D8 仍 HOLD。",
        }

PAGE="""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>小J｜iPhone Face ID 真實簽章候選</title>
<style>
body{background:#0b1724;color:#edf5ff;font-family:system-ui,-apple-system,sans-serif;padding:24px}
main{max-width:720px;margin:0 auto} article{background:#13263c;padding:22px;border:1px solid #3e586a;border-radius:16px}
button{display:block;padding:13px;width:100%;background:#4fd6a9;border:0;border-radius:12px;margin-top:14px;font-size:16px}
button:disabled{opacity:.45}p{line-height:1.6}pre{white-space:pre-wrap;word-break:break-word;border:1px solid #31485c;padding:12px}
.note{border-left:3px solid #f5bc5d;padding-left:12px;color:#ffdb9e}code{color:#a3e6ce}a{color:#96dbff}
</style></head><body><main><article>
<h1>小J｜iPhone Face ID 簽章</h1>
<p class="note">沿既有總場創辦人身分根接合；本頁只驗證裝置簽章，不會自行授予創辦人或 D8 權限。請先登入目前既有的 VS Code 網頁入口，才可操作本頁。</p>
<pre id="status">正在檢查目前挑戰…</pre>
<button id="register">① 使用 iPhone Face ID 建立本網域通行密鑰候選</button>
<button id="sign" disabled>② 使用 Face ID 簽署精確挑戰並產生驗章收據</button>
<p class="note">這次操作完成後會產生真實密碼學簽章收據，但若缺既有創辦人根的受信任綁定，正式 D8 結果仍為 HOLD；不會自動續作任何正式任務。</p>
<p>原有 <a href="https://taiji01.tailea1eef.ts.net:8445/">8445 挑戰頁</a> 保留不變。</p>
<p><a id="signedreceipt" href="#" hidden>檢視獨立密碼學簽章驗證收據（D8 HOLD）</a></p>
<script>
const el=document.getElementById("status"), rb=document.getElementById("register"),sb=document.getElementById("sign"),receiptLink=document.getElementById("signedreceipt");
const dec=s=>{s=s.replace(/-/g,"+").replace(/_/g,"/");while(s.length%4)s+="=";const b=atob(s),x=new Uint8Array(b.length);for(let i=0;i<b.length;i++)x[i]=b.charCodeAt(i);return x.buffer};
const enc=b=>{let s="";new Uint8Array(b).forEach(v=>s+=String.fromCharCode(v));return btoa(s).replace(/\\+/g,"-").replace(/\\//g,"_").replace(/=+$/,"")};
const creation=o=>{const p=o.publicKey;p.challenge=dec(p.challenge);p.user.id=dec(p.user.id);(p.excludeCredentials||[]).forEach(c=>c.id=dec(c.id));return {publicKey:p}};
const request=o=>{const p=o.publicKey;p.challenge=dec(p.challenge);(p.allowCredentials||[]).forEach(c=>c.id=dec(c.id));return {publicKey:p}};
const regJSON=c=>({id:c.id,rawId:enc(c.rawId),type:c.type,authenticatorAttachment:c.authenticatorAttachment,clientExtensionResults:c.getClientExtensionResults(),response:{clientDataJSON:enc(c.response.clientDataJSON),attestationObject:enc(c.response.attestationObject),transports:c.response.getTransports?c.response.getTransports():[]}});
const authJSON=c=>({id:c.id,rawId:enc(c.rawId),type:c.type,authenticatorAttachment:c.authenticatorAttachment,clientExtensionResults:c.getClientExtensionResults(),response:{clientDataJSON:enc(c.response.clientDataJSON),authenticatorData:enc(c.response.authenticatorData),signature:enc(c.response.signature),userHandle:c.response.userHandle?enc(c.response.userHandle):null}});
async function post(path,obj={}){const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},credentials:"same-origin",body:JSON.stringify(obj)});const j=await r.json();if(!r.ok)throw Error(j.reason_code||j.state||r.status);return j}
async function refresh(){try{const r=await fetch("status",{credentials:"same-origin"});const j=await r.json();el.textContent=JSON.stringify(j,null,2);rb.disabled=!!j.device_credential_candidate_enrolled;sb.disabled=!j.device_credential_candidate_enrolled||j.scope_valid!==true}catch(e){el.textContent=e.message}}
rb.onclick=async()=>{try{el.textContent="請確認 Safari Face ID，建立此網域的候選密鑰…";const o=await post("register/options");const c=await navigator.credentials.create(creation(o.options));const r=await post("register/complete",{ceremony_id:o.ceremony_id,response:regJSON(c)});el.textContent=r.message;await refresh()}catch(e){el.textContent="未建立密鑰："+e.message}};
sb.onclick=async()=>{try{const o=await post("sign/options");const d=o.display;if(!confirm("簽署這一個 D4 精確挑戰：\\n任務："+d.task_id+"\\n作用："+d.effect+"\\nSHA："+d.request_sha256+"\\n驗章期：5 分鐘\\n\\n不授權正式 D8，是否繼續？")){el.textContent="已取消。";return}const c=await navigator.credentials.get(request(o.options));const r=await post("sign/complete",{ceremony_id:o.ceremony_id,response:authJSON(c)});el.textContent=r.message+"\\n收據："+r.receipt_id+"\\nSHA256："+r.receipt_sha256;receiptLink.href="receipt/"+r.receipt_id;receiptLink.hidden=false}catch(e){el.textContent="簽章失敗："+e.message}};
refresh();
</script></article></main></body></html>"""


D4_EXISTING_HELPER_SOURCE_SHA256="ca365f8d1dab16380dcfc0f8d7eeec1cb5c8fe1c485db0d440e9238318ea1abd"
sys.path.insert(0,str(BASE))
import v11_existing_phone_exact_scope_extension as _d4

def d4_scoped():
    helper=BASE/"v11_existing_phone_exact_scope_extension.py"
    if helper.is_symlink() or sha(helper.read_bytes())!=D4_EXISTING_HELPER_SOURCE_SHA256:
        hold("HOLD_D4_SCOPED_EXISTING_HELPER_SOURCE_DRIFT")
    return _d4

V11_PAGE_TEMPLATE=r"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>小J｜D4 精確效果 Face ID 簽署</title>
<style>
*{box-sizing:border-box}
body{background:#0e1d30;color:#ecf4ff;font-family:-apple-system,BlinkMacSystemFont,system-ui,sans-serif;padding:22px;line-height:1.55}
main{max-width:720px;margin:0 auto}
article{background:#142b42;border:1px solid #456781;border-radius:18px;padding:23px}
h1{font-size:23px;margin:0 0 8px}
h2{font-size:16px;margin:22px 0 8px}
p{margin:10px 0}small{color:#b8cbdc}
pre{white-space:pre-wrap;word-break:break-word;padding:14px;background:#0b1928;border-radius:10px;font-size:13px;line-height:1.6}
code{overflow-wrap:anywhere;color:#adf3d9}
button{display:block;width:100%;padding:15px;border:0;border-radius:12px;margin-top:18px;background:#54dcb0;color:#061d17;font-size:17px;font-weight:700}
button:disabled{background:#8b98a4;color:#1a2a35}
.caution{padding:12px;border-left:3px solid #efbb73;background:#243241}
.tag{color:#aeeac9}
a{color:#a2dfff}
</style></head><body><main><article>
<h1>小J｜V11 重新驗證</h1>
<p class="tag">已重用既有 iPhone 通行密鑰；這是過期 V11 的新驗證請求，原簽章與使用紀錄均保留。</p>
<p class="caution"><strong>正式 D8 效果仍待總場裁決。</strong>這次 Face ID 是簽署限定意圖及授權請求；即使簽署成功，也不會直接部署、修改正典或發行 D4。</p>
<h2>這次唯一的兩項作用</h2>
<p>① 將現有手機通行密鑰可信綁定到本次 D4 創辦人身分。</p>
<p>② 申請由總場核准的 D4 發行者，最多發行一份已驗證十檔審查的正式收據。</p>
<h2>精確封包</h2>
<small>本次任務：D4_BROKER_ISSUANCE_TRUST_BINDING</small>
<pre>V11 SHA-256：__EXACT_SHA__
Scope challenge：__EXACT_CHALLENGE__
十檔來源：__TEN_SHA__
發行者公鑰候選：__ISSUER_SHA__
封包期限：__END_LOCAL__（台灣時間）
效力：待簽署、待總場正式 D8 裁決</pre>
<p id="result">__CURRENT_STATE__</p>
<button id="sign" disabled>等待本次重新驗證就緒</button>
<p><small>請本人按下簽署按鈕後使用 Face ID；每次挑戰最長五分鐘，舊簽章不會被重用。</small></p>
<p><a id="receipt" href="#" hidden>核對這次手機簽章收據</a></p>
<script>
const sign=document.getElementById('sign'),result=document.getElementById('result'),receipt=document.getElementById('receipt');
const endpoint=(path)=>{
  const isProxy=location.pathname.includes('/proxy/9122/');
  return (isProxy?'/proxy/9122/d4-exact':'/d4-exact')+path;
};
const unpack=(s)=>{
  s=s.split('-').join('+').split('_').join('/');
  while(s.length%4)s+='=';
  const raw=atob(s),buff=new Uint8Array(raw.length);
  for(let i=0;i<raw.length;i++)buff[i]=raw.charCodeAt(i);
  return buff.buffer;
};
const pack=(data)=>{
  const a=new Uint8Array(data);let raw='';
  for(const v of a)raw+=String.fromCharCode(v);
  return btoa(raw).split('+').join('-').split('/').join('_').replace(/=+$/,'');
};
const request=(options)=>{
  const x=options.publicKey;
  x.challenge=unpack(x.challenge);
  for(const c of (x.allowCredentials||[]))c.id=unpack(c.id);
  return {publicKey:x};
};
const toJSON=(c)=>({
  id:c.id,rawId:pack(c.rawId),type:c.type,
  authenticatorAttachment:c.authenticatorAttachment,
  clientExtensionResults:c.getClientExtensionResults(),
  response:{
    clientDataJSON:pack(c.response.clientDataJSON),
    authenticatorData:pack(c.response.authenticatorData),
    signature:pack(c.response.signature),
    userHandle:c.response.userHandle?pack(c.response.userHandle):null
  }
});
async function api(path,body){
  const res=await fetch(endpoint(path),{
    method:'POST',headers:{'Content-Type':'application/json'},
    credentials:'same-origin',body:JSON.stringify(body)
  });
  const j=await res.json();
  if(!res.ok)throw Error(j.reason_code||j.state||'未取得驗證許可');
  return j;
}
async function refresh(){
  try{
    const r=await fetch(endpoint('/status'),{credentials:'same-origin'});
    const s=await r.json();
    if(!r.ok)throw Error(s.reason_code||'目前不能簽署');
    sign.disabled=!s.operator_ready_to_start;
    if(s.signing_evidence_already_consumed){
      sign.disabled=true;sign.textContent='本次簽章已完成（不可再次簽署）';
      result.textContent='手機簽章已留證，等待總場正式 D8 裁決。';
      receipt.href=endpoint('/receipt');receipt.hidden=false;
    }else if(s.operator_ready_to_start){
      sign.textContent='用 iPhone Face ID 簽署本次兩項限定效果';
      result.textContent='已收到本人重啟驗證指示，現在可以啟動一次五分鐘挑戰。';
    }else{
      sign.textContent='等待本次重新驗證就緒';
      result.textContent='入口已接合，尚未開啟短效簽章窗口。';
    }
  }catch(e){sign.disabled=true;result.textContent='查詢總場失敗：'+e.message}
}
sign.onclick=async()=>{
  sign.disabled=true;
  try{
    if(!confirm('僅簽署本次 D4 身分綁定與一份 D4 收據發行請求。正式 D8 仍須總場裁決；不含部署、Git、資料庫及正典變更。是否繼續？')){
      await refresh();return;
    }
    const o=await api('/options',{});
    result.textContent='請使用 iPhone Face ID 確認，簽署時限五分鐘。';
    const c=await navigator.credentials.get(request(o.options));
    const z=await api('/complete',{ceremony_id:o.ceremony_id,response:toJSON(c)});
    result.textContent=z.message_zh_TW+'\n收據 SHA-256：'+z.evidence_sha256;
    receipt.href=endpoint('/receipt');receipt.hidden=false;
  }catch(e){result.textContent='簽署尚未完成：'+e.message}
  await refresh();
};
refresh();
</script></article></main></body></html>"""

def d4_scoped_page():
    from html import escape
    from datetime import timedelta,timezone
    helper=d4_scoped()
    s=helper.public_status()
    exp=helper.parse(s["original_scope_expires_at"]).astimezone(timezone(timedelta(hours=8)))
    replacements={
       "__EXACT_SHA__":s["scope_sha256"],
       "__EXACT_CHALLENGE__":s["scope_challenge"],
       "__TEN_SHA__":s["ten_static_manifest_sha256"],
       "__ISSUER_SHA__":s["issuer_existing_public_key_fingerprint_sha256"],
       "__END_LOCAL__":exp.strftime("%Y-%m-%d %H:%M:%S"),
       "__CURRENT_STATE__":s["state"],
    }
    result=V11_PAGE_TEMPLATE
    for token,value in replacements.items():result=result.replace(token,escape(value))
    return result


class Handler(BaseHTTPRequestHandler):
    server_version="W7TP-V7-DeviceSignatureCandidate/1.0"
    sys_version=""

    def log_message(self,*args):
        return

    def reply(self,status,obj,ctype="application/json; charset=utf-8"):
        raw=obj.encode() if isinstance(obj,str) else json.dumps(obj,ensure_ascii=False,sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type",ctype)
        self.send_header("Content-Length",str(len(raw)))
        self.send_header("Cache-Control","no-store")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("X-Frame-Options","DENY")
        self.send_header("Content-Security-Policy","default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-ancestors 'none'; form-action 'none'; connect-src 'self'")
        self.end_headers()
        if self.command!="HEAD":self.wfile.write(raw)

    def check_host(self):
        if self.headers.get("Host") not in CLIENT_HOSTS:
            hold("HOLD_HOST_HEADER_UNTRUSTED")

    def do_GET(self):
        try:
            self.check_host()
            route=urlsplit(self.path)
            if route.path in ("/d4-exact","/d4-exact/"):
                if route.query not in ("","utm_source=chatgpt.com"):
                    hold("HOLD_D4_LANDING_QUERY_FORBIDDEN")
                return self.reply(200,d4_scoped_page(),"text/html; charset=utf-8")
            if route.path=="/d4-exact/status":
                if route.query:hold("HOLD_D4_STATUS_QUERY_FORBIDDEN")
                return self.reply(200,d4_scoped().public_status())
            if route.path=="/d4-exact/receipt":
                if route.query:hold("HOLD_D4_RECEIPT_QUERY_FORBIDDEN")
                helper=d4_scoped()
                if not helper.EVIDENCE.is_file():
                    return self.reply(404,{"state":"NOT_YET_SIGNED"})
                checked=helper.verify_existing_phone_receipt(
                    helper.EVIDENCE,fido=fido,credential=get_credential_data())
                return self.reply(200,checked)
            # ChatGPT may append exactly this inert navigation-source query.
            # Whitelist GET landing ONLY; POST actions remain query-free.
            allowed_landing_query = (
                route.path in ("/", "/sign", "/sign/")
                and route.query == "utm_source=chatgpt.com"
            )
            if route.query and not allowed_landing_query:
                hold("HOLD_QUERY_PARAMETERS_FORBIDDEN")
            if route.path in ("/","/sign","/sign/"):
                return self.reply(200,PAGE,"text/html; charset=utf-8")
            if route.path in ("/status","/sign/status"):
                try:
                    scope=load_scope()
                    status={"scope_valid":True,"scope_challenge":scope["scope_challenge"],
                            "expires_at":scope["scope"]["expires_at"]}
                except Exception as exc:
                    status={"scope_valid":False,"scope_reason":str(exc)[:120]}
                status.update({"service":"V7_EXISTING_ROOT_DEVICE_SIGNATURE_CANDIDATE",
                               "credential_rp_id":HOSTNAME,"origin":RP_ORIGIN,
                               "device_credential_candidate_enrolled":get_credential() is not None,
                               "founder_identity_root_verified":False,
                               "formal_webauthn_signing_effect_authorized":False,
                               "D8_EFFECT_AUTHORIZED":False})
                return self.reply(200,status)
            if route.path.startswith("/receipt/"):
                ref=route.path.removeprefix("/receipt/")
                if len(ref)!=32 or any(c not in "0123456789abcdef" for c in ref):
                    hold("HOLD_RECEIPT_REF_INVALID")
                path=RECEIPT_DIR/(ref+"_decision.json")
                if not path.is_file():return self.reply(404,{"state":"HOLD","reason_code":"RECEIPT_NOT_FOUND"})
                raw,record=read_json_file(path)
                independent=independent_verify(ref)
                return self.reply(200,{
                    "signed_receipt":record,
                    "independent_total_field_evidence_verification":independent,
                })
            return self.reply(404,{"reason_code":"NOT_FOUND"})
        except Exception as exc:
            return self.reply(403,{"state":"HOLD","reason_code":str(exc)[:120]})

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        try:
            self.check_host()
            if self.headers.get("Origin")!=RP_ORIGIN:
                hold("HOLD_ORIGIN_MISMATCH")
            route=urlsplit(self.path)
            if route.query:hold("HOLD_QUERY_PARAMETERS_FORBIDDEN")
            length=int(self.headers.get("Content-Length","0"))
            if not 0<length<=65536:hold("HOLD_BODY_LENGTH_INVALID")
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict):hold("HOLD_BODY_OBJECT_REQUIRED")
            if route.path=="/d4-exact/options":
                if body:hold("HOLD_D4_EXACT_OPTIONS_BODY_NOT_EMPTY")
                helper=d4_scoped()
                return self.reply(200,helper.begin(fido,get_credential_data()))
            if route.path=="/d4-exact/complete":
                if set(body)!={"ceremony_id","response"} or not isinstance(body.get("ceremony_id"),str) or not isinstance(body.get("response"),dict):
                    hold("HOLD_D4_EXACT_COMPLETE_SHAPE_INVALID")
                helper=d4_scoped()
                return self.reply(200,helper.complete(fido,get_credential_data(),body["ceremony_id"],body["response"]))
            if route.path in ("/register/options","/sign/register/options"):
                return self.reply(200,start_registration())
            if route.path in ("/register/complete","/sign/register/complete"):
                return self.reply(200,complete_registration(body))
            if route.path in ("/sign/options","/sign/sign/options"):
                return self.reply(200,start_signature())
            if route.path in ("/sign/complete","/sign/sign/complete"):
                return self.reply(200,complete_signature(body))
            return self.reply(404,{"state":"HOLD","reason_code":"ROUTE_NOT_FOUND"})
        except (PermissionError,ValueError,TypeError,KeyError,FileExistsError) as exc:
            return self.reply(403,{"state":"HOLD","reason_code":str(exc)[:150]})
        except Exception:
            return self.reply(500,{"state":"HOLD","reason_code":"INTERNAL_SAFE_ERROR"})

    def do_PUT(self):
        return self.reply(405,{"reason_code":"METHOD_NOT_ALLOWED"})

    def do_DELETE(self):
        return self.reply(405,{"reason_code":"METHOD_NOT_ALLOWED"})

def main():
    if os.geteuid()==0:
        raise RuntimeError("HOLD_NO_ROOT")
    assert STATE_DIR.is_dir() and STATE_DIR.stat().st_mode&0o077==0
    assert RECEIPT_DIR.is_dir() and RECEIPT_DIR.stat().st_mode&0o077==0
    server=ThreadingHTTPServer(("127.0.0.1",PORT),Handler)
    print("V7_CANDIDATE_SERVER_ACTIVE_LOCAL_ONLY",flush=True)
    server.serve_forever()

if __name__=="__main__":
    main()
