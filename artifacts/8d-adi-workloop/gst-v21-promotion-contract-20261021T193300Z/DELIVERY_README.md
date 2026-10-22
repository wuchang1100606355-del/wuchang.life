# GST V2.1 精確規格升格執行契約候選

狀態：IMAGINED_CANDIDATE。這份交付完成受理描述、有限執行器、前後像與隔離驗證；它本身不授權正典升格。

## 精確對象

- 節點：taiji01；根目錄：`/home/taiji_admin/Taiji_Hub`。
- 分支：`codex/current-live-state-consolidation-20260915`；HEAD：`4aa306deba4834c68ca2f0abae23ed57eaed1df5`。
- 契約 raw SHA256：`7a8e405e5edde1a03a3a086742caf132bda3d7e464e6293936d2bc9057f66e49`。
- 精確效果：`GST_V21_SPEC_PROMOTE:7a8e405e5edde1a03a3a086742caf132bda3d7e464e6293936d2bc9057f66e49`。
- 原規格 SHA256：`0cf1d5f6f0c55bf1193cfd1227404b1999e61f1472d66eb8fd6087f2cd038855`；原規格位元組保持完全一致。
- 母正典：W7TP 8D ADI V2.3，`e3c5439657bb4cb97f466ea096d20f8e68ca60307286f01f9c66da0eb120dd2c`。

## 這次工程補齊了甚麼

本候選將前一輪精確規格請求接成一個有限、可回讀的規格身分升格契約。正式執行僅建立下列兩個檔案、更新一個既有索引，最後才產生派生回執：

| 正式路徑 | 動作 |
| --- | --- |
| `manifests/total_field/origin_cell_gst_v21_specification/SPECIFICATION.md` | 建立原規格的完全相同位元組 |
| `manifests/total_field/origin_cell_gst_v21_specification/CANONICAL_RECORD.json` | 建立需原生回執才能成立的身分紀錄 |
| `configs/total_field/w7tp_capability_internalization_registry_v1.json` | 僅向既有 CAP_INTERNAL_ORIGIN_CELL_V1 的 source_refs 追加一筆紀錄參照 |
| `manifests/total_field/origin_cell_gst_v21_specification/PROMOTION_RECEIPT.json` | 真實原生授權與後像驗證成功後，最後產生 |

索引原有 canonical=false、CANDIDATE_ONLY 與 D8 權威邊界維持。登錄紀錄存在不等於權威，靜態後像存在也不等於完整升格。runtime、codec 啟用、Odoo 業務效果、母正典切換及證據成熟度不在本效果範圍。

## 權威與驗收

43 個 immutable sources、3 個靜態後像、2 支執行程式及凍結 order 都由契約精確綁定。效果字串含整份契約的 SHA256，所以合法原生簽署同時限定程式、目標及前後像；新程式、新來源或新落點必須形成新的受理對象。

正式入口使用既有 `resolve_founder_signed_break_glass_effect`。它要求人類直接、單次、最多 300 秒的精確簽署，綁定效果、目標、HEAD、當下工作樹狀態與權威前像。本候選沒有簽署能力，也不接受呼叫者提供 PASS 當作授權。`ADMISSION_DESCRIPTOR.json` 是可審查描述，不是可使用的 grant。

原生授權回執和規格發布回執是兩個不同物件。後者只有在前者與實際後像核對成功後才能建立。`status` 會重新驗證持久簽署資料、原生 Stage B 簽章、原生回執、nonce 記錄、交易 journal 及實際後像，且不再消耗 nonce。

兩支候選與五支已綁定原生來源採原始碼載入，避開既有 bytecode cache 或預載模組。這項檢查不將模型或程式雜湊升格成權威。

## 可回復範圍與限制

寫入前會持久化單次執行記錄及有限的 12 個 journal 事件。已建立物件以內容與 inode（檔案實體識別）共同確認所有權。索引交換後保留原始前像；發現來源漂移或失敗時，只有仍由本次交易持有且符合精確內容的物件才可自動回復。外來索引、暫存前像或同內容的新 inode 都保留並進入復原待處理狀態。

授權稽核資料位於固定 repo 外路徑 `/home/taiji_admin/w7tp_gst_v21_specification_audit`，私有 grant 僅供本地冷驗證，模式 0600。nonce 記錄為永久單次排除；原生入口若已消耗 nonce 卻未完成回執，必須保留現場，不能重試同一授權。正式回執一旦已持久化，後續錯誤不走自動撤回；撤回需新的精確受控動作。

本程序要求協作鎖及獨佔的本地變更時段。Linux 原子交換本身不能保證對所有非協作寫入者提供通用 CAS；測試亦不宣稱實際斷電復原已獲驗證。回復指令只產生計畫，不自動抹除歷史或未知資料。

## 已驗證成果與歷史證據

最終隔離測試 43/43 通過，包含漂移、碰撞、路徑逸出、symlink、hardlink、假授權、過期、原生拒絕、重放、部分寫入、外來變更、冷查詢、cache 污染與未綁定稽核路徑。證據見 `evidence/REGRESSION_RESULTS.json` 與 `evidence/INDEPENDENT_VERIFICATION.json`。

第 2 批的 38/40 結果仍以 `_BATCH_2` 檔案保存；兩個未通過項目來自缺少回執父目錄與測試 replay 目錄權限設定，修正理由均保留。最終測試沒有使用真實私鑰、grant、nonce，也沒有在正式節點執行 apply。

前一輪 240 單位原生文字審查保持其原證據範圍：235 ACCEPT、4 ACCEPT_WITH_CORRECTION、1 HOLD_FOR_EVIDENCE。Tier 2 歷史 15.1 ms 的原碼及原始執行綁定仍待補證；本契約不把它升格成新實測。舊 G4 receipt 的三個 postimage 與現況不符，只限制該歷史回執的證明力，見 `evidence/HISTORICAL_RECEIPT_SCOPE.json`。

## 操作介面

以下為候選介面描述，命令存在不代表已獲正式授權。實際執行後像以 `evidence/REMOTE_DELIVERY_AND_NATIVE_GATE.json` 為準。

```bash
python3 -B candidate/promote_origin_cell_gst_v21_specification.py dry-run
python3 -B candidate/promote_origin_cell_gst_v21_specification.py probe-authority
python3 -B candidate/promote_origin_cell_gst_v21_specification.py status
python3 -B candidate/promote_origin_cell_gst_v21_specification.py recovery-plan
```

正式 apply 僅能在已建立本地獨佔變更時段、取得這一精確效果的原生 fresh signed grant 後，由本地操作員提供私有檔案路徑：

```text
python3 -B candidate/promote_origin_cell_gst_v21_specification.py apply --signed-grant <本地私有已簽署檔案> --exclusive-local-change-window
```

原生 fresh grant 需在交付包定稿後，依當次工作樹重新產生並立刻使用。不得沿用候選建立前的 git status 摘要。請勿將私鑰、raw nonce 或簽署資料貼入對話。

## 工程狀態

DESIGN、IMPLEMENTATION、TEST 指向本候選交付；DEPLOYMENT 僅指候選包送達，不等於正式程式安裝。RUNTIME_EFFECT 未執行；AUTHORITY 必須以本次原生入口的精確裁決為準。RECONSTRUCTED、EXECUTED、EFFECT_VERIFIED 持續分開。本輪沒有主張 D6 原胞重構。
