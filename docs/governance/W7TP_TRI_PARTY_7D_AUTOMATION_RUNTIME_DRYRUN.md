# M32A: W7TP Tri-party 7D Automation Runtime Dry-run

Status: `dry_run_only`

This contract defines a dry-run runtime for tri-party 7D packet automation.

Roles:
- local_xiaoj_router
- code_agent_lane
- cloud_provider_lane

The runtime validates a 7D task packet, splits visibility, runs policy/dead-letter checks, and returns a dry-run report. It does not execute CODE, call cloud APIs, read credentials, SSH, start containers, or perform formal writes.
