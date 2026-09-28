"""Regression cases from Founder conversation, 2026-09-27; no runtime effects."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tools.d8_guard_eval import evaluate_causal_claims

GOOD = {
 "FIELD_MODEL": {"model":"8_IN_1_SINGLE_STATE_FIELD"},
 "RECONSTRUCTION": {"mechanism":"RULE_RECONSTRUCTION","claim":"RECONSTRUCTION"},
 "CAPABILITY_EFFECT": {"observed":"QUEUED","claimed":"QUEUED"},
 "CURRENT_BINDING": {"evidence_scope":"CURRENT","binding_matches":True,"claims_current_ready":True},
 "RULE_TRANSFER": {"rule_body_transmitted":True,"claims_no_rules_transmitted":False},
 "COMPOSITION": {"required_dependency_failed":False,"continue_dependent_action":True,"authority_expanded_by_composition":False},
 "CAUSAL_ATTRIBUTION": {"basis":"EXPLICIT_CODE_PATH","claims_proven_cause":False},
 "EFFECT_EQUIVALENCE": {"same_task":True,"same_acceptance":True,"paired_test_observed":False,"claims_proven":False},
 "OBSERVATION_EFFECT": {"may_mutate":True,"claims_read_only":False},
}
BAD = {
 "FIELD_MODEL": {"model":"EIGHT_LINEAR_STEPS"},
 "RECONSTRUCTION": {"mechanism":"LOCAL_QUERY"},
 "CAPABILITY_EFFECT": {"claimed":"VERIFIED"},
 "CURRENT_BINDING": {"binding_matches":False},
 "RULE_TRANSFER": {"claims_no_rules_transmitted":True},
 "COMPOSITION": {"required_dependency_failed":True},
 "CAUSAL_ATTRIBUTION": {"basis":"TIME_ONLY","claims_proven_cause":True},
 "EFFECT_EQUIVALENCE": {"claims_proven":True},
 "OBSERVATION_EFFECT": {"claims_read_only":True},
}
def packet(kind="RECONSTRUCTION"):
 coord={"node_ref":"taiji03","object_ref":"service:test","state_ref":"version:1","observed_at":"2026-09-27T13:49:15+08:00"}
 return {"schema":"w7tp-causal-claims/1","claims":[{"id":"case:1","kind":kind,"coordinate":coord,
 "evidence":{"ref":"test:synthetic-not-live","coordinate":copy.deepcopy(coord)},"operands":copy.deepcopy(GOOD[kind])}]}

class CausalClaimsTests(unittest.TestCase):
 def test_valid_declarations_never_become_authority(self):
  for kind in GOOD:
   with self.subTest(kind=kind):
    result=evaluate_causal_claims(packet(kind))
    self.assertEqual(result["state"],"CANDIDATE_CONSISTENT")
    self.assertEqual(result["total_field_decision"],"NOT_RUN")
    self.assertFalse(result["evidence_authenticated"])
    self.assertFalse(result["live_effect_verified"])
 def test_nine_observed_misinterpretation_classes(self):
  for kind,changes in BAD.items():
   with self.subTest(kind=kind):
    p=packet(kind);p["claims"][0]["operands"].update(changes)
    self.assertEqual(len(evaluate_causal_claims(p)["findings"]),1)
 def test_historical_success_is_not_current_ready(self):
  p=packet("CURRENT_BINDING");p["claims"][0]["operands"]["evidence_scope"]="HISTORICAL"
  self.assertEqual(evaluate_causal_claims(p)["state"],"HOLD_CAUSAL_CLAIMS")
 def test_localized_hold_preserves_independent_work(self):
  p=packet("COMPOSITION");p["claims"][0]["operands"].update(required_dependency_failed=True,continue_dependent_action=False)
  self.assertEqual(evaluate_causal_claims(p)["findings"],[])
 def test_stacking_does_not_grant_authority(self):
  p=packet("COMPOSITION");p["claims"][0]["operands"]["authority_expanded_by_composition"]=True
  self.assertTrue(evaluate_causal_claims(p)["findings"])
 def test_malformed_inputs_fail_closed(self):
  for value in [None,[],{},{"schema":"w7tp-causal-claims/1","claims":[]}, {"schema":"w7tp-causal-claims/1","claims":[None]}]:
   self.assertEqual(evaluate_causal_claims(value)["state"],"HOLD_CAUSAL_CLAIMS")
 def test_invalid_operands_unknown_and_integer_bool_rejected(self):
  for value in [{},None,{"may_mutate":1,"claims_read_only":False},{"may_mutate":True,"claims_read_only":"UNKNOWN"}]:
   p=packet("OBSERVATION_EFFECT");p["claims"][0]["operands"]=value
   self.assertTrue(evaluate_causal_claims(p)["findings"])
 def test_evidence_coordinates_must_match(self):
  for key in ("node_ref","object_ref","state_ref","observed_at"):
   p=packet();p["claims"][0]["evidence"]["coordinate"][key]="other"
   self.assertEqual(evaluate_causal_claims(p)["findings"][0]["rule_id"],"EVIDENCE_COORDINATE_MISMATCH")
 def test_time_requires_timezone(self):
  p=packet();p["claims"][0]["coordinate"]["observed_at"]="2026-09-27T13:00:00"
  self.assertTrue(evaluate_causal_claims(p)["findings"])
 def test_duplicate_ids_and_unknown_kinds_rejected(self):
  p=packet();p["claims"].append(copy.deepcopy(p["claims"][0]))
  self.assertTrue(evaluate_causal_claims(p)["findings"])
  p=packet();p["claims"][0]["kind"]="UNKNOWN"
  self.assertTrue(evaluate_causal_claims(p)["findings"])
 def test_input_not_mutated(self):
  p=packet();before=copy.deepcopy(p);evaluate_causal_claims(p);self.assertEqual(p,before)
 def test_cli_reads_stdin_without_database_access(self):
  root=Path(__file__).resolve().parents[1]
  for text,expected in [(json.dumps(packet()),0),("{}",30),("not json",30)]:
   result=subprocess.run([sys.executable,"-B","tools/d8_guard_eval.py","--causal-claims-stdin"],input=text,text=True,capture_output=True,cwd=root)
   self.assertEqual(result.returncode,expected,result.stderr)
   self.assertFalse(json.loads(result.stdout)["writeback"])

if __name__=="__main__":
 unittest.main()
