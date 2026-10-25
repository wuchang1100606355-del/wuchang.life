from pathlib import Path
import json,hashlib,sys,copy,importlib.util

CANON='manifests/total_field/w7tp_8d_adi_v2_3_canonical/CONTRACT.json'
CH='e3c5439657bb4cb97f466ea096d20f8e68ca60307286f01f9c66da0eb120dd2c'
AH='3e13ab045925a08ff6c58277b7cf206e413a26580717516f7cfaf4ce7bdad871'
def sha(b):return hashlib.sha256(b).hexdigest()
def checks(m,c):
 e=[]
 def require(b,s):
  if not b:e.append(s)
 require(m['evidence_and_hashes']['canonical_refs']==[CANON],'CANONICAL_V23_REQUIRED')
 require(c['state']=='CANDIDATE_ONLY','CANDIDATE_ONLY_REQUIRED')
 require(c['design']['canonical_ref']==CANON and c['design']['canonical_sha256']==CH,'CANONICAL_BINDING_DRIFT')
 require(c['design']['observed_authority_sha256']==AH,'AUTHORITY_OBSERVATION_DRIFT')
 require(c['design']['authority_binding_role']=='OBSERVATION_NOT_AUTHORIZATION','HASH_IS_NOT_AUTHORIZATION')
 require(c['design']['semantics']=='8_IN_1_SINGLE_DYNAMIC_STATE_FIELD','8D_SEMANTICS_DRIFT')
 t=c['trust_seal'];a=c['ram_audio'];n=c['node_roles']
 require(t['effect_authorization'] is False and t['current_d8_required_for_effect'] is True,'TRUST_SEAL_NOT_D8')
 require(t['first_issue_requires']=='BYTE_EXACT_RECONSTRUCTION_EVIDENCE','FIRST_SEAL_BYTE_EXACT_REQUIRED')
 require(set(t['reuse_requires'])=={'same_reconstruction_key','packet_hash','rule_and_renderer_hash','lut_hash','base_material_hashes','current_target_digest_match'},'RECONSTRUCTION_KEY_DEPENDENCY_CLOSURE')
 require(set(t['retained_checks'])=={'integrity','identity','envelope','current_authority_for_effect','target_digest'},'VERIFICATION_ELIMINATION_FORBIDDEN')
 require(t['untrusted_evidence_cannot_issue_trusted_seal'] is True,'EVIDENCE_AUTHENTICITY_REQUIRED')
 require(a['generated_wav_disk_writes_allowed'] is False and a['buffer']=='io.BytesIO','GENERATED_WAV_RAM_ONLY')
 require(a['preexisting_voice_file_reads'] is True and a['code_and_lut_file_reads'] is True,'PRECONDITION_IO_COST_DISCLOSURE')
 require(a['zero_disk_scope']=='GENERATED_AUDIO_OUTPUT_ONLY_NOT_TOTAL_DISK_IO','ZERO_TOTAL_DISK_IO_UNPROVEN')
 require(a['scene_cell_example_bytes']==575 and a['scene_cell_size_is_global_invariant'] is False,'SCENE_SIZE_SCOPE')
 require(a['cross_platform_byte_exact']=='UNKNOWN_UNVERIFIED','CROSS_PLATFORM_NOT_PROVEN')
 require(a['numeric_contract_required_for_float_dsp'] is True,'FLOAT_DSP_CONTRACT_REQUIRED')
 require(n['02']['resolved_device_ref']=='UNKNOWN_UNVERIFIED','02_IDENTITY_MUST_NOT_BE_INVENTED')
 require(n['taiji03']['authority']=='REQUIRES_MEMBER_SEAT_PROFILE_AND_CURRENT_D8','ROLE_NOT_AUTHORITY')
 require(n['taiji01']['device_ref']=='HOME_POD_LAN_AUDIO_NODE_OFFICE_01' and n['taiji01']['d8_allow_required'] is True,'EXISTING_CONTROLLED_ROUTE_REQUIRED')
 require(m['manifest_state']=='CANDIDATE_FOR_TOTAL_FIELD_REVIEW' and m['lifecycle']['total_field_decision_ref'] is None,'SELF_PROMOTION_FORBIDDEN')
 return e
