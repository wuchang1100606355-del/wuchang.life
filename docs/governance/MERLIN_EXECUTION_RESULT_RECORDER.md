# Merlin Execution Result Recorder Governance
# 梅林路由器人工操作結果記錄器治理規格

Status: human result record only  
Scope: XiaoJ Intent Field / W7TP / EAMTP-7D / Merlin Router Firmware

## 1. Purpose

This layer records the outcome reported by a human operator after a Merlin
manual checklist has been reviewed or followed.

It does not execute router changes.

## 2. Accepted Outcomes

- `completed`
- `abandoned`
- `rollback_needed`
- `failed`
- `observation_only`

## 3. Input Rule

The recorder reads either:

- the latest JSON file under `runtime/merlin_human_execution_checklist/`; or
- an explicitly named checklist JSON within this repository.

Only a checklist with status `manual_checklist_ready`, `auto_execute: false`,
and `executable: false` may receive a result record.

The recorder copies only safe linkage metadata:

- intent
- ticket ID and hashes
- approval record hash
- checklist hash
- source checklist path

It does not copy checklist steps or embedded source approval content into the
result record.

## 4. Safety Boundary

This recorder must not:

- login to the router
- use SSH
- call a router HTTP admin API
- write nvram or apply configuration
- reboot or restart any service
- change firewall, WAN, WiFi, VPN, SSH, or QoS settings
- store password, API key, token, private key, or credentials
- auto-execute any checklist step

Operator and note input containing credential-like markers is rejected rather
than saved or echoed as a result record.

## 5. Outputs

- `runtime/merlin_execution_result/result_*.jsonl`
- `runtime/reports/merlin_execution_result_*.md`

Both outputs are result evidence only. They are not an approval to apply router
configuration and are not proof of an automated device action.

## 6. Usage

Use the latest checklist:

```bash
python3 runtime/router/merlin_execution_result_recorder.py \
  --latest-checklist \
  --status observation_only \
  --operator human_operator \
  --note "Reviewed without configuration change."
```

Use a specified checklist:

```bash
python3 runtime/router/merlin_execution_result_recorder.py \
  --checklist-json runtime/merlin_human_execution_checklist/<checklist>.json \
  --status abandoned \
  --operator human_operator \
  --note "Stopped before any manual configuration change."
```

## 7. Canonical Statement

小J可以記錄人工承接後的結果與證據連結，
但不得登入路由器、不得 SSH、不得套用設定、不得重啟服務、
不得保存或輸出任何憑證或敏感值。
