#!/home/taiji_admin/.local/share/w7tp-passkey-d8/venv/bin/python
"""Reuse original V11; prepare one exact handoff. Never renew/sign/grant/deploy."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,os,sys
ROOT=Path("/home/taiji_admin/Taiji_Hub")
RUN=ROOT/"artifacts/8d-adi-workloop/v11-verification-restart-20261019T0556Z"
BRIDGE=Path("/tmp/w7tp_v11_d8_d4_bridge_isolated_20261018/v11_d8_to_d4_existing_gate_adapter.py")
CONTEXT=Path("/tmp/w7tp_v11_effect_bridge_candidate_20261018_JXzTQQ/v11_exact_effect_bridge_preflight.py")
V11=ROOT/"runtime/total_field/pending_signature_archive/W7TP_D4_MOBILE_TO_SIGN_20261018T091837Z/successor_v11_d4_real_task_waiting_effect"
PREP=V11/"D8_POST_SIGNATURE_EXACT_REVIEW_PREP_20261018T2115_TPE/D8_EXACT_V11_REVIEW_READY_NOT_RECEIVED.json"
PINS={BRIDGE:"2aeb01cb65e2d3eaf2c73daac8936d051d9e5be7656f35513dad3f36e1ea4ecf",CONTEXT:"564c803443cb6c0b6edaecec4735895daa99db71f69a8cf00940ad3f33bc2301",PREP:"445c7c1d7ded3e515cf5b0a17aefa77ec5ac90e481a37d09e28723f14581ee4d"}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(path,name):
 if path.is_symlink() or sha(path)!=PINS[path]:raise RuntimeError("HOLD_EXISTING_IMPLEMENTATION_DRIFT")
 spec=importlib.util.spec_from_file_location(name,path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module
def main():
 sys.path.insert(0,str(ROOT))
 bridge=load(BRIDGE,"existing_v11_bridge")
 context=load(CONTEXT,"existing_v11_context")
 if sha(PREP)!=PINS[PREP]:raise RuntimeError("HOLD_PREPARED_REQUEST_DRIFT")
 packet_hash,context_ok=context.current_native_task_packet()
 if not context_ok:raise RuntimeError("HOLD_CURRENT_NATIVE_CONTEXT")
 sources=bridge.load_sources()
 if not bridge.verify_historical(sources):raise RuntimeError("HOLD_ORIGINAL_SIGNATURE")
 prior=json.loads(PREP.read_text())
 authority=sources["authority"]
 roles=json.loads((V11/"PENDING_EXISTING_FOUNDER_AND_D4_ISSUER_ROLE_BINDING.json").read_text())
 field=json.loads((ROOT/"runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_CANONICAL.json").read_text())
 now=datetime.now(timezone.utc)
 scope_current=now<bridge.timestamp(sources["scope"]["scope"]["expires_at_utc"])
 gaps=[]
 if not (ROOT/field["activation_receipt_ref"]).is_file():gaps.append("EXACT_ACTIVE_FIELD_RECEIPT_UNRESOLVED")
 if not roles.get("founder_sealed_dual_root_trusted_OS_proof"):gaps.append("TRUSTED_FOUNDER_BINDING_NOT_SUPPLIED")
 if not roles.get("issuer_formal_D4_role_signed"):gaps.append("D4_ISSUER_ROLE_NOT_SIGNED")
 if not set(bridge.EFFECTS).issubset(set(authority.get("allowed_effects",[]))):gaps.append("V11_EFFECTS_NOT_IN_CURRENT_AUTHORITY")
 if not scope_current:gaps.append("ORIGINAL_REQUEST_EXPIRED_HISTORICAL_SIGNATURE_REMAINS_VALID")
 result={
 "state":"ORIGINAL_V11_EVIDENCE_HANDOFF_READY_NOT_FORMALLY_ACCEPTED",
 "task_ref":bridge.TASK,
 "existing_prepared_review_ref":str(PREP),"existing_prepared_review_sha256":PINS[PREP],
 "current_context_packet_sha256":packet_hash,
 "original_signature_crypto_verified_now":True,
 "historical_signature_is_current_effect_approval":False,
 "original_sources_sha256":{k:sha(p) for k,p in bridge.SRC.items()},
 "same_two_effects":list(bridge.EFFECTS),"maximum_total_D4_receipts":1,
 "new_identity":False,"new_scope":False,"new_challenge":False,"new_signature":False,
 "formal_D8_received":False,"D8_EFFECT_AUTHORIZED":False,"D4_ISSUED":False,
 "unresolved":gaps,
 "single_engineering_target":"tools/total_field/w7tp_d8_reviewer_entrypoint.py",
 "minimum_change":"Add an evidence-only admission handoff for the existing exact V11 review object; independent trusted signer binding, continuation/expiry, effect permission and issuer-role proofs remain mandatory before any ALLOW or D4 issue.",
 "reuse_implementation_refs":[str(BRIDGE),str(CONTEXT)],
 "next":"Wire the original exact V11 review object into the existing trusted Total Field admission/issuer path; do not ask for another phone signature or alter the old consumed marker."
 }
 raw=(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode()
 target=RUN/"evidence"/("EXISTING_V11_HANDOFF_"+hashlib.sha256(raw).hexdigest()[:16]+".json")
 if target.exists():
  if target.read_bytes()!=raw:raise RuntimeError("HOLD_EXISTING_HANDOFF_DRIFT")
 else:
  fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,"wb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
 print(json.dumps({"state":result["state"],"original_signature_crypto_verified_now":True,"current_context_packet_sha256":packet_hash,"handoff_path":str(target),"handoff_sha256":sha(target),"unresolved":gaps,"new_scope":False,"new_challenge":False,"D8_EFFECT_AUTHORIZED":False,"D4_ISSUED":False},ensure_ascii=False))
 return 0
if __name__=="__main__":
 try:raise SystemExit(main())
 except Exception as exc:
  print(json.dumps({"state":"HOLD_EXISTING_V11_HANDOFF","error":type(exc).__name__+":"+str(exc)[:130]}))
  raise SystemExit(2)
