#!/usr/bin/env python3
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'capability_manifest.json').read_text(encoding='utf-8'))
assert m['status']=='IMPLEMENTATION_CANDIDATE'
assert m['canonical_promotion'] is False
assert m['source']['source_runtime_authority']=='NONE'
assert m['target']['native_runtime'].startswith('native_claw')
assert m['target']['direct_ip_port_client_path'] is False
tools=m['tool_contracts']
names=[x['source_tool'] for x in tools]
assert len(names)==29, len(names)
assert len(names)==len(set(names))
assert next(x for x in tools if x['source_tool']=='start_process')['class']=='DYNAMIC_EFFECT'
assert next(x for x in tools if x['source_tool']=='shutdown')['d8_required'] is True
assert next(x for x in tools if x['source_tool']=='read_file')['d8_required'] is False
assert m['command_cache']['cache_is_authority'] is False
assert 'D8_TOKEN' in m['command_cache']['never_store']
assert m['cloud_completion']['output_state']=='HYPOTHESIS_OR_CANDIDATE_ONLY'
assert 'COMPATIBILITY_TRANSPORT != CANONICAL_RUNTIME' in m['redteam_invariants']
s=json.loads((ROOT/'schemas'/'effect_envelope.schema.json').read_text(encoding='utf-8'))
assert 'authority_ref' in s['required']
assert 'idempotency_key' in s['required']
print('PASS_RDC_8D_ADI_EQUIVALENT_CAPABILITY_ORGAN_CANDIDATE')
