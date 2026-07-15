# TFCT／TRUE8D Runtime Candidate Policy 可追蹤封裝報告

RUN_ID=`TFCT_TRUE8D_RUNTIME_CANDIDATE_POLICY_PACKAGE_V0_1`

TRACKED_POLICY_RESPONSIBILITY=REBUILD_SOURCE
RUNTIME_POLICY_RESPONSIBILITY=RUNTIME_CONSUMER_TARGET
CANONICAL_EQUIVALENCE=MATCH
POLICY_SHA256=d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960
MATERIALIZATION_MODE=EXPLICIT_ONLY
NO_OVERWRITE=YES
CANONICAL_PROMOTION=NO
DEPLOY=NO
RESTART=NO

## 封裝原因

現行候選 runtime policy 位於受執行期目錄政策管理的路徑。本來源包在 `manifests/tfct_true8d_runtime_candidate_v0_1/` 保存可版本追蹤的候選 policy 與 package manifest，使相同內容能被確定性驗證及明確重建。這不建立第二套 policy 語義。

## 責任區隔

- `policy.json` 是可追蹤的候選來源。
- runtime policy 是 runtime materialization target，仍保留原位且未被移動、刪除或覆寫。
- `package_manifest.json` 只描述來源、目標、版本、候選狀態與完整性契約。
- 封裝工具的預設 `check` 只讀；只有明確呼叫 `materialize TARGET` 才可能建立一個不存在的候選目標。

## Canonical JSON 等價與 SHA-256 契約

等價判斷以 JSON 值為準，固定序列化為 `sort_keys=True`、`ensure_ascii=False`、`separators=(",", ":")`、`allow_nan=False`。tracked source 與 runtime policy 必須產生完全相同的 canonical bytes。

`policy_sha256` 是上述 canonical bytes 的 SHA-256：

`d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960`

物件 key 排序或排版差異不改變身份；任何規則值、陣列順序或狀態改變都會造成不匹配。

## 不覆蓋政策與 materialize 流程

`materialize` 僅接受使用者明確指定的候選 target：

1. target 不存在時，以 exclusive-create 建立來源 policy。
2. target 已存在且 canonical-equivalent 時回傳 `ALREADY_MATCH`，不寫入。
3. target 已存在但不同時回傳 `HOLD_TARGET_CONFLICT`，不覆寫。
4. Active Canonical 或 Pointer 類目標一律拒絕。

本次驗證只在臨時目錄執行 materialization；沒有改寫現行 runtime policy。

## 候選與正典邊界

來源包、policy、manifest 與工具均維持 `CANDIDATE` 邊界。`canonical_promotion=false`；本次沒有寫入 Active Canonical、Pointer、D3 engine 或 packet runtime，也沒有進行部署、重啟、資料庫或 router 寫入。

## 測試結果

Focused package suite：`PASS 15/15`。Package verifier：`PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE`。驗證涵蓋 canonical equivalence、manifest hash、嚴格 JSON、衝突不覆寫、重放身份及受保護檔案不變。

## 未執行事項

- 未執行 Canonical Promotion。
- 未部署、重啟或遠端安裝。
- 未寫入資料庫或 router 設定。
- 未執行 git commit。
- 未重跑既有 45 項 runtime suite 或全倉庫測試。

## 後續升格前置條件

若未來另案進行 Canonical Promotion，至少需要人工審查、tracked/runtime policy 等價證據、focused tests 與 verifier 持續通過、materialization 目標與操作權限明確化，以及 Active Canonical／Pointer 寫入的獨立明確授權。