def main():
 root=Path(sys.argv[1]).resolve();skills=root/'skills';errs=[];results=[]
 validator=skills/'govern-total-field-skills/scripts/validate_skill_manifest.py'
 spec=importlib.util.spec_from_file_location('existing_validator',validator);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
 try:import jsonschema;schema_status='JSONSCHEMA_EXECUTED'
 except ImportError:schema_status='NOT_RUN_JSONSCHEMA_UNAVAILABLE';errs.append(schema_status)
 for p in sorted(skills.glob('*/total-field-skill-manifest.json')):
  m=json.loads(p.read_text());c=json.loads((p.parent/'references/evolution-contract.json').read_text());r=v.validate_document(m,manifest_path=p)
  es=r['errors']+checks(m,c)
  design=json.loads((p.parent/'references/current-design-contract.json').read_text())
  if design['canonical_ref']!=CANON or design['canonical_sha256']!=CH:es.append('DESIGN_ROOT_DRIFT')
  results.append({'skill_id':m['skill_id'],'version':m['version'],'maximum_effect_class':m['classification']['maximum_effect_class'],'manifest_sha256':sha(p.read_bytes()),'errors':es,'static_definition_only':True})
  errs.extend(es)
 if len(results)!=6:errs.append('EXACTLY_SIX_NONEMPTY_MANIFESTS_REQUIRED')
 # Fresh mutated candidate inputs: every mutation must be rejected by the same gates.
 p=next(skills.glob('*/total-field-skill-manifest.json'));m=json.loads(p.read_text());c=json.loads((p.parent/'references/evolution-contract.json').read_text())
 mutations=[('trust_authorization',lambda x:x['trust_seal'].update(effect_authorization=True)),('skip_integrity',lambda x:x['trust_seal'].update(retained_checks=['target_digest'])),('wav_write',lambda x:x['ram_audio'].update(generated_wav_disk_writes_allowed=True)),('zero_total_io',lambda x:x['ram_audio'].update(zero_disk_scope='ALL_IO_ELIMINATED')),('fixed_575',lambda x:x['ram_audio'].update(scene_cell_size_is_global_invariant=True)),('invent_02',lambda x:x['node_roles']['02'].update(resolved_device_ref='MSI')),('unproven_cross_platform',lambda x:x['ram_audio'].update(cross_platform_byte_exact=True)),('authority_hash_grants',lambda x:x['design'].update(authority_binding_role='AUTHORIZATION')),('no_base_hash',lambda x:x['trust_seal'].update(reuse_requires=['same_reconstruction_key'])),('canonical_drift',lambda x:x['design'].update(canonical_sha256='0'*64))]
 attacks=[]
 for name,mut in mutations:
  x=copy.deepcopy(c);mut(x);es=checks(m,x);attacks.append({'case':name,'rejected':bool(es),'errors':es})
  if not es:errs.append('ADVERSARIAL_NOT_REJECTED:'+name)
 legacy=copy.deepcopy(m);legacy['evidence_and_hashes']['canonical_refs']=['docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1.md']
 es=checks(legacy,c);attacks.append({'case':'legacy_v21_current_ref','rejected':bool(es),'errors':es})
 if not es:errs.append('LEGACY_NOT_REJECTED')
 out={'state':'PASS_V23_CANDIDATE_BUNDLE' if not errs else 'HOLD_V23_CANDIDATE_BUNDLE','manifest_count':len(results),'passed':sum(not r['errors'] for r in results),'failed':sum(bool(r['errors']) for r in results),'schema_status':schema_status,'adversarial_cases':attacks,'results':results,'errors':errs,'runtime_audio_test':'NOT_RUN_REUSES_REFERENCED_HISTORICAL_EVIDENCE','authority_decision':'NOT_REVIEWED','effect_authorization':False,'cloud_sync':'NOT_PERFORMED'}
 print(json.dumps(out,ensure_ascii=False,indent=2));return bool(errs)
if __name__=='__main__':sys.exit(main())
