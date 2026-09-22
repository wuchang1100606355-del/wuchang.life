---
name: w7tp-router-wireguard-control
description: "以既有 Total Field Merlin 路由器治理鏈，建立 RT-BE86U WireGuard 雙棧入口、逐裝置 peer、LAN 直連與路由器 DNS 的 8D ADI 調整封包。用於路由器 VPN、固定公網 IPv4、IPv6、WireGuard、LAN/DNS、peer 新增或切換；讀取與計畫可直接執行，任何路由、NVRAM、防火牆、服務重啟或 VPN 切換均須單次精確 D8 授權並重新觀測。"
---

# W7TP Router WireGuard Control

## Purpose

把使用者的路由器網路意圖接到既有單一總場鏈：

`merlin_intent_driver -> merlin_apply_queue -> merlin_approval_gate -> merlin_human_execution_checklist -> merlin_execution_result_recorder`

不得建立第二套路由器控制架構，不得把 VPN、SSH、Git 或檔案傳輸稱為 D6。

## Required reference

執行前讀取 `references/total-field-capability-contract.json`。該檔是能力契約，不是 D8 或正典權威。

## Workflow

1. 唯讀確認 repository root、branch、HEAD、target-path worktree 狀態及目前 Total Field authority runtime。
2. 將請求映射到一個精確 intent：
   - `observe_status`
   - `lan_dns_direct_plan`
   - `wireguard_dual_stack_plan`
   - `wireguard_peer_plan`
   - `wireguard_cutover_plan`
   - `wireguard_disable_plan`
3. 執行：

   `python3 .skill-build/w7tp-router-wireguard-control/scripts/router_total_field_adapter.py --intent <INTENT> --note '<REDACTED_NOTE>'`

4. 僅把工具回傳的 `OBSERVED` 當現況；`PLAN`、`CANDIDATE`、`HOLD` 不得升格。
5. 若請求有副作用，必須同時具備：精確 target/preimage、單一 mutation、回退規則、重觀測規則、短時效單次 D8。缺一即回傳 `HOLD_D8_ROUTER_NETWORK_EFFECT_NOT_REGISTERED`，不得用聊天同意、模型判斷或一般管理權取代。
6. WireGuard Server 與至少一個外部 peer 完成 IPv4、IPv6、DNS、LAN access 重觀測前，不得停用 Tailscale 備援。

## 8D projection

- D1 Intent: 路由器作唯一遠端 VPN 入口；區網裝置各自直連路由器與路由器 DNS。
- D2 State: 區分現況觀測、計畫候選、已核准、已執行、已回退。
- D3 Coordinate: RT-BE86U、WAN/LAN/WireGuard 介面、peer 槽位與精確設定鍵。
- D4 Evidence: preimage hash、計畫 hash、去敏設定摘要、介面／listener／DNS／路由重觀測。
- D5 Execution / Policy: 一次只允許一個精確 mutation；失敗立即停止並依 preimage 回退。
- D6 Generative Transmission: `NOT_APPLICABLE_NETWORK_TRANSPORT_ONLY`。
- D7 Risk / Quarantine: 不輸出密碼、token、PSK、private key；不開放 WAN 管理面；不先切斷備援。
- D8 Envelope / Authority: Founder 單次、短時效、精確範圍、可重放防護；Skill 與模型不是權威。

## Reobservation contract

變更完成必須重新取得並比對：

- WireGuard UDP listener 與介面狀態。
- 外部 peer 的 IPv4 與 IPv6 通道。
- peer 經路由器 DNS 的解析。
- LAN 內 02、03、04 仍為直接連線，沒有任何節點成為 transit/exit node。
- 實測吞吐與設定前基線；未達要求只回報事實，不捏造「數百 M」。

## Completion boundary

只有 observable outcome、evidence、rollback、risk boundary 與 D8 scope 都通過才可 `PASS`。目前無精確 router-network D8 effect scope 時，本 Skill 的最高狀態是 `READY_LOCAL_PLAN_ONLY`。
