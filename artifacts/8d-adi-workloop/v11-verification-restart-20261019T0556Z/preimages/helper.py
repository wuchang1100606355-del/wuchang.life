#!/usr/bin/env python3
"""Existing V7 signer task-bound D4 owner *request* adapter.

Only extends existing 9122 FIDO2 verifier. Never issues Total Field D8
effect, founder root, signed D4 issuer receipt or a new credential.
A short live challenge is impossible until a separate user-ready marker is
created AFTER the human says they are ready to sign.
"""
from __future__ import annotations
import hashlib,hmac,json,os,re,secrets,sys,threading
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any,Mapping

from fido2.webauthn import AuthenticationResponse
from fido2.server import Fido2Server
from fido2.webauthn import AttestedCredentialData,UserVerificationRequirement
from fido2.webauthn import PublicKeyCredentialRpEntity

ROOT=Path("/home/taiji_admin/Taiji_Hub")
DIR=ROOT/"runtime/total_field/pending_signature_archive/W7TP_D4_MOBILE_TO_SIGN_20261018T091837Z/successor_v11_d4_real_task_waiting_effect"
V11=DIR/"D8_D4_REAL_TASK_EFFECT_TO_SIGN_V11.json"
V11_SHA256="c716e5d9996e1a5457f43d1f3e984d1c9577e3cba5d1f9bd497cd375dd61eb13"
BOUND_PENDING=DIR/"PENDING_EXISTING_FOUNDER_AND_D4_ISSUER_ROLE_BINDING.json"
BOUND_PENDING_SHA256="ec792f2173b0b43ef555aa9791d3d09c49664e9861cc988ba40bbc9b19b9675e"
CRED=Path("/tmp/w7tp_d4_redteam_8CYJzxxe/V7_MOBILE_DEVICE_SIGNATURE_CANDIDATE/mobile_candidate_public_credential.json")
CRED_SHA256="dc3e0c3b3a8d2abce785157f57f7581c378e5fda960e086666b624f2ff393de5"
PREVIOUS=Path("/tmp/w7tp_d4_redteam_8CYJzxxe/V7_MOBILE_DEVICE_SIGNATURE_CANDIDATE/signature_receipts/38260e44b5159f0529edc388720bb629_assertion.json")
PREVIOUS_SHA256="18b956ca7e3fcfbbb649b25fce0c4edc03c6290c67b08889f709fb7dcf083b44"
TEN=Path("/tmp/w7tp_d4_redteam_8CYJzxxe/v5_owner_static_review_20261018T062128Z/STATIC_SOURCE_MANIFEST.json")
REVIEW=Path("/tmp/w7tp_d4_redteam_8CYJzxxe/v5_owner_static_review_20261018T062128Z/RESULT/TOTAL_FIELD_STATIC_REVIEW_RESULT.json")
WORK=ROOT/"state/WORK_LEDGER.json"
ACTIONS=ROOT/"state/ACTION_LEDGER.json"
AUTH=ROOT/"runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
CANON=ROOT/"runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
ARM_DIR=DIR/"owner_ready_windows"
CONSUMED=DIR/"V11_USER_EXACT_SCOPE_SIGNATURE_CONSUMED.json"
EVIDENCE=DIR/"V11_USER_EXACT_SCOPE_SIGNED_ASSERTION.json"
TASK="D4_BROKER_ISSUANCE_TRUST_BINDING"
AID="A-D4-MOBILE-TASK-ADMISSION-20261018"
FIDO_RP="taiji01.tailea1eef.ts.net"
FIDO_ORIGIN="https://taiji01.tailea1eef.ts.net:8444"
EFFECTS=(
 "BIND_EXISTING_IPHONE_WEBAUTHN_CREDENTIAL_TO_FOUNDER_IDENTITY_FOR_D4_ONCE",
 "AUTHORIZE_SINGLE_USE_D4_BROKER_TRUSTED_ISSUER_AND_RECEIPT_FOR_PINNED_STATIC_REVIEW",
)
TTL=timedelta(minutes=5)
V11_ARM_PREFIX="OWNER_READY_"
LOCK=threading.RLock()
PENDING:dict[str,dict[str,Any]]={}
ACTIVE_CEREMONY_LIMIT=1

