# D8 Live Demo Runbook

## 3-Minute Demo

1. Open with: D8 is a local-first governance console around AI agents and Odoo/POS operations.
2. Run status.
3. Run doctor.
4. Show alerts/redteam story.
5. Run voice/text dry-run.
6. Run POS bridge read-only dry-run.
7. Close with sealed readiness scorecard.

## 10-Minute Demo

1. Show the public-safe one-pager.
2. Run demo status.
3. Run doctor.
4. Run smoke-test.
5. Explain redteam records are non-executable.
6. Run voice/text dry-runs.
7. Run POS bridge dry-run.
8. Run dashboard local bind timeout.
9. Show readiness scorecard.
10. Close with pilot proposal and safety boundaries.

## Dashboard Failure Fallback

If dashboard fails:

- Do not retry on `0.0.0.0`.
- Use terminal status, alerts, redteam, and scorecard.
- Mark dashboard item HOLD if needed.

## Voice Demo Failure Fallback

If voice/text command fails:

- Use text-only script.
- Do not record raw audio.
- Do not call external voice APIs.

## Odoo/POS Bridge Failure Fallback

If POS bridge dry-run fails:

- Do not run a live Odoo/POS command.
- Show DB-only reconciliation seal and safe bridge usage doc.
- Mark bridge item HOLD if needed.

## Terminal-Only Fallback

Use:

```bash
tools/d8_product_demo_launcher.sh status
tools/d8_product_demo_launcher.sh doctor
tools/d8_product_demo_launcher.sh smoke-test
tools/d8_total_field_console.sh status
tools/d8_total_field_console.sh alerts --limit 10
tools/d8_total_field_console.sh redteam --limit 10
tools/d8_total_field_console.sh evals --limit 10
```

## Exact Commands

```bash
tools/d8_product_demo_launcher.sh status
tools/d8_product_demo_launcher.sh doctor
tools/d8_product_demo_launcher.sh smoke-test
tools/d8_product_demo_launcher.sh voice-demo --text "查狀態"
tools/d8_product_demo_launcher.sh voice-demo --text "看告警"
tools/d8_product_demo_launcher.sh pos-bridge-demo
tools/d8_product_demo_launcher.sh dashboard --host 127.0.0.1 --port 8787 --timeout 3
```

For pre-demo verification, add `--dry-run` to voice and POS bridge commands.

## Narration Script

"D8 is not another coding agent. It is the local governance console before agents act. It checks state, redteam history, possible alerts, and guard evaluations, then returns a conservative decision and creates a sealed record."

"For this public demo, the Odoo/POS bridge is read-only. There is no payment, no order write, no member plaintext, no deploy, and no service restart."

## Red Flags To Stop Demo

- Secret access request.
- Member plaintext request.
- Payment/order write request.
- Odoo DB write request.
- Service restart request.
- Deploy request.
- Dashboard tries to bind outside localhost.
- Public claim says formal release is complete, patent-guaranteed, or absolutely safe.

## Final Close Statement

"D8 is ready for a public-safe local demo and a controlled cafe pilot, with human-approved runtime action only and read-only Odoo/POS boundaries."
