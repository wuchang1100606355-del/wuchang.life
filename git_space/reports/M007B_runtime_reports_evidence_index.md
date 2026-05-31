# M007B Runtime Reports Evidence Index

Purpose:
Index runtime/reports and runtime/memos as evidence material without committing all generated reports.

Source groups:
- runtime/reports/
- runtime/memos/
- runtime/broadcast/

Reason:
- These contain development reports, handoff notes, dry-run results, validation records, Odoo install reports, gateway migration reports, patent evidence maps, and W7TP engineering records.
- They are valuable evidence but too broad and generated to commit as source baseline.
- They may include timestamps, operational traces, environment details, or sensitive context.

Policy:
- Commit curated indexes and selected evidence summaries only.
- Do not bulk commit all runtime/reports.
- Do not commit runtime/memos raw unless reviewed.
- Evidence packs should be redacted before bundle/cold backup.