class D4ScopedHold(ValueError):
    pass
def require(c,code):
    if not c:raise D4ScopedHold(code)
def canon(d):return json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(data):return hashlib.sha256(data).hexdigest()
def b64(raw):
    import base64
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
def utcnow():return datetime.now(timezone.utc)
def parse(value):
    try:return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(timezone.utc)
    except Exception as exc:raise D4ScopedHold("HOLD_DATETIME_INVALID") from exc
def file_sha(p,limit=300000):
    require(p.is_file() and not p.is_symlink() and p.resolve(strict=True)==p,"HOLD_SOURCE_FILE_INVALID")
    require(p.stat().st_size<=limit,"HOLD_SOURCE_OVERSIZE")
    return sha(p.read_bytes())
def read_json(p,limit=300000):
    file_sha(p,limit)
    d=json.loads(p.read_text(encoding="utf8"))
    require(isinstance(d,dict),"HOLD_SOURCE_SCHEMA")
    return d

def existing_credential_must_match(credential:AttestedCredentialData):
    """Signed proof can only use the already-enrolled iPhone public credential."""
    value=read_json(CRED,8000)
    import base64
    encoded=value["credential_data_b64url"]
    raw=base64.urlsafe_b64decode(encoded+"="*((4-len(encoded)%4)%4))
    require(isinstance(credential,AttestedCredentialData) and bytes(credential)==raw,
            "HOLD_NOT_THE_ENROLLED_IPHONE_CREDENTIAL")
    return True

