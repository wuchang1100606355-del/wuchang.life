# M007 Tests / Validation Scope Decision

Original M007 inventory included runtime/reports and runtime/memos, too broad for test baseline.

M007A includes:
- tests/test_*.py
- Taiji_Odoo/addons/wuchang_core/tests/*.py
- runtime/check_7d.sh
- runtime/check_7d_full.sh

Excluded:
- runtime/reports/
- runtime/memos/
- runtime/broadcast/
- runtime generated reports
- historical handoff notes

Reason:
- Keep M007 focused on executable tests and validation scripts.
- Reports and memos belong to evidence/report index, not test core.
