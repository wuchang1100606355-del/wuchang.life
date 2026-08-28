# Total Field 控制／硬體調度最小延伸候選

狀態：**CANDIDATE_NOT_CANONICAL_NOT_PROMOTED**。此文件與程式不取代 `W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1`，不改 active pointer，也不建立第二套傳輸或權威架構。

## 權威與節點角色

- 總場是唯一 D8 決策／控制權威；`PRIMARY_DECISION_ENGINE=8D_ADI`。
- Founder architecture 是設計權威與 provenance，不是另一個 runtime authority endpoint。
- taiji01 是 Total Field authority/verifier、Native ADI primary、state sealer 與 receipt issuer。
- MSI Windows 是 Founder interface；MSI WSL 只負責 build/test、GTP packet generation 與 Drive projection，不形成第二權威。
- taiji02、taiji03、cloud 等 Linux workers 是 execution nodes。
- Open WebUI 只是自然語言操作介面，不是總場權威、正典或最終決策者。

## 既有架構沿用

- 傳輸只使用既有 `w7tp_gt_mesh` V2.1 carrier、reconstruction、object store、replay ledger 與 append-only journal。
- Placement 以 `w7tp_runtime.state_field.controlled_experiment_v1.bridge.PlacementPlanner` 為基底，新增 `TotalFieldPlacementPlanner` 的 Node capability view；沒有平行 scheduler core。
- 簽章驗證以注入的 `tools.total_field_ed25519_backend:Ed25519DetachedSignatureBackend` 為 production binding。候選不讀私鑰、不保存 raw key、不實作第二套 root of trust；測試只注入不含金鑰的 deterministic verifier contract。

## M8 Node／resource 與增量 ADI state field

每次 placement 由既有 mesh inventory 形成三個互相綁定的候選物件：

1. `NodeManifest`：node_id、可見 container engines、snapshot hash；只屬 evidence。
2. `NodeResourceState`：CPU、可用 RAM、可用 disk、GPU count/memory；綁定同一 snapshot hash。
3. `ExecutionLease`：總場 taiji01 簽發、目標節點、resource request 與 snapshot hash。

選擇順序固定為「先排除 UNKNOWN／不足／缺必要 container engine，再依 GPU surplus、GPU memory surplus、RAM surplus、CPU surplus、disk surplus、node_id 做 deterministic best fit」。結果順序不受 inventory 輸入順序影響。

節點驗證完成後寫入 incremental ADI state：`prior_state_ref → task_ref → verification_receipt`，logical time 必須單調遞增；所有 reservation、execution、verification 與 ADI records 都是 append-only。

## RESERVE／EXECUTE／VERIFY 與既有 Lease 狀態機

控制流程使用三個 phase，但 lease state 不另造：

- RESERVE：`ISSUED → ACKNOWLEDGED`
- EXECUTE：`ACKNOWLEDGED → RUNNING → RESULT_CANDIDATE`
- VERIFY：`RESULT_CANDIDATE → ACCEPTED`
- 過期與拒絕分別落在 `EXPIRED`、`REJECTED`

節點只在下列條件全部成立時進入 RESERVE：總場 authority active、未過期、scope 精確、taiji01 owner binding 正確、Ed25519 signature 通過、envelope/hash/TTL/nonce/replay/logical-time 通過、target node 與 snapshot hash 相符、資源仍足夠、policy 允許。

## 容器與服務能力

預設 policy 只允許：

- 名稱符合 `w7tp-canary-*` 的專用 container；run 時必用 immutable `@sha256:` image allowlist。
- 名稱符合 `w7tp-canary-*.service` 的專用 system/user unit。
- Container run 將 envelope 的 CPU、RAM、GPU count、GPU memory evidence label 與 pids limit cross-bind 到 Docker/Podman argv；不接受 envelope 與 engine args 不一致。

Generic existing-container adapter contract 已具備 inspect/start/stop/remove 能力，但必須同時具有：

- 新 D8 scope `MANAGE_EXISTING_CONTAINER`；
- exact 64-hex container ID allowlist；
- 執行前 current-state SHA-256 完全相符。

目前預設 authority 只設計 `EXECUTE_CANARY`，所以任何既有／正式 container live action 都會在 policy 前段被拒絕。正式 services 不符合 canary unit 名稱，也必定拒絕。

## 目前 authority gap

Live evidence 顯示目前 `ACTIVE_TOTAL_FIELD_AUTHORITY` 只含 `PROMOTE_ACCEPTED_CANDIDATE`，且 `expires_at=2026-08-21T11:47:01Z`；runtime profile 目前 `active=false`、`cross_node_authority_allowed=false`、`execution_authority=false`。因此本候選在目前 authority 狀態下必須 HOLD，不能執行 container/service action。

要啟用 canary 控制，必須由既有 Total Field root 建立一份新的、未過期、taiji01-owned active authority，scope 精確包含：

- `CROSS_NODE_CONTROL`
- `HARDWARE_SCHEDULE`
- `EXECUTE_CANARY`

若未來要管理既有 container，還要另加 `MANAGE_EXISTING_CONTAINER`，並經獨立 allowlist 與 live state hash 驗證；不得由本候選自行擴權。

## 升格條件

1. Founder／總場對本 profile 另行審查，產生新的 canonical successor 或明確 profile promotion；本候選不能自行升格。
2. taiji01 active authority、Ed25519 verifier、scope、expiry、node binding 與 persistent replay ledger 都有 live evidence。
3. Existing mesh receiver 在 reconstruction/hash 驗證後加入單一 control-artifact hook；不另開 listener。
4. 五節點以專用 canary 完成 RESERVE／EXECUTE／VERIFY、cross-node receipts、故障／過期／重播／漂移驗證。
5. 所有 plan、ExecutionLease 與 receipts 都同時提供 deterministic `human_summary_zh_tw`，精確呈現意圖、總場理由、節點／容器、資源依據、實際結果、未知／風險；JSON 不是人類唯一輸出。

## 部署整合點

- Source package：既有 versioned install `current/total_field_control`。
- Runtime config：`/etc/w7tp-gt-mesh-v21/total_field_control.json`；目前候選檔 `enabled=false`。
- Authority artifacts：沿用 `runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json` 與 `configs/total_field/active_total_field_authority_runtime_v1.json`，不得複製或重建 receipt。
- Receiver integration：既有 `w7tp_gt_mesh.receiver` 完成 carrier reconstruction 後，把 schema `W7TP_TOTAL_FIELD_CONTROL_TASK_CANDIDATE_V1` 交給 `TotalFieldNodeAgent.process`；其餘 transport 行為不變。
- systemd：不新增第二個 service。未來只對既有 `w7tp-gt-mesh-v21.service` 增加 control config path；在 authority gap 解決前保持 disabled，不 restart 正式服務。