def current_verified_sources(*,now:datetime|None=None):
    """Immutable exact-scope source checks. No FIDO ceremony, DB or mutation."""
    at=now or utcnow()
    require(file_sha(V11)==V11_SHA256,"HOLD_V11_SCOPE_HASH_DRIFT")
    p=read_json(V11);s=p["scope"]
    basis=dict(p);supplied=basis.pop("request_self_sha256",None)
    require(isinstance(supplied,str) and sha(canon(basis))==supplied,"HOLD_V11_SELFHASH")
    sys.path.insert(0,str(ROOT))
    from tools.total_field.w7tp_founder_passkey_v1 import scope_challenge
    require(p["scope_challenge"]==scope_challenge(s),"HOLD_REAL_NATIVE_CHALLENGE")
    require(p["state"]=="READY_FOR_OWNER_INTENT_SIGNATURE_ONLY_FORMAL_D8_PENDING","HOLD_SOURCE_STATE")
    require(p["formal_d8_effect_authorized"] is False and p["formal_d4_receipt_issued"] is False,"HOLD_FALSE_AUTHORITY")
    require(s["task_ref"]=="task:"+TASK and s["single_use"] is True,"HOLD_TASK_SCOPE")
    require(s["signature_ceremony_ttl_seconds_when_started"]==300,"HOLD_CHALLENGE_TTL")
    require(tuple(row["name"] for row in s["requested_scoped_effects"])==EFFECTS,"HOLD_EFFECT_SCOPE_CHANGED")
    require(at>=parse(s["created_at_utc"]) and at<parse(s["expires_at_utc"]),"HOLD_EXACT_SCOPE_EXPIRED")
    require(file_sha(CRED)==CRED_SHA256 and file_sha(PREVIOUS)==PREVIOUS_SHA256,"HOLD_PREVIOUS_CREDENTIAL_OR_EVIDENCE_DRIFT")
    c=read_json(CRED)
    require(c["status"]=="UNBOUND_MOBILE_DEVICE_KEY_CANDIDATE" and c["rp_id"]==FIDO_RP and c["origin"]==FIDO_ORIGIN,"HOLD_EXISTING_WEBAUTHN_CREDENTIAL_STATE")
    require(c["founder_identity_root_bound"] is False and c["D8_EFFECT_AUTHORIZED"] is False,"HOLD_CREDENTIAL_FALSE_ROOT_AUTHORITY")
    require(s["existing_mobile_credential_sha256"]==CRED_SHA256 and s["existing_mobile_signed_evidence_sha256"]==PREVIOUS_SHA256,"HOLD_CREDENTIAL_V11_SCOPE")
    require(file_sha(TEN)==s["ten_file_manifest_sha256"] and file_sha(REVIEW)==s["static_review_result_sha256"],"HOLD_TEN_SOURCE_ROOT_DRIFT")
    manifest=read_json(TEN)
    require(manifest["file_count"]==len(manifest["files"])==10,"HOLD_TEN_SOURCE_COUNT")
    for row in manifest["files"]:
        ref=Path("/tmp/w7tp_d4_redteam_8CYJzxxe")/row["path"]
        require(file_sha(ref)==row["sha256"] and ref.stat().st_size==row["size_bytes"],"HOLD_SOURCE_10_DRIFT")
    review=read_json(REVIEW)
    require(review["final_decision"]=="ACCEPT_STATIC_IMPLEMENTATION_CANDIDATE_ONLY" and review["single_use_consumed"] is True,"HOLD_CONSUMED_STATIC_REVIEW")
    require(review["source_files_verified"]==10 and review["deployment_authorized"] is False,"HOLD_STATIC_SCOPE_FALSE_EFFECT")
    require(file_sha(BOUND_PENDING)==BOUND_PENDING_SHA256,"HOLD_FOUNDER_OR_ISSUER_ROLE_SOURCE_CHANGED")
    roles=read_json(BOUND_PENDING)
    require(roles["task_ref"]==s["task_ref"] and roles["request_SHA256"]==V11_SHA256,"HOLD_ROLE_BINDING_SCOPE")
    require(roles["device_externally_authorized_as_Founder"] is False and roles["issuer_formal_D4_role_signed"] is False,"HOLD_PREMATURE_FORMAL_ROLE")
    keymeta=s["existing_authority_public_key_source_candidate"]
    require(keymeta["public_key_fingerprint_sha256"]==roles["issuer_existing_msi_authority_public_key_fingerprint"],"HOLD_ISSUER_FINGERPRINT_MISMATCH")
    require(keymeta["formal_D4_issuer_role_verified"] is False and keymeta["existing_D4_issuer"] is False,"HOLD_D4_ISSUER_ROLE_ALREADY_ACTIVE")
    current_work=read_json(WORK)
    t=next((x for x in current_work["TASKS"] if x.get("TASK_ID")==TASK),None)
    require(t is not None and t["STATE"]=="HOLD","HOLD_FORMAL_TASK_NOT_HOLD")
    from tools.total_field_dynamic_context_pull import canonical_sha256
    binding=s["current_task_context_binding"]
    require(canonical_sha256(t)==binding["task_canonical_sha256"],"HOLD_FORMAL_TASK_SHA_DRIFT")
    current_actions=read_json(ACTIONS)
    action=next((x for x in current_actions["ACTIONS"] if x.get("ACTION_ID")==AID),None)
    require(action is not None and action["STATE"]=="DONE" and canonical_sha256(action)==binding["action_canonical_sha256"],"HOLD_FORMAL_ACTION_EVIDENCE_DRIFT")
    require(action["LAST_CONFIRMED_EFFECT"].get("D8_EFFECT_AUTHORIZED") is False,"HOLD_ACTION_FORGED_AUTHORITY")
    adi_binding=next((e for e in t["D4_EVIDENCE"] if e.get("ref")==binding["adi_record_ref"]),None)
    require(adi_binding is not None and adi_binding["sha256"]==binding["adi_record_sha256"],"HOLD_NATIVE_ADI_TASK_BINDING_DRIFT")
    from tools.w7tp_task_state_minimum_packet import select_task_state_support_refs,build_task_state_minimum_packet
    refs=select_task_state_support_refs(task_id=TASK)
    require(refs["adi_record_ids"]==[binding["adi_record_ref"]] and AID in refs["action_refs"],"HOLD_NATIVE_TASK_REFS_DRIFT")
    packet=build_task_state_minimum_packet(task_id=TASK,**refs)
    require(packet["packet_sha256"]==binding["exact_task_native_minimum_packet_sha256"],"HOLD_NATIVE_TASK_PACKET_DRIFT")
    authority=read_json(AUTH)
    require(authority["node_id"]=="taiji01" and authority["formal_decision_authority"] is True,"HOLD_AUTHORITY_NODE_DRIFT")
    require(not any(e in authority["allowed_effects"] for e in EFFECTS),"HOLD_UNEXPECTED_EFFECT_ACTIVE_REQUIRES_NEW_SCOPE")
    require(file_sha(CANON)=="74752efc39ab9cf035a91b9e3886450d24e7bbf6ca2464d367e94cffd157f1f2","HOLD_CANONICAL_POINTER_DRIFT")
    return p

