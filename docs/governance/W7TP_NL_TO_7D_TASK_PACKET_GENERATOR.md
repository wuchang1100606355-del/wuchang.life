# M32B: Natural Language to 7D Task Packet Generator

Status: `plan_only`

This contract defines a governed natural-language-to-7D-task-packet generator. It converts a redacted user request into a structured 7D task packet containing task id, intent summary, allowed files, forbidden actions, validation commands, commit message, focused git status, evidence chain requirement, risk level, privacy boundary, and human review requirement.

This stage does not call models, does not call cloud APIs, does not read secrets, does not read raw member PII, and does not execute tasks. Prediction may prepare a task packet, but prediction must never claim verified status before validation.
