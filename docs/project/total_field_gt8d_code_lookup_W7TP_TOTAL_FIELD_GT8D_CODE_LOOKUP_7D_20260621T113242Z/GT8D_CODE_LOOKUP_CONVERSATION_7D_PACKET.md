# GT8D Code Lookup Conversation 7D Packet

STATE=TOTAL_FIELD_7D_PACKET
RUN_ID=W7TP_TOTAL_FIELD_GT8D_CODE_LOOKUP_7D_20260621T113242Z
HOST=taiji01
ROOT=/home/taiji_admin/Taiji_Hub
SOURCE=conversation_intake
WRITE_SCOPE=docs/project total_field packet only

## D1_IDENTITY
Total Field XiaoJ（總場小J）仍為本地治理權威。taiji01 為本次 GT8D code-owned lookup routing（程式持有查表路由）來源節點。LLM / Ollama / cloud worker 僅可作 semantic intake（語意入口）、slot fill（補槽）、candidate_result（候選結果），不得作最終 authority（權威）。

## D2_INTENT
將本對話的核心成果寫入總場：以 GT8D / 8D packet coordinate（8D 封包座標）+ local lookup table（本地查表）+ generative transfer（生成式傳輸）+ local reconstruction（現地還原）+ local verifier（本地驗證）作為正式路由設計。目標是讓 route_code / lookup_key 在本地以 0.03 秒級完成，不依賴 LLM 生成。

## D3_STATE
已完成 taiji01 GT8D code lookup setup。新增或更新：config/gt8d_lookup/route_table.json、runtime/gt8d_lookup/gt8d_route_resolver.py、/usr/local/bin/codex。codex --route 已改為 STATE=LOCAL_LOOKUP，不再呼叫 Ollama 進行路由生成。Ollama models present: xiaoj-gt8d-lookup-router, qwen2.5:1.5b, qwen2.5-coder:1.5b；但 route 主路徑 MODEL_USED=FALSE。

## D4_TOPOLOGY
User / CLI / frontend -> /usr/local/bin/codex -> runtime/gt8d_lookup/gt8d_route_resolver.py -> config/gt8d_lookup/route_table.json -> ROUTE_CODE + LOOKUP_KEY + D1-D8 output -> w7tp-cloud or local verifier -> local reconstruction -> candidate land decision. Internal node publish target includes taiji01, MSI-WSL, penguin. Cloud worker receives only redacted_packet / candidate request and returns candidate_result only.

## D5_RESOURCE
Primary resources: local JSON route table, Python resolver, codex wrapper, 8D/7D knowledge bundles, OpenWebUI Knowledge packs, optional qwen2.5:1.5b / qwen2.5-coder:1.5b for non-route tasks. Route lookup does not require large model. Browser / LINE WORKS / Odoo / POS / patent / code tasks are selected by route_code and lookup_key before any model or tool action.

## D6_GOVERNANCE
Governance rule: local code table is authority for routing. LLM may optionally suggest lookup_key only for ambiguous input, but code must validate exact ROUTE_CODE and LOOKUP_KEY. Forbidden by default: private_key, client_secret, refresh_token, access_token, token print, member plaintext, DB_WRITE, SERVICE_RESTART, DEPLOY, PRODUCTION_RELEASE, direct POS_ACTION, direct LINE WORKS send, direct browser high-risk action. Safety is risk-tiered governance（分級風險治理）, not blanket shutdown（全部關閉）。

## D7_VERIFICATION
Verified route lookup speed: ELAPSED=0.03 sec for three cases. MEMBER / LINE WORKS -> ROUTE_CODE=MEMBER_SERVICE, LOOKUP_KEY=member.service.lineworks.notify.v1. Odoo / POS -> ROUTE_CODE=ODOO_POS_ACTION, LOOKUP_KEY=odoo.pos.action.candidate.v1. Patent claim -> ROUTE_CODE=PATENT_ANALYSIS, LOOKUP_KEY=patent.analysis.gt8d.v1. Evidence dir: runtime/gt8d_lookup_evidence/W7TP_GT8D_ROUTE_003SEC_EVIDENCE_20260621T113027Z.

## EVIDENCE_HASHES
route_table.json=91684113e135d4cc760d7197176c39ba9d7bf9c25dd2bbfbb89158d718ab9485
gt8d_route_resolver.py=474a3e8382ee1a57c3ff2a38ca4f4609d4cbc9af0492061b2a6413f1e0d41ea4
/usr/local/bin/codex=2a320f9f2d3b440e6c47ee9152a8f2ff7e0d7e8a251018e51e9629a21e1fd26f
route_tests.txt=c61cd52afb270c16f912856e32707fb51b49e0aeccedbf3c9febdee3a515552c
report.txt=e607f7c0592e0d6fc3df2267824e465462054e9367593b5a81e3c0172de8c112

## CLAIM_SCOPE
CLAIMED=GT8D route lookup / intent routing / lookup_key selection can complete at 0.03 sec on taiji01 by local code lookup.
NOT_CLAIMED=full LINE WORKS API execution, full browser control, full Odoo write, or end-to-end service completion in 0.03 sec.

## SAFETY_FLAGS
SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
TOKEN_PRINT=FALSE
DB_WRITE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE

## NEXT_SAFE_ACTION
Seal this 7D packet with sha256_manifest. Optional next step: git add this packet plus route_table.json and gt8d_route_resolver.py after explicit human authorization.
