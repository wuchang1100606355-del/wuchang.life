#!/usr/bin/env python3
"""Single-use Founder-Passkey G4 activation for the T-007 V2.3 successor."""
from __future__ import annotations
import argparse, hashlib, json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
from tools.total_field.w7tp_founder_passkey_v1 import verify_authorization_passkey, PasskeyVerificationError

EFFECT="AUTHORIZE_W7TP_V23_GLOBAL_CANONICAL_ACTIVATION"
MAX_REQUEST_TTL_SECONDS=1800
class G4Error(ValueError):
 def __init__(self,code,path="$"): self.code,self.path=code,path; super().__init__(f"{code}:{path}")
def cj(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()
def load(p):
 try: v=json.loads(Path(p).read_text())
 except Exception as e: raise G4Error("HOLD_G4_JSON_INVALID",str(p)) from e
 if not isinstance(v,dict): raise G4Error("HOLD_G4_OBJECT_REQUIRED",str(p))
 return v
def utc(s):
 try: d=datetime.fromisoformat(s.replace("Z","+00:00"))
 except Exception as e: raise G4Error("HOLD_G4_TIME_INVALID") from e
 if d.tzinfo is None: raise G4Error("HOLD_G4_TIME_INVALID")
 return d.astimezone(timezone.utc)
def safe(root,ref):
 p=(root/ref).resolve()
 try:p.relative_to(root)
 except ValueError as e: raise G4Error("HOLD_G4_PATH_ESCAPE",ref) from e
 if not p.is_file() or p.is_symlink(): raise G4Error("HOLD_G4_INPUT_MISSING",ref)
 return p
def atomic(path,data):
 fd,name=tempfile.mkstemp(prefix="."+path.name+".",dir=path.parent)
 try:
  with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
  os.replace(name,path)
 finally:
  if os.path.exists(name): os.unlink(name)
def validate(root,request,authorization,now):
 if request.get("schema_version")!="W7TP-T007-G4-ACTIVATION/1.0" or request.get("authorized_effect")!=EFFECT: raise G4Error("HOLD_G4_REQUEST_SCHEMA")
 if request.get("single_use") is not True or request.get("task_id")!="T-007": raise G4Error("HOLD_G4_REPLAY_POLICY")
 created,expires=utc(request.get("created_at","")),utc(request.get("expires_at",""))
 if expires<=created or (expires-created).total_seconds()>MAX_REQUEST_TTL_SECONDS or not(created<=now<expires): raise G4Error("HOLD_G4_REQUEST_EXPIRED")
 bindings=request.get("bindings")
 if not isinstance(bindings,dict): raise G4Error("HOLD_G4_BINDINGS_REQUIRED")
 paths={}
 for name,b in bindings.items():
  if not isinstance(b,dict) or set(b)!={"ref","sha256"}: raise G4Error("HOLD_G4_BINDING_SCHEMA",name)
  p=safe(root,b["ref"])
  if sha(p)!=b["sha256"]: raise G4Error("HOLD_G4_SOURCE_DRIFT",name)
  paths[name]=p
 seal=load(paths["g1_g3_formal_seal"])
 if seal.get("formal") is not True or seal.get("seal_state")!="FORMAL_SEAL" or seal.get("contract_approved") is not True: raise G4Error("HOLD_G4_FORMAL_SEAL_INVALID")
 if now>=utc(seal["expires_at"]): raise G4Error("HOLD_G4_FORMAL_SEAL_EXPIRED")
 if seal.get("source_manifest_sha256")!=bindings["final_manifest"]["sha256"]: raise G4Error("HOLD_G4_SEAL_FINAL_BINDING")
 predecessor=load(paths["authority_preimage"]); successor=load(paths["authority_successor"]); receipt=load(paths["authority_successor_receipt"])
 old=set(predecessor.get("allowed_effects",[])); new=set(successor.get("allowed_effects",[]))
 if not old.issubset(new) or (new-old!={EFFECT} and not (request.get("completion_mode")=="CURRENT_FIELD_AFTER_ACTIVATION" and old==new and EFFECT in old)): raise G4Error("HOLD_G4_AUTHORITY_EFFECT_LINEAGE")
 for k in ("state","contract_state","formal_decision_authority","formal_seal_authority","node_id","prohibited_effects"):
  if predecessor.get(k)!=successor.get(k): raise G4Error("HOLD_G4_AUTHORITY_NON_EFFECT_DRIFT",k)
 if receipt.get("state")!="PENDING_FOUNDER_PASSKEY_G4_ACCEPTANCE" or receipt.get("formal") is not False or receipt.get("acceptance_mode")!="FOUNDER_PASSKEY_G4_ATOMIC" or receipt.get("authorized_effect")!=EFFECT: raise G4Error("HOLD_G4_AUTHORITY_SUCCESSOR_NOT_FORMAL")
 if receipt.get("predecessor_sha256")!=bindings["authority_preimage"]["sha256"] or receipt.get("successor_sha256")!=bindings["authority_successor"]["sha256"]: raise G4Error("HOLD_G4_AUTHORITY_RECEIPT_BINDING")
 if request.get("completion_mode")=="CURRENT_FIELD_AFTER_ACTIVATION":
  prior=load(paths["prior_activation_receipt"])
  unsigned=dict(prior); supplied=unsigned.pop("receipt_sha256",None)
  if supplied!=hashlib.sha256(cj(unsigned)).hexdigest() or prior.get("state")!="ACTIVATED" or prior.get("authorized_effect")!=EFFECT: raise G4Error("HOLD_G4_PRIOR_RECEIPT_INVALID")
  if prior.get("pointer_postimage_sha256")!=bindings["canonical_pointer_preimage"]["sha256"] or prior.get("authority_postimage_sha256")!=bindings["authority_preimage"]["sha256"]: raise G4Error("HOLD_G4_PRIOR_POSTIMAGE_DRIFT")
  for name in ("current_state_field","current_state_field_router"):
   successor_field=load(paths[name+"_successor"])
   if successor_field.get("version")!="2.3" or successor_field.get("semantics")!="8_IN_1_SINGLE_DYNAMIC_STATE_FIELD": raise G4Error("HOLD_G4_FIELD_SUCCESSOR_INVALID",name)
   dims={d.get("id"):d.get("field_en",d.get("field")) for d in successor_field.get("dimensions",[])}
   if dims!={"D1":"Intent","D2":"State","D3":"Coordinate","D4":"Evidence","D5":"Execution/Policy","D6":"Generative State Transmission","D7":"Risk/Isolation","D8":"Envelope/Authority"}: raise G4Error("HOLD_G4_FIELD_DIMENSIONS_INVALID",name)
 try: verify_authorization_passkey(root,authorization,scope=request)
 except PasskeyVerificationError as e: raise G4Error(e.code,getattr(e,"path","$")) from e
 return paths
def activate(root,request_path,authorization_path,replay_root,receipt_path,now=None):
 now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc); request=load(request_path); authorization=load(authorization_path)
 nonce=request.get("nonce")
 marker=replay_root/(hashlib.sha256(str(nonce).encode()).hexdigest()+".consumed")
 if marker.exists(): raise G4Error("HOLD_G4_REPLAY")
 paths=validate(root,request,authorization,now)
 replay_root.mkdir(parents=True,exist_ok=True)
 try: fd=os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 except FileExistsError as e: raise G4Error("HOLD_G4_REPLAY") from e
 os.close(fd)
 pointer=paths["canonical_pointer_preimage"]; authority=paths["authority_preimage"]
 pointer_before=pointer.read_bytes(); authority_before=authority.read_bytes()
 mutations=[("authority",authority,paths["authority_successor"],request["bindings"]["authority_preimage"]["sha256"]),("pointer",pointer,paths["canonical_pointer_successor"],request["bindings"]["canonical_pointer_preimage"]["sha256"])]
 if request.get("completion_mode")=="CURRENT_FIELD_AFTER_ACTIVATION":
  mutations.extend((name,paths[name+"_preimage"],paths[name+"_successor"],request["bindings"][name+"_preimage"]["sha256"]) for name in ("current_state_field","current_state_field_router"))
 backups={name:target.read_bytes() for name,target,source,expected in mutations}
 backup_dir=receipt_path.parent/"rollback_preimages";backup_dir.mkdir(exist_ok=True)
 for name,data in backups.items():
  destination=backup_dir/(name+"_"+hashlib.sha256(data).hexdigest()+".json")
  if destination.exists() and destination.read_bytes()!=data: raise G4Error("HOLD_G4_BACKUP_DRIFT",name)
  if not destination.exists(): atomic(destination,data)

 try:
  if sha(pointer)!=request["bindings"]["canonical_pointer_preimage"]["sha256"] or sha(authority)!=request["bindings"]["authority_preimage"]["sha256"]: raise G4Error("HOLD_G4_CAS_PREIMAGE_DRIFT")
  for name,b in request["bindings"].items():
   if sha(paths[name])!=b["sha256"]: raise G4Error("HOLD_G4_SOURCE_DRIFT",name)
  for name,target,source,expected in mutations:
   if sha(target)!=expected: raise G4Error("HOLD_G4_CAS_PREIMAGE_DRIFT",name)
   atomic(target,source.read_bytes())
  from tools.total_field.w7tp_v2_3_candidate_source import active_canonical_binding
  active=active_canonical_binding(pointer)
  if active.get("version")!="2.3" or active.get("canonical_id")!="W7TP_8D_ADI_V2_3": raise G4Error("HOLD_G4_POSTLOAD_FAILED")
  out={"schema_version":"W7TP-T007-G4-ACTIVATION-RECEIPT/1.0","state":"ACTIVATED","task_id":"T-007","authorized_effect":EFFECT,"activated_at":now.isoformat().replace("+00:00","Z"),"nonce":nonce,"request_sha256":sha(request_path),"authorization_sha256":sha(authorization_path),"pointer_preimage_sha256":hashlib.sha256(pointer_before).hexdigest(),"pointer_postimage_sha256":sha(pointer),"authority_preimage_sha256":hashlib.sha256(authority_before).hexdigest(),"authority_postimage_sha256":sha(authority),"loaded_canonical_id":active["canonical_id"],"loaded_version":active["version"],"rollback_available":True}
  if request.get("completion_mode")=="CURRENT_FIELD_AFTER_ACTIVATION":
   out["completion_mode"]=request["completion_mode"]
   out["field_postimages"]={name:sha(target) for name,target,source,expected in mutations if name.startswith("current_state_field")}
   for name,target,source,expected in mutations:
    if sha(target)!=sha(source): raise G4Error("HOLD_G4_POSTLOAD_FAILED",name)
  out["receipt_sha256"]=hashlib.sha256(cj(out)).hexdigest(); atomic(receipt_path,json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True).encode()+b"\n"); return out
 except Exception:
  for name,target,source,expected in reversed(mutations): atomic(target,backups[name])
  marker.unlink(missing_ok=True); raise
def main():
 p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,required=True);p.add_argument("--request",type=Path,required=True);p.add_argument("--authorization",type=Path,required=True);p.add_argument("--replay-root",type=Path,required=True);p.add_argument("--receipt",type=Path,required=True);a=p.parse_args()
 try:r=activate(a.repo_root.resolve(),a.request.resolve(),a.authorization.resolve(),a.replay_root.resolve(),a.receipt.resolve())
 except G4Error as e: print(json.dumps({"state":"HOLD","reason_code":e.code,"path":e.path}));return 2
 print(json.dumps(r,ensure_ascii=False,sort_keys=True));return 0
if __name__=="__main__": raise SystemExit(main())
