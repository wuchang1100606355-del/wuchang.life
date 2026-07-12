"""Canonical V2 8D packet composer and isolated receiver gateway."""
from __future__ import annotations
import hashlib, html, json, os, re, tempfile, time, uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Decision = Literal["W7TP_GENERATIVE", "W7TP_HYBRID", "DIRECT_TRANSFER", "NOT_ECONOMIC"]
PROTOCOL = "W7TP-8D-GT"
VERSION = "2.0"
RUN_RE = re.compile(r"^W7TP_GTF_[a-f0-9]{32}$")

def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def sha256_file(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()

def repeated_block(data: bytes) -> tuple[bytes,int] | None:
    if not data: return None
    prefix=[0]*len(data); matched=0
    for index in range(1,len(data)):
        while matched and data[index]!=data[matched]: matched=prefix[matched-1]
        if data[index]==data[matched]: matched+=1; prefix[index]=matched
    period=len(data)-prefix[-1]
    if period<len(data) and len(data)%period==0: return data[:period],len(data)//period
    return None

def packet_hash(packet: dict[str,Any]) -> str:
    clone=json.loads(canonical(packet)); clone["D8_envelope"]["integrity"]["packet_sha256"]=""
    return hashlib.sha256(canonical(clone)).hexdigest()

@dataclass(frozen=True)
class BuildResult:
    run_id:str; packet_path:Path; packet_bytes:int; generated_bytes:int; decision:Decision
    expected_sha256:str; actual_sha256:str; verifier_decision:str; total_field_seal:str

class PacketV2:
    def compose(self,source:Path,packet_path:Path,run_id:str,filename:str,intent:str="BYTE_EXACT") -> dict[str,Any]:
        data=source.read_bytes(); expected=hashlib.sha256(data).hexdigest(); rule=repeated_block(data)
        if rule:
            block,count=rule; decision:Decision="W7TP_GENERATIVE"
            generation={"provider":"repeat_block","block_bytes":list(block),"repeat_count":count,"residual_bytes":[]}
        else:
            decision="DIRECT_TRANSFER" if intent=="DIRECT_TRANSFER_ALLOWED" else "NOT_ECONOMIC"
            generation={"provider":"direct_residual","block_bytes":[],"repeat_count":0,"residual_bytes":list(data)}
        packet={
          "D1_intent":{"target":"verified_file","operation":"reconstruct","reconstruction_scope":"complete","equivalence_level":"L1_BYTE_EXACT","authority":"LOCAL_USER","result_intent":intent},
          "D2_state":{"source_state":"ANALYZED","target_state":"MATERIALIZED","current_state":"SEALED","terminal_state":"PASS","state_transition":["GATEWAY_START","RECONSTRUCT","BYTE_EXACT","TOTAL_FIELD_SEAL"]},
          "D3_coordinate":{"spatial":None,"temporal":None,"structural":{"byte_length":len(data)},"logical":{"domain_profile":"binary"},"relational":[]},
          "D4_evidence":{"source_hash":expected,"expected_hash":expected,"table_hash":None,"rule_hash":hashlib.sha256(canonical(generation)).hexdigest(),"execution_record":None,"verification_record":"BYTE_EXACT"},
          "D5_execution":{"bootstrap":"embedded_browser_gateway_v1","steps":["GATEWAY_START","RECONSTRUCT","BYTE_EXACT","TOTAL_FIELD_SEAL"],"dependencies":[],"output_action":"USER_DOWNLOAD","completion_action":"MATERIALIZE_AFTER_PASS","abort_action":"NO_OUTPUT"},
          "D6_generative_transmission":{"protocol":{"name":PROTOCOL,"version":VERSION,"mode":"SINGLE_PACKET","order":"STRICT","completion":"TOTAL_FIELD_SEAL"},"routing":{"carrier":"LOCAL_FILE","network_bytes_after_receive":0},"lookup":{"capability":"embedded_generation_rule_registry","keys":[generation["provider"]]},"references":{"approved_local_resources":[]},"reconstruction_contract":{"expected_bytes":len(data),"filename":Path(filename).name},"generation_rules":generation,"verification_contract":{"mode":"BYTE_EXACT","method":"SHA-256","expected_sha256":expected},"residual":{"present":generation["provider"]=="direct_residual"},"refill_policy":"NONE"},
          "D7_risk":{"secret_risk":"NOT_SCANNED_CONTENT_OPAQUE","privacy_risk":"LOCAL_ONLY","destructive_action":False,"write_boundary":"USER_INITIATED_DOWNLOAD","execution_boundary":"NO_NETWORK"},
          "D8_envelope":{"packet_id":run_id,"version":VERSION,"nonce":uuid.uuid4().hex,"ttl":86400,"authority":"LOCAL_USER","receiver_binding":"BROWSER_WEB_CRYPTO","integrity":{"method":"SHA-256","packet_sha256":""},"replay_policy":"USER_INITIATED","scope":"SINGLE_FILE","verification_entrypoint":"w7tpGateway"},
          "adjudication":decision,"authenticity":"UNVERIFIED"
        }
        packet["D8_envelope"]["integrity"]["packet_sha256"]=packet_hash(packet)
        document=self._html(packet)
        packet_path.parent.mkdir(parents=True,exist_ok=True)
        with packet_path.open("xb") as stream: stream.write(document)
        return packet

    def _html(self,packet:dict[str,Any])->bytes:
        name=html.escape(packet["D6_generative_transmission"]["reconstruction_contract"]["filename"],quote=True)
        payload=canonical(packet).decode().replace("</","<\\/")
        page=f'''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>W7TP單一封包</title><style>body{{font:20px system-ui;max-width:850px;margin:auto;padding:2rem;background:#111;color:#fff}}button{{font-size:20px;min-height:52px;padding:1rem}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style><h1>W7TP 8D 單一自重構封包</h1><p>檔案：{name}</p><button id="run">開啟閘道器、驗證並產生成品</button><pre id="state">READY</pre><script id="packet" type="application/json">{payload}</script><script>
const p=JSON.parse(document.querySelector('#packet').textContent),s=document.querySelector('#state');async function w7tpGateway(){{s.textContent='GATEWAY_START';const g=p.D6_generative_transmission.generation_rules;let bytes;if(g.provider==='repeat_block'){{const b=new Uint8Array(g.block_bytes);bytes=new Uint8Array(b.length*g.repeat_count);for(let i=0;i<g.repeat_count;i++)bytes.set(b,i*b.length)}}else bytes=new Uint8Array(g.residual_bytes);s.textContent='RECONSTRUCT';const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');if(hash!==p.D6_generative_transmission.verification_contract.expected_sha256){{s.textContent='HOLD: BYTE_EXACT';return}}s.textContent='PASS: BYTE_EXACT → TOTAL_FIELD_SEAL';const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([bytes]));a.download=p.D6_generative_transmission.reconstruction_contract.filename;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}}document.querySelector('#run').onclick=w7tpGateway;
</script></html>'''
        return page.encode()

    def isolated_receive(self,packet_path:Path,output_root:Path)->BuildResult:
        raw=packet_path.read_text(encoding="utf-8"); marker='<script id="packet" type="application/json">'; start=raw.index(marker)+len(marker); end=raw.index('</script>',start)
        packet=json.loads(raw[start:end].replace("<\\/","</")); run=packet["D8_envelope"]["packet_id"]
        if not RUN_RE.fullmatch(run) or packet_hash(packet)!=packet["D8_envelope"]["integrity"]["packet_sha256"]: raise ValueError("PACKET_INTEGRITY_HOLD")
        rules=packet["D6_generative_transmission"]["generation_rules"]; expected=packet["D6_generative_transmission"]["verification_contract"]["expected_sha256"]
        output_root.mkdir(parents=True,exist_ok=True); output=output_root/"received.bin"
        if output.exists() or output.is_symlink(): raise FileExistsError("OUTPUT_EXISTS")
        temp:Path|None=None
        try:
            with tempfile.NamedTemporaryFile("xb",dir=output_root,prefix=".gateway-",delete=False) as stream:
                temp=Path(stream.name)
                if rules["provider"]=="repeat_block":
                    block=bytes(rules["block_bytes"])
                    for _ in range(rules["repeat_count"]): stream.write(block)
                else:
                    residual=rules["residual_bytes"]
                    for at in range(0,len(residual),1024*1024): stream.write(bytes(residual[at:at+1024*1024]))
                stream.flush();os.fsync(stream.fileno())
            actual=sha256_file(temp)
            if actual!=expected: raise ValueError("BYTE_EXACT_HOLD")
            os.link(temp,output);temp.unlink();temp=None
            return BuildResult(run,packet_path,packet_path.stat().st_size,output.stat().st_size,packet["adjudication"],expected,actual,"PASS","PASS")
        finally:
            if temp: temp.unlink(missing_ok=True)
