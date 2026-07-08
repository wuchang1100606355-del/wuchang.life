# W7TP P1 Intent Automation Architecture Lock

STATE=W7TP_P1_INTENT_AUTOMATION_ARCHITECTURE_LOCK
LEVEL=P1_INITIAL_AUTOMATION
GOAL=使用者只表達自然語言意圖，後續由總場自動封包化、分派、驗證、回報、封證；高風險 HOLD 等使用者批准。

## Current MVP

目前狀態為人工貼入 MVP：

USER_INTENT
-> ChatGPT converts intent to Total Field command
-> User pastes command into target shell
-> Local node executes
-> Terminal returns STATE/RUN_ID/OUT/REPORT
-> ChatGPT interprets PASS/HOLD/NEXT

## P1 Target

P1 目標：

USER_INTENT
-> INTENT_PACKET
-> TOTAL_FIELD_INBOX
-> DISPATCHER
-> WORKER_ADAPTER
-> VERIFIER
-> PASS_OR_HOLD
-> SEAL_LEDGER
-> USER_REPORT

## Required Components

1. packet inbox
   - path: runtime/total_field/inbox/
   - purpose: receive intent packets and task packets.

2. dispatcher
   - purpose: classify target worker.
   - targets:
     - taiji01
     - taiji03
     - codex_worker
     - router_worker
     - verifier_worker

3. worker adapters
   - taiji01 adapter: repo/source packet/report tasks.
   - taiji03 adapter: edge VM/static site/local service tasks.
   - codex adapter: candidate patch/report generation.
   - router adapter: read-only first; write actions require HOLD approval.
   - verifier adapter: risk gate.

4. verifier
   - blocks:
     - secret/token/password/private key
     - member plaintext
     - raw audio
     - DB write
     - deploy
     - restart
     - router write
     - external API cost risk

5. human approval gate
   - required for:
     - DB_WRITE
     - DEPLOY
     - RESTART
     - ROUTER_WRITE
     - SECRET_RISK
     - MEMBER_PLAINTEXT_RISK

6. seal ledger
   - path: runtime/total_field/seal_ledger/
   - each run must record:
     - STATE
     - RUN_ID
     - INPUT_PACKET
     - WORKER
     - VERIFIER_RESULT
     - REPORT
     - NEXT

## Automation Rule

Low-risk read-only tasks may run automatically.

High-risk tasks must enter HOLD and wait for explicit user approval.

## Authority Rule

Terminal output and local reports are the source of truth.

ChatGPT and Codex outputs are candidate material only.

## P1 Completion Definition

P1 is complete only when:

1. intent packet can be written to inbox.
2. dispatcher can classify worker.
3. worker can produce candidate result.
4. verifier can PASS/HOLD.
5. seal ledger records run_id.
6. user receives final report.
7. high-risk actions are blocked automatically.

