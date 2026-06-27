# D8 30-Day Product Landing Roadmap

## Week 1: Stabilize Local Demo Package

- Stabilize `tools/d8_product_demo_launcher.py` and `tools/d8_product_demo_launcher.sh`.
- Improve dashboard readability for status, alerts, redteam, evals, reports, and seals.
- Verify `docs/product/D8_3_MINUTE_DEMO_SCRIPT.md`.
- Verify product docs and package manifest.
- Package a local-only demo that avoids Odoo writes, POS orders, payments, member plaintext, external API calls, and embeddings.

## Week 2: Cafe-Specific Evidence Layer

- Add cafe-specific labels in the dashboard and demo narrative.
- Prepare Odoo/POS read-only menu/eventbook evidence from sealed DB-only reports.
- Prepare voice/text operator scripts for status, preflight, alerts, and safe bridge checks.
- Build an incident demo story from the Odoo eventbook governance recovery sequence.
- Keep redteam artifacts non-executable and restricted.

## Week 3: First Real Operator Dry-Run

- Run the first real operator dry-run in 重新店 with no payment, no POS order, no member plaintext, and no Odoo DB write.
- Collect screenshots of dashboard, console status, alerts, preflight, and sealed reports.
- Collect operator feedback from store owner, staff, developer, and reviewer perspectives.
- Refine HOLD/WARN/BLOCK language so non-engineers can act on it.
- Prepare a simple sales page draft grounded in local evidence.

## Week 4: Pilot Package And Market Story

- Assemble the product pitch package.
- Prepare an invention disclosure package from existing technical and patent/investor docs.
- Draft service pricing for setup, monthly maintenance, Odoo/POS safe bridge, and custom governance rules.
- Prepare first customer pilot proposal for local-first agent governance.
- Produce media/demo script for a 30-second, 3-minute, and 10-minute presentation.

## Exit Criteria

- Local demo starts without external API.
- Dashboard is readable to a cafe operator.
- Preflight capsule appears before tasks.
- Alerts and redteam history can be shown without unsafe content execution.
- Odoo/POS bridge remains read-only.
- All claims are backed by evidence map rows.
- Every demo produces a report or seal.
