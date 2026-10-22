# 8D ADI Order: GST V2.1 精確升格請求與原生候選審查

Run-ID: gst-v21-exact-promotion-20261022T190316Z
Lifecycle: CANDIDATE_FOR_TOTAL_FIELD_REVIEW
Frozen: 2026-10-21T19:12:14.442461+00:00
Owner-ref: UNKNOWN_UNVERIFIED
Effect-class: E5

## D1 Intent
承接使用者「執行下一步」，建立精確 GST V2.1 規格正典身分升格請求，完成適用原生候選審查並保存真實結果。

## Verified facts
- [FACT|OBSERVED_AUTHORIZED_API] taiji01 root/branch/HEAD 與當前正典引用已核對 | source: evidence/LIVE_SNAPSHOT.json | hash: f07fafed173872d7154e5200aad9c67045a47c126ba3cce654fba51964962bb3
- [FACT|OBSERVED_AUTHORIZED_API] 原登錄 manifest 18 個來源全部雜湊與大小吻合 | source: evidence/CURRENT_ANCHORS.json | hash: 70a45e70b75c318d619441b2fb2758936cd6d8cc78c86350353269cd163ee3d3
- [INFERENCE|DERIVED_FROM_OBSERVED] 現有細粒度函式適用候選內容檢查；正式落點與執行器仍未在有界查核中確認 | source: evidence/NATIVE_ROUTE_REVIEW.json | hash: 6808b91b5714e0d37a949627b72b1b72bef178acca62bdce0e7231c8e17b3cdb

## Materials
- Allowed: 使用者指定之既有規格、授權程式庫唯讀資料及本輪候選 | licence: USER_AUTHORIZED_INTERNAL_REVIEW | checked: 2026-10-21T19:12:14.442461+00:00
- Excluded: 原始憑證、私鑰、nonce、會員明文 | reason: 本輪不需此類資料

## Build specification
- request = PROMOTION_REQUEST.json | SHA256 = cc5d289bd94689c5e35649b541c5c523687ee87a402a0c6ba8e0ec5ec6df4ef4
- remote candidate root = /home/taiji_admin/Taiji_Hub/artifacts/8d-adi-workloop/gst-v21-exact-promotion-20261022T190316Z
- native candidate function = tools.total_field.w7tp_d8_reviewer_entrypoint.fine_grain_check
- native formal decision = NOT_REQUESTED_THROUGH_UNSUPPORTED_CANARY_SCHEMA
- current mutable scope = create-only files in the exact new candidate directory
- formal requested scope = exact specification recognition only; runtime activation excluded

## Budget fuse
- Limit: 2 candidate_delivery_attempt
- Limit: 2 native_candidate_review_attempt
- Stop condition: stop at or before either limit; preserve every result and correction

## Acceptance
- [ ] AC-1: 原始規格、碼源、manifest 與受保護狀態精確綁定且來源可回讀 | evidence: evidence/CURRENT_ANCHORS.json
- [ ] AC-2: 完整候選請求以固定雜湊建立並在 taiji01 create-only 落盤 | evidence: evidence/CANDIDATE_DELIVERY_RECEIPT.json
- [ ] AC-3: 原生函式審查本請求與實際規格全文，回傳非零單位與各類判定 | evidence: evidence/NATIVE_CANDIDATE_REVIEW.json
- [ ] AC-4: 獨立審查者由 taiji01 回讀請求／審查結果／來源，核對交付與權威邊界 | evidence: evidence/INDEPENDENT_VERIFICATION.json
- [ ] AC-5: 受保護來源與既有運行綁定檢查完成，無正式升格與服務變更 | evidence: evidence/POST_OPERATION_VERIFICATION.json

## Non-goals
- 本輪不完成正式正典晉升、授權簽署、運行啟用、權威或角色變更。
- 不重跑已通過之重構測例，不更改歷史來源，不清理既有工作樹。

## D2-D8 projection
- D2 STATE: 登錄完成；精確候選送審；正式升格仍依原生可適用路徑核定。
- D3 COORDINATE: taiji01 / W7TP_8D_ADI_V2_3 / 4aa306deba4834c68ca2f0abae23ed57eaed1df5 / /home/taiji_admin/Taiji_Hub/artifacts/8d-adi-workloop/gst-v21-exact-promotion-20261022T190316Z
- D4 EVIDENCE: 當次雜湊、既有18檔來源、原生候選審查與獨立回讀。
- D5 EXECUTION_POLICY: exact create-only directory; drift hold; stop reference to withdraw candidate。
- D6 GENERATIVE_TRANSMISSION: 本輪RDC搬運不聲稱D6；GST定義與原件依來源規格。
- D7 RED_TEAM_RISK_CONFINEMENT: 候選與權威分離，正式落點缺口隔離，保留歷史證據成熟度。
- D8 ENVELOPE_AUTHORITY: IMAGINED_CANDIDATE; formal effect not granted; candidate review only。
