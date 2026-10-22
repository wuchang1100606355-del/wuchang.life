"""Capture a real mobile approval of the fixed GST promotion contract first.

No root private key, grant issuance, receipt repair, promotion, or D8 role binding.
The caller enforces request Host/Origin and request-body limits. GET is read-only.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import re
import secrets
import stat
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fido2 import cbor
from fido2.server import Fido2Server
from fido2.webauthn import AuthenticationResponse, AttestedCredentialData, UserVerificationRequirement

RP_ID = 'taiji01.tailea1eef.ts.net'
ORIGIN = 'https://taiji01.tailea1eef.ts.net:8444'
ROOT = Path('/home/taiji_admin/Taiji_Hub')
BUNDLE = 'artifacts/8d-adi-workloop/gst-v21-promotion-contract-20261021T193300Z'
LEAF = 'manifests/total_field/origin_cell_gst_v21_specification'
CONTRACT_SHA = '7a8e405e5edde1a03a3a086742caf132bda3d7e464e6293936d2bc9057f66e49'
DESCRIPTOR_SHA = '6c245b22d17da0dff2237d919616c0ee398d00b8002f0ca7e44fcddc70f17a7f'
CRED_SHA = 'dc3e0c3b3a8d2abce785157f57f7581c378e5fda960e086666b624f2ff393de5'
COSE_SHA = 'f7227e7f2738202e79b3aecee7f853dfe62e28b2ebcc24b4af6fb68c24b2f502'
CRED = Path('/tmp/w7tp_d4_redteam_8CYJzxxe/V7_MOBILE_DEVICE_SIGNATURE_CANDIDATE/mobile_candidate_public_credential.json')
STATE = Path('/home/taiji_admin/.local/share/w7tp-passkey-d8/gst-v21/mobile-approval-first')
EVIDENCE = STATE / 'SIGNED_APPROVAL.json'
PUBLIC_CRED = STATE / 'phone_credential_public.json'
LOCK = threading.RLock()
SCOPE = 'GST_V21_MOBILE_APPROVE_FIXED_PROMOTION_CONTRACT_V1'
DOMAIN = 'W7TP_GST_V21_MOBILE_FIXED_PROMOTION_CONTRACT_APPROVAL_V1'
MAX_BYTES = 131072
FILES = {
    BUNDLE + '/PROMOTION_CONTRACT.json': CONTRACT_SHA,
    BUNDLE + '/ADMISSION_DESCRIPTOR.json': DESCRIPTOR_SHA,
}
INTENDED_POSTIMAGES = {
    LEAF + '/SPECIFICATION.md': '0cf1d5f6f0c55bf1193cfd1227404b1999e61f1472d66eb8fd6087f2cd038855',
    LEAF + '/CANONICAL_RECORD.json': 'da238cde240dd2dfb77176db274180ca7e47f684046b7f4e306080b82e550d6f',
    'configs/total_field/w7tp_capability_internalization_registry_v1.json': '604fd4d1cc9f186f634dc9629aecd5a7c3d8fda9965660ea37ceef59a2ee1bb2',
}

def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def b64(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')

def unb64(value):
    require(isinstance(value, str) and len(value) <= MAX_BYTES and re.fullmatch(r'[A-Za-z0-9_-]+', value), 'BASE64URL_INVALID')
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))

def require(condition, reason):
    if not condition:
        raise PermissionError(reason)

def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'TIME_ZONE_REQUIRED')
    return result

def safe_path(path):
    require(path.is_absolute() and path.resolve() == path, 'SYMLINK_OR_RELATIVE_PATH_REJECTED')
    for part in (path, *path.parents):
        require(not part.is_symlink(), 'SYMLINK_REJECTED')

def raw_read(path, expected=None):
    safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_BYTES, 'SOURCE_TYPE_OR_SIZE_INVALID')
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES and (expected is None or sha(raw) == expected), 'SOURCE_HASH_OR_SIZE_INVALID')
    return raw

def read(path, expected=None):
    value = json.loads(raw_read(path, expected))
    require(isinstance(value, dict), 'SOURCE_SHAPE_INVALID')
    return value

def private_dir(path):
    safe_path(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    safe_path(path)
    info = path.stat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and info.st_mode & 0o077 == 0, 'PRIVATE_STATE_DIRECTORY_REQUIRED')

def initialize_state():
    private_dir(STATE)
    private_dir(STATE / 'ceremonies')
    if PUBLIC_CRED.exists():
        key_from_public(read(PUBLIC_CRED, CRED_SHA)['credential_data_b64url'])
    else:
        raw = raw_read(CRED, CRED_SHA)
        key_from_public(json.loads(raw)['credential_data_b64url'])
        persist_bytes_new(PUBLIC_CRED, raw)

def persist_bytes_new(path, raw):
    private_dir(path.parent)
    safe_path(path)
    require(len(raw) <= MAX_BYTES, 'PROOF_TOO_LARGE')
    # Atomic append-only publication: a crash cannot expose a partial JSON file.
    temporary = path.parent / ('.write-' + secrets.token_hex(16))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.link(temporary, path, follow_symlinks=False)
        dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        temporary.unlink(missing_ok=True)
    return raw

def persist_new(path, value):
    return persist_bytes_new(path, canon(value) + b'\n')

def bindings():
    return {
        'scope': SCOPE, 'target': str(ROOT), 'contract_sha256': CONTRACT_SHA,
        'descriptor_sha256': DESCRIPTOR_SHA, 'fixed_input_file_sha256': FILES,
        'approval_intent': 'APPROVE_FIXED_PROMOTION_CONTRACT',
        'intended_static_postimage_sha256': INTENDED_POSTIMAGES,
        'intended_postimages_are_current_state_claim': False,
        'receipt_repair_authorized_by_this_signature': False,
        'credential_file_sha256': CRED_SHA, 'mobile_cose_sha256': COSE_SHA,
        'rp_id': RP_ID, 'origin': ORIGIN, 'retroactive_human_signature_claim': False,
        'runtime_activation_authorized': False, 'other_writes_authorized': False,
    }

def make_server():
    return Fido2Server({'id': RP_ID, 'name': 'W7TP 手機授權'}, verify_origin=lambda origin: origin == ORIGIN)

def key_from_public(encoded):
    key = AttestedCredentialData(unb64(encoded))
    require(sha(cbor.encode(key.public_key)) == COSE_SHA, 'MOBILE_PUBLIC_KEY_MISMATCH')
    return key

def credential():
    record = read(PUBLIC_CRED if PUBLIC_CRED.exists() else CRED, CRED_SHA)
    encoded = record['credential_data_b64url']
    return key_from_public(encoded), encoded

def check_signing_inputs():
    for relative, expected in FILES.items():
        raw_read(ROOT / relative, expected)
    return credential()

def check_pending(pending):
    require(pending.get('schema') == DOMAIN + '/PENDING', 'PENDING_SCHEMA')
    payload = pending['signed_payload']
    require(payload.get('bindings') == bindings(), 'EXACT_SCOPE_CHANGED')
    require(set(payload) == {'bindings', 'ceremony_id', 'nonce', 'issued_at', 'expires_at', 'public_credential_sha256', 'single_use', 'transport_delay_requires_new_signature'}, 'PAYLOAD_FIELDS')
    require(re.fullmatch(r'[0-9a-f]{32}', payload['ceremony_id']) and pending['ceremony_id'] == payload['ceremony_id'], 'CEREMONY_ID')
    require(len(unb64(payload['nonce'])) == 32 and payload['single_use'] is True and payload['transport_delay_requires_new_signature'] is False, 'CHALLENGE_POLICY')
    require(0 < (instant(payload['expires_at']) - instant(payload['issued_at'])).total_seconds() <= 300, 'CHALLENGE_TTL')
    require(sha(unb64(pending['public_credential_b64url'])) == payload['public_credential_sha256'], 'PUBLIC_CREDENTIAL_BINDING')
    challenge = hashlib.sha256(canon([DOMAIN, payload])).digest()
    require(pending['webauthn_state'].get('challenge') == b64(challenge) and pending['webauthn_state'].get('user_verification') == 'required', 'CHALLENGE_STATE')
    return payload

def verify_proof(fido, proof):
    require(proof.get('schema') == DOMAIN + '/SIGNED_APPROVAL', 'PROOF_SCHEMA')
    pending = proof['pending']; payload = check_pending(pending)
    require(instant(payload['issued_at']) <= instant(proof['verified_at']) < instant(payload['expires_at']), 'VERIFICATION_OUTSIDE_CEREMONY')
    parsed = AuthenticationResponse.from_dict(proof['assertion'])
    client = json.loads(bytes(parsed.response.client_data))
    require(client.get('origin') == ORIGIN and client.get('crossOrigin', False) is False, 'EXACT_ORIGIN_REQUIRED')
    key = key_from_public(pending['public_credential_b64url'])
    verified = fido.authenticate_complete(pending['webauthn_state'], [key], parsed)
    auth = parsed.response.authenticator_data
    require(verified.credential_id == key.credential_id and auth.rp_id_hash == hashlib.sha256(RP_ID.encode()).digest(), 'EXACT_MOBILE_CREDENTIAL_AND_RP_REQUIRED')
    require(auth.is_user_present() and auth.is_user_verified(), 'USER_PRESENCE_AND_VERIFICATION_REQUIRED')
    require(proof.get('founder_binding_verified') is False and proof.get('formal_effect_authorized') is False, 'SIGNATURE_ONLY_STATE_REQUIRED')
    return {
        'state': 'MOBILE_SIGNATURE_SAVED_NATIVE_BINDING_PENDING', 'signature_verified': True,
        'human_approval_intent_captured': True, 'founder_binding_verified': False,
        'formal_effect_authorized': False, 'canonical_promotion_executed': False,
        'receipt_repair_executed': False, 'ed25519_grant_issued': False,
        'contract_sha256': CONTRACT_SHA, 'evidence_sha256': sha(canon(proof) + b'\n'),
        'verified_at': proof['verified_at'], 'can_request_passkey': False,
        'message': '手機授權簽章已保存；後續回執修復與身分綁定另行處理。',
    }

def _existing_pending():
    directory = STATE / 'ceremonies'
    if not directory.exists():
        return []
    safe_path(directory)
    result = []
    for item in directory.iterdir():
        require(re.fullmatch(r'[0-9a-f]{32}', item.name) is not None and not item.is_symlink(), 'CEREMONY_DIRECTORY_INVALID')
        pending = read(item / 'PENDING.json'); check_pending(pending); result.append(pending)
    return sorted(result, key=lambda value: instant(value['signed_payload']['issued_at']), reverse=True)

def public_entry(function):
    def guarded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except PermissionError:
            raise
        except Exception:
            # Never return assertion bytes, credential IDs, or library exception
            # contents through the HTTP wrapper.
            raise PermissionError('MOBILE_SIGNATURE_INPUT_OR_STATE_REJECTED') from None
    return guarded

@public_entry
def status(fido):
    with LOCK:
        if EVIDENCE.exists():
            return verify_proof(fido, read(EVIDENCE))
        check_signing_inputs()
        pending = _existing_pending()
        now = datetime.now(timezone.utc)
        current = next((value for value in pending if instant(value['signed_payload']['expires_at']) > now), None)
        out = {'state': 'SIGNING_IN_PROGRESS' if current else 'SIGNING_WINDOW_EXPIRED' if pending else 'READY_TO_SIGN',
               'signature_verified': False, 'founder_binding_verified': False,
               'formal_effect_authorized': False, 'can_request_passkey': True,
               'contract_sha256': CONTRACT_SHA, 'receipt_repair_executed': False}
        if current:
            out['expires_at'] = current['signed_payload']['expires_at']
        return out

@public_entry
def begin(fido):
    with LOCK:
        if EVIDENCE.exists():
            return verify_proof(fido, read(EVIDENCE))
        key, encoded = check_signing_inputs()
        now = datetime.now(timezone.utc)
        for pending in _existing_pending():
            if instant(pending['signed_payload']['issued_at']) <= now < instant(pending['signed_payload']['expires_at']):
                return {'state': 'SIGNING_IN_PROGRESS', 'ceremony_id': pending['ceremony_id'],
                        'options': pending['options'], 'expires_at': pending['signed_payload']['expires_at'],
                        'remaining_ms': max(1, int((instant(pending['signed_payload']['expires_at']) - now).total_seconds() * 1000)), 'pending_reused': True}
        initialize_state()
        ceremony_id = secrets.token_hex(16)
        payload = {'bindings': bindings(), 'ceremony_id': ceremony_id, 'nonce': b64(secrets.token_bytes(32)),
                   'issued_at': now.isoformat(), 'expires_at': (now + timedelta(seconds=300)).isoformat(),
                   'public_credential_sha256': sha(unb64(encoded)), 'single_use': True,
                   'transport_delay_requires_new_signature': False}
        challenge = hashlib.sha256(canon([DOMAIN, payload])).digest()
        options, state = fido.authenticate_begin([key], user_verification=UserVerificationRequirement.REQUIRED, challenge=challenge)
        options = dict(options)
        for allowed in options.get('publicKey', {}).get('allowCredentials', []):
            allowed.pop('transports', None)
        pending = {'schema': DOMAIN + '/PENDING', 'ceremony_id': ceremony_id, 'signed_payload': payload,
                   'webauthn_state': state, 'public_credential_b64url': encoded, 'options': options}
        persist_new(STATE / 'ceremonies' / ceremony_id / 'PENDING.json', pending)
        return {'state': 'SIGNING_IN_PROGRESS', 'ceremony_id': ceremony_id, 'options': options,
                'expires_at': payload['expires_at'], 'remaining_ms': 300000, 'pending_reused': False}

@public_entry
def complete(fido, body):
    with LOCK:
        require(isinstance(body, dict) and set(body) == {'ceremony_id', 'response'} and len(canon(body)) <= MAX_BYTES, 'COMPLETION_SHAPE_OR_SIZE_INVALID')
        if EVIDENCE.exists():
            return verify_proof(fido, read(EVIDENCE))
        require(isinstance(body['ceremony_id'], str) and re.fullmatch(r'[0-9a-f]{32}', body['ceremony_id']), 'CEREMONY_ID_INVALID')
        pending = read(STATE / 'ceremonies' / body['ceremony_id'] / 'PENDING.json')
        payload = check_pending(pending)
        now = datetime.now(timezone.utc)
        require(instant(payload['issued_at']) <= now < instant(payload['expires_at']), 'SIGNING_WINDOW_EXPIRED')
        proof = {'schema': DOMAIN + '/SIGNED_APPROVAL', 'pending': pending, 'assertion': body['response'],
                 'verified_at': now.isoformat(), 'verified_at_source': 'LOCAL_SERVER_OBSERVATION_NOT_INDEPENDENT_SIGNING_TIMESTAMP',
                 'founder_binding_verified': False, 'formal_effect_authorized': False}
        summary = verify_proof(fido, proof)
        # No target/readback/role/receipt action comes between crypto verification
        # and persistence. Subsequent repair or native acceptance cannot lose proof.
        raw = persist_new(EVIDENCE, proof)
        require(sha(raw_read(EVIDENCE)) == sha(raw), 'SAVED_PROOF_READBACK_MISMATCH')
        return summary

PAGE = r'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GST V2.1 手機授權</title><style>
*{box-sizing:border-box}body{margin:0;background:#101a27;color:#f0f5ff;font:17px/1.65 system-ui,sans-serif}main{max-width:720px;margin:4vh auto;padding:24px}section{background:#1a2a3d;border-radius:18px;padding:24px}h1{font-size:28px;line-height:1.3}button,a.phone{display:block;width:100%;box-sizing:border-box;padding:17px;margin:14px 0;border:0;border-radius:11px;font:700 18px system-ui;text-align:center;background:#98edc6;color:#102c20;text-decoration:none;cursor:pointer}button:disabled{opacity:.5;cursor:default}button#cancel{background:#e4eaf3}code{font-size:12px;overflow-wrap:anywhere}#result{white-space:pre-wrap}small{color:#c2cfe0}#phoneqr{max-width:190px;width:100%;background:white;border-radius:8px}summary{cursor:pointer}</style></head><body><main><section>
<h1>先完成手機授權</h1><p>請優先在 <strong>iPhone 的 Safari</strong> 開啟此頁，使用先前已登錄的手機通行金鑰。電腦上的 Windows 通行金鑰與這把手機金鑰不同。</p>
<a class="phone" href="https://taiji01.tailea1eef.ts.net:8444/proxy/9122/gst-v21/">在手機開啟</a><img id="phoneqr" alt="在手機開啟此授權頁的 QR 碼" hidden>
<p><strong>本次授權內容：</strong>核准固定契約指定的 GST V2.1 靜態規格升格；簽章先保存，後續回執修復與身分綁定另行處理。</p>
<p>本次簽章只核准這份固定契約，不宣稱目前的規格檔案或回執已符合契約。此頁不授權回執修復、不直接修改回執，也不會將手機金鑰自行升為 Founder 權限。</p>
<button id="sign" disabled>使用手機通行金鑰授權</button><button id="cancel" hidden disabled>取消等待，恢復按鈕</button><button id="retrysave" hidden disabled>重試保存同一份簽章，不需重簽</button><p id="result" role="status" aria-live="polite">正在讀取既有狀態…</p>
<details><summary>核對固定範圍</summary><p>契約：<code>7a8e405e5edde1a03a3a086742caf132bda3d7e464e6293936d2bc9057f66e49</code></p><p>固定授權描述：<code>6c245b22d17da0dff2237d919616c0ee398d00b8002f0ca7e44fcddc70f17a7f</code></p><small>不倒填舊的本人簽署、不啟用執行階段。重新開啟頁面不產生挑戰；同一個未到期的驗證窗口會沿用。已保存的簽章不因後續傳輸或修復延遲而要求重簽。</small></details>
</section></main><script>
'use strict';
const $=id=>document.getElementById(id),base=location.pathname.includes('/proxy/9122/')?'/proxy/9122/gst-v21':'/gst-v21';
let active=null,sequence=0,current=null,pendingSubmission=null;
const decode=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-s.length%4)%4)),c=>c.charCodeAt(0));
const encode=b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
function serialized(c){return{id:c.id,rawId:encode(c.rawId),type:c.type,authenticatorAttachment:c.authenticatorAttachment,clientExtensionResults:c.getClientExtensionResults(),response:{clientDataJSON:encode(c.response.clientDataJSON),authenticatorData:encode(c.response.authenticatorData),signature:encode(c.response.signature),userHandle:c.response.userHandle?encode(c.response.userHandle):null}};}
async function api(path,body,signal){const r=await fetch(base+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal});const d=await r.json();if(!r.ok)throw Error(d.reason_code||d.reason||'服務未完成請求');return d;}
const live=op=>!!op&&active===op&&op.sequence===sequence;
function enable(){const waiting=active&&active.phase!=='saving';$('sign').disabled=!!active||!!pendingSubmission||!current?.can_request_passkey||!window.isSecureContext||!window.PublicKeyCredential;$('cancel').hidden=!waiting;$('cancel').disabled=!waiting;$('retrysave').hidden=!pendingSubmission;$('retrysave').disabled=!!active||!pendingSubmission;}
function show(d){current=d;if(d.signature_verified){$('sign').textContent='手機簽章已保存';$('result').textContent='手機授權簽章已保存；後續回執修復與身分綁定另行處理。\n目前尚未標記正式升格完成。\n簽章紀錄 SHA-256：'+d.evidence_sha256;}else{$('sign').textContent=d.state==='SIGNING_WINDOW_EXPIRED'?'開啟新的手機驗證窗口':'使用手機通行金鑰授權';$('result').textContent=d.state==='SIGNING_WINDOW_EXPIRED'?'先前窗口已逾時且未收到簽章。再次點按才會開啟新窗口，原契約與舊紀錄會保留。':'請在手機按下授權按鈕；未到期的窗口會沿用。';}enable();}
function cancel(op,timed=false){if(!live(op)||op.phase==='saving')return;active=null;clearTimeout(op.timer);op.controller.abort();$('result').textContent=timed?'本次等待已逾時，按鈕已恢復；尚未保存簽章。請點按重試。':'已取消等待，按鈕已恢復；未到期的窗口會沿用。';enable();}
$('cancel').onclick=()=>cancel(active);
async function savePending(op){
  const submission=pendingSubmission;if(!submission)throw Error('本頁沒有待保存的簽章');
  $('result').textContent='正在驗證並保存同一份手機簽章，不發起新的通行金鑰驗證…';
  const done=await api('/complete',submission.body);
  if(!live(op))return;
  if(done.signature_verified!==true)throw Error('伺服器尚未確認簽章保存');
  pendingSubmission=null;show(done);
}
function showSaveFailure(e){
  const expired=e.message==='SIGNING_WINDOW_EXPIRED';
  $('result').textContent=(expired?'伺服器回報原驗證窗口已逾時，尚未接受此簽章。':'手機已產生簽章，伺服器是否保存尚未確認：'+e.message+'。')+'\n同一份簽章仍暫存在本頁記憶體。請勿重新整理或關閉此頁；按「重試保存同一份簽章，不需重簽」只會再次提交原簽章。'+(pendingSubmission?.expires_at?'\n原驗證期限：'+pendingSubmission.expires_at:'')+'\n重試不會延長驗證期限；若伺服器尚未保存且期限已過，仍可能拒收。';
}
$('retrysave').onclick=async()=>{
  if(active||!pendingSubmission)return;
  const op={sequence:++sequence,controller:new AbortController(),phase:'saving',timer:null};active=op;enable();
  try{await savePending(op);}catch(e){if(live(op))showSaveFailure(e);}finally{if(live(op)){active=null;enable();}}
};

$('sign').onclick=async()=>{if(active||pendingSubmission||!current?.can_request_passkey)return;const op={sequence:++sequence,controller:new AbortController(),phase:'preparing',timer:null};active=op;enable();op.timer=setTimeout(()=>cancel(op,true),120000);try{$('result').textContent='正在開啟手機通行金鑰…';const sent=Date.now(),d=await api('/options',{},op.controller.signal);if(!live(op))return;if(d.signature_verified){show(d);return;}const remaining=Math.min(120000,Math.max(0,Number(d.remaining_ms)-(Date.now()-sent)));if(!Number.isFinite(remaining)||remaining<1){cancel(op,true);return;}clearTimeout(op.timer);op.timer=setTimeout(()=>cancel(op,true),remaining);const p=d.options.publicKey;p.challenge=decode(p.challenge);(p.allowCredentials||[]).forEach(c=>{c.id=decode(c.id);delete c.transports;});p.timeout=remaining;if(!/iPhone|iPad|Android/i.test(navigator.userAgent))p.hints=['hybrid'];op.phase='authenticating';enable();$('result').textContent='請在手機的通行金鑰視窗完成 Face ID、Touch ID 或裝置驗證。';const c=await navigator.credentials.get({publicKey:p,signal:op.controller.signal});if(!live(op))return;if(!c)throw Error('未取得手機簽章');clearTimeout(op.timer);pendingSubmission={body:{ceremony_id:d.ceremony_id,response:serialized(c)},expires_at:d.expires_at};op.phase='saving';enable();await savePending(op);}catch(e){if(live(op)){if(pendingSubmission)showSaveFailure(e);else $('result').textContent='尚未完成手機授權：'+e.message+'。若您在電腦看到 Windows 通行金鑰錯誤，請在 iPhone Safari 開啟上方手機連結。';}}finally{clearTimeout(op.timer);if(live(op)){active=null;enable();}}};
const qr=$('phoneqr');qr.onload=()=>{qr.hidden=false};qr.onerror=()=>{qr.hidden=true};qr.src=base+'/phone-link.svg';
api('/status').then(show).catch(e=>{$('result').textContent='暫時無法讀取簽署狀態：'+e.message;});
</script></body></html>'''
