# W7TP GT Mesh V2.1 節點部署座標

此目錄只提供部署座標、節點設定與 systemd units。總場（`authority:TOTAL_FIELD`）是唯一 D8 決策／控制權威，`PRIMARY_DECISION_ENGINE=8D_ADI`；Founder architecture 保留為設計權威與 provenance。部署包本身不升格 canonical、active pointer 或 promotion，也不把模型、節點、Git 或 transport 當成 authority。

## 拓撲

- MSI、taiji01、taiji03 與美國節點固定監聽各自可由核心網路綁定的 Tailscale 位址 TCP 9238，不綁定一般 LAN 全介面。taiji02 的即時觀測是 Tailscale userspace networking，尾網位址不在核心網卡上，因此 receiver 只監聽 `127.0.0.1:9238`，再由既有 Tailscale Serve 以 raw TCP 將 `100.111.139.7:9238` 映射至同一 receiver；Serve 只是 carrier，不建立第二個 receiver 或第二權威。
- taiji01 是 Total Field authority/verifier、Native ADI primary、state sealer 與 receipt issuer；MSI Windows 是 Founder interface，MSI WSL 只做 build/test/GTP packet generation 與 Drive projection，其他 Linux 節點是 execution workers。MSI 不建立第二權威。
- taiji02、taiji03、wuchang-us-free-node 每五分鐘採集一次低成本狀態，生成 V2.1 封包並直接傳向 taiji01 與 MSI；taiji01 傳向 MSI。
- MSI 每五分鐘採集一次，生成 V2.1 封包並傳向四個可執行遠端節點。
- MSI 同時將本機與接收封包拆分成 Drive projection envelopes，spool 位於 `/mnt/c/Users/o0930/AppData/Local/W7TP/gt_mesh_v21/drive_spool`。
- `peers` 是傳輸路由，不是 authority 路由；Git 欄位只形成 D4 evidence。taiji01 可選 Native ADI hook 只送小型 append-only reference record，不傳完整 snapshot，也不重啟或修改既有 `:9110` service。

## 動態索引範圍

各 config 的 `containers.names` 為空陣列代表不限容器名稱、讀取該節點可見的所有容器 metadata；同一探測也涵蓋 images、volumes、networks。另採集指定 system/user services、監聽 ports、CPU/GPU/RAM/disk/IP/virtualization metadata、受限安全欄位的 Tailscale discovered-node topology、少量明確 curated paths 及 Git D4 座標。不存在或不可讀的項目保持 `UNKNOWN`。

curated paths 只對已列出的 source/runtime、V2.1 canonical/schema 與相容基座做有預算的 hash；不遞迴掃描整個 repository，不讀秘密內容。可變的 object store、journal、outbox 與 receipts 固定寫入各使用者的 `.local/state/w7tp-gt-mesh-v21/<node>`，cloud 寫入 `/var/lib/w7tp-gt-mesh-v21/<node>`，不得寫進 Git root。

## systemd 選擇

- `systemd/user/<node>` 是使用者層 unit，可在 user manager 且 linger 已啟用時使用。
- `systemd/system/<node>` 是系統層 fallback，服務仍以該節點既有非 root 使用者執行；cloud 使用 system unit。
- live snapshot 顯示 MSI 與 taiji02 已有 linger，因此 manifest 優先 user unit；user manager 會提供 `XDG_RUNTIME_DIR=/run/user/<uid>`。MSI 無 passwordless sudo，不把 system fallback 當成可直接執行路徑。taiji01、taiji03 未有 linger且具 system unit 安裝條件，優先 system unit。
- 不可同時啟用同一節點的 user 與 system receiver，否則會競爭 TCP 9238。
- 每份 config 的 mesh service scope 已對準 manifest 的 preferred scope；若改用 fallback scope，須同步將該 service inventory 項目的 `scope` 改成實際層級，否則只會得到明確 `UNKNOWN`，不應猜測成 active。

每組包含：

- `w7tp-gt-mesh-v21.service`：常駐 receiver。
- `w7tp-gt-mesh-v21-cycle.service`：一次 collect/send/spool 及 durable retry。
- `w7tp-gt-mesh-v21-cycle.timer`：每 5 分鐘觸發，附 0–15 秒分散延遲。

部署前先建立 config/runtime 目錄，並將同一 GitHub commit 的 versioned source 安裝到 MSI `/home/taiji_admin/.local/opt/w7tp_gt_mesh_v21/<commit>`、其餘節點 `/opt/w7tp/gt_mesh_v21/<commit>`，再以原子 `current` 指向該版本。`current` 必須同時含頂層 `w7tp_gt_mesh`、既有 `w7tp_runtime.state_field` 子集、V2.1 canonical 與 schema；遠端節點不依賴 repository checkout。將該節點 config 複製為 manifest 指定的 `config.json`，只選一組 unit 啟用。Python 最低版本為 3.11。

從 Windows/DrvFS 複製 unit 與 config 到 Linux 時，unit 落地權限固定為 `0644`；config 目錄與 `config.json` 必須由實際服務帳號擁有，分別使用 `0700` 與 `0600`，runtime 目錄也只給該服務帳號所需權限。不要沿用 DrvFS 顯示的 executable/world-writable mode。taiji02 啟動 receiver 後，以 `tailscale serve --bg --tcp=9238 tcp://127.0.0.1:9238` 建立尾網內原始 TCP 入口，並以 `tailscale serve status` 與遠端 `/healthz` 同時驗證；不得使用公開 Funnel。

啟動後的最小驗證是：`doctor` 通過、`/healthz` 回應 `LIVE_SERVICE_PRESENCE_ONLY`、timer 顯示下一次觸發時間、一次 cycle 產生本地 packet/carrier refs，且雙向路由各有 receiver receipt 或明確 retry record。這些證據仍不單獨建立 final authority。

## 可重現版本包

`build_release_bundle.py` 從同一個 live repository 抽取本服務、既有 state-field 核心子集、固定 V2.1 正典與 schema。它會先核對正典 hash，拒絕覆寫既有 output，排除編譯暫存檔，並為每個落地檔建立 SHA-256 manifest。`source_head` 只標成 D4 evidence，不會決定權威或生效狀態。

```text
python3 services/w7tp_gt_mesh_v21/deploy/build_release_bundle.py \
  --repo-root /home/taiji_admin/Taiji_Hub \
  --service-root /home/taiji_admin/Taiji_Hub/services/w7tp_gt_mesh_v21 \
  --output /tmp/w7tp_gt_mesh_v21/<version> \
  --source-head <pushed-commit>
```

每個版本包同時包含 `RELEASE_MANIFEST.json` 與 `HUMAN_RELEASE_SUMMARY_ZH_TW.txt`。機器 manifest 先供驗證；最後面向人的輸出固定用自然繁中說明意圖、總場理由、節點與容器、結果、風險與未知。
