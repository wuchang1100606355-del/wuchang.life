const $=s=>document.querySelector(s); let boot=null, preview=null, pending=null;
async function rpc(url,params={}){
  const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({jsonrpc:"2.0",method:"call",params,id:Date.now()})});
  const j=await r.json(); if(j.error) throw new Error(j.error.data?.message||j.error.message||"RPC_ERROR"); return j.result;
}
function show(id){$(id).classList.remove("hidden")}
function evidence(extra={}){
  const rows={
    "D1 意圖":$("#intent").value||"未輸入",
    "D2 狀態":extra.state||preview?.state||"READY",
    "D3 座標":boot?.organization_ref||"UNKNOWN",
    "D4 證據":extra.evidence||preview?.lookup_receipt_hash||"尚未形成",
    "D5 執行／政策":extra.policy||"候選建議；本人確認前不得作用",
    "D6 生成式狀態傳輸":"本頁不以差分傳輸宣稱效果；僅顯示本次受治理狀態投影",
    "D7 風險／隔離":"紅茶券單一沙盒；雲端模型非必要依賴",
    "D8 封套／權威":extra.authority||"模型無直接作用權；自然人確認才可扣券"
  };
  $("#field").innerHTML=Object.entries(rows).map(([k,v])=>`<div class="drow"><b>${k}</b><span>${String(v)}</span></div>`).join(""); show("#evidence");
}
async function init(){
  boot=await rpc("/wuchang/xiaoj/api/sovereign-demo-bootstrap");
  $("#runtime").textContent=boot.state==="READY"&&boot.feature_enabled?"實機已連線":"HOLD";
}
init().catch(e=>{$("#runtime").textContent="HOLD"; console.error(e)});
$("#understand").onclick=async()=>{
  try{
    if(!boot||boot.state!=="READY") throw new Error("總場能力座尚未就緒");
    preview=await rpc("/wuchang/xiaoj/api/staff-red-tea-voucher-preview",{seat_ref:boot.seat_ref,last_three:"757"});
    if(preview.state!=="MATCH") throw new Error(preview.state);
    $("#suggestionTitle").textContent="先用你已經有的紅茶提貨券";
    $("#suggestionBody").textContent=`你現在有 ${preview.red_tea_voucher_count} 張可用紅茶券。你只說想喝點東西，小J沒有直接迎合點餐，而是先找到你已持有、現在可用的權益；不需要再付款。`;
    show("#suggestion");
  }catch(e){$("#runtime").textContent="HOLD"; alert(e.message)}
};
$("#why").onclick=()=>evidence({state:"MATCH + TEMPORARY_INTENT",policy:"建議可提出；尚未取得執行權",authority:"目前只有建議權，沒有扣券權"});
$("#doit").onclick=async()=>{
  try{
    pending=await rpc("/wuchang/xiaoj/api/staff-red-tea-voucher-request",{checkout_ref:preview.checkout_ref,order_ref:"XJ-DEMO-"+Date.now()});
    $("#authorityBody").textContent=`店員請求已建立，但目前仍有 ${pending.voucher_count_before} 張。狀態：${pending.state}。沒有江先生本人確認，小J不能扣券。`;
    show("#authority"); evidence({state:pending.state,evidence:pending.request_hash,authority:"HOLD：等待自然人本人確認"});
  }catch(e){alert(e.message)}
};
$("#confirm").onclick=async()=>{
  try{
    const r=await rpc("/wuchang/xiaoj/api/member-red-tea-voucher-confirm",{checkout_ref:pending.checkout_ref,approve:true});
    $("#resultTitle").textContent=`已完成：${r.voucher_count_before} → ${r.voucher_count_after}`;
    $("#resultBody").textContent="1 張聊國紅茶提貨券已由本人確認後核銷。";
    $("#txhash").textContent="transaction_hash: "+r.transaction_hash; show("#result");
    evidence({state:r.state,evidence:r.transaction_hash,policy:"ALLOW：本人確認後執行 1 張紅茶券核銷",authority:"自然人確認 + 沙盒封套 + 能力座"});
    $("#authority").classList.add("hidden");
  }catch(e){alert(e.message)}
};
$("#deny").onclick=async()=>{
  try{
    const r=await rpc("/wuchang/xiaoj/api/member-red-tea-voucher-confirm",{checkout_ref:pending.checkout_ref,approve:false});
    $("#resultTitle").textContent="DENY：本人不同意";
    $("#resultBody").textContent="作用已停止；提貨券沒有被核銷。"; $("#txhash").textContent="";
    show("#result"); evidence({state:r.state,evidence:r.owner_confirmation_ref||"DENY",policy:"DENY：停止作用",authority:"自然人拒絕優先於模型建議"});
    $("#authority").classList.add("hidden");
  }catch(e){alert(e.message)}
};
