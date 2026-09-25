# W7TP Total / Branch Runtime Solidification Spec

STATE=SPEC_W7TP_TOTAL_BRANCH_RUNTIME_SOLIDIFICATION_V01

## Fixed Authority Statements

Codex is a candidate development agent under Total Field governance, not the authority of Total Field.
Codex 是總場治理下的候選開發代理，不是總場權威。

LLM is the public-relations layer of Total Field, not the authority of Total Field.
LLM 是總場的公關層，不是總場的權威層。

## 1. Why Total / Branch Before Codex

Total Field and Branch Field must be solidified before Codex is attached because development agents are tools under governance, not governance itself. The operating structure must define authority, registries, queues, verifier gates, risk policy, evidence, commit queue, release manifest, and seal before any candidate implementation can be accepted.

One sentence rule:

```text
先把總場變成作業系統，再讓 Codex 成為總場底下的工具。
```

## 2. Total Field Authority Definition

Total Field / 總場 is the authority layer. It owns governance, packet registration, schema registry, verifier registry, risk policy, work queue, evidence chain, commit queue, release manifest, and seal/tag state.

Total Field decisions are limited to:

```text
ALLOW
HOLD
BLOCK
VERIFY_READY
STAGE_READY
COMMIT_READY
RELEASE_READY
SEALED
```

## 3. Branch Field Controlled Execution Definition

Branch Field / 分場 is a limited execution and projection layer. It can run controlled local lookup, local verifier subsets, local route tables, template sets, and projections for UI, POS, voice, browser, property, association, website, or custom branch contexts.

Branch Field cannot grant Total Field authority, read member plaintext, capture payment without human review, deploy, or read secrets.

## 4. Codex Candidate-Only Definition

Codex receives only `W7TP_CODEX_TASK_PACKET` and returns only `W7TP_CODEX_RESULT_PACKET`. Codex can propose candidate code, candidate docs, candidate reports, verify plans, exact stage plans, and commit plans.

Codex cannot become authority, cannot override verifier decisions, cannot auto-stage, cannot auto-commit, cannot deploy, cannot restart services, cannot write DB, cannot read secrets, and cannot read member plaintext.

## 5. LLM Public-Relations Layer

LLM / local model is a public-relations and semantic translation layer. It can help phrase safe answers, translate intent, and provide candidate capability. It cannot become authority, change verifier decisions, grant identity, approve payment, deploy, or treat inferred text as truth.

## 6. Verifier Final Decision

Verifier is the final decision maker. Candidate outputs from Codex, Branch Field, or LLM remain untrusted until verifier accepts the evidence and emits a decision. A `PASS` result means ready for review, not automatic release.

## 7. Work Item / Codex Task / Result Packet Flow

```text
Total Field work item
  -> W7TP_CODEX_TASK_PACKET
  -> Codex candidate implementation
  -> W7TP_CODEX_RESULT_PACKET
  -> verifier review
  -> exact stage plan
  -> commit plan
  -> seal/tag only after explicit human authorization
```

## 8. Exact Stage / Commit Plan

Every Codex result must include an exact file list. The next action must be:

```text
git diff -- <exact files>
then exact stage only
```

No broad staging is allowed.

## 9. Forbidden Git Operation

`git add .` is forbidden. Automatic staging and automatic commits are forbidden. Codex must not run `git add`, `git commit`, deployment commands, service restarts, or release commands without explicit human authorization and an exact packet.

## 10. Safety Limits

Required hard flags:

```text
SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
DB_WRITE=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
EXTERNAL_API_CALL=FALSE
MODEL_DOWNLOAD=FALSE
LLM_AUTHORITY=FALSE
CODEX_AUTHORITY=FALSE
AUTO_STAGE=FALSE
AUTO_COMMIT=FALSE
```

This round is local CLI/runtime solidification only. Reports may be written under `runtime/total_field/`. No external API call, model download, new port, service restart, deployment, DB write, secret read, or member plaintext read is permitted.
