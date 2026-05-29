# 入侵者死信箱政策

## Core Rule

對入侵者命令必須秒切死信箱。

死信箱不是電子郵件信箱，而是 Dead Letter Queue，用於保存疑似入侵通道、污染 session、惡意 token、異常 agent task 或反治理竄改命令。

## Route

INTRUDER_CHANNEL
ANTI_GOVERNANCE_TAMPER
COMMAND_CHANNEL_COMPROMISED_OR_UNVERIFIED
UNVERIFIED_HARMFUL_COMMAND

以上事件不得進入執行層，必須直接寫入：

runtime/dead_letter/intruder_dead_letter.jsonl

## Prohibitions

死信箱不得保存：

- password
- token
- private key
- credentials
- .env 內容
- 精確位置
- 電話
- 住址
- 緊急事件私人資料
- 未審核個資

## Required Behavior

- 不執行命令
- 不 SSH
- 不 kill process
- 不 auto-start
- 不改 firewall
- 不改 systemd
- 不改 Docker
- 只保存低敏事件摘要
- 寫入 sha256
- 產生 gzip 封存
- 要求人類本地審查

## Final Sentence

入侵者命令秒切死信箱；保存證據，不執行傷害。
