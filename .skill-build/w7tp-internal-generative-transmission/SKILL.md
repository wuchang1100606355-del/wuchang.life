---
name: w7tp-internal-generative-transmission
description: 以 Founder 意圖啟動 8D 網路分析與 ADI 節點、基座、路由定位，透過總場控制既有 W7TP 生成式傳輸；固定區域網路為主、VPN 為輔，並由接收端本機重構與重新觀測閉環。用於 Taiji_Hub 內部已登記節點通訊，不用於普通複製、同步、Git、SSH、提示傳遞或未授權外部效果。
---

# W7TP 內部生成式傳輸總場技能

## 能力身分

- `SKILL_ID=W7TP_INTERNAL_GENERATIVE_TRANSMISSION_TOTAL_FIELD_V1`
- 本技能是總場工作程序與既有工具入口，不是 canonical、D8、模型權威或第二套 Receiver。
- 真實專案預設為 `/home/taiji_admin/Taiji_Hub`；每次重新確認 ROOT、BRANCH、HEAD、WORKTREE、canonical pointer、authority 與 runtime，不沿用舊座標。

## 適用時機

用於 Founder 要求內部節點交換意圖／狀態場封包、分析網路、定位設備與基座、選擇 LAN/VPN 路徑、建立 D6 封包或在接收端本機重構。

下列情況不得標成 D6：普通檔案複製、壓縮、同步、備份、Git、SSH、SMB、Tailscale、VPN、提示詞／上下文傳遞、雲端或本機模型切換。這些最多是載體或推理供給。

## 固定路徑

```text
Founder Intent
→ D1-D8 current network field
→ ADI locate node / identity / base / capability / route / evidence
→ Total Field selects admitted target and scope
→ LAN reachability and Receiver check
→ VPN only after LAN is observed unavailable or inapplicable
→ build one logical target reconstruction packet
→ bind a recipient envelope for each admitted target when identity/base differs
→ receiver-local deterministic reconstruction
→ digest/coordinate/lineage consistency
→ reobserve on mismatch or effect boundary
→ append-only receipt to Total Field
```

「一次封包到全節點」指一個邏輯目標封包。只有節點具有相同已准入基座、相容 namespace、相同目標狀態與有效群組封套時，才可共用相同封包位元組；否則必須保持共同 payload、逐節點封套，不得廣播後忽略身分或基座差異。

## D1-D8 投影

- `D1 Intent`：Founder 當次目標、節點範圍與可觀測結果。
- `D2 State`：設備、介面、Receiver、基座、封包與效果目前狀態。
- `D3 Coordinate`：node identity、LAN IP、備援 VPN IP、port、namespace、base ref、logical time。
- `D4 Evidence`：即時連線結果、基座 digest、封包 digest、Receiver receipt；不得升格為權威。
- `D5 Execution/Policy`：總場選路與 fail-closed；LAN 為主，VPN 為輔。
- `D6 Generative Transmission`：`TARGET_BASE_STATE + MINIMUM_REQUIRED_DELTA + REFERENCES + COORDINATES + RECONSTRUCTION_RULES + VERIFICATION_RULES`，由接收端本機確定性重構。
- `D7 Risk/Quarantine`：錯誤身分、基座不符、路由漂移、TTL、nonce、秘密與不可逆效果立即 HOLD/BLOCK。
- `D8 Envelope/Authority`：Sender、Receiver、作用範圍及外部效果授權；內部快速路徑不能繞過外部效果 D8。

## 必要輸入與准入

每個目標至少要有：

- 當次 Founder intent reference 與 target-state commitment。
- 正式 node identity；主機名稱或 IP 相似不得合併節點。
- 已重新觀測的 LAN 座標；VPN 座標只作備援。
- Receiver 的 exact admitted base reference、版本及 digest。
- namespace、lineage、reconstruction rules、verification rules、TTL、nonce 與 envelope reference。
- 允許的效果範圍及上一個已驗證回復點。

缺一即標記 `8D_INDEX_GAP` 或 `8D_CAPABILITY_GAP`，不得用傳統搜尋、模型推測、舊 receipt 或普通複製補位。

## 現有工具綁定

只復用 `/home/taiji_admin/Taiji_Hub/services/w7tp_gt_mesh_v21`：

- 建包：`w7tp_gt_mesh.packet:build_transfer`
- 接收重構：`w7tp_gt_mesh.receiver:MeshReceiver.receive`
- 執行容器：`w7tp_gt_mesh.app:MeshRuntime`
- 網路送達：`w7tp_gt_mesh.transport:MeshTransport.send`
- 狀態觀測：`w7tp_gt_mesh.inventory:collect_snapshot`
- 儲存與收據：`w7tp_gt_mesh.journal:MeshStorage`

實際單次測試固定使用 `queue_on_failure=False` 或等價不排隊行為，避免失敗封包殘留後續重送。不得用 CLI cycle/retry 代替有界測試。

## 執行與停止條件

1. 先觀測全部目標的 identity、LAN、Receiver、基座引用與 digest；不啟動服務。
2. 只對基座閉合且目標座標未漂移的節點建立封包。
3. 先做單一 Sender→Receiver；必須同時取得 `PASS_RECEIVED` 與 `PASS_EXACT_CANONICAL_JSON_HASH`。
4. 再對其他已准入節點使用同一邏輯 packet；每節點獨立保存 receipt，不以部分成功冒充全體成功。
5. LAN 失敗必須留下本次不可達證據後才可使用已登記 VPN；VPN 成功不得回報 LAN 成功。
6. 重構結果、target digest、coordinate 或 lineage 任一不一致立即停止，不自動改基座、降級 direct copy 或重試其他版本。
7. 只有全部指定節點的本次收據與重新觀測閉合，才能回報該有界測試 PASS；不自動提升 canonical、D8、部署或外部效果。

## 成功與反例

成功：兩個已登記節點有相同已准入基座；LAN 可達；一個邏輯 packet 在各 Receiver 本地重構相同 target digest，各自產生精確重構 receipt。

HOLD：節點可 ping 但 Receiver 未監聽、基座只有物件數沒有正式 ref/digest、設定名稱與 live identity 衝突、或只能由 VPN 可達但尚未證明 LAN 不可用。

BLOCK：要求忽略 target digest、用模型猜回內容、把 VPN/SSH/Git 當 D6、用一個無 recipient binding 的封包廣播至不同身分／基座節點，或未授權產生外部效果。

## 固定輸出

區分 `OBSERVED / RECONSTRUCTED / INFERRED / CONFLICT / UNKNOWN`，並輸出：

```text
STATE=
CURRENT_POSITION=
PROVEN_STATE=
CANDIDATE_STATE=
HOLD_STATE=
CONFLICTS=
UNKNOWNS=
AUTHORITY=
NEXT=
```

`NEXT` 只給第一個阻斷點的最短有效動作。
