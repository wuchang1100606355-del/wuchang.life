# Total Factory / Branch Factory Automation Capability And Work Count Cleanup

STATE=TOTAL_FACTORY_BRANCH_AUTOMATION_CAPABILITY_SOLIDIFIED
DATE=2026-06-26
ROOT=/home/taiji_admin/Taiji_Hub

## 0. Total Factory Decision

This packet solidifies the AI Browser member UI generative reconstruction plan into an automation-capability frame.

Total Factory preflight:

- `TASK_NAME=TOTAL_FACTORY_BRANCH_AUTOMATION_SOLIDIFY_AND_WORK_COUNT_CLEANUP_PLAN`
- `DECISION=PASS`
- `ALLOW_SANDBOX=TRUE`
- `ALLOW_LAND=TRUE`

Landing boundary:

- This packet may add documentation and a dry-run inventory tool.
- It must not delete, move, rewrite, or archive workflow artifacts.
- It must not touch Odoo addon files, Odoo DB, POS orders, payments, services, deploy, secrets, or member plaintext.

## 1. Solidification Criteria

The plan is considered solidified only when all criteria are true:

1. Product plan exists and is decision-complete.
2. Missing items are enumerated with packet ownership.
3. Every implementation packet has allowed actions, forbidden actions, and validation.
4. Total Factory preflight returns `PASS` or `INFO`.
5. Work-count cleanup is inventory-only until a later archive LAND task.
6. Total Factory and Branch Factory responsibilities are separated.
7. No branch receives authority just because it can compute.
8. No cleanup candidate is deleted without a separate Total Factory seal.

Solidified source:

- `docs/product/AI_BROWSER_MEMBER_UI_GENERATIVE_RECONSTRUCTION_GAP_FILL_20260626.md`

## 2. Work Count Cleanup Mechanism

Tool:

```bash
python3 tools/d8_work_count_cleanup_inventory.py
```

Optional report:

```bash
python3 tools/d8_work_count_cleanup_inventory.py --write-report
```

The tool is intentionally inventory-only:

- It counts tasks, results, seals, duplicate task-name groups, orphan tasks, orphan results, and archive candidates.
- It never deletes.
- It never moves files.
- It never rewrites workflow artifacts.
- It never reads secrets or member plaintext.
- It only recommends archive candidates for a later LAND task.

### Cleanup States

| State | Meaning | Allowed action |
| --- | --- | --- |
| `active` | Latest work item for a task name | Keep |
| `open_orphan` | Task capsule has no result yet | Review, do not archive automatically |
| `sealed` | Task has result and seal | Keep or candidate archive later |
| `duplicate_old` | Older task with same task name | Candidate archive if aged and not protected |
| `protected` | WARN/HOLD/BLOCK/FAIL/ERROR | Keep for redteam/governance |
| `archive_candidate` | Older than retention and non-protected | Separate archive LAND task required |
| `dead_letter_required` | Inconsistent or unreadable artifact | Human review |

### Default Retention

- Keep latest 3 task capsules per task name.
- Mark older non-protected items as archive candidates only after 14 days.
- Never archive WARN/HOLD/BLOCK/FAIL/ERROR automatically.
- Never archive artifacts with read errors.
- Never archive artifacts referenced by current docs or active status pointers without a separate reference check.

### Required Archive LAND Task

Actual archive requires a separate task:

```text
TOTAL_FACTORY_WORK_COUNT_ARCHIVE_LAND_P1
```

That task must:

- run Total Factory preflight,
- run the inventory tool,
- produce a candidate archive manifest,
- ask Total Factory for final approval,
- move files only into a timestamped archive folder,
- write sha256 before/after manifest,
- validate no active pointer broke,
- finalize with a Total Factory seal.

No task is allowed to delete workflow evidence.

## 3. Total Factory / Branch Factory Capability Split

### Total Factory

The Total Factory is the only final governance authority.

Capabilities:

- Preflight and postflight gate.
- PASS/INFO/WARN/HOLD/BLOCK decision.
- Hard-wall enforcement.
- Review of work-count cleanup candidates.
- Evidence seal generation.
- Global task count and duplicate inventory.
- Cross-branch capability registry.
- Redteam quarantine and writeback.
- Final authority for release, archive, deployment, Odoo DB write, payment, and sensitive sync.

Forbidden:

- It should not perform branch work directly when a branch can safely prepare a candidate.
- It must not expose secrets or member plaintext to branch factories.

### Branch Factory

Branch Factories prepare candidates, never final authority.

Candidate branch types:

