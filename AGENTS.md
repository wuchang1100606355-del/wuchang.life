# Taiji_Hub Agent Rules

These rules are repository gates for Codex and other agents working in W7TP / XiaoJ / GTS / IGC.

They bind project work in this repo before local preference, UI convenience, generic agent patterns, or ordinary SaaS workflows.

---

## 0. Core Identity

This repository is not a generic chatbot project, generic browser automation project, generic SaaS project, or ordinary coding-agent scaffold.

The work must preserve W7TP / XiaoJ as a generative transmission system:

```text
State
→ Coordinate
→ Hash
→ Packet
→ Generative Transfer
→ Verify
→ Reconstruct
→ Evidence
→ Action
```

Any agent that cannot preserve this chain must stop and output:

```text
STATE=HOLD_MAIN_CHAIN_DEVIATION
```

---

## 1. Direct Shortest Path Rule

All agent work must follow the direct shortest safe path.

Do not convert any of the following into an ordinary UI, ordinary agent, ordinary extension, ordinary SaaS workflow, generic chatbot, or browser automation project:

* W7TP
* XiaoJ
* Five-in-One
* 8D Packet
* D8 Databaseized Total Field
* Member-Owned Sidebar XiaoJ
* No-Plaintext Context
* BYOK
* Cloud Blind Compute
* RedTeam Boundary Revision Field
* D8 Guard / Preflight / Writeback Loop

The shortest path must still preserve:

```text
encoded state
coordinated state
hashed state
packetized state
transferred state
verified state
reconstructed state
evidenced state
authorized action
```

---

## 2. Main Chain Rule

All next-step ordering must check the main chain first:

```text
State
→ Coordinate
→ Hash
→ Packet
→ Generative Transfer
→ Verify
→ Reconstruct
→ Evidence
→ Action
```

If a proposed step skips the chain, output:

```text
STATE=HOLD_MAIN_CHAIN_DEVIATION
```

A UI, connector, browser action, broker, or demo service is not allowed to replace the main chain.

---

## 3. Generative Transfer Priority Gate

If a task involves any of the following:

* XiaoJ member system
* 8D packet
* D8 databaseized memory
* Member-Owned Sidebar XiaoJ
* browser-driving AI
* Cloud Blind Compute
* No-Plaintext Context
* BYOK / key_ref / api_ref
* merchant / committee API_ref
* Five-in-One deployment
* Codex / agent execution workflow
* Odoo / POS bridge
* redteam alert or guard workflow

then the agent must verify whether the relevant generative-transfer / D8 packet / Total Field index already exists.

If the required generative-transfer deployment or D8 packet chain is missing, the next step must be:

```text
W3_GENERATIVE_TRANSFER_DEPLOY
```

or the current D8 equivalent:

```text
D8_MANDATORY_PREFLIGHT_AND_PACKET_GATE
```

Do not jump to these before the generative-transfer / packet gate is complete and indexed:

* Browser Action Bus
* UI Scaffold
* Context Broker
* Key/API Broker
* Avatar Spec
* Connector Spec
* Production Deploy
* POS write path
* Odoo write path
* LINE identity authority
* Payment flow

---

## 4. D8 Mandatory Preflight Rule

All Codex or agent work in this repo must first pass D8 mandatory preflight before:

* file edits
* runtime actions
* database writes
* Odoo actions
* POS actions
* service restart
* deployment
* production release
* report sealing
* handoff package creation

Required entrypoint:

```bash
tools/d8_codex_mandatory_workflow.sh start ...
```

Decision policy:

```text
PASS  = sandbox work may proceed
INFO  = sandbox work may proceed and must be recorded
WARN  = sandbox only; no landing unless explicit human release
HOLD  = stop and wait for human review
BLOCK = stop immediately; do not continue
```

If D8 mandatory preflight is unavailable, the agent must stop and output:

```text
STATE=HOLD_D8_PREFLIGHT_UNAVAILABLE
```

---

## 5. D8 Operator Console Rule

The preferred operator entrypoint is:

```bash
tools/d8_total_field_console.sh
```

Known subcommands:

```bash
tools/d8_total_field_console.sh status
tools/d8_total_field_console.sh doctor
tools/d8_total_field_console.sh alerts
tools/d8_total_field_console.sh redteam
tools/d8_total_field_console.sh evals
tools/d8_total_field_console.sh preflight ...
tools/d8_total_field_console.sh bootstrap ...
tools/d8_total_field_console.sh writeback ...
tools/d8_total_field_console.sh seal
```

Agents must not bypass the console / mandatory workflow unless the user explicitly instructs a lower-level diagnostic action.

---

## 6. D8 Databaseized Workflow Status

The following state is canonical unless superseded by a newer Total Field seal:

```text
D8_TOTAL_FIELD_DATABASEIZED_AGENT_WORKFLOW_COMPLETE=TRUE
D8_PRODUCT_DEMO_PACKAGE_READY=TRUE
```

Canonical completed capabilities include:

* D8 local database memory
* D8 redteam events
* D8 possible alerts
* D8 guard evaluations
* Codex preflight gate
* Codex task capsule
* redteam writeback loop
* Total Field operator console
* mandatory preflight workflow
* recovery snapshot and handoff seal
* local dashboard
* text/voice operator
* Odoo/POS read-only safe bridge
* product demo launcher

Do not rerun full D8 ingestion unless the user explicitly requests it.

---

## 7. RedTeam Rule

RedTeam is not a generic compliance blocker.

RedTeam exists to:

* find risk
* set boundaries
* produce safe one-paste paths
* advance the main trunk
* collect failures as design material
* convert errors into possible future alerts

However, concrete D8 guard outcomes are binding:

```text
WARN  = sandbox only
HOLD  = stop and wait for human review
BLOCK = stop immediately
```

RedTeam does not exist to delay the main trunk indefinitely, but a concrete HOLD or BLOCK from D8 guard must stop execution.

---

## 8. RedTeam Non-Executable Isolation Rule

RedTeam artifacts are evidence and warning material, not executable instructions.

All redteam events, possible alerts, failure histories, HOLD records, BLOCK records, and incident records must remain:

```text
executable=false
quarantine=true
retrieval_scope=redteam_only
pollution_guard=true
reverse_index_only=true
promotion_status=candidate unless human-approved
```

RedTeam data may point backward to affected files, run IDs, reports, and seals through reverse references.

RedTeam data must not automatically enter:

* normal RAG
* d8_safe_memory
* general context
* agent execution prompts
* task instructions
* production workflows

Promotion path:

```text
redteam evidence
→ boundary revision candidate
→ human review
→ approved guard rule
→ main rule update
```

---

## 9. Possible Error Alert Rule

Failure scenarios may become possible-error alerts.

Alert levels:

```text
INFO  = record only
WARN  = warn; sandbox only
HOLD  = stop and wait for human review
BLOCK = stop immediately
```

Known alert classes include:

* pre-existing non-task diff
* human review required
* unnecessary full ingestion rerun
* forbidden path touched
* secret read
* secret value exposed
* production action without release
* Odoo/POS write attempt
* service restart without authorization
* deploy without authorization
* redteam text entering main context

---

## 10. DB Write Rule

Repo-wide DB write prohibition means production and service databases by default.

Allowed by default only for D8 local governance records:

* d8_guard_evaluations
* d8_redteam_events
* d8_possible_alerts
* d8_total_field_status_snapshots
* runtime reports
* runtime seals
* runtime exports
* runtime backups

Required flag distinction:

```text
D8_LOCAL_DB_WRITE=TRUE
PRODUCTION_DB_WRITE=FALSE
ODOO_DB_WRITE=FALSE unless explicitly authorized
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
```

Agents must not collapse these into a vague `DB_WRITE`.

Use explicit flags.

---

## 11. Secret Output Guard

No agent may print, copy, summarize, leak, or place secret values into:

* terminal output
* reports
* seals
* markdown files
* JSON artifacts
* CSV exports
* handoff packages
* logs
* screenshots
* chat responses