def arm_status(now=None):
    """Operator human readiness marker. This is NOT a cryptographic D8 grant."""
    t=now or utcnow()
    if not ARM_DIR.is_dir():return False,None
    paths=sorted(ARM_DIR.glob("OWNER_READY_*.json"),reverse=True)
    if len(paths)>16:return False,None
    for path in paths:
        try:
            x=read_json(path,8000)
            issued=parse(x["issued_at_utc"]);exp=parse(x["expires_at_utc"])
            if (x["state"]=="OWNER_SAID_CAN_SIGN_ARMED_WINDOW_ONLY"
                and x["V11_scope_file_sha256"]==V11_SHA256
                and x["V11_scope_challenge"]==read_json(V11)["scope_challenge"]
                and issued<=t<exp<=issued+TTL
                and x["D8_EFFECT_AUTHORIZED"] is False):
                return True,exp
        except (OSError,KeyError,ValueError,TypeError):continue
    return False,None

def public_status(*,now:datetime|None=None):
    t=now or utcnow()
    p=current_verified_sources(now=t);s=p["scope"]
    armed,until=arm_status(now=t)
    used=CONSUMED.is_file() or EVIDENCE.is_file()
    return {
      "schema":"W7TP_EXISTING_IPHONE_V11_D4_SINGLE_USE_OWNER_SIGNATURE_STATUS_V1",
      "state":"SIGNED_OWNER_INTENT_PENDING_TOTAL_FIELD_D8" if used else ("OWNER_READY_WINDOW_FOR_EXACT_SIGNATURE" if armed else "WAIT_OWNER_SAYS_CAN_SIGN"),
      "scope_sha256":V11_SHA256,
      "scope_challenge":p["scope_challenge"],
      "task_ref":s["task_ref"],
      "ten_static_manifest_sha256":s["ten_file_manifest_sha256"],
      "accepted_ten_source_count":10,
      "issuer_existing_public_key_fingerprint_sha256":s["existing_authority_public_key_source_candidate"]["public_key_fingerprint_sha256"],
      "issuer_role_state":"PENDING_FORMAL_D8",
      "existing_founder_identity_binding_state":"PENDING_FORMAL_D8",
      "requested_effects":list(EFFECTS),
      "original_scope_expires_at":s["expires_at_utc"],
      "original_mobile_credential_reused":True,
      "new_credential_registration_required":False,
      "faceid_challenge_duration_seconds":300,
      "operator_ready_to_start":armed and not used,
      "operator_ready_window_expires_at":until.isoformat() if until else None,
      "signing_evidence_already_consumed":used,
      "formal_D8_EFFECT_AUTHORIZED":False,
      "formal_D4_ISSUED":False,
      "new_FaceID_challenge_created_by_status":False,
    }

