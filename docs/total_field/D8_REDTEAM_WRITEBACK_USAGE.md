# D8 Redteam Writeback Usage

`tools/d8_redteam_writeback.py` records warning and failure evidence in the local D8 redteam quarantine field.

It must not write to `d8_memory` or `d8_safe_memory`, and redteam text must never be treated as executable instructions.

## Dry Run

```bash
python3 tools/d8_redteam_writeback.py \
  --run-id TEST \
  --event-type TEST_DRY_RUN \
  --alert-level WARN \
  --title "Dry run" \
  --summary "Preview only" \
  --evidence-json '{}' \
  --reverse-refs-json '[]' \
  --affected-paths-json '[]' \
  --candidate-rule "Preview rule" \
  --dry-run
```

## Real Local Writeback

Use only for local `taiji_d8` redteam quarantine writeback. All rows are forced non-executable, quarantined, `redteam_only`, pollution-guarded, and reverse-index-only.
