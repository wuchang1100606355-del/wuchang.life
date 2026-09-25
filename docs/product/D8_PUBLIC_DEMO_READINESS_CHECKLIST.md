# D8 Public Demo Readiness Checklist

## Demo Prerequisites

- Use local repo path `/home/taiji_admin/Taiji_Hub`.
- Confirm demo is local-only and review-only.
- Confirm no external API, embedding, deploy, service restart, Odoo write, POS order, payment capture, member plaintext, or secret access.
- Confirm demo artifacts are public-safe and do not expose internal-only reasoning, dictionaries, weights, credentials, or private incident contents.

## Required Terminal Commands

Run these before the live session:

```bash
tools/d8_product_demo_launcher.sh status
tools/d8_product_demo_launcher.sh doctor
tools/d8_product_demo_launcher.sh smoke-test
tools/d8_product_demo_launcher.sh voice-demo --text "查狀態" --dry-run
tools/d8_product_demo_launcher.sh voice-demo --text "看告警" --dry-run
tools/d8_product_demo_launcher.sh pos-bridge-demo --dry-run
tools/d8_product_demo_launcher.sh dashboard --host 127.0.0.1 --port 8787 --timeout 3
```

## Dashboard Readiness

- Dashboard must bind only to `127.0.0.1`.
- Demo must not bind to `0.0.0.0`.
- Dashboard demo should be short-lived or manually stopped after the session.
- If dashboard does not start, switch to terminal-only fallback.

## Voice/Text Readiness

- Voice/text demo must use dry-run commands.
- Use only safe commands such as "查狀態" and "看告警".
- Do not record raw audio.
- Do not send voice text to an external API.

## Odoo/POS Read-Only Readiness

- POS bridge demo must run read-only or dry-run.
- Do not create orders.
- Do not capture payments.
- Do not read member plaintext.
- Do not write Odoo DB.

## Safety Flags Checklist

- SECRET_READ=FALSE
- MEMBER_PLAINTEXT_READ=FALSE
- RAW_AUDIO_SAVED=FALSE
- ODOO_DB_WRITE=FALSE
- ODOO_MODULE_UPGRADE=FALSE
- POS_ORDER_CREATED=FALSE
- PAYMENT_CAPTURE=FALSE
- PRODUCTION_DB_WRITE=FALSE
- SERVICE_RESTART=FALSE
- DEPLOY=FALSE
- PRODUCTION_RELEASE=FALSE
- EXTERNAL_API_CALL=FALSE
- EMBEDDING_GENERATED=FALSE

## Forbidden Live-Demo Actions

- Do not open secrets.
- Do not inspect environment/config values.
- Do not restart services.
- Do not deploy.
- Do not modify Odoo, LINE login, compose files, or AGENTS.md.
- Do not show internal-only rules, dictionaries, weights, or WHY_IT_RUNS material.

## Recovery Fallback

- If dashboard fails, use terminal console output.
- If voice dry-run fails, show text command flow.
- If POS bridge dry-run fails, show sealed read-only evidence report.
- If any safety flag fails, stop the demo and issue a HOLD.

## What To Show

- Status.
- Doctor.
- Smoke-test result.
- Alerts and redteam story.
- Public-safe one-pager.
- Pilot checklist.
- Readiness scorecard.
- Seal/report trail.

## What Not To Show

- Secret values.
- Member plaintext.
- Private incident contents.
- Odoo credentials/config.
- Internal-only dictionaries, weights, or WHY_IT_RUNS.
- Any claim of production release readiness.

## PASS / HOLD / FAIL Decision

- PASS: all required tests pass and safety flags remain false.
- HOLD: a non-safety demo dependency fails but no unsafe action occurs.
- FAIL: required outputs are missing or claim-safety review fails.
- BLOCK: any hard safety flag fails.
