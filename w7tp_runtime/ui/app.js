'use strict';
let csrf='',timer=null,capabilitySummary=null;
const terminalStates=new Set(['PASS','HOLD','BLOCK','ERROR','CANCELLED']);
const fields=[['run_id','run_id'],['progress','進度'],['source_bytes','來源大小'],['packet_bytes','封包大小'],['reduction_ratio','縮減倍率'],['expected_sha256','expected SHA-256'],['actual_sha256','actual SHA-256'],['integrity','內容完整性'],['authenticity','來源真實性'],['reason_code','reason code']];
const safe=value=>value==null?'—':String(value);
const reasonText=code=>{
  if(code==='NOT_GENERATIVELY_REDUCIBLE'||code==='REDUCTION_RATIO_TOO_LOW'||code==='SINGLE_BLOCK_FORBIDDEN')return '目前產品實作尚未完成此檔案的單封包建構方式；不是檔案不能重構。';
  if(code==='ARTIFACT_NOT_READY')return '工作尚未完成，請等待工作狀態更新。';
  return code?`工作回報：${code}`:'工作依真實狀態處理中。';
};
async function loadCapabilities(){const response=await fetch('/api/capabilities');capabilitySummary=await response.json();csrf=capabilitySummary.csrf_token}
function gateLink(id,ready,runId){const link=document.querySelector(`#${id}`);link.classList.toggle('disabled',!ready);link.setAttribute('aria-disabled',String(!ready));if(ready)link.href=`/api/jobs/${encodeURIComponent(runId)}/${id}`;else link.removeAttribute('href')}
function render(job){
  document.querySelector('#state').textContent=safe(job.state);
  document.querySelector('#guidance').textContent=reasonText(job.reason_code);
  const list=document.querySelector('#result');list.replaceChildren();
  for(const[key,label]of fields){const term=document.createElement('dt'),description=document.createElement('dd');term.textContent=label;let value=job[key];if(key==='authenticity'&&value==='UNVERIFIED')value='尚未驗證';if(key==='reason_code'&&value)value=reasonText(value);description.textContent=safe(value);list.append(term,description)}
  document.querySelector('#json').textContent=JSON.stringify(job,null,2);
  gateLink('packet',Boolean(job.packet_ready),job.run_id);gateLink('report',Boolean(job.report_ready),job.run_id);
  document.querySelector('#capabilities').disabled=!terminalStates.has(job.state);
  if(!terminalStates.has(job.state))timer=setTimeout(()=>poll(job.run_id),500);
}
async function poll(runId){const response=await fetch(`/api/jobs/${encodeURIComponent(runId)}`);render(await response.json())}
document.querySelector('#capabilities').addEventListener('click',()=>{if(capabilitySummary)document.querySelector('#json').textContent=JSON.stringify(capabilitySummary,null,2)});
document.querySelector('#job').addEventListener('submit',async event=>{event.preventDefault();clearTimeout(timer);const file=document.querySelector('#source').files[0],bytes=new Uint8Array(await file.arrayBuffer());let hex='';for(const byte of bytes)hex+=byte.toString(16).padStart(2,'0');const body={source_hex:hex,filename:file.name,target_os:'portable',target_name:'reconstructed.bin'};const response=await fetch('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(body)});render(await response.json())});
loadCapabilities();
