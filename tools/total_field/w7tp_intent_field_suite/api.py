"""Private-by-default shared HTTP API and accessible XiaoJ product interface."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from tools.tfct_true8d_runtime_candidate import RuntimeCandidateError
from tools.total_field_candidate_gateway import (
    TotalFieldGatewayError,
    receive_candidate,
)
from tools.total_field.w7tp_field_application_runtime import (
    FieldApplicationError,
    device_llm_execution_policy,
)

from .canonical_hash import canonical_sha256
from .contracts import CONTRACTS
from .drift_monitor import client_drift_rules, evaluate_drift
from .identity_prefix import assert_llm_candidate_does_not_mutate_identity
from .identity_projection import (
    IdentityPrefixResolver,
    verify_trusted_identity_projection,
)
from .node_inventory import collect_inventory
from .packet_builder import process_intent


MAX_REQUEST_BYTES = 64 * 1024
CAFE_POS_TOTAL_FIELD_RECEIVER = "receive_candidate"
CAFE_POS_TOTAL_FIELD_RECEIVER_REF = (
    "tools.total_field_candidate_gateway.receive_candidate"
)
CAFE_POS_RECEIVER_CONTEXT_KEYS = frozenset(
    {
        "request_id",
        "caller_ref",
        "observation_domain_ref",
        "receiver_ref",
        "merchant_mode",
        "community_happiness_coin_accepted",
        "consumer_happiness_coin_issued",
        "community_merchant_ticket_quota",
        "fund_1_to_1_to_1_binding",
    }
)
CAFE_POS_REQUEST_ID_PATTERN = re.compile(r"^odoo-cafe:[a-f0-9]{32}$")
OPAQUE_REF_PATTERN = re.compile(r"^[A-Za-z0-9_.:/-]{3,180}$")
INDEPENDENT_MERCHANT_MODE = "INDEPENDENT_MERCHANT_OUTSIDE_COMMUNITY"
INDEPENDENT_MERCHANT_FALSE_FLAGS = (
    "community_happiness_coin_accepted",
    "consumer_happiness_coin_issued",
    "community_merchant_ticket_quota",
    "fund_1_to_1_to_1_binding",
)

PRODUCT_HTML = """<!doctype html>
<html lang="zh-Hant" data-llm-execution="USER_DEVICE_ONLY">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<title>AI 影音小J｜生成式傳輸測試</title>
<style>
:root{color-scheme:dark;--bg:#07111f;--panel:#10243b;--text:#f7fbff;--muted:#c6d7e8;--accent:#5eead4;--focus:#fbbf24;--danger:#fda4af}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(145deg,#07111f,#132d46);color:var(--text);font:18px/1.6 system-ui,sans-serif}
main{width:min(1100px,94vw);margin:auto;padding:2rem 0 4rem}.hero,.panel{background:rgba(16,36,59,.96);border:1px solid #37617f;border-radius:20px;padding:clamp(1rem,3vw,2rem);box-shadow:0 18px 50px #0005}.hero{margin-bottom:1rem}
h1{font-size:clamp(2rem,5vw,4rem);line-height:1.1;margin:.2rem 0 1rem}h2{margin-top:0}.lead{font-size:1.2rem;color:var(--muted)}
label{display:block;font-weight:750;margin:.85rem 0 .35rem}select,textarea,input,button{font:inherit}select,textarea,input{width:100%;color:var(--text);background:#071827;border:2px solid #5c7f98;border-radius:12px;padding:.8rem}textarea{min-height:9rem;resize:vertical}
button{border:0;border-radius:999px;padding:.8rem 1.25rem;font-weight:800;background:var(--accent);color:#052019;cursor:pointer;margin:.8rem .4rem .2rem 0}button.secondary{background:#dbeafe;color:#10243b}button:focus-visible,select:focus-visible,textarea:focus-visible,input:focus-visible{outline:4px solid var(--focus);outline-offset:3px}
.grid{display:grid;grid-template-columns:minmax(0,1.02fr) minmax(0,.98fr);gap:1rem;align-items:start}.status{padding:.8rem;border-left:5px solid var(--accent);background:#071827;margin:.8rem 0;border-radius:.55rem}.hold{border-color:var(--danger)}pre{white-space:pre-wrap;word-break:break-word;background:#06131f;padding:1rem;border-radius:12px;max-height:36rem;overflow:auto}.small{font-size:.9rem;color:var(--muted)}.skip{position:fixed;top:-5rem;left:1rem;z-index:20;background:#fff;color:#07111f;padding:.7rem 1rem;border-radius:.7rem}.skip:focus{top:1rem}.topbar{width:min(1100px,94vw);margin:auto;display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:1rem 0}.brand{display:flex;align-items:center;gap:.55rem;color:#fff;text-decoration:none;font-weight:900}.brand-mark{display:grid;place-items:center;width:2.5rem;height:2.5rem;border-radius:.8rem;background:var(--accent);color:#052019}.topbar nav{display:flex;gap:.8rem}.topbar nav a{display:inline-flex;align-items:center;min-height:44px;color:#dff8f2;font-weight:750}.proofs{display:grid;grid-template-columns:repeat(3,1fr);gap:.6rem;margin-top:1.2rem}.proof{padding:.7rem;border:1px solid #ffffff38;border-radius:.9rem;background:#ffffff0b}.proof strong,.proof span{display:block}.proof span{font-size:.78rem;color:#c6d7e8}.journey{display:grid;grid-template-columns:repeat(3,1fr);gap:.4rem;padding:0;margin:0 0 1rem;list-style:none}.journey li{padding:.5rem;border-radius:.7rem;background:#071827;color:#91a9ba;text-align:center;font-size:.75rem;font-weight:850}.journey li.active{background:#614b08;color:#fff3bd}.journey li.done{background:#0b594f;color:#d9fff7}.suggestion{display:flex;justify-content:space-between;align-items:center;gap:.7rem;padding:.65rem;margin:.65rem 0;border:1px dashed #6f99a9;border-radius:.8rem;background:#0a1d2c}.suggestion p{margin:0}.privacy{display:grid;grid-template-columns:repeat(2,1fr);gap:.4rem;margin:.8rem 0}.privacy span{padding:.48rem;border-radius:.6rem;background:#071827;color:#c6d7e8;font-size:.73rem}.actions{display:flex;flex-wrap:wrap;gap:.5rem}.guided-card{margin-top:1rem;padding:1rem;border:2px solid #a47c1c;border-radius:1rem;background:#191d24}.guided-head{display:flex;justify-content:space-between;gap:.6rem}.question-id{font:700 .7rem/1.4 ui-monospace,monospace;color:#dbc36f}.option[aria-pressed="true"]{outline:3px solid var(--focus);background:var(--focus)}.system-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:.45rem;margin-bottom:1rem}.system-state{padding:.6rem;border:1px solid #37617f;border-radius:.8rem;background:#071827;min-height:4.7rem}.system-state strong,.system-state span{display:block}.system-state strong{font-size:.7rem;color:#9fb6c8}.system-state span{font-size:.78rem;font-weight:850}.empty{display:grid;place-items:center;min-height:16rem;text-align:center;border:1px dashed #5c7f98;border-radius:1rem;color:var(--muted);padding:1rem}.empty-mark{display:grid;place-items:center;width:4rem;height:4rem;margin:auto;border-radius:1.2rem;background:#123f48;color:var(--accent);font-weight:950}.candidate{display:grid;gap:.7rem}.candidate-summary{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}.result-card{padding:.7rem;border:1px solid #37617f;border-radius:.8rem;background:#071827}.result-card strong,.result-card span{display:block}.result-card strong{font-size:.7rem;color:#9fb6c8}.result-card span{font-weight:850;word-break:break-word}.dimensions{display:grid;grid-template-columns:repeat(4,1fr);gap:.4rem}.dimension{padding:.6rem;border-radius:.7rem;background:#06131f;min-height:5rem}.dimension strong,.dimension span{display:block}.dimension strong{font-size:.7rem;color:var(--accent)}.dimension span{font-size:.7rem;word-break:break-word}.evidence-risk{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}.evidence-risk section{padding:.7rem;border:1px solid #37617f;border-radius:.8rem}.evidence-risk h3{margin:0;font-size:.95rem}.evidence-risk ul{margin:.35rem 0 0;padding-left:1.1rem;font-size:.72rem;overflow-wrap:anywhere}.hash{font:700 .7rem/1.5 ui-monospace,monospace;word-break:break-all}d
{display:contents}
</style>
<style>
details{border:1px solid #37617f;border-radius:.8rem;background:#071827}
summary{cursor:pointer;min-height:48px;padding:.65rem;font-weight:800}
.nodes{margin:1rem auto}.node-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.55rem}
.node{padding:.7rem;border:1px solid #37617f;border-radius:.8rem;background:#071827}
.node strong,.node span{display:block}.node strong{overflow-wrap:anywhere}.node span{font-size:.7rem;color:#9fb6c8}
.node .node-state{display:inline-flex;margin-top:.4rem;padding:.15rem .4rem;border-radius:999px;background:#193347;color:#d5e6f2;font-weight:850}
.node .usable{background:#0b594f;color:#d9fff7}
.truth{display:grid;grid-template-columns:repeat(4,1fr);gap:.55rem;margin-top:1rem}
.truth article{padding:.75rem;border-radius:.8rem;background:#071827}.truth b,.truth span{display:block}
.truth b{font-size:.72rem;color:var(--accent)}.truth span{font-size:.72rem;color:#c6d7e8}
.redteam-monitor{display:grid;grid-template-columns:minmax(12rem,.34fr) 1fr;gap:.8rem;align-items:center;padding:1rem;border:2px solid #37617f;border-radius:1rem;background:#071827;margin:.8rem 0 1rem}
.redteam-monitor strong,.redteam-monitor span{display:block}.redteam-monitor .eyebrow{font-size:.7rem;color:var(--accent);font-weight:900;letter-spacing:.08em}.redteam-monitor p{margin:0;color:#c6d7e8;font-size:.78rem}.redteam-monitor ul{margin:.35rem 0 0;padding-left:1.2rem;font-size:.75rem}.redteam-monitor[data-state="DRIFT_ALERT"]{border-color:var(--danger);background:#37121a}.redteam-monitor[data-state="DRIFT_ALERT"] .eyebrow{color:#fecdd3}
.footer{width:min(1100px,94vw);margin:auto;padding:0 0 2rem;color:#9fb6c8;font-size:.72rem}
.footer div{display:flex;justify-content:space-between;gap:1rem;border-top:1px solid #37617f;padding-top:1rem}
[aria-busy="true"]{cursor:progress}[hidden]{display:none!important}
@media(max-width:900px){
  .grid{grid-template-columns:1fr}
  .dimensions,.node-grid{grid-template-columns:repeat(2,1fr)}
  .truth{grid-template-columns:repeat(2,1fr)}
}
@media(max-width:620px){
  body{font-size:17px}.topbar{align-items:flex-start}.topbar .brand-label{display:none}
  .proofs,.system-strip,.candidate-summary,.evidence-risk,.privacy,.truth,.dimensions,.node-grid{grid-template-columns:1fr}
  .suggestion,.footer div{align-items:flex-start;flex-direction:column}.suggestion button{width:100%}
  .redteam-monitor{grid-template-columns:1fr}
}
@media(prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}*,*:before,*:after{animation:none!important;transition:none!important}
}
</style>
</head>
<body><a class="skip" href="#main">跳到主要操作</a><header class="topbar"><a class="brand" href="/" aria-label="回到五常社區發展協會首頁"><span class="brand-mark" aria-hidden="true">總</span><span class="brand-label">五常社區發展協會</span></a><nav aria-label="頁面導覽"><a href="#workspace">開始測試</a><a href="#nodes">節點狀態</a></nav></header><main id="main">
<section class="hero" aria-labelledby="title"><p class="small">AI 影音小J · 單一共用意圖場</p><h1 id="title">立即測試生成式傳輸</h1><p class="lead">聊國咖啡館老闆的私家傳輸技術，小傳輸量，可產生大檔案結果。</p><p>用日常語言說明需求，小J協助整理；你確認的最小意圖候選才送交總場查表、驗證與封印。所有輸出都是 L3 候選。免費訂閱。</p><div class="proofs" aria-label="系統核心邊界"><div class="proof"><strong>設備端理解</strong><span>LLM 僅在使用者設備</span></div><div class="proof"><strong>伺服器端總場</strong><span>只收最小候選與證據引用</span></div><div class="proof"><strong>人類保有裁決</strong><span>不自動形成正式 D8</span></div></div></section>
<aside class="status" aria-label="裝置端 LLM 邊界"><strong>LLM 只在使用者設備執行；本頁不在伺服器載入或執行模型。</strong> taiji01 與合作伺服器不載入模型、不讀取原始 prompt 或模型脈絡。本頁目前只使用裝置端固定規則提出場域建議；未來接入裝置端模型時，資料仍留在使用者設備。</aside>
<aside id="redteam-monitor" class="redteam-monitor" data-state="MONITORING_CLEAR" role="status" aria-live="polite" aria-atomic="true"><div><span class="eyebrow">ALWAYS-ON REDTEAM</span><strong id="redteam-state">常駐紅隊觀點監看中</strong></div><div><p id="redteam-detail">裝置端即時預警；每次狀態續接再由總場確定性規則重驗。兩端皆不使用伺服器 LLM。</p><ul id="drift-alerts" hidden></ul></div></aside>
<div id="workspace" class="grid">
<section class="panel" aria-labelledby="input-title"><p class="small">STEP 01 · 用日常語言開始</p><h2 id="input-title">把需要處理的事說清楚</h2><p class="small">不需要理解封包；系統只追問形成安全候選不可缺的資料。</p>
<ol class="journey" aria-label="候選建立進度"><li id="step-intent" class="active">描述需求</li><li id="step-guide">一次一題</li><li id="step-candidate">候選核對</li></ol>
<label for="profile">服務場域</label><select id="profile"><option value="GENERIC" selected>一般需求</option><option value="ASSOCIATION">社區服務與志工協作</option><option value="PROPERTY">物業設備與檢查</option><option value="CAFE_POS">商家商品候選</option><option value="HOUSEHOLD">日常提醒與照護</option></select>
<div id="profile-suggestion" class="suggestion" hidden><p><span class="small">裝置端規則建議</span><br><strong id="suggested-profile"></strong></p><button id="apply-suggestion" class="secondary" type="button">採用建議</button></div>
<label for="intent">希望得到什麼結果？</label><textarea id="intent" maxlength="2000" aria-describedby="input-boundary" placeholder="例如：整理一份不含個資的社區活動流程候選，讓志工逐項核對。"></textarea>
<div id="input-boundary" class="privacy"><span>請勿輸入姓名或聯絡方式</span><span>請勿輸入密碼或 token</span><span>請勿貼上付款資料</span><span>請勿上傳原始私密影音</span></div>
<div class="actions"><button id="start" type="button">建立 L3 候選</button><button id="reset" class="secondary" type="button">重新開始</button></div><div id="message" class="status" role="status" aria-live="polite">等待你描述需求；目前尚未送出任何資料。</div>
<div id="guided" class="guided-card" hidden><div class="guided-head"><div><p id="question-kicker" class="small">STEP 02 · 一次一題</p><h2 id="question-label"></h2></div><span id="question-id" class="question-id"></span></div><p id="reason" class="small"></p><div id="options" aria-label="安全選項"></div><label for="answer">你的回答</label><input id="answer" maxlength="500" autocomplete="off" aria-describedby="reason"><button id="continue" class="secondary" type="button">回答並續接同一意圖</button></div>
</section>
<section class="panel" aria-labelledby="preview-title"><p class="small">STEP 03 · 人先看懂再決定</p><h2 id="preview-title">總場候選工作台</h2><p class="small">先看人類摘要，再展開技術封包。伺服器沒有模型或正式交易權。</p><div class="system-strip" aria-label="運行邊界狀態"><div class="system-state"><strong>使用者設備</strong><span>理解／確認</span></div><div class="system-state"><strong>伺服器總場</strong><span>查表／驗證／封印</span></div><div id="d8-state" class="system-state"><strong>D8 狀態</strong><span>尚未裁決</span></div></div><div id="empty-result" class="empty"><div><span class="empty-mark" aria-hidden="true">8D</span><h3>候選會在這裡逐層展開</h3><p>先看到目的、證據、風險與權限邊界，不只是一大段 JSON。</p></div></div><div id="candidate" class="candidate" hidden><div class="candidate-summary"><div class="result-card"><strong>你要的結果</strong><span id="result-intent"></span></div><div class="result-card"><strong>服務場域</strong><span id="result-profile"></span></div><div class="result-card"><strong>總場風險狀態</strong><span id="result-risk"></span></div><div class="result-card"><strong>D8 候選裁決</strong><span id="result-d8"></span></div></div><div id="dimension-grid" class="dimensions" aria-label="D1至D8候選摘要"></div><div class="evidence-risk"><section aria-labelledby="evidence-title"><h3 id="evidence-title">證據引用</h3><ul id="evidence-list"></ul></section><section aria-labelledby="risk-title"><h3 id="risk-title">風險與阻擋</h3><ul id="risk-list"></ul></section></div><div class="result-card"><strong>內容封印 SHA-256</strong><span id="content-hash" class="hash"></span></div><details><summary>技術人員：展開完整 D1–D8 封包</summary><pre id="preview" tabindex="0">尚無候選。</pre></details></div></section>
</div>
<section id="nodes" class="panel nodes" aria-labelledby="nodes-title"><p class="small">READ-ONLY CAPABILITY VIEW</p><h2 id="nodes-title">總場、節點與容器可用狀態</h2><p id="node-status" class="small">正在讀取遮蔽後的節點與容器狀態；不顯示帳號、IP 或秘密。</p><div id="node-grid" class="node-grid" aria-live="polite"></div></section>
<section class="truth" aria-label="產品真實邊界"><article><b>生成式傳輸</b><span>協定原生 8D 意圖場封包，不是檔案搬運。</span></article><article><b>離線能力</b><span>設備保留候選；總場恢復後重驗與去重。</span></article><article><b>正式權限</b><span>所有 AI 與節點都只有候選權，不能自設 D8。</span></article><article><b>公益定位</b><span>研究展示、不募款、婉謝捐款，以科技服務社區。</span></article></section>
</main><footer class="footer"><div><span>五常社區發展協會 · AI 影音小J · 總場候選治理</span><span>LLM_INFERENCE=USER_DEVICE_ONLY · SERVER_LLM=BLOCK</span></div></footer>
<script>
const $=id=>document.getElementById(id);const PROFILE_LABELS={GENERIC:'一般需求',ASSOCIATION:'社區服務與志工協作',PROPERTY:'物業設備與檢查',CAFE_POS:'商家商品候選',HOUSEHOLD:'日常提醒與照護'};const REDTEAM_CLIENT_RULES=__REDTEAM_CLIENT_RULES__;const REDTEAM_LABELS={GT_CORE_DEFINITION_DRIFT:'生成式傳輸技術定義發生飄移',TOTAL_FIELD_AUTHORITY_DRIFT:'企圖繞過總場或人工裁決',SERVER_LLM_BOUNDARY_DRIFT:'企圖把 LLM 移到伺服器執行',UNSAFE_SIDE_EFFECT_DRIFT:'要求未經確認的正式副作用',PUBLIC_TRUST_OVERCLAIM_DRIFT:'對外信任主張超過現有證據',SENSITIVE_DATA_BOUNDARY_ALERT:'輸入疑似包含敏感資料',AUTHORITY_FIELD_ESCALATION_ALERT:'輸入企圖攜帶正式權限欄位'};let intent={},guided=null,busy=false;
function setBusy(value){busy=value;$('start').disabled=value;$('continue').disabled=value;$('workspace').setAttribute('aria-busy',String(value));if(value){$('message').textContent='總場正在查表並驗證候選，請稍候。'}}
function setJourney(stage){const ids=['step-intent','step-guide','step-candidate'];const index=ids.indexOf(stage);ids.forEach((id,i)=>{$(id).className=i<index?'done':i===index?'active':''})}
function setMessage(text,hold=false){$('message').textContent=text;$('message').className=hold?'status hold':'status'}
function localRedteam(text){const folded=String(text||'').toLocaleLowerCase();const alerts=[];REDTEAM_CLIENT_RULES.forEach(rule=>{if(rule.markers.some(marker=>folded.includes(marker.toLocaleLowerCase())))alerts.push({code:rule.code,severity:rule.severity})});if(/(?:[\\w.+-]+@[\\w.-]+\\.[a-z]{2,}|\\bbearer\\s+[a-z0-9._~-]{8,}|-----begin [a-z ]*private key-----)/i.test(folded))alerts.push({code:'SENSITIVE_DATA_BOUNDARY_ALERT',severity:'CRITICAL'});return{status:alerts.length?'DRIFT_ALERT':'MONITORING_CLEAR',alert_count:alerts.length,alerts,llm_execution:'NONE_DETERMINISTIC_RULES'}}
function renderRedteam(monitor,source='裝置端即時預警'){const safe=monitor||localRedteam('');const alert=safe.status==='DRIFT_ALERT'||Number(safe.alert_count)>0;const root=$('redteam-monitor');root.dataset.state=alert?'DRIFT_ALERT':'MONITORING_CLEAR';$('redteam-state').textContent=alert?`紅隊飄移告警 · ${safe.alert_count} 項`:'常駐紅隊觀點監看中';$('redteam-detail').textContent=alert?`${source}已停止候選續接；請移除飄移後再由總場審查。`:`${source}正常；規則持續監看技術定義、總場權限、裝置端 LLM、個資與對外主張。`;const list=$('drift-alerts');list.textContent='';list.hidden=!alert;(safe.alerts||[]).forEach(item=>{const li=document.createElement('li');li.textContent=`${REDTEAM_LABELS[item.code]||item.code} · ${item.severity||'HIGH'}`;list.appendChild(li)});return !alert}
function refreshDeviceRedteam(){return renderRedteam(localRedteam(`${$('intent').value}\n${$('answer').value}`))}
function suggestProfile(text){const rules=[['ASSOCIATION',/(社區|志工|活動|協會|課程)/],['PROPERTY',/(物業|設備|檢查|維修|大樓)/],['CAFE_POS',/(咖啡|商品|價格|商家|餐點)/],['HOUSEHOLD',/(提醒|家庭|日常|照護|醫囑)/]];return(rules.find(([,rule])=>rule.test(text))||['GENERIC'])[0]}
function refreshSuggestion(){const text=$('intent').value.trim();if(!text){$('profile-suggestion').hidden=true;return}const value=suggestProfile(text);$('profile-suggestion').hidden=false;$('suggested-profile').textContent=PROFILE_LABELS[value];$('apply-suggestion').dataset.profile=value}
async function api(payload){const response=await fetch('/api/intent-field',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(response.status===401){window.location.assign('/google/member/login');return null}try{return await response.json()}catch(error){return{state:'HOLD',reason_code:'AUTH_OR_GATEWAY_RESPONSE_INVALID'}}}
function humanDecision(value){return value==='PENDING_TOTAL_FIELD_REVIEW'?'待總場審查':value||'候選待審'}
function humanRisk(value){return value==='CLEAR_PRELIMINARY'?'初步清晰，仍待人工核對':value||'待核對'}
function describe(key,value){let summary='已建立';if(key==='D1')summary=value.requested_result||value.intent||summary;if(key==='D2')summary=value.state||summary;if(key==='D3')summary=value.destination_field||summary;if(key==='D4')summary=value.capability_ref||summary;if(key==='D5')summary=value.candidate_only?'僅建立候選':summary;if(key==='D6')summary=value.reconstruction_conditions?.equivalence_level||summary;if(key==='D7')summary=humanRisk(value.risk_status);if(key==='D8')summary=humanDecision(value.decision);return String(summary)}
function addItems(root,values,emptyText){root.textContent='';(values.filter(Boolean).length?values.filter(Boolean):[emptyText]).forEach(value=>{const li=document.createElement('li');li.textContent=String(value);root.appendChild(li)})}
function renderCandidate(result){guided=null;$('guided').hidden=true;$('empty-result').hidden=true;$('candidate').hidden=false;$('result-intent').textContent=result.D1?.requested_result||'待人工核對';$('result-profile').textContent=PROFILE_LABELS[result.profile]||result.profile;$('result-risk').textContent=humanRisk(result.D7?.risk_status);$('result-d8').textContent=humanDecision(result.D8?.decision);$('d8-state').querySelector('span').textContent=humanDecision(result.D8?.decision);$('content-hash').textContent=result.content_sha256||'';$('preview').textContent=JSON.stringify(result,null,2);const labels={D1:'目的',D2:'目前狀態',D3:'場域座標',D4:'能力與證據',D5:'執行邊界',D6:'生成式傳輸',D7:'風險阻擋',D8:'裁決封套'};const grid=$('dimension-grid');grid.textContent='';Object.keys(labels).forEach(key=>{const card=document.createElement('article');card.className='dimension';const strong=document.createElement('strong');strong.textContent=`${key} · ${labels[key]}`;const span=document.createElement('span');span.textContent=describe(key,result[key]||{});card.append(strong,span);grid.appendChild(card)});const evidence=[...(result.D4?.source_refs||[]),...Object.entries(result.D4?.source_snapshot||{}).map(([key,value])=>`${key}: ${value}`)];addItems($('evidence-list'),evidence,'沒有可驗證證據');addItems($('risk-list'),Object.entries(result.D7||{}).map(([key,value])=>`${key}: ${value}`),'尚無風險資料');setJourney('step-candidate');setMessage('L3 候選已建立；請核對目的、證據、風險與 D8 邊界。')}
function renderGuided(result){guided=result;$('guided').hidden=false;$('guided').dataset.field=result.question.field;$('candidate').hidden=true;$('empty-result').hidden=false;$('question-label').textContent=result.question.prompt;$('question-kicker').textContent=`STEP 02 · 尚需 ${result.remaining_field_count} 個最小欄位`;$('question-id').textContent=result.question.question_id;$('reason').textContent=result.question.reason;$('options').textContent='';result.question.options.forEach(value=>{const button=document.createElement('button');button.type='button';button.className='secondary option';button.textContent=value;button.setAttribute('aria-pressed','false');button.onclick=()=>{[...$('options').children].forEach(item=>item.setAttribute('aria-pressed','false'));button.setAttribute('aria-pressed','true');$('answer').value=value;$('answer').focus()};$('options').appendChild(button)});setJourney('step-guide');setMessage(`只差 ${result.remaining_field_count} 個必要欄位；每次只問一題。`);$('answer').focus()}
function show(result){renderRedteam(result.redteam_drift_monitor,'總場確定性規則重驗');if(result.state==='HOLD_DETOUR_ALERT'||result.redteam_drift_monitor?.status==='DRIFT_ALERT'){$('guided').hidden=true;$('candidate').hidden=true;$('empty-result').hidden=false;$('d8-state').querySelector('span').textContent='HOLD_DETOUR_ALERT';setMessage('紅隊偵測到飄移，已停止候選續接並交回總場審查。',true);return}if(result.state==='NEEDS_USER_GUIDED_COMPLETION'){renderGuided(result);return}if(result.content_sha256){renderCandidate(result);return}$('guided').hidden=true;$('d8-state').querySelector('span').textContent='HOLD';setMessage(`已安全拒絕：${result.reason_code||'UNKNOWN_BOUNDARY'}`,true)}
$('intent').addEventListener('input',()=>{refreshSuggestion();refreshDeviceRedteam()});$('answer').addEventListener('input',refreshDeviceRedteam);$('apply-suggestion').onclick=()=>{$('profile').value=$('apply-suggestion').dataset.profile;setMessage(`已採用「${PROFILE_LABELS[$('profile').value]}」場域建議，仍可自行更改。`)};
$('start').onclick=async()=>{if(busy)return;const requested=$('intent').value.trim();if(!requested){setMessage('請先用一句話描述希望得到的結果。',true);$('intent').focus();return}if(!refreshDeviceRedteam()){setMessage('裝置端紅隊已停止送出；請先移除飄移或敏感內容。',true);return}intent={requested_result:requested};guided=null;$('candidate').hidden=true;$('empty-result').hidden=false;setJourney('step-intent');setBusy(true);try{const result=await api({profile:$('profile').value,intent});if(result)show(result)}catch(error){setMessage('服務暫時無法回應；沒有建立候選或正式交易。',true)}finally{setBusy(false)}};
$('continue').onclick=async()=>{if(busy||!guided)return;const answer=$('answer').value.trim();if(!answer){setMessage('請選擇安全選項或輸入回答。',true);$('answer').focus();return}if(!refreshDeviceRedteam()){setMessage('裝置端紅隊已停止續接；請先移除飄移或敏感內容。',true);return}const current=guided;setBusy(true);try{const result=await api({profile:$('profile').value,intent,state_id:current.state_id,question_id:current.question.question_id,answer});if(!result)return;if(result.state!=='HOLD_DETOUR_ALERT'&&result.redteam_drift_monitor?.status!=='DRIFT_ALERT'&&(result.state==='NEEDS_USER_GUIDED_COMPLETION'||result.content_sha256))intent[current.question.field]=answer;$('answer').value='';show(result)}catch(error){setMessage('續接失敗；原意圖未被修改，請稍後再試。',true)}finally{setBusy(false)}};
$('reset').onclick=()=>{intent={};guided=null;$('intent').value='';$('answer').value='';$('profile').value='GENERIC';$('profile-suggestion').hidden=true;$('guided').hidden=true;$('candidate').hidden=true;$('empty-result').hidden=false;$('d8-state').querySelector('span').textContent='尚未裁決';setJourney('step-intent');renderRedteam(localRedteam(''));setMessage('已清除本頁候選；目前尚未送出任何資料。');$('intent').focus()};
function renderNodes(result){$('node-status').textContent=result.summary||'節點與容器狀態暫不可用。';const grid=$('node-grid');grid.textContent='';(result.nodes||[]).forEach(node=>{const card=document.createElement('article');card.className='node';const name=document.createElement('strong');name.textContent=node.node_id||'SANITIZED_NODE';const detail=document.createElement('span');detail.textContent=`節點 · ${node.os||'OS 未知'} · CPU ${node.cpu||'待驗證'} · GPU ${node.gpu||'待驗證'}`;const state=document.createElement('span');state.className='node-state'+(node.base_transport_state==='INSTALLED_USABLE'?' usable':'');state.textContent=node.base_transport_state||'UNVERIFIED';card.append(name,detail,state);grid.appendChild(card)});(result.containers||[]).forEach(container=>{const card=document.createElement('article');card.className='node';const name=document.createElement('strong');name.textContent=container.name||container.container_ref||'SANITIZED_CONTAINER';const detail=document.createElement('span');detail.textContent=`容器 · ${container.image||'映像待分類'} · ${container.role||'角色待分類'}`;const state=document.createElement('span');state.className='node-state'+(container.runtime_state==='RUNNING'?' usable':'');state.textContent=`${container.runtime_state||'UNKNOWN'} · 總場唯讀納管`;card.append(name,detail,state);grid.appendChild(card)});grid.dataset.nodeCount=String((result.nodes||[]).length);grid.dataset.containerCount=String((result.containers||[]).length)}
fetch('/api/nodes').then(r=>r.json()).then(renderNodes).catch(()=>{$('node-status').textContent='節點狀態暫不可用；不影響本頁離線整理需求。'});
</script></body></html>"""

PRODUCT_HTML = PRODUCT_HTML.replace(
    "__REDTEAM_CLIENT_RULES__",
    json.dumps(client_drift_rules(), ensure_ascii=False, separators=(",", ":")),
)

PRODUCT_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-labelledby="title"><title id="title">AI 影音小J總場</title><rect width="64" height="64" rx="18" fill="#0b6b61"/><path d="M18 17h28v7H36v8h8v7h-8v9h-8v-9h-8v-7h8v-8H18z" fill="#e9fff8"/><circle cx="49" cy="15" r="6" fill="#fbbf24"/></svg>"""


def health_payload() -> dict[str, Any]:
    return {"state": "PASS", "service": "W7TP_SHARED_INTENT_FIELD", "candidate_only": True}


def ready_payload() -> dict[str, Any]:
    return {"state": "PASS", "authoritative_sources": "READABLE", "shared_runtime": True}


def capabilities_payload() -> dict[str, Any]:
    return {
        "state": "PASS",
        "profiles": {key: value.packet_type for key, value in CONTRACTS.items()},
        "formal_execution": False,
        "llm_execution": device_llm_execution_policy(),
        "redteam_drift_monitor": {
            "mode": "ALWAYS_ON_EVERY_STATE_TRANSITION",
            "llm_execution": "NONE_DETERMINISTIC_RULES",
            "decision_authority": "LOCAL_TOTAL_FIELD_ONLY",
        },
        "natural_person_identity_prefix": {
            "one_natural_person_one_dedicated_packet": True,
            "device_and_social_accounts_are_bindings": True,
            "plaintext_identity_visible": False,
            "position": "SYSTEM_IMMUTABLE_PREFIX",
            "llm_mutable": False,
            "llm_writable_region": "CANDIDATE_BODY_ONLY",
            "http_body_prefix_accepted": False,
            "trusted_gateway_injection_required": True,
            "trusted_gateway_binding_state": "NOT_YET_EVIDENCED",
            "trusted_gateway_source_state": "SOURCE_INTERFACE_LANDED_NOT_DEPLOYED",
        },
    }


def node_payload() -> dict[str, Any]:
    try:
        inventory = collect_inventory(probe=False)
    except FieldApplicationError as exc:
        inventory = {"state": "HOLD", "reason_code": exc.reason_code, "nodes": []}
    nodes = inventory.get("nodes", [])
    containers = inventory.get("containers", [])
    usable = sum(1 for node in nodes if node.get("base_transport_state") == "INSTALLED_USABLE")
    return {
        "state": inventory.get("state"),
        "scope": inventory.get("scope", "ALL_NODES_AND_CONTAINERS"),
        "runtime_mutation_authority": False,
        "summary": f"{len(nodes)} 節點、{len(containers)} 容器已納入總場唯讀盤點；{usable} 節點基礎程式可用，IP 與帳號已遮蔽。",
        "nodes": nodes,
        "containers": containers,
    }


def _validated_cafe_pos_receiver_context(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise FieldApplicationError(
            "CAFE_POS_RECEIVER_CONTEXT_REQUIRED", "$.receiver_context"
        )
    context = dict(value)
    if frozenset(context) != CAFE_POS_RECEIVER_CONTEXT_KEYS:
        raise FieldApplicationError(
            "CAFE_POS_RECEIVER_CONTEXT_INVALID", "$.receiver_context"
        )
    request_id = context.get("request_id")
    caller_ref = context.get("caller_ref")
    observation_domain_ref = context.get("observation_domain_ref")
    if not CAFE_POS_REQUEST_ID_PATTERN.fullmatch(str(request_id or "")):
        raise FieldApplicationError(
            "CAFE_POS_REQUEST_ID_INVALID", "$.receiver_context.request_id"
        )
    for field_name, field_value in (
        ("caller_ref", caller_ref),
        ("observation_domain_ref", observation_domain_ref),
    ):
        if not OPAQUE_REF_PATTERN.fullmatch(str(field_value or "")):
            raise FieldApplicationError(
                "CAFE_POS_OPAQUE_REF_INVALID",
                f"$.receiver_context.{field_name}",
            )
    if context.get("receiver_ref") != CAFE_POS_TOTAL_FIELD_RECEIVER_REF:
        raise FieldApplicationError(
            "CAFE_POS_RECEIVER_REF_INVALID", "$.receiver_context.receiver_ref"
        )
    if context.get("merchant_mode") != INDEPENDENT_MERCHANT_MODE:
        raise FieldApplicationError(
            "CAFE_POS_MERCHANT_MODE_INVALID", "$.receiver_context.merchant_mode"
        )
    for field_name in INDEPENDENT_MERCHANT_FALSE_FLAGS:
        if context.get(field_name) is not False:
            raise FieldApplicationError(
                "CAFE_POS_COMMUNITY_VALUE_BOUNDARY_REQUIRED",
                f"$.receiver_context.{field_name}",
            )
    return context


def _cafe_pos_reference_only_fields(
    result: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        "D1": {"intent_ref": f"sha256:{result['D2']['intent_sha256']}"},
        "D2": {"state_ref": f"sha256:{result['D2']['intent_state_id']}"},
        "D3": {
            "node_ref": result["D3"]["node_ref"],
            "routing_ref": result["D3"]["scenario_ref"],
        },
        "D4": {"evidence_ref": f"sha256:{result['content_sha256']}"},
        "D5": {"execution_ref": "execution:cafe-pos-candidate-only"},
        "D6": {"privacy_boundary_ref": "privacy:reference-only"},
        "D7": {
            "capability_ref": result["D4"]["capability_ref"],
            "routing_ref": result["D3"]["scenario_ref"],
            "reconstruction_condition": "L3_CANDIDATE_LOCAL_STATE_MACHINE",
        },
        "D8": {
            "adjudication_policy_ref": "priority/tfct/candidate/v0_1"
        },
    }


def _cafe_pos_gateway_request(
    result: Mapping[str, Any], context: Mapping[str, Any]
) -> dict[str, Any]:
    request_id = str(context["request_id"])
    resolved_fields = _cafe_pos_reference_only_fields(result)
    return {
        "profile_schema_version": "8d-gte-runtime-candidate-profile/0.1",
        "profile_type": "RUNTIME_REQUEST",
        "gte": {
            "schema_version": "8d-gte-candidate/0.1",
            "lifecycle": "CANDIDATE",
            "event_ref": request_id,
            "observation_domain_ref": context["observation_domain_ref"],
            "dimensions": {
                f"D{index}_ref": f"field/tfct/D{index}/v0_1"
                for index in range(1, 9)
            },
            "constraint_hypergraph_ref": "constraints/tfct/runtime-hypergraph/v0_1",
            "convergence_operator_ref": "convergence/tfct/finite-fixed-point/v0_1",
            "priority_policy_ref": "priority/tfct/candidate/v0_1",
            "fixed_point_status": "PENDING",
            "verification": {
                "final_decision": "PENDING",
                "commit_applied": False,
            },
            "tfs_result": None,
        },
        "source_mode": "TOTAL_FIELD_PULL",
        "event": {
            "event_id": request_id,
            "event_ref": request_id,
            "event_code": "STATE_UPDATE",
            "logical_time": request_id,
        },
        "rule_set_ref": "rules/tfct/identity_v0_1",
        "resolved_fields": resolved_fields,
        "context": {
            "request_ref": request_id,
            "caller_ref": context["caller_ref"],
            "merchant_mode": context["merchant_mode"],
            **{
                field: context[field]
                for field in INDEPENDENT_MERCHANT_FALSE_FLAGS
            },
        },
        "adi_requested": False,
    }


def _attach_cafe_pos_total_field_receipt(
    result: dict[str, Any], context: Mapping[str, Any]
) -> None:
    request_id = str(context["request_id"])
    gateway_request = _cafe_pos_gateway_request(result, context)
    gateway_result = receive_candidate(
        gateway_request,
        previous_state=gateway_request["resolved_fields"],
        observation_domains={},
    )
    d3_transition = gateway_result.get("d3_transition")
    d3_event_id = (
        d3_transition.get("event_id")
        if isinstance(d3_transition, Mapping)
        else None
    )
    same_request_id_chain = (
        gateway_result.get("event_ref") == request_id
        and gateway_result.get("gte", {}).get("event_ref") == request_id
        and d3_event_id == request_id
        and gateway_request["context"]["request_ref"] == request_id
    )
    if not same_request_id_chain:
        raise FieldApplicationError("TOTAL_FIELD_REQUEST_ID_CHAIN_MISMATCH")
    receipt = {
        "schema_version": "w7tp.odoo-cafe-total-field-receipt.v1",
        "receipt_state": "PASS",
        "request_id": request_id,
        "caller_ref": context["caller_ref"],
        "receiver": CAFE_POS_TOTAL_FIELD_RECEIVER,
        "receiver_ref": CAFE_POS_TOTAL_FIELD_RECEIVER_REF,
        "event_ref": gateway_result["event_ref"],
        "d3_event_id": d3_event_id,
        "same_request_id_chain": True,
        "total_field_decision": gateway_result["final_decision"],
        "decision_reason_codes": gateway_result["decision_reason_codes"],
        "fixed_point_status": gateway_result["fixed_point_status"],
        "commit_applied": gateway_result["commit_applied"],
        "state_ref": gateway_result["state_ref"],
        "tfid": gateway_result["tfid"],
        "total_field_hash": gateway_result["total_field_hash"],
        "gte_lifecycle": gateway_result["gte"]["lifecycle"],
        "gateway_result_sha256": canonical_sha256(gateway_result),
        "observation_domain_bound": False,
        "candidate_runtime_only": True,
        "real_order_created": False,
        "payment_transaction": False,
        "invoice_created": False,
        "member_plaintext": False,
        "canonical_write": False,
        "community_happiness_coin_accepted": False,
        "consumer_happiness_coin_issued": False,
        "community_merchant_ticket_quota": False,
        "fund_1_to_1_to_1_binding": False,
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    execution_metadata = result.setdefault("execution_metadata", {})
    execution_metadata.update(
        {
            "request_id": request_id,
            "caller_ref": context["caller_ref"],
            "total_field_receipt": receipt,
        }
    )


def _projection_http_status(reason_code: str) -> int:
    if reason_code in {
        "IDENTITY_PROJECTION_UNTRUSTED_SOURCE",
        "IDENTITY_PROJECTION_HEADER_REQUIRED",
        "IDENTITY_PROJECTION_EXPIRED",
        "IDENTITY_PROJECTION_NOT_YET_VALID",
    }:
        return 401
    if reason_code in {
        "IDENTITY_PREFIX_RESOLVER_REQUIRED",
        "IDENTITY_PREFIX_NOT_FOUND",
        "IDENTITY_PREFIX_REGISTRY_EVIDENCE_REQUIRED",
    }:
        return 503
    if reason_code in {
        "HOLD_IDENTITY_PREFIX_CONFLICT",
        "HOLD_IDENTITY_PACKET_CONFLICT",
    }:
        return 409
    return 422


def process_http_request(
    payload: bytes,
    *,
    trusted_identity_projection_headers: Mapping[str, Any] | None = None,
    trusted_boundary: bool = False,
    identity_prefix_resolver: IdentityPrefixResolver | None = None,
    identity_registry_snapshot: Mapping[str, Any] | None = None,
    projection_now: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Process one shared API request without owning a second HTTP server."""

    if len(payload) < 2 or len(payload) > MAX_REQUEST_BYTES:
        return 400, {"state": "HOLD", "reason_code": "REQUEST_SIZE_INVALID"}
    redteam_monitor = evaluate_drift({})
    projection_verification: dict[str, Any] | None = None
    try:
        if trusted_identity_projection_headers is not None or trusted_boundary:
            projection_verification = verify_trusted_identity_projection(
                trusted_identity_projection_headers or {},
                trusted_boundary=trusted_boundary,
                identity_prefix_resolver=identity_prefix_resolver,
                identity_registry_snapshot=identity_registry_snapshot,
                now=projection_now,
            )
        request = json.loads(payload)
        if not isinstance(request, dict) or not isinstance(request.get("intent"), dict):
            raise FieldApplicationError("INTENT_OBJECT_REQUIRED")
        assert_llm_candidate_does_not_mutate_identity(request)
        redteam_monitor = evaluate_drift(
            {"intent": request["intent"], "answer": request.get("answer")}
        )
        result = process_intent(
            str(request.get("profile") or ""),
            request["intent"],
            state_id=request.get("state_id"),
            question_id=request.get("question_id"),
            answer=request.get("answer"),
            execution_metadata={
                "surface": "EXISTING_INTENT_SERVICE_9107",
                "llm_inference_location": "USER_DEVICE_ONLY",
                "server_llm_execution": "BLOCK",
                **(
                    {
                        "identity_projection_state": projection_verification["state"],
                        "identity_projection_ref": projection_verification[
                            "projection"
                        ]["projection_ref"],
                        "identity_projection_sha256": projection_verification[
                            "projection"
                        ]["projection_sha256"],
                        "identity_projection_issuer_ref": projection_verification[
                            "projection"
                        ]["issuer_ref"],
                    }
                    if projection_verification is not None
                    else {}
                ),
            },
            trusted_identity_prefix=(
                projection_verification["identity_prefix"]
                if projection_verification is not None
                else None
            ),
            identity_registry_snapshot=(
                projection_verification["identity_registry_snapshot"]
                if projection_verification is not None
                else None
            ),
        )
        receiver_context = request.get("receiver_context")
        if receiver_context is not None:
            if request.get("profile") != "CAFE_POS":
                raise FieldApplicationError(
                    "TOTAL_FIELD_RECEIVER_CAFE_POS_ONLY", "$.receiver_context"
                )
            if (
                result.get("D8", {}).get("decision")
                != "PENDING_TOTAL_FIELD_REVIEW"
                or not result.get("content_sha256")
            ):
                raise FieldApplicationError(
                    "CAFE_POS_COMPLETE_CANDIDATE_REQUIRED",
                    "$.receiver_context",
                )
            _attach_cafe_pos_total_field_receipt(
                result,
                _validated_cafe_pos_receiver_context(receiver_context),
            )
    except FieldApplicationError as exc:
        status = (
            _projection_http_status(exc.reason_code)
            if exc.reason_code.startswith("IDENTITY_")
            or exc.reason_code.startswith("HOLD_IDENTITY_")
            else 422
        )
        return status, {
            "state": "HOLD",
            "reason_code": exc.reason_code,
            "path": exc.path,
            "candidate_only": True,
            "redteam_drift_monitor": redteam_monitor,
        }
    except (TotalFieldGatewayError, RuntimeCandidateError) as exc:
        return 422, {
            "state": "HOLD",
            "reason_code": exc.reason_code,
            "path": getattr(exc, "path", "$"),
            "candidate_only": True,
            "redteam_drift_monitor": redteam_monitor,
        }
    except (ValueError, json.JSONDecodeError):
        return 400, {"state": "HOLD", "reason_code": "REQUEST_JSON_INVALID"}
    return 200, result