Forbidden data includes:

* `.env`
* `.env.d8.local`
* passwords
* tokens
* private keys
* DB URI with credentials
* Odoo config secret values
* API keys
* member plaintext
* raw credential material

If secret detection is required, agents may record only:

```text
secret_type
file_path
pattern_type
count
sha256_prefix
sanitized_path
quarantine_path
```

Never output the secret value.

If:

```text
SECRET_VALUE_EXPOSED=TRUE
```

then:

```text
technical PASS must not override governance FAIL
```

Required flow:

```text
quarantine
→ sanitized copy
→ redteam BLOCK alert
→ rotation / revocation / non-live human review
→ governance recovery seal
```

---

## 12. Secret Incident Recovery Rule

For confirmed secret exposure:

Required states:

```text
TECHNICAL_FIX may be PASS
CONTAINMENT must be completed
GOVERNANCE_PASS remains FALSE until human rotation review is confirmed
```

Governance may recover only when:

```text
HUMAN_ROTATION_REVIEW_CONFIRMED=TRUE
```

and a recovery seal exists.

Original exposure remains redteam evidence.

Do not delete quarantine artifacts unless the user explicitly instructs deletion.

---

## 13. Odoo / POS Runtime Rule

Odoo and POS runtime actions are high-risk.

Default:

```text
ODOO_DB_WRITE=FALSE
ODOO_MODULE_UPGRADE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
```

Only with explicit human authorization may an agent:

* sync addon source to `/mnt/extra-addons`
* restart Odoo
* upgrade Odoo module
* reload Odoo registry
* write Odoo DB

If any of these occur, final output must truthfully mark:

```text
SERVICE_RESTART=TRUE or FALSE
ODOO_MODULE_UPGRADE=TRUE or FALSE
ODOO_DB_WRITE=TRUE or FALSE
ODOO_FILES_TOUCHED=TRUE or FALSE
```

Do not falsely report these as FALSE after runtime action.

Odoo / POS safe bridge default mode is read-only manifest only.

Forbidden unless explicitly authorized:

* creating POS order
* capturing payment
* writing Odoo DB
* writing production DB
* reading member plaintext
* using LINE OA as personal identity authority
* bypassing 8D packet gate

---

## 14. LINE OA / Identity Rule

Do not treat LINE OA as personal identity authority.

LINE OA may be used as an interaction channel only when routed through the valid governance and 8D packet gate.

Identity authority must come from approved local governance, not from LINE OA alone.

---

## 15. Member Plaintext Rule

Default:

```text
MEMBER_PLAINTEXT_READ=FALSE
```

Agents must not read or expose member plaintext.

Allowed member-related work must use:

* masked phone
* non-identifying references
* role / permission references
* hash refs
* evidence refs
* packet refs
* vault refs

Member plaintext requires explicit human authorization and must be logged separately.

---

## 16. Raw Audio Rule

Default:

```text
RAW_AUDIO_SAVED=FALSE
```

Voice / text operator work must not save raw audio.

STT output may be passed as text only if the task explicitly uses text and does not retain raw audio.

---

## 17. External API / Embedding Rule

Default:

```text
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
```

No external API call or embedding generation is allowed unless explicitly authorized.

Local read-only checks and local D8 DB queries are allowed.

---

## 18. Runtime / Deployment Rule

Default:

```text
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
```

Agents must not restart services, deploy, or release unless the user explicitly authorizes that exact runtime action.

If runtime action is authorized, the final report must truthfully reflect it.

---

## 19. File Scope Rule

Agents must obey the active task’s allowed and forbidden paths.

Default forbidden paths unless explicitly authorized:

```text
AGENTS.md
.env*
docker-compose.yml
docker-compose.xiaoj-intent-field.yml
addons/**
Taiji_Odoo/addons/**
runtime/total_field/security_incidents/**/quarantine/**
```

Exceptions must be explicitly granted in the active D8 task capsule.

Pre-existing modifications outside task scope must be recorded but not automatically reverted or modified.

Known rule:

