# W7TP Intent Build Commandization

## Definition

Intent build opens a Construction Field from an Intent Packet, then moves through document packet context, sandbox index scoping, Cloud Candidate generation, Total Field Receipt, Subfield Check, and Total Field Decision.

Governance sentence:

```text
意圖開場，文件入場，索引開範圍，雲端出候選，分場核對，總場決選。
```

This is not schema first and not file landing first. The executable path starts from operator intent, creates bounded scope, allows cloud candidate proposals only, and reserves approval for Total Field decision.

## CLI

Tool:

```bash
python3 tools/w7tp_intent_build_cli.py <subcommand>
```

Subcommands:

- `open-intent`: create `INTENT_PACKET.json` from `--intent-text`.
- `open-field`: create `CONSTRUCTION_FIELD_PACKET.json` from an Intent Packet.
- `index-source`: write packets to a sandbox JSONL index only.
- `open-scope`: create bounded scope from Intent Packet and sandbox index.
- `make-cloud-request`: create a dry-run cloud candidate request.
- `mock-cloud-response`: create one good and one bad mock cloud candidate.
- `receive`: convert candidates into Total Field receipts and reject bad candidates at receipt gate.
- `subfield-check`: run SOURCE, SCOPE, RISK, TECH, EVIDENCE, and AUTHORITY checks on received candidates.
- `decide`: produce the Total Field final decision.
- `seal`: seal the full chain and write `SHA256SUMS.txt`.
- `run-demo`: run the full dry-run chain in one command.

## Flow

```text
Intent text
  -> Intent Packet
  -> Construction Field Packet
  -> sandbox jsonl index
  -> Bounded Scope From Intent Packet
  -> Cloud Candidate Request From Scope Packet
  -> Mock Cloud Candidate Responses
  -> Total Field Receipts
  -> Subfield Report
  -> Total Field Final Decision Packet
  -> Intent Build Full Chain Seal
```

## Safety Boundary

- No real cloud call.
- Cloud candidates are candidates only.
- Cloud cannot decide approval.
- Cloud cannot claim the artifact is landed.
- Cloud cannot request production DB write.
- Cloud cannot request deploy, restart, router write, or git push.
- No secret/env/token/password reading.
- No member plaintext reading.
- No raw audio saving.
- No DB write.
- No deploy.
- No service restart.
- No router write.
- No git add, commit, or push.
- No Odoo module upgrade.

Hard risk flags:

```text
SECRET_READ
MEMBER_PLAINTEXT_READ
RAW_AUDIO_SAVED
DB_WRITE
SERVICE_RESTART
DEPLOY
ROUTER_WRITE
PRODUCTION_RELEASE
GIT_PUSH
```

## Demo

```bash
RUN_ID=INTENT_BUILD_COMMANDIZATION_$(date -u +%Y%m%d_%H%M%S)
python3 tools/w7tp_intent_build_cli.py run-demo \
  --intent-text "驗證意圖式建構指令化" \
  --out "runtime/total_field/intent_build_cli_demo/${RUN_ID}"
```

Expected output:

```text
STATE=PASS_INTENT_BUILD_COMMAND_DEMO
FINAL_DECISION=APPROVE_TO_SANDBOX_INDEX
GOOD_RECEIPT_DECISION=RECEIVED_FOR_SUBFIELD_CHECK
BAD_RECEIPT_DECISION=REJECT_AT_RECEIPT
DB_WRITE=FALSE
CLOUD_REAL_CALL=FALSE
GIT_ADD=FALSE
GIT_COMMIT=FALSE
```

## Non-Goals

This commandization is not schema-first landing, not file-first landing, and not free generative completion. It is an intent-first, scope-bounded, candidate-only, Total Field decided construction workflow.
