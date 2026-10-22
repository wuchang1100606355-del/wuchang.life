import sys,importlib.util,json,unittest,subprocess,tempfile,hashlib,io
from pathlib import Path
from unittest.mock import patch
R=Path("/home/taiji_admin/Taiji_Hub");sys.path.insert(0,str(R))
W=R/"artifacts/8d-adi-workloop/v11-verification-restart-20261019T0556Z"
spec=importlib.util.spec_from_file_location("tools.total_field.w7tp_d8_reviewer_entrypoint",W/"candidate/w7tp_d8_reviewer_entrypoint_evidence_intake.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sys.modules[spec.name]=m
import tools.total_field
tools.total_field.w7tp_d8_reviewer_entrypoint=m
m.ROOT=R
# Original tests derive schema/layout and executable bits from module.__file__.
# Candidate functions run against the actual installation coordinate, without changing source.
m.__file__=str(R/'tools/total_field/w7tp_d8_reviewer_entrypoint.py')
result=json.loads(subprocess.check_output(["/home/taiji_admin/.local/share/w7tp-passkey-d8/venv/bin/python","-B",str(W/"resume_existing_v11.py")],text=True))
class V11IntakeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=W/"evidence")
  self.out=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def call(self,data=None):
  response=subprocess.CompletedProcess([],0,json.dumps(data or result),"")
  with patch("subprocess.run",return_value=response):
   return m.receive_v11_evidence(repo_root=R,output_dir=self.out)
 def test_real_verified_result_received_only(self):
  r=self.call();self.assertEqual(r["state"],"RECEIVED_AS_EVIDENCE_ONLY");self.assertFalse(r["formal_d8_request_received"]);self.assertIsNone(r["formal_d8_request_id"]);self.assertFalse(r["D8_EFFECT_AUTHORIZED"]);self.assertFalse(r["D4_ISSUED"])
 def test_replay_idempotent(self):
  a=self.call();b=self.call();self.assertEqual(a,b)
 def test_wrong_root(self):
  with self.assertRaises(m.D8ReviewError):m.receive_v11_evidence(repo_root=Path("/tmp"),output_dir=self.out)
 def test_output_escape(self):
  with self.assertRaises(m.D8ReviewError):m.receive_v11_evidence(repo_root=R,output_dir=W/"../../../../escape")
 def test_output_symlink(self):
  link=self.out/"link";link.symlink_to(W/"evidence",target_is_directory=True)
  with self.assertRaises(m.D8ReviewError):m.receive_v11_evidence(repo_root=R,output_dir=link/"x")
 def test_fake_authority(self):
  d=dict(result,D8_EFFECT_AUTHORIZED=True)
  with self.assertRaises(m.D8ReviewError):self.call(d)
 def test_unsigned(self):
  with self.assertRaises(m.D8ReviewError):self.call(dict(result,original_signature_crypto_verified_now=False))
 def test_new_challenge_forbidden(self):
  with self.assertRaises(m.D8ReviewError):self.call(dict(result,new_challenge=True))
 def test_hash_drift(self):
  with self.assertRaises(m.D8ReviewError):self.call(dict(result,handoff_sha256="0"*64))
 def test_bad_response(self):
  with patch("subprocess.run",return_value=subprocess.CompletedProcess([],0,"broken","")):
   with self.assertRaises(m.D8ReviewError):m.receive_v11_evidence(repo_root=R,output_dir=self.out)
 def test_existing_receipt_cannot_be_overwritten(self):
  target=self.out/"V11_EVIDENCE_INTAKE_RECEIPT.json";target.write_bytes(b"original\n")
  with self.assertRaises(m.D8ReviewError):self.call()
  self.assertEqual(target.read_bytes(),b"original\n")
 def test_supported_authority_decisions_unchanged(self):
  self.assertEqual(set(m.SUPPORTED_REQUESTED_DECISIONS),{"ALLOW_P2_ISOLATED_CANARY_EXECUTION_ONLY","ALLOW_NO_NETWORK_OFFLINE_CANARY_IMAGE_BUILD_ONLY"})
from tests.test_w7tp_d8_reviewer_entrypoint import D8ReviewerEntrypointTests
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(V11IntakeTests),unittest.defaultTestLoader.loadTestsFromTestCase(D8ReviewerEntrypointTests)])
stream=io.StringIO()
import contextlib
with contextlib.redirect_stdout(io.StringIO()):
 r=unittest.TextTestRunner(stream=stream,verbosity=1).run(suite)
(W/"evidence/intake-tests-layout-corrected.txt").write_text(stream.getvalue())
report={"state":"PASS" if r.wasSuccessful() else "FAIL","run":r.testsRun,"failures":len(r.failures),"errors":len(r.errors),"new_cases":12,"original_cases":r.testsRun-12,"source_sha256":hashlib.sha256((W/"candidate/w7tp_d8_reviewer_entrypoint_evidence_intake.py").read_bytes()).hexdigest()}
(W/"evidence/intake-tests-layout-corrected.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
if not r.wasSuccessful():print(stream.getvalue())
raise SystemExit(0 if r.wasSuccessful() else 2)
