# GST V2.1 精確升格請求與原生候選審查結案
Status: DONE

完成範圍：本次精確候選請求已在 taiji01 落盤，原生細粒度審查與獨立遠端回讀已完成。
正式正典升格：HOLD_PENDING_APPLICABLE_CONTRACT；正式 D8 效果未授權，運行啟用未執行。
本檔的 DONE 僅對應本輪凍結 order.md 的候選交付產品，不代表正典升格完成。

## Acceptance
- [PASS] AC-1: 原始規格、碼源、18 項登錄來源及 35 個受保護來源已精確綁定 | evidence: evidence/CURRENT_ANCHORS.json
- [PASS] AC-2: 完整候選以固定 SHA256 在 taiji01 新建落盤並回讀 | evidence: evidence/CANDIDATE_DELIVERY_RECEIPT.json
- [PASS] AC-3: 原生函式實際審查完整請求及逐位元組一致的規格全文，共 240 單位 | evidence: evidence/NATIVE_CANDIDATE_REVIEW.json
- [PASS] AC-4: 獨立遠端回讀 18／18 項通過，12 份凍結輸入均一致 | evidence: evidence/INDEPENDENT_VERIFICATION.json
- [PASS] AC-5: 35 個受保護檔案及 branch／HEAD 未變；既有運行綁定原生狀態仍 PASS | evidence: evidence/POST_OPERATION_VERIFICATION.json

Independent functional verification: PASS_INDEPENDENT_CANDIDATE_DELIVERY_VERIFIED, 18/18 checks; independent remote writes=0 | evidence: evidence/INDEPENDENT_VERIFICATION.json

## 原生判定與候選說明
原生結果：235 ACCEPT、4 ACCEPT_WITH_CORRECTION、1 HOLD_FOR_EVIDENCE；REJECT_TECHNICAL_DRIFT、REJECT_OVERCLAIM、TRADE_SECRET_QUARANTINE 均為 0。
完整單位判定原樣保存於 evidence/NATIVE_REVIEW_UNITS.json，原生 held=true 保留。
四項補明為三項本地權威邊界、一項 6-bit 可信路由邊界；候選補充文字記於 evidence/REVIEW_DISPOSITION.json，未改寫原規格、原請求或原生判定。
唯一待證單位 W7TP-B6CCF437DB268133 指向 Tier 2 歷史 15.1 ms 主張；對應 32-bit 原碼、美國原件與原始執行紀錄仍待綁定。
該主張保留歷史歸屬，不冒充本輪新實測；此 HOLD 不否定 Founder 定義，也不是新發生的執行故障。
細粒度審查是原生文字規則分類，不核驗所有引用證據內容、不發 D8；ACCEPT 計數不是準確率或升格完成度。

## 權威、實際行為與證據限制
request lifecycle=IMAGINED_CANDIDATE；workloop lifecycle=CANDIDATE_FOR_TOTAL_FIELD_REVIEW。
formal total_field_decision=NOT_REVIEWED；formal_effect_authorized=false。
未呼叫正式 resolver、未要求親簽、未消耗 nonce、未切換母正典、未改 codec、未啟用新 consumer、未重跑既有重構測例。
本輪使用 RDC 傳遞資料，沒有把一般傳檔標為 D6 生成式傳輸。
既有 GST V2.3 runtime_status() 的 PASS 僅對應既有運行綁定，不替本 GST V2.1 新 codec 提供正式授權。
35 個受保護檔案雜湊與 run 外 Git status 不變只支持所檢查範圍；不擴張為所有外部服務或資料庫事件皆未發生。
舊 G4 receipt 與當前檔案有三個前後像不一致，已原樣記錄於 evidence/GOVERNOR_PREFLIGHT.json；這限制該條舊回執的證明力，不推定所有原生路線失效。

## 工作迴圈與成本
order.md、PROMOTION_REQUEST.json、intent-envelope.json 及 INPUT_MANIFEST.json 保持原始位元組。
只更新本輪新建目錄內的進度用 closeout／handoff；原前像另存 evidence/WORKLOOP_PROGRESS_PREIMAGES.json。decisions／budget 只追加事件。
本輪候選交付與結案證據同步合計 candidate_delivery_attempt=2／2；原生審查 native_candidate_review_attempt=1／2。結案同步不重跑原生審查。
材料範圍為使用者授權的既有規格、程式庫唯讀來源及本輪候選證據；不包含原始憑證、私鑰、nonce 或會員明文。
背景工作：無持續執行中的 reviewer、codec 或正式升格流程。
退出／回復方式：停止引用本候選目錄並保留證據；沒有母正典或運行狀態需要由本輪還原。

## 未結事項與唯一下一步
正式規格身分升格的受理／執行器／穩定落點，在已查入口中仍未確認；approved_write_set=[]、effect_execution_ready=false。
在具體執行契約完成前，不產生空泛簽署請求，也不把候選審查替代為正式核定。
NEXT：沿既有總場建立本精確 GST V2.1 規格的正式升格受理與執行契約，綁定執行器、落點、前後像、回復及驗收，再交適用原生入口裁決。
