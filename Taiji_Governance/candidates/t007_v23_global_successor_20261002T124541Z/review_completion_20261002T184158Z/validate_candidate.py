#!/usr/bin/env python3
"""Read-only candidate evidence verifier; never emits formal approval or promotes."""
import argparse
import hashlib
import json
from pathlib import Path

def digest(data):
    return hashlib.sha256(data).hexdigest()

def checked(root, ref):
    p = Path(ref)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('UNSAFE_PATH')
    for i in range(1, len(p.parts)+1):
        if (root/Path(*p.parts[:i])).is_symlink():
            raise ValueError('SYMLINK_NOT_ALLOWED:'+ref)
    return root/p

def validate(repo, bundle):
    failures=[]
    def require(ok,code):
        if not ok: failures.append(code)
    def read(name): return json.loads((bundle/name).read_text())
    def load_ref(binding):
        p=checked(repo,binding['ref'])
        data=p.read_bytes()
        require(digest(data)==binding['sha256'],'SOURCE_HASH_DRIFT:'+binding['ref'])
        return json.loads(data) if p.suffix=='.json' else None
    manifest=read('SHA256_MANIFEST.json')
    for name,expected in manifest['files'].items():
        require(digest(checked(bundle,name).read_bytes())==expected,'CANDIDATE_HASH_DRIFT:'+name)
    c=read('GLOBAL_SUCCESSOR_CONTRACT.json')
    for binding in c['source_bindings']: load_ref(binding)
    old_manifest=load_ref(c['source_bindings'][-1])
    oldroot=checked(repo,c['extends']['ref']).parent
    for name,v in old_manifest['files'].items():
        data=checked(oldroot,name).read_bytes()
        require(digest(data)==v['sha256'] and len(data)==v['bytes'],'PRIOR_CANDIDATE_DRIFT:'+name)
    previous_contract=load_ref(c['extends'])
    p=load_ref(c['predecessor_pointer'])
    require(p['version']=='2.1' and p['state']=='ACTIVE_CANONICAL','PREDECESSOR_NOT_ACTIVE_V21')
    require(c['version_transition']=={'from':'2.1','to':'2.3','mode':'APPEND_ONLY_SUCCESSOR'},'BAD_SUCCESSION')
    require(c['state']=='CANDIDATE_ONLY' and not any(c['non_effects'].values()),'AUTHORITY_ESCALATION')
    require(c['promotion_plan']['enabled'] is False,'PROMOTION_MUST_BE_DISABLED')
    require(c['dimension_contract']==previous_contract['proposed_successor']['dimension_contract'],'DEFINITION_DRIFT')
    f=load_ref(c['field_successor'])
    predecessor=load_ref(f['predecessors'][0])
    load_ref(f['predecessors'][1])
    require(f['scope']==predecessor['scope'],'ROUTER_SCOPE_LOST')
    require(f['nodes']==predecessor['nodes'],'INVENTORY_LOST_OR_INVENTED')
    require(f['safety_flags']==predecessor['safety_flags'],'SAFETY_SCOPE_CHANGED')
    dims={d['id']:d['field_en'] for d in f['dimensions']}
    require(len(f['dimensions'])==8 and dims=={f'D{i}':c['dimension_contract'][f'D{i}'] for i in range(1,9)},'DIMENSION_MAPPING_DRIFT')
    require(f['activation'] is False and f['state']=='CANDIDATE_NOT_ACTIVE','FIELD_AUTO_ACTIVATED')
    r=load_ref(c['authority_successor_receipt'])
    a0=load_ref(r['predecessor']); a1=load_ref(r['successor']); d8=load_ref(r['gst_d8_binding'])
    require(r['predecessor']['sha256']==d8['authority_pointer_sha256'],'D8_AUTHORITY_PARENT_MISMATCH')
    require(set(a0['allowed_effects'])<=set(a1['allowed_effects']),'AUTHORITY_EFFECT_REMOVED')
    require(d8['required_effect'] in a1['allowed_effects'],'GST_EFFECT_LOST')
    require({k:v for k,v in a0.items() if k!='allowed_effects'}=={k:v for k,v in a1.items() if k!='allowed_effects'},'NON_EFFECT_AUTHORITY_DRIFT')
    require(r['preserved_effects']==sorted(set(a0['allowed_effects'])),'PRESERVATION_CLAIM_WRONG')
    require(r['added_effects']==sorted(set(a1['allowed_effects'])-set(a0['allowed_effects'])) and r['removed_effects']==[],'EFFECT_DIFF_WRONG')
    require(r['formal'] is False and r['formal_acceptance_ref'] is None,'FORGED_FORMAL_RECEIPT')
    require(d8['canonical_pointer_changed'] is False and d8['scope_boundary']=='DOES_NOT_PROMOTE_GLOBAL_CANONICAL_OR_SECOND_TOTAL_FIELD','GST_GLOBAL_SCOPE_ESCALATION')
    for key in ('active_binding','consumer','contract','activation_record','activation_result'):
        load_ref({'ref':d8[key+'_ref'],'sha256':d8[key+'_sha256']})
    require(c['review_owner']['implemented_by_this_package'] is False,'UNIMPLEMENTED_REVIEW_OWNER_CLAIM')
    return {'state':'FAIL_CANDIDATE' if failures else 'PASS_CANDIDATE_STATIC_EVIDENCE',
            'failures':failures,'total_field_decision':'NOT_RUN','global_canonical_promotion':'HOLD',
            'dynamic_context':c['dynamic_context'],'consumer_runtime_validation':'NOT_RUN'}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--bundle',type=Path,default=Path(__file__).resolve().parent)
    a=p.parse_args()
    try: result=validate(a.repo.resolve(),a.bundle.resolve())
    except (OSError,ValueError,KeyError,TypeError) as e:
        result={'state':'HOLD_INPUT_MISSING_OR_INVALID','reason':str(e),'total_field_decision':'NOT_RUN','global_canonical_promotion':'HOLD'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['state']=='PASS_CANDIDATE_STATIC_EVIDENCE' else 2)