| Branch Factory | Work it may prepare | Must not do |
| --- | --- | --- |
| `member_ui_branch` | AI Browser UI mock payloads, dashboard shell, screenshots | Grant real member authority |
| `review_branch` | Review policy candidates, tests, evidence forms | Approve self or bypass owner review |
| `merchant_branch` | Merchant dashboard, POS display candidates, LINE WORKS notices | Create formal POS order/payment |
| `property_branch` | Property dashboard, committee/repair workflows | Grant cross-community access |
| `family_branch` | Family task/care reminder candidates | Expose minor/elder sensitive data |
| `integration_branch` | Google/LINE adapter status and candidate sync | Read OAuth secrets or treat external tools as authority |
| `redteam_branch` | Route scans, hard-wall tests, leakage tests | Promote redteam records into executable workflow |
| `cleanup_branch` | Inventory and archive-candidate manifests | Delete/move without Total Factory archive seal |

### Branch Output Packet

Every branch output must use:

```json
{
  "branch_id": "member_ui_branch",
  "task_name": "AI_BROWSER_MEMBER_UI_DEMO_SHELL_LAND_P1",
  "authority": "candidate_only",
  "input_refs": [],
  "output_refs": [],
  "forbidden_actions": [
    "secret_read",
    "member_plaintext_read",
    "odoo_db_write",
    "payment_capture",
    "service_restart",
    "deploy"
  ],
  "validation": {
    "tests_run": [],
    "screenshots": [],
    "route_scan": null
  },
  "total_factory_required": true
}
```

## 4. Automation Capability Levels

| Level | Name | Allowed automation | Examples |
| --- | --- | --- | --- |
| L0 | Observe | Read metadata and refs | Count tasks, list routes, inspect docs |
| L1 | Draft | Produce candidate docs/code | UI mock spec, review policy draft |
| L2 | Dry-run | Run no-write verification | payload lint, screenshot, route scan |
| L3 | Sandbox write | Write sandbox docs/tools/assets | demo shell, dry-run tools |
| L4 | Controlled local write | Modify Odoo addon or local model | requires Total Factory seal and tests |
| L5 | External candidate sync | Send ref-only messages/tasks | Google/LINE candidate notifications |
| L6 | Production-impacting action | DB write, deploy, restart, payment | human + Total Factory explicit release only |

Default for current member UI work:

- P1 demo shell: L3 max.
- P2 review workbench: L4 after explicit release.
- P5 integrations: L5 candidate-only, no secrets printed.
- Cleanup: L0/L1 until archive LAND task.

## 5. Automation Work Queue Rules

Each automated work item must have:

- unique `task_name`,
- branch owner,
- Total Factory preflight,
- allowed paths,
- forbidden paths,
- expected output,
- evidence ref,
- result state,
- retention state,
- next safe command.

Queue limits:

- Max 1 active LAND task per branch.
- Max 3 open orphan tasks per branch before cleanup review.
- Max 10 duplicate task capsules per task name before mandatory inventory.
- Any WARN/HOLD/BLOCK pauses branch automation until reviewed.
- Any public route/security redteam finding pauses member/review UI promotion.

## 6. Immediate Capability Roadmap

### R1: Inventory Foundation

Deliverable:

- `tools/d8_work_count_cleanup_inventory.py`

Validation:

- Run without `--write-report`.
- Confirm counts and candidates only.

### R2: Member UI Branch

Deliverable:

- `AI_BROWSER_MEMBER_UI_DEMO_SHELL_LAND_P1`

Validation:

- Mock payload PII scan.
- Responsive screenshots.
- No public write route.

### R3: Review Branch

Deliverable:

- `AI_BROWSER_REVIEW_WORKBENCH_LAND_P2`

Validation:

- Self-review blocked.
- Evidence ref required.
- Append-only review event.

### R4: Branch Factory Registry

Deliverable:

- Branch capability registry JSON/YAML.

Validation:

- Every branch has max automation level.
- Every branch has forbidden actions.
- Every branch has Total Factory escalation rules.

### R5: Archive Candidate Workflow

Deliverable:

- Archive manifest generator.

Validation:

- No delete mode.
- Sha256 manifest before/after.
- Active pointer check.

## 7. Redteam Rules

Must HOLD:

- Any cleanup script with delete mode.
- Any branch writing production DB.
- Any branch reading OAuth secrets.
- Any branch syncing member plaintext to Google/LINE.
- Any branch granting authority from a claim.
- Any branch auto-approving owner-required records.
- Any branch treating Google Tasks/Sheets as authority.
- Any route using public unauthenticated write for member/review state.

Must BLOCK:

- Payment capture by AI.
- Service restart/deploy without explicit release.
- Secret print.
- Member plaintext dump.
- Redteam record promoted into executable workflow.

## 8. Next Safe Command

```bash
python3 tools/d8_work_count_cleanup_inventory.py
```
