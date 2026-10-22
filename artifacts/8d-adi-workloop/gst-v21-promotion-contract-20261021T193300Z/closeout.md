Status: DONE

# GST V2.1 精確規格升格契約候選：交付結案

DONE 的範圍是本輪候選程式、精確契約、隔離驗證及實機送達／受理回覆；正式正典升格維持 HOLD_FOUNDER_FRESH_SIGNATURE_REQUIRED。

## Acceptance

- [PASS] AC-1: 當次來源、母正典、原請求與原生能力上下文已綁定；43 immutable sources，連同既有索引共44受保護路徑於交付前後一致。 | evidence: evidence/CURRENT_BINDINGS.json
- [PASS] AC-2: 契約綁定3個靜態後像、2份程式、12個journal槽及所有有限稽核路徑；派生回執最後建立。 | evidence: evidence/CONTRACT_VALIDATION.json
- [PASS] AC-3: 最終43/43隔離測試通過；第2批fixture失誤原證據完整保留。 | evidence: evidence/REGRESSION_RESULTS.json
- [PASS] AC-4: 獨立代理以完整合成fixture實跑測試，來源前後SHA穩定，未將測試成果作正式授權。 | evidence: evidence/INDEPENDENT_VERIFICATION.json
- [PASS] AC-5: taiji01候選回讀一致；原生角色前提PASS、精確效果無簽授權回覆HOLD，正式來源與外部工作樹不變。 | evidence: evidence/REMOTE_DELIVERY_AND_NATIVE_GATE.json
- [PASS] AC-6: handoff、封存內容、結案與單一後續動作已完整描述。 | evidence: handoff.json

- Independent functional verification: gst_request_verifier 獨立程序與合成輸入43項，受測程式與交付程式雜湊相同。 | evidence: evidence/INDEPENDENT_VERIFICATION.json

## Materials and scope

Allowed materials: 使用者授權內部原始碼、原請求與證據、合成測試資料。
Excluded materials: 私鑰、原始憑證、會員明文、真實nonce與簽章值。
Non-goals: 未執行正式apply、codec/runtime啟用、母正典或權威切換、Odoo業務操作、Git commit/push、工作樹清理。
Human input: 本輪沿用「下一步」之候選工程授權；原生新鮮精確簽署並未取得。
Gates: 隔離功能及候選交付通過；正式D8授權維持原生HOLD。
Background processes: 已完成兩個遠端程序，exit code皆0；無候選交付以外背景任務。
Budget: candidate_delivery 2/2，native_gate_probe 2/2，regression_batch 3/3；停止額外回歸。

## Findings and limits

Refuted hypotheses: 呼叫者PASS、靜態後像、模擬回執、歷史receipt或角色鏈PASS均不能自動授權本次效果。bytecode污染不能取代精確原始碼。第2批兩項測試問題來自fixture父目錄缺失與權限0755，最終已修正，舊結果沒有覆寫。
Rollback: 本輪候選停止引用即可，不修改受保護來源。未來正式執行的部分失敗，只回復仍屬本交易且精確匹配的物件；原生audit/replay不可刪除，已發布receipt撤回需要新受控動作。僅在協作鎖及獨佔變更窗口內承諾此行為；無全敵意並發或斷電實測保證。
Protected unchanged state: 44個受保護路徑、HEAD、branch、既有母指標、權威、field、codec及既有runtime保持，原工作樹不清理。
Open debt: 精確Founder新鮮簽署；歷史Tier 2 15.1ms綁定仍待補證；signed apply沒有在正式節點執行。
Manifest hash: 954d208a18e62b89024fa0ce67610f4f6cb867da2cddc791927bff4fb2b34e4f (ARTIFACT_MANIFEST.json；排除自身與進度中繼檔，排除清單已列明)。
Total Field receipt: 正式授權receipt未產生。實際原生答覆 HOLD_FOUNDER_FRESH_SIGNATURE_REQUIRED，證據 evidence/NATIVE_EXACT_EFFECT_PROBE.json。
Contract SHA256: 7a8e405e5edde1a03a3a086742caf132bda3d7e464e6293936d2bc9057f66e49

## Phase boundary

DESIGN=COMPLETE_FOR_BOUNDED_CANDIDATE
IMPLEMENTATION=EXACT_SOURCE_BOUND_CANDIDATE
TEST=PASS_43_OF_43_ISOLATED
DEPLOYMENT=CANDIDATE_DELIVERY_ONLY
RUNTIME_EFFECT=NOT_EXECUTED
AUTHORITY=HOLD_FOUNDER_FRESH_SIGNATURE_REQUIRED

## NEXT

由 Founder 在 taiji01 既有本地權威路徑，對 ADMISSION_DESCRIPTOR.json 所綁定的精確契約完成一次新鮮單次簽署。