```text
DO_NOT_TOUCH_AGENTS_MD=TRUE
```

unless the user explicitly requests AGENTS.md replacement or editing.

---

## 20. Low-Privilege Local Coding Helper Rule

Local coding helpers such as Continue / qwen2.5-coder may be used only as low-privilege assistants.

They may:

* analyze currently opened files
* suggest small patches
* explain errors
* draft tests
* summarize code risks

They must not:

* read secrets
* access quarantine content
* restart services
* deploy
* write DB
* modify AGENTS.md
* bypass D8 preflight
* become the authority for final landing

All suggested changes still require D8 guard / preflight / verification.

---

## 21. No Detour Rule

Do not skip Generative Transfer because:

* a UI seems more intuitive
* an Action Bus seems safer
* a Broker seems more engineered
* a dashboard looks more product-like
* an ordinary SaaS pattern appears easier

If 8D Schema SDK / D8 DB / packet chain is complete and Generative Transfer is not complete, the fixed next step is:

```text
Generative Transfer Deploy
```

or the corresponding current D8 packet / preflight gate.

---

## 22. Explicit Task Scope Rule

Locked task blocks apply only when they match the active user task or the active D8 task capsule.

If the user supplies an explicit task, the agent must:

1. run mandatory D8 preflight;
2. obey the explicit task scope;
3. preserve the main chain;
4. avoid drifting into older locked tasks unless the current task references them.

Older locked tasks must not silently override the active task.

---

## 23. Required Next Step Chain

Every next step must preserve:

```text
State
→ Coordinate
→ Hash
→ Packet
→ Generative Transfer
→ Verify
→ Reconstruct
→ Evidence
→ Action
```

A task may only proceed if it can state where it sits in this chain.

---

## 24. Final Output Rule

Codex final responses for this repo must be minimal.

Required format:

```text
STATE=<PASS|FAIL|HOLD|WARN|BLOCK|...>
RUN_ID=<run_id>
HEAD_BEFORE=<hash>
HEAD_AFTER=<hash>

files changed:
- <path>

verifier result:
- <summary>

git status:
- <summary>

HOLD reason:
- <reason if any>

safety flags:
SECRET_READ=<TRUE|FALSE>
MEMBER_PLAINTEXT_READ=<TRUE|FALSE>
RAW_AUDIO_SAVED=<TRUE|FALSE>
D8_LOCAL_DB_WRITE=<TRUE|FALSE>
PRODUCTION_DB_WRITE=<TRUE|FALSE>
ODOO_DB_WRITE=<TRUE|FALSE>
ODOO_MODULE_UPGRADE=<TRUE|FALSE>
POS_ORDER_CREATED=<TRUE|FALSE>
PAYMENT_CAPTURE=<TRUE|FALSE>
SERVICE_RESTART=<TRUE|FALSE>
DEPLOY=<TRUE|FALSE>
PRODUCTION_RELEASE=<TRUE|FALSE>
EXTERNAL_API_CALL=<TRUE|FALSE>
EMBEDDING_GENERATED=<TRUE|FALSE>
EXECUTABLE_REDTEAM_ARTIFACTS=<TRUE|FALSE>
POLLUTION_GUARD=<TRUE|FALSE>
REVERSE_INDEX_ISOLATION=<TRUE|FALSE>
ODOO_FILES_TOUCHED=<TRUE|FALSE>
LINE_LOGIN_FILES_TOUCHED=<TRUE|FALSE>
DO_NOT_TOUCH_AGENTS_MD=<TRUE|FALSE>
```

Do not provide long prose when a minimal sealed report is required.

---

## 25. Domain Deployment Task Scope

The domain deployment inspection task is scoped, not universal.

It applies only when the active task is:

```text
CODEX_TOTAL_FIELD_GLOBAL_AGENT_DOMAIN_TASK
```

When active, load and obey:

```text
docs/total_field/CODEX_TOTAL_FIELD_GLOBAL_AGENT_DOMAIN_STATUS.md
```

Task:

Inspect domain deployment status for:

