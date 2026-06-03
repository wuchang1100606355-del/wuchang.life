# W7TP Indexer One-Shot Server Job Governance

Status: `plan-only`

## Purpose

Move `wuchang_os_indexer` away from a local restart-loop container model and
toward a server-preferred one-shot or scheduled job model.

## Observed Facts

| Field | Observed Value |
| --- | --- |
| Container | `wuchang_os_indexer` |
| Image | `w7tp-indexer:latest` |
| Command | `python -u watcher.py` |
| ExitCode | `0` |
| Previous RestartPolicy | `unless-stopped` |
| Observed result | Restart loop caused by clean exit combined with restart policy |
| Current status | `Exited (0)` |

## Policy

```json
{
  "restart": "no",
  "execution_mode": "one_shot_or_scheduled",
  "target_host": "pure_linux_server"
}
```

The worker and any automated development agent must not:

- use SSH
- start a container
- transfer files to a server
- access or store secrets
- access raw member PII
- write a formal database
- commit to Git

This document does not authorize deployment, scheduling, container execution,
file transfer, or host-side changes.

## Required Result

Any future separately approved one-shot execution must return:

- summary JSON
- markdown report
- SHA256 proof
- exit code
- resource usage summary
