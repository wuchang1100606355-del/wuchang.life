# taiji01 File Restructure Package v0.1

Purpose: prepare a governed file restructuring workflow for the `taiji01` system host.

This package is conservative:

- read-only inventory first
- dry-run plan before copy/move
- no secret output
- no `.ssh`, key, token, service account JSON, or private env content collection
- no process kill or service restart
- no production Odoo/POS/container modification
- no automated remote write to `taiji01` unless it is a metric-governed write
- apply requires local SSH/local console human operation or metric-governed write

## Workflow

```bash
bash deploy/host_refactor/taiji01_file_restructure_v0_1/HOST_READONLY_INVENTORY.sh
bash deploy/host_refactor/taiji01_file_restructure_v0_1/BUILD_HOST_RESTRUCTURE_PLAN.sh
bash deploy/host_refactor/taiji01_file_restructure_v0_1/DRY_RUN_HOST_RESTRUCTURE.sh
```

Apply is intentionally gated:

```bash
APPLY=1 TAIJI_LOCAL_WRITE_WINDOW=1 bash deploy/host_refactor/taiji01_file_restructure_v0_1/APPLY_HOST_RESTRUCTURE.sh
```

Metric-governed write requires:

```bash
APPLY=1 \
TAIJI_METRIC_GOVERNED_WRITE=1 \
TAIJI_METRIC_GATE_DECISION=allow_with_audit \
TAIJI_METRIC_WRITE_MANIFEST=/path/to/approved_manifest.jsonl \
bash deploy/host_refactor/taiji01_file_restructure_v0_1/APPLY_HOST_RESTRUCTURE.sh
```

Do not run apply through non-interactive SSH automation without metric gate. Ungoverned remote automated write is `L3_metric_hazard`.

## Target Layout

```text
~/Taiji_System_Host/
  runtime/
  governance/
  deploy/
  adapters/
  schemas/
  docs/
  logs/
  archive/
  controlled_manifest_only/
```

`controlled_manifest_only/` receives metadata references only. Restricted files are not copied automatically.
