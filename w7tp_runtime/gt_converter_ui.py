"""Loopback-only W7TP 8D V2 packet builder service."""
from __future__ import annotations
import argparse, html, json, os, re, secrets, tempfile, threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from .gt_packet_v2 import PacketV2, RUN_RE, canonical

MAX_REQUEST_BYTES=64*1024*1024
UI_ROOT=Path(__file__).with_name("ui")
TERMINAL={"PASS","HOLD","BLOCK","ERROR"}

class Store:
 def __init__(self,root:Path):
  self.root=root;self.jobs_root=root/"jobs";self.ledger=root/"ledger";self.jobs_root.mkdir(parents=True,exist_ok=True);self.ledger.mkdir(parents=True,exist_ok=True);self.lock=threading.RLock();self.jobs={}
  for path in self.ledger.glob("*.json"):
   try:
    item=json.loads(path.read_text());
    if RUN_RE.fullmatch(item.get("run_id","")):self.jobs[item["run_id"]]=item
   except (OSError,ValueError):pass
 def save(self,job:dict[str,Any]):
  keys=("state","run_id","progress","source_name","source_bytes","packet_bytes","generated_bytes","network_bytes","adjudication","expected_sha256","actual_sha256","verifier_decision","total_field_seal","integrity","authenticity","reason_code","packet_ready")
  safe={key:job.get(key) for key in keys};safe["source_name"]=html.escape(str(safe.get("source_name") or "source.bin"),quote=True);safe["reason_code"]=html.escape(str(safe["reason_code"]),quote=True) if safe.get("reason_code") else None
  target=self.ledger/f'{job["run_id"]}.json';temporary=target.with_suffix(".tmp")
  with self.lock:temporary.write_bytes(canonical(safe)+b"\n");os.replace(temporary,target);self.jobs[job["run_id"]]=safe
 def get(self,run:str):
  with self.lock:return dict(self.jobs[run]) if run in self.jobs else None

class Service:
 def __init__(self,root:Path):self.store=Store(root);self.executor=ThreadPoolExecutor(max_workers=2,thread_name_prefix="w7tp-v2");self.csrf_token=secrets.token_urlsafe(32)
 def enqueue(self,source:Path,filename:str,intent:str):
  run=f'W7TP_GTF_{secrets.token_hex(16)}';directory=self.store.jobs_root/run;directory.mkdir(mode=0o700);owned=directory/"source.bin";os.replace(source,owned)
  job={"state":"QUEUED","run_id":run,"progress":0,"source_name":Path(filename).name,"source_bytes":owned.stat().st_size,"packet_bytes":None,"generated_bytes":None,"network_bytes":0,"adjudication":None,"expected_sha256":None,"actual_sha256":None,"verifier_decision":None,"total_field_seal":None,"integrity":"UNVERIFIED","authenticity":"UNVERIFIED","reason_code":None,"packet_ready":False};self.store.save(job);self.executor.submit(self._run,job,owned,intent);return self.store.get(run)
 def _run(self,job,source,intent):
  directory=source.parent;packet=directory/"w7tp-single-packet.html"
  try:
   job.update(state="PACKET_BUILD",progress=25);self.store.save(job);composer=PacketV2();document=composer.compose(source,packet,job["run_id"],job["source_name"],intent)
   job.update(state="GATEWAY_START",progress=50,packet_bytes=packet.stat().st_size,adjudication=document["adjudication"],expected_sha256=document["D4_evidence"]["expected_hash"]);self.store.save(job)
   received=composer.isolated_receive(packet,directory/"isolated_receiver")
   economic=document["adjudication"]!="NOT_ECONOMIC"
   job.update(state="PASS" if economic else "HOLD",progress=100,generated_bytes=received.generated_bytes,actual_sha256=received.actual_sha256,verifier_decision=received.verifier_decision,total_field_seal=received.total_field_seal,integrity="PASS",packet_ready=economic,reason_code=None if economic else "NOT_ECONOMIC_NO_GENERATIVE_PROVIDER")
  except Exception as exc:job.update(state="HOLD" if isinstance(exc,(ValueError,FileExistsError)) else "ERROR",progress=100,reason_code=exc.args[0] if exc.args and isinstance(exc.args[0],str) else "INTERNAL_ERROR",packet_ready=False)
  finally:source.unlink(missing_ok=True);self.store.save(job)
 def close(self):self.executor.shutdown(wait=True)

def stream_multipart(handler:BaseHTTPRequestHandler,length:int,boundary:bytes)->tuple[Path,str,str]:
 if length<=0 or length>MAX_REQUEST_BYTES:raise ValueError("REQUEST_TOO_LARGE")
 remaining=length;line=handler.rfile.readline();remaining-=len(line)
 if line.rstrip(b"\r\n")!=b"--"+boundary:raise ValueError("INVALID_MULTIPART")
 headers={}
 while remaining>0:
  line=handler.rfile.readline();remaining-=len(line)
  if line in (b"\r\n",b"\n"):break
  key,value=line.decode("utf-8","replace").split(":",1);headers[key.lower().strip()]=value.strip()
 disposition=headers.get("content-disposition","");match=re.search(r'filename="([^"\\/]*)"',disposition)
 if not match:raise ValueError("FILE_REQUIRED")
 filename=match.group(1) or "source.bin";temporary=tempfile.NamedTemporaryFile("wb",delete=False);path=Path(temporary.name);previous=None
 try:
  delimiter=b"--"+boundary
  while remaining>0:
   line=handler.rfile.readline();remaining-=len(line)
   if line.rstrip(b"\r\n") in (delimiter,delimiter+b"--"):
    if previous is not None:temporary.write(previous[:-2] if previous.endswith(b"\r\n") else previous[:-1] if previous.endswith(b"\n") else previous)
    break
   if previous is not None:temporary.write(previous)
   previous=line
  temporary.close();return path,filename,"BYTE_EXACT"
 except Exception:temporary.close();path.unlink(missing_ok=True);raise

