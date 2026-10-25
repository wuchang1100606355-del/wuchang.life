from pathlib import Path
import json,hashlib,copy,shutil,subprocess,sys,re,datetime,importlib.util,tarfile

RUN=Path(__file__).resolve().parents[1]
MATERIAL=Path(__file__).resolve().parent
REPO=Path('/home/taiji_admin/Taiji_Hub')
SKILLS=RUN/'skills'; E=RUN/'evidence'
NOW=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
CANON='manifests/total_field/w7tp_8d_adi_v2_3_canonical/CONTRACT.json'
CANON_HASH='e3c5439657bb4cb97f466ea096d20f8e68ca60307286f01f9c66da0eb120dd2c'
AUTH='runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json'
AUTH_HASH='3e13ab045925a08ff6c58277b7cf206e413a26580717516f7cfaf4ce7bdad871'
OLD='docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1.md'
AUDIO='artifacts/8d-adi-workloop/origin-cell-verified-reconstruction-candidate-20261023T233100Z8'
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
def load(p):return json.loads(p.read_text())
def cmd(args):
 r=subprocess.run(args,cwd=REPO,text=True,capture_output=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'});return {'command':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
def event(kind,summary,ref='order.md',label='CANDIDATE',status='CLOSED'):
 p=RUN/'decisions.jsonl'; seq=len(p.read_text().splitlines())+1
 d={'event_id':f'evt-{seq:04d}','logical_time':NOW,'event_type':kind,'status':status,'evidence_label':label,'observation_status':'DERIVED_FROM_OBSERVED' if label=='FACT' else 'DECLARED_ONLY','source_ref':ref,'source_sha256':sha((RUN/ref).read_bytes()) if (RUN/ref).is_file() else 'NONE','summary':summary,'authority_state':'CANDIDATE_FOR_TOTAL_FIELD_REVIEW','supersedes':[]}
 with p.open('a') as f:f.write(json.dumps(d,ensure_ascii=False)+'\n')
 return d['event_id']
assert sha((REPO/CANON).read_bytes())==CANON_HASH,'CANONICAL_DRIFT'
assert sha((REPO/AUTH).read_bytes())==AUTH_HASH,'AUTHORITY_DRIFT'
branch=cmd(['git','branch','--show-current'])['stdout'].strip();head=cmd(['git','rev-parse','HEAD'])['stdout'].strip()
assert head=='3594b4e8292d537ff8d111e44c70c4fc6f177b39','HEAD_DRIFT'
tracked=cmd(['git','diff','--name-only'])['stdout'].splitlines()
protected={n:sha((REPO/n).read_bytes()) for n in tracked if (REPO/n).is_file()}
for n in [CANON,AUTH,'runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json','runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_CANONICAL.json']:
 protected[n]=sha((REPO/n).read_bytes())
dump(E/'protected-preimage.json',protected)
snapshot={'node':'taiji01','root':str(REPO),'branch':branch,'head':head,'observed_at':NOW,'mode':'CANDIDATE_ONLY','canonical_ref':CANON,'canonical_sha256':CANON_HASH,'authority_ref':AUTH,'authority_sha256':AUTH_HASH,'authority_tracked_dirty':AUTH in tracked,'formal_authority_verification':'NOT_COMPLETED_CURRENT_RECEIPT_CHAIN_REQUIRED','existing_changes_preserved':True}
dump(E/'coordinate.json',snapshot)
sources=[]
names=[d.name for d in sorted((MATERIAL/'baseline').iterdir())]
for name in names:
 hits=[]
 for base in [REPO/'.skill-build',Path('/home/taiji_admin/.codex/skills'),REPO/'runtime/isolated/govern_total_field_skills_v2_2_0_source_candidate_20260802T165359Z']:
  p=base/name/'SKILL.md'
  if p.is_file():
   body=p.read_text();hits.append({'path':str(p),'sha256':sha(p.read_bytes()),'legacy_v21_current_ref':OLD in body,'classification':'OBSERVED_FILE_NOT_PROOF_LOADED'})
 sources.append({'name':name,'bounded_roots_only':True,'local_matches':hits,'not_found_means':'NOT_FOUND_IN_SEARCHED_LOCATIONS_NOT_GLOBAL_ABSENCE'})
dump(E/'taiji01-source-inventory.json',sources)
audio_evidence={}
for n in ['EVIDENCE.json','audio_scene_lab/MSI_ZERO_DISK_EVIDENCE.json','audio_scene_lab/TRUST_BRIDGE_RUN.json','audio_scene_lab/AUDIO_SCENE_FAST_PATH_RESULT.json','audio_scene_lab/EMOTION_LUT_V23_CANDIDATE.json','audio_scene_lab/run_emotion_lut.py','audio_scene_lab/audio_scene_trust_bridge.py','candidate/origin_cell_verified_reconstruction.py']:
 p=REPO/AUDIO/n;b=p.read_bytes();audio_evidence[n]={'path':str(p.relative_to(REPO)),'sha256':sha(b),'evidence_class':'OBSERVED_CURRENT_ARTIFACT_HISTORICAL_EXECUTION_NOT_RERUN'}
 if p.suffix=='.json':dump(E/'audio'/p.name,json.loads(b))
dump(E/'audio-source-bindings.json',audio_evidence)
routes={}
for n in ['ACTIVE_HOMEPOD_BINDING.json','ACTIVE_HOMEPOD_PLAYBACK_ROUTE.json']:
 p=REPO/'runtime/total_field/device_registry/hom_epod'/n;d=load(p)
 routes[n]={'ref':str(p.relative_to(REPO)),'sha256':sha(p.read_bytes()),'declared_state':d.get('route_state',d.get('binding_state')),'bridge_node_ref':d.get('bridge_node_ref'),'device_ref':d.get('device_ref'),'port':d.get('raop_port'),'tested_at':d.get('tested_at'),'current_playback_test':'NOT_RUN','d8_required':d.get('d8_allow_required',d.get('governance',{}).get('d8_allow_required'))}
dump(E/'node-route-evidence.json',routes)
accepts={'AC-1':'六大技能候選與清單完整、舊原件不覆寫','AC-2':'現行 V2.3 契約綁定與六份清單驗證零失敗','AC-3':'三項能力契約與負向邊界測試完成','AC-4':'來源差異、未驗證節點與正式權威缺口如實交接','AC-5':'既有變更、正典、服務與 Git 狀態保護驗證'}
order=f'''# 8D ADI Order: 六大技能 V2.3 隔離升級候選

Run-ID: {RUN.name}
Lifecycle: CANDIDATE_FOR_TOTAL_FIELD_REVIEW
Frozen: {NOW}
Owner-ref: Founder current user instruction; Seat UNKNOWN_UNVERIFIED
Effect-class: E2

## D1 Intent
沿既有來源建立六大技能升級候選及驗證器，不更新現用技能與正式系統。

## Verified facts
- [FACT|OBSERVED_DIRECT] taiji01 V2.3 contract hash matched | source: evidence/coordinate.json | hash: {sha((E/'coordinate.json').read_bytes())}
- [FACT|OBSERVED_DIRECT] audio candidate records located; execution not rerun | source: evidence/audio-source-bindings.json | hash: {sha((E/'audio-source-bindings.json').read_bytes())}

## Materials
- Allowed: user-owned skill text and deidentified project code | licence: USER_AUTHORIZED_CANDIDATE_USE_ONLY | checked: {NOW}
- Excluded: credentials, member plaintext, private selectors, sound playback

## Build specification
- canonical_ref = {CANON} | source: live canonical pointer
- canonical_sha256 = {CANON_HASH}
- authority_sha256 = {AUTH_HASH} | observed binding only; no new effect grant
- cloud SKILL.md plus explicitly identified executor resources; no claim of cloud-resource equality
- derive six candidate definitions and add shared evolution contract; preserve existing effect-class ceilings

## Budget fuse
- Limit: 2 attempt
- Stop condition: stop on two failed candidate validation attempts or protected-source drift

## Acceptance
'''+''.join(f'- [ ] {k}: {v} | evidence: evidence/acceptance.json\n' for k,v in accepts.items())+'''
## Non-goals
- no deployment, service restart, audio output, identity/Seat mutation, canonical writes, Git commit/push or cloud skill installation

## D2-D8 projection
- D2 STATE: six source versions become new candidates; runtime unverified
- D3 COORDINATE: taiji01, exact branch/HEAD and source refs in evidence/coordinate.json
- D4 EVIDENCE: historical records, current artifact hashes and validators kept distinct
- D5 EXECUTION_POLICY: new candidate directory only; rollback by retiring this unpromoted directory
- D6 GENERATIVE_TRANSMISSION: NOT_CLAIMED for this package transport; existing reconstruction protocol reused by reference
- D7 RED_TEAM_RISK_CONFINEMENT: reject authority inflation, zero-total-I/O and total-verification-elimination claims
- D8 ENVELOPE_AUTHORITY: CANDIDATE_ONLY; receipt NOT_REVIEWED; no Seat invented
'''
(RUN/'order.md').write_text(order)
event('ORDER_FROZEN','Freeze exact candidate-only scope, acceptance and source coordinates')
pre=event('DECISION','RED_TEAM_PRE_DEFINITION: source version ambiguity mitigated by provenance; runtime claims withheld','evidence/taiji01-source-inventory.json','FACT')
shared={
 'schema_version':'w7tp-six-skills-v23-evolution-candidate/1.0','state':'CANDIDATE_ONLY',
 'design':{'canonical_ref':CANON,'canonical_sha256':CANON_HASH,'observed_authority_sha256':AUTH_HASH,'authority_binding_role':'OBSERVATION_NOT_AUTHORIZATION','semantics':'8_IN_1_SINGLE_DYNAMIC_STATE_FIELD'},
 'trust_seal':{'effect_authorization':False,'current_d8_required_for_effect':True,'first_issue_requires':'BYTE_EXACT_RECONSTRUCTION_EVIDENCE','reuse_requires':['same_reconstruction_key','packet_hash','rule_and_renderer_hash','lut_hash','base_material_hashes','current_target_digest_match'],'retained_checks':['integrity','identity','envelope','current_authority_for_effect','target_digest'],'skipped_operation':'REPEATED_MODEL_INFERENCE_ONLY_WHEN_NOT_REQUIRED_BY_PINNED_RULE','seal_authenticity':'CANDIDATE_HASH_RECORD_NOT_INDEPENDENT_SIGNATURE','untrusted_evidence_cannot_issue_trusted_seal':True,'evidence_ref':AUDIO+'/audio_scene_lab/TRUST_BRIDGE_RUN.json'},
 'ram_audio':{'effect_authorization':False,'model_output':['semantic_slots','emotion_code'],'mapping':'VERSIONED_DETERMINISTIC_LUT','buffer':'io.BytesIO','generated_wav_disk_writes_allowed':False,'preexisting_voice_file_reads':True,'code_and_lut_file_reads':True,'zero_disk_scope':'GENERATED_AUDIO_OUTPUT_ONLY_NOT_TOTAL_DISK_IO','scene_cell_example_bytes':575,'scene_cell_size_is_global_invariant':False,'model_zero_acoustic_guessing_is':'DESIGN_BOUNDARY_NOT_END_TO_END_MEASURED_CLAIM','numeric_contract_required_for_float_dsp':True,'cross_platform_byte_exact':'UNKNOWN_UNVERIFIED','runtime_dependency_versions_in_key':'REQUIRED_BEFORE_CROSS_RUNTIME_REUSE'},
 'node_roles':{'taiji03':{'role':'ORGANIZATION_CONTROL_AND_CELL_ISSUANCE_CANDIDATE','authority':'REQUIRES_MEMBER_SEAT_PROFILE_AND_CURRENT_D8','observation_status':'DECLARED_ONLY'},'02':{'role':'AI_AUDIOVISUAL_RAM_RECONSTRUCTION_AND_PROJECTION_CANDIDATE','resolved_device_ref':'UNKNOWN_UNVERIFIED','observation_status':'DECLARED_ONLY'},'taiji01':{'role':'EXISTING_TOTAL_FIELD_HOMEPOD_ROUTER','device_ref':'HOME_POD_LAN_AUDIO_NODE_OFFICE_01','endpoint':'192.168.50.101:7000','endpoint_status':'FOUNDER_DECLARED_CURRENT_REACHABILITY_NOT_TESTED','route_ref':'runtime/total_field/device_registry/hom_epod/ACTIVE_HOMEPOD_PLAYBACK_ROUTE.json','d8_allow_required':True,'playback':'NOT_RUN'},'stacking_cells_does_not_increase_authority':True},
 'forbidden_promotions':['TRUST_SEAL_TO_D8','FILE_EXISTS_TO_LOADED','CANDIDATE_TO_ACTIVE','REGISTERED_TO_RUNNING','HISTORICAL_TEST_TO_CURRENT_EFFECT','HASH_MATCH_TO_AUTHORITY','CACHE_TO_ALL_VERIFICATION_ELIMINATION'],
 'provenance':{'audio_records':'OBSERVED_CURRENT_FILE_CONTAINING_HISTORICAL_MSI_RESULT','formal_authority':'NOT_REVIEWED','cloud_resources':'NOT_RETRIEVED_EXECUTOR_RESOURCE_BASELINE_EXPLICIT'}}
dump(RUN/'shared/evolution-contract.json',shared)
clause='''## V2.3 六大技能共用升級條款（隔離候選）

依 taiji01 活躍指標解析現行 V2.3 契約並核對 SHA-256；引用本次快照，不把快照當授權。八維為八合一單一動態狀態場；D5 執行／政策與 D8 封套／權威分離。身分與角色席位約束整個封套。

重用已驗證重構信任標章時，首次須有逐位元組一致證據，重用須核對 reconstruction_key、封包、規則、LUT、基底及結果摘要；effect_authorization 永遠為 false。快路徑可省去不必要的重複模型推理，不能取消完整性、身分、封套或當次效果授權。

模型只提供語義槽位與 emotion_code；音訊參數由版本化 LUT 決定。生成音訊使用 CPU 記憶體 io.BytesIO 完成合成與 SHA-256，不寫出暫存 WAV。既有語音基底、程式與 LUT 的讀取成本須揭露；575 位元組只是一個已記錄範例，非所有原胞固定大小。浮點聲學運算須另列數值與重播契約，跨平台位元組一致性未驗不得宣稱。

依創辦人指定分工建立候選：03 管秩序及原胞發行、02 負責影音重構投射、taiji01 沿既有 HomePod 受控路由。02 身分與各節點當前授權未核對前，維持候選；不得由角色名稱取得超管權。

只產生候選、證據與有界交接；未取得精確總場收據，不部署、不改正典、不變更席位、不自授 D8。文字更新不等於已載入、運行或效果驗收。
'''
(RUN/'shared/paste-back-v23.md').write_text(clause)
design={'schema':'w7tp-current-design-source-candidate/1.0','version':'2.3','canonical_ref':CANON,'canonical_sha256':CANON_HASH,'authority_ref':AUTH,'observed_authority_sha256':AUTH_HASH,'authority_verified':False,'source':'TAIJI01_OBSERVED_CONTRACT_AND_FOUNDER_CURRENT_INSTRUCTION','state':'CANDIDATE_ONLY','old_versions':'HISTORICAL_REFERENCE_ONLY'}
template=load(MATERIAL/'baseline/govern-total-field-skills/total-field-skill-manifest.json')
roles={
 'govern-total-field-skills':('總場技能治理','版本、效果分級與三項能力契約稽核；不簽發正式權威'),
 'govern-8d-adi-evidence-workloop':('8D ADI 證據工作迴圈','凍結升級意圖、追蹤證據與保留更正沿革'),
 'audit-technology-identity':('8D 技術身分閘門','精確區分省推理、保留驗證、輸出零落盤的主張範圍'),
 'integrated-engineering-delivery':('整合式工程交付','依實機與最小差異產生候選交付，執行範圍仍按次授權'),
 'govern-8d-adi-git-index':('8D ADI Git 重構索引','綁定六技能版本與來源物件；本輪不建立提交與推送義務'),
 'trace-file-8d-adi-causality':('8D ADI 檔案意圖場重構','從有界來源內容追蹤輸入、規則與結果；不由名稱推定因果')}
source_deltas=[]
for name in names:
 src=MATERIAL/'baseline'/name;dst=SKILLS/name
 shutil.copytree(src,dst)
 (dst/'SKILL.md').write_text((MATERIAL/'cloud'/name/'SKILL.md').read_text()+'\n\n'+clause+'\n完整機讀候選契約：`references/evolution-contract.json`。本技能作用：'+roles[name][1]+'。\n')
 for p in sorted(dst.rglob('*')):
  if p.is_file() and p.suffix in {'.md','.json','.py','.yaml','.yml'}:
   text=p.read_text();new=text.replace(OLD,CANON)
   if p.suffix=='.md':new=new.replace('V2.1 locks','V2.3 locks').replace('Canonical V2.1 locks','Canonical V2.3 locks').replace('Apply the V2.1 locks','Apply the V2.3 locks')
   if new!=text:p.write_text(new);source_deltas.append({'file':str(p.relative_to(RUN)),'change':'CURRENT_CONTRACT_REF_V21_TO_V23_HISTORY_NOT_DELETED'})
 refs=dst/'references';refs.mkdir(exist_ok=True)
 dump(refs/'current-design-contract.json',design)
 dump(refs/'evolution-contract.json',shared)
 (refs/'version-observation-causality.md').write_text('''# V2.3 候選版本與因果紀律
現行設計依 current-design-contract.json 綁定 taiji01 契約。舊版只作歷史；當次觀測、歷史執行與候選要求分列。修改來源、規則、LUT、基底或相依執行環境後重驗受影響結論；不得由雜湊、名稱或時間推定因果或權威。依附實際節點、物件、版本與觀測時間。
''')
 (refs/'capability-interoperability.md').write_text('# 候選能力重用契約\n沿既有提供者、節點、輸入輸出與精確授權重用。檔案存在、工具曝光、可連線、已執行與效果驗收分開記錄；本包不啟用遠端能力。\n')
 dump(refs/'capability-source-index.json',{'state':'CANDIDATE_ONLY','sources':audio_evidence,'routes':routes,'unresolved':['02 device identity','active Seat/profile','current exact D8 receipt','cross-platform audio replay']})
 manifest=dst/'total-field-skill-manifest.json'
 if manifest.exists():d=load(manifest);origin_version=d['version'];v=list(map(int,origin_version.split('.')));v[-1]+=1;d['version']='.'.join(map(str,v))
 else:
  d=copy.deepcopy(template);origin_version='NONE';d['skill_id']='w7tp.integrated-engineering-delivery';d['version']='1.0.0';d['display_name_zh']=roles[name][0]
  d['classification']={'primary_family':'F18','secondary_families':['F10','F15','F17','F20'],'maximum_effect_class':'E5'}
  d['product_output_contract'].update({'intended_users':['Founder','受授權工程維護者'],'user_need':'將自創架構意圖收斂為可逆可驗證交付','product_outcome':'在每次精確授權範圍內完成工程交付；本輪只建候選','deliverables':['現況差距證據','有界候選執行包','驗證與回滾契約'],'interface_behavior':'繁體中文結論、證據與唯一下一步','quality_thresholds':['不擅改使用者定義','不將候選視為部署','沿既有能力最小差異修正'],'acceptance_criteria':['候選完整、輸入與相依可核對','正式效果須另取得精確授權與總場收據','宣告浮點時具備浮點資料索引與數值重播契約']})
  d['execution_contract']['forbidden_effects']=[x for x in d['execution_contract']['forbidden_effects'] if x not in ['LIVE_DB_WRITE','DEPLOY','RESTART','ROUTER_WRITE']]+['UNAUTHORIZED_LIVE_EFFECTS','SELF_AUTHORITY','PROTECTED_DATA_EXPOSURE']
  d['execution_contract']['persistent_side_effects']=['VERSIONED_CANDIDATE_ARTIFACTS','EXACTLY_AUTHORIZED_ENGINEERING_CHANGES_ONLY_AFTER_SEPARATE_D8']
  d['lifecycle']['replacement_refs']=[]
 d['manifest_state']='CANDIDATE_FOR_TOTAL_FIELD_REVIEW';d['lifecycle']['state']=d['manifest_state'];d['lifecycle']['total_field_decision_ref']=None
 d['product_output_contract']['deliverables'].append('V2.3 三項能力有界候選契約與來源證據')
 d['product_output_contract']['quality_thresholds']=[x.replace('V2.1','V2.3') for x in d['product_output_contract']['quality_thresholds']]
 d['d1_d8_projection']['D6']['contract']=d['d1_d8_projection']['D6']['contract'].replace('V2.1','V2.3')
 d['evidence_and_hashes']['canonical_refs']=[CANON]
 if d['w7tp_contract'].get('claimed'):d['w7tp_contract']['canonical_ref']=CANON
 if origin_version!='NONE':d['lifecycle'].setdefault('replacement_refs',[]).append(d['skill_id']+'@'+origin_version)
 # References declare design; no invented runtime claim or canonical seal.
 d['verification_contract']['static_checks']=list(dict.fromkeys(d['verification_contract'].get('static_checks',[])+['V23_CANONICAL_HASH_BINDING','EVOLUTION_CONTRACT_BOUNDARIES','FLOAT_NUMERIC_CONTRACT_WHEN_DECLARED']))
 d['verification_contract']['evidence_required']=list(dict.fromkeys(d['verification_contract']['evidence_required']+['CURRENT_SOURCE_PROVENANCE','V23_EVOLUTION_CANDIDATE_CONTRACT']))
 d['evidence_and_hashes']['evidence_destination']='artifacts/8d-adi-workloop/'+RUN.name+'/evidence/'
 # Every included source byte is pinned; history baseline remains in source-materials.
 files=[p for p in sorted(dst.rglob('*')) if p.is_file() and p!=manifest]
 d['evidence_and_hashes']['implementation_refs']=[str(p.relative_to(dst)) for p in files]
 d['evidence_and_hashes']['implementation_sha256']={str(p.relative_to(dst)):sha(p.read_bytes()) for p in files}
 d['evidence_and_hashes']['manifest_self_hash']='PENDING_TOTAL_FIELD_SEAL'
 dump(manifest,d)
dump(E/'migration-deltas.json',source_deltas)
dump(E/'origins.json',load(MATERIAL/'origins.json'))
dump(E/'candidate-definition-provenance.json',{'integrated_engineering_manifest':'NEW_CANDIDATE_DERIVED_FROM_SCHEMA_TEMPLATE_NOT_EXISTING_REGISTERED_MANIFEST','cloud_body':'CURRENT_SKILLS_API_SOURCE','references_and_scripts':'EXECUTOR_BASELINE_EXPLICITLY_VERSIONED','runtime_equivalence':'NOT_CLAIMED','source_alignment':'V23_CURRENT_CANONICAL_REFS_ALIGNED_WITHIN_NEW_CANDIDATE_ONLY','cloud_sync':'NOT_PERFORMED','local_install':'NOT_PERFORMED'})
print(json.dumps({'state':'CANDIDATE_SOURCES_BUILT','run':str(RUN),'skills':len(names),'next':'RUN_VALIDATORS'},ensure_ascii=False))
