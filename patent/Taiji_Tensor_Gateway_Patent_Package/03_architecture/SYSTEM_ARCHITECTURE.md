# System Architecture

## Runtime Pipeline

User Input  
→ Metric Ramp Translator  
→ Five-Dimensional Metric Tensor Packet  
→ Schema Validator  
→ Context Replay Index  
→ Dispatch Engine  
→ Governance Layer  
→ Worker / Confirmation / Rejection / Deadbox  
→ Metrics Feedback  
→ Replay Index Update

## Tensor Dimensions

1. Intent
2. Resource
3. Time
4. Authority
5. Topology

## Governance Decisions

- dry_run
- route_to_worker
- ask_confirm
- reject
- dead_letter

## Deadbox Trigger Conditions

- schema_invalid
- node_offline
- model_unavailable
- timeout
- permission_denied
- confirmation_missing
- risk_L3_forbidden
- execution_failed
- context_unrecoverable
- replay_detected
- stale_context
- confirmation_expired
- context_chain_broken
- duplicate_task_id
- pasted_output_as_command

## Replay Protection

The Context Replay Index prevents stale context, duplicated packets, reused confirmation tokens, old terminal output, offline queue replay, and deadbox replay attempts from being treated as new executable tasks.