def begin(fido:Fido2Server,credential:AttestedCredentialData,*,pending:dict|None=None,now:datetime|None=None,fixture_only:bool=False,fixture_arm_until:datetime|None=None):
    """Begin only from user-triggered route after explicit operator readiness."""
    t=now or utcnow()
    request=current_verified_sources(now=t)
    require(isinstance(fido,Fido2Server) and isinstance(credential,AttestedCredentialData),"HOLD_EXISTING_SIGNER_REQUIRED")
    if not fixture_only:
        existing_credential_must_match(credential)
    if fixture_only:
        armed=bool(fixture_arm_until and t<fixture_arm_until)
        arm_expires=fixture_arm_until
    else:
        armed,arm_expires=arm_status(now=t)
        require(not CONSUMED.exists() and not EVIDENCE.exists(),"HOLD_ONE_REAL_SIGNATURE_ALREADY_RECORDED")
    require(armed and arm_expires is not None,"HOLD_USER_NOT_YET_READY_TO_SIGN")
    with LOCK:
        target=pending if pending is not None else PENDING
        for name,entry in list(target.items()):
            if t>=entry["expires_at"]:target.pop(name,None)
        require(not target,"HOLD_OTHER_EXACT_CHALLENGE_ALREADY_ACTIVE")
        s=request["scope"]
        body={
          "schema":"W7TP_V11_D4_FOUNDER_USER_INTENT_ES256_EXACT_CLAIMS_V1",
          "exact_scope_file_sha256":V11_SHA256,
          "exact_scope_challenge":request["scope_challenge"],
          "task_ref":"task:"+TASK,
          "current_adi_record_sha256":s["current_task_context_binding"]["adi_record_sha256"],
          "current_task_packet_sha256":s["current_task_context_binding"]["exact_task_native_minimum_packet_sha256"],
          "ten_source_manifest_sha256":s["ten_file_manifest_sha256"],
          "prior_real_phone_public_credential_sha256":s["existing_mobile_credential_sha256"],
          "issuer_candidate_public_key_fingerprint_sha256":s["existing_authority_public_key_source_candidate"]["public_key_fingerprint_sha256"],
          "requested_effects":list(EFFECTS),
          "D8_AWAITING_FORMAL_DECISION":True,
          "scope_one_time_nonce":s["one_time_nonce"],
          "ceremony_one_time_nonce":secrets.token_hex(32),
        }
        signature_challenge=hashlib.sha256(canon(body)).digest()
        options,state=fido.authenticate_begin([credential],user_verification=UserVerificationRequirement.REQUIRED,challenge=signature_challenge)
        ceremony=secrets.token_hex(16)
        stop=min(t+TTL,arm_expires,parse(s["expires_at_utc"]))
        require(stop>t,"HOLD_CEREMONY_EXPIRED_BEFORE_BEGIN")
        target[ceremony]={
           "issued_at":t,"expires_at":stop,"webauthn_state":state,
           "signed_payload":body,"webauthn_challenge_b64url":b64(signature_challenge),
           "scope_sha256":V11_SHA256,"credential_id":credential.credential_id,
           "fixture_only":fixture_only,
        }
        return {
         "state":"ISOLATED_REAL_DEVICE_INTENT_SIGNATURE_OPTIONS_NOT_D8_GRANT" if fixture_only else "REAL_PHONE_OWNER_INTENT_EXACT_EFFECT_CHALLENGE_300SEC",
         "ceremony_id":ceremony,"options":dict(options),
         "display":{
          "task_ref":s["task_ref"],
          "scope_sha256":V11_SHA256,"scope_challenge":request["scope_challenge"],
          "requested_effects":list(EFFECTS),
          "issuer_candidate_fingerprint":body["issuer_candidate_public_key_fingerprint_sha256"],
          "ten_manifest_sha256":s["ten_file_manifest_sha256"],
          "original_scope_expiry":s["expires_at_utc"],
          "ceremony_expiry":stop.isoformat(),
          "formal_D8_EFFECT_AUTHORIZED":False,
         },
         "fixture_only":fixture_only,
        }

