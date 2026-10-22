# 8D ADI Order: GST V2.1 精確升格執行契約候選

Run-ID: gst-v21-promotion-contract-20261021T193300Z
Lifecycle: CANDIDATE_FOR_TOTAL_FIELD_REVIEW
Frozen: 2026-10-21T19:35:51.874635+00:00
Owner-ref: UNKNOWN_UNVERIFIED
Effect-class: E5

## D1 Intent
承接最新「下一步」，沿既有總場完成本 GST V2.1 規格的受理與執行契約候選，綁定前後像、原生授權、回復與驗收。

## Verified facts
- [FACT|OBSERVED_AUTHORIZED_API] 41 個受保護來源與本次座標核對完成 | source: evidence/CURRENT_BINDINGS.json | hash: 20c045127879354a6cbb1c3c086536843ba0cc6a775e1b8e7d6b5966aa98805c
- [FACT|OBSERVED_AUTHORIZED_API] 原生能力上下文投影已取得並驗證；沒有執行完整上下文pull或重構 | source: evidence/NATIVE_CAPABILITY_CONTEXT.json | hash: 544bd88691e0ae643788ed26500b4c8d990cf0c57eee83651420b369518c1afa
- [INFERENCE|DERIVED_FROM_OBSERVED] 專用規格葉節點與既有原胞source_refs追加可閉合落點；新路徑仍是候選設計 | source: evidence/CURRENT_BINDINGS.json | hash: 20c045127879354a6cbb1c3c086536843ba0cc6a775e1b8e7d6b5966aa98805c

## Materials
- Allowed: 使用者授權程式庫來源、上一輪凍結候選、測試合成資料 | licence: USER_AUTHORIZED_INTERNAL_ENGINEERING | checked: 2026-10-21T19:35:51.874635+00:00
- Excluded: 私鑰、原始憑證、會員明文、真實nonce輸出 | reason: 本輪無需此類內容

## Build specification
- root/head/source bindings = evidence/CURRENT_BINDINGS.json
- formal leaf proposal = manifests/total_field/origin_cell_gst_v21_specification
- static postimages = exact existing spec + bounded canonical record + existing registry with one source_ref appended to CAP_INTERNAL_ORIGIN_CELL_V1
- dynamic receipt = produced only from an actual native decision and physical readback; explicitly derived after authorization, not a fabricated fixed hash
- admission = exact effect string contains immutable contract digest; native resolver verifies fresh human signed effect, target, root/head/status/authority and single-use condition
- replay = existing resolver protocol with an explicitly bounded persistence adapter; no model authority, no acceptance of caller-supplied PASS
- candidate executor = dedicated, finite-path helper in this candidate run, reusing existing resolver and native capability context; not installed into live tools
- filesystem transaction = preflight, exact CAS, no symlinks, staged payloads, receipt last, rollback only owned matching writes, preserve audit and recovery debt
- production boundary = current turn never calls signed apply or consumes a nonce; tests use an isolated synthetic root with conspicuous non-authority markers
- current mutable scope = local candidate project and new remote artifacts/8d-adi-workloop/gst-v21-promotion-contract-20261021T193300Z; progress metadata mutable, frozen inputs and observed source files immutable

## Budget fuse
- Limit: 2 candidate_delivery
- Limit: 2 native_gate_probe
- Limit: 3 regression_batch
- Stop condition: stop at the limit; two failed attempts on one unchanged causal hypothesis stop that hypothesis

## Acceptance
- [ ] AC-1: 當次來源、母正典、原請求與原生能力上下文精確綁定 | evidence: evidence/CURRENT_BINDINGS.json
- [ ] AC-2: 完整契約、靜態後像、原生受理描述、receipt派生規則與回復條件均可機器驗證 | evidence: evidence/CONTRACT_VALIDATION.json
- [ ] AC-3: 候選執行器在隔離根目錄驗證授權拒絕、來源漂移、路徑、重放、並發、部分失敗與回復 | evidence: evidence/REGRESSION_RESULTS.json
- [ ] AC-4: 獨立功能驗證與紅隊結論有實際非空輸入、未把fixture成功當正式授權 | evidence: evidence/INDEPENDENT_VERIFICATION.json
- [ ] AC-5: taiji01 原生入口對精確本次效果實際回覆；候選交付回讀與正式來源不變條件驗證 | evidence: evidence/REMOTE_DELIVERY_AND_NATIVE_GATE.json
- [ ] AC-6: 交付包、handoff、結案與workloop validator完整，唯一剩餘動作明確 | evidence: handoff.json

## Non-goals
- 本輪不正式升格、不啟用codec、不改母正典/權威、不重跑已有重構或240單位審查、不清理工作樹、不提交推送。

## D2-D8 projection
- D2 STATE: 既有候選送審完成，現在補齊執行契約候選。
- D3 COORDINATE: taiji01，現行V2.3與HEAD 4aa306deba4834c68ca2f0abae23ed57eaed1df5。
- D4 EVIDENCE: 當次來源綁定、歷史結果分級、隔離功能測試與獨立驗證。
- D5 EXECUTION_POLICY: 只建立及交付候選；正式效果必須另有原生精確簽署裁決。
- D6 GENERATIVE_TRANSMISSION: 本輪未主張；RDC與ZIP僅載體。
- D7 RED_TEAM_RISK_CONFINEMENT: 授權注入、漂移、競態及部分寫入納入驗收。
- D8 ENVELOPE_AUTHORITY: CANDIDATE_ONLY，native gate缺簽回覆不等於正式核准。
