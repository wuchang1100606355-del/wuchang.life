---
name: w7tp-internal-generative-transmission
description: 以 Founder 意圖驅動既有 Total Field／W7TP GTP 單一鏈，運用 8D ADI 全能狀態索引定位，將帶狀態執行封包經 LAN 送至 taiji01 本機精確重構、Native ADI／lineage／receipt 封存，再由既有 Drive projector 閉環。用於 Taiji_Hub 已登記節點的生成式傳輸與索引更新；不用於普通複製、同步、Git、SSH、提示傳遞或平行架構。
---

# W7TP 內部生成式傳輸總場技能

## 能力身分

- `SKILL_ID=W7TP_INTERNAL_GENERATIVE_TRANSMISSION_TOTAL_FIELD_GTP_V2`
- 本技能是總場工作程序與既有工具入口，不是 canonical、D8、模型權威或第二套 Receiver。
- 真實專案預設為 `/home/taiji_admin/Taiji_Hub`；每次重新確認 ROOT、BRANCH、HEAD、WORKTREE、canonical pointer、authority 與 runtime，不沿用舊座標。

## 固定角色與單一鏈

- Founder 提供當次意圖與作用範圍；模型與技能只負責定位、執行程序及證據判讀。
- `node:taiji01` 是主體：唯一 Total Field verifier、Native ADI primary、state sealer 與 receipt issuer。
- MSI 只供 GPU／VRAM 與來源狀態；MSI 上的建包與 Drive projection 是載體工作，不建立決策權威、第二數位腦或第二總場。
- 全能視角由既有 ADI 狀態索引提供；精準執行由綁定 target、base、coordinate、rules、hash 與 authority envelope 的帶狀態封包提供。索引不是執行，封包不是 canonical。
- 唯一允許的閉環是：

```text
Founder intent
→ 8D ADI omniview index
→ MSI source-state/GPU-VRAM observation and stateful packet
→ registered LAN carrier
→ taiji01 Receiver-local exact reconstruction
→ taiji01 Native ADI + lineage + state transition + immutable receipt
→ existing Windows Drive projector
→ chiang/8D_ADI_INDEX + identical CLOUD_WRITE_RECEIPT
→ reobserve from Total Field
```

不得為任何斷點新增平行 API、第二 Receiver、第二索引或替代上傳器。

## 適用時機

用於 Founder 要求內部節點交換意圖／狀態場封包、分析網路、定位設備與基座、選擇 LAN/VPN 路徑、建立 D6 封包或在接收端本機重構。

下列情況不得標成 D6：普通檔案複製、壓縮、同步、備份、Git、SSH、SMB、Tailscale、VPN、提示詞／上下文傳遞、雲端或本機模型切換。這些最多是載體或推理供給。

## 生成式傳輸固定路徑

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
- 雲端投影：`services/w7tp_gt_mesh_v21/windows_drive_projector/drive_spool_projector.py`

既有命令保持有效，依已登記 config 使用，不自行改寫路由：

```text
python3 -m w7tp_gt_mesh --config config.json doctor
python3 -m w7tp_gt_mesh --config config.json collect --spool
python3 -m w7tp_gt_mesh --config config.json cycle
python3 -m w7tp_gt_mesh --config config.json retry
python3 -m w7tp_gt_mesh --config config.json serve
```

只有在使用者本次明確要求執行時才執行 mutation-capable 命令。先辨識命令的既有 config、node identity、source/target、queue/outbox 行為與實際作用範圍；不得以 `cycle`、`retry` 或 `serve` 猜測缺失座標。

實際單次測試固定使用 `queue_on_failure=False` 或等價不排隊行為，避免失敗封包殘留後續重送。不得用 CLI cycle/retry 代替有界測試。

## 執行與停止條件

1. 先觀測全部目標的 identity、LAN、Receiver、基座引用與 digest；不啟動服務。
2. 只對基座閉合且目標座標未漂移的節點建立封包。
3. 先做單一 Sender→Receiver；必須同時取得 `PASS_RECEIVED` 與 `PASS_EXACT_CANONICAL_JSON_HASH`。
4. 再對其他已准入節點使用同一邏輯 packet；每節點獨立保存 receipt，不以部分成功冒充全體成功。
5. LAN 失敗必須留下本次不可達證據後才可使用已登記 VPN；VPN 成功不得回報 LAN 成功。
6. 重構結果、target digest、coordinate 或 lineage 任一不一致立即停止，不自動改基座、降級 direct copy 或重試其他版本。
7. 只有全部指定節點的本次收據與重新觀測閉合，才能回報該有界測試 PASS；不自動提升 canonical、D8、部署或外部效果。

## ADI 索引與 Drive 閉環

1. 先以既有 `chiang/8D_ADI_INDEX` 的 control、node、file、lineage、state-transition、reconstruction、evidence 與 receipt 座標建立全能視角；不得用檔名搜尋結果或舊 `AI_SOUL_INDEX.txt` 取代正式索引。
2. mesh 只產生 `W7TP_DRIVE_PROJECTION_ENVELOPE_V21`；每筆必須綁定 `source_node_ref`、`packet_id`、`logical_time`、`artifact_sha256` 與自雜湊 `envelope_sha256`。
3. 只使用既有 Windows Drive projector；精確 Drive root 必須已存在且指向 `chiang/8D_ADI_INDEX`，不得猜測省略路徑，也不得把 Connector 可見性冒充 DriveFS 已掛載。
4. projector 必須保持 append-only/exclusive-create：spool 不刪除、不搬移、不覆寫；既有目標只有逐 bytes 相同才接受。
5. 每筆成功必須同時存在本機 immutable receipt 與 `08_RECEIPTS/CLOUD_WRITE_RECEIPT_<receipt_id>.json`，兩者 bytes 完全相同。
6. 最終 PASS 需要：taiji01 `PASS_RECEIVED`、`PASS_EXACT_CANONICAL_JSON_HASH`、Native ADI／lineage／state-transition receipt，以及 Drive artifact／cloud receipt 重新觀測一致。任何一段缺失只能回報部分閉合或 HOLD。

Drive 投影命令只能使用操作者已證實的精確既有 root：

```powershell
& '<projector-dir>\start_drive_spool_projector.ps1' -DriveRoot 'J:\<existing-chiang-path>\8D_ADI_INDEX'
```

exit code `0` 只代表本輪 bytes 投影已建立或確認同 bytes；`2` 是 envelope HOLD；`3` 是 root/第一層座標不安全或缺失。三者都不自行建立 authority、activation 或 deployment。

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