def complete(fido:Fido2Server,credential:AttestedCredentialData,ceremony_id:str,assertion:Mapping,*,pending:dict|None=None,now:datetime|None=None,fixture_only:bool=False):
    """Signature completion uses real existing FIDO2 verifier; no D8 grant."""
    t=now or utcnow()
    with LOCK:
        target=pending if pending is not None else PENDING
        record=target.pop(ceremony_id,None)
        require(record is not None,"HOLD_CHALLENGE_NOT_ISSUED_OR_REPLAY")
        require(record["fixture_only"]==fixture_only,"HOLD_CEREMONY_MODE_MISMATCH")
        if not fixture_only:
            existing_credential_must_match(credential)
        require(record["issued_at"]<=t<record["expires_at"],"HOLD_CEREMONY_EXPIRED")
        request=current_verified_sources(now=t)
        require(record["scope_sha256"]==V11_SHA256 and request["scope_challenge"]==record["signed_payload"]["exact_scope_challenge"],"HOLD_BOUND_SCOPE_DRIFT")
        require(record["webauthn_state"]["challenge"]==record["webauthn_challenge_b64url"],"HOLD_CHALLENGE_STATE_DRIFT")
        require(b64(hashlib.sha256(canon(record["signed_payload"])).digest())==record["webauthn_challenge_b64url"],"HOLD_PENDING_SIGNED_PAYLOAD_CHANGED")
        require(record["signed_payload"]["requested_effects"]==list(EFFECTS),"HOLD_EFFECT_MUTATED_AFTER_ISSUANCE")
        require(record["signed_payload"]["ten_source_manifest_sha256"]==request["scope"]["ten_file_manifest_sha256"],"HOLD_TEN_SOURCE_DRIFT")
        require(record["signed_payload"]["scope_one_time_nonce"]==request["scope"]["one_time_nonce"],"HOLD_NONCE_TAMPER")
        if not fixture_only:
            armed,deadline=arm_status(now=t)
            require(armed,"HOLD_OPERATOR_READY_WINDOW_EXPIRED")
            require(not CONSUMED.exists() and not EVIDENCE.exists(),"HOLD_ALREADY_SIGNED_SCOPE")
        parsed=AuthenticationResponse.from_dict(assertion)
        verified=fido.authenticate_complete(record["webauthn_state"],[credential],parsed)
        require(verified.credential_id==credential.credential_id==record["credential_id"],"HOLD_CREDENTIAL_PUBLIC_KEY_MISMATCH")
        require(parsed.response.authenticator_data.is_user_present() and parsed.response.authenticator_data.is_user_verified(),"HOLD_FACEID_UV_UP_MISSING")
        evidence={
          "schema":"W7TP_V11_EXISTING_PHONE_ES256_EXACT_D4_FOUNDER_INTENT_ASSERTION_V1",
          "state":"PASS_WEBAUTHN_USER_INTENT_SIGNATURE_PENDING_TOTAL_FIELD_D8",
          "signed_at_utc":t.isoformat(),
          "request_scope_file_sha256":V11_SHA256,
          "request_scope_challenge":request["scope_challenge"],
          "task_ref":"task:"+TASK,
          "signed_payload":record["signed_payload"],
          "webauthn_state":record["webauthn_state"],
          "webauthn_assertion":dict(assertion),
          "registered_phone_credential_sha256":CRED_SHA256 if not fixture_only else "ISOLATED_TEST_CREDENTIAL",
          "fido2_validated":True,
          "user_verification_validated":True,
          "scope_is_single_use":True,
          "formal_owner_root_binding_verified":False,
          "formal_D8_EFFECT_AUTHORIZED":False,
          "formal_D4_ISSUED":False,
          "explicit_user_ready_window_ref":"OPERATOR_READY_AFTER_USER_MESSAGE" if not fixture_only else "ISOLATED_FIXTURE",
          "fixture_only":fixture_only,
        }
        evidence["evidence_self_sha256"]=sha(canon(evidence))
        if not fixture_only:
            # Atomic fail-closed one-use marker, before creating the receipt.
            marker={
              "scope_sha256":V11_SHA256,
              "signed_evidence_sha256":sha(canon(evidence)),
              "consumed_at_utc":t.isoformat(),
              "D8_EFFECT_AUTHORIZED":False,
              "D4_ISSUED":False,
            }
            atomic_write_new(CONSUMED,marker)
            atomic_write_new(EVIDENCE,evidence)
            recheck=verify_existing_phone_receipt(EVIDENCE,fido=fido,credential=credential)
            require(recheck["web_authn_signature_verified"] is True and recheck["D8_EFFECT_AUTHORIZED"] is False,"HOLD_INDEPENDENT_REAL_ES256_RECHECK")
        return {
          "state":evidence["state"],
          "web_authn_signature_verified":True,
          "request_scope_sha256":V11_SHA256,
          "signed_payload_sha256":sha(canon(record["signed_payload"])),
          "evidence_sha256":sha(canon(evidence)),
          "fixture_only":fixture_only,
          "formal_D8_EFFECT_AUTHORIZED":False,
          "formal_D4_ISSUED":False,
          "message_zh_TW":"已完成這次兩項精確效果的 iPhone Face ID 簽章。這是正式總場裁決的身分意圖證據；D8 尚未核准，D4 尚未發行。",
        }

