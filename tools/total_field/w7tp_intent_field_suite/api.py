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
:root{color-scheme:light;--canvas:#f2f6f4;--surface:#fff;--surface-soft:#edf7f4;--ink:#173042;--muted:#5b6d78;--brand:#087f70;--brand-deep:#075e55;--accent:#f4b63e;--line:#cbdad6;--focus:#bf5b08;--danger:#b4233e}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:1rem}body{margin:0;background:radial-gradient(circle at 85% 0,#d8eee8 0,transparent 28rem),var(--canvas);color:var(--ink);font:17px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{width:min(1120px,94vw);margin:auto;padding:1.25rem 0 4rem}.hero,.panel{background:var(--surface);border:1px solid var(--line);border-radius:24px;padding:clamp(1.1rem,3vw,2rem);box-shadow:0 16px 38px #163a3014}.hero{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(17rem,.75fr);gap:clamp(1.2rem,3vw,2.4rem);align-items:center;margin-bottom:1rem;background:linear-gradient(135deg,#075e55,#0b3f4d);color:#fff;border:0;box-shadow:0 20px 52px #083e3638}
h1{font-size:clamp(2.15rem,5vw,4.4rem);line-height:1.05;letter-spacing:-.04em;margin:.25rem 0 1rem}h2,h3{line-height:1.25}h2{margin:.15rem 0 .5rem;font-size:clamp(1.45rem,2.8vw,2rem)}h3{margin:.3rem 0}.lead{font-size:clamp(1.05rem,2vw,1.28rem);color:#e8fff9;margin:.5rem 0}.small{font-size:.86rem;color:var(--muted)}.eyebrow{margin:0 0 .35rem;color:var(--brand);font-size:.76rem;font-weight:900;letter-spacing:.08em;text-transform:uppercase}.hero .eyebrow{color:#bff6e8}
label{display:block;font-weight:800;margin:1rem 0 .4rem}select,textarea,input,button{font:inherit}select,textarea,input{width:100%;color:var(--ink);background:#fff;border:2px solid #9dbab3;border-radius:14px;padding:.82rem}textarea{min-height:10rem;resize:vertical}select:hover,textarea:hover,input:hover{border-color:#5c9388}
button,.button-link{display:inline-flex;align-items:center;justify-content:center;min-height:46px;border:0;border-radius:999px;padding:.72rem 1.15rem;font-weight:850;background:var(--brand);color:#fff;cursor:pointer;text-decoration:none}button.secondary,.button-link.secondary{background:#e3efec;color:var(--brand-deep)}button.ghost{background:#fff;color:var(--brand-deep);border:1px solid var(--line)}button:hover,.button-link:hover{filter:brightness(.96)}button:focus-visible,.button-link:focus-visible,select:focus-visible,textarea:focus-visible,input:focus-visible,summary:focus-visible,[tabindex="-1"]:focus-visible{outline:4px solid var(--focus);outline-offset:3px}
.hero-actions{display:flex;flex-wrap:wrap;gap:.6rem;margin:1.1rem 0 .55rem}.hero-actions .button-link{background:var(--accent);color:#2f240b}.hero-actions .text-link{display:inline-flex;align-items:center;min-height:46px;color:#e8fff9;font-weight:800}.hero-note{font-size:.82rem;color:#c9e9e2;margin:.35rem 0 0}.quick-flow{list-style:none;padding:1rem;margin:0;display:grid;gap:.65rem;background:#ffffff12;border:1px solid #ffffff32;border-radius:18px}.quick-flow li{display:grid;grid-template-columns:2.25rem 1fr;gap:.65rem;align-items:center}.quick-flow b{display:grid;place-items:center;width:2.25rem;height:2.25rem;border-radius:50%;background:#fff;color:var(--brand-deep)}.quick-flow strong,.quick-flow span{display:block}.quick-flow span{font-size:.78rem;color:#d7f3ec}
.grid{display:grid;grid-template-columns:minmax(0,1.17fr) minmax(0,.83fr);gap:1rem;align-items:start}.workspace-intro{grid-column:1/-1;display:flex;justify-content:space-between;align-items:end;gap:1.2rem;padding:.25rem .2rem}.workspace-intro p{margin:.25rem 0}.input-panel{border-top:6px solid var(--brand)}.preview-panel{border-top:6px solid #b9cbc7;position:sticky;top:1rem}.status{padding:.72rem .85rem;border-left:5px solid var(--brand);background:var(--surface-soft);margin:.8rem 0;border-radius:.65rem;color:#31564f}.hold{border-color:var(--danger);background:#fff0f2;color:#7e1f33}pre{white-space:pre-wrap;word-break:break-word;background:#102b35;color:#eafff9;padding:1rem;border-radius:12px;max-height:36rem;overflow:auto}
.skip{position:fixed;top:-5rem;left:1rem;z-index:20;background:#fff;color:var(--ink);padding:.7rem 1rem;border-radius:.7rem}.skip:focus{top:1rem}.topbar{width:min(1120px,94vw);margin:auto;display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:.75rem 0}.brand{display:flex;align-items:center;gap:.55rem;color:var(--ink);text-decoration:none;font-weight:900}.brand-mark{display:grid;place-items:center;width:2.65rem;height:2.65rem;border-radius:.85rem;background:var(--brand);color:#fff}.topbar nav{display:flex;gap:.45rem}.topbar nav a{display:inline-flex;align-items:center;min-height:44px;padding:0 .55rem;color:var(--brand-deep);font-weight:800}
.journey{display:grid;grid-template-columns:repeat(3,minmax(6rem,1fr));gap:.4rem;padding:0;margin:0;list-style:none;min-width:min(100%,24rem)}.journey li{padding:.55rem;border-radius:.75rem;background:#e6eeec;color:#697b78;text-align:center;font-size:.75rem;font-weight:850}.journey li.active{background:#fff0c7;color:#6a4800}.journey li.done{background:#d8f2eb;color:#075e55}.field-hint{margin:.2rem 0 .65rem;color:var(--muted);font-size:.82rem}.field-error{margin:.35rem 0;color:var(--danger);font-weight:800}.examples{display:flex;align-items:center;flex-wrap:wrap;gap:.45rem;margin:.65rem 0}.examples>span{font-size:.78rem;color:var(--muted);font-weight:800}.example{min-height:38px;padding:.42rem .72rem;background:#eef4f2;color:var(--brand-deep);border:1px solid var(--line);font-size:.78rem}.suggestion{display:flex;justify-content:space-between;align-items:center;gap:.7rem;padding:.7rem;margin:.65rem 0;border:1px dashed #6d9e94;border-radius:.85rem;background:var(--surface-soft)}.suggestion p{margin:0}.privacy-note{margin:.8rem 0;padding:.7rem .8rem;border-radius:.75rem;background:#f5f7f6;color:#50625f;font-size:.78rem}.actions{display:flex;flex-wrap:wrap;gap:.55rem;margin-top:.7rem}.actions button{margin:0}.guided-card{margin-top:1rem;padding:1rem;border:2px solid #e1b54e;border-radius:1rem;background:#fffaf0}.guided-head{display:flex;justify-content:space-between;gap:.6rem}.question-id{font:700 .7rem/1.4 ui-monospace,monospace;color:#785a12}.option{margin:.25rem .3rem .25rem 0}.option[aria-pressed="true"]{outline:3px solid var(--focus);background:#ffe8a5;color:#533b00}.system-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:.45rem;margin-bottom:1rem}.system-state{padding:.65rem;border:1px solid var(--line);border-radius:.8rem;background:#f5f8f7;min-height:4.7rem}.system-state strong,.system-state span{display:block}.system-state strong{font-size:.68rem;color:#647b76}.system-state span{font-size:.78rem;font-weight:850}.empty{display:grid;place-items:center;min-height:15rem;text-align:center;border:1px dashed #95b5ae;border-radius:1rem;color:var(--muted);padding:1rem;background:#fbfdfc}.empty-mark{display:grid;place-items:center;width:3.6rem;height:3.6rem;margin:auto;border-radius:1.1rem;background:#d9f1eb;color:var(--brand);font-weight:950}.candidate{display:grid;gap:.7rem}.candidate-summary{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}.result-card{padding:.72rem;border:1px solid var(--line);border-radius:.8rem;background:#f7faf9}.result-card strong,.result-card span{display:block}.result-card strong{font-size:.68rem;color:#647b76}.result-card span{font-weight:850;word-break:break-word}.dimensions{display:grid;grid-template-columns:repeat(2,1fr);gap:.4rem}.dimension{padding:.65rem;border-radius:.7rem;background:#eaf4f1;min-height:5rem}.dimension strong,.dimension span{display:block}.dimension strong{font-size:.7rem;color:var(--brand-deep)}.dimension span{font-size:.7rem;word-break:break-word}.evidence-risk{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}.evidence-risk section{padding:.7rem;border:1px solid var(--line);border-radius:.8rem}.evidence-risk h3{margin:0;font-size:.95rem}.evidence-risk ul{margin:.35rem 0 0;padding-left:1.1rem;font-size:.72rem;overflow-wrap:anywhere}.candidate-next{padding:.8rem;border-radius:.85rem;background:#e8f5f1}.candidate-next p{margin:0 0 .55rem}.candidate-next .actions{margin:0}.hash{font:700 .7rem/1.5 ui-monospace,monospace;word-break:break-all}.sr-only{position:absolute!important;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
</style>
<style>
details{border:1px solid var(--line);border-radius:.8rem;background:#f7faf9}
summary{cursor:pointer;min-height:48px;padding:.65rem;font-weight:800;color:var(--brand-deep)}
.nodes{margin:1rem auto}.node-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.55rem}
.node{padding:.7rem;border:1px solid var(--line);border-radius:.8rem;background:#f7faf9}
.node strong,.node span{display:block}.node strong{overflow-wrap:anywhere}.node span{font-size:.7rem;color:#647b76}
.node .node-state{display:inline-flex;margin-top:.4rem;padding:.15rem .4rem;border-radius:999px;background:#e5ecea;color:#405552;font-weight:850}
.node .usable{background:#d8f2eb;color:#075e55}
.truth{display:grid;grid-template-columns:repeat(4,1fr);gap:.55rem;margin-top:1rem}
.truth article{padding:.8rem;border-radius:.8rem;background:#e8f2ef}.truth b,.truth span{display:block}
.truth b{font-size:.72rem;color:var(--brand-deep)}.truth span{font-size:.72rem;color:#536864}.trust-panel{display:grid;grid-template-columns:minmax(0,1fr) minmax(18rem,.8fr);gap:1rem;align-items:start;margin:1rem 0;padding:1rem;border-radius:1rem;background:#e8f2ef}.trust-panel p{margin:.25rem 0;color:#405a55;font-size:.8rem}.trust-panel details{background:#fff}
.redteam-monitor{display:grid;grid-template-columns:minmax(12rem,.34fr) 1fr;gap:.8rem;align-items:center;padding:.85rem 1rem;border:1px solid var(--line);border-radius:1rem;background:#f7faf9;margin:.8rem 0 1rem}
.redteam-monitor strong,.redteam-monitor span{display:block}.redteam-monitor .eyebrow{font-size:.68rem;color:var(--brand);font-weight:900;letter-spacing:.08em}.redteam-monitor p{margin:0;color:#60736f;font-size:.76rem}.redteam-monitor ul{margin:.35rem 0 0;padding-left:1.2rem;font-size:.75rem}.redteam-monitor[data-state="DRIFT_ALERT"]{border-color:var(--danger);background:#fff0f2}.redteam-monitor[data-state="DRIFT_ALERT"] .eyebrow{color:var(--danger)}
.footer{width:min(1120px,94vw);margin:auto;padding:0 0 2rem;color:#61736f;font-size:.72rem}
.footer div{display:flex;justify-content:space-between;gap:1rem;border-top:1px solid var(--line);padding-top:1rem}
[aria-busy="true"]{cursor:progress}[hidden]{display:none!important}
@media(max-width:900px){
  .hero,.grid{grid-template-columns:1fr}.preview-panel{position:static}.workspace-intro{align-items:flex-start}
  .dimensions,.node-grid{grid-template-columns:repeat(2,1fr)}
  .truth{grid-template-columns:repeat(2,1fr)}
}
@media(max-width:620px){
  body{font-size:16px}.topbar{gap:.35rem}.topbar .brand-label{display:none}.topbar nav{gap:0}.topbar nav a{padding:0 .4rem;font-size:.8rem}
  main{padding-top:.4rem}.hero{padding:1.1rem;border-radius:18px;gap:.8rem}.hero h1{font-size:2.15rem}.hero-actions{margin:.8rem 0 .35rem}.hero-actions .button-link{width:100%}.hero-actions .text-link{min-height:38px}.quick-flow{grid-template-columns:repeat(3,1fr);padding:.65rem;gap:.35rem}.quick-flow li{display:block;text-align:center}.quick-flow b{margin:0 auto .25rem}.quick-flow span{display:none}.quick-flow strong{font-size:.72rem}
  .workspace-intro{align-items:stretch;flex-direction:column}.journey{width:100%;min-width:0;grid-template-columns:repeat(3,1fr)}.journey li{padding:.45rem .2rem;font-size:.68rem}.panel{padding:1rem;border-radius:18px}textarea{min-height:8.5rem}.actions button{flex:1 1 9rem}.examples{align-items:stretch}.example{flex:1 1 8rem}
  .system-strip,.candidate-summary,.evidence-risk,.truth,.dimensions,.node-grid,.trust-panel{grid-template-columns:1fr}
  .suggestion,.footer div{align-items:flex-start;flex-direction:column}.suggestion button{width:100%}
  .redteam-monitor{grid-template-columns:1fr}.nodes{padding:1rem}
}
@media(prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}*,*:before,*:after{animation:none!important;transition:none!important}
}
</style>
</head>
<body><a class="skip" href="#main">跳到主要操作</a><header class="topbar"><a class="brand" href="/" aria-label="回到五常社區發展協會首頁"><span class="brand-mark" aria-hidden="true">總</span><span class="brand-label">五常社區發展協會</span></a><nav aria-label="頁面導覽"><a href="#workspace">開始測試</a><a href="#trust">資料邊界</a></nav></header><main id="main">
<section class="hero" aria-labelledby="title"><div><p class="eyebrow">AI 影音小J · 單一共用意圖場</p><h1 id="title">立即測試生成式傳輸</h1><p class="lead">聊國咖啡館老闆的私家傳輸技術，小傳輸量，可產生大檔案結果。</p><p>不用先懂 8D。先說你希望完成什麼，小J一次只問一個必要問題，再把結果整理成可核對的安全候選。</p><div class="hero-actions"><a class="button-link" href="#intent">立即測試生成式傳輸</a><a class="text-link" href="#how-it-works">先看三個步驟 ↓</a></div><p class="hero-note">免費訂閱 · 不會自動建立訂單、付款或正式執行</p></div><ol id="how-it-works" class="quick-flow" aria-label="三步完成生成式傳輸候選"><li><b>1</b><div><strong>說一句話</strong><span>描述想得到的結果</span></div></li><li><b>2</b><div><strong>回答一題</strong><span>只補不可缺的資料</span></div></li><li><b>3</b><div><strong>核對結果</strong><span>人看懂後再決定</span></div></li></ol></section>
<div id="workspace" class="grid" aria-labelledby="workspace-title">
<div class="workspace-intro"><div><p class="eyebrow">自然語言工作區</p><h2 id="workspace-title">從一句日常用語開始</h2><p class="small">下方是唯一操作入口；右側只顯示這一筆候選的核對結果。</p></div><ol class="journey" aria-label="候選建立進度"><li id="step-intent" class="active">1 描述需求</li><li id="step-guide">2 回答一題</li><li id="step-candidate">3 核對候選</li></ol></div>
<section class="panel input-panel" aria-labelledby="input-title"><p class="eyebrow">第 1 步 · 從這裡開始</p><h2 id="input-title">你希望小J幫你整理什麼？</h2><p class="field-hint">像平常說話即可，不需要輸入封包欄位或技術指令。</p>
<label for="intent">用一句話說明希望得到的結果</label><textarea id="intent" maxlength="2000" aria-describedby="input-boundary" aria-errormessage="intent-error" aria-invalid="false" placeholder="例如：幫我整理不含個資的社區活動流程，讓志工可以逐項核對。"></textarea><p id="intent-error" class="field-error" role="alert" hidden>請先用一句話描述希望得到的結果。</p>
<div class="examples" aria-label="可以直接套用的需求範例"><span>不知道怎麼寫？直接選：</span><button class="example" type="button" data-profile="ASSOCIATION" data-example="整理一份不含個資的社區活動流程，讓志工逐項核對。">社區活動流程</button><button class="example" type="button" data-profile="PROPERTY" data-example="整理公共設備檢查項目，產生只讀候選供管理人員核對。">設備檢查項目</button><button class="example" type="button" data-profile="CAFE_POS" data-example="整理咖啡館菜單查詢需求，不建立真實訂單或付款。">咖啡館菜單查詢</button></div>
<label for="profile">這次要處理哪一類？</label><p class="field-hint">不確定就保留「一般需求」，系統會在你的設備上提出建議。</p><select id="profile"><option value="GENERIC" selected>一般需求</option><option value="ASSOCIATION">社區服務與志工協作</option><option value="PROPERTY">物業設備與檢查</option><option value="CAFE_POS">商家商品候選</option><option value="HOUSEHOLD">日常提醒與照護</option></select>
<div id="profile-suggestion" class="suggestion" hidden><p><span class="small">依這句話建議的使用情境</span><br><strong id="suggested-profile"></strong></p><button id="apply-suggestion" class="secondary" type="button">採用建議</button></div>
<p id="input-boundary" class="privacy-note"><strong>送出前確認：</strong>不要輸入姓名、聯絡方式、密碼、token、付款資料或原始私密影音。</p>
<div class="actions"><button id="start" type="button">整理成安全候選</button><button id="reset" class="secondary" type="button">清除重來</button></div><div id="message" class="status" role="status" aria-live="polite">尚未送出。先在上方說一句你想完成的事。</div>
<div id="guided" class="guided-card" hidden><div class="guided-head"><div><p id="question-kicker" class="eyebrow">第 2 步 · 一次一題</p><h2 id="question-label"></h2></div><span id="question-id" class="question-id"></span></div><p id="reason" class="small"></p><div id="options" aria-label="安全選項"></div><label for="answer">你的回答</label><input id="answer" maxlength="500" autocomplete="off" aria-describedby="reason"><button id="continue" class="secondary" type="button">回答並看下一步</button><p class="field-hint">在文字欄按 Enter 也可以繼續。</p></div>
</section>
<section class="panel preview-panel" aria-labelledby="preview-title"><p id="preview-kicker" class="eyebrow">候選預覽 · 等待第 1 步</p><h2 id="preview-title" tabindex="-1">你的核對結果</h2><p class="small">先看白話摘要；只有需要時才展開技術封包。</p><div class="system-strip" aria-label="運行邊界狀態"><div class="system-state"><strong>你的設備</strong><span>理解／確認</span></div><div class="system-state"><strong>伺服器總場</strong><span>查表／驗證</span></div><div id="d8-state" class="system-state"><strong>正式權限</strong><span>尚未裁決</span></div></div><div id="empty-result" class="empty"><div><span class="empty-mark" aria-hidden="true">✓</span><h3>結果會清楚顯示在這裡</h3><p>先完成左側（手機為上方）的一句需求；系統會整理目的、證據、風險與權限邊界。</p></div></div><div id="candidate" class="candidate" hidden><div class="candidate-summary"><div class="result-card"><strong>你要的結果</strong><span id="result-intent"></span></div><div class="result-card"><strong>使用情境</strong><span id="result-profile"></span></div><div class="result-card"><strong>風險狀態</strong><span id="result-risk"></span></div><div class="result-card"><strong>候選裁決</strong><span id="result-d8"></span></div></div><div id="dimension-grid" class="dimensions" aria-label="D1至D8候選摘要"></div><div class="evidence-risk"><section aria-labelledby="evidence-title"><h3 id="evidence-title">證據引用</h3><ul id="evidence-list"></ul></section><section aria-labelledby="risk-title"><h3 id="risk-title">風險與阻擋</h3><ul id="risk-list"></ul></section></div><div class="candidate-next"><p><strong>這只是安全候選，尚未形成正式執行。</strong></p><div class="actions"><button id="edit-candidate" class="secondary" type="button">返回修改</button><button id="new-candidate" class="ghost" type="button">建立另一筆</button></div></div><div class="result-card"><strong>內容封印 SHA-256</strong><span id="content-hash" class="hash"></span></div><details><summary>技術人員：展開完整 D1–D8 封包</summary><pre id="preview" tabindex="0">尚無候選。</pre></details></div></section>
</div>
<section id="trust" class="trust-panel" aria-labelledby="trust-title"><div><p class="eyebrow">資料與權限邊界</p><h2 id="trust-title">你的原始內容不交給伺服器模型</h2><p><strong>LLM 只在使用者設備執行；本頁不在伺服器載入或執行模型。</strong></p><p>taiji01 與合作伺服器不載入模型；只接收你確認的最小意圖候選，再由總場查表、驗證與封印。所有輸出都是 L3 候選。</p></div><details><summary>需要技術細節時再展開</summary><p>伺服器不讀取原始 prompt 或模型脈絡。本頁目前只使用裝置端固定規則提出場域建議；未來接入裝置端模型時，資料仍留在使用者設備。</p></details></section>
<aside id="redteam-monitor" class="redteam-monitor" data-state="MONITORING_CLEAR" aria-label="常駐紅隊監看狀態"><span id="redteam-announcement" class="sr-only" aria-live="polite"></span><div><span class="eyebrow">ALWAYS-ON REDTEAM</span><strong id="redteam-state">常駐紅隊觀點監看中</strong></div><div><p id="redteam-detail">裝置端即時預警；每次狀態續接再由總場確定性規則重驗。兩端皆不使用伺服器 LLM。</p><ul id="drift-alerts" hidden></ul></div></aside>
<section id="nodes" class="panel nodes" aria-labelledby="nodes-title"><p class="eyebrow">技術狀態 · 選看</p><h2 id="nodes-title">總場、節點與容器可用狀態</h2><p id="node-status" class="small" role="status" aria-live="polite">正在讀取遮蔽後的節點與容器狀態；不顯示帳號、IP 或秘密。</p><div id="node-grid" class="node-grid"></div></section>
<section class="truth" aria-label="產品真實邊界"><article><b>生成式傳輸</b><span>協定原生 8D 意圖場封包，不是檔案搬運。</span></article><article><b>離線能力</b><span>設備保留候選；總場恢復後重驗與去重。</span></article><article><b>正式權限</b><span>所有 AI 與節點都只有候選權，不能自設 D8。</span></article><article><b>公益定位</b><span>研究展示、不募款、婉謝捐款，以科技服務社區。</span></article></section>
</main><footer class="footer"><div><span>五常社區發展協會 · AI 影音小J · 總場候選治理</span><span>LLM_INFERENCE=USER_DEVICE_ONLY · SERVER_LLM=BLOCK</span></div></footer>
<script>
const $=id=>document.getElementById(id);const PROFILE_LABELS={GENERIC:'一般需求',ASSOCIATION:'社區服務與志工協作',PROPERTY:'物業設備與檢查',CAFE_POS:'商家商品候選',HOUSEHOLD:'日常提醒與照護'};const REDTEAM_CLIENT_RULES=__REDTEAM_CLIENT_RULES__;const REDTEAM_LABELS={GT_CORE_DEFINITION_DRIFT:'生成式傳輸技術定義發生飄移',TOTAL_FIELD_AUTHORITY_DRIFT:'企圖繞過總場或人工裁決',SERVER_LLM_BOUNDARY_DRIFT:'企圖把 LLM 移到伺服器執行',UNSAFE_SIDE_EFFECT_DRIFT:'要求未經確認的正式副作用',PUBLIC_TRUST_OVERCLAIM_DRIFT:'對外信任主張超過現有證據',SENSITIVE_DATA_BOUNDARY_ALERT:'輸入疑似包含敏感資料',AUTHORITY_FIELD_ESCALATION_ALERT:'輸入企圖攜帶正式權限欄位'};let intent={},guided=null,busy=false;
function setBusy(value){busy=value;$('start').disabled=value;$('continue').disabled=value;$('workspace').setAttribute('aria-busy',String(value));if(value){$('message').textContent='總場正在查表並驗證候選，請稍候。'}}
function setJourney(stage){const ids=['step-intent','step-guide','step-candidate'];const index=ids.indexOf(stage);ids.forEach((id,i)=>{$(id).className=i<index?'done':i===index?'active':''})}
function setMessage(text,hold=false){$('message').textContent=text;$('message').className=hold?'status hold':'status'}
function setIntentValidity(valid){$('intent').setAttribute('aria-invalid',String(!valid));$('intent-error').hidden=valid}
function localRedteam(text){const folded=String(text||'').toLocaleLowerCase();const alerts=[];REDTEAM_CLIENT_RULES.forEach(rule=>{if(rule.markers.some(marker=>folded.includes(marker.toLocaleLowerCase())))alerts.push({code:rule.code,severity:rule.severity})});if(/(?:[\\w.+-]+@[\\w.-]+\\.[a-z]{2,}|\\bbearer\\s+[a-z0-9._~-]{8,}|-----begin [a-z ]*private key-----)/i.test(folded))alerts.push({code:'SENSITIVE_DATA_BOUNDARY_ALERT',severity:'CRITICAL'});return{status:alerts.length?'DRIFT_ALERT':'MONITORING_CLEAR',alert_count:alerts.length,alerts,llm_execution:'NONE_DETERMINISTIC_RULES'}}
function renderRedteam(monitor,source='裝置端即時預警'){const safe=monitor||localRedteam('');const alert=safe.status==='DRIFT_ALERT'||Number(safe.alert_count)>0;const root=$('redteam-monitor');const nextState=alert?'DRIFT_ALERT':'MONITORING_CLEAR';const previousState=root.dataset.state;root.dataset.state=nextState;$('redteam-state').textContent=alert?`紅隊飄移告警 · ${safe.alert_count} 項`:'常駐紅隊觀點監看中';$('redteam-detail').textContent=alert?`${source}已停止候選續接；請移除飄移後再由總場審查。`:`${source}正常；規則持續監看技術定義、總場權限、裝置端 LLM、個資與對外主張。`;const list=$('drift-alerts');list.textContent='';list.hidden=!alert;(safe.alerts||[]).forEach(item=>{const li=document.createElement('li');li.textContent=`${REDTEAM_LABELS[item.code]||item.code} · ${item.severity||'HIGH'}`;list.appendChild(li)});if(previousState!==nextState)$('redteam-announcement').textContent=alert?'安全監看發現需要修改的內容，已停止送出。':'安全監看已恢復正常。';return !alert}
function refreshDeviceRedteam(){return renderRedteam(localRedteam(`${$('intent').value}\n${$('answer').value}`))}
function suggestProfile(text){const rules=[['ASSOCIATION',/(社區|志工|活動|協會|課程)/],['PROPERTY',/(物業|設備|檢查|維修|大樓)/],['CAFE_POS',/(咖啡|商品|價格|商家|餐點)/],['HOUSEHOLD',/(提醒|家庭|日常|照護|醫囑)/]];return(rules.find(([,rule])=>rule.test(text))||['GENERIC'])[0]}
function refreshSuggestion(){const text=$('intent').value.trim();if(!text){$('profile-suggestion').hidden=true;return}const value=suggestProfile(text);$('profile-suggestion').hidden=false;$('suggested-profile').textContent=PROFILE_LABELS[value];$('apply-suggestion').dataset.profile=value}
async function api(payload){const response=await fetch('/api/intent-field',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(response.status===401){window.location.assign('/google/member/login');return null}try{return await response.json()}catch(error){return{state:'HOLD',reason_code:'AUTH_OR_GATEWAY_RESPONSE_INVALID'}}}
function humanDecision(value){return value==='PENDING_TOTAL_FIELD_REVIEW'?'待總場審查':value||'候選待審'}
function humanRisk(value){return value==='CLEAR_PRELIMINARY'?'初步清晰，仍待人工核對':value||'待核對'}
function humanHoldReason(value){const reasons={AUTH_OR_GATEWAY_RESPONSE_INVALID:'服務回應無法核對',DEVICE_LLM_REQUIRED:'需要在使用者設備完成理解',REQUEST_JSON_INVALID:'輸入格式無法安全處理'};return reasons[value]||'目前資料未通過安全檢查'}
function describe(key,value){let summary='已建立';if(key==='D1')summary=value.requested_result||value.intent||summary;if(key==='D2')summary=value.state||summary;if(key==='D3')summary=value.destination_field||summary;if(key==='D4')summary=value.capability_ref||summary;if(key==='D5')summary=value.candidate_only?'僅建立候選':summary;if(key==='D6')summary=value.reconstruction_conditions?.equivalence_level||summary;if(key==='D7')summary=humanRisk(value.risk_status);if(key==='D8')summary=humanDecision(value.decision);return String(summary)}
function addItems(root,values,emptyText){root.textContent='';(values.filter(Boolean).length?values.filter(Boolean):[emptyText]).forEach(value=>{const li=document.createElement('li');li.textContent=String(value);root.appendChild(li)})}
function renderCandidate(result){guided=null;$('guided').hidden=true;$('empty-result').hidden=true;$('candidate').hidden=false;$('preview-kicker').textContent='第 3 步 · 核對這一筆候選';$('result-intent').textContent=result.D1?.requested_result||'待人工核對';$('result-profile').textContent=PROFILE_LABELS[result.profile]||result.profile;$('result-risk').textContent=humanRisk(result.D7?.risk_status);$('result-d8').textContent=humanDecision(result.D8?.decision);$('d8-state').querySelector('span').textContent=humanDecision(result.D8?.decision);$('content-hash').textContent=result.content_sha256||'';$('preview').textContent=JSON.stringify(result,null,2);const labels={D1:'目的',D2:'目前狀態',D3:'場域座標',D4:'能力與證據',D5:'執行邊界',D6:'生成式傳輸',D7:'風險阻擋',D8:'裁決封套'};const grid=$('dimension-grid');grid.textContent='';Object.keys(labels).forEach(key=>{const card=document.createElement('article');card.className='dimension';const strong=document.createElement('strong');strong.textContent=`${key} · ${labels[key]}`;const span=document.createElement('span');span.textContent=describe(key,result[key]||{});card.append(strong,span);grid.appendChild(card)});const evidence=[...(result.D4?.source_refs||[]),...Object.entries(result.D4?.source_snapshot||{}).map(([key,value])=>`${key}: ${value}`)];addItems($('evidence-list'),evidence,'沒有可驗證證據');addItems($('risk-list'),Object.entries(result.D7||{}).map(([key,value])=>`${key}: ${value}`),'尚無風險資料');setJourney('step-candidate');setMessage('安全候選已建立；請核對目的、證據、風險與權限邊界。');$('preview-title').focus()}
function renderGuided(result){guided=result;$('guided').hidden=false;$('guided').dataset.field=result.question.field;$('candidate').hidden=true;$('empty-result').hidden=false;$('preview-kicker').textContent='候選預覽 · 等待第 2 步';$('question-label').textContent=result.question.prompt;$('question-kicker').textContent=`第 2 步 · 尚需 ${result.remaining_field_count} 個最小欄位`;$('question-id').textContent=result.question.question_id;$('reason').textContent=result.question.reason;$('options').textContent='';result.question.options.forEach(value=>{const button=document.createElement('button');button.type='button';button.className='secondary option';button.textContent=value;button.setAttribute('aria-pressed','false');button.onclick=()=>{[...$('options').children].forEach(item=>item.setAttribute('aria-pressed','false'));button.setAttribute('aria-pressed','true');$('answer').value=value;$('answer').focus()};$('options').appendChild(button)});setJourney('step-guide');setMessage(`只差 ${result.remaining_field_count} 個必要欄位；每次只問一題。`);$('answer').focus()}
function show(result){renderRedteam(result.redteam_drift_monitor,'總場確定性規則重驗');if(result.state==='HOLD_DETOUR_ALERT'||result.redteam_drift_monitor?.status==='DRIFT_ALERT'){$('guided').hidden=true;$('candidate').hidden=true;$('empty-result').hidden=false;$('d8-state').querySelector('span').textContent='HOLD_DETOUR_ALERT';setMessage('安全監看發現內容飄移，已停止續接；請修改輸入後再試。',true);return}if(result.state==='NEEDS_USER_GUIDED_COMPLETION'){renderGuided(result);return}if(result.content_sha256){renderCandidate(result);return}$('guided').hidden=true;$('d8-state').querySelector('span').textContent='HOLD';setMessage(`無法建立候選：${humanHoldReason(result.reason_code)}。請修改後再試。`,true)}
$('intent').addEventListener('input',()=>{if($('intent').value.trim())setIntentValidity(true);refreshSuggestion();refreshDeviceRedteam()});$('answer').addEventListener('input',refreshDeviceRedteam);$('answer').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.isComposing){event.preventDefault();$('continue').click()}});$('apply-suggestion').onclick=()=>{$('profile').value=$('apply-suggestion').dataset.profile;setMessage(`已採用「${PROFILE_LABELS[$('profile').value]}」使用情境，仍可自行更改。`)};
document.querySelectorAll('.example').forEach(button=>{button.onclick=()=>{$('intent').value=button.dataset.example;$('profile').value=button.dataset.profile;setIntentValidity(true);refreshSuggestion();refreshDeviceRedteam();setMessage('範例已放入輸入框；你可以先修改，再整理成安全候選。');$('intent').focus()}});
$('start').onclick=async()=>{if(busy)return;const requested=$('intent').value.trim();if(!requested){setIntentValidity(false);setMessage('請先用一句話描述希望得到的結果。',true);$('intent').focus();return}setIntentValidity(true);if(!refreshDeviceRedteam()){setMessage('安全監看已停止送出；請先移除飄移或敏感內容。',true);return}intent={requested_result:requested};guided=null;$('candidate').hidden=true;$('empty-result').hidden=false;$('preview-kicker').textContent='候選預覽 · 正在整理';setJourney('step-intent');setBusy(true);try{const result=await api({profile:$('profile').value,intent});if(result)show(result)}catch(error){setMessage('服務暫時無法回應；保留你的輸入，稍後可直接重試。',true)}finally{setBusy(false)}};
$('continue').onclick=async()=>{if(busy||!guided)return;const answer=$('answer').value.trim();if(!answer){setMessage('請選擇安全選項或輸入回答。',true);$('answer').focus();return}if(!refreshDeviceRedteam()){setMessage('裝置端紅隊已停止續接；請先移除飄移或敏感內容。',true);return}const current=guided;setBusy(true);try{const result=await api({profile:$('profile').value,intent,state_id:current.state_id,question_id:current.question.question_id,answer});if(!result)return;if(result.state!=='HOLD_DETOUR_ALERT'&&result.redteam_drift_monitor?.status!=='DRIFT_ALERT'&&(result.state==='NEEDS_USER_GUIDED_COMPLETION'||result.content_sha256))intent[current.question.field]=answer;$('answer').value='';show(result)}catch(error){setMessage('續接失敗；原意圖未被修改，請稍後再試。',true)}finally{setBusy(false)}};
$('reset').onclick=()=>{intent={};guided=null;$('intent').value='';$('answer').value='';$('profile').value='GENERIC';$('profile-suggestion').hidden=true;$('guided').hidden=true;$('candidate').hidden=true;$('empty-result').hidden=false;$('preview-kicker').textContent='候選預覽 · 等待第 1 步';$('d8-state').querySelector('span').textContent='尚未裁決';setIntentValidity(true);setJourney('step-intent');renderRedteam(localRedteam(''));setMessage('已清除本頁候選；先在上方說一句你想完成的事。');$('intent').focus()};
$('edit-candidate').onclick=()=>{$('intent').focus();setMessage('原需求已保留；修改後可重新整理成安全候選。')};$('new-candidate').onclick=()=>{$('reset').click()};
function renderNodes(result){$('node-status').textContent=result.summary||'節點與容器狀態暫不可用。';const grid=$('node-grid');grid.textContent='';(result.nodes||[]).forEach(node=>{const card=document.createElement('article');card.className='node';const name=document.createElement('strong');name.textContent=node.node_id||'SANITIZED_NODE';const detail=document.createElement('span');detail.textContent=`節點 · ${node.os||'OS 未知'} · CPU ${node.cpu||'待驗證'} · GPU ${node.gpu||'待驗證'}`;const state=document.createElement('span');state.className='node-state'+(node.base_transport_state==='INSTALLED_USABLE'?' usable':'');state.textContent=node.base_transport_state||'UNVERIFIED';card.append(name,detail,state);grid.appendChild(card)});(result.containers||[]).forEach(container=>{const card=document.createElement('article');card.className='node';const name=document.createElement('strong');name.textContent=container.name||container.container_ref||'SANITIZED_CONTAINER';const detail=document.createElement('span');detail.textContent=`容器 · ${container.image||'映像待分類'} · ${container.role||'角色待分類'}`;const state=document.createElement('span');state.className='node-state'+(container.runtime_state==='RUNNING'?' usable':'');state.textContent=`${container.runtime_state||'UNKNOWN'} · 總場唯讀納管`;card.append(name,detail,state);grid.appendChild(card)});grid.dataset.nodeCount=String((result.nodes||[]).length);grid.dataset.containerCount=String((result.containers||[]).length)}
fetch('/api/nodes').then(r=>r.json()).then(renderNodes).catch(()=>{$('node-status').textContent='節點狀態暫不可用；不影響本頁離線整理需求。'});
if(window.location.hash==='#workspace')requestAnimationFrame(()=>{$('workspace').scrollIntoView({block:'start'})});
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
