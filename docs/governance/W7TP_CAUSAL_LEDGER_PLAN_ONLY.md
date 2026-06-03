# W7TP Causal Ledger Plan-Only Governance
# W7TP 因果帳本治理層

Status: plan-only / schema + packet builder + analyzer
Scope: Wuchang Smart Cloud / XiaoJ Intent Field / W7TP / EAMTP-7D

## 1. Purpose

W7TP Causal Ledger Layer converts system events into auditable causal event packets.

It absorbs the useful architecture concepts from causal chain, DAG, vector clocks, CRDT, Byzantine-aware CRDT, compressed causal clocks, and temporal-causal graph auditing.

It does not implement a production blockchain or financial ledger.

## 2. Core Concepts

Useful concepts:

- causal ledger instead of total-order blockchain
- partial order instead of forced global total order
- DAG event dependency graph
- happens-before relation
- vector clock / compressed clock
- CRDT convergence
- Byzantine-aware causal linkage
- parent set immutability
- temporal-causal graph auditing
- red-team causal attack model

## 3. W7TP Mapping

Traditional blockchain:
- global total order
- single chain
- mempool bottleneck
- consensus-heavy transaction ordering

W7TP causal ledger:
- event DAG
- parent event references
- causal clock
- EAMTP packet linkage
- policy gate
- dead-letter for forged causal state
- pending_review for high-risk causal event
- local-first redacted event records

## 4. Allowed Behaviors

The system may:

- create causal event packets
- record parent event hashes
- classify causal event risk
- generate causal ledger reports
- validate event packet structure
- classify red-team causal threats
- create plan-only DAG summaries
- propose CRDT-safe merge strategies
- propose compressed clock strategies
- route high-risk causal events to pending_review
- route hardwall causal attacks to dead_letter

## 5. Forbidden Behaviors

The system must not:

- create production cryptocurrency
- perform financial settlement
- write Odoo/Postgres production ledgers automatically
- overwrite balances by LWW
- accept client-side forged vector clocks as authority
- send raw PII to cloud
- trust unauthenticated parent sets
- auto-merge financial CRDT conflicts
- execute smart contracts
- bypass human review for money, access control, policy, or identity

## 6. Red-Team Hardwalls

Dead-letter:

- forged vector clock
- client-side timestamp authority for money
- parent-set mutation after event creation
- unrestricted LWW balance merge
- unsigned financial delta
- raw PII causal graph to cloud
- SPV-only high-risk security decision
- topology path supplied without proof
- double-spend causal conflict
- forged event dependency path

Pending review:

- CRDT merge plan
- node clock compression change
- causal graph audit alert
- offline sync reconciliation
- access control event merge
- POS / points / member service causal event
- governance policy causal event

## 7. Canonical Statement

小J / W7TP 的因果帳本層不是傳統區塊鏈，
也不是自動金融帳本。

它是小J意圖場內的可稽核事件因果層，
用來記錄 EAMTP 封包、操作單、審核、結果、節點事件、Odoo/POS/LINE/梅林治理事件之間的因果關係。

所有高風險因果事件必須經過 Policy Gate；
所有偽造時鐘、偽造父節點、雙重支付、未簽章金融狀態、原始個資上雲，都必須 dead_letter。
