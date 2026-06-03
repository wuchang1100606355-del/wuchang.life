# W7TP GEI Chat Handoff Template

## Current Context
- System: W7TP / XiaoJ / Wuchang Smart Cloud
- Mode: development / patent formation / evidence chain building
- Current field: governed hive restructure + GEI context field
- Runtime rule: no runtime copy, no restart, no DB write, no secret read unless explicitly approved

## Current Main Index
- W7TP_FIELD_ATLAS/02_governed_hive_master_index.yaml
- W7TP_FIELD_ATLAS/gei_context/W7TP_GEI_CONTEXT_INDEX_V1.yaml
- W7TP_FIELD_ATLAS/task_boards/W7TP_GOVERNED_HIVE_TASK_BOARD_V1.yaml

## Decision Boundary
GEI snapshots are context only.
They do not authorize:
- sync
- copy
- restart
- deploy
- DB write
- secret access

## Next Recommended Work
- Review latest GEI snapshot
- Keep task board compressed
- Create decision packet before any runtime action
