# DIRECT_SHORTEST_PATH_GTP_POLICY_20260613_072439

## 中文

本文件建立 Direct Shortest Path GTP repo gate，讓 W7TP / XiaoJ / Five-in-One / 8D Packet 的下一步不再被普通 UI、普通 agent、普通 browser extension 或一般 workflow automation 的思路帶偏。

### 為何之前偏航

之前的工程排序容易把「比較看得見」的 UI、Action Bus、Broker、Avatar、Connector 放在主鏈前面。這會讓 W7TP / XiaoJ 從生成式傳輸系統被降維成普通產品功能，導致 State、Coordinate、Hash、Packet、Generative Transfer 的核心鏈節沒有先被固化。

### 為何記憶不等於硬 gate

模型記憶只能提醒，不會約束 repo 內每一次 agent 執行。記憶不夠，必須把生成式傳輸優先寫成 repo gate。

### 為何要把規則寫進 repo

repo 內的 `AGENTS.md` 是工程入口規則。把 Direct Shortest Path、Generative Transfer Priority、Main Chain、Redteam、No Detour 寫進 repo，可以讓後續 Codex / agent 在讀取專案時先接受硬 gate，而不是依賴外部對話上下文。

### 生成式傳輸是 W7TP / XiaoJ 主幹

8D SDK 定義封包；Generative Transfer Deploy 定義封包如何安全流動。沒有 Generative Transfer Deploy，封包只是一組結構，還不是可驗證、可重建、可留證、可行動的主幹傳輸鏈。

### 後續禁止先做 UI / Action Bus / Broker

Codex 之後不得先做 UI / Action Bus / Broker。若 `W3_GENERATIVE_TRANSFER_DEPLOY` 尚未完成並被 Master Deploy Index 索引，下一步必須是它。

不得把小J降維成普通 AI agent、chatbot、browser extension 或 workflow automation。

## English

This document establishes the Direct Shortest Path GTP repo gate. W7TP / XiaoJ / Five-in-One / 8D Packet work must not be diverted into ordinary UI, ordinary agent, ordinary browser extension, or ordinary workflow automation patterns.

### Why Drift Happened

Prior sequencing could over-prioritize visible surfaces such as UI, Action Bus, Broker, Avatar, or Connector work. That puts product surfaces before the trunk chain and risks reducing W7TP / XiaoJ from a generative transmission system into ordinary product plumbing.

### Why Memory Is Not A Hard Gate

Model memory can remind an agent, but it does not bind every repo execution. The priority must live in the repository itself so future agents read it before planning.

### Why This Belongs In The Repo

`AGENTS.md` is the project-level operating gate. Encoding Direct Shortest Path, Generative Transfer Priority, Main Chain, Redteam, and No Detour rules in the repo makes the rule auditable, hashable, and commit-bound.

### Generative Transfer Is The W7TP / XiaoJ Trunk

The 8D SDK defines the packet; Generative Transfer Deploy defines how the packet flows safely. Without Generative Transfer Deploy, the packet is only a structure, not a verifiable, reconstructable, evidenced, action-ready transfer chain.

### Next Step Rule

Codex must not start with UI, Action Bus, or Broker work. If `W3_GENERATIVE_TRANSFER_DEPLOY` is missing or not indexed, the next required step is `W3_GENERATIVE_TRANSFER_DEPLOY`.

## Policy Packet

- packet: `packets/redteam/operation_windows/DIRECT_SHORTEST_PATH_GTP_POLICY_20260613_072439.json`
- verifier: `scripts/verify/verify_direct_shortest_path_gtp.sh`
- required_next_step_if_missing: `W3_GENERATIVE_TRANSFER_DEPLOY`
- main_chain: State -> Coordinate -> Hash -> Packet -> Generative Transfer -> Verify -> Reconstruct -> Evidence -> Action