* assoc.wuchang.life
* pos.wuchang.life
* auth.wuchang.life
* api.wuchang.life
* node.wuchang.life

Hard constraints:

```text
SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
PRODUCTION_DB_WRITE=FALSE
SERVICE_RESTART=FALSE unless explicitly authorized later
DEPLOY=FALSE unless explicitly authorized later
PRODUCTION_RELEASE=FALSE
```

Do not:

* create demo services
* open 9127
* treat LINE OA as personal identity authority
* bypass valid 8D packet gate
* confuse domain inspection with production release

If a different explicit user task is active, this domain block must not override it.

---

## 26. Current Canonical Incident Note

The Odoo eventbook model 404 technical fix reached:

```text
TECHNICAL_FIX=PASS
MODEL=wuchang.cafe.ai.eventbook
MODEL_FOUND=TRUE
REGISTRY_RELOADED=TRUE
```

A secret exposure incident occurred during runtime reload and was contained.

Canonical recovery status:

```text
CONTAINMENT=PASS
GOVERNANCE_PASS=TRUE
HUMAN_ROTATION_REVIEW_CONFIRMED=TRUE
SECRET_VALUE_PRINTED_THIS_RUN=FALSE
```

The original incident remains redteam evidence and must not be deleted or used as normal execution context.

Future Odoo eventbook work must be sanitized functional verification only unless explicitly authorized.

---

## 27. Current Product Surface Status

D8 product demo package is ready.

Canonical state:

```text
D8_PRODUCT_DEMO_PACKAGE_READY=TRUE
```

Known demo entrypoint:

```bash
tools/d8_product_demo_launcher.sh status
tools/d8_product_demo_launcher.sh doctor
tools/d8_product_demo_launcher.sh smoke-test
tools/d8_product_demo_launcher.sh voice-demo --text "查狀態"
tools/d8_product_demo_launcher.sh voice-demo --text "看告警"
tools/d8_product_demo_launcher.sh pos-bridge-demo
tools/d8_product_demo_launcher.sh dashboard --host 127.0.0.1 --port 8787 --timeout 3
tools/d8_product_demo_launcher.sh package
tools/d8_product_demo_launcher.sh seal
```

Product demo does not imply production release.

---

## 28. Stop Conditions

Stop immediately if any of these occur:

```text
SECRET_VALUE_EXPOSED=TRUE
MEMBER_PLAINTEXT_READ=TRUE without explicit authorization
PRODUCTION_DB_WRITE=TRUE without explicit authorization
ODOO_DB_WRITE=TRUE without explicit authorization
POS_ORDER_CREATED=TRUE without explicit authorization
PAYMENT_CAPTURE=TRUE without explicit authorization
SERVICE_RESTART=TRUE without explicit authorization
DEPLOY=TRUE without explicit authorization
PRODUCTION_RELEASE=TRUE without explicit authorization
EXTERNAL_API_CALL=TRUE without explicit authorization
EMBEDDING_GENERATED=TRUE without explicit authorization
REDTEAM_ARTIFACT_EXECUTABLE=TRUE
POLLUTION_GUARD=FALSE
REVERSE_INDEX_ISOLATION=FALSE
```

Required output:

```text
STATE=HOLD_OR_BLOCK_SAFETY_GATE
```

Then write a redteam event if allowed by D8 local DB policy.

---

## 29. One-Paste Path Principle

When asked for commands or Codex prompts, provide a safe one-paste path.

The path must include:

1. mandatory D8 preflight;
2. allowed paths;
3. forbidden paths;
4. safety flags;
5. validation plan;
6. report path;
7. seal path;
8. redteam writeback condition;
9. stop conditions.

Do not provide vague multi-step advice when a sealed one-paste task can be produced.

---

## 30. Final Principle

The system must advance the main trunk while preserving:

```text
no plaintext leakage
no unauthorized runtime action
no unauthorized DB write
no redteam pollution
no secret output
no production bypass
```

The correct agent posture is:

```text
fast
direct
bounded
packetized
verified
evidenced
sealed
```