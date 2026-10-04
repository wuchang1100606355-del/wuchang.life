from __future__ import annotations
import hashlib,json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from tools.total_field import w7tp_t007_g4_activation_v1 as g4
ROOT=Path(__file__).resolve().parents[1]
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True)+"\n");return hashlib.sha256(p.read_bytes()).hexdigest()
class G4ActivationTests(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory(dir=ROOT); base=Path(td.name); now=datetime.now(timezone.utc)
  canonical=ROOT/"manifests/total_field/w7tp_8d_adi_v2_3_canonical/CONTRACT.json"; schema=ROOT/"schemas/field/w7tp_8d_adi_v2_3_canonical_contract_v1.schema.json"
  pointer0={"schema":"w7tp.total_field.active_w7tp_canonical_pointer.v1","state":"ACTIVE_CANONICAL","namespace":"w7tp_canonical","canonical_id":"W7TP_8D_ADI_CANONICAL_V2_1_FOUNDER_LOCKED_SUCCESSOR_20260728","version":"2.1","canonical_path":"docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1_FOUNDER_LOCKED_SUCCESSOR_20260728.md","canonical_sha256":g4.sha(ROOT/"docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1_FOUNDER_LOCKED_SUCCESSOR_20260728.md"),"machine_schema_path":"schemas/w7tp_8d_multipurpose_packet_canonical_v2_1.schema.json","machine_schema_sha256":g4.sha(ROOT/"schemas/w7tp_8d_multipurpose_packet_canonical_v2_1.schema.json")}
  pointer1={**pointer0,"canonical_id":"W7TP_8D_ADI_V2_3","version":"2.3","canonical_path":canonical.relative_to(ROOT).as_posix(),"canonical_sha256":g4.sha(canonical),"machine_schema_path":schema.relative_to(ROOT).as_posix(),"machine_schema_sha256":g4.sha(schema)}
  authority0={"allowed_effects":["AUTHORIZE_FORMAL_SUCCESSOR_REBIND_REVIEW"],"contract_state":"ACTIVE_FORMAL","formal_decision_authority":True,"formal_seal_authority":True,"node_id":"taiji01","prohibited_effects":[],"state":"ACTIVE_TOTAL_FIELD_AUTHORITY"}
  authority1={**authority0,"allowed_effects":[*authority0["allowed_effects"],g4.EFFECT]}
  files={"canonical_pointer_preimage":base/"pointer.json","canonical_pointer_successor":base/"pointer-next.json","current_state_field_preimage":base/"field.json","authority_preimage":base/"authority.json","authority_successor":base/"authority-next.json","authority_successor_receipt":base/"authority-receipt.json","final_manifest":base/"manifest.json","g1_g3_formal_seal":base/"seal.json"}
  write(files["canonical_pointer_preimage"],pointer0);write(files["canonical_pointer_successor"],pointer1);write(files["current_state_field_preimage"],{"state":"CURRENT"});msha=write(files["final_manifest"],{"files":[]})
  write(files["authority_preimage"],authority0);write(files["authority_successor"],authority1)
  write(files["authority_successor_receipt"],{"state":"PENDING_FOUNDER_PASSKEY_G4_ACCEPTANCE","formal":False,"acceptance_mode":"FOUNDER_PASSKEY_G4_ATOMIC","authorized_effect":g4.EFFECT,"predecessor_sha256":g4.sha(files["authority_preimage"]),"successor_sha256":g4.sha(files["authority_successor"])})
  write(files["g1_g3_formal_seal"],{"formal":True,"seal_state":"FORMAL_SEAL","contract_approved":True,"expires_at":(now+timedelta(minutes=4)).isoformat(),"source_manifest_sha256":msha})
  bindings={k:{"ref":p.relative_to(ROOT).as_posix(),"sha256":g4.sha(p)} for k,p in files.items()}
  request={"schema_version":"W7TP-T007-G4-ACTIVATION/1.0","task_id":"T-007","authorized_effect":g4.EFFECT,"created_at":now.isoformat(),"expires_at":(now+timedelta(minutes=4)).isoformat(),"nonce":"nonce:test","single_use":True,"bindings":bindings}
  rp=base/"request.json";ap=base/"authorization.json";write(rp,request);write(ap,{"webauthn":{}})
  return td,base,files,rp,ap,now
 def test_cas_activation_and_replay(self):
  td,base,files,rp,ap,now=self.fixture()
  with td,patch.object(g4,"verify_authorization_passkey",return_value=object()):
   out=g4.activate(ROOT,rp,ap,base/"replay",base/"receipt.json",now)
   self.assertEqual("ACTIVATED",out["state"]);self.assertEqual("2.3",out["loaded_version"])
   with self.assertRaisesRegex(g4.G4Error,"HOLD_G4_REPLAY"):g4.activate(ROOT,rp,ap,base/"replay",base/"receipt2.json",now)
 def test_source_drift_stops_before_write(self):
  td,base,files,rp,ap,now=self.fixture()
  with td,patch.object(g4,"verify_authorization_passkey",return_value=object()):
   files["current_state_field_preimage"].write_text("{}")
   with self.assertRaisesRegex(g4.G4Error,"HOLD_G4_SOURCE_DRIFT"):g4.activate(ROOT,rp,ap,base/"replay",base/"receipt.json",now)
 def continuation(self,base,files,rp,ap,now):
  prior=base/'prior-receipt.json'
  g4.activate(ROOT,rp,ap,base/'first-replay',prior,now)
  request=json.loads(rp.read_text()); request['completion_mode']='CURRENT_FIELD_AFTER_ACTIVATION';request['nonce']='nonce:continuation'
  dims=json.loads((ROOT/'manifests/total_field/w7tp_8d_adi_v2_3_canonical/CONTRACT.json').read_text())['dimensions']
  for name in ('current_state_field','current_state_field_router'):
   if name=='current_state_field':target=files['current_state_field_preimage']
   else:target=base/'router.json';write(target,{'state':'OLD_ROUTER'})
   successor=base/(name+'-next.json');write(successor,{'version':'2.3','semantics':'8_IN_1_SINGLE_DYNAMIC_STATE_FIELD','dimensions':[{'id':k,'field_en':v} for k,v in dims.items()]})
   files[name+'_preimage']=target;files[name+'_successor']=successor
  files['prior_activation_receipt']=prior
  write(files['authority_successor_receipt'],{'state':'PENDING_FOUNDER_PASSKEY_G4_ACCEPTANCE','formal':False,'acceptance_mode':'FOUNDER_PASSKEY_G4_ATOMIC','authorized_effect':g4.EFFECT,'predecessor_sha256':g4.sha(files['authority_preimage']),'successor_sha256':g4.sha(files['authority_successor'])})
  request['bindings']={k:{'ref':p.relative_to(ROOT).as_posix(),'sha256':g4.sha(p)} for k,p in files.items()}
  write(rp,request)
 def test_continuation_updates_both_fields(self):
  td,base,files,rp,ap,now=self.fixture()
  with td,patch.object(g4,'verify_authorization_passkey',return_value=object()):
   self.continuation(base,files,rp,ap,now)
   out=g4.activate(ROOT,rp,ap,base/'completion-replay',base/'completion.json',now)
   self.assertEqual(2,len(out['field_postimages']))
   for name in ('current_state_field','current_state_field_router'):
    self.assertEqual(g4.sha(files[name+'_successor']),g4.sha(files[name+'_preimage']))
 def test_continuation_postload_failure_rolls_back_all_targets(self):
  td,base,files,rp,ap,now=self.fixture()
  with td,patch.object(g4,'verify_authorization_passkey',return_value=object()):
   self.continuation(base,files,rp,ap,now)
   targets=[files[k] for k in ('canonical_pointer_preimage','authority_preimage','current_state_field_preimage','current_state_field_router_preimage')]
   before={p:p.read_bytes() for p in targets}
   with patch('tools.total_field.w7tp_v2_3_candidate_source.active_canonical_binding',side_effect=RuntimeError('postload-failure')):
    with self.assertRaisesRegex(RuntimeError,'postload-failure'):g4.activate(ROOT,rp,ap,base/'completion-replay',base/'completion.json',now)
   for p in targets:self.assertEqual(before[p],p.read_bytes())
   self.assertFalse(list((base/'completion-replay').glob('*.consumed')))
if __name__=="__main__":unittest.main()