def atomic_write_new(path,obj):
    raw=(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as h:h.write(raw);h.flush();os.fsync(h.fileno())
    return sha(raw)

def verify_existing_phone_receipt(path,*,fido:Fido2Server,credential:AttestedCredentialData):
    """Cryptographic verification without trusting claims as a D8 grant."""
    d=read_json(path,50000)
    basis=dict(d);h=basis.pop("evidence_self_sha256",None)
    require(h==sha(canon(basis)),"HOLD_SIGNED_EVIDENCE_SELFHASH")
    require(d["request_scope_file_sha256"]==V11_SHA256,"HOLD_EVIDENCE_SCOPE_SHA")
    current=current_verified_sources()
    require(d["request_scope_challenge"]==current["scope_challenge"],"HOLD_EVIDENCE_CHALLENGE")
    signed=d["signed_payload"]
    require(signed["requested_effects"]==list(EFFECTS) and signed["scope_one_time_nonce"]==current["scope"]["one_time_nonce"],"HOLD_EVIDENCE_SCOPE_BINDING")
    existing_credential_must_match(credential)
    assert_data=AuthenticationResponse.from_dict(d["webauthn_assertion"])
    trusted_server=Fido2Server(
        PublicKeyCredentialRpEntity(id=FIDO_RP,name="W7TP existing Founder phone"),
        verify_origin=lambda origin: origin==FIDO_ORIGIN)
    proof=trusted_server.authenticate_complete(d["webauthn_state"],[credential],assert_data)
    require(proof.credential_id==credential.credential_id,"HOLD_CRYPTO_PUBLIC_KEY_ID")
    require(assert_data.response.authenticator_data.is_user_present() and assert_data.response.authenticator_data.is_user_verified(),"HOLD_FACEID_VALIDATION")
    require(d["formal_D8_EFFECT_AUTHORIZED"] is False and d["formal_D4_ISSUED"] is False,"HOLD_FALSE_D8_AUTHORITY")
    return {"state":"PASS_EXISTING_WEBAUTHN_SIGNATURE_ONLY_PENDING_D8",
            "web_authn_signature_verified":True,"user_verification":True,
            "scope_sha256":V11_SHA256,"D8_EFFECT_AUTHORIZED":False,
            "D4_ISSUED":False}

if __name__=="__main__":
    print(json.dumps(public_status(),ensure_ascii=False,sort_keys=True,indent=2))