class Server(ThreadingHTTPServer):
 daemon_threads=True
 def __init__(self,address,service):
  if address[0]!="127.0.0.1":raise ValueError("NON_LOCAL_BIND")
  self.service=service;super().__init__(address,Handler)

class Handler(BaseHTTPRequestHandler):
 server:Server
 def log_message(self,*args):pass
 def allowed(self,mutating=False):
  hosts={f"127.0.0.1:{self.server.server_port}",f"localhost:{self.server.server_port}"};host=self.headers.get("Host","")
  if host not in hosts:return self.reply(403,{"state":"BLOCK","reason_code":"INVALID_HOST"})
  origin=self.headers.get("Origin")
  if origin and origin not in {f"http://{h}" for h in hosts}:return self.reply(403,{"state":"BLOCK","reason_code":"INVALID_ORIGIN"})
  if mutating and self.headers.get("X-CSRF-Token")!=self.server.service.csrf_token:return self.reply(403,{"state":"BLOCK","reason_code":"INVALID_CSRF"})
  return True
 def reply(self,status,value):
  body=json.dumps(value,ensure_ascii=False,separators=(",",":")).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(body)));self.send_header("X-Content-Type-Options","nosniff");self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");self.end_headers();self.wfile.write(body);return False
 def route(self,path):
  match=re.fullmatch(r"/api/w7tp/v2/jobs/(W7TP_GTF_[a-f0-9]{32})(?:/(packet))?",path);return match.groups() if match else (None,None)
 def do_GET(self):
  if not self.allowed():return
  path=urlparse(self.path).path
  if path=="/health":return self.reply(200,{"state":"PASS"})
  if path=="/api/w7tp/v2/capabilities":return self.reply(200,{"state":"PASS","csrf_token":self.server.service.csrf_token,"packet_carries_transport_protocol":True,"packet_carries_verification_method":True,"one_time_gateway_supported":True,"total_field_verifier_bound":True,"adjudications":["W7TP_GENERATIVE","W7TP_HYBRID","DIRECT_TRANSFER","NOT_ECONOMIC"]})
  if path in {"/","/index.html","/app.css","/app.js"}:
   file=UI_ROOT/("index.html" if path in {"/","/index.html"} else path[1:]);body=file.read_bytes();kind="text/html" if file.suffix==".html" else "text/css" if file.suffix==".css" else "text/javascript";self.send_response(200);self.send_header("Content-Type",kind+"; charset=utf-8");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body);return
  run,artifact=self.route(path)
  if not run:return self.reply(400,{"state":"BLOCK","reason_code":"INVALID_RUN_ID"})
  job=self.server.service.store.get(run)
  if not job:return self.reply(404,{"state":"HOLD","reason_code":"JOB_NOT_FOUND"})
  if not artifact:return self.reply(200,job)
  target=self.server.service.store.jobs_root/run/"w7tp-single-packet.html";root=(self.server.service.store.jobs_root/run).resolve()
  if not job.get("packet_ready") or target.is_symlink() or root not in target.resolve(strict=False).parents or not target.is_file():return self.reply(404,{"state":"HOLD","reason_code":"ARTIFACT_NOT_READY"})
  body=target.read_bytes();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Disposition",'attachment; filename="w7tp-single-packet.html"');self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
 def do_POST(self):
  if not self.allowed(True):return
  if urlparse(self.path).path!="/api/w7tp/v2/jobs":return self.reply(404,{"state":"HOLD","reason_code":"NOT_FOUND"})
  try:
   kind=self.headers.get("Content-Type","");match=re.fullmatch(r'multipart/form-data;\s*boundary=(?:"([^"]+)"|([^;]+))',kind)
   if not match:raise ValueError("MULTIPART_REQUIRED")
   source,name,intent=stream_multipart(self,int(self.headers.get("Content-Length","0")),(match.group(1) or match.group(2)).encode());job=self.server.service.enqueue(source,name,intent);return self.reply(202,job)
  except ValueError as exc:return self.reply(413 if str(exc)=="REQUEST_TOO_LARGE" else 400,{"state":"BLOCK","reason_code":str(exc)})

def create_server(host="127.0.0.1",port=8787,data_root:Path|None=None):return Server((host,port),Service(data_root or Path.home()/".w7tp_gt_converter_ui"))
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--host",default="127.0.0.1");parser.add_argument("--port",type=int,default=8787);parser.add_argument("--data-root",type=Path);args=parser.parse_args()
 try:server=create_server(args.host,args.port,args.data_root)
 except ValueError as exc:print(f"STATE=BLOCK\nREASON_CODE={exc}");return 20
 print(f"STATE=PASS\nURL=http://127.0.0.1:{server.server_port}",flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.shutdown();server.service.close();server.server_close()
 return 0
if __name__=="__main__":raise SystemExit(main())
