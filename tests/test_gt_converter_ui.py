import hashlib,http.client,json,os,tempfile,threading,time,unittest
from pathlib import Path
from w7tp_runtime.gt_converter_ui import Service,Server,MAX_REQUEST_BYTES
from w7tp_runtime.gt_packet_v2 import PacketV2

UI_REDTEAM_CASES=["reject_non_local_bind","reject_invalid_host","reject_origin","reject_csrf","reject_json_hex","reject_oversize","reject_invalid_run","reject_arbitrary_download","reject_symlink_packet","hide_payload","hide_path","multipart_stream","artifact_gate","d1_d8_complete","protocol_bound","verification_bound","one_time_gateway","total_field_seal","random_input_direct_transfer","repeat_block_provider"]

class V2UITests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.service=Service(self.root);self.server=Server(("127.0.0.1",0),self.service);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.port=self.server.server_port;self.host=f"127.0.0.1:{self.port}"
 def tearDown(self):self.server.shutdown();self.server.server_close();self.service.close();self.thread.join();self.temp.cleanup()
 def request(self,method,path,body=None,headers=None):
  conn=http.client.HTTPConnection("127.0.0.1",self.port,timeout=10);base={"Host":self.host};base.update(headers or {});conn.request(method,path,body,base);response=conn.getresponse();data=response.read();status=response.status;conn.close();return status,data
 def post(self,payload,filename="fixture.bin"):
  boundary="W7TPBOUNDARY";body=(f"--{boundary}\r\nContent-Disposition: form-data; name=\"source\"; filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode()+payload+f"\r\n--{boundary}--\r\n".encode());return self.request("POST","/api/w7tp/v2/jobs",body,{"Content-Type":f"multipart/form-data; boundary={boundary}","X-CSRF-Token":self.service.csrf_token})
 def wait(self,run):
  for _ in range(200):
   status,raw=self.request("GET",f"/api/w7tp/v2/jobs/{run}");job=json.loads(raw)
   if job["state"] in {"PASS","HOLD","BLOCK","ERROR"}:return job
   time.sleep(.02)
  self.fail("timeout")
 def test_capabilities_truthful(self):
  status,raw=self.request("GET","/api/w7tp/v2/capabilities");cap=json.loads(raw);self.assertEqual(status,200)
  for key in ("packet_carries_transport_protocol","packet_carries_verification_method","one_time_gateway_supported","total_field_verifier_bound"):self.assertIs(cap[key],True)
 def test_security_headers_and_bind(self):
  with self.assertRaisesRegex(ValueError,"NON_LOCAL_BIND"):Server(("0.0.0.0",0),Service(self.root/"x"))
  self.assertEqual(self.request("GET","/health",headers={"Host":"evil"})[0],403);self.assertEqual(self.request("GET","/health",headers={"Origin":"https://evil"})[0],403)
 def test_csrf_and_json_hex_rejected(self):
  self.assertEqual(self.request("POST","/api/w7tp/v2/jobs",b"{}",{"Content-Type":"application/json"})[0],403)
  self.assertEqual(self.request("POST","/api/w7tp/v2/jobs",b'{"source_hex":"00"}',{"Content-Type":"application/json","X-CSRF-Token":self.service.csrf_token})[0],400)
 def test_oversized_and_invalid_run(self):
  self.assertEqual(self.request("POST","/api/w7tp/v2/jobs",b"x",{"Content-Length":str(MAX_REQUEST_BYTES+1),"Content-Type":"multipart/form-data; boundary=x","X-CSRF-Token":self.service.csrf_token})[0],413)
  self.assertEqual(self.request("GET","/api/w7tp/v2/jobs/../../secret")[0],400)
 def test_random_input_is_not_false_product_pass(self):
  payload=os.urandom(65537);status,raw=self.post(payload);self.assertEqual(status,202);run=json.loads(raw)["run_id"];job=self.wait(run)
  self.assertEqual(job["state"],"HOLD");self.assertEqual(job["adjudication"],"NOT_ECONOMIC");self.assertEqual(job["generated_bytes"],len(payload));self.assertEqual(job["expected_sha256"],hashlib.sha256(payload).hexdigest());self.assertEqual(job["expected_sha256"],job["actual_sha256"]);self.assertEqual(job["verifier_decision"],"PASS");self.assertEqual(job["total_field_seal"],"PASS");self.assertEqual(job["reason_code"],"NOT_ECONOMIC_NO_GENERATIVE_PROVIDER")
  status,packet=self.request("GET",f"/api/w7tp/v2/jobs/{run}/packet");self.assertEqual(status,404)
 def test_repeat_block_is_provider_not_gate(self):
  status,raw=self.post(b"RULE"*20000);job=self.wait(json.loads(raw)["run_id"]);self.assertEqual(job["state"],"PASS");self.assertEqual(job["adjudication"],"W7TP_GENERATIVE")
 def test_packet_has_d1_d8_and_contracts(self):
  status,raw=self.post(b"ABCD"*20000);run=json.loads(raw)["run_id"];self.assertEqual(self.wait(run)["state"],"PASS");path=self.root/"jobs"/run/"w7tp-single-packet.html";text=path.read_text();marker='<script id="packet" type="application/json">';start=text.index(marker)+len(marker);packet=json.loads(text[start:text.index('</script>',start)])
  for number in range(1,9):self.assertTrue(any(key.startswith(f"D{number}_") for key in packet))
  d6=packet["D6_generative_transmission"];self.assertIn("protocol",d6);self.assertIn("lookup",d6);self.assertIn("references",d6);self.assertIn("reconstruction_contract",d6);self.assertIn("verification_contract",d6)
  d8=packet["D8_envelope"];self.assertTrue(d8["nonce"]);self.assertTrue(d8["ttl"]);self.assertTrue(d8["receiver_binding"]);self.assertTrue(d8["integrity"]["packet_sha256"]);self.assertTrue(d8["verification_entrypoint"])
 def test_artifact_gate_and_arbitrary_download(self):
  run="W7TP_GTF_"+"a"*32;directory=self.root/"jobs"/run;directory.mkdir();(directory/"w7tp-single-packet.html").write_text("partial");self.service.store.save({"run_id":run,"state":"GATEWAY_START","packet_ready":False})
  self.assertEqual(self.request("GET",f"/api/w7tp/v2/jobs/{run}/packet")[0],404);self.assertEqual(self.request("GET",f"/api/w7tp/v2/jobs/{run}/source")[0],400)
 def test_symlink_packet_rejected(self):
  status,raw=self.post(b"X"*40000);run=json.loads(raw)["run_id"];self.wait(run);packet=self.root/"jobs"/run/"w7tp-single-packet.html";packet.unlink();packet.symlink_to(self.root/"ledger"/f"{run}.json");self.assertEqual(self.request("GET",f"/api/w7tp/v2/jobs/{run}/packet")[0],404)
 def test_ledger_hides_payload_path_and_xss(self):
  payload=b"SECRET-NOT-IN-LEDGER";status,raw=self.post(payload,'<img src=x>.bin');run=json.loads(raw)["run_id"];job=self.wait(run);encoded=json.dumps(job);self.assertNotIn(payload.decode(),encoded);self.assertNotIn(str(self.root),encoded);self.assertNotIn("<img",job["source_name"])
 def test_ui_single_action_and_multipart(self):
  page=self.request("GET","/")[1].decode();script=self.request("GET","/app.js")[1].decode();self.assertIn("選檔 → 建立、驗證並下載單一封包",page);self.assertNotIn('name="os"',page);self.assertNotIn("source_hex",script);self.assertIn("new FormData",script);self.assertIn("/api/w7tp/v2/jobs",script)

if __name__=="__main__":unittest.main()
